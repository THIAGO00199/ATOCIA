#!/usr/bin/env python3
"""Matched-budget fusion rules for simultaneous level and dispersion changes."""
from __future__ import annotations
import json, hashlib, math
from pathlib import Path
import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "job_table.parquet"
BASE = ROOT / "audit" / "trajectory_online_models_v2.json"
PREV = ROOT / "audit" / "combined_window_detectors_v1.json"
OUT = ROOT / "audit" / "mixed_change_fusion_v1.json"
REPORT = ROOT / "PM100_MIXED_CHANGE_FUSION_V1.md"
HORIZONS = (1, 2, 3, 6)
WINDOWS = (5, 10, 20)
METHODS = ("mean", "variance", "max", "sum", "l2")
FUSIONS = ("max", "sum", "l2")
MIN_FORECASTS = 41
TAIL = 0.05
SAMPLE_PER_BIN = 250
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
            if np.isfinite(x).all():
                yield x


def error_series(x, horizon, alpha):
    t = np.arange(4, len(x) - horizon)
    if len(t) < MIN_FORECASTS:
        return None
    smooth = np.empty(len(x), dtype=np.float64)
    smooth[0] = x[0]
    for i in range(1, len(x)):
        smooth[i] = alpha * x[i] + (1.0 - alpha) * smooth[i - 1]
    e = np.abs(x[t + horizon] - smooth[t])
    return e if len(e) >= MIN_FORECASTS and np.isfinite(e).all() else None


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


def fusion_paths(mean_path, var_path, mean_q95, var_q95):
    a = mean_path / mean_q95
    b = var_path / var_q95
    return {
        "max": np.maximum(a, b),
        "sum": (a + b) / math.sqrt(2.0),
        "l2": np.sqrt(a * a + b * b)
    }


def qhigher(values, q):
    return float(np.quantile(np.asarray(values, dtype=np.float64), q, method="higher"))


def bin_index(n, edges):
    return int(np.searchsorted(edges, n, side="right"))


def first_cross(path, threshold, w):
    ix = np.flatnonzero(path > threshold)
    return int(2 * w + ix[0]) if len(ix) else None


def scenarios():
    out = []
    # One-factor controls: mean-only and SD-only, in both step and ramp forms.
    for shape in ("step", "ramp"):
        for delta in (0.5, 1.0, 2.0):
            out.append({
                "name": f"mean_{shape}_d{delta:g}",
                "shape": shape, "mean_shift_sd": delta,
                "sd_multiplier": 1.0, "cp_fraction": 0.50,
                "class": "mean_only"
            })
        for mult in (1.5, 2.0):
            out.append({
                "name": f"sd_{shape}_m{mult:g}",
                "shape": shape, "mean_shift_sd": 0.0,
                "sd_multiplier": mult, "cp_fraction": 0.50,
                "class": "sd_only"
            })
        # Simultaneous positive level and dispersion changes.
        for delta in (0.5, 1.0, 2.0):
            for mult in (1.5, 2.0):
                out.append({
                    "name": f"mixed_{shape}_d{delta:g}_m{mult:g}",
                    "shape": shape, "mean_shift_sd": delta,
                    "sd_multiplier": mult, "cp_fraction": 0.50,
                    "class": "mixed"
                })
    return out


def perturb(e, w, spec):
    n = len(e)
    if n < 4 * w:
        return None, None
    frac = float(spec["cp_fraction"])
    cp = 2 * w + int(round(frac * (n - 4 * w)))
    if cp < 2 * w or n - cp < 2 * w:
        return None, None
    ref = e[cp - w:cp]
    center = float(np.mean(ref))
    scale = max(float(np.std(ref, ddof=1)), 1.0)
    delta = float(spec["mean_shift_sd"]) * scale
    mult = float(spec["sd_multiplier"])
    y = e.copy()
    post_n = n - cp
    if spec["shape"] == "step":
        progress = np.ones(post_n, dtype=np.float64)
    elif spec["shape"] == "ramp":
        ramp_n = min(post_n, max(2 * w, int(math.ceil(0.5 * post_n))))
        progress = np.ones(post_n, dtype=np.float64)
        progress[:ramp_n] = np.linspace(1.0 / ramp_n, 1.0, ramp_n, endpoint=True)
    else:
        raise ValueError(spec["shape"])
    post = e[cp:]
    y[cp:] = np.maximum(
        0.0,
        center + progress * delta + (1.0 + progress * (mult - 1.0)) * (post - center)
    )
    return y, cp


