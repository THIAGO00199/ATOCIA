#!/usr/bin/env python3
"""Apply a frozen ATRP-1 model to the separate Aug 31 AcmeTrace/Kalos holdout.

No fitting, calibration, feature selection, or baseline selection occurs here.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
PILOT = ROOT / "ACMETRACE_KALOS_PILOT"
PANEL = PILOT / "kalos_gpu_panel_aug31_2023_holdout_v1.csv.gz"
PANEL_REPORT = PILOT / "kalos_gpu_panel_aug31_2023_holdout_v1_report.json"
MODEL = PILOT / "atrp1_huber_13f_train6_val29_test30_v1_model.npz"
MODEL_REPORT = PILOT / "atrp1_huber_13f_train6_val29_test30_v1.json"
OUT = PILOT / "atrp1_frozen_model_aug31_holdout_eval_v1.json"
SEED = 20261122
N_BOOT = 2000


def main():
    panel_report = json.loads(PANEL_REPORT.read_text(encoding="utf-8"))
    model_report = json.loads(MODEL_REPORT.read_text(encoding="utf-8"))
    with np.load(MODEL, allow_pickle=False) as z:
        beta = z["beta"].astype(np.float64)
        mu = z["feature_mean"].astype(np.float64)
        sd = z["feature_scale"].astype(np.float64)
        alpha = float(z["alpha"])
        feature_names = z["feature_names"].tolist()
        baseline_name = str(z["baseline_name"])
    if beta.shape != (14,) or mu.shape != (13,) or sd.shape != (13,):
        raise RuntimeError("Unexpected frozen model parameter shape")
    if baseline_name != "persistence":
        raise RuntimeError("This evaluator is defined for the frozen persistence residual baseline")

    n_times = int(panel_report["common_timestamps"])
    arr = np.full((n_times, 2344, 3), np.nan, dtype=np.float32)
    gpu_map = {}
    host_map = {}
    gpu_hosts = []
    first = datetime.fromisoformat(panel_report["first_timestamp"])
    with gzip.open(PANEL, "rt", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            gid, hid = row["gpu_id_hash"], row["host_id_hash"]
            if gid not in gpu_map:
                gpu_map[gid] = len(gpu_map)
                gpu_hosts.append(-1)
            gi = gpu_map[gid]
            if hid not in host_map:
                host_map[hid] = len(host_map)
            hi = host_map[hid]
            if gpu_hosts[gi] not in (-1, hi):
                raise RuntimeError("GPU-to-host mapping changed within holdout")
            gpu_hosts[gi] = hi
            ts = datetime.fromisoformat(row["timestamp"])
            step = (ts - first).total_seconds() / 15.0
            ti = int(round(step))
            if abs(step - ti) > 1e-6 or not 0 <= ti < n_times:
                raise RuntimeError("Timestamp does not align to 15-second grid")
            if np.isfinite(arr[ti, gi]).any():
                raise RuntimeError("Duplicate GPU/time record")
            arr[ti, gi] = np.asarray(
                [float(row["power_w"]), float(row["gpu_temp_c"]), float(row["gpu_util_pct"])],
                dtype=np.float32,
            )
    gpu_hosts = np.asarray(gpu_hosts, dtype=np.int32)
    if len(gpu_map) != 2335 or len(host_map) != 292 or np.any(gpu_hosts < 0):
        raise RuntimeError("Unexpected Aug 31 GPU/host counts")

    Xs, ys, ps, gs, hs = [], [], [], [], []
    for t in range(2, n_times - 1):
        hist = arr[t - 2:t + 1]
        target = arr[t + 1, :, 0]
        mask = np.isfinite(hist).all(axis=(0, 2)) & np.isfinite(target)
        if not np.any(mask):
            continue
        p2, p1, p0 = hist[:, mask, 0]
        t2, t1, t0 = hist[:, mask, 1]
        u2, u1, u0 = hist[:, mask, 2]
        X = np.column_stack((
            p0, p1, p2, p0 - p1, p1 - p2,
            t0, t1, t2, t0 - t1,
            u0, u1, u2, u0 - u1,
        ))
        ids = np.flatnonzero(mask)
        Xs.append(X)
        ys.append(target[mask])
        ps.append(p0)
        gs.append(ids)
        hs.append(gpu_hosts[ids])
    X = np.concatenate(Xs)
    y = np.concatenate(ys)
    p = np.concatenate(ps)
    gpu = np.concatenate(gs)
    host = np.concatenate(hs)

    z = np.column_stack((np.ones(len(X)), (X - mu) / sd))
    pred = p + z @ beta
    if not np.isfinite(pred).all():
        raise RuntimeError("Non-finite model predictions")

    def metric(y_true, y_pred, groups, n_groups):
        err = y_true - y_pred
        ae = np.abs(err)
        counts = np.bincount(groups, minlength=n_groups)
        sums = np.bincount(groups, weights=ae, minlength=n_groups)
        ok = counts > 0
        return {
            "n_forecasts": int(len(err)),
            "entities": int(ok.sum()),
            "micro_mae_w": float(ae.mean()),
            "micro_rmse_w": float(np.sqrt(np.mean(err * err))),
            "macro_entity_mae_w": float(np.mean(sums[ok] / counts[ok])),
            "prediction_min_w": float(np.min(y_pred)),
            "prediction_max_w": float(np.max(y_pred)),
        }

    model_m = metric(y, pred, host, len(host_map))
    base_m = metric(y, p, host, len(host_map))
    # Also compute macro metrics per GPU.
    model_gpu = metric(y, pred, gpu, len(gpu_map))
    base_gpu = metric(y, p, gpu, len(gpu_map))

    host_abs_model = np.bincount(host, weights=np.abs(y - pred), minlength=len(host_map))
    host_abs_base = np.bincount(host, weights=np.abs(y - p), minlength=len(host_map))
    host_n = np.bincount(host, minlength=len(host_map))
    host_delta = (host_abs_base / host_n) - (host_abs_model / host_n)
    rng = np.random.default_rng(SEED)
    boot_idx = rng.integers(0, len(host_delta), size=(N_BOOT, len(host_delta)))
    boot = host_delta[boot_idx].mean(axis=1)
    ci = np.quantile(boot, [0.025, 0.975]).tolist()

    util_t = X[:, 9]
    subgroups = {}
    for name, mask in (
        ("util_0_10", util_t < 10),
        ("util_10_50", (util_t >= 10) & (util_t < 50)),
        ("util_50_90", (util_t >= 50) & (util_t < 90)),
        ("util_90_100", util_t >= 90),
    ):
        if np.any(mask):
            eb, em = y[mask] - p[mask], y[mask] - pred[mask]
            subgroups[name] = {
                "n": int(mask.sum()),
                "baseline_mae_w": float(np.mean(np.abs(eb))),
                "model_mae_w": float(np.mean(np.abs(em))),
                "baseline_rmse_w": float(np.sqrt(np.mean(eb * eb))),
                "model_rmse_w": float(np.sqrt(np.mean(em * em))),
            }

    results = {
        "experiment": "Frozen ATRP-1 application to separate Aug 31 temporal holdout",
        "model_source": str(MODEL),
        "model_alpha": alpha,
        "model_sha256": hashlib.sha256(MODEL.read_bytes()).hexdigest(),
        "panel_sha256": hashlib.sha256(PANEL.read_bytes()).hexdigest(),
        "panel_source_revision": panel_report["source_revision"],
        "panel_first_timestamp": panel_report["first_timestamp"],
        "panel_last_timestamp": panel_report["last_timestamp"],
        "panel_common_timestamps": n_times,
        "sampling_interval_seconds": 15,
        "horizon_seconds": 15,
        "fit_or_tuning_on_holdout": False,
        "baseline_name": "persistence",
        "features": feature_names,
        "samples": {
            "forecasts": int(len(y)),
            "gpu_entities": int(len(gpu_map)),
            "host_entities": int(len(host_map)),
            "forecast_timestamps": int(n_times - 3),
        },
        "model_metrics": {
            "micro_mae_w": float(np.mean(np.abs(y - pred))),
            "micro_rmse_w": float(np.sqrt(np.mean((y - pred) ** 2))),
            "macro_gpu_mae_w": model_gpu["macro_entity_mae_w"],
            "macro_host_mae_w": model_m["macro_entity_mae_w"],
            "prediction_min_w": float(pred.min()),
            "prediction_max_w": float(pred.max()),
        },
        "baseline_metrics": {
            "micro_mae_w": float(np.mean(np.abs(y - p))),
            "micro_rmse_w": float(np.sqrt(np.mean((y - p) ** 2))),
            "macro_gpu_mae_w": base_gpu["macro_entity_mae_w"],
            "macro_host_mae_w": base_m["macro_entity_mae_w"],
            "prediction_min_w": float(p.min()),
            "prediction_max_w": float(p.max()),
        },
        "skill_vs_persistence": {
            "micro_mae": float(1 - np.mean(np.abs(y - pred)) / np.mean(np.abs(y - p))),
            "micro_rmse": float(1 - np.sqrt(np.mean((y - pred) ** 2)) / np.sqrt(np.mean((y - p) ** 2))),
            "macro_gpu_mae": float(1 - model_gpu["macro_entity_mae_w"] / base_gpu["macro_entity_mae_w"]),
            "macro_host_mae": float(1 - model_m["macro_entity_mae_w"] / base_m["macro_entity_mae_w"]),
        },
        "host_paired_bootstrap": {
            "replicates": N_BOOT,
            "seed": SEED,
            "mean_host_mae_improvement_w": float(host_delta.mean()),
            "ci_95_w": [float(ci[0]), float(ci[1])],
            "hosts_improved": int(np.sum(host_delta > 0)),
            "hosts_equal": int(np.sum(host_delta == 0)),
            "hosts_worse": int(np.sum(host_delta < 0)),
            "median_improvement_w": float(np.median(host_delta)),
            "p05_improvement_w": float(np.quantile(host_delta, 0.05)),
            "p95_improvement_w": float(np.quantile(host_delta, 0.95)),
        },
        "subgroups_by_current_gpu_utilization": subgroups,
        "limitations": [
            "Single short tail window within Kalos, not an independent cluster or hardware population.",
            "Same 15-second cadence and forecast horizon as training; no sub-second test.",
            "This is a later date and a different time of day, but not a full-day evaluation.",
            "No parameter fitting, calibration, or threshold choice was made on this holdout.",
            "Forecasting improvement does not imply energy savings or operational control benefit.",
        ],
    }
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
