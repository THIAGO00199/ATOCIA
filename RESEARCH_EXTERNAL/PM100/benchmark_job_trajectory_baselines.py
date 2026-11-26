#!/usr/bin/env python3
"""Causal naive baselines for within-job PM100 power-trajectory forecasting.

This is a secondary node/job-aggregate benchmark, not a per-GPU benchmark.
Jobs are kept separate and split chronologically by start/end time.
"""
from __future__ import annotations
import argparse, json, math, statistics
from pathlib import Path
import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parent
HORIZONS = (1, 2, 3, 6)  # 20, 40, 60, 120 seconds
WINDOWS = (3, 5, 10)

def metrics_add(acc, y, pred):
    err = pred - y
    acc["abs"] += float(np.abs(err).sum())
    acc["sq"] += float(np.square(err).sum())
    acc["n"] += int(err.size)
    acc["job_mae_sum"] += float(np.abs(err).mean())
    acc["job_rmse_sum"] += float(np.sqrt(np.square(err).mean()))
    acc["job_count"] += 1

def metrics_finish(acc):
    if not acc["n"]:
        return {"mae_W": None, "rmse_W": None, "n_forecasts": 0}
    return {
        "mae_W": acc["abs"] / acc["n"],
        "rmse_W": math.sqrt(acc["sq"] / acc["n"]),
        "macro_job_mae_W": acc["job_mae_sum"] / acc["job_count"],
        "macro_job_rmse_W": acc["job_rmse_sum"] / acc["job_count"],
        "n_forecasts": acc["n"],
        "n_jobs": acc["job_count"],
    }

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=ROOT / "job_table.parquet")
    ap.add_argument("--output", type=Path, default=ROOT / "audit" / "trajectory_baselines_v1.json")
    ap.add_argument("--memory-limit", default="512MB")
    args = ap.parse_args()

    con = duckdb.connect(database=":memory:", config={"threads":"1", "memory_limit":args.memory_limit})
    source = str(args.input.resolve()).replace("'", "''")
    rel = f"read_parquet('{source}')"

    # Calendar cutoffs are based only on GPU jobs' start times.
    q = con.execute(
        f"SELECT quantile_cont(epoch(start_time), 0.70), "
        f"quantile_cont(epoch(start_time), 0.85) FROM {rel} "
        "WHERE num_gpus_alloc > 0 AND start_time IS NOT NULL"
    ).fetchone()
    val_cut, test_cut = float(q[0]), float(q[1])

    query = (
        f"SELECT start_time, end_time, num_gpus_alloc, power_consumption "
        f"FROM {rel} WHERE num_gpus_alloc > 0 AND start_time IS NOT NULL "
        "AND end_time IS NOT NULL ORDER BY start_time"
    )
    cur = con.execute(query)

    acc = {
        split: {
            h: {"persistence":{"abs":0.0,"sq":0.0,"n":0,"job_mae_sum":0.0,"job_rmse_sum":0.0,"job_count":0},
                **{f"ma{w}":{"abs":0.0,"sq":0.0,"n":0,"job_mae_sum":0.0,"job_rmse_sum":0.0,"job_count":0} for w in WINDOWS},
                "jobs":0}
            for h in HORIZONS
        } for split in ("train","validation","test")
    }
    skipped_overlap = 0
    jobs_seen = 0
    jobs_with_sequence = 0

    while True:
        batch = cur.fetchmany(256)
        if not batch:
            break
        for start, end, gpu_count, seq in batch:
            jobs_seen += 1
            if seq is None or len(seq) < 2:
                continue
            if any(v is None for v in seq):
                continue
            x = np.asarray(seq, dtype=np.float64)
            if not np.isfinite(x).all():
                continue
            start_ts, end_ts = start.timestamp(), end.timestamp()
            if end_ts < val_cut:
                split = "train"
            elif start_ts >= val_cut and end_ts < test_cut:
                split = "validation"
            elif start_ts >= test_cut:
                split = "test"
            else:
                skipped_overlap += 1
                continue
            jobs_with_sequence += 1

            cumulative = np.concatenate(([0.0], np.cumsum(x)))
            for h in HORIZONS:
                n = len(x) - h
                if n <= 0:
                    continue
                y = x[h:]
                persistence = x[:-h]
                a = acc[split][h]
                metrics_add(a["persistence"], y, persistence)
                t = np.arange(n)
                for w in WINDOWS:
                    left = np.maximum(0, t - w + 1)
                    count = t - left + 1
                    pred = (cumulative[t + 1] - cumulative[left]) / count
                    metrics_add(a[f"ma{w}"], y, pred)
                a["jobs"] += 1

    result = {
        "dataset":"PM100 v1",
        "target":"job-level aggregate node input power (W), not GPU-only",
        "sampling_interval_seconds":20,
        "split_method":"chronological by GPU-job start time quantiles; discard jobs crossing cutoffs",
        "train_start_time_epoch_cutoff":val_cut,
        "test_start_time_epoch_cutoff":test_cut,
        "jobs_seen":jobs_seen,
        "jobs_used_after_split":jobs_with_sequence,
        "jobs_discarded_crossing_split_boundaries":skipped_overlap,
        "horizons_seconds":{str(h):h*20 for h in HORIZONS},
        "windows_samples":list(WINDOWS),
        "metrics":{},
        "validation_selected_window_by_horizon":{},
        "test_skill_vs_persistence":{},
        "validation_selected_window_by_horizon_macro":{},
        "macro_test_skill_vs_persistence":{},
        "caveat":"Naive causal baselines only; this does not test ATRP-1 or establish model superiority."
    }

    for split in ("train","validation","test"):
        result["metrics"][split] = {}
        for h in HORIZONS:
            a = acc[split][h]
            result["metrics"][split][str(h*20)] = {
                "jobs":a["jobs"],
                "persistence":metrics_finish(a["persistence"]),
                **{f"ma{w}":metrics_finish(a[f"ma{w}"]) for w in WINDOWS}
            }

    for h in HORIZONS:
        v = result["metrics"]["validation"][str(h*20)]
        candidates = [(v[f"ma{w}"]["mae_W"], w) for w in WINDOWS if v[f"ma{w}"]["mae_W"] is not None]
        best = min(candidates)[1] if candidates else None
        result["validation_selected_window_by_horizon"][str(h*20)] = best
        macro_candidates = [(v[f"ma{w}"]["macro_job_mae_W"], w) for w in WINDOWS if v[f"ma{w}"]["macro_job_mae_W"] is not None]
        macro_best = min(macro_candidates)[1] if macro_candidates else None
        result["validation_selected_window_by_horizon_macro"][str(h*20)] = macro_best
        t = result["metrics"]["test"][str(h*20)]
        if best is not None and t[f"ma{best}"]["mae_W"] is not None and t["persistence"]["mae_W"]:
            result["test_skill_vs_persistence"][str(h*20)] = (
                1.0 - t[f"ma{best}"]["mae_W"] / t["persistence"]["mae_W"]
            )
        else:
            result["test_skill_vs_persistence"][str(h*20)] = None
        if macro_best is not None and t[f"ma{macro_best}"]["macro_job_mae_W"] is not None and t["persistence"]["macro_job_mae_W"]:
            result["macro_test_skill_vs_persistence"][str(h*20)] = (
                1.0 - t[f"ma{macro_best}"]["macro_job_mae_W"] / t["persistence"]["macro_job_mae_W"]
            )
        else:
            result["macro_test_skill_vs_persistence"][str(h*20)] = None

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Wrote: {args.output}")

if __name__ == "__main__":
    main()
