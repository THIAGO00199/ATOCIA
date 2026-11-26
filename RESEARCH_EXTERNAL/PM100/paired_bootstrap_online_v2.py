#!/usr/bin/env python3
"""Paired uncertainty for frozen PM100 V2 EWMA vs MA3/MA5.
No tuning: EWMA alphas are read from the completed V2 audit JSON.
Resampling units: jobs and job-start dates (cluster bootstrap).
"""
from pathlib import Path
import json, hashlib
import numpy as np
import duckdb
import benchmark_online_models_v2 as base

ROOT=Path(__file__).resolve().parent
INPUT=ROOT/'job_table.parquet'
SOURCE=ROOT/'audit'/'trajectory_online_models_v2.json'
OUT=ROOT/'audit'/'paired_bootstrap_online_v2.json'
REPORT=ROOT/'PM100_PAIRED_BOOTSTRAP_ONLINE_V2.md'
REPS=10000
SEED=20261123
HORIZONS=base.HORIZONS

def dated_scan(con, rel, val_cut, test_cut):
    cur=con.execute(f"SELECT CAST(start_time AS DATE),start_time,end_time,num_gpus_alloc,num_nodes_alloc,power_consumption FROM {rel} WHERE num_gpus_alloc>0 AND start_time IS NOT NULL AND end_time IS NOT NULL ORDER BY start_time")
    while True:
        batch=cur.fetchmany(256)
        if not batch: break
        for day,start,end,gpus,nodes,seq in batch:
            if base.split_for(start,end,val_cut,test_cut)!='test': continue
            if seq is None or len(seq)<6 or any(v is None for v in seq): continue
            x=np.asarray(seq,dtype=np.float64)
            if not np.isfinite(x).all(): continue
            yield str(day),x,int(gpus or 0),int(nodes or 0)

def ci_job(arr, rng):
    # arr columns: comparator abs sum, EWMA abs sum, forecast count,
    # comparator job MAE, EWMA job MAE
    n=len(arr); micro=np.empty(REPS); macro=np.empty(REPS)
    # Chunk replicates to keep peak RAM bounded on the laptop.
    for lo in range(0,REPS,100):
        hi=min(REPS,lo+100); idx=rng.integers(0,n,size=(hi-lo,n)); z=arr[idx]
        micro[lo:hi]=(z[:,:,0].sum(axis=1)/z[:,:,2].sum(axis=1))-(z[:,:,1].sum(axis=1)/z[:,:,2].sum(axis=1))
        macro[lo:hi]=z[:,:,3].mean(axis=1)-z[:,:,4].mean(axis=1)
    return micro,macro

def ci_date(groups, rng):
    days=list(groups); n=len(days)
    blocks=[groups[d] for d in days]
    # Each date block stores sum comparator abs, sum EWMA abs, n forecasts,
    # sum comparator job MAE, sum EWMA job MAE, number of jobs.
    a=np.stack(blocks)
    idx=rng.integers(0,n,size=(REPS,n)); z=a[idx].sum(axis=1)
    micro=z[:,0]/z[:,2]-z[:,1]/z[:,2]
    macro=z[:,3]/z[:,5]-z[:,4]/z[:,5]
    return micro,macro

def summarize(v):
    return {'ci95_low_W':float(np.quantile(v,.025)), 'ci95_high_W':float(np.quantile(v,.975)),
            'bootstrap_median_W':float(np.median(v))}

