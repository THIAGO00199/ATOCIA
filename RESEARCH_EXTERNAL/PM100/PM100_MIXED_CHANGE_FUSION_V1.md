# PM100 — fusão de detectores em mudanças simultâneas (V1)

**Status:** comparação exploratória com orçamento de alertas igualado na validação; mudanças sintéticas não são mudanças físicas observadas.

## Pergunta e protocolo

Uma fusão por soma normalizada ou norma L2 recupera sensibilidade em mudanças simultâneas de nível e dispersão, em comparação com a regra pelo máximo?

Foram comparadas cinco alternativas: média isolada, variância isolada, máximo normalizado (regra anterior), soma normalizada e norma L2. Para média e variância, os limiares individuais são os percentis 95 dos máximos por job. Para cada fusão, os sinais são combinados ponto a ponto na série temporal e só então é calculado o máximo por job; o limiar é o percentil 95 desses máximos combinados na validação, separado por horizonte, janela e quartil de duração. Portanto, todos têm a mesma meta empírica de 5% por job na validação; a fusão não recebe dois orçamentos de 5%.

Os testes sintéticos usam os mesmos jobs amostrados por horizonte e quartil. O ponto de mudança está no meio do trecho monitorado. Foram incluídos controles de mudança somente na média, somente na escala do desvio-padrão e mudanças simultâneas. Degraus e rampas são avaliados separadamente.

Jobs vistos: validação 17,998; teste 10,278. Cenários: 22; amostra de até 250 jobs por quartil e horizonte.

## Alertas naturais no teste — janela de 10 amostras

Fração de jobs com pelo menos um alerta, ponderada pelos tamanhos dos quartis. Não é taxa de falsos positivos: não existem rótulos independentes para as mudanças naturais.

| Horizonte | Média | Variância | Máximo | Soma | L2 |
|---:|---:|---:|---:|---:|---:|
| 20 s | 5.77% | 3.47% | 4.94% | 4.00% | 4.47% |
| 40 s | 3.57% | 3.61% | 3.58% | 3.19% | 3.30% |
| 60 s | 2.61% | 4.30% | 3.48% | 3.10% | 3.16% |
| 120 s | 3.62% | 4.37% | 4.31% | 4.05% | 4.21% |

## Mudanças simultâneas — janela de 10 amostras

Detecção após a mudança / pré-alerta anterior à mudança. O JSON contém atrasos, intervalos de Wilson, resultados por quartil e comparações pareadas das fusões contra o máximo.

### Degraus simultâneos

