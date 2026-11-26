#!/usr/bin/env python3
"""Three conservative CPU pulse trials with passive baseline and recovery."""
import csv, glob, multiprocessing as mp, os, time
from datetime import datetime, timezone
ROOT='/sys/devices/virtual/powercap/intel-rapl'
OUT='/home/iknowyou/ATOCIA/repeated_trials.csv'

def read(p):
    with open(p) as f: return int(f.read().strip())
def burn(stop):
    x=1
    while not stop.is_set(): x=(x*1664525+1013904223)&0xffffffff

def main():
    domains={}
    for p in glob.glob(ROOT+'/intel-rapl:*'):
        try:
            n=read_name=open(p+'/name').read().strip()
            if n in ('package-0','psys'): domains[n]=(p+'/energy_uj',read(p+'/max_energy_range_uj'))
        except OSError: pass
    if 'package-0' not in domains: raise SystemExit('RAPL package unavailable')
    zones={}
    for p in glob.glob('/sys/class/thermal/thermal_zone*'):
        try:
            n=open(p+'/type').read().strip()
            if n in ('x86_pkg_temp','TCPU'): zones[n]=p+'/temp'
        except OSError: pass
    fields=['timestamp_utc','trial','phase','elapsed_s','package-0_power_w','psys_power_w']+['temp_C_'+n for n in zones]
    os.makedirs(os.path.dirname(OUT),exist_ok=True)
    with open(OUT,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for trial in range(1,4):
            stop=mp.Event(); worker=None
            prev={n:read(v[0]) for n,v in domains.items()}; pt=time.monotonic(); phase_start=pt
            phase='baseline'; phase_durations={'baseline':30,'load':20,'recovery':30}; count=0
            print(f'TRIAL {trial}: baseline',flush=True)
            while True:
                now=time.monotonic()
                if now-pt < 1: time.sleep(max(0,1-(now-pt)))
                now=time.monotonic(); dt=now-pt
                row={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'trial':trial,'phase':phase,'elapsed_s':round(now-phase_start,3)}
                for n,(path,mx) in domains.items():
                    cur=read(path); delta=cur-prev[n]
                    if delta<0: delta+=mx
                    row[n+'_power_w']=round(delta/1e6/dt,4) if dt>0 else ''
                    prev[n]=cur
                ts={}
                for n,path in zones.items():
                    try: ts[n]=read(path)/1000
                    except OSError: pass
                    row['temp_C_'+n]=round(ts[n],2) if n in ts else ''
                w.writerow(row); f.flush(); count+=1
                if ts and max(ts.values())>=75:
                    print('Temperature guard reached; aborting trial sequence',flush=True)
                    if worker: stop.set(); worker.join(timeout=2)
                    return
                pt=now
                if now-phase_start >= phase_durations[phase]:
                    if phase=='baseline':
                        phase='load'; phase_start=time.monotonic(); stop=mp.Event(); worker=mp.Process(target=burn,args=(stop,)); worker.start(); print(f'TRIAL {trial}: load',flush=True)
                    elif phase=='load':
                        stop.set(); worker.join(timeout=2)
                        if worker.is_alive(): worker.terminate(); worker.join()
                        worker=None; phase='recovery'; phase_start=time.monotonic(); print(f'TRIAL {trial}: recovery',flush=True)
                    else:
                        print(f'TRIAL {trial}: complete ({count} samples)',flush=True); break
            if worker:
                stop.set(); worker.join(timeout=2)
    print('DONE: '+OUT,flush=True)
if __name__=='__main__': main()
