#!/usr/bin/env python3
"""Exploratory causal change detection on PM100 online EWMA forecast errors.

Per job and horizon, the first five realized absolute forecast errors establish
an initial reference level. CUSUM and one-sided Page-Hinkley then monitor
standardized positive deviations. Thresholds are calibrated on validation
job-level maximum statistics (95th percentile) and frozen before test.
This is exploratory alerting, not ground-truth changepoint validation.
"""
from __future__ import annotations
import json, hashlib, math
from pathlib import Path
import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "job_table.parquet"
BASELINE_JSON = ROOT / "audit" / "trajectory_online_models_v2.json"
OUT_JSON = ROOT / "audit" / "error_change_detection_v1.json"
OUT_MD = ROOT / "PM100_ERROR_CHANGE_DETECTION_V1.md"
HORIZONS = (1, 2, 3, 6)
BASELINE_N = 5
MIN_FORECASTS = 15
CUSUM_K = 0.50
PH_DELTA = 0.25
TARGET_TAIL = 0.05

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def split_for(start, end, val_cut, test_cut):
    a, b = start.timestamp(), end.timestamp()
    if b < val_cut: return "train"
    if a >= val_cut and b < test_cut: return "validation"
    if a >= test_cut: return "test"
    return "overlap"

def scan(con, rel, val_cut, test_cut, split):
    cur = con.execute(
        f"SELECT start_time,end_time,num_gpus_alloc,num_nodes_alloc,power_consumption "
        f"FROM {rel} WHERE num_gpus_alloc>0 AND start_time IS NOT NULL "
        f"AND end_time IS NOT NULL ORDER BY start_time"
    )
    while True:
        batch = cur.fetchmany(256)
        if not batch: break
        for start, end, gpus, nodes, seq in batch:
            if split_for(start, end, val_cut, test_cut) != split: continue
            if seq is None or len(seq) < 6 or any(v is None for v in seq): continue
            x = np.asarray(seq, dtype=np.float64)
            if not np.isfinite(x).all(): continue
            yield x

def error_series(x, horizon, alpha):
    n = len(x) - horizon - 4
    if n < MIN_FORECASTS: return None
    t = np.arange(4, len(x) - horizon)
    s = np.empty(len(x), dtype=np.float64)
    s[0] = x[0]
    for i in range(1, len(x)):
        s[i] = alpha * x[i] + (1.0 - alpha) * s[i-1]
    return np.abs(x[t + horizon] - s[t])

def detector_maxima(errors):
    # Initial reference uses only the first five realized errors.
    ref = errors[:BASELINE_N]
    center = float(np.mean(ref))
    scale = max(float(np.std(ref, ddof=1)), 1.0)
    z = (errors[BASELINE_N:] - center) / scale
    if len(z) == 0: return None
    c = 0.0
    cmax = 0.0
    cpath = []
    ph_sum = 0.0
    ph_min = 0.0
    ph_mean = 0.0
    ph_n = 0
    phmax = 0.0
    ppath = []
    for v in z:
        value = float(v)
        c = max(0.0, c + value - CUSUM_K)
        cmax = max(cmax, c)
        cpath.append(c)
        ph_n += 1
        ph_mean += (value - ph_mean) / ph_n
        ph_sum += value - ph_mean - PH_DELTA
        ph_min = min(ph_min, ph_sum)
        ph_stat = ph_sum - ph_min
        phmax = max(phmax, ph_stat)
        ppath.append(ph_stat)
    return cmax, phmax, center, scale, len(z), np.asarray(cpath), np.asarray(ppath)

def percentile_higher(a, q):
    return float(np.quantile(np.asarray(a, dtype=np.float64), q, method="higher"))