| Horizonte | Cenário | Máximo | Soma | L2 |
|---:|---|---:|---:|---:|
| 20 s | d=0.5 SD, SD×1.5 | 6.0% / 2.5% | 4.5% / 2.1% | 5.7% / 2.6% |
| 20 s | d=0.5 SD, SD×2.0 | 12.7% / 2.5% | 11.7% / 2.1% | 12.8% / 2.6% |
| 20 s | d=1.0 SD, SD×1.5 | 5.1% / 2.5% | 3.1% / 2.1% | 3.6% / 2.6% |
| 20 s | d=1.0 SD, SD×2.0 | 9.2% / 2.5% | 6.4% / 2.1% | 8.1% / 2.6% |
| 20 s | d=2.0 SD, SD×1.5 | 11.8% / 2.5% | 5.6% / 2.1% | 8.9% / 2.6% |
| 20 s | d=2.0 SD, SD×2.0 | 10.0% / 2.5% | 6.2% / 2.1% | 8.8% / 2.6% |
| 40 s | d=0.5 SD, SD×1.5 | 5.6% / 1.3% | 5.7% / 1.1% | 5.4% / 1.2% |
| 40 s | d=0.5 SD, SD×2.0 | 14.3% / 1.3% | 12.9% / 1.1% | 14.8% / 1.2% |
| 40 s | d=1.0 SD, SD×1.5 | 3.2% / 1.3% | 3.0% / 1.1% | 3.2% / 1.2% |
| 40 s | d=1.0 SD, SD×2.0 | 8.2% / 1.3% | 7.6% / 1.1% | 8.6% / 1.2% |
| 40 s | d=2.0 SD, SD×1.5 | 7.4% / 1.3% | 5.3% / 1.1% | 6.2% / 1.2% |
| 40 s | d=2.0 SD, SD×2.0 | 6.2% / 1.3% | 4.9% / 1.1% | 5.8% / 1.2% |
| 60 s | d=0.5 SD, SD×1.5 | 4.9% / 1.4% | 4.3% / 1.1% | 4.6% / 1.4% |
| 60 s | d=0.5 SD, SD×2.0 | 14.3% / 1.4% | 11.8% / 1.1% | 13.2% / 1.4% |
| 60 s | d=1.0 SD, SD×1.5 | 2.9% / 1.4% | 3.4% / 1.1% | 3.1% / 1.4% |
| 60 s | d=1.0 SD, SD×2.0 | 7.8% / 1.4% | 6.6% / 1.1% | 7.6% / 1.4% |
| 60 s | d=2.0 SD, SD×1.5 | 3.7% / 1.4% | 3.8% / 1.1% | 3.6% / 1.4% |
| 60 s | d=2.0 SD, SD×2.0 | 4.3% / 1.4% | 4.0% / 1.1% | 4.4% / 1.4% |
| 120 s | d=0.5 SD, SD×1.5 | 6.9% / 1.8% | 4.7% / 1.9% | 5.9% / 2.2% |
| 120 s | d=0.5 SD, SD×2.0 | 14.3% / 1.8% | 10.1% / 1.9% | 13.1% / 2.2% |
| 120 s | d=1.0 SD, SD×1.5 | 4.5% / 1.8% | 3.7% / 1.9% | 4.1% / 2.2% |
| 120 s | d=1.0 SD, SD×2.0 | 9.6% / 1.8% | 6.9% / 1.9% | 8.5% / 2.2% |
| 120 s | d=2.0 SD, SD×1.5 | 4.5% / 1.8% | 3.6% / 1.9% | 3.8% / 2.2% |
| 120 s | d=2.0 SD, SD×2.0 | 5.3% / 1.8% | 4.1% / 1.9% | 4.5% / 2.2% |

### Rampas simultâneas

