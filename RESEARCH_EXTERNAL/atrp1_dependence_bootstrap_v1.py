#!/usr/bin/env python3
"""Dependence-aware uncertainty analysis for frozen ATRP-1 holdouts.

Read-only: loads the existing AcmeTrace panels and frozen NPZ, prints JSON,
and does not fit a model or write/overwrite evaluation artifacts.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
from datetime import datetime
from pathlib import Path

import numpy as np

PILOT = Path(__file__).resolve().parent / "ACMETRACE_KALOS_PILOT"
MODEL = PILOT / "atrp1_huber_13f_train6_val29_test30_v1_model.npz"
SEED = 20261122
REPLICATES = 3000
BLOCK_LENGTHS = (2, 4, 8, 16)  # 30 s, 60 s, 120 s, 240 s


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_panel(panel_name: str, report_name: str, beta, mu, sd, window_id=None):
    report = json.loads((PILOT / report_name).read_text(encoding="utf-8"))
    if window_id is not None:
        ordered = sorted(
            report["windows"].items(),
            key=lambda kv: datetime.fromisoformat(kv[1]["first_timestamp"]),
        )
        info = ordered[window_id - 1][1]
        n_times = int(info["common_timestamps"])
        first = datetime.fromisoformat(info["first_timestamp"])
    else:
        n_times = int(report["common_timestamps"])
        first = datetime.fromisoformat(report["first_timestamp"])

    panel = PILOT / panel_name
    gpu_map, host_map, gpu_hosts = {}, {}, []
    rows = []
    with gzip.open(panel, "rt", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if window_id is not None and int(row["window_id"]) != window_id:
                continue
            gid, hid = row["gpu_id_hash"], row["host_id_hash"]
            if gid not in gpu_map:
                gpu_map[gid] = len(gpu_map)
                gpu_hosts.append(-1)
            gi = gpu_map[gid]
            if hid not in host_map:
                host_map[hid] = len(host_map)
            hi = host_map[hid]
            if gpu_hosts[gi] not in (-1, hi):
                raise RuntimeError("GPU-to-host mapping mismatch")
            gpu_hosts[gi] = hi

            timestamp = datetime.fromisoformat(row["timestamp"])
            step = (timestamp - first).total_seconds() / 15.0
            ti = int(round(step))
            if abs(step - ti) > 1e-6 or not 0 <= ti < n_times:
                raise RuntimeError("Timestamp does not align to the 15-second grid")
            rows.append((
                ti, gi, float(row["power_w"]),
                float(row["gpu_temp_c"]), float(row["gpu_util_pct"])
            ))

    arr = np.full((n_times, len(gpu_map), 3), np.nan, dtype=np.float32)
    for ti, gi, power, temp, util in rows:
        if np.isfinite(arr[ti, gi]).any():
            raise RuntimeError("Duplicate GPU/timestamp observation")
        arr[ti, gi] = (power, temp, util)

    gpu_hosts = np.asarray(gpu_hosts, dtype=np.int32)
    if np.any(gpu_hosts < 0):
        raise RuntimeError("GPU host mapping is incomplete")
    return arr, gpu_hosts, len(host_map), report


def timestamp_acf(values, lag):
    if len(values) <= lag:
        return None
    a, b = values[:-lag], values[lag:]
    if np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def evaluate(label, panel_name, report_name, beta, mu, sd, window_id=None):
    arr, gpu_hosts, n_hosts, panel_report = load_panel(
        panel_name, report_name, beta, mu, sd, window_id
    )
    n_times, n_gpus, _ = arr.shape
    n_forecast_slots = n_times - 3
    sum_base = np.zeros((n_forecast_slots, n_hosts), dtype=np.float64)
    sum_model = np.zeros_like(sum_base)
    counts = np.zeros_like(sum_base)

    timestamp_base_mae, timestamp_model_mae = [], []
    for out_t, t in enumerate(range(2, n_times - 1)):
        history = arr[t - 2:t + 1]
        target = arr[t + 1, :, 0]
        mask = np.isfinite(history).all(axis=(0, 2)) & np.isfinite(target)
        if not np.any(mask):
            continue

        p2, p1, p0 = history[:, mask, 0]
        t2, t1, t0 = history[:, mask, 1]
        u2, u1, u0 = history[:, mask, 2]
        features = np.column_stack((
            p0, p1, p2, p0 - p1, p1 - p2,
            t0, t1, t2, t0 - t1,
            u0, u1, u2, u0 - u1,
        ))
        design = np.column_stack((
            np.ones(len(features)), (features - mu) / sd
        ))
        prediction = p0 + design @ beta
        y = target[mask]
        host_ids = gpu_hosts[np.flatnonzero(mask)]
        abs_base = np.abs(y - p0)
        abs_model = np.abs(y - prediction)

        sum_base[out_t] = np.bincount(
            host_ids, weights=abs_base, minlength=n_hosts
        )
        sum_model[out_t] = np.bincount(
            host_ids, weights=abs_model, minlength=n_hosts
        )
        counts[out_t] = np.bincount(host_ids, minlength=n_hosts)
        timestamp_base_mae.append(float(abs_base.mean()))
        timestamp_model_mae.append(float(abs_model.mean()))

    valid_hosts = counts.sum(axis=0) > 0
    baseline_mae = float(sum_base.sum() / counts.sum())
    model_mae = float(sum_model.sum() / counts.sum())
    host_delta = (
        sum_base.sum(axis=0)[valid_hosts] / counts.sum(axis=0)[valid_hosts]
        - sum_model.sum(axis=0)[valid_hosts] / counts.sum(axis=0)[valid_hosts]
    )

    # Comparator: host-only paired bootstrap, same estimand as original reports.
    rng = np.random.default_rng(SEED)
    host_idx = rng.integers(0, len(host_delta), size=(REPLICATES, len(host_delta)))
    host_boot = host_delta[host_idx].mean(axis=1)

    # Descriptive autocorrelation of the synchronized timestamp-level MAE delta.
    time_delta = np.asarray(timestamp_base_mae) - np.asarray(timestamp_model_mae)
    acf = {str(lag): timestamp_acf(time_delta, lag) for lag in (1, 2, 4, 8)}

    # Two-way product-weight bootstrap:
    # (1) synchronized circular moving blocks of timestamps, applied to all hosts;
    # (2) host-cluster resampling with replacement, independent of time blocks.
    n_t, n_h = sum_base.shape
    block_results = {}
    for block_length in BLOCK_LENGTHS:
        rng = np.random.default_rng(SEED + block_length)
        boot_macro = np.empty(REPLICATES)
        boot_micro = np.empty(REPLICATES)
        boot_skill = np.empty(REPLICATES)
        n_blocks = (n_t + block_length - 1) // block_length

        for r in range(REPLICATES):
            starts = rng.integers(0, n_t, size=n_blocks)
            sampled_times = np.concatenate([
                (start + np.arange(block_length)) % n_t for start in starts
            ])[:n_t]
            time_weights = np.bincount(
                sampled_times, minlength=n_t
            ).astype(np.float64)

            sampled_hosts = rng.integers(0, n_h, size=n_h)
            host_weights = np.bincount(
                sampled_hosts, minlength=n_h
            ).astype(np.float64)

            base_by_host = time_weights @ sum_base
            model_by_host = time_weights @ sum_model
            count_by_host = time_weights @ counts
            has_data = count_by_host > 0
            per_host_delta = (
                base_by_host[has_data] - model_by_host[has_data]
            ) / count_by_host[has_data]
            boot_macro[r] = (
                per_host_delta @ host_weights[has_data]
            ) / host_weights[has_data].sum()

            total_base = float(base_by_host @ host_weights)
            total_model = float(model_by_host @ host_weights)
            total_count = float(count_by_host @ host_weights)
            boot_micro[r] = (total_base - total_model) / total_count
            boot_skill[r] = 1.0 - total_model / total_base

        block_results[str(block_length)] = {
            "block_seconds": block_length * 15,
            "macro_host_delta_ci95_w": np.quantile(
                boot_macro, [0.025, 0.975]
            ).tolist(),
            "micro_delta_ci95_w": np.quantile(
                boot_micro, [0.025, 0.975]
            ).tolist(),
            "micro_skill_ci95_pct": (
                100 * np.quantile(boot_skill, [0.025, 0.975])
            ).tolist(),
        }

    return {
        "label": label,
        "forecasts": int(counts.sum()),
        "forecast_timestamps": int(np.count_nonzero(counts.sum(axis=1))),
        "gpus": int(n_gpus),
        "hosts": int(valid_hosts.sum()),
        "baseline_micro_mae_w": baseline_mae,
        "model_micro_mae_w": model_mae,
        "micro_mae_improvement_w": baseline_mae - model_mae,
        "micro_mae_skill_pct": 100 * (baseline_mae - model_mae) / baseline_mae,
        "macro_host_mean_improvement_w": float(host_delta.mean()),
        "host_only_bootstrap_ci95_w": np.quantile(
            host_boot, [0.025, 0.975]
        ).tolist(),
        "timestamp_mean_delta_acf": acf,
        "two_way_circular_block_bootstrap": block_results,
        "panel_sha256": sha256(PILOT / panel_name),
        "panel_source_revision": panel_report.get(
            "source_revision", panel_report.get("source_revision")
        ),
    }


def main():
    with np.load(MODEL, allow_pickle=False) as z:
        beta = z["beta"].astype(np.float64)
        mu = z["feature_mean"].astype(np.float64)
        sd = z["feature_scale"].astype(np.float64)
        alpha = float(z["alpha"])
        baseline = str(z["baseline_name"])

    if beta.shape != (14,) or mu.shape != (13,) or sd.shape != (13,):
        raise RuntimeError("Unexpected frozen model parameter shapes")
    if baseline != "persistence":
        raise RuntimeError("This script expects the frozen persistence baseline")

    results = {
        "model": {
            "sha256": sha256(MODEL),
            "alpha": alpha,
            "baseline": baseline,
            "fit_or_tuning_performed": False,
        },
        "bootstrap": {
            "replicates_per_block_length": REPLICATES,
            "seed": SEED,
            "block_lengths_seconds": [15 * x for x in BLOCK_LENGTHS],
            "time_blocks": "circular moving blocks synchronized across all hosts",
            "host_resampling": "cluster bootstrap with replacement",
        },
        "evaluations": [
            evaluate(
                "Kalos 2023-08-30 temporal holdout",
                "kalos_gpu_panel_8windows_v2.csv.gz",
                "kalos_gpu_panel_8windows_v2_report.json",
                beta, mu, sd, window_id=8,
            ),
            evaluate(
                "Kalos 2023-08-31 temporal holdout",
                "kalos_gpu_panel_aug31_2023_holdout_v1.csv.gz",
                "kalos_gpu_panel_aug31_2023_holdout_v1_report.json",
                beta, mu, sd,
            ),
            evaluate(
                "Seren 2023-08-18 cross-cluster holdout",
                "seren_gpu_panel_aug18_2023_crosscluster_v1.csv.gz",
                "seren_gpu_panel_aug18_2023_crosscluster_v1_report.json",
                beta, mu, sd,
            ),
        ],
    }
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