def main():
    baseline = json.loads(BASELINE_JSON.read_text(encoding="utf-8"))
    alphas = {1: float(baseline["horizons_seconds"]["20"]["selected_validation"]["ewma_alpha"]),
              2: float(baseline["horizons_seconds"]["40"]["selected_validation"]["ewma_alpha"]),
              3: float(baseline["horizons_seconds"]["60"]["selected_validation"]["ewma_alpha"]),
              6: float(baseline["horizons_seconds"]["120"]["selected_validation"]["ewma_alpha"])}
    con = duckdb.connect(":memory:", config={"threads":"1", "memory_limit":"512MB"})
    src = str(INPUT.resolve()).replace("'", "''")
    rel = f"read_parquet('{src}')"
    val_cut, test_cut = con.execute(
        f"SELECT quantile_cont(epoch(start_time),.70), "
        f"quantile_cont(epoch(start_time),.85) FROM {rel} "
        "WHERE num_gpus_alloc>0 AND start_time IS NOT NULL"
    ).fetchone()

    records = {split: {h: [] for h in HORIZONS} for split in ("validation", "test")}
    jobs_seen = {"validation": 0, "test": 0}
    for split in ("validation", "test"):
        for x in scan(con, rel, val_cut, test_cut, split):
            jobs_seen[split] += 1
            for h in HORIZONS:
                e = error_series(x, h, alphas[h])
                if e is None: continue
                vals = detector_maxima(e)
                if vals is not None:
                    cmax, phmax, center, scale, monitored, cpath, ppath = vals
                    rec = {
                        "cusum_max": cmax, "ph_max": phmax,
                        "initial_mae": center, "initial_sd": scale,
                        "monitored_points": monitored,
                        "forecasts": int(len(e))
                    }
                    if split == "test":
                        rec["_cusum_path"] = cpath
                        rec["_ph_path"] = ppath
                    records[split][h].append(rec)

    result = {
        "dataset": "PM100 v1",
        "input_sha256": sha256(INPUT),
        "baseline_result_sha256": sha256(ROOT / "audit" / "trajectory_online_models_v2.json"),
        "question": "Can causal one-sided detectors flag sustained increases in absolute EWMA forecast error within a job?",
        "target": "job-level aggregate node input power (W), not GPU-only",
        "split": "same chronological 70/85% start_time split as V2; train excluded; validation calibrates thresholds; test evaluated with frozen thresholds",
        "ewma_alphas_frozen_from_v2_validation": {str(h*20): alphas[h] for h in HORIZONS},
        "detector": {
            "reference": f"first {BASELINE_N} realized absolute forecast errors per job",
            "standardization": "(absolute error - initial reference mean) / max(initial reference sample SD, 1 W)",
            "cusum_k": CUSUM_K,
            "page_hinkley_delta": PH_DELTA,
            "statistic": "CUSUM: fixed-reference one-sided recursion; Page-Hinkley: cumulative deviation from running mean minus delta, measured above its running minimum",
            "threshold_calibration": "95th percentile (higher empirical quantile) of validation per-job maximum statistic, separately for each detector and horizon",
            "nominal_validation_job_alert_fraction": TARGET_TAIL,
            "minimum_forecasts_per_job": MIN_FORECASTS
        },
        "jobs_seen": jobs_seen,
        "horizons": {}
    }
    lines = []
    lines += [
        "# PM100 — detecção exploratória de aumentos no erro online (V1)",
        "",
        f"**Data:** 23/11/2026  ",
        "**Status:** fase exploratória concluída; não é validação de ponto de mudança com rótulo de verdade-terreno.",
        "",
        "## Pergunta e protocolo",
        "",
        "A pergunta é se detectores unilaterais conseguem sinalizar aumentos persistentes no erro absoluto da EWMA durante um job. Para cada job e horizonte, os primeiros cinco erros absolutos realizados formam uma referência inicial. Depois, os erros são padronizados pela média e pelo desvio-padrão dessa referência (piso de 1 W). O CUSUM usa referência fixa; o Page-Hinkley acompanha a média acumulada e mede o desvio acumulado acima de seu mínimo.",
        "",
        "Os hiperparâmetros estruturais foram fixados antes do teste: CUSUM k=0,50; Page-Hinkley delta=0,25; mínimo de 15 previsões por job. Para cada horizonte e detector, o limiar é o percentil empírico superior de 95% dos máximos por job na validação. O limiar é congelado antes de avaliar o teste.",
        "",
        "A referência usa erros já realizados, portanto o alerta só pode ocorrer depois que os alvos correspondentes chegam. Não é previsão pré-execução nem detecção instantânea.",
        "",
        "## Cobertura"
    ]
    lines += [f"- Jobs elegíveis vistos na partição de validação: {jobs_seen['validation']:,}.",
              f"- Jobs elegíveis vistos na partição de teste: {jobs_seen['test']:,}.",
              f"- Requisito: pelo menos {MIN_FORECASTS} previsões por job e horizonte."]
    for h in HORIZONS:
        sec = h * 20
        v = records["validation"][h]
        t = records["test"][h]
        if not v or not t:
            result["horizons"][str(sec)] = {"error":"insufficient eligible jobs"}
            continue
        cthr = percentile_higher([r["cusum_max"] for r in v], 1-TARGET_TAIL)
        pthr = percentile_higher([r["ph_max"] for r in v], 1-TARGET_TAIL)
        cflags = [r for r in t if r["cusum_max"] > cthr]
        pflags = [r for r in t if r["ph_max"] > pthr]
        cdelays = [int(np.flatnonzero(r["_cusum_path"] > cthr)[0] + 1) for r in cflags]
        pdelays = [int(np.flatnonzero(r["_ph_path"] > pthr)[0] + 1) for r in pflags]
        def summary(flags, threshold, delays):
            return {
                "threshold": threshold,
                "test_alert_jobs": len(flags),
                "test_eligible_jobs": len(t),
                "test_alert_fraction": len(flags)/len(t),
                "median_monitored_points_to_alert_after_reference": float(np.median(delays)) if delays else None,
                "median_seconds_to_alert_after_reference": float(np.median(delays) * 20.0) if delays else None,
                "median_forecasts_among_alerted_jobs": float(np.median([r["forecasts"] for r in flags])) if flags else None,
                "median_total_forecasts_eligible": float(np.median([r["forecasts"] for r in t]))
            }
        item = {
            "validation_eligible_jobs": len(v),
            "test_eligible_jobs": len(t),
            "validation_cusum_threshold": cthr,
            "validation_page_hinkley_threshold": pthr,
            "cusum": summary(cflags, cthr, cdelays),
            "page_hinkley": summary(pflags, pthr, pdelays),
            "validation_cusum_empirical_exceedance_fraction": sum(r["cusum_max"] > cthr for r in v)/len(v),
            "validation_page_hinkley_empirical_exceedance_fraction": sum(r["ph_max"] > pthr for r in v)/len(v),
            "test_median_initial_reference_mae_W": float(np.median([r["initial_mae"] for r in t]))
        }
        result["horizons"][str(sec)] = item
        lines += [
            "",
            f"## Horizonte {sec} s",
            "",
            f"- Jobs elegíveis: validação {len(v):,}; teste {len(t):,}.",
            f"- Limiar CUSUM congelado: {cthr:.4f}; alertas no teste: {len(cflags):,}/{len(t):,} ({len(cflags)/len(t):.1%}).",
            f"- Limiar Page-Hinkley congelado: {pthr:.4f}; alertas no teste: {len(pflags):,}/{len(t):,} ({len(pflags)/len(t):.1%}).",
            f"- Atraso mediano após a referência: CUSUM {item['cusum']['median_seconds_to_alert_after_reference']} s; Page-Hinkley {item['page_hinkley']['median_seconds_to_alert_after_reference']} s.",
            f"- Previsões medianas por job entre os alertados: CUSUM {item['cusum']['median_forecasts_among_alerted_jobs']}; Page-Hinkley {item['page_hinkley']['median_forecasts_among_alerted_jobs']} (mediana de todos os elegíveis: {item['cusum']['median_total_forecasts_eligible']}).",
            f"- Fração de excedência na própria validação: CUSUM {item['validation_cusum_empirical_exceedance_fraction']:.1%}; Page-Hinkley {item['validation_page_hinkley_empirical_exceedance_fraction']:.1%}.",
            f"- MAE inicial mediana dos jobs elegíveis no teste: {item['test_median_initial_reference_mae_W']:.2f} W."
        ]
    result["limitations"] = [
        "No ground-truth changepoint labels exist in this experiment; a threshold crossing is an alert, not a verified regime change.",
        "Validation calibration targets an empirical 5% job-level exceedance on the same validation distribution; it is not a guaranteed false-positive rate on future data.",
        "Only one chronological split and a short test date window are used; temporal generalization remains unproven.",
        "The initial five realized errors can be unstable and may include startup behavior; the first five are a reference, not a known stationary regime.",
        "Absolute-error changes can reflect noise, job heterogeneity, load shape, or forecasting mismatch; they do not identify physical causes.",
        "The analysis uses EWMA parameters frozen in V2 and does not change ATOCIA or ATRP-1.",
        "PM100 target is aggregate node power per job, not GPU-only power; PM100 has no GPU temperature signal."
    ]
    lines += ["", "## Limitações", ""] + [f"- {x}" for x in result["limitations"]]
    lines += ["", "## Conclusão", "",
              "Os detectores foram avaliados como mecanismos de alerta de aumento persistente do erro, com limiares calibrados na validação. A taxa de alertas no teste deve ser interpretada como incidência de alertas, não como taxa de falsos positivos, pois não há rótulos independentes de mudança real. Sem rótulos ou intervenções controladas, não é possível afirmar precisão, recall ou atraso verdadeiro de detecção.",
              "",
              "O resultado desta fase serve para decidir se vale desenhar uma validação confirmatória com mudanças sintéticas controladas ou rótulos operacionais independentes. Não demonstra, por si só, que existem regimes físicos distintos.",
              "",
              "## Artefatos", "",
              "- Script: `detect_error_changes_v1.py`",
              "- Resultado integral: `audit/error_change_detection_v1.json`",
              "- Relatório: `PM100_ERROR_CHANGE_DETECTION_V1.md`",
              "",
              "O Parquet original, os resultados V2, os pesos ATRP-1 e os relatórios anteriores não foram alterados.",
              "",
              "**Fase encerrada; aguardar autorização antes de iniciar a próxima.**"]
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Wrote: {OUT_JSON}")
    print(f"Wrote: {OUT_MD}")

if __name__ == "__main__":
    main()