| Horizonte | Cenário | Máximo | Soma | L2 |
|---:|---|---:|---:|---:|
| 20 s | d=0.5 SD, SD×1.5 | 5.4% / 2.5% | 3.8% / 2.1% | 5.1% / 2.6% |
| 20 s | d=0.5 SD, SD×2.0 | 11.2% / 2.5% | 10.5% / 2.1% | 11.3% / 2.6% |
| 20 s | d=1.0 SD, SD×1.5 | 5.2% / 2.5% | 2.9% / 2.1% | 4.4% / 2.6% |
| 20 s | d=1.0 SD, SD×2.0 | 7.9% / 2.5% | 5.5% / 2.1% | 7.5% / 2.6% |
| 20 s | d=2.0 SD, SD×1.5 | 9.0% / 2.5% | 5.1% / 2.1% | 8.0% / 2.6% |
| 20 s | d=2.0 SD, SD×2.0 | 8.0% / 2.5% | 4.7% / 2.1% | 6.6% / 2.6% |
| 40 s | d=0.5 SD, SD×1.5 | 4.9% / 1.3% | 4.8% / 1.1% | 4.9% / 1.2% |
| 40 s | d=0.5 SD, SD×2.0 | 13.2% / 1.3% | 11.4% / 1.1% | 13.5% / 1.2% |
| 40 s | d=1.0 SD, SD×1.5 | 3.3% / 1.3% | 3.0% / 1.1% | 3.2% / 1.2% |
| 40 s | d=1.0 SD, SD×2.0 | 7.2% / 1.3% | 6.6% / 1.1% | 7.4% / 1.2% |
| 40 s | d=2.0 SD, SD×1.5 | 6.4% / 1.3% | 3.7% / 1.1% | 5.4% / 1.2% |
| 40 s | d=2.0 SD, SD×2.0 | 5.6% / 1.3% | 3.5% / 1.1% | 5.1% / 1.2% |
| 60 s | d=0.5 SD, SD×1.5 | 4.3% / 1.4% | 3.7% / 1.1% | 4.1% / 1.4% |
| 60 s | d=0.5 SD, SD×2.0 | 13.3% / 1.4% | 10.1% / 1.1% | 11.9% / 1.4% |
| 60 s | d=1.0 SD, SD×1.5 | 2.6% / 1.4% | 2.7% / 1.1% | 2.1% / 1.4% |
| 60 s | d=1.0 SD, SD×2.0 | 7.2% / 1.4% | 5.9% / 1.1% | 6.6% / 1.4% |
| 60 s | d=2.0 SD, SD×1.5 | 2.9% / 1.4% | 2.7% / 1.1% | 2.3% / 1.4% |
| 60 s | d=2.0 SD, SD×2.0 | 4.1% / 1.4% | 3.3% / 1.1% | 3.4% / 1.4% |
| 120 s | d=0.5 SD, SD×1.5 | 5.7% / 1.8% | 4.3% / 1.9% | 5.1% / 2.2% |
| 120 s | d=0.5 SD, SD×2.0 | 12.7% / 1.8% | 8.8% / 1.9% | 11.4% / 2.2% |
| 120 s | d=1.0 SD, SD×1.5 | 3.5% / 1.8% | 3.4% / 1.9% | 3.5% / 2.2% |
| 120 s | d=1.0 SD, SD×2.0 | 8.3% / 1.8% | 6.0% / 1.9% | 7.4% / 2.2% |
| 120 s | d=2.0 SD, SD×1.5 | 4.0% / 1.8% | 3.1% / 1.9% | 3.5% / 2.2% |
| 120 s | d=2.0 SD, SD×2.0 | 4.8% / 1.8% | 3.9% / 1.9% | 4.4% / 2.2% |

## Diferença pareada em relação à fusão pelo máximo

Diferença = taxa de detecção do método alternativo menos a taxa do máximo. O intervalo é uma aproximação normal pareada de 95%, calculada sobre os mesmos jobs sintéticos; não corrige multiplicidade entre cenários.

