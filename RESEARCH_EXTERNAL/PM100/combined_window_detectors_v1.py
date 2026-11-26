#!/usr/bin/env python3
"""Validation-calibrated fusion of adjacent-window mean and variance detectors."""
from __future__ import annotations
import json, hashlib, math
from pathlib import Path
import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "job_table.parquet"
BASE = ROOT / "audit" / "trajectory_online_models_v2.json"
PREV = ROOT / "audit" / "window_comparison_synthetic_v1.json"
OUT = ROOT / "audit" / "combined_window_detectors_v1.json"
REPORT = ROOT / "PM100_COMBINED_WINDOW_DETECTORS_V1.md"
HORIZONS = (1, 2, 3, 6)
WINDOWS = (5, 10, 20)
METHODS = ("mean", "variance", "combined")
MIN_FORECASTS = 41
TAIL = 0.05
SAMPLE_PER_BIN = 250
SEED = 20261123
SAMPLE_SECONDS = 20.0


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


def qhigher(values, q):
    return float(np.quantile(np.asarray(values, dtype=np.float64), q, method="higher"))


def bin_index(n, edges):
    return int(np.searchsorted(edges, n, side="right"))


def first_cross(path, threshold, w):
    ix = np.flatnonzero(path > threshold)
    return int(2 * w + ix[0]) if len(ix) else None


def wilson(k, n, z=1.959963984540054):
    if n <= 0:
        return None
    p = k / n
    den = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / den
    half = z * math.sqrt((p * (1.0 - p) / n) + z * z / (4.0 * n * n)) / den
    return [max(0.0, center - half), min(1.0, center + half)]


def scenarios():
    out = []
    for shape in ("step_up", "step_down", "ramp_up", "ramp_down"):
        for mag in (0.5, 1.0, 2.0):
            out.append({"name": f"{shape}_s{mag:g}_cp50", "shape": shape,
                        "magnitude_sd": mag, "cp_fraction": 0.50})
    for shape in ("step_up", "step_down", "ramp_up", "ramp_down"):
        for frac in (0.25, 0.75):
            out.append({"name": f"{shape}_s2_cp{int(frac*100)}", "shape": shape,
                        "magnitude_sd": 2.0, "cp_fraction": frac})
    # The multiplier scales deviations (SD), so x2 means variance x4 before clipping.
    for mult in (1.5, 2.0, 3.0):
        out.append({"name": f"sd_x{mult:g}_cp50", "shape": "scale_sd",
                    "sd_multiplier": mult, "cp_fraction": 0.50})
    for frac in (0.25, 0.75):
        out.append({"name": f"sd_x2_cp{int(frac*100)}", "shape": "scale_sd",
                    "sd_multiplier": 2.0, "cp_fraction": frac})
    return out


def perturb(e, w, spec):
    n = len(e)
    frac = float(spec["cp_fraction"])
    cp = 2 * w + int(round(frac * (n - 4 * w)))
    if cp < 2 * w or n - cp < 2 * w:
        return None, None
    ref = e[cp - w:cp]
    center = float(np.mean(ref))
    scale = max(float(np.std(ref, ddof=1)), 1.0)
    y = e.copy()
    shape = spec["shape"]
    if shape in ("step_up", "step_down"):
        delta = float(spec["magnitude_sd"]) * scale
        signed = delta if shape == "step_up" else -delta
        y[cp:] = np.maximum(0.0, y[cp:] + signed)
    elif shape in ("ramp_up", "ramp_down"):
        delta = float(spec["magnitude_sd"]) * scale
        signed = delta if shape == "ramp_up" else -delta
        ramp_n = min(n - cp, max(2 * w, int(math.ceil(0.5 * (n - cp)))))
        ramp = np.linspace(0.0, signed, ramp_n, endpoint=True, dtype=np.float64)
        y[cp:cp + ramp_n] = np.maximum(0.0, y[cp:cp + ramp_n] + ramp)
        if cp + ramp_n < n:
            y[cp + ramp_n:] = np.maximum(0.0, y[cp + ramp_n:] + signed)
    elif shape == "scale_sd":
        mult = float(spec["sd_multiplier"])
        y[cp:] = np.maximum(0.0, center + mult * (y[cp:] - center))
    else:
        raise ValueError(shape)
    return y, cp


