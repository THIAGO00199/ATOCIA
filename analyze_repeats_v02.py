#!/usr/bin/env python3
"""Offline descriptive analysis of existing ATOCIA repeated trials. No hardware load."""
import csv, statistics, math, os
ROOT='/home/iknowyou/ATOCIA'
SRC=os.path.join(ROOT,'repeated_trials.csv')
OUT=os.path.join(ROOT,'REPEAT_ANALYSIS_2026-11-20.md')
with open(SRC,newline='') as f: rows=list(csv.DictReader(f))
if not rows: raise SystemExit('No rows found')
trials=sorted(set(r['trial'] for r in rows),key=int)
def vals(q,k): return [float(r[k]) for r in q if r.get(k,'')]
def mean(q,k):
 v=vals(q,k); return statistics.mean(v) if v else float('nan')
def fmt(x,d=3): return f'{x:.{d}f}'
lines=['# ATOCIA — Repeated-trial descriptive analysis','', 'Source: `repeated_trials.csv` (existing data only; no new CPU workload).','', '## Per-trial phase means','', '| Trial | Phase | Samples | Package W | PSys W | CPU package °C |', '|---:|---|---:|---:|---:|---:|']
metrics=[]
for t in trials:
 phases={p:[r for r in rows if r['trial']==t and r['phase']==p] for p in ('baseline','load','recovery')}
 for p,q in phases.items():
  temps=vals(q,'temp_C_x86_pkg_temp')
  lines.append(f"| {t} | {p} | {len(q)} | {fmt(mean(q,'package-0_power_w'))} | {fmt(mean(q,'psys_power_w'))} | {fmt(statistics.mean(temps),2) if temps else 'NA'} |")
 b,l,rec=(phases[p] for p in ('baseline','load','recovery'))
 metrics.append((t,mean(l,'package-0_power_w')-mean(b,'package-0_power_w'),mean(l,'temp_C_x86_pkg_temp')-mean(b,'temp_C_x86_pkg_temp'),mean(rec,'temp_C_x86_pkg_temp')-mean(b,'temp_C_x86_pkg_temp'),mean(rec,'package-0_power_w')-mean(b,'package-0_power_w')))
lines += ['', '## Within-trial changes (load minus baseline; recovery minus baseline)', '', '| Trial | Package Δ W | CPU temp Δ °C | Recovery temp Δ °C | Recovery package Δ W |', '|---:|---:|---:|---:|---:|']
for t,pw,tc,tr,pwr in metrics: lines.append(f'| {t} | {fmt(pw)} | {fmt(tc,2)} | {fmt(tr,2)} | {fmt(pwr)} |')
lines += ['', '## Pooled descriptive summary','']
for idx,label in ((1,'Package power increase during load'),(2,'CPU package temperature increase during load'),(3,'Recovery temperature offset'),(4,'Recovery package power offset')):
 a=[m[idx] for m in metrics]
 lines.append(f'- {label}: mean {fmt(statistics.mean(a),3)}, trial range {fmt(min(a),3)} to {fmt(max(a),3)}.')
lines += ['', '## Interpretation and limits','', '- All three trials show increased package power and CPU package temperature during the CPU pulse.', '- Package power during recovery is close to baseline in all three trials; temperature is still slightly above baseline at the end of the 30-second recovery window.', '- These are descriptive results from three short repetitions, not a population-level statistical claim.', '- The CPU temperature sensor is quantized at roughly 1 °C and the sampling interval is about one second. This is too coarse for trustworthy fine-grained thermal time-constant identification.', '- Ambient temperature and fan RPM were not measured. The experiment therefore cannot identify absolute thermal resistance or a calibrated two-node RC model.', '- PSys is a distinct platform energy domain and must not be added to package power.', '- No causal claim about energy savings or controller superiority is supported.', '', '## Next offline modeling step','', 'Use these data to define the observation model and sensor uncertainty. For physical parameter identification, collect longer and varied pulse lengths with ambient temperature and fan behavior recorded. Keep controller work in offline simulation until the model passes held-out-trial prediction checks.','']
with open(OUT,'w') as f:f.write('\n'.join(lines))
print('WROTE',OUT)
print('\n'.join(lines[:34]))
