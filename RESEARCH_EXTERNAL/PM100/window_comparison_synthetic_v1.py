#!/usr/bin/env python3
"""Window-comparison change detectors with frozen validation thresholds and synthetic tests."""
from __future__ import annotations
import json, hashlib, math
from pathlib import Path
import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "job_table.parquet"
BASE = ROOT / "audit" / "trajectory_online_models_v2.json"
OUT = ROOT / "audit" / "window_comparison_synthetic_v1.json"
REPORT = ROOT / "PM100_WINDOW_COMPARISON_SYNTHETIC_V1.md"
HORIZONS = (1, 2, 3, 6)
WINDOWS = (5, 10, 20)
KINDS = ("mean", "variance")
MIN_FORECASTS = 41
TARGET_TAIL = 0.05
SAMPLE_PER_BIN = 250
SEED = 20261123
SAMPLE_SECONDS = 20.0


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
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
    s_prev = cs[ends - w] - cs[ends - 2 * w]
    s_recent = cs[ends] - cs[ends - w]
    q_prev = cs2[ends - w] - cs2[ends - 2 * w]
    q_recent = cs2[ends] - cs2[ends - w]
    m_prev, m_recent = s_prev / w, s_recent / w
    v_prev = np.maximum((q_prev - s_prev * s_prev / w) / max(w - 1, 1), 0.0)
    v_recent = np.maximum((q_recent - s_recent * s_recent / w) / max(w - 1, 1), 0.0)
    mean_stat = np.abs(m_recent - m_prev) / np.sqrt((v_prev + v_recent) / w + 1.0)
    variance_stat = np.abs(np.log((v_recent + 1.0) / (v_prev + 1.0)))
    return mean_stat, variance_stat


def qhigher(values, q):
    return float(np.quantile(np.asarray(values, dtype=np.float64), q, method="higher"))


def bin_index(n, edges):
    return int(np.searchsorted(edges, n, side="right"))


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
                        "magnitude": mag, "cp_fraction": 0.50})
    for shape in ("step_up", "step_down", "ramp_up", "ramp_down"):
        for frac in (0.25, 0.75):
            out.append({"name": f"{shape}_s2_cp{int(frac*100)}", "shape": shape,
                        "magnitude": 2.0, "cp_fraction": frac})
    for mult in (1.5, 2.0, 3.0):
        out.append({"name": f"variance_x{mult:g}_cp50", "shape": "scale_sd",
                    "sd_multiplier": mult, "cp_fraction": 0.50})
    for frac in (0.25, 0.75):
        out.append({"name": f"variance_x2_cp{int(frac*100)}", "shape": "scale_sd",
                    "sd_multiplier": 2.0, "cp_fraction": frac})
    return out


def perturb(e, w, spec):
    n = len(e)
    frac = float(spec["cp_fraction"])
    cp = 2 * w + int(round(frac * (n - 4 * w)))
    if cp <= 0 or n - cp < 2 * w:
        return None, None
    ref = e[cp - w:cp]
    center = float(np.mean(ref))
    scale = max(float(np.std(ref, ddof=1)), 1.0)
    y = e.copy()
    shape = spec["shape"]
    if shape in ("step_up", "step_down"):
        delta = float(spec["magnitude"]) * scale
        signed = delta if shape == "step_up" else -delta
        y[cp:] = np.maximum(0.0, y[cp:] + signed)
    elif shape in ("ramp_up", "ramp_down"):
        delta = float(spec["magnitude"]) * scale
        signed = delta if shape == "ramp_up" else -delta
        ramp_n = min(n - cp, max(2 * w, int(math.ceil(0.5 * (n - cp)))))
        ramp = np.linspace(0.0, signed, ramp_n, endpoint=True, dtype=np.float64)
        y[cp:cp + ramp_n] = np.maximum(0.0, y[cp:cp + ramp_n] + ramp)
        if cp + ramp_n < n:
            y[cp + ramp_n:] = np.maximum(0.0, y[cp + ramp_n:] + signed)
    elif shape == "scale_sd":
        # Legacy scenario names say variance_xN; N actually scales SD, so variance scales by N^2 before clipping.
        mult = float(spec["sd_multiplier"])
        y[cp:] = np.maximum(0.0, center + mult * (y[cp:] - center))
    else:
        raise ValueError(shape)
    return y, cp


def first_cross(path, threshold, w):
    ix = np.flatnonzero(path > threshold)
    return int(2 * w + ix[0]) if len(ix) else None


