# PM100 — detecção após perturbações na potência bruta (V2, baseline pareado)

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

Cada célula informa detecção após a mudança na série alterada / alerta pós-ponto na série original sem intervenção / ganho incremental (diferença) / pré-alerta na série alterada. n conta instâncias cenário-job; os mesmos jobs são reutilizados em cenários diferentes e, portanto, n não é o número de jobs únicos.

| Horizonte | Classe | Método | Alterada | Original pós-CP | Incremento (p.p.) | Pré-alerta | n instâncias |
|---:|---|---|---:|---:|---:|---:|---:|
| 20 s | Nível isolado | mean | 2.2% | 2.2% | +0.0 p.p. | 1.8% | 4800 |
| 20 s | Nível isolado | variance | 1.7% | 2.0% | -0.3 p.p. | 1.0% | 4800 |
| 20 s | Nível isolado | max | 2.4% | 2.5% | -0.1 p.p. | 1.0% | 4800 |
| 20 s | Dispersão isolada | mean | 3.4% | 2.2% | +1.1 p.p. | 1.8% | 1600 |
| 20 s | Dispersão isolada | variance | 6.3% | 2.0% | +4.3 p.p. | 1.0% | 1600 |
| 20 s | Dispersão isolada | max | 5.2% | 2.5% | +2.8 p.p. | 1.0% | 1600 |
| 20 s | Nível + dispersão | mean | 3.5% | 2.2% | +1.2 p.p. | 1.8% | 9600 |
| 20 s | Nível + dispersão | variance | 6.7% | 2.0% | +4.7 p.p. | 1.0% | 9600 |
| 20 s | Nível + dispersão | max | 5.5% | 2.5% | +3.0 p.p. | 1.0% | 9600 |
| 40 s | Nível isolado | mean | 1.7% | 1.5% | +0.2 p.p. | 1.2% | 4800 |
| 40 s | Nível isolado | variance | 1.3% | 1.5% | -0.2 p.p. | 1.2% | 4800 |
| 40 s | Nível isolado | max | 1.4% | 1.5% | -0.1 p.p. | 1.5% | 4800 |
| 40 s | Dispersão isolada | mean | 1.6% | 1.5% | +0.1 p.p. | 1.2% | 1600 |
| 40 s | Dispersão isolada | variance | 5.6% | 1.5% | +4.1 p.p. | 1.2% | 1600 |
| 40 s | Dispersão isolada | max | 4.8% | 1.5% | +3.3 p.p. | 1.5% | 1600 |
| 40 s | Nível + dispersão | mean | 1.7% | 1.5% | +0.2 p.p. | 1.2% | 9600 |
| 40 s | Nível + dispersão | variance | 5.9% | 1.5% | +4.4 p.p. | 1.2% | 9600 |
| 40 s | Nível + dispersão | max | 5.0% | 1.5% | +3.5 p.p. | 1.5% | 9600 |
| 60 s | Nível isolado | mean | 1.2% | 1.2% | +0.0 p.p. | 1.2% | 4800 |
| 60 s | Nível isolado | variance | 2.8% | 3.0% | -0.2 p.p. | 1.8% | 4800 |
| 60 s | Nível isolado | max | 1.8% | 1.8% | +0.1 p.p. | 1.8% | 4800 |
| 60 s | Dispersão isolada | mean | 1.6% | 1.2% | +0.3 p.p. | 1.2% | 1600 |
| 60 s | Dispersão isolada | variance | 5.9% | 3.0% | +2.9 p.p. | 1.8% | 1600 |
| 60 s | Dispersão isolada | max | 4.0% | 1.8% | +2.2 p.p. | 1.8% | 1600 |
| 60 s | Nível + dispersão | mean | 1.5% | 1.2% | +0.2 p.p. | 1.2% | 9600 |
| 60 s | Nível + dispersão | variance | 5.6% | 3.0% | +2.6 p.p. | 1.8% | 9600 |
| 60 s | Nível + dispersão | max | 3.7% | 1.8% | +1.9 p.p. | 1.8% | 9600 |
| 120 s | Nível isolado | mean | 2.7% | 2.2% | +0.4 p.p. | 1.0% | 4800 |
| 120 s | Nível isolado | variance | 2.2% | 2.5% | -0.2 p.p. | 1.8% | 4800 |
| 120 s | Nível isolado | max | 2.4% | 2.0% | +0.4 p.p. | 1.5% | 4800 |
| 120 s | Dispersão isolada | mean | 3.2% | 2.2% | +1.0 p.p. | 1.0% | 1600 |
| 120 s | Dispersão isolada | variance | 3.8% | 2.5% | +1.2 p.p. | 1.8% | 1600 |
| 120 s | Dispersão isolada | max | 3.9% | 2.0% | +1.9 p.p. | 1.5% | 1600 |
| 120 s | Nível + dispersão | mean | 2.9% | 2.2% | +0.7 p.p. | 1.0% | 9600 |
| 120 s | Nível + dispersão | variance | 3.9% | 2.5% | +1.4 p.p. | 1.8% | 9600 |
| 120 s | Nível + dispersão | max | 3.7% | 2.0% | +1.7 p.p. | 1.5% | 9600 |

