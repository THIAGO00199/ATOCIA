# ATOCIA — temporal intelligence for computing infrastructure

Research and development of methods to observe, model, and anticipate power variations and thermal dynamics in computing systems, with a long-term focus on GPUs, AI clusters, and HPC.

**Status:** research laboratory and experimental prototypes. This is not a data-center controller or a production-ready system.

## Two related but distinct technical tracks

### 1. ATRP-1 — GPU power forecasting

A first lightweight forecasting model has been implemented and evaluated to estimate GPU power 15 seconds ahead using historical power, temperature, and utilization telemetry.

- Huber Ridge with a residual correction over persistence.
- 13 causal features derived from the previous three samples.
- Trained on Kalos cluster windows, with the hyperparameter selected only on validation data.
- Frozen model artifact verified by hash before evaluation.

**Recorded results for the same frozen model:**

| Evaluation | MAE reduction vs. persistence | RMSE reduction |
|---|---:|---:|
| Kalos, temporal holdout 30 Aug | 23.54% | 29.53% |
| Kalos, temporal holdout 31 Aug | 20.92% | 27.41% |
| Seren, zero-shot transfer | 0.88% | 13.75% |

Both Kalos temporal holdouts retained positive MAE improvement in the reanalysis that accounts for temporal and host dependence. In Seren, the MAE improvement is small and confidence intervals cross zero; there is no convincing evidence of a gain on this metric across clusters. The RMSE reduction is a separate observation and does not change that conclusion.

**Interpretation:** the results show a promising temporal signal within Kalos; cross-cluster transfer remains the main challenge. They do not demonstrate generalization to other architectures, energy savings, cost reduction, thermal safety, or operational readiness.

### 2. Local thermal physics and instrumentation

- Passive Linux telemetry collectors for available power, temperature, frequency, and system state.
- A conventional RC thermal baseline and offline mathematical tests.
- Repeated load-and-recovery observations on a single Intel laptop.
- 38 offline tests passed in the local suite verified on 25 Nov 2026.

Local experiments show a repeatable qualitative response of package power and temperature to short CPU pulses. They do not yet robustly identify the physical thermal parameters: ambient temperature, fan behavior, and other variables are not sufficiently observed. This track does not validate GPU behavior in a rack or data center.

### 3. Exploratory external benchmarks

The research also includes analyses of job-level aggregated telemetry and power-change detection. In the PM100 V2 analysis, interventions are synthetic: incremental detection is modest for mean-only changes and more noticeable in some variance/dispersion and mixed-shift scenarios. Absolute rates remain low in the selected scenarios. There are no labels for real physical changes and no evidence of operational suitability.

## Relationship to TDT

Temporal Debt Theory (TDT) is a research hypothesis related to the project's conceptual motivation. The mathematical connection between TDT and the thermal or forecasting models has not been established. The RC and ATRP-1 models must be evaluated using their own assumptions, baselines, and metrics; their results should not be attributed to TDT.

## Validation architecture

1. Observational instrumentation and signal-quality audits.
2. Simple baselines and reduced-order physical models.
3. Forecasting with temporal evaluation against persistence.
4. Tests for transfer, missing sensors, irregular sampling, and unseen regimes.
5. Simulation and shadow mode before any operational recommendation.

No hardware control is enabled. Local collectors are observational and do not change power limits, frequency, governor, EPP, fans, firmware, or services.

## Start here

- `RESEARCH_EXTERNAL/ATRP1_EXECUTIVE_SUMMARY_2026-11-22.md` — experimental question, model, and results.
- `RESEARCH_EXTERNAL/ATRP1_DEPENDENCE_AWARE_REANALYSIS_2026-11-22.md` — intervals accounting for temporal and host dependence.
- `MODEL_V1/ATRP1_SPEC.md` — model specification.
- `MODEL_V1/EXPERIMENT_PROTOCOL_V1.md` — evaluation and leakage-prevention protocol.
- `THERMAL_PHYSICS_BASELINE_V1.md` — local physical baseline and assumptions.
- `RESEARCH_EXTERNAL/PM100/PM100_RAW_POWER_CHANGE_DETECTION_V2.md` — synthetic-intervention detection benchmark.

## Data, reproducibility, and attribution

External benchmarks use datasets published by third parties. Derived panels, raw files, and complete datasets must not be redistributed automatically. Any release must preserve attribution, license terms, and dataset provenance. Treat scripts, derived results, and original data as separate materials.

Previously observed holdouts must not be reused as untouched test sets when selecting future variants. New versions require independent training/validation splits and a separate holdout.

---

[Português](README.md) · [Español](README.es.md)

## Public repository data policy

Raw local telemetry captures, collector logs, complete third-party datasets, and source metadata dumps are intentionally not included in this public repository. See DATA_PROVENANCE.md for dataset attribution and redistribution notes.
