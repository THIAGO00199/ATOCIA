#!/usr/bin/env python3
"""Causal online PM100 benchmark: persistence, trailing MA, EWMA, Ridge.

Fits Ridge only on the chronological training partition, selects EWMA alpha and
Ridge penalty on validation, and evaluates the frozen choices once on test.
Power sequences remain isolated by job. Uses NumPy/DuckDB only.
"""
from __future__ import annotations
import json, hashlib, math
from pathlib import Path
import duckdb
import numpy as np

ROOT=Path(__file__).resolve().parent
INPUT=ROOT/"job_table.parquet"
OUTPUT=ROOT/"audit"/"trajectory_online_models_v2.json"
HORIZONS=(1,2,3,6)
ALPHAS=(0.05,0.10,0.20,0.30,0.50,0.70,0.90)
LAMBDAS=(0.01,0.1,1.0,10.0,100.0)
WINDOWS=(3,5)

def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def features(x,h,gpus,nodes):
    n=len(x)-h-4
    if n<=0: return None,None,None
    t=np.arange(4,len(x)-h)
    cs=np.concatenate(([0.0],np.cumsum(x)))
    lags=np.column_stack([x[t],x[t-1],x[t-2],x[t-4]])
    means=np.column_stack([(cs[t+1]-cs[np.maximum(0,t-w+1)])/(t-np.maximum(0,t-w+1)+1) for w in (3,5)])
    left=np.maximum(0,t-4)
    cnt=t-left+1
    mean5=(cs[t+1]-cs[left])/cnt
    sq=np.concatenate(([0.0],np.cumsum(x*x)))
    var5=np.maximum(0.0,(sq[t+1]-sq[left])/cnt-mean5*mean5)
    std5=np.sqrt(var5)
    slope=(x[t]-x[t-2])[:,None]
    static=np.column_stack([np.full(len(t),np.log1p(max(0,gpus))),np.full(len(t),np.log1p(max(0,nodes)))])
    X=np.column_stack([lags,means,std5,slope,static])
    y=x[t+h]
    return t,X,y

def ewma_at_origins(x,origins,alpha):
    s=np.empty(len(x),dtype=np.float64); s[0]=x[0]
    for i in range(1,len(x)): s[i]=alpha*x[i]+(1-alpha)*s[i-1]
    return s[origins]

def split_for(start,end,val_cut,test_cut):
    a,b=start.timestamp(),end.timestamp()
    if b<val_cut:return "train"
    if a>=val_cut and b<test_cut:return "validation"
    if a>=test_cut:return "test"
    return "overlap"

def scan(con,rel,val_cut,test_cut,split):
    cur=con.execute(f"SELECT start_time,end_time,num_gpus_alloc,num_nodes_alloc,power_consumption FROM {rel} WHERE num_gpus_alloc>0 AND start_time IS NOT NULL AND end_time IS NOT NULL ORDER BY start_time")
    while True:
        batch=cur.fetchmany(256)
        if not batch:break
        for start,end,gpus,nodes,seq in batch:
            if split_for(start,end,val_cut,test_cut)!=split:continue
            if seq is None or len(seq)<6 or any(v is None for v in seq):continue
            x=np.asarray(seq,dtype=np.float64)
            if not np.isfinite(x).all():continue
            yield x,int(gpus or 0),int(nodes or 0)