## Comparação pareada: intervenção versus potência original — janela de 200 s

Diferença = indicador de primeiro alerta pós-CP na série alterada menos o mesmo indicador na série original não alterada, no mesmo job e no mesmo ponto de referência. IC normal pareado de 95%, sem correção por multiplicidade.

| Método | Ganho médio pareado (p.p.) | IC95% ganho positivo | IC95% ganho negativo | Inclui zero |
|---|---:|---:|---:|---:|
| mean | +0.45 p.p. | 28 | 0 | 132 |
| variance | +2.22 p.p. | 92 | 0 | 68 |
| max | +1.79 p.p. | 71 | 0 | 89 |

## Comparação pareada do máximo com os detectores isolados — janela de 200 s

Diferença = detecção do máximo menos detecção do detector isolado, nas séries alteradas. Intervalos normais pareados de 95%, sem correção por multiplicidade; contam-se 160 combinações de cenário e horizonte.

| Comparação | Diferença média (p.p.) | IC95% favorece máximo | IC95% favorece isolado | Inclui zero |
|---|---:|---:|---:|---:|
| Máximo − mean | +1.46 p.p. | 49 | 0 | 111 |
| Máximo − variance | -0.75 p.p. | 0 | 17 | 143 |

## Síntese dos ganhos incrementais

Para mudanças apenas de nível, o ganho médio foi praticamente nulo: +0,15 p.p. (média), −0,23 p.p. (variância) e +0,05 p.p. (máximo). Para mudanças apenas de dispersão, os ganhos foram +0,64, +3,14 e +2,55 p.p., respectivamente. Nas mudanças simultâneas, foram +0,58, +3,30 e +2,53 p.p.

Assim, a resposta incremental observada está concentrada em mudanças que alteram a dispersão. O detector de variância teve o maior ganho médio, enquanto o máximo foi intermediário. As taxas absolutas de detecção permanecem baixas e não demonstram sensibilidade adequada para uso operacional.

Os totais agregam combinações de cenário e horizonte; os mesmos jobs aparecem em diferentes cenários. Os intervalos pareados são exploratórios e não têm correção para multiplicidade.

## Cenários individuais de referência — janela de 200 s

Cada método: detecção após a mudança / alerta pós-CP na série original / ganho incremental em pontos percentuais / pré-alerta.

