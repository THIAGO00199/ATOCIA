#!/usr/bin/env python3
"""Robust Ridge/interaction follow-up to the first Kalos ATRP-1 pilot."""
from __future__ import annotations

import csv
import gzip
import json
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
PILOT = ROOT / "ACMETRACE_KALOS_PILOT"
PANEL = PILOT / "kalos_gpu_panel_4windows_v1.csv.gz"
REPORT = PILOT / "kalos_gpu_panel_4windows_v1_report.json"
OUT = PILOT / "atrp1_huber_interaction_power_15s_v1.json"
ALPHAS = (10.0, 100.0, 1000.0)


def main():
    rep = json.loads(REPORT.read_text(encoding="utf-8"))
    wins = sorted(rep["windows"].items(), key=lambda kv: datetime.fromisoformat(kv[1]["first_timestamp"]))
    arrays = []
    gpu_map, host_map = {}, {}
    gpu_hosts = []
    for _, info in wins:
        arrays.append(np.full((info["common_timestamps"], 2344, 3), np.nan, dtype=np.float32))

    with gzip.open(PANEL, "rt", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            w = int(row["window_id"]) - 1
            gid, hid = row["gpu_id_hash"], row["host_id_hash"]
            if gid not in gpu_map:
                gpu_map[gid] = len(gpu_map)
                gpu_hosts.append(-1)
            gi = gpu_map[gid]
            if hid not in host_map:
                host_map[hid] = len(host_map)
            hi = host_map[hid]
            if gpu_hosts[gi] not in (-1, hi):
                raise RuntimeError("GPU host map is inconsistent")
            gpu_hosts[gi] = hi
            first = datetime.fromisoformat(wins[w][1]["first_timestamp"])
            ts = datetime.fromisoformat(row["timestamp"])
            steps = (ts - first).total_seconds() / 15
            ti = int(round(steps))
            if abs(steps - ti) > 1e-6:
                raise RuntimeError("Unexpected time interval")
            arrays[w][ti, gi] = (
                float(row["power_w"]), float(row["gpu_temp_c"]), float(row["gpu_util_pct"])
            )
    if len(gpu_map) != 2344 or len(host_map) != 293:
        raise RuntimeError("Entity count changed")
    gpu_hosts = np.asarray(gpu_hosts, dtype=np.int32)

    windows = []
    for wi, arr in enumerate(arrays):
        out = {k: [] for k in ("X", "y", "p", "gpu", "host")}
        for t in range(2, arr.shape[0] - 1):
            h = arr[t-2:t+1]
            target = arr[t+1, :, 0]
            mask = np.isfinite(h).all(axis=(0,2)) & np.isfinite(target)
            if not np.any(mask):
                continue
            p2,p1,p0 = h[:,mask,0]
            t2,t1,t0 = h[:,mask,1]
            u2,u1,u0 = h[:,mask,2]
            X = np.column_stack((
                p0,p1,p2,p0-p1,p1-p2,
                t0,t1,t2,t0-t1,
                u0,u1,u2,u0-u1,
                p0*u0/100.0,
                p0*(t0-40.0)/40.0,
                u0*t0/100.0,
            ))
            out["X"].append(X)
            out["y"].append(target[mask])
            out["p"].append(p0)
            ids = np.flatnonzero(mask)
            out["gpu"].append(ids)
            out["host"].append(gpu_hosts[ids])
        windows.append({
            k: np.concatenate(v) for k,v in out.items()
        })

    def baseline(d):
        x = d["X"]
        p0,p1,p2 = x[:,0],x[:,1],x[:,2]
        return {
            "persistence": p0,
            "ma3": (p0+p1+p2)/3,
            "ewma05": .5*p0+.5*(.5*p1+.5*p2),
        }

    def score(d, pred):
        e = np.abs(d["y"]-pred)
        gc = np.bincount(d["gpu"], weights=e)
        gn = np.bincount(d["gpu"])
        hc = np.bincount(d["host"], weights=e)
        hn = np.bincount(d["host"])
        gm = gn>0; hm=hn>0
        return {
            "micro_mae_w": float(e.mean()),
            "micro_rmse_w": float(np.sqrt(np.mean((d["y"]-pred)**2))),
            "macro_gpu_mae_w": float(np.mean(gc[gm]/gn[gm])),
            "macro_host_mae_w": float(np.mean(hc[hm]/hn[hm])),
            "host_mae": hc[hm]/hn[hm],
        }

    train = {k:np.concatenate([windows[0][k],windows[1][k]]) for k in ("X","y","p","gpu","host")}
    val, test = windows[2], windows[3]

    # Train-only standardization
    mu = train["X"].mean(axis=0)
    sd = train["X"].std(axis=0)
    sd[sd<1e-9]=1
    xtr=(train["X"]-mu)/sd
    xva=(val["X"]-mu)/sd
    xte=(test["X"]-mu)/sd
    # Add unpenalized intercept.
    ztr=np.column_stack((np.ones(len(xtr)),xtr))
    zva=np.column_stack((np.ones(len(xva)),xva))
    zte=np.column_stack((np.ones(len(xte)),xte))
    residual=train["y"]-train["p"]
    center=np.median(residual)
    abs_dev=np.abs(residual-center)
    q75=float(np.quantile(abs_dev,0.75))
    if q75>1e-9:
        # Normal-consistent robust scale from the 75th percentile; unlike MAD,
        # this remains defined when over half of telemetry deltas are exactly 0.
        scale=q75/1.150349380376008
    else:
        positive=abs_dev[abs_dev>1e-9]
        scale=float(np.median(positive)*1.4826) if len(positive) else float(np.std(residual))
    if not np.isfinite(scale) or scale<=0:
        raise RuntimeError("Invalid robust residual scale after fallback")
    delta=1.345*scale
    reg_diag=np.diag(np.r_[0.0,np.ones(xtr.shape[1])])

    fitted={}
    for alpha in ALPHAS:
        weights=np.ones(len(residual),dtype=np.float64)
        beta=np.zeros(ztr.shape[1],dtype=np.float64)
        for _ in range(5):
            zw=ztr*weights[:,None]
            lhs=ztr.T@zw+alpha*reg_diag
            rhs=ztr.T@(weights*residual)
            beta=np.linalg.solve(lhs,rhs)
            err=residual-ztr@beta
            ae=np.abs(err)
            weights=np.ones_like(ae)
            mask=ae>delta
            weights[mask]=delta/ae[mask]
        val_pred=val["p"]+zva@beta
        fitted[str(alpha)]={"beta":beta,"validation":score(val,val_pred)}
    chosen=min(fitted,key=lambda a:fitted[a]["validation"]["macro_host_mae_w"])
    beta=fitted[chosen]["beta"]
    pred= test["p"]+zte@beta
    base_preds=baseline(test)
    val_baselines=baseline(val)
    best_base=min(val_baselines,key=lambda n:score(val,val_baselines[n])["macro_host_mae_w"])
    base_pred=base_preds[best_base]
    sm=score(test,pred); bm=score(test,base_pred)

    # Host-level paired bootstrap. Positive improvement favors robust Ridge.
    diff=bm["host_mae"]-sm["host_mae"]
    rng=np.random.default_rng(20261122)
    boot=diff[rng.integers(0,len(diff),(2000,len(diff)))].mean(axis=1)
    ci=np.quantile(boot,[.025,.975]).tolist()

    # Subgroup diagnostics by observed utilization at time t.
    u=test["X"][:,9]  # GPU utilization at t
    subgroup={}
    for name,mask in (
        ("util_0_10",u<10),
        ("util_10_50",(u>=10)&(u<50)),
        ("util_50_90",(u>=50)&(u<90)),
        ("util_90_100",u>=90),
    ):
        if not np.any(mask): continue
        subgroup[name]={
            "n":int(mask.sum()),
            "baseline_mae_w":float(np.mean(np.abs(test["y"][mask]-base_pred[mask]))),
            "huber_mae_w":float(np.mean(np.abs(test["y"][mask]-pred[mask]))),
            "baseline_rmse_w":float(np.sqrt(np.mean((test["y"][mask]-base_pred[mask])**2))),
            "huber_rmse_w":float(np.sqrt(np.mean((test["y"][mask]-pred[mask])**2))),
        }

    # Ablation: same Huber objective and selection protocol, but no interaction features.
    xtr13=(train["X"][:,:13]-mu[:13])/sd[:13]
    xva13=(val["X"][:,:13]-mu[:13])/sd[:13]
    xte13=(test["X"][:,:13]-mu[:13])/sd[:13]
    ztr13=np.column_stack((np.ones(len(xtr13)),xtr13))
    zva13=np.column_stack((np.ones(len(xva13)),xva13))
    zte13=np.column_stack((np.ones(len(xte13)),xte13))
    reg13=np.diag(np.r_[0.0,np.ones(13)])
    ablation={}
    for alpha in ALPHAS:
        weights=np.ones(len(residual),dtype=np.float64)
        beta13=np.zeros(14,dtype=np.float64)
        for _ in range(5):
            zw=ztr13*weights[:,None]
            beta13=np.linalg.solve(ztr13.T@zw+alpha*reg13,ztr13.T@(weights*residual))
            err=residual-ztr13@beta13
            ae=np.abs(err)
            weights=np.ones_like(ae)
            mask=ae>delta
            weights[mask]=delta/ae[mask]
        vp=val["p"]+zva13@beta13
        ablation[str(alpha)]={"beta":beta13,"validation":score(val,vp)}
    alpha13=min(ablation,key=lambda a:ablation[a]["validation"]["macro_host_mae_w"])
    pred13=test["p"]+zte13@ablation[alpha13]["beta"]
    score13=score(test,pred13)

    result={
        "experiment":"Robust Ridge with three interaction features",
        "target":"per-GPU power at t+15 seconds (W)",
        "train_windows":[wins[0][1]["first_timestamp"],wins[1][1]["first_timestamp"]],
        "validation_window":wins[2][1]["first_timestamp"],
        "untouched_test_window":wins[3][1]["first_timestamp"],
        "train_samples":int(len(train["y"])),
        "validation_samples":int(len(val["y"])),
        "test_samples":int(len(test["y"])),
        "feature_count":int(xtr.shape[1]),
        "extra_features":["power_t * utilization_t / 100","power_t * (temperature_t - 40) / 40","utilization_t * temperature_t / 100"],
        "loss":"Huber IRLS; scale estimated from the 75th percentile of absolute centered training residuals because more than half the deltas are exactly zero",
        "selected_alpha":float(chosen),
        "validation_model_metrics":{
            a:{k:v for k,v in d["validation"].items() if k!="host_mae"} for a,d in fitted.items()
        },
        "validation_selected_baseline":best_base,
        "ablation_without_interactions":{
            "feature_count":13,
            "selected_alpha":float(alpha13),
            "validation_metrics_by_alpha":{
                a:{k:v for k,v in d["validation"].items() if k!="host_mae"}
                for a,d in ablation.items()
            },
            "untouched_test_metrics":{k:v for k,v in score13.items() if k!="host_mae"},
            "test_skill_vs_persistence_macro_host_mae":float(1-score13["macro_host_mae_w"]/bm["macro_host_mae_w"]),
            "test_skill_vs_persistence_micro_mae":float(1-score13["micro_mae_w"]/bm["micro_mae_w"]),
        },
        "test":{
            "baseline_name":best_base,
            "baseline_metrics":{k:v for k,v in bm.items() if k!="host_mae"},
            "huber_metrics":{k:v for k,v in sm.items() if k!="host_mae"},
            "skill_vs_baseline":{
                k:float(1-sm[k]/bm[k]) for k in ("micro_mae_w","micro_rmse_w","macro_gpu_mae_w","macro_host_mae_w")
            },
            "host_bootstrap_ci_95_mae_improvement_w":ci,
            "host_count":int(len(diff)),
            "subgroups_by_current_gpu_utilization":subgroup,
        },
        "limits":[
            "Four short separated windows only; this does not establish six-month generalization.",
            "One-step horizon is 15 seconds; not a sub-second transient test.",
            "This is a follow-up experiment, not a validated product model or novelty claim.",
            "The final date window was not used for selection.",
        ],
    }
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2,ensure_ascii=False))
    print(f"\nWrote {OUT}")


if __name__=="__main__":
    main()
