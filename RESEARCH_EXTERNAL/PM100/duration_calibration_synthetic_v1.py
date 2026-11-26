#!/usr/bin/env python3
"""Duration-conditioned thresholds and controlled synthetic error-step tests."""
from __future__ import annotations
import json, hashlib
from pathlib import Path
import duckdb
import numpy as np

ROOT=Path(__file__).resolve().parent
INPUT=ROOT/"job_table.parquet"
BASE=ROOT/"audit"/"trajectory_online_models_v2.json"
OUT=ROOT/"audit"/"duration_calibration_synthetic_v1.json"
REPORT=ROOT/"PM100_DURATION_CALIBRATION_SYNTHETIC_V1.md"
H=(1,2,3,6); BASE_N=5; MIN_N=15; MIN_SYN=40
K=.50; DELTA=.25; TAIL=.05; SHIFTS=(.5,1.,2.)

def sha(p):
    z=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): z.update(b)
    return z.hexdigest()

def split(a,b,v,t):
    a=a.timestamp(); b=b.timestamp()
    if b<v:return "train"
    if a>=v and b<t:return "validation"
    if a>=t:return "test"
    return "overlap"

def scan(con,rel,v,t,part):
    cur=con.execute(f"SELECT start_time,end_time,power_consumption FROM {rel} WHERE num_gpus_alloc>0 AND start_time IS NOT NULL AND end_time IS NOT NULL ORDER BY start_time")
    while True:
        batch=cur.fetchmany(256)
        if not batch:break
        for a,b,seq in batch:
            if split(a,b,v,t)!=part or seq is None or len(seq)<6 or any(x is None for x in seq):continue
            x=np.asarray(seq,dtype=np.float64)
            if np.isfinite(x).all():yield x

def errors(x,h,alpha):
    if len(x)-h-4<MIN_N:return None
    t=np.arange(4,len(x)-h); s=np.empty(len(x)); s[0]=x[0]
    for i in range(1,len(x)):s[i]=alpha*x[i]+(1-alpha)*s[i-1]
    return np.abs(x[t+h]-s[t])

def paths(e):
    ref=e[:BASE_N]; mu=float(ref.mean()); sd=max(float(ref.std(ddof=1)),1.)
    z=(e[BASE_N:]-mu)/sd
    cpath=np.zeros(len(z)); ppath=np.zeros(len(z))
    c=0.; ps=0.; pmin=0.; pm=0.; n=0
    for i,v in enumerate(z):
        v=float(v); c=max(0.,c+v-K); cpath[i]=c
        n+=1; pm+=(v-pm)/n; ps+=v-pm-DELTA; pmin=min(pmin,ps); ppath[i]=ps-pmin
    return sd,cpath,ppath

def qhi(a,q):return float(np.quantile(np.asarray(a),q,method="higher"))
def bidx(n,edges):return int(np.searchsorted(edges,n,side="right"))

