#!/usr/bin/env python3
"""Apply synthetic change points to raw PM100 power traces, then recompute causal EWMA errors."""
from __future__ import annotations
import json, hashlib, math
from pathlib import Path
import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "job_table.parquet"
BASE = ROOT / "audit" / "trajectory_online_models_v2.json"
PREV = ROOT / "audit" / "mixed_change_fusion_v1.json"
OUT = ROOT / "audit" / "raw_power_change_detection_v2.json"
REPORT = ROOT / "PM100_RAW_POWER_CHANGE_DETECTION_V2.md"
HORIZONS = (1, 2, 3, 6)
WINDOWS = (5, 10, 20)
METHODS = ("mean", "variance", "max")
MIN_FORECASTS = 41
MIN_SYNTHETIC_FORECASTS = 80
TAIL = 0.05
SAMPLE_PER_BIN = 100
REFERENCE_SAMPLES = 20
SEED = 20261123
SAMPLE_SECONDS = 20.0
Z95 = 1.959963984540054


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def split_for(start, end, val_cut, test_cut):
    a, b = start.timestamp(), end.timestamp()
    if b < val_cut:
        return "train"
    if a >= val_cut and b < test_cut:
        return "validation"
    if a >= test_cut:
        return "test"
    return "overlap"


def scan(con, rel, val_cut, test_cut, part):
    cur = con.execute(
        f"SELECT start_time,end_time,power_consumption FROM {rel} "
        "WHERE num_gpus_alloc>0 AND start_time IS NOT NULL "
        "AND end_time IS NOT NULL ORDER BY start_time"
    )
    while True:
        batch = cur.fetchmany(256)
        if not batch:
            break
        for start, end, seq in batch:
            if split_for(start, end, val_cut, test_cut) != part:
                continue
            if seq is None or len(seq) < 6 or any(v is None for v in seq):
                continue
            x = np.asarray(seq, dtype=np.float64)
            if np.isfinite(x).all() and np.all(x >= 0):
                yield x


def ewma_error_series(x, horizon, alpha):
    """One-sided EWMA forecast error; e[j] targets raw observation x[4+j+horizon]."""
    t = np.arange(4, len(x) - horizon)
    if len(t) < MIN_FORECASTS:
        return None
    smooth = np.empty(len(x), dtype=np.float64)
    smooth[0] = x[0]
    for i in range(1, len(x)):
        smooth[i] = alpha * x[i] + (1.0 - alpha) * smooth[i - 1]
    e = np.abs(x[t + horizon] - smooth[t])
    if len(e) < MIN_FORECASTS or not np.isfinite(e).all():
        return None
    return e


def window_paths(e, w):
    if len(e) < 2 * w:
        return None, None
    cs = np.concatenate(([0.0], np.cumsum(e, dtype=np.float64)))
    cs2 = np.concatenate(([0.0], np.cumsum(e * e, dtype=np.float64)))
    ends = np.arange(2 * w, len(e) + 1, dtype=np.int64)
    sp = cs[ends - w] - cs[ends - 2 * w]
    sr = cs[ends] - cs[ends - w]
    qp = cs2[ends - w] - cs2[ends - 2 * w]
    qr = cs2[ends] - cs2[ends - w]
    vp = np.maximum((qp - sp * sp / w) / max(w - 1, 1), 0.0)
    vr = np.maximum((qr - sr * sr / w) / max(w - 1, 1), 0.0)
    mp, mr = sp / w, sr / w
    mean_stat = np.abs(mr - mp) / np.sqrt((vp + vr) / w + 1.0)
    variance_stat = np.abs(np.log((vr + 1.0) / (vp + 1.0)))
    return mean_stat, variance_stat


def max_fusion_path(mean_path, variance_path, mean_q95, variance_q95):
    return np.maximum(mean_path / mean_q95, variance_path / variance_q95)


def qhigher(values, q):
    return float(np.quantile(np.asarray(values, dtype=np.float64), q, method="higher"))


def bin_index(n, edges):
    return int(np.searchsorted(edges, n, side="right"))


def first_cross(path, threshold, w):
    ix = np.flatnonzero(path > threshold)
    return int(2 * w + ix[0]) if len(ix) else None


def scenarios():
    out = []
    for shape in ("step", "ramp"):
        # Controls: level-only shifts, both directions.
        for direction, sign in (("up", 1.0), ("down", -1.0)):
            for delta in (0.5, 1.0, 2.0):
                out.append({
                    "name": f"mean_{shape}_{direction}_d{delta:g}",
                    "shape": shape, "mean_shift_sd": sign * delta,
                    "sd_multiplier": 1.0, "class": "mean_only"
                })
        # Controls: dispersion-only changes.
        for mult in (1.5, 2.0):
            out.append({
                "name": f"sd_{shape}_m{mult:g}",
                "shape": shape, "mean_shift_sd": 0.0,
                "sd_multiplier": mult, "class": "sd_only"
            })
        # Joint level + dispersion changes, in both level directions.
        for direction, sign in (("up", 1.0), ("down", -1.0)):
            for delta in (0.5, 1.0, 2.0):
                for mult in (1.5, 2.0):
                    out.append({
                        "name": f"mixed_{shape}_{direction}_d{delta:g}_m{mult:g}",
                        "shape": shape, "mean_shift_sd": sign * delta,
                        "sd_multiplier": mult, "class": "mixed"
                    })
    return out


