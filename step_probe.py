#!/usr/bin/env python3
"""Conservative one-worker CPU step probe with temperature stop guard."""
import argparse, csv, glob, multiprocessing as mp, os, time
from datetime import datetime, timezone
ROOT='/sys/devices/virtual/powercap/intel-rapl'

def read(path):
    with open(path) as f: return int(f.read().strip())

def burn(stop):
    x=1
    while not stop.is_set():
        x=(x*1664525+1013904223)&0xffffffff

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--duration',type=int,default=20)
    ap.add_argument('--interval',type=float,default=1.0)
    ap.add_argument('--stop-c',type=float,default=75.0)
    ap.add_argument('--output',default='/home/iknowyou/ATOCIA/step_probe.csv')
    a=ap.parse_args()
    if not 1 <= a.duration <= 30: ap.error('duration must be 1..30 seconds')
    domains={}
    for p in glob.glob(ROOT+'/intel-rapl:*'):
        try:
            n=open(p+'/name').read().strip()
            if n in ('package-0','psys'): domains[n]=(p+'/energy_uj',read(p+'/max_energy_range_uj'))
        except OSError: pass
    if 'package-0' not in domains: raise SystemExit('RAPL package counter unavailable')
    zones={}
    for p in glob.glob('/sys/class/thermal/thermal_zone*'):
        try:
            name=open(p+'/type').read().strip()
            if name in ('x86_pkg_temp','TCPU'): zones[name]=p+'/temp'
        except OSError: pass
    def temps():
        out={}
        for n,p in zones.items():
            try: out[n]=read(p)/1000
            except OSError: pass
        return out
    prev={n:read(v[0]) for n,v in domains.items()}; pt=time.monotonic(); start=pt
    stop=mp.Event(); worker=mp.Process(target=burn,args=(stop,)); worker.start()
    os.makedirs(os.path.dirname(os.path.abspath(a.output)),exist_ok=True)
    fields=['timestamp_utc','elapsed_s','package-0_power_w','psys_power_w']+['temp_C_'+n for n in zones]
    count=0; reason='duration_complete'
    try:
        with open(a.output,'w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
            while time.monotonic()-start < a.duration:
                time.sleep(max(0,pt+a.interval-time.monotonic()))
                now=time.monotonic(); dt=now-pt; row={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'elapsed_s':round(now-start,3)}
                for n,(path,mx) in domains.items():
                    cur=read(path); delta=cur-prev[n]
                    if delta<0: delta+=mx
                    row[n+'_power_w']=round(delta/1e6/dt,3) if dt>0 else ''
                    prev[n]=cur
                ts=temps()
                for n in zones: row['temp_C_'+n]=round(ts[n],2) if n in ts else ''
                w.writerow(row); f.flush(); count+=1
                print('sample=%d t=%.1fs package=%.2fW psys=%.2fW temps=%s' % (count,row['elapsed_s'],row['package-0_power_w'],row.get('psys_power_w',float('nan')),ts),flush=True)
                if ts and max(ts.values()) >= a.stop_c:
                    reason='temperature_guard'; print('STOP: temperature guard reached',flush=True); break
                pt=now
    finally:
        stop.set(); worker.join(timeout=2)
        if worker.is_alive(): worker.terminate(); worker.join()
    print('RESULT: '+reason+'; samples='+str(count)+'; output='+a.output,flush=True)
if __name__=='__main__': main()
