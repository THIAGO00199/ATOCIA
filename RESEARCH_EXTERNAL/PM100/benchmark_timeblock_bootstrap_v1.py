#!/usr/bin/env python3
"""Calendar-start-date moving-block bootstrap for PM100 test jobs.

Jobs remain intact and paired. Contiguous blocks of job start dates are resampled
circularly; no model fitting and no modification of source data or old artifacts.
"""
from __future__ import annotations
import json, hashlib
from pathlib import Path
import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "job_table.parquet"
OUTPUT = ROOT / "audit" / "trajectory_timeblock_bootstrap_v1.json"
HORIZONS = (1, 2, 3, 6)
BLOCK_DAYS = (1, 2, 3)
REPS = 5000
SEED = 20261122
MICRO = {1:3, 2:3, 3:5, 6:5}
MACRO = {1:3, 2:3, 3:3, 6:3}

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def ci(a):
    return [float(x) for x in np.quantile(a,[.025,.975])]

def main():
    con=duckdb.connect(":memory:",config={"threads":"1","memory_limit":"512MB"})
    src=str(INPUT.resolve()).replace("'","''")
    rel=f"read_parquet('{src}')"
    val_cut,test_cut=con.execute(
        f"SELECT quantile_cont(epoch(start_time),.70),quantile_cont(epoch(start_time),.85) "
        f"FROM {rel} WHERE num_gpus_alloc>0 AND start_time IS NOT NULL"
    ).fetchone()
    cur=con.execute(
        f"SELECT job_id,start_time,end_time,power_consumption FROM {rel} "
        "WHERE num_gpus_alloc>0 AND start_time IS NOT NULL AND end_time IS NOT NULL ORDER BY start_time"
    )
    jobs=[]; seen=0; overlap=0; bad=0
    while True:
        batch=cur.fetchmany(256)
        if not batch: break
        for jid,start,end,seq in batch:
            seen+=1
            if seq is None or len(seq)<2 or any(v is None for v in seq):
                bad+=1; continue
            x=np.asarray(seq,dtype=np.float64)
            if not np.isfinite(x).all(): bad+=1; continue
            s,e=start.timestamp(),end.timestamp()
            if e<val_cut: split="train"
            elif s>=val_cut and e<test_cut: split="validation"
            elif s>=test_cut: split="test"
            else: overlap+=1; continue
            if split!="test": continue
            day=start.date().isoformat()
            scores={}
            for h in HORIZONS:
                n=len(x)-h
                if n<=0: continue
                y=x[h:]; p=x[:-h]
                t=np.arange(n); cs=np.concatenate(([0.],np.cumsum(x)))
                preds={}
                for w in (3,5):
                    left=np.maximum(0,t-w+1); cnt=t-left+1
                    preds[w]=(cs[t+1]-cs[left])/cnt
                scores[h]={"n":int(n),"base_abs":float(np.abs(y-p).sum()),
                           **{f"ma{w}_abs":float(np.abs(y-preds[w]).sum()) for w in (3,5)}}
            if scores: jobs.append({"day":day,"scores":scores})
    days=sorted({j["day"] for j in jobs})
    day_index={d:i for i,d in enumerate(days)}
    rng=np.random.default_rng(SEED)
    out={
      "dataset":"PM100 v1","input_sha256":sha256(INPUT),
      "split":"existing chronological 70/85% start-time split; existing test jobs only",
      "resampling_unit":"circular moving blocks of consecutive calendar start dates; jobs retained whole and paired within sampled dates",
      "block_lengths_days":list(BLOCK_DAYS),"replicates":REPS,"seed":SEED,
      "jobs_seen":seen,"test_jobs_with_valid_sequences":len(jobs),
      "jobs_skipped_crossing_split_boundaries":overlap,"jobs_skipped_bad_sequences":bad,
      "test_start_date_count":len(days),"test_start_date_first":days[0] if days else None,
      "test_start_date_last":days[-1] if days else None,
      "note":"Jobs are clustered by start date, not by every timestamp they span. Circular resampling is a sensitivity analysis; the short test calendar span limits temporal inference.",
      "horizons":{}
    }
    for h in HORIZONS:
        valid=[j for j in jobs if h in j["scores"]]
        if not valid: continue
        dcount=len(days)
        # Per-start-date sufficient statistics for paired micro and macro estimands.
        agg={day:np.zeros(5,dtype=np.float64) for day in days}
        # columns: base abs, selected micro abs, selected macro abs, n forecasts, jobs
        mw,aw=MICRO[h],MACRO[h]
        for j in valid:
            sc=j["scores"][h]; a=agg[j["day"]]
            a[0]+=sc["base_abs"]; a[1]+=sc[f"ma{mw}_abs"]; a[2]+=sc[f"ma{aw}_abs"]
            a[3]+=sc["n"]; a[4]+=1
        mat=np.stack([agg[d] for d in days])
        point_base=mat[:,0].sum(); point_micro=mat[:,1].sum(); point_macro=mat[:,2].sum()
        point_n=mat[:,3].sum(); point_jobs=mat[:,4].sum()
        # macro requires per-job MAE; separately aggregate sum of per-job MAE by day
        macro_base={day:0. for day in days}; macro_micro={day:0. for day in days}; macro_model={day:0. for day in days}
        for j in valid:
            sc=j["scores"][h]; n=sc["n"]; day=j["day"]
            macro_base[day]+=sc["base_abs"]/n
            macro_micro[day]+=sc[f"ma{mw}_abs"]/n
            macro_model[day]+=sc[f"ma{aw}_abs"]/n
        mbase=np.array([macro_base[d] for d in days])
        mmicro=np.array([macro_micro[d] for d in days])
        mmodel=np.array([macro_model[d] for d in days])
        # Micro selected-window and macro selected-window both compared paired to persistence.
        block_results={}
        for L in BLOCK_DAYS:
            if L>dcount: continue
            micro_skill=np.empty(REPS); macro_skill=np.empty(REPS)
            micro_delta=np.empty(REPS); macro_delta=np.empty(REPS)
            for r in range(REPS):
                starts=rng.integers(0,dcount,size=int(np.ceil(dcount/L)))
                sampled=[]
                for s0 in starts: sampled.extend((s0+k)%dcount for k in range(L))
                counts=np.bincount(sampled[:dcount],minlength=dcount).astype(float)
                b=float(np.dot(counts,mat[:,0])); mm=float(np.dot(counts,mat[:,1]))
                nn=float(np.dot(counts,mat[:,3]))
                micro_skill[r]=100*(1-mm/b); micro_delta[r]=(b-mm)/nn
                # each sampled start-date cluster repeats its complete jobs
                mb=float(np.dot(counts,mbase)); md=float(np.dot(counts,mmodel))
                macro_skill[r]=100*(1-md/mb); macro_delta[r]=(mb-md)/max(1.,np.dot(counts,mat[:,4]))
            block_results[str(L)]={
              "micro_skill_pct_ci95":ci(micro_skill),"micro_delta_W_ci95":ci(micro_delta),
              "macro_skill_pct_ci95":ci(macro_skill),"macro_job_delta_W_ci95":ci(macro_delta),
              "bootstrap_probability_micro_improvement":float(np.mean(micro_delta>0)),
              "bootstrap_probability_macro_improvement":float(np.mean(macro_delta>0))
            }
        out["horizons"][str(h*20)]={
          "test_jobs":len(valid),"forecasts":int(point_n),
          "point_estimates":{
            "micro_baseline_mae_W":float(point_base/point_n),
            "micro_selected_MA":mw,"micro_model_mae_W":float(point_micro/point_n),
            "micro_skill_pct":float(100*(1-point_micro/point_base)),
            "macro_baseline_job_mae_W":float(mbase.sum()/point_jobs),
            "macro_selected_MA":aw,"macro_model_job_mae_W":float(mmodel.sum()/point_jobs),
            "macro_skill_pct":float(100*(1-mmodel.sum()/mbase.sum()))
          },
          "date_block_bootstrap":block_results
        }
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(out,indent=2),encoding="utf-8")
    print(json.dumps(out,indent=2)); print(f"Wrote: {OUTPUT}")

if __name__=="__main__": main()