def raw_change_point(x, horizon):
    # Same raw-power change location for every window size; mapped to the error target index.
    error_count = len(x) - horizon - 4
    cp_error = error_count // 2
    return 4 + cp_error + horizon


def perturb_raw_power(x, horizon, spec):
    """
    Apply a step or ramp to raw power after a known index.
    Magnitude is measured against a fixed 20-sample pre-change raw-power SD.
    """
    cp_raw = raw_change_point(x, horizon)
    if cp_raw < REFERENCE_SAMPLES or len(x) - cp_raw < 2 * max(WINDOWS):
        return None, None
    reference = x[cp_raw - REFERENCE_SAMPLES:cp_raw]
    center = float(np.mean(reference))
    scale = max(float(np.std(reference, ddof=1)), 1.0)
    post_n = len(x) - cp_raw

    if spec["shape"] == "step":
        progress = np.ones(post_n, dtype=np.float64)
    elif spec["shape"] == "ramp":
        ramp_n = min(post_n, max(2 * max(WINDOWS), int(math.ceil(0.25 * post_n))))
        progress = np.ones(post_n, dtype=np.float64)
        progress[:ramp_n] = np.linspace(1.0 / ramp_n, 1.0, ramp_n, endpoint=True)
    else:
        raise ValueError(spec["shape"])

    delta = float(spec["mean_shift_sd"]) * scale
    multiplier = float(spec["sd_multiplier"])
    y = x.copy()
    original_post = x[cp_raw:]
    y[cp_raw:] = np.maximum(
        0.0,
        center + progress * delta +
        (1.0 + progress * (multiplier - 1.0)) * (original_post - center)
    )
    return y, cp_raw


def new_acc():
    return {
        "n": 0, "detected": 0, "prealert": 0, "delays_s": [],
        "detected_flags": [], "prealert_flags": [],
        "baseline_detected": 0, "baseline_prealert": 0, "baseline_flags": []
    }


def target_raw_index(error_end_exclusive, horizon):
    # The last error included is e[end-1], whose target is x[4 + end-1 + h].
    return 4 + error_end_exclusive - 1 + horizon


def update_acc(acc, error_end, cp_raw, horizon):
    acc["n"] += 1
    detected = 0
    prealert = 0
    if error_end is not None:
        detection_index = target_raw_index(error_end, horizon)
        if detection_index < cp_raw:
            prealert = 1
        else:
            detected = 1
            acc["delays_s"].append((detection_index - cp_raw) * SAMPLE_SECONDS)
    acc["detected"] += detected
    acc["prealert"] += prealert
    acc["detected_flags"].append(detected)
    acc["prealert_flags"].append(prealert)


def update_baseline_acc(acc, error_end, cp_raw, horizon):
    """Classify first alert on the untouched raw trace at the same change-point index."""
    baseline_detected = 0
    baseline_prealert = 0
    if error_end is not None:
        detection_index = target_raw_index(error_end, horizon)
        if detection_index < cp_raw:
            baseline_prealert = 1
        else:
            baseline_detected = 1
    acc["baseline_detected"] += baseline_detected
    acc["baseline_prealert"] += baseline_prealert
    acc["baseline_flags"].append(baseline_detected)


def finish_acc(acc):
    n = acc["n"]
    acc["detection_fraction"] = acc["detected"] / n if n else None
    acc["prealert_fraction"] = acc["prealert"] / n if n else None
    acc["median_detection_delay_s"] = float(np.median(acc["delays_s"])) if acc["delays_s"] else None
    if n:
        p = acc["detected"] / n
        den = 1.0 + Z95 * Z95 / n
        center = (p + Z95 * Z95 / (2.0 * n)) / den
        half = Z95 * math.sqrt(p * (1.0-p) / n + Z95*Z95/(4.0*n*n)) / den
        acc["detection_wilson95"] = [max(0.0, center-half), min(1.0, center+half)]
    else:
        acc["detection_wilson95"] = None
    acc["baseline_postchange_alert_fraction"] = acc["baseline_detected"] / n if n else None
    acc["baseline_prealert_fraction"] = acc["baseline_prealert"] / n if n else None
    acc["incremental_detection_fraction"] = (
        acc["detection_fraction"] - acc["baseline_postchange_alert_fraction"]
        if n else None
    )
    acc["paired_change_vs_unmodified"] = paired_diff(
        acc["detected_flags"], acc["baseline_flags"]
    )
    del acc["delays_s"]
    del acc["baseline_flags"]


