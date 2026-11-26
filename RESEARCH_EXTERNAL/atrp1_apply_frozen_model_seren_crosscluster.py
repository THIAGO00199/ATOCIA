#!/usr/bin/env python3
"""Apply the frozen Kalos ATRP-1 model to the separate Seren cluster holdout."""
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
PANEL = PILOT / "seren_gpu_panel_aug18_2023_crosscluster_v1.csv.gz"
PANEL_REPORT = PILOT / "seren_gpu_panel_aug18_2023_crosscluster_v1_report.json"
MODEL = PILOT / "atrp1_huber_13f_train6_val29_test30_v1_model.npz"
OUT = PILOT / "atrp1_frozen_kalos_model_on_seren_crosscluster_eval_v1.json"
SEED = 20261122
N_BOOT = 2000


def main():
    panel_report = json.loads(PANEL_REPORT.read_text(encoding="utf-8"))
    with np.load(MODEL, allow_pickle=False) as z:
        beta = z["beta"].astype(np.float64)
        mu = z["feature_mean"].astype(np.float64)
        sd = z["feature_scale"].astype(np.float64)
        alpha = float(z["alpha"])
        delta = float(z["huber_delta"])
        feature_names = z["feature_names"].tolist()
        baseline_name = str(z["baseline_name"])
    if beta.shape != (14,) or mu.shape != (13,) or sd.shape != (13,):
        raise RuntimeError("Unexpected model parameter shape")
    if baseline_name != "persistence":
        raise RuntimeError("Unexpected frozen baseline")

    n_times = int(panel_report["common_timestamps"])
    n_gpu_columns = int(panel_report["gpu_columns_in_source"])
    arr = np.full((n_times, n_gpu_columns, 3), np.nan, dtype=np.float32)
    gpu_map, host_map = {}, {}
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
                raise RuntimeError("GPU-to-host mapping changed")
            gpu_hosts[gi] = hi
            ts = datetime.fromisoformat(row["timestamp"])
            step = (ts - first).total_seconds() / 15.0
            ti = int(round(step))
            if abs(step - ti) > 1e-6 or not 0 <= ti < n_times:
                raise RuntimeError("Timestamp alignment error")
            if np.isfinite(arr[ti, gi]).any():
                raise RuntimeError("Duplicate GPU/timestamp record")
            arr[ti, gi] = np.asarray(
                [float(row["power_w"]), float(row["gpu_temp_c"]), float(row["gpu_util_pct"])],
                dtype=np.float32,
            )
    gpu_hosts = np.asarray(gpu_hosts, dtype=np.int32)
    if len(gpu_map) != panel_report["gpu_entities_with_data"]:
        raise RuntimeError("GPU entity count does not match extraction report")
    if len(host_map) != panel_report["unique_hosts_with_data"] or np.any(gpu_hosts < 0):
        raise RuntimeError("Host entity count or GPU mapping mismatch")

    Xs, ys, ps, gs, hs = [], [], [], [], []
    for t in range(2, n_times - 1):
        history = arr[t - 2:t + 1]
        target = arr[t + 1, :, 0]
        mask = np.isfinite(history).all(axis=(0, 2)) & np.isfinite(target)
        if not np.any(mask):
            continue
        p2, p1, p0 = history[:, mask, 0]
        t2, t1, t0 = history[:, mask, 1]
        u2, u1, u0 = history[:, mask, 2]
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

    standardized = (X - mu) / sd
    z = np.column_stack((np.ones(len(X)), standardized))
    pred = p + z @ beta
    if not np.isfinite(pred).all():
        raise RuntimeError("Non-finite forecasts")

    def grouped_mae(y_true, y_pred, groups, n_groups):
        ae = np.abs(y_true - y_pred)
        counts = np.bincount(groups, minlength=n_groups)
        sums = np.bincount(groups, weights=ae, minlength=n_groups)
        ok = counts > 0
        return float(np.mean(sums[ok] / counts[ok]))

    e_model = y - pred
    e_base = y - p
    host_model = grouped_mae(y, pred, host, len(host_map))
    host_base = grouped_mae(y, p, host, len(host_map))
    gpu_model = grouped_mae(y, pred, gpu, len(gpu_map))
    gpu_base = grouped_mae(y, p, gpu, len(gpu_map))

    host_n = np.bincount(host, minlength=len(host_map))
    host_abs_model = np.bincount(host, weights=np.abs(e_model), minlength=len(host_map))
    host_abs_base = np.bincount(host, weights=np.abs(e_base), minlength=len(host_map))
    host_delta = host_abs_base / host_n - host_abs_model / host_n
    rng = np.random.default_rng(SEED)
    boot_i = rng.integers(0, len(host_delta), size=(N_BOOT, len(host_delta)))
    boot = host_delta[boot_i].mean(axis=1)
    ci = np.quantile(boot, [0.025, 0.975]).tolist()

    subgroups = {}
    util_t = X[:, 9]
    for name, mask in (
        ("util_0_10", util_t < 10),
        ("util_10_50", (util_t >= 10) & (util_t < 50)),
        ("util_50_90", (util_t >= 50) & (util_t < 90)),
        ("util_90_100", util_t >= 90),
    ):
        if np.any(mask):
            eb, em = e_base[mask], e_model[mask]
            subgroups[name] = {
                "n": int(mask.sum()),
                "baseline_mae_w": float(np.mean(np.abs(eb))),
                "model_mae_w": float(np.mean(np.abs(em))),
                "baseline_rmse_w": float(np.sqrt(np.mean(eb * eb))),
                "model_rmse_w": float(np.sqrt(np.mean(em * em))),
            }

    shift = {}
    for j, name in enumerate(feature_names):
        zcol = standardized[:, j]
        shift[name] = {
            "z_mean": float(zcol.mean()),
            "z_std": float(zcol.std()),
            "fraction_abs_z_gt_3": float(np.mean(np.abs(zcol) > 3)),
            "abs_z_p95": float(np.quantile(np.abs(zcol), 0.95)),
        }

    results = {
        "experiment": "Frozen Kalos-trained ATRP-1 applied to Seren, cross-cluster",
        "model_source": str(MODEL),
        "model_alpha": alpha,
        "huber_delta_from_train": delta,
        "model_sha256": hashlib.sha256(MODEL.read_bytes()).hexdigest(),
        "panel_sha256": hashlib.sha256(PANEL.read_bytes()).hexdigest(),
        "source_revision": panel_report["source_revision"],
        "cluster": "Seren",
        "window": {
            "first_timestamp": panel_report["first_timestamp"],
            "last_timestamp": panel_report["last_timestamp"],
            "common_timestamps": n_times,
            "sampling_interval_seconds": 15,
            "horizon_seconds": 15,
        },
        "fit_or_tuning_on_seren": False,
        "baseline": "persistence",
        "samples": {
            "forecast_count": int(len(y)),
            "gpu_entities_with_forecasts": int(len(np.unique(gpu))),
            "host_entities_with_forecasts": int(len(np.unique(host))),
            "forecast_timestamps": n_times - 3,
        },
        "target_distribution": {
            "min_w": float(y.min()),
            "max_w": float(y.max()),
            "mean_w": float(y.mean()),
            "std_w": float(y.std()),
        },
        "model_metrics": {
            "micro_mae_w": float(np.mean(np.abs(e_model))),
            "micro_rmse_w": float(np.sqrt(np.mean(e_model * e_model))),
            "macro_gpu_mae_w": gpu_model,
            "macro_host_mae_w": host_model,
            "prediction_min_w": float(pred.min()),
            "prediction_max_w": float(pred.max()),
            "fraction_negative_predictions": float(np.mean(pred < 0)),
        },
        "baseline_metrics": {
            "micro_mae_w": float(np.mean(np.abs(e_base))),
            "micro_rmse_w": float(np.sqrt(np.mean(e_base * e_base))),
            "macro_gpu_mae_w": gpu_base,
            "macro_host_mae_w": host_base,
        },
        "skill_vs_persistence": {
            "micro_mae": float(1 - np.mean(np.abs(e_model)) / np.mean(np.abs(e_base))),
            "micro_rmse": float(1 - np.sqrt(np.mean(e_model * e_model)) / np.sqrt(np.mean(e_base * e_base))),
            "macro_gpu_mae": float(1 - gpu_model / gpu_base),
            "macro_host_mae": float(1 - host_model / host_base),
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
        "feature_shift_vs_kalos_training_scaler": shift,
        "limitations": [
            "One short window from the separate Seren cluster; not a second organization or dataset.",
            "The date is 2023-08-18 and does not follow the Kalos training calendar chronologically; this is a spatial transfer test, not a later-time test.",
            "No model fitting, calibration, threshold choice, or feature selection was performed on Seren.",
            "Potential hardware heterogeneity is not yet fully verified from cluster_summary metadata.",
            "One window does not characterize the entire Seren cluster or all GPU types.",
        ],
    }
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
