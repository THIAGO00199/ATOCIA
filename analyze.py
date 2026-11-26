#!/usr/bin/env python3
"""Summarize ATOCIA Pulse CSV captures using only Python's standard library."""
import argparse, csv, math, statistics
from pathlib import Path

p = argparse.ArgumentParser(description='Summarize Pulse telemetry CSV')
p.add_argument('csv_file', nargs='?', default='/home/iknowyou/ATOCIA/pulse.csv')
a = p.parse_args()
path = Path(a.csv_file)
with path.open(newline='', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))
if not rows:
    raise SystemExit('No samples found')
print(f'ATOCIA Pulse report — {path.name}')
print(f'Samples: {len(rows)}')
try:
    elapsed = [float(r['elapsed_s']) for r in rows]
    print(f'Duration: {elapsed[-1]:.2f} s')
except (KeyError, ValueError):
    pass
for col in rows[0]:
    if col.endswith('_power_w'):
        vals = [float(r[col]) for r in rows if r.get(col, '')]
        if vals:
            print(f'{col}: mean={statistics.mean(vals):.3f} W | median={statistics.median(vals):.3f} W | min={min(vals):.3f} W | max={max(vals):.3f} W | stdev={statistics.pstdev(vals):.3f} W')
for col in rows[0]:
    if col.startswith('temp_C_'):
        vals = [float(r[col]) for r in rows if r.get(col, '')]
        if vals:
            print(f'{col}: mean={statistics.mean(vals):.2f} C | min={min(vals):.2f} C | max={max(vals):.2f} C')
print('Note: package-0 and psys are different scopes; do not add their power values.')