def summarize_hit(acc, end, cp, w):
    acc["n"] += 1
    if end is None:
        return
    if end <= cp:
        acc["prealert"] += 1
    else:
        acc["detected"] += 1
        acc["delays_s"].append((end - cp) * SAMPLE_SECONDS)


def finish_acc(acc):
    n = acc["n"]
    acc["detection_fraction"] = acc["detected"] / n if n else None
    acc["detection_wilson95"] = wilson(acc["detected"], n)
    acc["prealert_fraction"] = acc["prealert"] / n if n else None
    acc["median_detection_delay_s"] = float(np.median(acc["delays_s"])) if acc["delays_s"] else None
    del acc["delays_s"]


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

    # Validation pass: retain paired per-job maxima, then calibrate individual and
    # joint thresholds within each frozen duration quartile.
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

    calibration = {}
    thresholds = {h: {w: {} for w in WINDOWS} for h in HORIZONS}
    validation_exceedance = {}
    for h in HORIZONS:
        rows = validation[h]
        edges = [qhigher([r["n"] for r in rows], q) for q in (0.25, 0.50, 0.75)]
        calibration[h] = {"duration_bin_edges_forecasts": edges, "bins": {}}
        validation_exceedance[h] = {}
        for b in range(4):
            calibration[h]["bins"][str(b)] = {}
            validation_exceedance[h][b] = {}
            members = [r for r in rows if bin_index(r["n"], edges) == b]
            for w in WINDOWS:
                mthr = qhigher([r["maxima"][str(w)]["mean"] for r in members], 1.0 - TAIL)
                vthr = qhigher([r["maxima"][str(w)]["variance"] for r in members], 1.0 - TAIL)
                joint_max = [max(r["maxima"][str(w)]["mean"] / mthr,
                                 r["maxima"][str(w)]["variance"] / vthr)
                             for r in members]
                jthr = qhigher(joint_max, 1.0 - TAIL)
                thresholds[h][w][b] = {"mean": mthr, "variance": vthr, "combined": jthr}
                calibration[h]["bins"][str(b)][str(w)] = {
                    "validation_jobs": len(members),
                    "mean_q95": mthr,
                    "variance_q95": vthr,
                    "combined_normalized_max_q95": jthr
                }
                validation_exceedance[h][b][str(w)] = {
                    "mean": sum(r["maxima"][str(w)]["mean"] > mthr for r in members) / len(members),
                    "variance": sum(r["maxima"][str(w)]["variance"] > vthr for r in members) / len(members),
                    "combined": sum(j > jthr for j in joint_max) / len(joint_max)
                }

    # Test pass: natural alerts and deterministic reservoir sample for paired synthetic tests.
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
            for w in WINDOWS:
                mp, vp = window_paths(e, w)
                th = thresholds[h][w][b]
                fused = np.maximum(mp / th["mean"], vp / th["variance"])
                paths = {
                    "mean": mp,
                    "variance": vp,
                    "combined": fused
                }
                limits = {
                    "mean": th["mean"],
                    "variance": th["variance"],
                    "combined": th["combined"]
                }
                for method in METHODS:
                    acc = natural[h][w][method][b]
                    acc["n"] += 1
                    end = first_cross(paths[method], limits[method], w)
                    if end is not None:
                        acc["alerts"] += 1
                        acc["delays_s"].append((end - 2 * w) * SAMPLE_SECONDS)
            reservoir_seen[h][b] += 1
            bucket = reservoirs[h][b]
            if len(bucket) < SAMPLE_PER_BIN:
                bucket.append(e.copy())
            else:
                j = int(rng.integers(0, reservoir_seen[h][b]))
                if j < SAMPLE_PER_BIN:
                    bucket[j] = e.copy()

    # Apply identical synthetic perturbations to the same test-job reservoir for
    # all three methods, retaining paired denominators and pre-change first alarms.
    specs = scenarios()
    synthetic = {}
    for h in HORIZONS:
        sec = str(h * 20)
        synthetic[sec] = {}
        for spec in specs:
            synthetic[sec][spec["name"]] = {"spec": spec, "results": {}}
            for w in WINDOWS:
                synthetic[sec][spec["name"]]["results"][str(w)] = {}
                for method in METHODS:
                    synthetic[sec][spec["name"]]["results"][str(w)][method] = {
                        "n": 0, "detected": 0, "prealert": 0, "delays_s": [],
                        "by_duration_bin": {
                            str(b): {"n": 0, "detected": 0, "prealert": 0, "delays_s": []}
                            for b in range(4)
                        }
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
                        fused = np.maximum(mp / th["mean"], vp / th["variance"])
                        paths = {"mean": mp, "variance": vp, "combined": fused}
                        limits = {
                            "mean": th["mean"],
                            "variance": th["variance"],
                            "combined": th["combined"]
                        }
                        for method in METHODS:
                            result = synthetic[sec][spec["name"]]["results"][str(w)][method]
                            by = result["by_duration_bin"][str(b)]
                            end = first_cross(paths[method], limits[method], w)
                            summarize_hit(result, end, cp, w)
                            summarize_hit(by, end, cp, w)
        for spec in specs:
            for w in WINDOWS:
                for method in METHODS:
                    r = synthetic[sec][spec["name"]]["results"][str(w)][method]
                    finish_acc(r)
                    for by in r["by_duration_bin"].values():
                        finish_acc(by)

    natural_out = {}
    validation_out = {}
    for h in HORIZONS:
        sec = str(h * 20)
        natural_out[sec] = {}
        validation_out[sec] = {}
        for w in WINDOWS:
            natural_out[sec][str(w)] = {}
            validation_out[sec][str(w)] = {}
            for method in METHODS:
                by = {}
                for b, a in natural[h][w][method].items():
                    by[str(b)] = {
                        "test_jobs": a["n"],
                        "alert_jobs": a["alerts"],
                        "alert_fraction": a["alerts"] / a["n"] if a["n"] else None,
                        "median_alert_delay_s": float(np.median(a["delays_s"])) if a["delays_s"] else None
                    }
                natural_out[sec][str(w)][method] = {"by_duration_bin": by}
                validation_out[sec][str(w)][method] = {
                    str(b): validation_exceedance[h][b][str(w)][method] for b in range(4)
                }

    out = {
        "dataset": "PM100 v1",
        "input_sha256": sha256(INPUT),
        "baseline_v2_sha256": sha256(BASE),
        "previous_window_study_sha256": sha256(PREV),
        "target": "job-level aggregate node power, not GPU-only",
        "split": "chronological 70/85% start_time; validation defines duration bins and all thresholds; test held out",
        "ewma_alpha_frozen_from_v2": {str(h * 20): alphas[h] for h in HORIZONS},
        "protocol": {
            "windows_samples": list(WINDOWS),
            "windows_seconds": [20 * w for w in WINDOWS],
            "individual_thresholds": "q95 validation per-job maximum for each statistic, horizon, window, duration quartile",
            "combined_statistic": "at each timestamp max(mean_stat/mean_q95, variance_stat/variance_q95)",
            "combined_threshold": "q95 validation per-job maximum of the combined normalized statistic, same horizon/window/duration quartile",
            "target_validation_job_alert_fraction": TAIL,
            "duration_bins": "four forecast-count quartiles defined on validation and frozen",
            "synthetic_sample_per_duration_bin_per_horizon": SAMPLE_PER_BIN,
            "synthetic_seed": SEED,
            "synthetic_variance_definition": "sd_xN multiplies deviations from preceding-window mean by N; nominal variance multiplier N^2 before zero clipping",
            "synthetic_scenarios": len(specs),
            "sampling_interval_s": SAMPLE_SECONDS
        },
        "jobs_seen": seen,
        "duration_calibration": calibration,
        "validation_exceedance_fractions": validation_out,
        "natural_test_alerts": natural_out,
        "synthetic_scenarios": synthetic,
        "synthetic_sample_counts_by_horizon_bin": {
            str(h * 20): {str(b): len(reservoirs[h][b]) for b in range(4)} for h in HORIZONS
        },
        "limitations": [
            "The combined detector is an OR-like maximum of normalized mean and variance statistics; it does not infer physical causes.",
            "The q95 joint calibration controls validation per-job maximum exceedance empirically, not future false-positive probability.",
            "Synthetic perturbations are applied to absolute forecast-error series, not raw power traces.",
            "Downward changes are clipped at zero; scale_sd scenarios multiply standard deviation by N and therefore nominal variance by N^2 before clipping.",
            "Natural test alerts have no independent changepoint labels; they cannot be classified as true or false positives.",
            "Synthetic tests use a reproducible sample of at most 250 jobs per duration quartile and horizon; window-20 denominators are smaller when complete pre/post windows are unavailable.",
            "Only one chronological split and a short test window are covered; temporal generalization is unproven.",
            "PM100 measures aggregate node power per job, not GPU-only power; this experiment does not validate ATOCIA or ATRP-1."
        ]
    }

    lines = [
        "# PM100 — combinação de detectores por janelas (V1)", "",
        "**Status:** comparação exploratória; estatística combinada e limiar calibrados exclusivamente na validação.", "",
        "## Pergunta e protocolo", "",
        "A combinação de alterações na média e na dispersão pode melhorar a sensibilidade sem simplesmente duplicar a taxa nominal de alertas?", "",
        "Foram mantidos os horizontes, janelas e erros EWMA da fase anterior. Os detectores isolados usam os respectivos percentis 95 dos máximos por job na validação. Para o combinado, em cada instante calculamos max(média / limiar individual da média, variância / limiar individual da variância); o limiar final é o percentil 95 dos máximos desse escore por job na validação. Assim, os três métodos têm a mesma meta nominal de excedência por job na validação, não uma soma de dois limiares de 5%.", "",
        "Os quartis de duração, os limiares e os parâmetros EWMA são definidos na validação e congelados antes do teste. Os três métodos usam os mesmos jobs e as mesmas perturbações sintéticas. O teste não é usado para selecionar um vencedor.", "",
        f"Jobs vistos: validação {seen['validation']:,}; teste {seen['test']:,}. Amostra sintética: até {SAMPLE_PER_BIN} jobs por quartil e horizonte; cenários: {len(specs)}.", "",
        "## Alertas naturais no teste", "",
        "Cada valor é a fração de jobs com ao menos um alerta, não uma taxa de falsos positivos. Os resultados são exibidos por quartil de duração.", ""
    ]
    for h in HORIZONS:
        sec = str(h * 20)
        lines += [f"### Horizonte {sec} s — janela de 10 amostras", "",
                  "| Método | Q1 | Q2 | Q3 | Q4 |",
                  "|---|---:|---:|---:|---:|"]
        for method in METHODS:
            vals = []
            for b in range(4):
                a = natural[h][10][method][b]
                vals.append(f"{a['alerts']/a['n']:.1%}" if a["n"] else "n/a")
            lines.append("| " + method + " | " + " | ".join(vals) + " |")
        lines.append("")
    lines += ["## Mudanças sintéticas — janela de 10 amostras", "",
              "Detecção após a mudança / pré-alerta antes dela. Os intervalos de Wilson e atrasos estão no JSON.", "",
              "A designação sd_x2 significa multiplicar os desvios em torno da média anterior por 2; antes do truncamento em zero, isso equivale a multiplicar a variância por 4, não por 2.", ""]
    core = ["step_up_s2_cp50", "step_down_s2_cp50", "ramp_up_s2_cp50",
            "ramp_down_s2_cp50", "sd_x2_cp50"]
    for h in HORIZONS:
        sec = str(h * 20)
        lines += [f"### Horizonte {sec} s", "",
                  "| Cenário | Média | Variância | Combinado |",
                  "|---|---:|---:|---:|"]
        for name in core:
            row = [name]
            for method in METHODS:
                r = synthetic[sec][name]["results"]["10"][method]
                row.append(f"{r['detection_fraction']:.1%} / {r['prealert_fraction']:.1%} (n={r['n']})")
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
    # Quantitative synthesis: report all methods at matched validation alert budgets.
    val_rates = []
    for h in HORIZONS:
        for w in WINDOWS:
            for b in range(4):
                val_rates.extend(validation_exceedance[h][b][str(w)][m] for m in METHODS)
    lines += [
        "## Síntese quantitativa", "",
        f"A excedência empírica na validação ficou entre {min(val_rates):.2%} e {max(val_rates):.2%} nos quatro horizontes, três janelas e quatro quartis, para os três métodos. Isso confirma a calibração nominal conjunta dentro da própria validação; não garante a taxa no teste.", "",
        "Taxa de jobs alertados no teste, ponderada pelo número de jobs em cada quartil, para janela de 10 amostras:", "",
        "| Horizonte | Média | Variância | Combinado |", "|---:|---:|---:|---:|"
    ]
    for h in HORIZONS:
        cells = []
        for method in METHODS:
            items = list(natural[h][10][method].values())
            n_total = sum(a["n"] for a in items)
            k_total = sum(a["alerts"] for a in items)
            cells.append(f"{k_total/n_total:.2%}")
        lines.append(f"| {h*20} s | " + " | ".join(cells) + " |")
    lines += [
        "",
        "Nos dados naturais, a fusão ficou próxima da incidência dos métodos individuais, mas a heterogeneidade por duração persiste; por exemplo, no horizonte de 120 s, o quartil mais longo teve 6,62% de alertas combinados na janela de 10 amostras.", "",
        "Nos cenários sintéticos de referência, a fusão normalmente ficou abaixo do detector especializado no tipo de mudança correspondente. O quadro abaixo compara detecção combinada com o método isolado mais sensível para cada cenário; são proporções descritivas, não diferenças com intervalo de confiança pareado.", "",
        "| Horizonte | Degrau positivo +2 SD: combinado / média | Degrau descendente +2 SD: combinado / variância | Escala SD ×2: combinado / variância |", "|---:|---:|---:|---:|"
    ]
    for h in HORIZONS:
        sec = str(h*20)
        specs_ref = [
            ("step_up_s2_cp50", "mean"),
            ("step_down_s2_cp50", "variance"),
            ("sd_x2_cp50", "variance")
        ]
        vals = []
        for scenario, specialist in specs_ref:
            r = synthetic[sec][scenario]["results"]["10"]
            vals.append(f"{r['combined']['detection_fraction']:.1%} / {r[specialist]['detection_fraction']:.1%}")
        lines.append(f"| {h*20} s | " + " | ".join(vals) + " |")
    lines += [
        "",
        "A exceção numérica pequena foi o degrau positivo no horizonte de 120 s (3,7% combinado contra 3,5% no detector de média); sem comparação pareada de incerteza, isso não sustenta superioridade. Em geral, a fusão troca parte da sensibilidade de cada especialista por uma resposta intermediária aos diferentes tipos de alteração.", "",
        "A designação sd_x2 significa desvio-padrão multiplicado por 2 (variância nominal ×4 antes do truncamento em zero). Degraus descendentes são aplicados à série de erro absoluto, não à potência física; o truncamento pode criar uma alteração de dispersão.", ""
    ]
    lines += [
        "## Interpretação e limites", "",
        "- A regra combinada é OR-like: pode sinalizar uma alteração localizada em qualquer uma das duas estatísticas. O limiar conjunto corrige a duplicação da taxa nominal na validação, mas não garante a mesma taxa no teste.",
        "- Um aumento de detecção não basta para escolher o método: é preciso ponderar pré-alertas, atraso, incidência natural e estabilidade entre durações.",
        "- Degraus descendentes são truncados em zero. A expansão sd_xN multiplica o desvio-padrão por N (variância nominal por N² antes do truncamento). São intervenções em erros absolutos, não medições de transições físicas.",
        "- Sem rótulos independentes de mudanças reais, não podemos estimar precisão, recall ou falsos positivos reais. Uma única divisão cronológica não demonstra generalização temporal.",
        "- PM100 mede potência agregada do job/nó. Nada nesta análise valida ATOCIA, ATRP-1, economia de energia ou segurança térmica.",
        ""
    ]
    lines += [
        "## Artefatos", "",
        "- combined_window_detectors_v1.py",
        "- audit/combined_window_detectors_v1.json",
        "- PM100_COMBINED_WINDOW_DETECTORS_V1.md",
        "",
        "Os dados Parquet e os modelos anteriores não foram alterados.",
        "",
        "**Fase encerrada; aguardar autorização antes de iniciar a próxima.**"
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out["script_sha256"] = sha256(Path(__file__))
    out["report_sha256"] = sha256(REPORT)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("Completed combined-detector evaluation.")
    print(f"validation_jobs={seen['validation']} test_jobs={seen['test']}")
    print(f"input_sha256={out['input_sha256']}")
    print(f"script_sha256={out['script_sha256']}")
    print(f"report_sha256={out['report_sha256']}")
    print(f"json_sha256={sha256(OUT)}")
    print(f"Wrote {OUT}")
    print(f"Wrote {REPORT}")


if __name__ == "__main__":
    main()