| Horizonte | Cenário | Média | Variância | Máximo |
|---:|---|---:|---:|---:|
| 20 s | mean_step_up_d2 | 2.0% / 2.2% / -0.2 p.p. / 1.8% | 1.5% / 2.0% / -0.5 p.p. / 1.0% | 2.2% / 2.5% / -0.3 p.p. / 1.0% |
| 20 s | mean_step_down_d2 | 2.5% / 2.2% / +0.3 p.p. / 1.8% | 2.0% / 2.0% / +0.0 p.p. / 1.0% | 3.2% / 2.5% / +0.8 p.p. / 1.0% |
| 20 s | sd_step_m2 | 3.5% / 2.2% / +1.3 p.p. / 1.8% | 9.8% / 2.0% / +7.8 p.p. / 1.0% | 8.2% / 2.5% / +5.8 p.p. / 1.0% |
| 20 s | mixed_step_up_d1_m2 | 4.0% / 2.2% / +1.8 p.p. / 1.8% | 9.5% / 2.0% / +7.5 p.p. / 1.0% | 7.5% / 2.5% / +5.0 p.p. / 1.0% |
| 20 s | mixed_step_down_d1_m2 | 4.0% / 2.2% / +1.8 p.p. / 1.8% | 10.2% / 2.0% / +8.2 p.p. / 1.0% | 8.8% / 2.5% / +6.2 p.p. / 1.0% |
| 20 s | mixed_ramp_up_d1_m2 | 3.5% / 2.2% / +1.3 p.p. / 1.8% | 8.5% / 2.0% / +6.5 p.p. / 1.0% | 6.0% / 2.5% / +3.5 p.p. / 1.0% |
| 20 s | mixed_ramp_down_d1_m2 | 3.8% / 2.2% / +1.5 p.p. / 1.8% | 9.0% / 2.0% / +7.0 p.p. / 1.0% | 7.2% / 2.5% / +4.7 p.p. / 1.0% |
| 40 s | mean_step_up_d2 | 1.0% / 1.5% / -0.5 p.p. / 1.2% | 1.0% / 1.5% / -0.5 p.p. / 1.2% | 1.0% / 1.5% / -0.5 p.p. / 1.5% |
| 40 s | mean_step_down_d2 | 1.2% / 1.5% / -0.2 p.p. / 1.2% | 1.8% / 1.5% / +0.3 p.p. / 1.2% | 1.2% / 1.5% / -0.2 p.p. / 1.5% |
| 40 s | sd_step_m2 | 1.8% / 1.5% / +0.3 p.p. / 1.2% | 8.0% / 1.5% / +6.5 p.p. / 1.2% | 8.2% / 1.5% / +6.8 p.p. / 1.5% |
| 40 s | mixed_step_up_d1_m2 | 1.0% / 1.5% / -0.5 p.p. / 1.2% | 6.5% / 1.5% / +5.0 p.p. / 1.2% | 6.5% / 1.5% / +5.0 p.p. / 1.5% |
| 40 s | mixed_step_down_d1_m2 | 1.5% / 1.5% / +0.0 p.p. / 1.2% | 9.2% / 1.5% / +7.8 p.p. / 1.2% | 9.0% / 1.5% / +7.5 p.p. / 1.5% |
| 40 s | mixed_ramp_up_d1_m2 | 1.5% / 1.5% / +0.0 p.p. / 1.2% | 7.2% / 1.5% / +5.8 p.p. / 1.2% | 6.5% / 1.5% / +5.0 p.p. / 1.5% |
| 40 s | mixed_ramp_down_d1_m2 | 2.5% / 1.5% / +1.0 p.p. / 1.2% | 9.2% / 1.5% / +7.8 p.p. / 1.2% | 9.2% / 1.5% / +7.8 p.p. / 1.5% |
| 60 s | mean_step_up_d2 | 1.2% / 1.2% / +0.0 p.p. / 1.2% | 2.5% / 3.0% / -0.5 p.p. / 1.8% | 1.5% / 1.8% / -0.3 p.p. / 1.8% |
| 60 s | mean_step_down_d2 | 1.5% / 1.2% / +0.2 p.p. / 1.2% | 2.2% / 3.0% / -0.8 p.p. / 1.8% | 2.0% / 1.8% / +0.2 p.p. / 1.8% |
| 60 s | sd_step_m2 | 2.2% / 1.2% / +1.0 p.p. / 1.2% | 7.0% / 3.0% / +4.0 p.p. / 1.8% | 5.8% / 1.8% / +4.0 p.p. / 1.8% |
| 60 s | mixed_step_up_d1_m2 | 1.8% / 1.2% / +0.5 p.p. / 1.2% | 6.0% / 3.0% / +3.0 p.p. / 1.8% | 5.0% / 1.8% / +3.2 p.p. / 1.8% |
| 60 s | mixed_step_down_d1_m2 | 1.5% / 1.2% / +0.2 p.p. / 1.2% | 6.5% / 3.0% / +3.5 p.p. / 1.8% | 4.8% / 1.8% / +3.0 p.p. / 1.8% |
| 60 s | mixed_ramp_up_d1_m2 | 1.2% / 1.2% / +0.0 p.p. / 1.2% | 5.5% / 3.0% / +2.5 p.p. / 1.8% | 4.5% / 1.8% / +2.7 p.p. / 1.8% |
| 60 s | mixed_ramp_down_d1_m2 | 1.8% / 1.2% / +0.5 p.p. / 1.2% | 6.0% / 3.0% / +3.0 p.p. / 1.8% | 5.2% / 1.8% / +3.5 p.p. / 1.8% |
| 120 s | mean_step_up_d2 | 2.5% / 2.2% / +0.3 p.p. / 1.0% | 2.8% / 2.5% / +0.2 p.p. / 1.8% | 2.5% / 2.0% / +0.5 p.p. / 1.5% |
| 120 s | mean_step_down_d2 | 3.2% / 2.2% / +1.0 p.p. / 1.0% | 2.5% / 2.5% / +0.0 p.p. / 1.8% | 2.5% / 2.0% / +0.5 p.p. / 1.5% |
| 120 s | sd_step_m2 | 3.2% / 2.2% / +1.0 p.p. / 1.0% | 4.5% / 2.5% / +2.0 p.p. / 1.8% | 4.8% / 2.0% / +2.8 p.p. / 1.5% |
| 120 s | mixed_step_up_d1_m2 | 3.0% / 2.2% / +0.8 p.p. / 1.0% | 4.5% / 2.5% / +2.0 p.p. / 1.8% | 3.8% / 2.0% / +1.7 p.p. / 1.5% |
| 120 s | mixed_step_down_d1_m2 | 2.2% / 2.2% / +0.0 p.p. / 1.0% | 4.5% / 2.5% / +2.0 p.p. / 1.8% | 4.0% / 2.0% / +2.0 p.p. / 1.5% |
| 120 s | mixed_ramp_up_d1_m2 | 3.5% / 2.2% / +1.3 p.p. / 1.0% | 3.5% / 2.5% / +1.0 p.p. / 1.8% | 4.0% / 2.0% / +2.0 p.p. / 1.5% |
| 120 s | mixed_ramp_down_d1_m2 | 4.2% / 2.2% / +2.0 p.p. / 1.0% | 3.8% / 2.5% / +1.2 p.p. / 1.8% | 4.8% / 2.0% / +2.8 p.p. / 1.5% |

