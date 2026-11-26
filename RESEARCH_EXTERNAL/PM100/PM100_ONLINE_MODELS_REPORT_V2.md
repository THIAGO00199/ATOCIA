# PM100 — previsão online intra-job: EWMA, Ridge e diagnóstico por idade do job

**Data:** 22/11/2026  
**Fase:** benchmark de modelos online e diagnóstico descritivo de não estacionariedade  
**Status:** concluída; aguardar confirmação para o próximo bloco  
**Dataset:** PM100 v1 — Marconi100, CINECA  
**Alvo:** potência agregada de entrada dos nós atribuídos a cada job (W), não potência isolada da GPU.

## 1. Pergunta

Durante a execução de um job GPU, modelos causais mais flexíveis que persistência e médias móveis conseguem prever a potência agregada 20, 40, 60 e 120 segundos à frente? O erro muda sistematicamente conforme o job avança?

## 2. Protocolo

- Arquivo original: `job_table.parquet`.
- SHA-256: `10bc1ba948cd362657e97eea9b5f96ff16d77ac6e8e0e78894d60e2074d4fd89`.
- Split cronológico original mantido: quantis 70%/85% de `start_time`; jobs que cruzam os limites são descartados.
- Treino: 94.763 jobs; validação: 17.998 jobs.
- O teste foi avaliado uma vez após a seleção na validação.
- Cada job é uma sequência isolada; arrays de jobs diferentes nunca são concatenados.
- Origem de previsão (t): somente observações do próprio job até (t). Alvo: (P_{t+h}).
- Modelos: persistência; MA(3); MA(5); EWMA; Ridge causal.
- EWMA: α selecionado na validação entre 0,05; 0,10; 0,20; 0,30; 0,50; 0,70; 0,90.
- Ridge: ajustado somente no treino, com padronização calculada no treino; penalidade selecionada na validação entre 0,01; 0,1; 1; 10; 100.
- Ridge usa 10 features disponíveis até a origem: potência em (t,t-1,t-2,t-4), médias móveis causais de 3 e 5 amostras, desvio-padrão de 5 amostras, inclinação (P_t-P_{t-2}), λ log(1 + GPUs alocadas) e λ log(1 + nós alocados).
- Métricas micro: todos os forecasts recebem peso igual. Macro: cada job recebe peso igual.

### Correção de cobertura

Uma primeira versão experimental exigia nove amostras de histórico e excluía uma fração excessiva de jobs curtos. Ela foi preservada como piloto, mas não é usada como resultado principal. A versão V2 reduz o histórico mínimo a quatro amostras e compara todos os métodos no mesmo suporte por horizonte.

O teste V2 inclui 10.278 jobs em 20 s, 10.222 em 40 s, 10.185 em 60 s e 9.844 em 120 s. Isso é mais próximo da cobertura do benchmark anterior, mas ainda exclui jobs curtos demais para formar as features causais.

## 3. Seleção feita na validação

| Horizonte | EWMA α selecionado | Ridge λ selecionado |
|---|---:|---:|
| 20 s | 0,70 | 100 |
| 40 s | 0,50 | 0,01 |
| 60 s | 0,30 | 100 |
| 120 s | 0,30 | 100 |

O Ridge selecionou um extremo da grade em três horizontes e apresentou pouca variação de MAE entre penalidades na validação. Isso é um sinal de que a configuração atual não está bem identificada pela grade; não justifica ampliar a busca depois de observar o teste.

## 4. Resultados no holdout

### MAE micro (W)

| Horizonte | Persistência | MA(3) | MA(5) | EWMA | Ridge |
|---|---:|---:|---:|---:|---:|
| 20 s | 183,58 | 161,15 | **159,17** | 166,20 | 171,09 |
| 40 s | 179,24 | 164,50 | 163,85 | **161,54** | 169,77 |
| 60 s | 195,42 | 172,33 | 170,36 | **168,77** | 182,57 |
| 120 s | 206,52 | 186,54 | 183,74 | **181,99** | 191,60 |

Skill micro do EWMA sobre persistência: **9,47%; 9,87%; 13,64%; 11,88%** nos quatro horizontes.

A EWMA não vence o melhor MA em 20 s: MA(5) tem MAE 7,03 W menor. Nos horizontes 40–120 s, a vantagem pontual do EWMA sobre MA(5) é pequena: 2,31 W; 1,60 W; 1,75 W. Sem intervalos pareados para essas diferenças, não se deve declarar superioridade estatística.

### MAE macro por job (W)

