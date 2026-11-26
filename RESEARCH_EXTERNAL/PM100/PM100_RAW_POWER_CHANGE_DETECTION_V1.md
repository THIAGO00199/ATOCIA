# PM100 — detecção após perturbações na potência bruta (V1)

**Status:** mudanças artificiais inseridas na série medida de potência; erros EWMA recalculados de forma causal. Não são mudanças reais rotuladas.

## Pergunta e protocolo

Os detectores por janelas reconhecem alterações quando a intervenção ocorre na potência original, antes de o erro de previsão ser calculado?

Mantivemos a divisão cronológica, os alphas EWMA V2 e os detectores de média, variância e máximo normalizado. Limiar e quartis de duração foram calibrados somente na validação. A amostra sintética é retirada do teste, com até 100 jobs por quartil e horizonte e pelo menos 80 erros de previsão para permitir todas as larguras de janela.

As mudanças foram inseridas na potência bruta: degraus e rampas de nível para cima/baixo; mudanças isoladas na escala do desvio-padrão; e mudanças simultâneas de nível e dispersão. A escala local é o desvio-padrão dos 20 pontos brutos anteriores ao evento. Depois da intervenção, o EWMA é recalculado usando apenas o passado disponível para cada previsão.

Jobs vistos: validação 17,998; teste 10,278. Cenários: 40. O ponto de mudança é conhecido em cada série. Atraso é calculado na escala temporal de amostragem de 20 s.

## Alertas naturais no teste — janela de 200 s

Frações de jobs com ao menos um alerta, não taxas de falso positivo. Não há rótulos independentes de mudanças naturais.

| Horizonte | Média | Variância | Máximo |
|---:|---:|---:|---:|
| 20 s | 5.77% | 3.47% | 4.94% |
| 40 s | 3.57% | 3.61% | 3.58% |
| 60 s | 2.61% | 4.30% | 3.48% |
| 120 s | 3.62% | 4.37% | 4.31% |

## Detecção sintética por classe — janela de 200 s

Proporção ponderada de jobs em que o primeiro alerta ocorreu após a mudança bruta / proporção de pré-alertas anteriores à mudança.

| Horizonte | Classe | Média | Variância | Máximo |
|---:|---|---:|---:|---:|
| 20 s | Nível isolado | 2.2% / 1.8% (n=4800) | 1.7% / 1.0% (n=4800) | 2.4% / 1.0% (n=4800) |
| 20 s | Dispersão isolada | 3.4% / 1.8% (n=1600) | 6.3% / 1.0% (n=1600) | 5.2% / 1.0% (n=1600) |
| 20 s | Nível + dispersão | 3.5% / 1.8% (n=9600) | 6.7% / 1.0% (n=9600) | 5.5% / 1.0% (n=9600) |
| 40 s | Nível isolado | 1.7% / 1.2% (n=4800) | 1.3% / 1.2% (n=4800) | 1.4% / 1.5% (n=4800) |
| 40 s | Dispersão isolada | 1.6% / 1.2% (n=1600) | 5.6% / 1.2% (n=1600) | 4.8% / 1.5% (n=1600) |
| 40 s | Nível + dispersão | 1.7% / 1.2% (n=9600) | 5.9% / 1.2% (n=9600) | 5.0% / 1.5% (n=9600) |
| 60 s | Nível isolado | 1.2% / 1.2% (n=4800) | 2.8% / 1.8% (n=4800) | 1.8% / 1.8% (n=4800) |
| 60 s | Dispersão isolada | 1.6% / 1.2% (n=1600) | 5.9% / 1.8% (n=1600) | 4.0% / 1.8% (n=1600) |
| 60 s | Nível + dispersão | 1.5% / 1.2% (n=9600) | 5.6% / 1.8% (n=9600) | 3.7% / 1.8% (n=9600) |
| 120 s | Nível isolado | 2.7% / 1.0% (n=4800) | 2.2% / 1.8% (n=4800) | 2.4% / 1.5% (n=4800) |
| 120 s | Dispersão isolada | 3.2% / 1.0% (n=1600) | 3.8% / 1.8% (n=1600) | 3.9% / 1.5% (n=1600) |
| 120 s | Nível + dispersão | 2.9% / 1.0% (n=9600) | 3.9% / 1.8% (n=9600) | 3.7% / 1.5% (n=9600) |

## Comparação pareada do máximo com os detectores isolados — janela de 200 s

Diferença = detecção do máximo menos detecção do detector isolado. Intervalos normais pareados de 95%, sem correção por multiplicidade; contam-se 160 combinações de cenário e horizonte.

| Comparação | Diferença média | IC95% favorece máximo | IC95% favorece isolado | Inclui zero |
|---|---:|---:|---:|---:|
| Máximo − mean | +1.46% | 49 | 0 | 111 |
| Máximo − variance | -0.75% | 0 | 17 | 143 |

## Cenários individuais de referência — janela de 200 s

Detecção após a mudança / pré-alerta, com atraso mediano no JSON.

