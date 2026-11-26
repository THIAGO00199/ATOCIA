#!/usr/bin/env python3
"""ATOCIA Pulse 0.2: read-only RAPL, thermal, power-supply and CPU telemetry."""
import argparse,csv,glob,os,time
from datetime import datetime,timezone
ROOT='/sys/devices/virtual/powercap/intel-rapl'
def txt(p):
 try:
  with open(p) as f:return f.read().strip()
 except (OSError,ValueError):return ''
def num(p):
 s=txt(p)
 try:return int(s)
 except (TypeError,ValueError):return None
def discover_domains():
 out={}
 for p in sorted(glob.glob(ROOT+'/intel-rapl:*')):
  n=txt(p+'/name')
  if n in ('package-0','psys') and os.path.isfile(p+'/energy_uj'):
   m=num(p+'/max_energy_range_uj')
   if m:out[n]=(p+'/energy_uj',m)
 return out
def discover_zones():
 out={}
 for p in sorted(glob.glob('/sys/class/thermal/thermal_zone*')):
  n=txt(p+'/type').replace(',','_')
  if n and os.path.isfile(p+'/temp'):out[os.path.basename(p)+'_'+n]=p+'/temp'
 return out
def discover_fans():
 out={}
 for d in glob.glob('/sys/class/hwmon/hwmon*'):
  chip=txt(d+'/name') or os.path.basename(d)
  for p in glob.glob(d+'/fan*_input'):
   out[chip+'_'+os.path.basename(p)]=p
 return out
def cpu_stat():
 line=txt('/proc/stat').splitlines()[0].split()
 vals=list(map(int,line[1:]))
 idle=vals[3]+(vals[4] if len(vals)>4 else 0)
 return sum(vals),idle
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--duration',type=float,default=60);ap.add_argument('--interval',type=float,default=1);ap.add_argument('--output',default='/home/iknowyou/ATOCIA/pulse_v02.csv');a=ap.parse_args()
 if a.duration<=0 or a.interval<=0:ap.error('duration and interval must be positive')
 domains=discover_domains();zones=discover_zones();fans=discover_fans()
 if 'package-0' not in domains:raise SystemExit('RAPL package-0 unavailable')
 supply=glob.glob('/sys/class/power_supply/*')
 ac=next((p for p in supply if txt(p+'/type')=='Mains'),None)
 bat=next((p for p in supply if txt(p+'/type')=='Battery'),None)
 freq='/sys/devices/system/cpu/cpu0/cpufreq/'
 prev={k:num(v[0]) for k,v in domains.items()};pt=time.monotonic();start=pt;cpu0=cpu_stat()
 fields=['timestamp_utc','elapsed_s','cpu_util_pct','cpu_freq_khz','cpu_governor','ac_online','battery_status','battery_capacity_pct']
 for k in domains:fields += [k+'_energy_uj',k+'_power_w']
 fields += ['temp_C_'+k for k in zones]+['fan_rpm_'+k for k in fans]
 os.makedirs(os.path.dirname(os.path.abspath(a.output)),exist_ok=True)
 with open(a.output,'w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();count=0
  while time.monotonic()-start<a.duration:
   time.sleep(max(0,pt+a.interval-time.monotonic()));now=time.monotonic();dt=now-pt
   cpu1=cpu_stat();total=cpu1[0]-cpu0[0];idle=cpu1[1]-cpu0[1];util=100*(total-idle)/total if total>0 else ''
   row={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'elapsed_s':round(now-start,3),'cpu_util_pct':round(util,2) if util!='' else '', 'cpu_freq_khz':num(freq+'scaling_cur_freq') or '', 'cpu_governor':txt(freq+'scaling_governor'), 'ac_online':txt(ac+'/online') if ac else '', 'battery_status':txt(bat+'/status') if bat else '', 'battery_capacity_pct':num(bat+'/capacity') if bat else ''}
   for k,(path,mx) in domains.items():
    cur=num(path)
    if cur is None:continue
    delta=cur-prev[k]
    if delta<0:delta+=mx
    row[k+'_energy_uj']=cur;row[k+'_power_w']=round(delta/1e6/dt,4) if dt>0 else '' ;prev[k]=cur
   for k,path in zones.items():
    v=num(path);row['temp_C_'+k]=round(v/1000,2) if v is not None else ''
   for k,path in fans.items():row['fan_rpm_'+k]=num(path) or ''
   w.writerow(row);f.flush();count+=1;pt=now;cpu0=cpu1
   print('sample=%d elapsed=%.1fs package=%.2fW util=%s%% temp=%s'%(count,now-start,row.get('package-0_power_w',0),row['cpu_util_pct'],{k:row['temp_C_'+k] for k in zones if 'x86_pkg_temp' in k}),flush=True)
 print('DONE samples=%d output=%s'%(count,a.output),flush=True)
if __name__=='__main__':main()