def main():
    source=json.loads(SOURCE.read_text())
    alphas={int(h)//20:float(v['selected_validation']['ewma_alpha']) for h,v in source['horizons_seconds'].items()}
    con=duckdb.connect(':memory:',config={'threads':'1','memory_limit':'512MB'})
    src=str(INPUT.resolve()).replace("'","''"); rel=f"read_parquet('{src}')"
    val_cut,test_cut=con.execute(f"SELECT quantile_cont(epoch(start_time),.70),quantile_cont(epoch(start_time),.85) FROM {rel} WHERE num_gpus_alloc>0 AND start_time IS NOT NULL").fetchone()
    # Per horizon, one row per eligible job. Store absolute-error sums and job MAEs.
    per={h:{'ma3':[],'ma5':[]} for h in HORIZONS}
    dates={h:{'ma3':{},'ma5':{}} for h in HORIZONS}
    for day,x,g,nodes in dated_scan(con,rel,val_cut,test_cut):
        for h in HORIZONS:
            t,X,y=base.features(x,h,g,nodes)
            if X is None: continue
            ew=base.ewma_at_origins(x,t,alphas[h])
            preds={'ma3':np.array([x[max(0,i-2):i+1].mean() for i in t]),
                   'ma5':np.array([x[max(0,i-4):i+1].mean() for i in t])}
            ewerr=np.abs(y-ew); n=len(y); ew_sum=float(ewerr.sum()); ew_mae=float(ewerr.mean())
            for name,pred in preds.items():
                err=np.abs(y-pred); row=[float(err.sum()),ew_sum,n,float(err.mean()),ew_mae]
                per[h][name].append(row)
                # date aggregation includes sums of per-job macro errors and job count
                d=dates[h][name].setdefault(day,np.zeros(6,dtype=np.float64))
                d[0]+=row[0]; d[1]+=row[1]; d[2]+=row[2]; d[3]+=row[3]; d[4]+=row[4]; d[5]+=1
    rng=np.random.default_rng(SEED)
    out={'dataset':'PM100 v1','source_audit_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
         'input_sha256':base.sha256(INPUT),'method':'paired bootstrap of frozen V2 test predictions; no parameter retuning',
         'replicates':REPS,'seed':SEED,'positive_difference_means_comparator_has_higher_error_and_EWMA_is_better':True,
         'resampling':['job-level paired bootstrap (jobs sampled with replacement)','job-start-date cluster bootstrap (dates sampled with replacement; all jobs on sampled date retained)'],
         'horizons_seconds':{}}
    lines=['# PM100 — bootstrap pareado dos modelos online V2','',f'**Réplicas:** {REPS:,} por estimativa  |  **Seed:** {SEED}  |  **Data:** 23/11/2026','',
           'Parâmetros EWMA congelados conforme a seleção na validação V2. Nenhum hiperparâmetro foi reajustado. Diferença = MAE do comparador − MAE EWMA; valores positivos favorecem EWMA.','',
           'O bootstrap por job estima incerteza sobre jobs do holdout; o bootstrap por data preserva agrupamento de jobs pela data de início. O holdout contém poucas datas, portanto o intervalo por data é sensível ao pequeno número de clusters.','']
    for h in HORIZONS:
        hs=str(h*20); out['horizons_seconds'][hs]={}
        lines += [f'## Horizonte {hs} s','',f"EWMA α congelado: {alphas[h]:.2f}."]
        for name in ('ma3','ma5'):
            a=np.asarray(per[h][name],dtype=np.float64)
            if not len(a): continue
            job_micro,job_macro=ci_job(a,rng)
            dg=dates[h][name]
            date_arr=np.stack([dg[d] for d in sorted(dg)])
            date_micro,date_macro=ci_date({d:dg[d] for d in sorted(dg)},rng)
            point_micro=float(a[:,0].sum()/a[:,2].sum()-a[:,1].sum()/a[:,2].sum())
            point_macro=float(a[:,3].mean()-a[:,4].mean())
            item={'n_jobs':int(len(a)),'n_start_dates':int(len(dg)),
                  'point_difference_comparator_minus_ewma':{'micro_W':point_micro,'macro_W':point_macro},
                  'job_bootstrap':{'micro':summarize(job_micro),'macro':summarize(job_macro)},
                  'date_cluster_bootstrap':{'micro':summarize(date_micro),'macro':summarize(date_macro)}}
            out['horizons_seconds'][hs][name]=item
            lines += [f'### EWMA vs {name.upper()}','',f"- Jobs: {len(a):,}; datas de início: {len(dg)}.",
                      f"- Diferença pontual micro (MAE {name.upper()} − EWMA): **{point_micro:.3f} W**.",
                      f"- IC95% job bootstrap micro: [{item['job_bootstrap']['micro']['ci95_low_W']:.3f}, {item['job_bootstrap']['micro']['ci95_high_W']:.3f}] W.",
                      f"- IC95% cluster por data micro: [{item['date_cluster_bootstrap']['micro']['ci95_low_W']:.3f}, {item['date_cluster_bootstrap']['micro']['ci95_high_W']:.3f}] W.",
                      f"- Diferença pontual macro: **{point_macro:.3f} W**.",
                      f"- IC95% job bootstrap macro: [{item['job_bootstrap']['macro']['ci95_low_W']:.3f}, {item['job_bootstrap']['macro']['ci95_high_W']:.3f}] W.",
                      f"- IC95% cluster por data macro: [{item['date_cluster_bootstrap']['macro']['ci95_low_W']:.3f}, {item['date_cluster_bootstrap']['macro']['ci95_high_W']:.3f}] W.",'']
        lines += ['']
    lines += ['## Interpretação e limites','',
      '- Intervalos que incluem zero não sustentam diferença clara entre os modelos no nível de confiança nominal de 95%.',
      '- O bootstrap por job não preserva dependência temporal/calendária entre jobs; o cluster bootstrap por data tenta preservar choques compartilhados dentro de cada data, mas há poucos clusters.',
      '- O intervalo por data não equivale a validação em novos períodos: o holdout cobre somente 11 datas de início.',
      '- A análise compara apenas previsões de teste dos parâmetros V2 já congelados; não seleciona novos modelos.',
      '- O alvo continua sendo potência agregada dos nós por job, não potência GPU individual.','']
    OUT.write_text(json.dumps(out,indent=2),encoding='utf-8')
    REPORT.write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(out,indent=2)); print(f'Wrote: {OUT}'); print(f'Wrote: {REPORT}')

if __name__=='__main__': main()
