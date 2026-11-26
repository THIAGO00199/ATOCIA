#!/usr/bin/env python3
import csv, math, statistics, os
from pathlib import Path
base=Path("/home/iknowyou/ATOCIA/EXPERIMENTS")
files={
 "S1":"ATOCIA_PERTURBATION_RECOVERY_2026-11-21.csv",
 "S2":"ATOCIA_PERTURBATION_RECOVERY_SESSION2_2026-11-21.csv",
 "S3_HELD_OUT":"ATOCIA_PERTURBATION_RECOVERY_SESSION3_2026-11-21.csv",
}
metrics={
 "Package MSR power (W)":"msr_package_power_w",
 "PSys power (W)":"psys_power_w",
 "GT non-RC6 proxy (%)":"gpu_card1_gt_non_rc6_residency_pct",
 "CPU utilization (%)":"cpu_util_pct",
 "CPU package temp (C)":"temp_C_thermal_zone5_x86_pkg_temp",
}
horizons={1:"0.5s",2:"1s",4:"2s",10:"5s"}
windows={"MA-3":3,"MA-5":5,"MA-10":10}
def load(path):
 with open(path,newline="") as f: rows=list(csv.DictReader(f))
 return rows
def metric_vals(rows,key):
 out=[]
 for r in rows:
  try:
   t=float(r["elapsed_s"]); y=float(r[key])
   if math.isfinite(t) and math.isfinite(y): out.append((t,y))
  except (ValueError,KeyError,TypeError): pass
 return out
def score(vals,h,window):
 # Preserve temporal positions. A target must be exactly h row-steps later.
 # Exclude any gap > 0.8 s to avoid silently treating missing samples as regular.
 pairs=[]
 for i in range(window-1,len(vals)-h):
  history=vals[i-window+1:i+1]
  future=vals[i+h]
  if len(history)!=window: continue
  if any(history[j+1][0]-history[j][0] > .8 for j in range(len(history)-1)): continue
  if future[0]-vals[i][0] > h*.5+.35 or future[0]-vals[i][0] < h*.5-.35: continue
  pred=vals[i][1] if window==1 else statistics.mean(x[1] for x in history)
  pairs.append((future[1],pred))
 if not pairs:return None
 err=[p-y for y,p in pairs]
 return (len(err),sum(abs(x) for x in err)/len(err),math.sqrt(sum(x*x for x in err)/len(err)))
print("ATOCIA BASELINE FORECAST BENCHMARK — persistence vs trailing moving averages")
print("Horizon indexes nominal 0.5 s samples; MA windows: 1.5, 2.5, 5.0 s.")
print("Metrics: MAE and RMSE in each metric's native units. No ATOCIA predictor evaluated.")
for name,fn in files.items():
 rows=load(base/fn)
 print(f"\n## {name}: {len(rows)} rows")
 for label,key in metrics.items():
  vals=metric_vals(rows,key)
  if len(vals)<20: continue
  print(f"\n{label} (n={len(vals)})")
  for h,hlabel in horizons.items():
   out=[]
   for method,w in [("Persistence",1),*windows.items()]:
    s=score(vals,h,w)
    if s: out.append(f"{method}: MAE={s[1]:.4f}, RMSE={s[2]:.4f}, n={s[0]}")
   print(hlabel+" | "+" | ".join(out))
