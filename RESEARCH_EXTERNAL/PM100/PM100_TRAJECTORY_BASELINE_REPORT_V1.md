# PM100 — benchmark de baselines para trajetória de potência por job

**Data:** 21/11/2026  
**Tipo:** benchmark exploratório de métodos causais simples; não é resultado do ATRP-1.

## Pergunta
Durante a execução de um job GPU, até que ponto o histórico de potência agregada dos nós ajuda a prever o mesmo sinal 20, 40, 60 e 120 segundos à frente?

## Dados e protocolo
- PM100 v1 completo: 231.238 jobs; 210.573 com GPU alocada.
- Alvo: soma, por job, da potência de entrada das duas PSUs de todos os nós alocados; unidade W; amostragem 20 s.
- Jobs mantidos como sequências independentes; nunca concatenar jobs.
- Corte cronológico por quantis de start_time dos jobs GPU: 70% treino, 15% validação, 15% teste; jobs que cruzam fronteiras são descartados.
- 150.955 jobs foram utilizados após descartar sequências de um único ponto e jobs cruzando fronteiras; 321 cruzavam explicitamente os limites temporais.
- Horizontes: 20, 40, 60 e 120 s.
- Comparadores: persistência e médias móveis causais trailing MA(3), MA(5), MA(10).
- Escolha do tamanho da janela feita na validação, sem otimizar no teste.
- O teste contém entre 10.222 e 10.842 jobs por horizonte, com 5,74–5,79 milhões de previsões por horizonte.

## Resultado no teste
### Métricas micro — todas as previsões recebem peso igual
| Horizonte | Janela escolhida na validação | MAE persistência (W) | MAE MA escolhida (W) | Skill vs persistência |
|---|---:|---:|---:|---:|
| 20 s | MA(3) | 184,54 | 162,11 | 12,15% |
| 40 s | MA(3) | 180,15 | 165,39 | 8,20% |
| 60 s | MA(5) | 196,19 | 171,10 | 12,79% |
| 120 s | MA(5) | 207,45 | 184,63 | 11,00% |

### Métricas macro — cada job recebe o mesmo peso
Para evitar que jobs longos dominem o resultado, também foi calculada a média do MAE de cada job. Pela validação macro, MA(3) foi escolhida nos quatro horizontes.

| Horizonte | MAE macro persistência (W) | MAE macro MA(3) (W) | Skill macro vs persistência |
|---|---:|---:|---:|
| 20 s | 210,68 | 196,60 | 6,69% |
| 40 s | 212,28 | 202,82 | 4,46% |
| 60 s | 226,57 | 210,67 | 7,02% |
| 120 s | 257,54 | 243,52 | 5,44% |

## Interpretação
- Existe sinal temporal explorável no alvo agregado por job/nós: uma média móvel simples supera persistência no holdout cronológico nos quatro horizontes.
- A melhora é menor quando cada job recebe o mesmo peso (4,46–7,02%), o que é uma estimativa menos dominada por jobs longos.
- Isso é baseline, não descoberta de um modelo ATOCIA. Não prova que ATRP-1 supera métodos tradicionais.
- MAE absoluto em W depende do número e configuração de nós alocados; não comparar jobs de tamanhos diferentes sem estratificação ou normalização.
- RMSE é elevado em relação ao MAE, indicando erros extremos/outliers importantes.
- O alvo é agregado por job, não potência individual de GPU; PM100 não tem temperatura GPU.
- Sem intervalos de confiança por job, testes por subgrupos ou avaliação de mudanças de regime. Esses são próximos passos antes de qualquer alegação robusta.

## Próximo passo técnico
Implementar um modelo online intra-execução que use lags e metadados disponíveis até o instante de previsão, comparar com MA(3)/MA(5), persistência, EWMA e Ridge causal, e reportar micro + macro por job. Manter o teste PM100 como validação secundária e não confundir essa tarefa com previsão pré-execução de potência de jobs.