def main():
    base=json.loads(BASE.read_text())
    al={1:base["horizons_seconds"]["20"]["selected_validation"]["ewma_alpha"],
        2:base["horizons_seconds"]["40"]["selected_validation"]["ewma_alpha"],
        3:base["horizons_seconds"]["60"]["selected_validation"]["ewma_alpha"],
        6:base["horizons_seconds"]["120"]["selected_validation"]["ewma_alpha"]}
    con=duckdb.connect(":memory:",config={"threads":"1","memory_limit":"512MB"})
    src=str(INPUT.resolve()).replace("'","''"); rel=f"read_parquet('{src}')"
    v,t=con.execute(f"SELECT quantile_cont(epoch(start_time),.70),quantile_cont(epoch(start_time),.85) FROM {rel} WHERE num_gpus_alloc>0 AND start_time IS NOT NULL").fetchone()
    val={h:[] for h in H}; seen={"validation":0,"test":0}
    for x in scan(con,rel,v,t,"validation"):
        seen["validation"]+=1
        for h in H:
            e=errors(x,h,al[h])
            if e is None:continue
            _,c,p=paths(e)
            val[h].append({"n":len(e),"c":float(c.max(initial=0)),"p":float(p.max(initial=0))})
    cal={}
    for h in H:
        ns=[r["n"] for r in val[h]]
        edges=[qhi(ns,q) for q in (.25,.5,.75)]
        bins={i:[] for i in range(4)}
        for r in val[h]:bins[bidx(r["n"],edges)].append(r)
        cal[h]={"edges":edges,"bins":{}}
        for i in range(4):
            a=bins[i]
            cal[h]["bins"][str(i)]={"n_val":len(a),"min_n":min([r["n"] for r in a],default=None),
                "max_n":max([r["n"] for r in a],default=None),
                "ct":qhi([r["c"] for r in a],.95) if a else None,
                "pt":qhi([r["p"] for r in a],.95) if a else None}
    null={h:{i:{"n":0,"ca":0,"pa":0} for i in range(4)} for h in H}
    for x in scan(con,rel,v,t,"test"):
        seen["test"]+=1
        for h in H:
            e=errors(x,h,al[h])
            if e is None:continue
            _,c,p=paths(e); i=bidx(len(e),cal[h]["edges"]); th=cal[h]["bins"][str(i)]
            if th["ct"] is None:continue
            a=null[h][i]; a["n"]+=1
            a["ca"]+=int(float(c.max(initial=0))>th["ct"])
            a["pa"]+=int(float(p.max(initial=0))>th["pt"])
    syn={h:{str(d):{i:{"n":0,"cd":0,"pd":0,"cp":0,"pp":0,"cdelay":[],"pdelay":[]} for i in range(4)} for d in SHIFTS} for h in H}
    for x in scan(con,rel,v,t,"test"):
        for h in H:
            e=errors(x,h,al[h])
            if e is None or len(e)<MIN_SYN:continue
            i=bidx(len(e),cal[h]["edges"]); th=cal[h]["bins"][str(i)]
            if th["ct"] is None:continue
            cp_full=BASE_N+max(3,(len(e)-BASE_N)//2)
            if len(e)-cp_full<15:continue
            sd,_,_=paths(e); cp_mon=cp_full-BASE_N
            for d in SHIFTS:
                changed=e.copy(); changed[cp_full:]+=d*sd
                _,c,p=paths(changed)
                cfirst=np.flatnonzero(c>th["ct"]); pfirst=np.flatnonzero(p>th["pt"])
                a=syn[h][str(d)][i]; a["n"]+=1
                cpre=bool(len(cfirst) and cfirst[0]<cp_mon)
                ppre=bool(len(pfirst) and pfirst[0]<cp_mon)
                a["cp"]+=int(cpre); a["pp"]+=int(ppre)
                if len(cfirst) and cfirst[0]>=cp_mon:
                    a["cd"]+=1; a["cdelay"].append(int(cfirst[0]-cp_mon)*20)
                if len(pfirst) and pfirst[0]>=cp_mon:
                    a["pd"]+=1; a["pdelay"].append(int(pfirst[0]-cp_mon)*20)
    out={"dataset":"PM100 v1","input_sha256":sha(INPUT),"baseline_v2_sha256":sha(BASE),
         "target":"job-level aggregate node power, not GPU-only",
         "split":"chronological 70/85% start_time; validation defines bins and thresholds; test is held out",
         "ewma_alpha_frozen":{str(h*20):al[h] for h in H},
         "protocol":{"duration_bins":"four validation forecast-count quartiles, separately by horizon",
             "threshold":"95th percentile of validation per-job maxima within each duration bin",
             "cusum_k":K,"page_hinkley_delta":DELTA,"initial_errors":BASE_N,
             "synthetic_step":"persistent +delta*initial reference SD at midpoint of monitored tail",
             "synthetic_deltas_sd":list(SHIFTS),"minimum_natural_forecasts":MIN_N,"minimum_synthetic_forecasts":MIN_SYN},
         "jobs_seen":seen,"horizons":{}}
    md=["# PM100 — calibração por duração e mudanças sintéticas (V1)","",
        "**Status:** experimento controlado; as mudanças injetadas são artificiais, não transições físicas observadas.","",
        "## Protocolo","",
        "Em cada horizonte, os quatro grupos de duração são definidos pelos quartis do número de previsões na validação. O limiar de cada detector é o percentil 95 dos máximos por job dentro de cada grupo. Grupos e limiares são congelados antes do teste.",
        "No teste, também são injetados aumentos persistentes de +0,5, +1 e +2 desvios-padrão da referência inicial, na metade da sequência monitorada. Medimos detecção depois da mudança, alertas antes dela e atraso. Isso testa a mecânica do detector, não mudanças reais.",
        f"Jobs vistos: validação {seen['validation']:,}; teste {seen['test']:,}.",""]
    for h in H:
        sec=h*20; ce=cal[h]; hr={"duration_bin_edges_forecast_count":ce["edges"],"bins":{}}
        md += [f"## Horizonte {sec} s","",f"Quartis de duração (previsões): {ce['edges']}","","| Grupo | Val jobs | Test jobs | Alertas CUSUM | Alertas PH |","|---|---:|---:|---:|---:|"]
        for i in range(4):
            th=ce["bins"][str(i)]; a=null[h][i]; n=a["n"]
            cr=a["ca"]/n if n else None; pr=a["pa"]/n if n else None
            hr["bins"][str(i)]={"validation_calibration":th,"test_n":n,"cusum_alerts":a["ca"],"page_hinkley_alerts":a["pa"],"cusum_alert_fraction":cr,"page_hinkley_alert_fraction":pr}
            md.append(f"| Q{i+1} ({th['min_n']}–{th['max_n']}) | {th['n_val']} | {n} | {cr:.1%} | {pr:.1%} |" if n else f"| Q{i+1} | {th['n_val']} | 0 | n/a | n/a |")
        hr["synthetic"]={}
        md += ["","**Perturbações sintéticas**","","| Aumento | Jobs | Detect CUSUM | Detect PH | Pré-alerta CUSUM | Pré-alerta PH | Atraso CUSUM | Atraso PH |","|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for d in SHIFTS:
            total={k:0 for k in ("n","cd","pd","cp","pp")}; cd=[]; pd=[]; by={}
            for i in range(4):
                a=syn[h][str(d)][i]
                for k in total:total[k]+=a[k]
                cd+=a["cdelay"]; pd+=a["pdelay"]
                n=a["n"]
                by[str(i)]={"n":n,"cusum_detection":a["cd"]/n if n else None,"page_hinkley_detection":a["pd"]/n if n else None,
                    "cusum_prealert":a["cp"]/n if n else None,"page_hinkley_prealert":a["pp"]/n if n else None,
                    "cusum_delay_s":float(np.median(a["cdelay"])) if a["cdelay"] else None,
                    "page_hinkley_delay_s":float(np.median(a["pdelay"])) if a["pdelay"] else None}
            n=total["n"]; cdel=float(np.median(cd)) if cd else None; pdel=float(np.median(pd)) if pd else None
            hr["synthetic"][str(d)]={"n":n,"cusum_detection":total["cd"]/n if n else None,"page_hinkley_detection":total["pd"]/n if n else None,
                "cusum_prealert":total["cp"]/n if n else None,"page_hinkley_prealert":total["pp"]/n if n else None,
                "cusum_median_delay_s":cdel,"page_hinkley_median_delay_s":pdel,"by_duration_bin":by}
            md.append(f"| +{d} SD | {n} | {total['cd']/n:.1%} | {total['pd']/n:.1%} | {total['cp']/n:.1%} | {total['pp']/n:.1%} | {cdel if cdel is not None else 'n/a'} | {pdel if pdel is not None else 'n/a'} |" if n else f"| +{d} SD | 0 | n/a | n/a | n/a | n/a | n/a | n/a |")
        out["horizons"][str(sec)]=hr; md.append("")
    out["limitations"]=[
        "Synthetic shifts are added to absolute forecast-error series, not raw power traces; they assess detector mechanics only.",
        "Only persistent upward steps are tested; decreases, variance shifts, gradual drifts, and other patterns are not covered.",
        "Duration quartiles may not remove all duration dependence; inspect alert rates by bin.",
        "Natural alerts have no independent changepoint labels and cannot be called true or false positives.",
        "Only one chronological split and a short test window; temporal generalization is unproven.",
        "The first five realized errors may be unstable; PM100 target is aggregate node power, not GPU-only power.",
        "This experiment does not validate ATOCIA or ATRP-1."
    ]
    md += ["## Limitações",""]+["- "+x for x in out["limitations"]]
    md += ["","## Interpretação","",
        "A calibração por duração é promissora apenas se as taxas de alerta natural ficarem mais estáveis entre grupos e a detecção sintética permanecer útil. Detecção de perturbações artificiais não prova detecção de mudanças reais.",
        "","## Artefatos","","- duration_calibration_synthetic_v1.py","- audit/duration_calibration_synthetic_v1.json","- PM100_DURATION_CALIBRATION_SYNTHETIC_V1.md",
        "","Dados originais, V2, ATRP-1 e relatórios anteriores não foram alterados.","","**Fase encerrada; aguardar autorização antes da próxima.**"]
    OUT.write_text(json.dumps(out,indent=2),encoding="utf-8")
    REPORT.write_text("\n".join(md)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2)); print(f"Wrote {OUT}"); print(f"Wrote {REPORT}")

if __name__=="__main__":main()