| Horizonte | Cenário | Média | Variância | Máximo |
|---:|---|---:|---:|---:|
| 20 s | mean_step_up_d2 | 2.0% / 1.8% | 1.5% / 1.0% | 2.2% / 1.0% |
| 20 s | mean_step_down_d2 | 2.5% / 1.8% | 2.0% / 1.0% | 3.2% / 1.0% |
| 20 s | sd_step_m2 | 3.5% / 1.8% | 9.8% / 1.0% | 8.2% / 1.0% |
| 20 s | mixed_step_up_d1_m2 | 4.0% / 1.8% | 9.5% / 1.0% | 7.5% / 1.0% |
| 20 s | mixed_step_down_d1_m2 | 4.0% / 1.8% | 10.2% / 1.0% | 8.8% / 1.0% |
| 20 s | mixed_ramp_up_d1_m2 | 3.5% / 1.8% | 8.5% / 1.0% | 6.0% / 1.0% |
| 20 s | mixed_ramp_down_d1_m2 | 3.8% / 1.8% | 9.0% / 1.0% | 7.2% / 1.0% |
| 40 s | mean_step_up_d2 | 1.0% / 1.2% | 1.0% / 1.2% | 1.0% / 1.5% |
| 40 s | mean_step_down_d2 | 1.2% / 1.2% | 1.8% / 1.2% | 1.2% / 1.5% |
| 40 s | sd_step_m2 | 1.8% / 1.2% | 8.0% / 1.2% | 8.2% / 1.5% |
| 40 s | mixed_step_up_d1_m2 | 1.0% / 1.2% | 6.5% / 1.2% | 6.5% / 1.5% |
| 40 s | mixed_step_down_d1_m2 | 1.5% / 1.2% | 9.2% / 1.2% | 9.0% / 1.5% |
| 40 s | mixed_ramp_up_d1_m2 | 1.5% / 1.2% | 7.2% / 1.2% | 6.5% / 1.5% |
| 40 s | mixed_ramp_down_d1_m2 | 2.5% / 1.2% | 9.2% / 1.2% | 9.2% / 1.5% |
| 60 s | mean_step_up_d2 | 1.2% / 1.2% | 2.5% / 1.8% | 1.5% / 1.8% |
| 60 s | mean_step_down_d2 | 1.5% / 1.2% | 2.2% / 1.8% | 2.0% / 1.8% |
| 60 s | sd_step_m2 | 2.2% / 1.2% | 7.0% / 1.8% | 5.8% / 1.8% |
| 60 s | mixed_step_up_d1_m2 | 1.8% / 1.2% | 6.0% / 1.8% | 5.0% / 1.8% |
| 60 s | mixed_step_down_d1_m2 | 1.5% / 1.2% | 6.5% / 1.8% | 4.8% / 1.8% |
| 60 s | mixed_ramp_up_d1_m2 | 1.2% / 1.2% | 5.5% / 1.8% | 4.5% / 1.8% |
| 60 s | mixed_ramp_down_d1_m2 | 1.8% / 1.2% | 6.0% / 1.8% | 5.2% / 1.8% |
| 120 s | mean_step_up_d2 | 2.5% / 1.0% | 2.8% / 1.8% | 2.5% / 1.5% |
| 120 s | mean_step_down_d2 | 3.2% / 1.0% | 2.5% / 1.8% | 2.5% / 1.5% |
| 120 s | sd_step_m2 | 3.2% / 1.0% | 4.5% / 1.8% | 4.8% / 1.5% |
| 120 s | mixed_step_up_d1_m2 | 3.0% / 1.0% | 4.5% / 1.8% | 3.8% / 1.5% |
| 120 s | mixed_step_down_d1_m2 | 2.2% / 1.0% | 4.5% / 1.8% | 4.0% / 1.5% |
| 120 s | mixed_ramp_up_d1_m2 | 3.5% / 1.0% | 3.5% / 1.8% | 4.0% / 1.5% |
| 120 s | mixed_ramp_down_d1_m2 | 4.2% / 1.0% | 3.8% / 1.8% | 4.8% / 1.5% |

## Interpretação e limites

- Este teste é mais próximo da variável medida do que as intervenções anteriores nos resíduos: a potência bruta é alterada e o EWMA é recalculado. Ainda assim, as intervenções são sintéticas e não validam detecção de mudanças físicas reais.
- Um degrau de potência pode gerar um pico transitório no erro enquanto o EWMA se adapta; portanto, não se espera necessariamente que o erro permaneça deslocado. A resposta depende de alpha e horizonte.
- Pré-alerta significa que o primeiro cruzamento ocorreu antes do ponto de mudança conhecido; não é contado como detecção daquela mudança.
- Degraus descendentes e expansão de dispersão podem sofrer truncamento em zero. Os intervalos de Wilson e os resultados por quartil estão no JSON.
- PM100 mede potência agregada do job/nó, não GPU-only. Não há rótulos naturais, outra divisão temporal, validação operacional ou demonstração de economia de energia.
- Nada nesta fase valida ATOCIA ou ATRP-1.

## Artefatos

- raw_power_change_detection_v1.py
- audit/raw_power_change_detection_v1.json
- PM100_RAW_POWER_CHANGE_DETECTION_V1.md

O Parquet original e os modelos anteriores não foram alterados.

**Fase encerrada; aguardar autorização antes da próxima.**
