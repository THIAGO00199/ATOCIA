# PM100 — calibração por duração e mudanças sintéticas (V1)

**Status:** experimento controlado; as mudanças injetadas são artificiais, não transições físicas observadas.

## Protocolo

Em cada horizonte, os quatro grupos de duração são definidos pelos quartis do número de previsões na validação. O limiar de cada detector é o percentil 95 dos máximos por job dentro de cada grupo. Grupos e limiares são congelados antes do teste.
No teste, também são injetados aumentos persistentes de +0,5, +1 e +2 desvios-padrão da referência inicial, na metade da sequência monitorada. Medimos detecção depois da mudança, alertas antes dela e atraso. Isso testa a mecânica do detector, não mudanças reais.
Jobs vistos: validação 17,998; teste 10,278.

## Horizonte 20 s

Quartis de duração (previsões): [36.0, 131.0, 410.0]

| Grupo | Val jobs | Test jobs | Alertas CUSUM | Alertas PH |
|---|---:|---:|---:|---:|
| Q1 (15–35) | 3603 | 1826 | 6.0% | 5.8% |
| Q2 (36–130) | 3652 | 2458 | 4.4% | 3.9% |
| Q3 (131–409) | 3647 | 2530 | 5.1% | 5.2% |
| Q4 (410–4317) | 3637 | 2327 | 5.2% | 5.4% |

**Perturbações sintéticas**

| Aumento | Jobs | Detect CUSUM | Detect PH | Pré-alerta CUSUM | Pré-alerta PH | Atraso CUSUM | Atraso PH |
|---:|---:|---:|---:|---:|---:|---:|---:|
| +0.5 SD | 7226 | 3.7% | 3.8% | 1.5% | 1.2% | 1220.0 | 1680.0 |
| +1.0 SD | 7226 | 3.9% | 4.0% | 1.5% | 1.2% | 1220.0 | 1640.0 |
| +2.0 SD | 7226 | 4.3% | 4.5% | 1.5% | 1.2% | 1380.0 | 1980.0 |

## Horizonte 40 s

Quartis de duração (previsões): [51.0, 163.0, 476.0]

| Grupo | Val jobs | Test jobs | Alertas CUSUM | Alertas PH |
|---|---:|---:|---:|---:|
| Q1 (15–50) | 3338 | 1656 | 2.4% | 2.8% |
| Q2 (51–162) | 3373 | 2517 | 5.1% | 4.3% |
| Q3 (163–475) | 3367 | 2277 | 6.0% | 5.9% |
| Q4 (476–4316) | 3364 | 2154 | 6.3% | 5.3% |

**Perturbações sintéticas**

| Aumento | Jobs | Detect CUSUM | Detect PH | Pré-alerta CUSUM | Pré-alerta PH | Atraso CUSUM | Atraso PH |
|---:|---:|---:|---:|---:|---:|---:|---:|
| +0.5 SD | 7205 | 4.3% | 4.0% | 1.7% | 1.5% | 1590.0 | 1460.0 |
| +1.0 SD | 7205 | 4.4% | 4.1% | 1.7% | 1.5% | 1620.0 | 1510.0 |
| +2.0 SD | 7205 | 4.7% | 4.5% | 1.7% | 1.5% | 1700.0 | 1630.0 |

## Horizonte 60 s

Quartis de duração (previsões): [56.0, 170.0, 490.0]

| Grupo | Val jobs | Test jobs | Alertas CUSUM | Alertas PH |
|---|---:|---:|---:|---:|
| Q1 (15–55) | 3267 | 1797 | 2.2% | 2.3% |
| Q2 (56–169) | 3297 | 2498 | 4.6% | 4.0% |
| Q3 (170–489) | 3294 | 2186 | 6.1% | 6.3% |
| Q4 (490–4315) | 3286 | 2098 | 5.6% | 5.1% |

**Perturbações sintéticas**

| Aumento | Jobs | Detect CUSUM | Detect PH | Pré-alerta CUSUM | Pré-alerta PH | Atraso CUSUM | Atraso PH |
|---:|---:|---:|---:|---:|---:|---:|---:|
| +0.5 SD | 7180 | 3.9% | 3.6% | 1.6% | 1.6% | 1460.0 | 1300.0 |
| +1.0 SD | 7180 | 4.0% | 3.7% | 1.6% | 1.6% | 1480.0 | 1420.0 |
| +2.0 SD | 7180 | 4.2% | 4.0% | 1.6% | 1.6% | 1550.0 | 1510.0 |

## Horizonte 120 s

Quartis de duração (previsões): [63.0, 171.0, 521.0]

| Grupo | Val jobs | Test jobs | Alertas CUSUM | Alertas PH |
|---|---:|---:|---:|---:|
| Q1 (15–62) | 3171 | 1990 | 2.2% | 2.6% |
| Q2 (63–170) | 3156 | 2371 | 3.7% | 3.2% |
| Q3 (171–520) | 3211 | 2145 | 6.8% | 7.1% |
| Q4 (521–4312) | 3180 | 2021 | 5.9% | 4.9% |

**Perturbações sintéticas**

| Aumento | Jobs | Detect CUSUM | Detect PH | Pré-alerta CUSUM | Pré-alerta PH | Atraso CUSUM | Atraso PH |
|---:|---:|---:|---:|---:|---:|---:|---:|
| +0.5 SD | 7111 | 4.0% | 3.5% | 1.6% | 1.7% | 1390.0 | 1360.0 |
| +1.0 SD | 7111 | 4.1% | 3.6% | 1.6% | 1.7% | 1420.0 | 1380.0 |
| +2.0 SD | 7111 | 4.3% | 3.7% | 1.6% | 1.7% | 1500.0 | 1430.0 |

## Limitações

- Synthetic shifts are added to absolute forecast-error series, not raw power traces; they assess detector mechanics only.
- Only persistent upward steps are tested; decreases, variance shifts, gradual drifts, and other patterns are not covered.
- Duration quartiles may not remove all duration dependence; inspect alert rates by bin.
- Natural alerts have no independent changepoint labels and cannot be called true or false positives.
- Only one chronological split and a short test window; temporal generalization is unproven.
- The first five realized errors may be unstable; PM100 target is aggregate node power, not GPU-only power.
- This experiment does not validate ATOCIA or ATRP-1.

## Interpretação

A calibração por duração é promissora apenas se as taxas de alerta natural ficarem mais estáveis entre grupos e a detecção sintética permanecer útil. Detecção de perturbações artificiais não prova detecção de mudanças reais.

## Artefatos

- duration_calibration_synthetic_v1.py
- audit/duration_calibration_synthetic_v1.json
- PM100_DURATION_CALIBRATION_SYNTHETIC_V1.md

Dados originais, V2, ATRP-1 e relatórios anteriores não foram alterados.

**Fase encerrada; aguardar autorização antes da próxima.**