def main():
    con=duckdb.connect(":memory:",config={"threads":"1","memory_limit":"512MB"})
    src=str(INPUT.resolve()).replace("'","''"); rel=f"read_parquet('{src}')"
    val_cut,test_cut=con.execute(f"SELECT quantile_cont(epoch(start_time),.70),quantile_cont(epoch(start_time),.85) FROM {rel} WHERE num_gpus_alloc>0 AND start_time IS NOT NULL").fetchone()
    p=10
    stats={h:{"sum":np.zeros(p),"sumsq":np.zeros(p),"G":np.zeros((p+1,p+1)),"b":np.zeros(p+1),"n":0} for h in HORIZONS}
    train_jobs=0
    for x,g,nodes in scan(con,rel,val_cut,test_cut,"train"):
        train_jobs+=1
        for h in HORIZONS:
            t,X,y=features(x,h,g,nodes)
            if X is None:continue
            s=stats[h]; s["sum"]+=X.sum(axis=0); s["sumsq"]+=(X*X).sum(axis=0)
            Z=np.column_stack([np.ones(len(X)),X])
            s["G"]+=Z.T@Z; s["b"]+=Z.T@y; s["n"]+=len(y)
    models={}
    for h,s in stats.items():
        mu=s["sum"]/s["n"]; sd=np.sqrt(np.maximum(s["sumsq"]/s["n"]-mu*mu,1e-12))
        T=np.zeros((p+1,p+1)); T[0,0]=1
        for j in range(p): T[j+1,0]=-mu[j]/sd[j]; T[j+1,j+1]=1/sd[j]
        G=T@s["G"]@T.T; b=T@s["b"]
        fits={}
        for lam in LAMBDAS:
            A=G.copy(); A[np.arange(1,p+1),np.arange(1,p+1)]+=lam
            try: fits[lam]=np.linalg.solve(A,b)
            except np.linalg.LinAlgError: fits[lam]=np.linalg.lstsq(A,b,rcond=None)[0]
        models[h]={"mu":mu,"sd":sd,"fits":fits,"n_train_forecasts":s["n"]}
    # Validation selection; all candidate decisions are made here, not on test.
    val={h:{"ridge":{lam:[0.,0.] for lam in LAMBDAS},"ewma":{a:[0.,0.] for a in ALPHAS}} for h in HORIZONS}
    val_jobs=0
    for x,g,nodes in scan(con,rel,val_cut,test_cut,"validation"):
        val_jobs+=1
        for h in HORIZONS:
            t,X,y=features(x,h,g,nodes)
            if X is None:continue
            m=models[h]; Q=(X-m["mu"])/m["sd"]
            for lam,beta in m["fits"].items():
                pred=beta[0]+Q@beta[1:]; a=val[h]["ridge"][lam]; a[0]+=float(np.abs(y-pred).sum()); a[1]+=len(y)
            for alpha in ALPHAS:
                pred=ewma_at_origins(x,t,alpha); a=val[h]["ewma"][alpha]; a[0]+=float(np.abs(y-pred).sum()); a[1]+=len(y)
    selected={}
    for h in HORIZONS:
        r=min(LAMBDAS,key=lambda z:val[h]["ridge"][z][0]/max(1,val[h]["ridge"][z][1]))
        e=min(ALPHAS,key=lambda z:val[h]["ewma"][z][0]/max(1,val[h]["ewma"][z][1]))
        selected[h]={"ridge_lambda":r,"ewma_alpha":e}
    # Test: frozen parameters, paired job evaluation, plus job-age terciles.
    names=["persistence","ma3","ma5","ewma","ridge"]
    acc={h:{name:{"abs":0.,"sq":0.,"n":0,"job_mae":0.,"jobs":0,"age_abs":[0.,0.,0.],"age_n":[0,0,0]} for name in names} for h in HORIZONS}
    test_jobs=0
    for x,g,nodes in scan(con,rel,val_cut,test_cut,"test"):
        test_jobs+=1
        for h in HORIZONS:
            t,X,y=features(x,h,g,nodes)
            if X is None:continue
            m=models[h]; Q=(X-m["mu"])/m["sd"]
            preds={"persistence":x[t],"ma3":np.array([x[max(0,i-2):i+1].mean() for i in t]),"ma5":np.array([x[max(0,i-4):i+1].mean() for i in t])}
            preds["ewma"]=ewma_at_origins(x,t,selected[h]["ewma_alpha"])
            beta=m["fits"][selected[h]["ridge_lambda"]]; preds["ridge"]=beta[0]+Q@beta[1:]
            cuts=np.array_split(np.arange(len(y)),3)
            for name,pred in preds.items():
                err=np.abs(y-pred); a=acc[h][name]
                a["abs"]+=float(err.sum()); a["sq"]+=float(np.square(y-pred).sum()); a["n"]+=len(y)
                a["job_mae"]+=float(err.mean()); a["jobs"]+=1
                for k,ix in enumerate(cuts):
                    if len(ix):a["age_abs"][k]+=float(err[ix].sum()); a["age_n"][k]+=len(ix)
    out={"dataset":"PM100 v1","input_sha256":sha256(INPUT),"target":"job-level aggregate node input power (W), not GPU-only",
         "split":"same chronological 70/85% start_time split; existing test evaluated once after validation selection",
         "horizons_seconds":{str(h*20):{"train_jobs":train_jobs,"validation_jobs":val_jobs,"test_jobs":test_jobs,
             "n_train_forecasts":models[h]["n_train_forecasts"],"selected_validation":selected[h],
             "validation_mae_W":{"ridge":{str(k):v[0]/max(1,v[1]) for k,v in val[h]["ridge"].items()},
                                 "ewma":{str(k):v[0]/max(1,v[1]) for k,v in val[h]["ewma"].items()}},
             "test":{name:{"micro_mae_W":a["abs"]/max(1,a["n"]),"micro_rmse_W":math.sqrt(a["sq"]/max(1,a["n"])),
                           "macro_job_mae_W":a["job_mae"]/max(1,a["jobs"]),"n_forecasts":a["n"],"n_jobs":a["jobs"],
                           "job_age_tercile_micro_mae_W":[a["age_abs"][k]/max(1,a["age_n"][k]) for k in range(3)]}
                     for name,a in acc[h].items()}}
             for h in HORIZONS},
         "ridge_features":["power_t","power_t-1","power_t-2","power_t-4","mean_3","mean_5","std_5","slope_t_minus_t2","log1p(num_gpus_alloc)","log1p(num_nodes_alloc)"],
         "ridge_lambdas":list(LAMBDAS),"ewma_alphas":list(ALPHAS),
         "regime_diagnostic":"test error stratified by within-job forecast-age terciles; descriptive only, not a causal changepoint detector",
         "limitations":["Only 11 test start dates; no broad temporal generalization claim.","Jobs are split by their own start/end times; forecasts use only within-job observations available at each origin.","Ridge is a within-job trajectory model; it is not pre-execution job power prediction.","No GPU-only power or GPU temperature is present in PM100.","Job-age terciles are a descriptive regime/nonstationarity diagnostic, not proof of physical regimes."]}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True); OUTPUT.write_text(json.dumps(out,indent=2),encoding="utf-8")
    print(json.dumps(out,indent=2)); print(f"Wrote: {OUTPUT}")

if __name__=="__main__":main()