| Horizonte | Cenário | Soma − máximo (IC95%) | L2 − máximo (IC95%) |
|---:|---|---:|---:|
| 20 s | step, d=0.5, SD×1.5 | -1.5% [-2.7%, -0.3%] | -0.3% [-0.9%, +0.3%] |
| 20 s | step, d=0.5, SD×2.0 | -1.0% [-2.4%, +0.4%] | +0.1% [-0.8%, +1.0%] |
| 20 s | step, d=1.0, SD×1.5 | -2.0% [-3.3%, -0.7%] | -1.5% [-2.4%, -0.6%] |
| 20 s | step, d=1.0, SD×2.0 | -2.8% [-4.1%, -1.5%] | -1.1% [-2.0%, -0.2%] |
| 20 s | step, d=2.0, SD×1.5 | -6.2% [-7.9%, -4.5%] | -2.9% [-4.1%, -1.7%] |
| 20 s | step, d=2.0, SD×2.0 | -3.8% [-5.4%, -2.2%] | -1.2% [-2.3%, -0.1%] |
| 20 s | ramp, d=0.5, SD×1.5 | -1.6% [-2.8%, -0.4%] | -0.3% [-1.0%, +0.4%] |
| 20 s | ramp, d=0.5, SD×2.0 | -0.7% [-2.1%, +0.7%] | +0.1% [-0.8%, +1.0%] |
| 20 s | ramp, d=1.0, SD×1.5 | -2.3% [-3.5%, -1.1%] | -0.8% [-1.5%, -0.1%] |
| 20 s | ramp, d=1.0, SD×2.0 | -2.4% [-3.7%, -1.1%] | -0.4% [-1.2%, +0.4%] |
| 20 s | ramp, d=2.0, SD×1.5 | -3.9% [-5.4%, -2.4%] | -1.0% [-1.8%, -0.2%] |
| 20 s | ramp, d=2.0, SD×2.0 | -3.3% [-4.7%, -1.9%] | -1.4% [-2.4%, -0.4%] |
| 40 s | step, d=0.5, SD×1.5 | +0.1% [-1.2%, +1.4%] | -0.2% [-1.0%, +0.6%] |
| 40 s | step, d=0.5, SD×2.0 | -1.4% [-2.9%, +0.1%] | +0.5% [-0.4%, +1.4%] |
| 40 s | step, d=1.0, SD×1.5 | -0.2% [-1.3%, +0.9%] | +0.0% [-0.7%, +0.7%] |
| 40 s | step, d=1.0, SD×2.0 | -0.6% [-1.9%, +0.7%] | +0.4% [-0.5%, +1.3%] |
| 40 s | step, d=2.0, SD×1.5 | -2.1% [-3.5%, -0.7%] | -1.2% [-2.2%, -0.2%] |
| 40 s | step, d=2.0, SD×2.0 | -1.3% [-2.6%, -0.0%] | -0.4% [-1.3%, +0.5%] |
| 40 s | ramp, d=0.5, SD×1.5 | -0.1% [-1.4%, +1.2%] | +0.0% [-0.9%, +0.9%] |
| 40 s | ramp, d=0.5, SD×2.0 | -1.8% [-3.2%, -0.4%] | +0.3% [-0.6%, +1.2%] |
| 40 s | ramp, d=1.0, SD×1.5 | -0.3% [-1.4%, +0.8%] | -0.1% [-1.0%, +0.8%] |
| 40 s | ramp, d=1.0, SD×2.0 | -0.6% [-2.0%, +0.8%] | +0.2% [-0.7%, +1.1%] |
| 40 s | ramp, d=2.0, SD×1.5 | -2.7% [-4.1%, -1.3%] | -1.0% [-2.0%, -0.0%] |
| 40 s | ramp, d=2.0, SD×2.0 | -2.1% [-3.5%, -0.7%] | -0.5% [-1.4%, +0.4%] |
| 60 s | step, d=0.5, SD×1.5 | -0.6% [-1.8%, +0.6%] | -0.3% [-1.0%, +0.4%] |
| 60 s | step, d=0.5, SD×2.0 | -2.5% [-4.0%, -1.0%] | -1.1% [-2.1%, -0.1%] |
| 60 s | step, d=1.0, SD×1.5 | +0.5% [-0.5%, +1.5%] | +0.2% [-0.5%, +0.9%] |
| 60 s | step, d=1.0, SD×2.0 | -1.2% [-2.5%, +0.1%] | -0.2% [-1.1%, +0.7%] |
| 60 s | step, d=2.0, SD×1.5 | +0.1% [-0.9%, +1.1%] | -0.1% [-0.7%, +0.5%] |
| 60 s | step, d=2.0, SD×2.0 | -0.3% [-1.5%, +0.9%] | +0.1% [-0.7%, +0.9%] |
| 60 s | ramp, d=0.5, SD×1.5 | -0.6% [-1.7%, +0.5%] | -0.2% [-0.8%, +0.4%] |
| 60 s | ramp, d=0.5, SD×2.0 | -3.2% [-4.8%, -1.6%] | -1.4% [-2.4%, -0.4%] |
| 60 s | ramp, d=1.0, SD×1.5 | +0.1% [-0.9%, +1.1%] | -0.5% [-1.1%, +0.1%] |
| 60 s | ramp, d=1.0, SD×2.0 | -1.3% [-2.6%, -0.0%] | -0.6% [-1.4%, +0.2%] |
| 60 s | ramp, d=2.0, SD×1.5 | -0.2% [-1.2%, +0.8%] | -0.6% [-1.3%, +0.1%] |
| 60 s | ramp, d=2.0, SD×2.0 | -0.8% [-1.9%, +0.3%] | -0.7% [-1.4%, +0.0%] |
| 120 s | step, d=0.5, SD×1.5 | -2.2% [-3.5%, -0.9%] | -1.0% [-2.0%, -0.0%] |
| 120 s | step, d=0.5, SD×2.0 | -4.2% [-6.0%, -2.4%] | -1.2% [-2.3%, -0.1%] |
| 120 s | step, d=1.0, SD×1.5 | -0.8% [-2.0%, +0.4%] | -0.4% [-1.4%, +0.6%] |
| 120 s | step, d=1.0, SD×2.0 | -2.7% [-4.2%, -1.2%] | -1.1% [-2.3%, +0.1%] |
| 120 s | step, d=2.0, SD×1.5 | -0.9% [-2.1%, +0.3%] | -0.7% [-1.6%, +0.2%] |
| 120 s | step, d=2.0, SD×2.0 | -1.2% [-2.4%, +0.0%] | -0.8% [-1.9%, +0.3%] |
| 120 s | ramp, d=0.5, SD×1.5 | -1.4% [-2.6%, -0.2%] | -0.6% [-1.4%, +0.2%] |
| 120 s | ramp, d=0.5, SD×2.0 | -3.9% [-5.6%, -2.2%] | -1.3% [-2.5%, -0.1%] |
| 120 s | ramp, d=1.0, SD×1.5 | -0.1% [-1.2%, +1.0%] | +0.0% [-0.9%, +0.9%] |
| 120 s | ramp, d=1.0, SD×2.0 | -2.3% [-3.7%, -0.9%] | -0.9% [-2.0%, +0.2%] |
| 120 s | ramp, d=2.0, SD×1.5 | -0.9% [-2.0%, +0.2%] | -0.5% [-1.4%, +0.4%] |
| 120 s | ramp, d=2.0, SD×2.0 | -0.9% [-2.2%, +0.4%] | -0.4% [-1.5%, +0.7%] |

