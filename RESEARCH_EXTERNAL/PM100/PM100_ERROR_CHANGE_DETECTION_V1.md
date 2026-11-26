# PM100 — detecção exploratória de aumentos no erro online (V1)

**Data:** 23/11/2026  
**Status:** fase exploratória concluída; não é validação de ponto de mudança com rótulo de verdade-terreno.

## Pergunta e protocolo

A pergunta é se detectores unilaterais conseguem sinalizar aumentos persistentes no erro absoluto da EWMA durante um job. Para cada job e horizonte, os primeiros cinco erros absolutos realizados formam uma referência inicial. Depois, os erros são padronizados pela média e pelo desvio-padrão dessa referência (piso de 1 W). O CUSUM usa referência fixa; o Page-Hinkley acompanha a média acumulada e mede o desvio acumulado acima de seu mínimo.

Os hiperparâmetros estruturais foram fixados antes do teste: CUSUM k=0,50; Page-Hinkley delta=0,25; mínimo de 15 previsões por job. Para cada horizonte e detector, o limiar é o percentil empírico superior de 95% dos máximos por job na validação. O limiar é congelado antes de avaliar o teste.

A referência usa erros já realizados, portanto o alerta só pode ocorrer depois que os alvos correspondentes chegam. Não é previsão pré-execução nem detecção instantânea.

## Cobertura
- Jobs elegíveis vistos na partição de validação: 17,998.
- Jobs elegíveis vistos na partição de teste: 10,278.
- Requisito: pelo menos 15 previsões por job e horizonte.

## Horizonte 20 s

- Jobs elegíveis: validação 14,539; teste 9,141.
- Limiar CUSUM congelado: 4242.9564; alertas no teste: 535/9,141 (5.9%).
- Limiar Page-Hinkley congelado: 1959.9208; alertas no teste: 477/9,141 (5.2%).
- Atraso mediano após a referência: CUSUM 18.680 s (5,2 h); Page-Hinkley 21.120 s (5,9 h).
- Previsões medianas por job entre os alertados: CUSUM 2.117; Page-Hinkley 1.396 (mediana de todos os elegíveis: 153).
- Fração de excedência na própria validação: CUSUM 5,0%; Page-Hinkley 5,0%.
- MAE inicial mediana dos jobs elegíveis no teste: 29.35 W.

## Horizonte 40 s

- Jobs elegíveis: validação 13,442; teste 8,604.
- Limiar CUSUM congelado: 5153.9738; alertas no teste: 482/8,604 (5.6%).
- Limiar Page-Hinkley congelado: 2776.9867; alertas no teste: 410/8,604 (4.8%).
- Atraso mediano após a referência: CUSUM 17.390 s (4,8 h); Page-Hinkley 21.950 s (6,1 h).
- Previsões medianas por job entre os alertados: CUSUM 1.474,5; Page-Hinkley 1.434,5 (mediana de todos os elegíveis: 170).
- Fração de excedência na própria validação: CUSUM 5,0%; Page-Hinkley 5,0%.
- MAE inicial mediana dos jobs elegíveis no teste: 32.54 W.

## Horizonte 60 s

- Jobs elegíveis: validação 13,144; teste 8,579.
- Limiar CUSUM congelado: 6482.0387; alertas no teste: 460/8,579 (5.4%).
- Limiar Page-Hinkley congelado: 3532.4571; alertas no teste: 405/8,579 (4.7%).
- Atraso mediano após a referência: CUSUM 18.670 s (5,2 h); Page-Hinkley 23.500 s (6,5 h).
- Previsões medianas por job entre os alertados: CUSUM 1.344; Page-Hinkley 1.433 (mediana de todos os elegíveis: 169).
- Fração de excedência na própria validação: CUSUM 5,0%; Page-Hinkley 5,0%.
- MAE inicial mediana dos jobs elegíveis no teste: 33.31 W.

## Horizonte 120 s

- Jobs elegíveis: validação 12,718; teste 8,527.
- Limiar CUSUM congelado: 7315.8492; alertas no teste: 434/8,527 (5.1%).
- Limiar Page-Hinkley congelado: 4233.4299; alertas no teste: 393/8,527 (4.6%).
- Atraso mediano após a referência: CUSUM 17.350 s (4,8 h); Page-Hinkley 24.700 s (6,9 h).
- Previsões medianas por job entre os alertados: CUSUM 1.341; Page-Hinkley 1.431 (mediana de todos os elegíveis: 168).
- Fração de excedência na própria validação: CUSUM 5,0%; Page-Hinkley 5,0%.
- MAE inicial mediana dos jobs elegíveis no teste: 35.51 W.

## Limitações

- No ground-truth changepoint labels exist in this experiment; a threshold crossing is an alert, not a verified regime change.
- Validation calibration targets an empirical 5% job-level exceedance on the same validation distribution; it is not a guaranteed false-positive rate on future data.
- Only one chronological split and a short test date window are used; temporal generalization remains unproven.
- The initial five realized errors can be unstable and may include startup behavior; the first five are a reference, not a known stationary regime.
- Absolute-error changes can reflect noise, job heterogeneity, load shape, or forecasting mismatch; they do not identify physical causes.
- The analysis uses EWMA parameters frozen in V2 and does not change ATOCIA or ATRP-1.
- PM100 target is aggregate node power per job, not GPU-only power; PM100 has no GPU temperature signal.

## Conclusão

Os detectores foram avaliados como mecanismos de alerta de aumento persistente do erro, com limiares calibrados na validação. A taxa de alertas no teste deve ser interpretada como incidência de alertas, não como taxa de falsos positivos, pois não há rótulos independentes de mudança real. Sem rótulos ou intervenções controladas, não é possível afirmar precisão, recall ou atraso verdadeiro de detecção.

O principal achado metodológico é uma forte dependência do comprimento do job: a mediana de previsões entre jobs alertados fica entre 1.341 e 2.117, enquanto a mediana de todos os jobs elegíveis fica entre 153 e 170. Os alertas surgem, em mediana, somente após 4,8–6,9 horas de observações de 20 s. Portanto, o limiar global baseado no máximo por job favorece trajetórias muito longas; o detector, nesta forma, não é um mecanismo rápido ou prático para a maioria dos jobs. A taxa de alertas perto de 5% não prova que os alertas correspondam a mudanças reais.

## Artefatos

- Script: `detect_error_changes_v1.py`
- Resultado integral: `audit/error_change_detection_v1.json`
- Relatório: `PM100_ERROR_CHANGE_DETECTION_V1.md`

O Parquet original, os resultados V2, os pesos ATRP-1 e os relatórios anteriores não foram alterados.

**Fase encerrada; aguardar autorização antes de iniciar a próxima.**
