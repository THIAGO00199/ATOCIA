#!/usr/bin/env python3
"""Job-cluster bootstrap and allocation-stratified analysis for PM100 v1.

Recomputes the existing chronological split and causal baselines. No model fitting.
Writes a new JSON artifact only; raw Parquet and prior reports are untouched.
"""
from __future__ import annotations
import json, math, hashlib
from pathlib import Path
import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "job_table.parquet"
OUTPUT = ROOT / "audit" / "trajectory_job_bootstrap_v1.json"
HORIZONS = (1, 2, 3, 6)
WINDOWS = (3, 5, 10)
REPS = 5000
SEED = 20261122

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def qci(x):
    return np.quantile(np.asarray(x), [0.025, 0.975]).tolist()

def main():
    con = duckdb.connect(database=":memory:", config={"threads":"1","memory_limit":"512MB"})
    src = str(INPUT.resolve()).replace("'", "''")
    rel = f"read_parquet('{src}')"
    val_cut, test_cut = con.execute(
        f"SELECT quantile_cont(epoch(start_time),0.70), quantile_cont(epoch(start_time),0.85) "
        f"FROM {rel} WHERE num_gpus_alloc>0 AND start_time IS NOT NULL"
    ).fetchone()
    query = (
        f"SELECT job_id,start_time,end_time,num_gpus_alloc,num_nodes_alloc,run_time,power_consumption "
        f"FROM {rel} WHERE num_gpus_alloc>0 AND start_time IS NOT NULL AND end_time IS NOT NULL "
        f"ORDER BY start_time"
    )
    cur = con.execute(query)
    jobs = []
    jobs_seen = 0
    skipped_overlap = 0
    skipped_bad_sequence = 0
    while True:
        batch = cur.fetchmany(256)
        if not batch:
            break
        for jid, start, end, ngpu, nnodes, runtime, seq in batch:
            jobs_seen += 1
            if seq is None or len(seq) < 2 or any(v is None for v in seq):
                skipped_bad_sequence += 1
                continue
            x = np.asarray(seq, dtype=np.float64)
            if not np.isfinite(x).all():
                skipped_bad_sequence += 1
                continue
            s, e = start.timestamp(), end.timestamp()
            if e < val_cut:
                split = "train"
            elif s >= val_cut and e < test_cut:
                split = "validation"
            elif s >= test_cut:
                split = "test"
            else:
                skipped_overlap += 1
                continue
            if split != "test":
                continue
            if nnodes is None or int(nnodes) < 1:
                continue

            # Per-job absolute-error sums, preserving job as the bootstrap unit.
            scores = {}
            for h in HORIZONS:
                n = len(x) - h
                if n <= 0:
                    continue
                y = x[h:]
                persistence = x[:-h]
                t = np.arange(n)
                lefts = {}
                cumulative = np.concatenate(([0.0], np.cumsum(x)))
                for w in WINDOWS:
                    left = np.maximum(0, t - w + 1)
                    count = t - left + 1
                    lefts[w] = (cumulative[t + 1] - cumulative[left]) / count
                scores[h] = {
                    "n": int(n),
                    "persistence_abs": float(np.abs(y - persistence).sum()),
                    **{f"ma{w}_abs": float(np.abs(y - lefts[w]).sum()) for w in WINDOWS}
                }
            if scores:
                jobs.append({
                    "job_id": int(jid),
                    "nodes": int(nnodes),
                    "gpus": int(ngpu or 0),
                    "runtime": int(runtime or 0),
                    "scores": scores
                })

    # The existing validation report fixed these choices before test:
    # micro MAE: MA3 at 20/40s; MA5 at 60/120s.
    # macro job MAE: MA3 at all horizons.
    micro_choice = {1:3, 2:3, 3:5, 6:5}
    macro_choice = {1:3, 2:3, 3:3, 6:3}
    result = {
        "dataset":"PM100 v1",
        "input_sha256":sha256(INPUT),
        "split":"same chronological start-time 70/85% quantile split; only existing test jobs",
        "validation_selected_micro_windows_seconds":{
            str(h*20): micro_choice[h]*20 for h in HORIZONS
        },
        "validation_selected_macro_windows_seconds":{
            str(h*20): macro_choice[h]*20 for h in HORIZONS
        },
        "bootstrap":{
            "unit":"whole job, paired model-vs-persistence",
            "replicates":REPS,
            "seed":SEED,
            "interval":"percentile 95%",
        },
        "jobs_seen_in_gpu_query":jobs_seen,
        "test_jobs_with_valid_sequences":len(jobs),
        "jobs_skipped_crossing_split_boundaries":skipped_overlap,
        "jobs_skipped_bad_sequences":skipped_bad_sequence,
        "horizons":{}
    }

    rng = np.random.default_rng(SEED)
    for h in HORIZONS:
        valid = [j for j in jobs if h in j["scores"]]
        if not valid:
            continue
        n = np.asarray([j["scores"][h]["n"] for j in valid], dtype=np.float64)
        base = np.asarray([j["scores"][h]["persistence_abs"] for j in valid])
        micro_w = micro_choice[h]
        macro_w = macro_choice[h]
        micro_model = np.asarray([j["scores"][h][f"ma{micro_w}_abs"] for j in valid])
        macro_model = np.asarray([j["scores"][h][f"ma{macro_w}_abs"] for j in valid])
        base_job = base / n
        micro_job = micro_model / n
        macro_job = macro_model / n

        # Point estimates
        point = {
            "horizon_seconds":h*20,
            "test_jobs":len(valid),
            "forecasts":int(n.sum()),
            "micro":{
                "baseline_mae_W":float(base.sum()/n.sum()),
                "selected_MA":micro_w,
                "model_mae_W":float(micro_model.sum()/n.sum()),
                "skill_pct":float(100*(1-micro_model.sum()/base.sum()))
            },
            "macro":{
                "baseline_job_mae_W":float(base_job.mean()),
                "selected_MA":macro_w,
                "model_job_mae_W":float(macro_job.mean()),
                "skill_pct":float(100*(1-macro_job.mean()/base_job.mean()))
            }
        }

        boot = {k: {"micro_delta":np.empty(REPS),"micro_skill":np.empty(REPS),
                    "macro_delta":np.empty(REPS),"macro_skill":np.empty(REPS)}
                for k in ("micro_selected","macro_selected")}
        for r in range(REPS):
            ix = rng.integers(0,len(valid),size=len(valid))
            b = base[ix]; nn = n[ix]
            for key, m in (("micro_selected",micro_model),("macro_selected",macro_model)):
                mm = m[ix]
                boot[key]["micro_delta"][r] = (b.sum()-mm.sum())/nn.sum()
                boot[key]["micro_skill"][r] = 100*(1-mm.sum()/b.sum())
                bd = b/nn; md = mm/nn
                boot[key]["macro_delta"][r] = float((bd-md).mean())
                boot[key]["macro_skill"][r] = 100*(1-float(md.mean()/bd.mean()))

        intervals = {}
        for key, arrays in boot.items():
            intervals[key] = {
                "micro_delta_W_ci95":qci(arrays["micro_delta"]),
                "micro_skill_pct_ci95":qci(arrays["micro_skill"]),
                "macro_job_delta_W_ci95":qci(arrays["macro_delta"]),
                "macro_job_skill_pct_ci95":qci(arrays["macro_skill"]),
                "bootstrap_probability_micro_improvement":float(np.mean(arrays["micro_delta"]>0)),
                "bootstrap_probability_macro_improvement":float(np.mean(arrays["macro_delta"]>0))
            }

        # Allocation strata: 1 node, 2-4 nodes, 5+ nodes.
        strata = {}
        for label, predicate in (
            ("1_node",lambda j:j["nodes"]==1),
            ("2_to_4_nodes",lambda j:2<=j["nodes"]<=4),
            ("5_plus_nodes",lambda j:j["nodes"]>=5),
        ):
            group=[j for j in valid if predicate(j)]
            if not group:
                continue
            gn=np.asarray([j["scores"][h]["n"] for j in group],dtype=float)
            gb=np.asarray([j["scores"][h]["persistence_abs"] for j in group],dtype=float)
            gm=np.asarray([j["scores"][h][f"ma{micro_w}_abs"] for j in group],dtype=float)
            strata[label]={
                "jobs":len(group),
                "micro_baseline_mae_W":float(gb.sum()/gn.sum()),
                "micro_selected_MA":micro_w,
                "micro_model_mae_W":float(gm.sum()/gn.sum()),
                "micro_skill_pct":float(100*(1-gm.sum()/gb.sum())),
                "macro_baseline_job_mae_W":float(np.mean(gb/gn)),
                "macro_model_job_mae_W":float(np.mean(gm/gn)),
                "macro_skill_pct":float(100*(1-np.mean(gm/gn)/np.mean(gb/gn)))
            }

        result["horizons"][str(h*20)] = {
            **point,
            "job_bootstrap_intervals":intervals,
            "node_allocation_strata":strata
        }

    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))
    print(f"Wrote: {OUTPUT}")

if __name__ == "__main__":
    main()