| Horizonte | Persistência | MA(3) | MA(5) | EWMA | Ridge |
|---|---:|---:|---:|---:|---:|
| 20 s | 184,42 | 172,84 | 182,23 | **170,96** | 192,24 |
| 40 s | 190,59 | 184,31 | 194,01 | **179,91** | 196,42 |
| 60 s | 210,92 | 198,23 | 206,84 | **198,07** | 217,33 |
| 120 s | 237,84 | 228,97 | 236,75 | **225,72** | 240,23 |

Skill macro do EWMA sobre persistência: **7,30%; 5,60%; 6,09%; 5,10%**.

A diferença macro EWMA–MA(3) é de apenas 1,88 W; 4,40 W; 0,16 W; 3,26 W. Em particular, 60 s é praticamente empate em ponto estimado.

### Ridge

O Ridge melhora a MAE micro sobre persistência, mas perde para MA(3), MA(5) e EWMA nos quatro horizontes. Na métrica macro, fica pior que persistência em todos os horizontes (skill entre −4,24% e −1,01%). A versão atual foi treinada com peso igual por forecast, de modo que jobs longos contribuem mais para o ajuste; o resultado macro desfavorável indica que a configuração não representa bem o desempenho médio por job.

**Conclusão sobre Ridge:** este primeiro Ridge causal, com lags, estatísticas locais e metadados de alocação, não demonstrou vantagem sobre os métodos de suavização simples. Não é evidência contra todo modelo Ridge possível; um Ridge com ponderação por job e/ou features diferentes seria outro experimento, que precisaria ser definido antes de consultar um novo holdout.

## 5. Diagnóstico de mudança de regime / idade do job

Foi calculada a MAE micro por tercil da posição temporal dentro de cada job (primeiro, segundo e último terço). Para EWMA:

| Horizonte | Primeiro terço | Terço central | Último terço |
|---|---:|---:|---:|
| 20 s | 175,80 W | 169,75 W | 152,99 W |
| 40 s | 170,56 W | 162,43 W | 151,59 W |
| 60 s | 177,71 W | 169,19 W | 159,37 W |
| 120 s | 191,35 W | 181,50 W | 173,08 W |

O erro cai do primeiro para o último terço em todos os horizontes. Mas a persistência também apresenta queda semelhante. Isso sugere que a previsibilidade da série varia com a idade do job, possivelmente por uma fase inicial mais instável, mas **não identifica uma mudança física de regime**.

Este bloco ainda não implementa CUSUM, Page-Hinkley, PELT ou outro detector formal de pontos de mudança. O diagnóstico por tercis é descritivo, feito depois da previsão, e não foi usado para ajustar o modelo.

## 6. Limitações

1. O holdout cobre apenas 11 datas de início (03–13/10/2020); não sustenta generalização temporal ampla.
2. Os ganhos do EWMA sobre MA(5) em 40–120 s são pequenos. Ainda faltam intervalos de confiança pareados para a diferença entre modelos.
3. O bootstrap temporal anterior foi feito para os baselines MA selecionados, não para estes resultados EWMA/Ridge; seus intervalos não podem ser reaproveitados como se cobrissem os novos modelos.
4. A estratificação por idade não substitui um detector de mudança de regime nem prova uma causa operacional.
5. O alvo é potência agregada de nós por job, não potência GPU individual; PM100 não contém temperatura GPU.
6. Esta tarefa é previsão online intra-job. Não é previsão pré-execução da potência total de um job.
7. MAE e RMSE absolutos dependem do tamanho/configuração do job; a métrica macro reduz, mas não elimina, essa heterogeneidade.

## 7. Conclusão da fase

- EWMA é competitivo: vence MA(5) por pequenas margens em 40, 60 e 120 s, e tem melhor MAE macro nos quatro horizontes.
- MA(5) continua melhor em micro a 20 s.
- Ridge não acrescentou valor sobre os baselines de suavização nesta configuração.
- O erro tende a diminuir ao longo da execução, mas isso é apenas um padrão por idade do job, não uma detecção formal de regimes.
- Nenhuma alegação de superioridade estatística do EWMA sobre MA pode ser feita sem bootstrap pareado específico para esta comparação.

## 8. Artefatos

- Script principal: `PM100/benchmark_online_models_v2.py`
- Resultado integral: `PM100/audit/trajectory_online_models_v2.json`
- Piloto de histórico longo, preservado para auditoria: `PM100/benchmark_online_models_v1.py` e `PM100/audit/trajectory_online_models_v1.json`
- Este relatório: `PM100/PM100_ONLINE_MODELS_REPORT_V2.md`

O Parquet original, os pesos ATRP-1 e os relatórios anteriores não foram alterados. A análise não treinou nem modificou ATRP-1.

**Fase encerrada. Aguardar confirmação antes de iniciar o próximo bloco.**