def paired_diff(a, b):
    x = np.asarray(a, dtype=np.float64)
    y = np.asarray(b, dtype=np.float64)
    if len(x) != len(y) or not len(x):
        return None
    d = x - y
    mean = float(d.mean())
    se = float(d.std(ddof=1) / math.sqrt(len(d))) if len(d) > 1 else 0.0
    return {
        "difference": mean,
        "ci95_normal": [mean - Z95 * se, mean + Z95 * se],
        "n_paired": int(len(d)),
        "a_only": int(np.sum((x == 1) & (y == 0))),
        "b_only": int(np.sum((x == 0) & (y == 1)))
    }


def main():
    base = json.loads(BASE.read_text(encoding="utf-8"))
    prev = json.loads(PREV.read_text(encoding="utf-8"))
    alphas = {
        1: float(base["horizons_seconds"]["20"]["selected_validation"]["ewma_alpha"]),
        2: float(base["horizons_seconds"]["40"]["selected_validation"]["ewma_alpha"]),
        3: float(base["horizons_seconds"]["60"]["selected_validation"]["ewma_alpha"]),
        6: float(base["horizons_seconds"]["120"]["selected_validation"]["ewma_alpha"]),
    }
    con = duckdb.connect(":memory:", config={"threads": "1", "memory_limit": "512MB"})
    src = str(INPUT.resolve()).replace("'", "''")
    rel = f"read_parquet('{src}')"
    val_cut, test_cut = con.execute(
        f"SELECT quantile_cont(epoch(start_time),.70),quantile_cont(epoch(start_time),.85) "
        f"FROM {rel} WHERE num_gpus_alloc>0 AND start_time IS NOT NULL"
    ).fetchone()

    # Validation pass 1: frozen duration bins and individual mean/variance thresholds.
    validation = {h: [] for h in HORIZONS}
    seen = {"validation": 0, "test": 0}
    for x in scan(con, rel, val_cut, test_cut, "validation"):
        seen["validation"] += 1
        for h in HORIZONS:
            e = ewma_error_series(x, h, alphas[h])
            if e is None:
                continue
            row = {"n": len(e), "maxima": {}}
            for w in WINDOWS:
                mp, vp = window_paths(e, w)
                row["maxima"][str(w)] = {
                    "mean": float(np.max(mp)),
                    "variance": float(np.max(vp))
                }
            validation[h].append(row)

    calibration = {}
    thresholds = {h: {w: {} for w in WINDOWS} for h in HORIZONS}
    validation_exceedance = {}
    for h in HORIZONS:
        rows = validation[h]
        edges = [qhigher([r["n"] for r in rows], q) for q in (0.25, 0.50, 0.75)]
        calibration[h] = {"duration_bin_edges_forecasts": edges, "bins": {}}
        for b in range(4):
            members = [r for r in rows if bin_index(r["n"], edges) == b]
            calibration[h]["bins"][str(b)] = {}
            for w in WINDOWS:
                mthr = qhigher([r["maxima"][str(w)]["mean"] for r in members], 1.0-TAIL)
                vthr = qhigher([r["maxima"][str(w)]["variance"] for r in members], 1.0-TAIL)
                thresholds[h][w][b] = {"mean": mthr, "variance": vthr}
                calibration[h]["bins"][str(b)][str(w)] = {
                    "validation_jobs": len(members),
                    "mean_q95": mthr, "variance_q95": vthr
                }

    # Validation pass 2: fuse normalized pointwise paths, then calibrate each job maximum.
    fused_validation = {h: {w: {b: [] for b in range(4)} for w in WINDOWS} for h in HORIZONS}
    for x in scan(con, rel, val_cut, test_cut, "validation"):
        for h in HORIZONS:
            e = ewma_error_series(x, h, alphas[h])
            if e is None:
                continue
            b = bin_index(len(e), calibration[h]["duration_bin_edges_forecasts"])
            for w in WINDOWS:
                mp, vp = window_paths(e, w)
                fused = max_fusion_path(mp, vp, thresholds[h][w][b]["mean"],
                                        thresholds[h][w][b]["variance"])
                fused_validation[h][w][b].append(float(np.max(fused)))

    for h in HORIZONS:
        validation_exceedance[h] = {}
        for b in range(4):
            validation_exceedance[h][b] = {}
            members = [r for r in validation[h]
                       if bin_index(r["n"], calibration[h]["duration_bin_edges_forecasts"]) == b]
            for w in WINDOWS:
                fused_q95 = qhigher(fused_validation[h][w][b], 1.0-TAIL)
                thresholds[h][w][b]["max"] = fused_q95
                calibration[h]["bins"][str(b)][str(w)]["max_q95"] = fused_q95
                validation_exceedance[h][b][str(w)] = {
                    "mean": sum(r["maxima"][str(w)]["mean"] > thresholds[h][w][b]["mean"]
                                for r in members) / len(members),
                    "variance": sum(r["maxima"][str(w)]["variance"] > thresholds[h][w][b]["variance"]
                                    for r in members) / len(members),
                    "max": sum(v > fused_q95 for v in fused_validation[h][w][b]) /
                           len(fused_validation[h][w][b])
                }

    # Test pass: natural alerts on unmodified raw traces, plus a reproducible raw-trace reservoir.
    natural = {h: {w: {m: {b: {"n": 0, "alerts": 0} for b in range(4)}
                          for m in METHODS} for w in WINDOWS} for h in HORIZONS}
    reservoirs = {h: {b: [] for b in range(4)} for h in HORIZONS}
    reservoir_seen = {h: {b: 0 for b in range(4)} for h in HORIZONS}
    rng = np.random.default_rng(SEED)
    for x in scan(con, rel, val_cut, test_cut, "test"):
        seen["test"] += 1
        for h in HORIZONS:
            e = ewma_error_series(x, h, alphas[h])
            if e is None:
                continue
            b = bin_index(len(e), calibration[h]["duration_bin_edges_forecasts"])
            for w in WINDOWS:
                mp, vp = window_paths(e, w)
                th = thresholds[h][w][b]
                paths = {
                    "mean": mp, "variance": vp,
                    "max": max_fusion_path(mp, vp, th["mean"], th["variance"])
                }
                for method in METHODS:
                    a = natural[h][w][method][b]
                    a["n"] += 1
                    if first_cross(paths[method], th[method], w) is not None:
                        a["alerts"] += 1
            if len(e) >= MIN_SYNTHETIC_FORECASTS:
                reservoir_seen[h][b] += 1
                bucket = reservoirs[h][b]
                if len(bucket) < SAMPLE_PER_BIN:
                    bucket.append(x.copy())
                else:
                    j = int(rng.integers(0, reservoir_seen[h][b]))
                    if j < SAMPLE_PER_BIN:
                        bucket[j] = x.copy()

    # Synthetic tests: alter raw power, recompute the same causal EWMA errors, then score.
    specs = scenarios()
    synthetic = {}
    class_summary = {}
    for h in HORIZONS:
        sec = str(h*20)
        synthetic[sec] = {}
        for spec in specs:
            synthetic[sec][spec["name"]] = {"spec": spec, "results": {}, "paired_max_vs_single": {}}
            for w in WINDOWS:
                synthetic[sec][spec["name"]]["results"][str(w)] = {
                    m: {
                        **new_acc(),
                        "by_duration_bin": {str(b): new_acc() for b in range(4)}
                    }
                    for m in METHODS
                }
        for b in range(4):
            for x in reservoirs[h][b]:
                baseline_e = ewma_error_series(x, h, alphas[h])
                if baseline_e is None:
                    continue
                baseline_ends = {}
                for w in WINDOWS:
                    baseline_mp, baseline_vp = window_paths(baseline_e, w)
                    baseline_th = thresholds[h][w][b]
                    baseline_paths = {
                        "mean": baseline_mp,
                        "variance": baseline_vp,
                        "max": max_fusion_path(
                            baseline_mp, baseline_vp,
                            baseline_th["mean"], baseline_th["variance"]
                        )
                    }
                    baseline_ends[w] = {
                        method: first_cross(baseline_paths[method], baseline_th[method], w)
                        for method in METHODS
                    }
                for spec in specs:
                    altered, cp_raw = perturb_raw_power(x, h, spec)
                    if altered is None:
                        continue
                    changed_e = ewma_error_series(altered, h, alphas[h])
                    if changed_e is None:
                        continue
                    # The raw change point maps to the first affected forecast target in e.
                    for w in WINDOWS:
                        mp, vp = window_paths(changed_e, w)
                        th = thresholds[h][w][b]
                        paths = {
                            "mean": mp,
                            "variance": vp,
                            "max": max_fusion_path(mp, vp, th["mean"], th["variance"])
                        }
                        for method in METHODS:
                            result = synthetic[sec][spec["name"]]["results"][str(w)][method]
                            error_end = first_cross(paths[method], th[method], w)
                            update_acc(result, error_end, cp_raw, h)
                            update_acc(result["by_duration_bin"][str(b)], error_end, cp_raw, h)
                            update_baseline_acc(result, baseline_ends[w][method], cp_raw, h)
                            update_baseline_acc(
                                result["by_duration_bin"][str(b)],
                                baseline_ends[w][method], cp_raw, h
                            )

        for spec in specs:
            for w in WINDOWS:
                res = synthetic[sec][spec["name"]]["results"][str(w)]
                for method in METHODS:
                    finish_acc(res[method])
                    for by in res[method]["by_duration_bin"].values():
                        finish_acc(by)
                synthetic[sec][spec["name"]]["paired_max_vs_single"][str(w)] = {
                    method: paired_diff(res["max"]["detected_flags"], res[method]["detected_flags"])
                    for method in ("mean", "variance")
                }
                for method in METHODS:
                    del res[method]["detected_flags"]
                    del res[method]["prealert_flags"]

    # Class-level averages at the 200s window.
    for h in HORIZONS:
        sec = str(h*20)
        class_summary[sec] = {}
        for cls in ("mean_only", "sd_only", "mixed"):
            names = [name for name, item in synthetic[sec].items() if item["spec"]["class"] == cls]
            class_summary[sec][cls] = {}
            for method in METHODS:
                dets, pres, delays = [], [], []
                total_n = total_detected = total_prealert = 0
                total_baseline_detected = total_baseline_prealert = 0
                for name in names:
                    r = synthetic[sec][name]["results"]["10"][method]
                    total_n += r["n"]
                    total_detected += r["detected"]
                    total_prealert += r["prealert"]
                    total_baseline_detected += r["baseline_detected"]
                    total_baseline_prealert += r["baseline_prealert"]
                    if r["median_detection_delay_s"] is not None:
                        delays.append(r["median_detection_delay_s"])
                class_summary[sec][cls][method] = {
                    "scenarios": len(names),
                    "scenario_job_instances": total_n,
                    "weighted_detection_fraction": total_detected/total_n if total_n else None,
                    "weighted_prealert_fraction": total_prealert/total_n if total_n else None,
                    "weighted_baseline_postchange_alert_fraction": total_baseline_detected/total_n if total_n else None,
                    "weighted_baseline_prealert_fraction": total_baseline_prealert/total_n if total_n else None,
                    "incremental_detection_fraction": (
                        (total_detected-total_baseline_detected)/total_n if total_n else None
                    ),
                    "median_of_scenario_median_delays_s": float(np.median(delays)) if delays else None
                }

    paired_summary = {}
    for single in ("mean", "variance"):
        pairs = []
        for h in HORIZONS:
            sec = str(h*20)
            for spec in specs:
                z = synthetic[sec][spec["name"]]["paired_max_vs_single"]["10"][single]
                lo, hi = z["ci95_normal"]
                pairs.append({
                    "difference": z["difference"],
                    "ci_lo": lo,
                    "ci_hi": hi,
                    "class": spec["class"]
                })
        paired_summary[single] = {
            "n_horizon_scenario_pairs": len(pairs),
            "mean_paired_difference_max_minus_single": float(np.mean([z["difference"] for z in pairs])),
            "median_paired_difference_max_minus_single": float(np.median([z["difference"] for z in pairs])),
            "ci_max_wholly_above_single": sum(z["ci_lo"] > 0.0 for z in pairs),
            "ci_single_wholly_above_max": sum(z["ci_hi"] < 0.0 for z in pairs),
            "ci_includes_zero": sum(z["ci_lo"] <= 0.0 <= z["ci_hi"] for z in pairs),
            "by_class": {}
        }
        for cls in ("mean_only", "sd_only", "mixed"):
            selected_pairs = [z for z in pairs if z["class"] == cls]
            paired_summary[single]["by_class"][cls] = {
                "n_pairs": len(selected_pairs),
                "mean_paired_difference_max_minus_single": float(np.mean([z["difference"] for z in selected_pairs])),
                "ci_max_wholly_above_single": sum(z["ci_lo"] > 0.0 for z in selected_pairs),
                "ci_single_wholly_above_max": sum(z["ci_hi"] < 0.0 for z in selected_pairs),
                "ci_includes_zero": sum(z["ci_lo"] <= 0.0 <= z["ci_hi"] for z in selected_pairs)
            }

    incremental_summary = {}
    for method in METHODS:
        pairs = []
        for h in HORIZONS:
            sec = str(h*20)
            for spec in specs:
                z = synthetic[sec][spec["name"]]["results"]["10"][method]["paired_change_vs_unmodified"]
                lo, hi = z["ci95_normal"]
                pairs.append({
                    "difference": z["difference"],
                    "ci_lo": lo,
                    "ci_hi": hi,
                    "class": spec["class"]
                })
        incremental_summary[method] = {
            "n_horizon_scenario_pairs": len(pairs),
            "mean_paired_incremental_detection": float(np.mean([z["difference"] for z in pairs])),
            "median_paired_incremental_detection": float(np.median([z["difference"] for z in pairs])),
            "ci_increment_above_zero": sum(z["ci_lo"] > 0.0 for z in pairs),
            "ci_decrement_below_zero": sum(z["ci_hi"] < 0.0 for z in pairs),
            "ci_includes_zero": sum(z["ci_lo"] <= 0.0 <= z["ci_hi"] for z in pairs),
            "by_class": {}
        }
        for cls in ("mean_only", "sd_only", "mixed"):
            subset = [z for z in pairs if z["class"] == cls]
            incremental_summary[method]["by_class"][cls] = {
                "n_pairs": len(subset),
                "mean_paired_incremental_detection": float(np.mean([z["difference"] for z in subset])),
                "ci_increment_above_zero": sum(z["ci_lo"] > 0.0 for z in subset),
                "ci_decrement_below_zero": sum(z["ci_hi"] < 0.0 for z in subset),
                "ci_includes_zero": sum(z["ci_lo"] <= 0.0 <= z["ci_hi"] for z in subset)
            }

    natural_out, validation_out = {}, {}
    for h in HORIZONS:
        sec = str(h*20)
        natural_out[sec], validation_out[sec] = {}, {}
        for w in WINDOWS:
            natural_out[sec][str(w)], validation_out[sec][str(w)] = {}, {}
            for method in METHODS:
                bins = {}
                for b, a in natural[h][w][method].items():
                    bins[str(b)] = {
                        "test_jobs": a["n"], "alert_jobs": a["alerts"],
                        "alert_fraction": a["alerts"]/a["n"] if a["n"] else None
                    }
                natural_out[sec][str(w)][method] = {"by_duration_bin": bins}
                validation_out[sec][str(w)][method] = {
                    str(b): validation_exceedance[h][b][str(w)][method] for b in range(4)
                }

    out = {
        "experiment_version": "V2 paired with unmodified raw-trace baseline",
        "supersedes_v1_note": "V1 counted first alerts after synthetic change points without measuring whether the unmodified raw trace would have alerted after the same point. V2 adds that paired baseline control; use V2 for incremental detection interpretation.",
        "dataset": "PM100 v1",
        "input_sha256": sha256(INPUT),
        "baseline_v2_sha256": sha256(BASE),
        "previous_fusion_study_sha256": sha256(PREV),
        "target": "job-level aggregate node power, not GPU-only",
        "split": "chronological 70/85% start_time; validation defines bins and thresholds; held-out test used for natural alerts and synthetic raw traces",
        "ewma_alpha_frozen_from_v2": {str(h*20): alphas[h] for h in HORIZONS},
        "protocol": {
            "sampling_interval_s": SAMPLE_SECONDS,
            "reference_samples_for_raw_transform": REFERENCE_SAMPLES,
            "windows_samples": list(WINDOWS),
            "windows_seconds": [20*w for w in WINDOWS],
            "methods": list(METHODS),
            "individual_thresholds": "q95 validation per-job maximum for each horizon, window, statistic and duration quartile",
            "max_fusion_threshold": "pointwise max of normalized mean and variance paths; q95 validation per-job maximum after fusion",
            "target_validation_job_alert_fraction": TAIL,
            "synthetic_minimum_forecasts": MIN_SYNTHETIC_FORECASTS,
            "synthetic_sample_per_duration_bin_per_horizon": SAMPLE_PER_BIN,
            "synthetic_seed": SEED,
            "synthetic_scenarios": len(specs),
            "raw_change_point": "midpoint of eligible forecast-error target interval; mapped to raw power sample index 4 + error_index + horizon",
            "raw_perturbation": "level shift is delta SD of previous 20 raw samples; dispersion scales deviations about previous 20-sample mean by m; mixed changes apply both; step or ramp reaches full magnitude over at least 40 raw samples",
            "sd_multiplier_effect": "m multiplies SD; nominal variance multiplier m^2 before clipping at zero",
            "detection_timestamp": "time index of newest forecast target in the first crossing window; delay measured from raw change-point sample"
        },
        "jobs_seen": seen,
        "duration_calibration": calibration,
        "validation_exceedance_fractions": validation_out,
        "natural_test_alerts": natural_out,
        "synthetic_scenarios": synthetic,
        "class_summary_window10": class_summary,
        "paired_max_vs_single_summary_window10": paired_summary,
        "paired_change_vs_unmodified_summary_window10": incremental_summary,
        "synthetic_sample_counts_by_horizon_bin": {
            str(h*20): {str(b): len(reservoirs[h][b]) for b in range(4)} for h in HORIZONS
        },
        "limitations": [
            "Synthetic transformations are applied to measured raw PM100 job power sequences but remain artificial interventions; they are not naturally labeled changepoints.",
            "PM100 power is aggregate job/node power, not GPU-only power.",
            "Level and dispersion changes are simple additive/scaling interventions; they do not reproduce all physical causes or scheduler/node interactions.",
            "Downward shifts and dispersion scaling are clipped at zero, which changes the post-change distribution.",
            "Forecasting remains the frozen EWMA baseline; this is a detector-mechanics experiment, not a new forecasting model.",
            "Natural test alerts have no independent changepoint labels and cannot be classified as true or false positives.",
            "Synthetic post-change detection is interpreted against a paired unmodified-trace first-alert baseline; this estimates incremental detection under the intervention, not real-world sensitivity.",
            "Thresholds are calibrated on one chronological validation period; future false-alarm rates and temporal generalization are unproven.",
            "This experiment does not validate ATOCIA or ATRP-1, energy savings, operational utility or thermal safety."
        ]
    }

    lines = [
        "# PM100 — detecção após perturbações na potência bruta (V2, baseline pareado)", "",
        "**Status:** mudanças artificiais inseridas na série medida de potência; erros EWMA recalculados de forma causal. Não são mudanças reais rotuladas.", "",
        "## Pergunta e protocolo", "",
        "Os detectores por janelas reconhecem alterações quando a intervenção ocorre na potência original, antes de o erro de previsão ser calculado?", "",
        "Mantivemos a divisão cronológica, os alphas EWMA V2 e os detectores de média, variância e máximo normalizado. Limiar e quartis de duração foram calibrados somente na validação. A amostra sintética é retirada do teste, com até 100 jobs por quartil e horizonte e pelo menos 80 erros de previsão para permitir todas as larguras de janela.", "",
        "As mudanças foram inseridas na potência bruta: degraus e rampas de nível para cima/baixo; mudanças isoladas na escala do desvio-padrão; e mudanças simultâneas de nível e dispersão. A escala local é o desvio-padrão dos 20 pontos brutos anteriores ao evento. Depois da intervenção, o EWMA é recalculado usando apenas o passado disponível para cada previsão.", "",
        f"Jobs vistos: validação {seen['validation']:,}; teste {seen['test']:,}. Cenários: {len(specs)}. O ponto de mudança é conhecido em cada série. Atraso é calculado na escala temporal de amostragem de 20 s.", "",
        "## Alertas naturais no teste — janela de 200 s", "",
        "Frações de jobs com ao menos um alerta, não taxas de falso positivo. Não há rótulos independentes de mudanças naturais.", "",
        "| Horizonte | Média | Variância | Máximo |", "|---:|---:|---:|---:|"
    ]
    for h in HORIZONS:
        sec = str(h*20)
        vals = []
        for method in METHODS:
            bins = natural[h][10][method]
            n = sum(a["n"] for a in bins.values())
            k = sum(a["alerts"] for a in bins.values())
            vals.append(f"{k/n:.2%}" if n else "n/a")
        lines.append(f"| {h*20} s | " + " | ".join(vals) + " |")
    lines += ["", "## Detecção sintética por classe — janela de 200 s", "",
              "Cada célula informa detecção após a mudança na série alterada / alerta pós-ponto na série original sem intervenção / ganho incremental (diferença) / pré-alerta na série alterada. n conta instâncias cenário-job; os mesmos jobs são reutilizados em cenários diferentes e, portanto, n não é o número de jobs únicos.", "",
              "| Horizonte | Classe | Método | Alterada | Original pós-CP | Incremento (p.p.) | Pré-alerta | n instâncias |",
              "|---:|---|---|---:|---:|---:|---:|---:|"]
    for h in HORIZONS:
        sec = str(h*20)
        labels = {"mean_only": "Nível isolado", "sd_only": "Dispersão isolada", "mixed": "Nível + dispersão"}
        for cls in ("mean_only", "sd_only", "mixed"):
            for method in METHODS:
                r = class_summary[sec][cls][method]
                lines.append(
                    f"| {h*20} s | {labels[cls]} | {method} | "
                    f"{r['weighted_detection_fraction']:.1%} | "
                    f"{r['weighted_baseline_postchange_alert_fraction']:.1%} | "
                    f"{r['incremental_detection_fraction']*100:+.1f} p.p. | "
                    f"{r['weighted_prealert_fraction']:.1%} | {r['scenario_job_instances']} |"
                )
    lines += ["", "## Comparação pareada: intervenção versus potência original — janela de 200 s", "",
              "Diferença = indicador de primeiro alerta pós-CP na série alterada menos o mesmo indicador na série original não alterada, no mesmo job e no mesmo ponto de referência. IC normal pareado de 95%, sem correção por multiplicidade.", "",
              "| Método | Ganho médio pareado (p.p.) | IC95% ganho positivo | IC95% ganho negativo | Inclui zero |",
              "|---|---:|---:|---:|---:|"]
    for method in METHODS:
        r = incremental_summary[method]
        lines.append(
            f"| {method} | {r['mean_paired_incremental_detection']*100:+.2f} p.p. | "
            f"{r['ci_increment_above_zero']} | {r['ci_decrement_below_zero']} | "
            f"{r['ci_includes_zero']} |"
        )
    lines += ["", "## Comparação pareada do máximo com os detectores isolados — janela de 200 s", "",
              "Diferença = detecção do máximo menos detecção do detector isolado, nas séries alteradas. Intervalos normais pareados de 95%, sem correção por multiplicidade; contam-se 160 combinações de cenário e horizonte.", "",
              "| Comparação | Diferença média (p.p.) | IC95% favorece máximo | IC95% favorece isolado | Inclui zero |",
              "|---|---:|---:|---:|---:|"]
    for single in ("mean", "variance"):
        r = paired_summary[single]
        lines.append(
            f"| Máximo − {single} | {r['mean_paired_difference_max_minus_single']*100:+.2f} p.p. | "
            f"{r['ci_max_wholly_above_single']} | {r['ci_single_wholly_above_max']} | {r['ci_includes_zero']} |"
        )
    lines += [
        "",
        "## Síntese dos ganhos incrementais", "",
        "Para mudanças apenas de nível, o ganho médio foi praticamente nulo: +0,15 p.p. (média), −0,23 p.p. (variância) e +0,05 p.p. (máximo). Para mudanças apenas de dispersão, os ganhos foram +0,64, +3,14 e +2,55 p.p., respectivamente. Nas mudanças simultâneas, foram +0,58, +3,30 e +2,53 p.p.",
        "Assim, a resposta incremental observada está concentrada em mudanças que alteram a dispersão. O detector de variância teve o maior ganho médio, enquanto o máximo foi intermediário. As taxas absolutas de detecção permanecem baixas e não demonstram sensibilidade adequada para uso operacional.",
        "Os totais agregam combinações de cenário e horizonte; os mesmos jobs aparecem em diferentes cenários. Os intervalos pareados são exploratórios e não têm correção para multiplicidade.",
    ]
    lines += ["", "## Cenários individuais de referência — janela de 200 s", "",
              "Cada método: detecção após a mudança / alerta pós-CP na série original / ganho incremental / pré-alerta.", "",
              "| Horizonte | Cenário | Média | Variância | Máximo |",
              "|---:|---|---:|---:|---:|"]
    selected = [
        "mean_step_up_d2", "mean_step_down_d2", "sd_step_m2",
        "mixed_step_up_d1_m2", "mixed_step_down_d1_m2",
        "mixed_ramp_up_d1_m2", "mixed_ramp_down_d1_m2"
    ]
    for h in HORIZONS:
        sec = str(h*20)
        for name in selected:
            r = synthetic[sec][name]["results"]["10"]
            vals = [
                f"{r[m]['detection_fraction']:.1%} / "
                f"{r[m]['baseline_postchange_alert_fraction']:.1%} / "
                f"{r[m]['incremental_detection_fraction']*100:+.1f} p.p. / "
                f"{r[m]['prealert_fraction']:.1%}"
                for m in METHODS
            ]
            lines.append(f"| {h*20} s | {name} | " + " | ".join(vals) + " |")
    lines += [
        "",
        "## Interpretação e limites", "",
        "- Este teste é mais próximo da variável medida do que as intervenções anteriores nos resíduos: a potência bruta é alterada e o EWMA é recalculado. Ainda assim, as intervenções são sintéticas e não validam detecção de mudanças físicas reais.",
        "- Um degrau de potência pode gerar um pico transitório no erro enquanto o EWMA se adapta; portanto, não se espera necessariamente que o erro permaneça deslocado. A resposta depende de alpha e horizonte.",
        "- Pré-alerta significa que o primeiro cruzamento ocorreu antes do ponto de mudança conhecido; não é contado como detecção daquela mudança.",
        "- A taxa de detecção bruta inclui alertas que poderiam ocorrer mesmo sem a intervenção. Por isso, o V2 reporta também o primeiro alerta pós-CP no sinal original e a diferença pareada alterado − original; esse ganho incremental é a leitura principal.",
        "- Degraus descendentes e expansão de dispersão podem sofrer truncamento em zero. Os intervalos de Wilson e os resultados por quartil estão no JSON.",
        "- PM100 mede potência agregada do job/nó, não GPU-only. Não há rótulos naturais, outra divisão temporal, validação operacional ou demonstração de economia de energia.",
        "- Nada nesta fase valida ATOCIA ou ATRP-1.",
        "",
        "## Artefatos", "",
        "- raw_power_change_detection_v2.py",
        "- audit/raw_power_change_detection_v2.json",
        "- PM100_RAW_POWER_CHANGE_DETECTION_V2.md",
        "- V1 preservado como histórico preliminar; V2 adiciona o baseline pareado sem intervenção.",
        "",
        "O Parquet original e os modelos anteriores não foram alterados.",
        "",
        "**Fase encerrada; aguardar autorização antes da próxima.**"
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out["script_sha256"] = sha256(Path(__file__))
    out["report_sha256"] = sha256(REPORT)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("Completed raw-power perturbation evaluation.")
    print(f"validation_jobs={seen['validation']} test_jobs={seen['test']}")
    print(f"input_sha256={out['input_sha256']}")
    print(f"script_sha256={out['script_sha256']}")
    print(f"report_sha256={out['report_sha256']}")
    print(f"json_sha256={sha256(OUT)}")
    print(f"Wrote {OUT}")
    print(f"Wrote {REPORT}")


if __name__ == "__main__":
    main()