def main():
    base = json.loads(BASE.read_text(encoding="utf-8"))
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

    paired = {h: [] for h in HORIZONS}
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
                row["maxima"][str(w)] = {"mean": float(np.max(mp)),
                                         "variance": float(np.max(vp))}
            paired[h].append(row)

    calibration, thresholds = {}, {}
    for h in HORIZONS:
        ns = [r["n"] for r in paired[h]]
        edges = [qhigher(ns, q) for q in (0.25, 0.50, 0.75)]
        calibration[h] = {"duration_bin_edges_forecasts": edges, "bins": {}}
        thresholds[h] = {w: {} for w in WINDOWS}
        for b in range(4):
            calibration[h]["bins"][str(b)] = {}
            for w in WINDOWS:
                calibration[h]["bins"][str(b)][str(w)] = {}
                for kind in KINDS:
                    vals = [r["maxima"][str(w)][kind] for r in paired[h]
                            if bin_index(r["n"], edges) == b]
                    threshold = qhigher(vals, 1.0 - TARGET_TAIL) if vals else None
                    thresholds[h][w][kind, b] = threshold
                    calibration[h]["bins"][str(b)][str(w)][kind] = {
                        "validation_jobs": len(vals), "threshold_q95": threshold
                    }

    natural = {h: {w: {k: {b: {"n": 0, "alerts": 0, "delays": []} for b in range(4)}
                          for k in KINDS} for w in WINDOWS} for h in HORIZONS}
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
                for kind, path in (("mean", mp), ("variance", vp)):
                    a = natural[h][w][kind][b]
                    a["n"] += 1
                    end = first_cross(path, thresholds[h][w][kind, b], w)
                    if end is not None:
                        a["alerts"] += 1
                        a["delays"].append((end - 2 * w) * SAMPLE_SECONDS)
            reservoir_seen[h][b] += 1
            bucket = reservoirs[h][b]
            if len(bucket) < SAMPLE_PER_BIN:
                bucket.append(e.copy())
            else:
                j = int(rng.integers(0, reservoir_seen[h][b]))
                if j < SAMPLE_PER_BIN:
                    bucket[j] = e.copy()

    specs = scenarios()
    synthetic = {}
    for h in HORIZONS:
        sec_key = str(h * 20)
        synthetic[sec_key] = {}
        for spec in specs:
            synthetic[sec_key][spec["name"]] = {"spec": spec, "results": {}}
            for w in WINDOWS:
                synthetic[sec_key][spec["name"]]["results"][str(w)] = {}
                for kind in KINDS:
                    synthetic[sec_key][spec["name"]]["results"][str(w)][kind] = {
                        "n": 0, "detected": 0, "prealert": 0, "delays_s": [],
                        "by_duration_bin": {str(b): {"n": 0, "detected": 0, "prealert": 0, "delays_s": []}
                                            for b in range(4)}
                    }
        for b in range(4):
            for e in reservoirs[h][b]:
                for spec in specs:
                    for w in WINDOWS:
                        changed, cp = perturb(e, w, spec)
                        if changed is None:
                            continue
                        mp, vp = window_paths(changed, w)
                        for kind, path in (("mean", mp), ("variance", vp)):
                            result = synthetic[sec_key][spec["name"]]["results"][str(w)][kind]
                            by = result["by_duration_bin"][str(b)]
                            end = first_cross(path, thresholds[h][w][kind, b], w)
                            for item in (result, by):
                                item["n"] += 1
                            if end is not None:
                                if end <= cp:
                                    for item in (result, by):
                                        item["prealert"] += 1
                                else:
                                    delay = (end - cp) * SAMPLE_SECONDS
                                    for item in (result, by):
                                        item["detected"] += 1
                                        item["delays_s"].append(delay)

    for h in HORIZONS:
        for spec in specs:
            for w in WINDOWS:
                for kind in KINDS:
                    r = synthetic[str(h * 20)][spec["name"]]["results"][str(w)][kind]
                    r["detection_fraction"] = r["detected"] / r["n"] if r["n"] else None
                    r["detection_wilson95"] = wilson(r["detected"], r["n"])
                    r["prealert_fraction"] = r["prealert"] / r["n"] if r["n"] else None
                    r["median_detection_delay_s"] = float(np.median(r["delays_s"])) if r["delays_s"] else None
                    del r["delays_s"]
                    for by in r["by_duration_bin"].values():
                        by["detection_fraction"] = by["detected"] / by["n"] if by["n"] else None
                        by["detection_wilson95"] = wilson(by["detected"], by["n"])
                        by["prealert_fraction"] = by["prealert"] / by["n"] if by["n"] else None
                        by["median_detection_delay_s"] = float(np.median(by["delays_s"])) if by["delays_s"] else None
                        del by["delays_s"]

    natural_out = {}
    for h in HORIZONS:
        sec_key = str(h * 20)
        natural_out[sec_key] = {}
        for w in WINDOWS:
            natural_out[sec_key][str(w)] = {}
            for kind in KINDS:
                bins = {}
                for b, a in natural[h][w][kind].items():
                    bins[str(b)] = {
                        "test_jobs": a["n"], "alert_jobs": a["alerts"],
                        "alert_fraction": a["alerts"] / a["n"] if a["n"] else None,
                        "median_alert_delay_s": float(np.median(a["delays"])) if a["delays"] else None
                    }
                natural_out[sec_key][str(w)][kind] = {"by_duration_bin": bins}

    out = {
        "dataset": "PM100 v1",
        "input_sha256": sha256(INPUT),
        "baseline_v2_sha256": sha256(BASE),
        "target": "job-level aggregate node power, not GPU-only",
        "split": "chronological 70/85% start_time; validation defines duration bins and thresholds; test is held out",
        "ewma_alpha_frozen_from_v2": {str(h * 20): alphas[h] for h in HORIZONS},
        "protocol": {
            "sampling_interval_s": SAMPLE_SECONDS,
            "windows_samples": list(WINDOWS),
            "windows_seconds": [int(w * SAMPLE_SECONDS) for w in WINDOWS],
            "statistics": {
                "mean": "absolute difference of adjacent-window means divided by sqrt((s2_prev+s2_recent)/w + 1 W^2)",
                "variance": "absolute log ratio of adjacent-window sample variances, each regularized by +1 W^2"
            },
            "threshold": "per-job maximum statistic q95 on validation, separately by horizon, window, statistic, and duration quartile",
            "duration_bins": "four validation forecast-count quartiles",
            "synthetic": "test error series altered with upward/downward persistent steps, gradual ramps, and variance expansion; three intensities and multiple changepoint positions",
            "synthetic_sample_per_duration_bin_per_horizon": SAMPLE_PER_BIN,
            "synthetic_minimum_forecasts_by_window": {str(w): max(MIN_FORECASTS, 4 * w) for w in WINDOWS},
            "synthetic_seed": SEED,
            "minimum_forecasts": MIN_FORECASTS,
            "nominal_validation_tail": TARGET_TAIL
        },
        "jobs_seen": seen,
        "duration_calibration": calibration,
        "natural_test_alerts": natural_out,
        "synthetic_scenarios": synthetic,
        "synthetic_sample_counts_by_horizon_bin": {
            str(h * 20): {str(b): len(reservoirs[h][b]) for b in range(4)} for h in HORIZONS
        },
        "limitations": [
            "Synthetic perturbations are applied to absolute forecast-error series, not raw power traces.",
            "Downward changes are clipped at zero because absolute errors cannot be negative; this changes their distribution.",
            "The 20-sample synthetic comparisons require at least 80 errors to place full pre- and post-change windows; their denominator is smaller than for 5- and 10-sample windows.",
            "Variance expansions are applied around the preceding-window mean and clipped at zero.",
            "Natural test alerts have no independent changepoint labels; they cannot be classified as true or false positives.",
            "Window thresholds are calibrated on validation job maxima and are not guaranteed to yield 5% alert rates on future data.",
            "Different window sizes and statistics are parallel candidate detectors; this test set is not used to select a final winner.",
            "Only one chronological split and a short test window are covered; temporal generalization remains unproven.",
            "Forecast errors are from EWMA models and PM100 measures aggregate node power, not GPU-only power.",
            "This experiment does not validate ATOCIA or ATRP-1."
        ]
    }

    lines = [
        "# PM100 — detectores por comparação de janelas e mudanças sintéticas (V1)", "",
        "**Status:** comparação exploratória com limiares congelados na validação; intervenções sintéticas não são mudanças físicas observadas.", "",
        "## Pergunta", "",
        "Comparar duas janelas adjacentes do erro absoluto da EWMA consegue sinalizar alterações de nível ou dispersão com mais sensibilidade e menor atraso que os detectores cumulativos explorados antes?", "",
        "## Protocolo", "",
        "Foram avaliadas janelas de 5, 10 e 20 amostras (100, 200 e 400 s). A estatística de média compara a diferença entre médias adjacentes, normalizada pela variabilidade observada nas duas janelas. A estatística de variância compara o logaritmo da razão entre variâncias adjacentes. Cada limiar é o percentil 95 dos máximos por job na validação, separado por horizonte, largura, estatística e quartil de duração. Tudo foi congelado antes do teste.", "",
        "No teste natural, medimos incidência de alertas por quartil. Para os testes sintéticos, foi usada uma amostra reprodutível de até 250 jobs por quartil e horizonte. Foram injetados degraus para cima/baixo, rampas graduais e expansão de variância; intensidades e posições de mudança são discriminadas no JSON. Um alerta antes do ponto injetado é contado como pré-alerta, não como detecção.", "",
        f"Jobs vistos: validação {seen['validation']:,}; teste {seen['test']:,}. Amostras sintéticas por horizonte/quartil: até {SAMPLE_PER_BIN}.", "",
        "## Alertas naturais no teste", "",
        "Percentuais por quartil de duração. São incidências de alerta, não taxas de falso positivo, pois não há rótulos independentes.", ""
    ]
    for h in HORIZONS:
        sec = h * 20
        lines += [f"### Horizonte {sec} s", "",
                  "| Estatística | Janela | Q1 | Q2 | Q3 | Q4 |",
                  "|---|---:|---:|---:|---:|---:|"]
        for w in WINDOWS:
            for kind in KINDS:
                vals = []
                for b in range(4):
                    a = natural[h][w][kind][b]
                    vals.append(f"{a['alerts']/a['n']:.1%}" if a["n"] else "n/a")
                lines.append(f"| {kind} | {w} ({w*20}s) | " + " | ".join(vals) + " |")
        lines.append("")
    lines += ["## Testes sintéticos no ponto médio", "",
              "Cada célula mostra detecção após a mudança / pré-alerta antes dela. O JSON contém ICs de Wilson de 95%, medianas de atraso, resultados por quartil e cenários nas posições 25%, 50% e 75%.",
              "Na janela de 20 amostras, a amostra efetiva cai para n=842–846 porque são necessários ao menos 80 erros para posicionar duas janelas completas antes e depois da mudança. Nas janelas de 5 e 10 amostras, n=1.000. O teto de 250 por quartil não garante 250 casos elegíveis em todas as configurações.", ""]
    main_specs = ["step_up_s2_cp50", "step_down_s2_cp50", "ramp_up_s2_cp50",
                  "ramp_down_s2_cp50", "variance_x2_cp50"]
    for h in HORIZONS:
        sec = h * 20
        lines += [f"### Horizonte {sec} s", "",
                  "| Estatística | Janela | Degrau +2σ | Degrau −2σ | Rampa +2σ | Rampa −2σ | Variância ×2 |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for w in WINDOWS:
            for kind in KINDS:
                cells = []
                for name in main_specs:
                    r = synthetic[str(sec)][name]["results"][str(w)][kind]
                    if r["n"]:
                        cells.append(f"{r['detection_fraction']:.1%} / {r['prealert_fraction']:.1%} (n={r['n']})")
                    else:
                        cells.append("n/a")
                lines.append(f"| {kind} | {w} ({w*20}s) | " + " | ".join(cells) + " |")
        lines.append("")
    lines += [
        "## Leitura e limites", "",
        "- Comparações de janelas detectam mudanças locais; a janela mais longa tende a exigir mais observações após a mudança, enquanto a janela curta pode responder mais rápido e oscilar mais.",
        "- A calibração por quartil reduz uma fonte conhecida de heterogeneidade, mas as taxas de alerta no teste devem ser lidas diretamente; não se presume que permaneçam em 5%.",
        "- O teste sintético avalia somente a mecânica dos detectores sobre erros absolutos observados. Não comprova que os mesmos padrões ocorram no consumo de energia real nem que alertas naturais indiquem mudanças verdadeiras.",
        "- Degraus descendentes são truncados em zero; expansões de variância também são centradas na janela anterior e truncadas em zero. Essas perturbações não reproduzem perfeitamente processos físicos.",
        "- Não foi escolhido um vencedor com base no teste. Uma escolha operacional exigiria critérios prévios, rótulos independentes e validação temporal em períodos adicionais.",
        "- PM100 mede potência agregada por job/nó, não potência exclusivamente da GPU. Nada nesta fase valida ATOCIA ou ATRP-1.",
        "",
        "## Artefatos", "",
        "- window_comparison_synthetic_v1.py",
        "- audit/window_comparison_synthetic_v1.json",
        "- PM100_WINDOW_COMPARISON_SYNTHETIC_V1.md",
        "",
        "O Parquet original, resultados V2, ATRP-1 e relatórios anteriores não foram alterados.",
        "",
        "**Fase encerrada; aguardar autorização antes da próxima.**"
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out["script_sha256"] = sha256(Path(__file__))
    out["report_sha256"] = sha256(REPORT)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("Completed window-comparison evaluation.")
    print(f"validation_jobs={seen['validation']} test_jobs={seen['test']}")
    print(f"input_sha256={out['input_sha256']}")
    print(f"script_sha256={out['script_sha256']}")
    print(f"report_sha256={out['report_sha256']}")
    print(f"json_sha256={sha256(OUT)}")
    print(f"Wrote {OUT}")
    print(f"Wrote {REPORT}")


if __name__ == "__main__":
    main()
