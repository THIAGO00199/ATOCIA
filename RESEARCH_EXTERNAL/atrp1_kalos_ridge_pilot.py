#!/usr/bin/env python3
"""Exploratory chronological ATRP-1 residual-Ridge pilot on AcmeTrace/Kalos.

Target: per-GPU power 15 seconds ahead.
Inputs: current and two previous 15-second observations of power, GPU temp,
and GPU utilization. No windows are bridged and no device IDs are model inputs.
Train: Aug 17 + Aug 22 windows. Validation: Aug 26. Test: Aug 29.
"""
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
OUT = PILOT / "atrp1_ridge_power_15s_v1.json"
RNG_SEED = 20261122
ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0)


def main() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    window_info = sorted(
        report["windows"].items(),
        key=lambda kv: datetime.fromisoformat(kv[1]["first_timestamp"]),
    )
    if len(window_info) != 4:
        raise RuntimeError("Expected exactly four windows")

    gpu_map: dict[str, int] = {}
    host_map: dict[str, int] = {}
    gpu_hosts: list[int] = []
    gpu_indices: list[int] = []
    ts_maps: list[dict[str, int]] = []
    arrays = []

    for _, info in window_info:
        first = datetime.fromisoformat(info["first_timestamp"])
        n = info["common_timestamps"]
        times = [
            (first.timestamp() + 15 * i)
            for i in range(n)
        ]
        ts_maps.append({})
        # Map ISO timestamps after parsing rows; each window is a short,
        # gap-free 15s sequence based on audited exact timestamp intersections.
        arrays.append(np.full((n, 2344, 3), np.nan, dtype=np.float32))

    with gzip.open(PANEL, "rt", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            w = int(row["window_id"]) - 1
            if w < 0 or w >= 4:
                raise RuntimeError("Unexpected window_id")
            gid = row["gpu_id_hash"]
            hid = row["host_id_hash"]
            if gid not in gpu_map:
                gpu_map[gid] = len(gpu_map)
                gpu_hosts.append(-1)
                gpu_indices.append(int(row["gpu_index"]))
            gi = gpu_map[gid]
            if hid not in host_map:
                host_map[hid] = len(host_map)
            hi = host_map[hid]
            if gpu_hosts[gi] not in (-1, hi):
                raise RuntimeError("GPU-to-host mapping changed")
            gpu_hosts[gi] = hi

            first = datetime.fromisoformat(window_info[w][1]["first_timestamp"])
            ts = datetime.fromisoformat(row["timestamp"])
            delta = (ts - first).total_seconds()
            ti = int(round(delta / 15))
            if abs(delta - 15 * ti) > 0.01 or not 0 <= ti < arrays[w].shape[0]:
                raise RuntimeError(f"Timestamp outside audited window: {row['timestamp']}")
            values = (
                float(row["power_w"]),
                float(row["gpu_temp_c"]),
                float(row["gpu_util_pct"]),
            )
            arrays[w][ti, gi, :] = values

    if len(gpu_map) != 2344 or len(host_map) != 293:
        raise RuntimeError(f"Unexpected entity counts: {len(gpu_map)} GPUs, {len(host_map)} hosts")
    if any(x < 0 for x in gpu_hosts):
        raise RuntimeError("Missing GPU host mapping")

    feature_windows = []
    for w, arr in enumerate(arrays):
        xs, ys, p_now, gpu_ids, host_ids = [], [], [], [], []
        # t is the most recent observed sample; target is t+1 (15 seconds).
        # Use three historical observations, all inside this same contiguous window.
        for t in range(2, arr.shape[0] - 1):
            hist = arr[t - 2 : t + 1]  # [t-2, t-1, t]
            target_power = arr[t + 1, :, 0]
            mask = np.isfinite(hist).all(axis=(0, 2)) & np.isfinite(target_power)
            if not np.any(mask):
                continue
            p2, p1, p0 = hist[:, mask, 0]
            temp2, temp1, temp0 = hist[:, mask, 1]
            util2, util1, util0 = hist[:, mask, 2]
            features = np.column_stack((
                p0, p1, p2,
                p0 - p1, p1 - p2,
                temp0, temp1, temp2, temp0 - temp1,
                util0, util1, util2, util0 - util1,
            )).astype(np.float64, copy=False)
            xs.append(features)
            ys.append(target_power[mask].astype(np.float64, copy=False))
            p_now.append(p0.astype(np.float64, copy=False))
            idx = np.flatnonzero(mask)
            gpu_ids.append(idx)
            host_ids.append(np.asarray(gpu_hosts, dtype=np.int32)[idx])
        if not xs:
            raise RuntimeError(f"No forecast samples in window {w+1}")
        feature_windows.append({
            "X": np.concatenate(xs),
            "y": np.concatenate(ys),
            "p_now": np.concatenate(p_now),
            "gpu": np.concatenate(gpu_ids),
            "host": np.concatenate(host_ids),
            "rows": sum(len(x) for x in ys),
        })

    train = {
        key: np.concatenate([feature_windows[0][key], feature_windows[1][key]])
        for key in ("X", "y", "p_now", "gpu", "host")
    }
    val = feature_windows[2]
    test = feature_windows[3]

    def baseline_predictions(d: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
        x = d["X"]
        p0, p1, p2 = x[:, 0], x[:, 1], x[:, 2]
        ewma05 = 0.5 * p0 + 0.5 * (0.5 * p1 + 0.5 * p2)
        ewma03 = 0.3 * p0 + 0.7 * (0.3 * p1 + 0.7 * p2)
        return {
            "persistence": p0,
            "moving_average_3": (p0 + p1 + p2) / 3.0,
            "ewma_alpha_0_5": ewma05,
            "ewma_alpha_0_3": ewma03,
        }

    def metrics(y: np.ndarray, pred: np.ndarray, gpu: np.ndarray, host: np.ndarray):
        err = np.abs(y - pred)
        gpu_mae = np.bincount(gpu, weights=err) / np.maximum(
            1, np.bincount(gpu)
        )
        host_mae = np.bincount(host, weights=err) / np.maximum(
            1, np.bincount(host)
        )
        active_gpu = np.bincount(gpu) > 0
        active_host = np.bincount(host) > 0
        return {
            "micro_mae_w": float(np.mean(err)),
            "micro_rmse_w": float(np.sqrt(np.mean((y - pred) ** 2))),
            "macro_gpu_mae_w": float(np.mean(gpu_mae[active_gpu])),
            "macro_host_mae_w": float(np.mean(host_mae[active_host])),
            "gpu_entities_evaluated": int(np.sum(active_gpu)),
            "host_entities_evaluated": int(np.sum(active_host)),
            "n_forecasts": int(len(y)),
            "host_mae": host_mae,
            "active_host": active_host,
        }

    val_baselines = baseline_predictions(val)
    val_baseline_metrics = {
        name: metrics(val["y"], pred, val["gpu"], val["host"])
        for name, pred in val_baselines.items()
    }
    selected_baseline = min(
        val_baseline_metrics,
        key=lambda name: val_baseline_metrics[name]["macro_host_mae_w"],
    )

    # Standardize features using training only. Fit Ridge to the residual
    # (future power - persistence) so the prediction is baseline + correction.
    mu = train["X"].mean(axis=0)
    sd = train["X"].std(axis=0)
    sd[sd < 1e-9] = 1.0
    xtr = (train["X"] - mu) / sd
    xva = (val["X"] - mu) / sd
    residual_tr = train["y"] - train["p_now"]
    x_mean = xtr.mean(axis=0)
    y_mean = residual_tr.mean()
    xc = xtr - x_mean
    yc = residual_tr - y_mean
    gram = xc.T @ xc
    rhs = xc.T @ yc

    ridge_models = {}
    for alpha in ALPHAS:
        coef = np.linalg.solve(gram + alpha * np.eye(gram.shape[0]), rhs)
        intercept = y_mean - x_mean @ coef
        residual_pred = xva @ coef + intercept
        pred = val["p_now"] + residual_pred
        ridge_models[str(alpha)] = {
            "coef": coef,
            "intercept": intercept,
            "validation": metrics(val["y"], pred, val["gpu"], val["host"]),
        }
    selected_alpha = min(
        ridge_models,
        key=lambda a: ridge_models[a]["validation"]["macro_host_mae_w"],
    )
    chosen = ridge_models[selected_alpha]
    xte = (test["X"] - mu) / sd
    ridge_test_pred = test["p_now"] + xte @ chosen["coef"] + chosen["intercept"]

    test_base = baseline_predictions(test)
    test_base_pred = test_base[selected_baseline]
    base_metrics = metrics(test["y"], test_base_pred, test["gpu"], test["host"])
    ridge_metrics = metrics(test["y"], ridge_test_pred, test["gpu"], test["host"])

    # Paired host-level bootstrap; hosts, not millions of correlated rows,
    # are the resampling unit. Difference > 0 favors Ridge.
    delta = (
        base_metrics["host_mae"][base_metrics["active_host"]]
        - ridge_metrics["host_mae"][ridge_metrics["active_host"]]
    )
    rng = np.random.default_rng(RNG_SEED)
    draws = rng.integers(0, len(delta), size=(2000, len(delta)))
    boot = delta[draws].mean(axis=1)
    ci = np.quantile(boot, [0.025, 0.975]).tolist()

    def clean_metric(m):
        return {k: v for k, v in m.items() if k not in ("host_mae", "active_host")}

    result = {
        "experiment": "ATRP-1 pilot: per-GPU 15-second-ahead power forecasting",
        "dataset": "AcmeTrace/Kalos",
        "target": "power_w at t+15s",
        "inputs": [
            "power at t, t-15s, t-30s",
            "GPU temperature at t, t-15s, t-30s",
            "GPU utilization at t, t-15s, t-30s",
            "one-step differences for power, temperature, utilization",
        ],
        "model": "Ridge residual correction over persistence",
        "features": 13,
        "split": {
            "train": [
                window_info[0][1]["first_timestamp"],
                window_info[1][1]["first_timestamp"],
            ],
            "validation": window_info[2][1]["first_timestamp"],
            "test": window_info[3][1]["first_timestamp"],
            "chronological": True,
            "test_used_for_selection": False,
            "windows_are_disjoint_and_never_bridged": True,
        },
        "samples_by_window": [
            {
                "window": i + 1,
                "samples": int(w["rows"]),
                "unique_gpus": int(len(np.unique(w["gpu"]))),
                "unique_hosts": int(len(np.unique(w["host"]))),
            }
            for i, w in enumerate(feature_windows)
        ],
        "train_samples": int(len(train["y"])),
        "validation_samples": int(len(val["y"])),
        "test_samples": int(len(test["y"])),
        "validation_baseline_selection": {
            "selected": selected_baseline,
            "metrics": {
                name: clean_metric(m)
                for name, m in val_baseline_metrics.items()
            },
        },
        "ridge_regularization_selection": {
            "selected_alpha": float(selected_alpha),
            "validation_metrics_by_alpha": {
                a: clean_metric(v["validation"]) for a, v in ridge_models.items()
            },
        },
        "untouched_test": {
            "selected_baseline": {
                "name": selected_baseline,
                "metrics": clean_metric(base_metrics),
            },
            "ridge_residual": {
                "alpha": float(selected_alpha),
                "metrics": clean_metric(ridge_metrics),
            },
            "skill_vs_selected_baseline": {
                key: float(1 - ridge_metrics[key] / base_metrics[key])
                for key in ("micro_mae_w", "macro_gpu_mae_w", "macro_host_mae_w")
            },
            "host_bootstrap_ci_95_for_host_macro_mae_improvement_w": ci,
            "bootstrap_hosts": int(len(delta)),
            "bootstrap_replicates": 2000,
            "bootstrap_seed": RNG_SEED,
        },
        "limits": [
            "Exploratory pilot only: four short, separated time windows, not full-period coverage.",
            "15-second sampling cannot validate sub-second dynamics.",
            "Test period is one future sampled window; generalization over all six months is not established.",
            "No hyperparameter or feature choices used the test window.",
            "Ridge is a first learnable baseline, not evidence of model novelty or commercial readiness.",
            "Metrics describe only this extracted panel and exact evaluation mask.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