## Resumo das diferenças pareadas

Entre 48 comparações pareadas de cenários mistos (quatro horizontes, seis degraus e seis rampas por horizonte), a soma teve 24 intervalos de 95% inteiramente abaixo de zero, nenhum inteiramente acima e 24 incluindo zero. Para L2, foram 14 abaixo, nenhum acima e 34 incluindo zero.

A diferença média pareada (alternativa menos máximo) foi -1.59 pontos percentuais para soma e -0.56 p.p. para L2.

Isso não demonstra que as alternativas sejam universalmente piores, mas não há evidência pareada de que recuperem a sensibilidade perdida em relação ao máximo. Os intervalos são aproximações normais e não foram ajustados por multiplicidade.

## Nota de auditoria

Um piloto inicial foi descartado: ele combinava os máximos separados dos dois sinais na validação, enquanto no teste combinava os sinais ponto a ponto antes de calcular o máximo. Para soma e L2, essas operações não são equivalentes e produziam limiares inflados. A execução final usa uma segunda passagem pela validação para calibrar os máximos das séries já combinadas ponto a ponto. Somente os resultados da execução corrigida são apresentados neste relatório.

## Interpretação e limites

- A comparação principal é entre regras com o mesmo orçamento empírico de alertas na validação. Incidências distintas no teste indicam deriva da distribuição ou do comportamento, não falsos positivos comprovados.
- Um ganho em cenários mistos não basta para declarar um detector superior: os controles de média-only e SD-only verificam se a fusão apenas favorece uma família de mudanças.
- O intervalo pareado é descritivo e normal-approximate; os cenários compartilham os mesmos jobs e múltiplas comparações são feitas. Não deve ser lido como confirmação independente.
- As perturbações alteram erros absolutos observados, não medições brutas de potência. O SD multiplier m implica variância nominal m² antes do truncamento.
- Sem rótulos reais e outros períodos temporais, não podemos estimar precisão, recall ou validade operacional. PM100 mede potência agregada por job/nó, não GPU-only.
- Nada nesta fase valida ATOCIA ou ATRP-1, economia de energia ou segurança térmica.

## Artefatos

- mixed_change_fusion_v1.py
- audit/mixed_change_fusion_v1.json
- PM100_MIXED_CHANGE_FUSION_V1.md

Os dados Parquet e os modelos anteriores não foram alterados.

**Fase encerrada; aguardar autorização antes de iniciar a próxima.**