def new_acc():
    return {"n": 0, "detected": 0, "prealert": 0, "delays_s": [],
            "detected_flags": [], "prealert_flags": []}


def update_acc(acc, end, cp):
    acc["n"] += 1
    detected = int(end is not None and end > cp)
    prealert = int(end is not None and end <= cp)
    acc["detected"] += detected
    acc["prealert"] += prealert
    acc["detected_flags"].append(detected)
    acc["prealert_flags"].append(prealert)
    if detected:
        acc["delays_s"].append((end - cp) * SAMPLE_SECONDS)


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
    del acc["delays_s"]


def paired_diff(a, b):
    """Paired difference a-b for binary detections, normal 95% CI."""
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

    # Keep per-job validation maxima so all candidates get a matched q95 budget.
    validation = {h: [] for h in HORIZONS}
    seen = {"validation": 0, "test": 0}
    for x in scan(con, rel, val_cut, test_cut, "validation"):
        seen["validation"] += 1
        for h in HORIZONS:
            e = error_series(x, h, alphas[h])
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

    # First calibrate individual mean and variance scales within frozen duration bins.
    calibration = {}
    thresholds = {h: {w: {} for w in WINDOWS} for h in HORIZONS}
    validation_exceedance = {}
    fusion_cal = {
        h: {w: {b: {f: [] for f in METHODS[2:]} for b in range(4)} for w in WINDOWS}
        for h in HORIZONS
    }
    for h in HORIZONS:
        rows = validation[h]
        edges = [qhigher([r["n"] for r in rows], q) for q in (0.25, 0.50, 0.75)]
        calibration[h] = {"duration_bin_edges_forecasts": edges, "bins": {}}
        for b in range(4):
            calibration[h]["bins"][str(b)] = {}
            members = [r for r in rows if bin_index(r["n"], edges) == b]
            for w in WINDOWS:
                mthr = qhigher([r["maxima"][str(w)]["mean"] for r in members], 1.0-TAIL)
                vthr = qhigher([r["maxima"][str(w)]["variance"] for r in members], 1.0-TAIL)
                thresholds[h][w][b] = {"mean": mthr, "variance": vthr}
                calibration[h]["bins"][str(b)][str(w)] = {
                    "validation_jobs": len(members),
                    "mean_q95": mthr,
                    "variance_q95": vthr
                }

    # Second validation pass: fuse the two statistic paths at each time point,
    # then take each job's maximum. This avoids combining maxima from different times.
    for x in scan(con, rel, val_cut, test_cut, "validation"):
        for h in HORIZONS:
            e = error_series(x, h, alphas[h])
            if e is None:
                continue
            b = bin_index(len(e), calibration[h]["duration_bin_edges_forecasts"])
            for w in WINDOWS:
                mp, vp = window_paths(e, w)
                th = thresholds[h][w][b]
                scores = fusion_paths(mp, vp, th["mean"], th["variance"])
                for f in METHODS[2:]:
                    fusion_cal[h][w][b][f].append(float(np.max(scores[f])))

    for h in HORIZONS:
        validation_exceedance[h] = {}
        for b in range(4):
            validation_exceedance[h][b] = {}
            members = [r for r in validation[h]
                       if bin_index(r["n"], calibration[h]["duration_bin_edges_forecasts"]) == b]
            for w in WINDOWS:
                for f in METHODS[2:]:
                    fthr = qhigher(fusion_cal[h][w][b][f], 1.0-TAIL)
                    thresholds[h][w][b][f] = fthr
                    calibration[h]["bins"][str(b)][str(w)][f + "_q95"] = fthr
                validation_exceedance[h][b][str(w)] = {
                    "mean": sum(r["maxima"][str(w)]["mean"] > thresholds[h][w][b]["mean"]
                                for r in members) / len(members),
                    "variance": sum(r["maxima"][str(w)]["variance"] > thresholds[h][w][b]["variance"]
                                    for r in members) / len(members)
                }
                for f in METHODS[2:]:
                    vals = fusion_cal[h][w][b][f]
                    validation_exceedance[h][b][str(w)][f] = (
                        sum(v > thresholds[h][w][b][f] for v in vals) / len(vals)
                    )

    natural = {h: {w: {m: {b: {"n": 0, "alerts": 0, "delays_s": []} for b in range(4)}
                          for m in METHODS} for w in WINDOWS} for h in HORIZONS}
    reservoirs = {h: {b: [] for b in range(4)} for h in HORIZONS}
    reservoir_seen = {h: {b: 0 for b in range(4)} for h in HORIZONS}
    rng = np.random.default_rng(SEED)
    for x in scan(con, rel, val_cut, test_cut, "test"):
        seen["test"] += 1
        for h in HORIZONS:
            e = error_series(x, h, alphas[h])
            if e is None:
                continue
            b = bin_index(len(e), calibration[h]["duration_bin_edges_forecasts"])
            reservoir_seen[h][b] += 1
            bucket = reservoirs[h][b]
            if len(bucket) < SAMPLE_PER_BIN:
                bucket.append(e.copy())
            else:
                j = int(rng.integers(0, reservoir_seen[h][b]))
                if j < SAMPLE_PER_BIN:
                    bucket[j] = e.copy()
            for w in WINDOWS:
                mp, vp = window_paths(e, w)
                th = thresholds[h][w][b]
                scores = fusion_paths(mp, vp, th["mean"], th["variance"])
                paths = {
                    "mean": mp, "variance": vp,
                    "max": scores["max"], "sum": scores["sum"], "l2": scores["l2"]
                }
                limits = {m: th[m] for m in METHODS}
                for m in METHODS:
                    a = natural[h][w][m][b]
                    a["n"] += 1
                    ix = first_cross(paths[m], limits[m], w)
                    if ix is not None:
                        a["alerts"] += 1
                        a["delays_s"].append((ix - 2*w) * SAMPLE_SECONDS)

    specs = scenarios()
    synthetic = {}
    for h in HORIZONS:
        sec = str(h*20)
        synthetic[sec] = {}
        for spec in specs:
            synthetic[sec][spec["name"]] = {
                "spec": spec, "results": {},
                "paired_fusion_vs_max": {}
            }
            for w in WINDOWS:
                synthetic[sec][spec["name"]]["results"][str(w)] = {
                    m: {"n": 0, "detected": 0, "prealert": 0, "delays_s": [],
                        "detected_flags": [], "prealert_flags": [],
                        "by_duration_bin": {str(b): new_acc() for b in range(4)}}
                    for m in METHODS
                }
        for b in range(4):
            for e in reservoirs[h][b]:
                for spec in specs:
                    for w in WINDOWS:
                        changed, cp = perturb(e, w, spec)
                        if changed is None:
                            continue
                        mp, vp = window_paths(changed, w)
                        th = thresholds[h][w][b]
                        scores = fusion_paths(mp, vp, th["mean"], th["variance"])
                        paths = {
                            "mean": mp, "variance": vp,
                            "max": scores["max"], "sum": scores["sum"], "l2": scores["l2"]
                        }
                        for m in METHODS:
                            result = synthetic[sec][spec["name"]]["results"][str(w)][m]
                            end = first_cross(paths[m], th[m], w)
                            update_acc(result, end, cp)
                            update_acc(result["by_duration_bin"][str(b)], end, cp)
        for spec in specs:
            for w in WINDOWS:
                res = synthetic[sec][spec["name"]]["results"][str(w)]
                paired = {}
                for m in METHODS:
                    finish_acc(res[m])
                    for by in res[m]["by_duration_bin"].values():
                        finish_acc(by)
                for f in ("sum", "l2"):
                    paired[f] = paired_diff(
                        res[f]["detected_flags"], res["max"]["detected_flags"]
                    )
                synthetic[sec][spec["name"]]["paired_fusion_vs_max"][str(w)] = paired
                for m in METHODS:
                    del res[m]["detected_flags"]
                    del res[m]["prealert_flags"]

    natural_out, validation_out = {}, {}
    for h in HORIZONS:
        sec = str(h*20)
        natural_out[sec], validation_out[sec] = {}, {}
        for w in WINDOWS:
            natural_out[sec][str(w)], validation_out[sec][str(w)] = {}, {}
            for m in METHODS:
                bins = {}
                for b, a in natural[h][w][m].items():
                    bins[str(b)] = {
                        "test_jobs": a["n"], "alert_jobs": a["alerts"],
                        "alert_fraction": a["alerts"]/a["n"] if a["n"] else None,
                        "median_alert_delay_s": float(np.median(a["delays_s"])) if a["delays_s"] else None
                    }
                natural_out[sec][str(w)][m] = {"by_duration_bin": bins}
                validation_out[sec][str(w)][m] = {
                    str(b): validation_exceedance[h][b][str(w)][m] for b in range(4)
                }

    out = {
        "dataset": "PM100 v1",
        "input_sha256": sha256(INPUT),
        "baseline_v2_sha256": sha256(BASE),
        "previous_fusion_study_sha256": sha256(PREV),
        "calibration_audit_note": "An initial pilot that combined separate per-job maxima for sum/L2 was discarded because it did not match pointwise fusion on test; the final run recomputes joint pointwise paths in a second validation pass before q95 calibration.",
        "target": "job-level aggregate node power, not GPU-only",
        "split": "chronological 70/85% start_time; validation defines bins and all thresholds; test held out",
        "ewma_alpha_frozen_from_v2": {str(h*20): alphas[h] for h in HORIZONS},
        "protocol": {
            "windows_samples": list(WINDOWS),
            "windows_seconds": [20*w for w in WINDOWS],
            "methods": list(METHODS),
            "fusion_calibration": "strictly pointwise on the validation time series before the per-job maximum is taken; the test uses the identical ordering of operations",
            "fusion_scores": {
                "max": "max(mean_stat/mean_q95, variance_stat/variance_q95)",
                "sum": "(mean_stat/mean_q95 + variance_stat/variance_q95)/sqrt(2)",
                "l2": "sqrt((mean_stat/mean_q95)^2 + (variance_stat/variance_q95)^2)"
            },
            "threshold": "individual mean/variance q95 from per-job maxima; for each fusion, pointwise normalized series are fused first, then per-job maxima are calibrated at q95 in validation, stratified by horizon, window and duration quartile",
            "target_validation_job_alert_fraction": TAIL,
            "synthetic_sample_per_duration_bin_per_horizon": SAMPLE_PER_BIN,
            "synthetic_seed": SEED,
            "synthetic_scenarios": len(specs),
            "synthetic_change_point": "midpoint of monitored tail",
            "mixed_perturbation": "post-change mean increases by delta times preceding-window SD while deviations around the preceding-window mean are scaled by m; step or linear ramp for both changes",
            "sd_multiplier_effect": "m multiplies SD; nominal variance multiplier m^2 before clipping",
            "sampling_interval_s": SAMPLE_SECONDS
        },
        "jobs_seen": seen,
        "duration_calibration": calibration,
        "validation_exceedance_fractions": validation_out,
        "natural_test_alerts": natural_out,
        "synthetic_scenarios": synthetic,
        "synthetic_sample_counts_by_horizon_bin": {
            str(h*20): {str(b): len(reservoirs[h][b]) for b in range(4)} for h in HORIZONS
        },
        "limitations": [
            "Synthetic transformations are applied to absolute forecast-error series, not raw power measurements.",
            "Mixed scenarios are positive level shifts plus SD expansion; they do not represent every possible joint change or physical mechanism.",
            "SD multiplier m implies variance multiplier m^2 before zero clipping.",
            "All methods are calibrated to q95 of validation per-job maxima; this is an empirical validation budget, not a guaranteed future false-alarm probability.",
            "Natural test alerts have no independent changepoint labels and cannot be classified as true or false positives.",
            "Synthetic evaluation uses a reproducible reservoir of up to 250 test jobs per duration bin and horizon; window 20 requires at least 80 forecasts, reducing some denominators.",
            "Only one chronological split and a short test window are covered; temporal generalization is unproven.",
            "PM100 target is aggregate job/node power, not GPU-only power; this does not validate ATOCIA or ATRP-1."
        ]
    }

    # Human-readable report.
    lines = [
        "# PM100 — fusão de detectores em mudanças simultâneas (V1)", "",
        "**Status:** comparação exploratória com orçamento de alertas igualado na validação; mudanças sintéticas não são mudanças físicas observadas.", "",
        "## Pergunta e protocolo", "",
        "Uma fusão por soma normalizada ou norma L2 recupera sensibilidade em mudanças simultâneas de nível e dispersão, em comparação com a regra pelo máximo?", "",
        "Foram comparadas cinco alternativas: média isolada, variância isolada, máximo normalizado (regra anterior), soma normalizada e norma L2. Para média e variância, os limiares individuais são os percentis 95 dos máximos por job. Para cada fusão, os sinais são combinados ponto a ponto na série temporal e só então é calculado o máximo por job; o limiar é o percentil 95 desses máximos combinados na validação, separado por horizonte, janela e quartil de duração. Portanto, todos têm a mesma meta empírica de 5% por job na validação; a fusão não recebe dois orçamentos de 5%.", "",
        "Os testes sintéticos usam os mesmos jobs amostrados por horizonte e quartil. O ponto de mudança está no meio do trecho monitorado. Foram incluídos controles de mudança somente na média, somente na escala do desvio-padrão e mudanças simultâneas. Degraus e rampas são avaliados separadamente.", "",
        f"Jobs vistos: validação {seen['validation']:,}; teste {seen['test']:,}. Cenários: {len(specs)}; amostra de até {SAMPLE_PER_BIN} jobs por quartil e horizonte.", "",
        "## Alertas naturais no teste — janela de 10 amostras", "",
        "Fração de jobs com pelo menos um alerta, ponderada pelos tamanhos dos quartis. Não é taxa de falsos positivos: não existem rótulos independentes para as mudanças naturais.", "",
        "| Horizonte | Média | Variância | Máximo | Soma | L2 |", "|---:|---:|---:|---:|---:|---:|"
    ]
    for h in HORIZONS:
        cells = []
        for m in METHODS:
            bins = natural[h][10][m]
            n = sum(a["n"] for a in bins.values())
            k = sum(a["alerts"] for a in bins.values())
            cells.append(f"{k/n:.2%}")
        lines.append(f"| {h*20} s | " + " | ".join(cells) + " |")
    lines += ["", "## Mudanças simultâneas — janela de 10 amostras", "",
              "Detecção após a mudança / pré-alerta anterior à mudança. O JSON contém atrasos, intervalos de Wilson, resultados por quartil e comparações pareadas das fusões contra o máximo.", "",
              "### Degraus simultâneos", "",
              "| Horizonte | Cenário | Máximo | Soma | L2 |",
              "|---:|---|---:|---:|---:|"]
    mixed_step = [s for s in specs if s["class"] == "mixed" and s["shape"] == "step"]
    for h in HORIZONS:
        sec = str(h*20)
        for spec in mixed_step:
            vals = []
            for m in ("max", "sum", "l2"):
                r = synthetic[sec][spec["name"]]["results"]["10"][m]
                vals.append(f"{r['detection_fraction']:.1%} / {r['prealert_fraction']:.1%}")
            lines.append(f"| {h*20} s | d={spec['mean_shift_sd']} SD, SD×{spec['sd_multiplier']} | " + " | ".join(vals) + " |")
    lines += ["", "### Rampas simultâneas", "",
              "| Horizonte | Cenário | Máximo | Soma | L2 |",
              "|---:|---|---:|---:|---:|"]
    mixed_ramp = [s for s in specs if s["class"] == "mixed" and s["shape"] == "ramp"]
    for h in HORIZONS:
        sec = str(h*20)
        for spec in mixed_ramp:
            vals = []
            for m in ("max", "sum", "l2"):
                r = synthetic[sec][spec["name"]]["results"]["10"][m]
                vals.append(f"{r['detection_fraction']:.1%} / {r['prealert_fraction']:.1%}")
            lines.append(f"| {h*20} s | d={spec['mean_shift_sd']} SD, SD×{spec['sd_multiplier']} | " + " | ".join(vals) + " |")
    lines += ["", "## Diferença pareada em relação à fusão pelo máximo", "",
              "Diferença = taxa de detecção do método alternativo menos a taxa do máximo. O intervalo é uma aproximação normal pareada de 95%, calculada sobre os mesmos jobs sintéticos; não corrige multiplicidade entre cenários.", "",
              "| Horizonte | Cenário | Soma − máximo (IC95%) | L2 − máximo (IC95%) |",
              "|---:|---|---:|---:|"]
    for h in HORIZONS:
        sec = str(h*20)
        for spec in mixed_step + mixed_ramp:
            p = synthetic[sec][spec["name"]]["paired_fusion_vs_max"]["10"]
            row = [f"{h*20} s", f"{spec['shape']}, d={spec['mean_shift_sd']}, SD×{spec['sd_multiplier']}"]
            for m in ("sum", "l2"):
                a = p[m]
                row.append(f"{a['difference']:+.1%} [{a['ci95_normal'][0]:+.1%}, {a['ci95_normal'][1]:+.1%}]")
            lines.append("| " + " | ".join(row) + " |")
    paired_summary = {}
    for f in ("sum", "l2"):
        neg = pos = overlap = 0
        diffs = []
        for h in HORIZONS:
            sec = str(h*20)
            for spec in mixed_step + mixed_ramp:
                z = synthetic[sec][spec["name"]]["paired_fusion_vs_max"]["10"][f]
                lo, hi = z["ci95_normal"]
                neg += int(hi < 0.0)
                pos += int(lo > 0.0)
                overlap += int(lo <= 0.0 <= hi)
                diffs.append(z["difference"])
        paired_summary[f] = {
            "n_scenarios": len(diffs),
            "ci_wholly_below_zero": neg,
            "ci_wholly_above_zero": pos,
            "ci_includes_zero": overlap,
            "mean_paired_difference": float(np.mean(diffs)),
            "median_paired_difference": float(np.median(diffs)),
            "min_paired_difference": float(np.min(diffs)),
            "max_paired_difference": float(np.max(diffs))
        }
    out["paired_fusion_summary_window10_mixed"] = paired_summary
    lines += [
        "",
        "## Resumo das diferenças pareadas", "",
        f"Entre 48 comparações pareadas de cenários mistos (quatro horizontes, seis degraus e seis rampas por horizonte), a soma teve {paired_summary['sum']['ci_wholly_below_zero']} intervalos de 95% inteiramente abaixo de zero, nenhum inteiramente acima e {paired_summary['sum']['ci_includes_zero']} incluindo zero. Para L2, foram {paired_summary['l2']['ci_wholly_below_zero']} abaixo, nenhum acima e {paired_summary['l2']['ci_includes_zero']} incluindo zero.",
        f"A diferença média pareada (alternativa menos máximo) foi {paired_summary['sum']['mean_paired_difference']*100:+.2f} pontos percentuais para soma e {paired_summary['l2']['mean_paired_difference']*100:+.2f} p.p. para L2.",
        "Isso não demonstra que as alternativas sejam universalmente piores, mas não há evidência pareada de que recuperem a sensibilidade perdida em relação ao máximo. Os intervalos são aproximações normais e não foram ajustados por multiplicidade.",
        "",
        "## Nota de auditoria", "",
        "Um piloto inicial foi descartado: ele combinava os máximos separados dos dois sinais na validação, enquanto no teste combinava os sinais ponto a ponto antes de calcular o máximo. Para soma e L2, essas operações não são equivalentes e produziam limiares inflados. A execução final usa uma segunda passagem pela validação para calibrar os máximos das séries já combinadas ponto a ponto. Somente os resultados da execução corrigida são apresentados neste relatório.",
    ]
    lines += [
        "",
        "## Interpretação e limites", "",
        "- A comparação principal é entre regras com o mesmo orçamento empírico de alertas na validação. Incidências distintas no teste indicam deriva da distribuição ou do comportamento, não falsos positivos comprovados.",
        "- Um ganho em cenários mistos não basta para declarar um detector superior: os controles de média-only e SD-only verificam se a fusão apenas favorece uma família de mudanças.",
        "- O intervalo pareado é descritivo e normal-approximate; os cenários compartilham os mesmos jobs e múltiplas comparações são feitas. Não deve ser lido como confirmação independente.",
        "- As perturbações alteram erros absolutos observados, não medições brutas de potência. O SD multiplier m implica variância nominal m² antes do truncamento.",
        "- Sem rótulos reais e outros períodos temporais, não podemos estimar precisão, recall ou validade operacional. PM100 mede potência agregada por job/nó, não GPU-only.",
        "- Nada nesta fase valida ATOCIA ou ATRP-1, economia de energia ou segurança térmica.",
        "",
        "## Artefatos", "",
        "- mixed_change_fusion_v1.py",
        "- audit/mixed_change_fusion_v1.json",
        "- PM100_MIXED_CHANGE_FUSION_V1.md",
        "",
        "Os dados Parquet e os modelos anteriores não foram alterados.",
        "",
        "**Fase encerrada; aguardar autorização antes de iniciar a próxima.**"
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out["script_sha256"] = sha256(Path(__file__))
    out["report_sha256"] = sha256(REPORT)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("Completed mixed-change fusion evaluation.")
    print(f"validation_jobs={seen['validation']} test_jobs={seen['test']}")
    print(f"input_sha256={out['input_sha256']}")
    print(f"script_sha256={out['script_sha256']}")
    print(f"report_sha256={out['report_sha256']}")
    print(f"json_sha256={sha256(OUT)}")
    print(f"Wrote {OUT}")
    print(f"Wrote {REPORT}")


if __name__ == "__main__":
    main()