## Interpretação e limites

- Este teste é mais próximo da variável medida do que as intervenções anteriores nos resíduos: a potência bruta é alterada e o EWMA é recalculado. Ainda assim, as intervenções são sintéticas e não validam detecção de mudanças físicas reais.
- Um degrau de potência pode gerar um pico transitório no erro enquanto o EWMA se adapta; portanto, não se espera necessariamente que o erro permaneça deslocado. A resposta depende de alpha e horizonte.
- Pré-alerta significa que o primeiro cruzamento ocorreu antes do ponto de mudança conhecido; não é contado como detecção daquela mudança.
- A taxa de detecção bruta inclui alertas que poderiam ocorrer mesmo sem a intervenção. Por isso, o V2 reporta também o primeiro alerta pós-CP no sinal original e a diferença pareada alterado − original; esse ganho incremental é a leitura principal.
- Degraus descendentes e expansão de dispersão podem sofrer truncamento em zero. Os intervalos de Wilson e os resultados por quartil estão no JSON.
- PM100 mede potência agregada do job/nó, não GPU-only. Não há rótulos naturais, outra divisão temporal, validação operacional ou demonstração de economia de energia.
- Nada nesta fase valida ATOCIA ou ATRP-1.

## Artefatos

- raw_power_change_detection_v2.py
- audit/raw_power_change_detection_v2.json
- PM100_RAW_POWER_CHANGE_DETECTION_V2.md
- V1 preservado como histórico preliminar; V2 adiciona o baseline pareado sem intervenção.

O Parquet original e os modelos anteriores não foram alterados.

**Fase encerrada; aguardar autorização antes da próxima.**
