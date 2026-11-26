#!/usr/bin/env python3
"""Single conservative 45 s CPU step with 30 s baseline and 60 s recovery."""
import argparse,csv,glob,multiprocessing as mp,os,time
from datetime import datetime,timezone
ROOT='/sys/devices/virtual/powercap/intel-rapl'
def read(p):
 with open(p) as f:return int(f.read().strip())
def burn(stop):
 x=1
 while not stop.is_set():x=(x*1664525+1013904223)&0xffffffff

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--load-s',type=int,default=45);ap.add_argument('--guard-c',type=float,default=75);ap.add_argument('--output',default='/home/iknowyou/ATOCIA/long_step_2026-11-20.csv');a=ap.parse_args()
 if not 10<=a.load_s<=60:ap.error('load-s must be 10..60')
 domains={}
 for p in glob.glob(ROOT+'/intel-rapl:*'):
  try:
   n=open(p+'/name').read().strip()
   if n in ('package-0','psys'):domains[n]=(p+'/energy_uj',read(p+'/max_energy_range_uj'))
  except OSError:pass
 zones={}
 for p in glob.glob('/sys/class/thermal/thermal_zone*'):
  try:
   n=open(p+'/type').read().strip()
   if n in ('x86_pkg_temp','TCPU'):zones[n]=p+'/temp'
  except OSError:pass
 fields=['timestamp_utc','phase','elapsed_s','package-0_power_w','psys_power_w']+['temp_C_'+n for n in zones]
 prev={n:read(v[0]) for n,v in domains.items()};pt=time.monotonic();phase='baseline';phase_start=pt;duration={'baseline':30,'load':a.load_s,'recovery':60};stop=mp.Event();worker=None
 with open(a.output,'w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  while True:
   time.sleep(max(0,1-(time.monotonic()-pt)));now=time.monotonic();dt=now-pt
   row={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'phase':phase,'elapsed_s':round(now-phase_start,3)}
   for n,(path,mx) in domains.items():
    cur=read(path);d=cur-prev[n]
    if d<0:d+=mx
    row[n+'_power_w']=round(d/1e6/dt,4);prev[n]=cur
   temps={}
   for n,path in zones.items():
    try:temps[n]=read(path)/1000
    except OSError:pass
    row['temp_C_'+n]=round(temps[n],2) if n in temps else ''
   w.writerow(row);f.flush();pt=now
   print('phase=%s t=%.1fs pkg=%.2fW temp=%s'%(phase,row['elapsed_s'],row['package-0_power_w'],temps),flush=True)
   if temps and max(temps.values())>=a.guard_c:
    print('STOP: thermal guard reached',flush=True);break
   if now-phase_start>=duration[phase]:
    if phase=='baseline':
     phase='load';phase_start=time.monotonic();stop=mp.Event();worker=mp.Process(target=burn,args=(stop,));worker.start();print('LOAD START',flush=True)
    elif phase=='load':
     stop.set();worker.join(timeout=2)
     if worker.is_alive():worker.terminate();worker.join()
     worker=None;phase='recovery';phase_start=time.monotonic();print('LOAD STOP — RECOVERY',flush=True)
    else:break
 if worker:
  stop.set();worker.join(timeout=2)
  if worker.is_alive():worker.terminate();worker.join()
 print('DONE '+a.output,flush=True)
if __name__=='__main__':main()
