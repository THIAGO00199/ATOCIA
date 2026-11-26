#!/usr/bin/env python3
"""ATRP-1 temporal re-evaluation on eight sparse AcmeTrace/Kalos windows.

Train: windows 1-6 (Aug 17, 22, 25, 26, 27, 28)
Validation: window 7 (Aug 29)
Final held-out test: window 8 (Aug 30)

The 13-feature Huber Ridge contains no interaction terms. Hyperparameters and
baseline are selected on Aug 29 only. Aug 30 is not read for model selection.
All windows remain separate; no lag is constructed across gaps.
"""
from __future__ import annotations

import csv
import gzip
import json
import hashlib
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
PILOT = ROOT / "ACMETRACE_KALOS_PILOT"
PANEL = PILOT / "kalos_gpu_panel_8windows_v2.csv.gz"
REPORT = PILOT / "kalos_gpu_panel_8windows_v2_report.json"
OUT = PILOT / "atrp1_huber_13f_train6_val29_test30_v1.json"
MODEL_OUT = PILOT / "atrp1_huber_13f_train6_val29_test30_v1_model.npz"
ALPHAS = (10.0, 100.0, 1000.0)
SEED = 20261122
N_BOOT = 2000


def load_windows():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    ordered = sorted(
        report["windows"].items(),
        key=lambda kv: datetime.fromisoformat(kv[1]["first_timestamp"]),
    )
    arrays = [
        np.full((info["common_timestamps"], 2344, 3), np.nan, dtype=np.float32)
        for _, info in ordered
    ]
    gpu_map: dict[str, int] = {}
    host_map: dict[str, int] = {}
    gpu_hosts: list[int] = []

    with gzip.open(PANEL, "rt", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            w = int(row["window_id"]) - 1
            if not 0 <= w < len(arrays):
                raise RuntimeError(f"Unexpected window_id={w+1}")
            gid, hid = row["gpu_id_hash"], row["host_id_hash"]
            if gid not in gpu_map:
                gpu_map[gid] = len(gpu_map)
                gpu_hosts.append(-1)
            gi = gpu_map[gid]
            if hid not in host_map:
                host_map[hid] = len(host_map)
            hi = host_map[hid]
            if gpu_hosts[gi] not in (-1, hi):
                raise RuntimeError("GPU-to-host mapping is inconsistent")
            gpu_hosts[gi] = hi

            first = datetime.fromisoformat(ordered[w][1]["first_timestamp"])
            ts = datetime.fromisoformat(row["timestamp"])
            steps = (ts - first).total_seconds() / 15.0
            ti = int(round(steps))
            if abs(steps - ti) > 1e-6 or not 0 <= ti < arrays[w].shape[0]:
                raise RuntimeError("Unexpected timestamp alignment")
            vals = np.asarray(
                [float(row["power_w"]), float(row["gpu_temp_c"]), float(row["gpu_util_pct"])],
                dtype=np.float32,
            )
            if np.isfinite(arrays[w][ti, gi]).any():
                raise RuntimeError("Duplicate GPU/timestamp row")
            arrays[w][ti, gi] = vals

    if len(gpu_map) != 2344 or len(host_map) != 293 or any(x < 0 for x in gpu_hosts):
        raise RuntimeError("Unexpected GPU/host identity counts")
    gpu_hosts_arr = np.asarray(gpu_hosts, dtype=np.int32)

    windows = []
    for wi, arr in enumerate(arrays):
        out = {k: [] for k in ("X", "y", "p", "gpu", "host")}
        for t in range(2, arr.shape[0] - 1):
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
            out["X"].append(X)
            out["y"].append(target[mask])
            out["p"].append(p0)
            out["gpu"].append(ids)
            out["host"].append(gpu_hosts_arr[ids])
        if not out["X"]:
            raise RuntimeError(f"Window {wi+1} produced no forecast samples")
        windows.append({
            k: np.concatenate(v) for k, v in out.items()
        })
    return ordered, windows, len(gpu_map), len(host_map)


def baseline_predictions(d):
    x = d["X"]
    p0, p1, p2 = x[:, 0], x[:, 1], x[:, 2]
    return {
        "persistence": p0,
        "moving_average_3": (p0 + p1 + p2) / 3.0,
        "ewma_alpha_0_5": 0.5 * p0 + 0.5 * (0.5 * p1 + 0.5 * p2),
        "ewma_alpha_0_3": 0.3 * p0 + 0.7 * (0.3 * p1 + 0.7 * p2),
    }


def score(d, pred, keep_host_mae=False):
    err = d["y"] - pred
    ae = np.abs(err)
    gpu_count = np.bincount(d["gpu"])
    gpu_sum = np.bincount(d["gpu"], weights=ae)
    host_count = np.bincount(d["host"])
    host_sum = np.bincount(d["host"], weights=ae)
    gm, hm = gpu_count > 0, host_count > 0
    result = {
        "n_forecasts": int(len(err)),
        "gpu_entities": int(gm.sum()),
        "host_entities": int(hm.sum()),
        "micro_mae_w": float(ae.mean()),
        "micro_rmse_w": float(np.sqrt(np.mean(err * err))),
        "macro_gpu_mae_w": float(np.mean(gpu_sum[gm] / gpu_count[gm])),
        "macro_host_mae_w": float(np.mean(host_sum[hm] / host_count[hm])),
        "prediction_min_w": float(np.min(pred)),
        "prediction_max_w": float(np.max(pred)),
    }
    if keep_host_mae:
        result["_host_mae"] = host_sum[hm] / host_count[hm]
    return result


def fit_huber(ztr, residual, alpha, delta, penalty):
    weights = np.ones(len(residual), dtype=np.float64)
    beta = np.zeros(ztr.shape[1], dtype=np.float64)
    for _ in range(5):
        zw = ztr * weights[:, None]
        lhs = ztr.T @ zw + alpha * penalty
        rhs = ztr.T @ (weights * residual)
        beta = np.linalg.solve(lhs, rhs)
        err = residual - ztr @ beta
        abs_err = np.abs(err)
        weights = np.ones_like(abs_err)
        mask = abs_err > delta
        weights[mask] = delta / abs_err[mask]
    return beta


def main():
    ordered, windows, gpu_count, host_count = load_windows()
    train_parts = windows[:6]
    val, test = windows[6], windows[7]
    train = {
        k: np.concatenate([w[k] for w in train_parts])
        for k in ("X", "y", "p", "gpu", "host")
    }

    # Train-only feature standardization.
    mu = train["X"].mean(axis=0)
    sd = train["X"].std(axis=0)
    sd[sd < 1e-9] = 1.0
    xtr = (train["X"] - mu) / sd
    xva = (val["X"] - mu) / sd
    xte = (test["X"] - mu) / sd
    ztr = np.column_stack((np.ones(len(xtr)), xtr))
    zva = np.column_stack((np.ones(len(xva)), xva))
    zte = np.column_stack((np.ones(len(xte)), xte))

    residual = train["y"] - train["p"]
    center = np.median(residual)
    q75 = float(np.quantile(np.abs(residual - center), 0.75))
    if q75 > 1e-9:
        scale = q75 / 1.150349380376008
    else:
        positive = np.abs(residual - center)
        positive = positive[positive > 1e-9]
        scale = float(np.median(positive) * 1.4826) if len(positive) else float(np.std(residual))
    if not np.isfinite(scale) or scale <= 0:
        raise RuntimeError("Invalid robust residual scale")
    delta = 1.345 * scale
    penalty = np.diag(np.r_[0.0, np.ones(xtr.shape[1])])

    # Select alpha on Aug 29 validation only.
    model_by_alpha = {}
    for alpha in ALPHAS:
        beta = fit_huber(ztr, residual, alpha, delta, penalty)
        pred_val = val["p"] + zva @ beta
        model_by_alpha[str(alpha)] = {
            "beta": beta,
            "metrics": score(val, pred_val),
        }
    chosen_alpha = min(
        model_by_alpha,
        key=lambda a: model_by_alpha[a]["metrics"]["macro_host_mae_w"],
    )
    beta = model_by_alpha[chosen_alpha]["beta"]

    # Choose the classical baseline on Aug 29 validation only.
    val_baselines = baseline_predictions(val)
    chosen_baseline = min(
        val_baselines,
        key=lambda name: score(val, val_baselines[name])["macro_host_mae_w"],
    )
    test_baselines = baseline_predictions(test)

    # Aug 30 samples are not scored or used until model and baseline selection finish.
    pred_test = test["p"] + zte @ beta
    base_test = test_baselines[chosen_baseline]
    model_m = score(test, pred_test, keep_host_mae=True)
    base_m = score(test, base_test, keep_host_mae=True)
    host_diff = base_m["_host_mae"] - model_m["_host_mae"]
    rng = np.random.default_rng(SEED)
    boot_idx = rng.integers(0, len(host_diff), size=(N_BOOT, len(host_diff)))
    boot = host_diff[boot_idx].mean(axis=1)
    ci = np.quantile(boot, [0.025, 0.975]).tolist()
    host_improvement_summary = {
        "hosts_improved": int(np.sum(host_diff > 0)),
        "hosts_equal": int(np.sum(host_diff == 0)),
        "hosts_worse": int(np.sum(host_diff < 0)),
        "median_improvement_w": float(np.median(host_diff)),
        "p05_improvement_w": float(np.quantile(host_diff, 0.05)),
        "p95_improvement_w": float(np.quantile(host_diff, 0.95)),
    }

    # Persist the deployable linear inference parameters and train-only scaler.
    feature_names = np.asarray([
        "power_t", "power_t_minus_15s", "power_t_minus_30s",
        "power_delta_t", "power_delta_previous",
        "temperature_t", "temperature_t_minus_15s", "temperature_t_minus_30s",
        "temperature_delta_t",
        "utilization_t", "utilization_t_minus_15s", "utilization_t_minus_30s",
        "utilization_delta_t",
    ])
    np.savez_compressed(
        MODEL_OUT, beta=beta, feature_mean=mu, feature_scale=sd,
        alpha=np.asarray(float(chosen_alpha)), huber_delta=np.asarray(float(delta)),
        feature_names=feature_names,
        baseline_name=np.asarray(chosen_baseline),
        target=np.asarray("DCGM per-GPU power at t+15s (W)"),
    )
    model_sha256 = hashlib.sha256(MODEL_OUT.read_bytes()).hexdigest()
    panel_sha256 = hashlib.sha256(PANEL.read_bytes()).hexdigest()

    # Pre-specified diagnostic subgroups from observed utilization at time t.
    util_t = test["X"][:, 9]
    subgroup = {}
    for name, mask in (
        ("util_0_10", util_t < 10),
        ("util_10_50", (util_t >= 10) & (util_t < 50)),
        ("util_50_90", (util_t >= 50) & (util_t < 90)),
        ("util_90_100", util_t >= 90),
    ):
        if np.any(mask):
            e_base = test["y"][mask] - base_test[mask]
            e_model = test["y"][mask] - pred_test[mask]
            subgroup[name] = {
                "n": int(mask.sum()),
                "baseline_mae_w": float(np.mean(np.abs(e_base))),
                "model_mae_w": float(np.mean(np.abs(e_model))),
                "baseline_rmse_w": float(np.sqrt(np.mean(e_base * e_base))),
                "model_rmse_w": float(np.sqrt(np.mean(e_model * e_model))),
            }

    results = {
        "experiment": "ATRP-1 Huber Ridge 13-feature chronological re-evaluation",
        "source": {
            "dataset": "AcmeTrace / Kalos",
            "revision": "a484f7763a7812fc72eb49b8ba865b12fe7638e1",
            "sampling_interval_seconds": 15,
            "target": "DCGM per-GPU power at t+15s (W)",
            "units": {
                "POWER_USAGE": "DCGM_FI_DEV_POWER_USAGE, W",
                "GPU_TEMP": "DCGM_FI_DEV_GPU_TEMP, degrees C",
                "GPU_UTIL": "DCGM_FI_DEV_GPU_UTIL, percent",
            },
        },
        "split": {
            "train_windows": [ordered[i][1]["first_timestamp"] for i in range(6)],
            "validation_window": ordered[6][1]["first_timestamp"],
            "final_test_window": ordered[7][1]["first_timestamp"],
            "chronological": True,
            "windows_never_bridged": True,
            "test_used_for_selection": False,
            "same_kalos_cluster_and_repeated_gpu_entities": True,
        },
        "samples": {
            "train": int(len(train["y"])),
            "validation": int(len(val["y"])),
            "test": int(len(test["y"])),
            "gpu_entities_total": gpu_count,
            "host_entities_total": host_count,
            "per_window_forecasts": [int(len(w["y"])) for w in windows],
        },
        "features": [
            "power_t", "power_t_minus_15s", "power_t_minus_30s",
            "power_delta_t", "power_delta_previous",
            "temperature_t", "temperature_t_minus_15s", "temperature_t_minus_30s",
            "temperature_delta_t",
            "utilization_t", "utilization_t_minus_15s", "utilization_t_minus_30s",
            "utilization_delta_t",
        ],
        "model": {
            "type": "Huber IRLS residual correction over persistence",
            "interaction_features": False,
            "alpha_candidates": list(ALPHAS),
            "selected_alpha": float(chosen_alpha),
            "huber_delta": float(delta),
            "validation_metrics_by_alpha": {
                a: model_by_alpha[a]["metrics"] for a in model_by_alpha
            },
            "selected_baseline_on_validation": chosen_baseline,
            "validation_baseline_metrics": {
                name: score(val, pred) for name, pred in val_baselines.items()
            },
        },
        "artifacts": {
            "model_parameters_npz": str(MODEL_OUT),
            "model_parameters_sha256": model_sha256,
            "combined_panel_sha256": panel_sha256,
        },
        "final_test": {
            "model_metrics": {k: v for k, v in model_m.items() if not k.startswith("_")},
            "baseline_name": chosen_baseline,
            "baseline_metrics": {k: v for k, v in base_m.items() if not k.startswith("_")},
            "skill_vs_baseline": {
                key: float(1.0 - model_m[key] / base_m[key])
                for key in ("micro_mae_w", "micro_rmse_w", "macro_gpu_mae_w", "macro_host_mae_w")
            },
            "host_paired_bootstrap": {
                "replicates": N_BOOT,
                "seed": SEED,
                "mean_host_mae_improvement_w": float(np.mean(host_diff)),
                "ci_95_w": [float(ci[0]), float(ci[1])],
                "host_improvement_distribution": host_improvement_summary,
                "interpretation": "positive values favor the model; resampling unit is host",
            },
            "subgroups_by_current_gpu_utilization": subgroup,
        },
        "limitations": [
            "The eight windows are short, sparse snapshots; not representative continuous six-month coverage.",
            "All evaluation is within Kalos; this tests later-time generalization on a repeated cluster, not unseen GPU models or clusters.",
            "Forecast horizon is 15 seconds only; no sub-second transients evaluated.",
            "Aug 29 has become validation/development data; Aug 30 is the new held-out date.",
            "Forecast improvement does not demonstrate energy savings or safe control.",
            "The original first Ridge model failed on MAE; the 16-feature interaction ablation showed no interaction benefit.",
            "Host bootstrap on one sampled date does not remove temporal dependence or prove broad external validity.",
        ],
    }
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nWrote {OUT}")
    print(f"Wrote {MODEL_OUT}")


if __name__ == "__main__":
    main()
