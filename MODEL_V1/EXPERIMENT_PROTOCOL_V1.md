# ATOCIA — protocolo de avaliação do previsor V1
**Status:** pré-registro experimental inicial; sem resultados do ATRP-1.

## Objetivo primário
Prever potência futura de uma entidade física claramente identificada (GPU ou nó) usando apenas informações disponíveis até o instante de previsão.

## Dataset inicial
Candidato preferencial: AcmeTrace/Kalos, pois os prefixos inspecionados mostram matrizes alinháveis de potência, temperatura e utilização. A inspeção cobre apenas 62 instantes de 15 segundos; não é suficiente para treino nem para escolher definitivamente a série.

PM100 será trilha separada de potência de nó, não proxy de potência individual de GPU.

## Etapas obrigatórias
1. Auditoria de continuidade, frequência, lacunas, valores inválidos e unidades.
2. Seleção documentada de entidade(s) com cobertura suficiente.
3. Split temporal: treino inicial, validação posterior, teste final ainda intocado.
4. Implementação dos comparadores causais.
5. Implementação ATRP-1 após congelar o protocolo.
6. Ajuste de hiperparâmetros apenas em treino/validação.
7. Uma única avaliação final no holdout; se houver mudanças após olhar o teste, ele deixa de ser holdout e será necessário outro conjunto intocado.
8. Avaliação por entidade e horizonte; intervalos de incerteza e custo de inferência.
9. Relatório completo incluindo falhas, limitações e reprodutibilidade.

## Baselines
Persistência, MA(3), MA(5), MA(10), EWMA, Ridge autoregressivo e HistGradientBoosting tabular.

## Anti-vazamento
- Nenhuma janela cruza o limite de GPU/job.
- Nenhuma feature usa timestamp ou medição posterior ao instante t.
- Nenhuma normalização ou imputação ajustada com dados de teste.
- Nenhum embaralhamento aleatório de linhas.
- Os resultados de teste não orientam seleção de modelo.

## Critério de superioridade
O ATRP-1 só será considerado superior se reduzir MAE contra o melhor baseline escolhido na validação, no teste intocado, e mantiver resultado consistente em múltiplos horizontes e entidades. Publicar skill score, MAE, RMSE, cobertura e largura de intervalo. Não ocultar casos em que perde.

## Restrições de execução
Desenvolvimento e auditoria devem respeitar o uso normal do notebook. Não iniciar downloads grandes, instalação pesada, treino ou benchmarks enquanto houver jogo ou outra carga interativa ativa sem autorização explícita.

## 10. Separação entre trilha térmica e trilha de potência
O laboratório local já contém uma avaliação exploratória Ridge para temperatura (5/10/20 s) e uma baseline RC física condicional. Esses modelos devem ser comparadores na trilha térmica, não substitutos dos comparadores de potência GPU. A trilha ATRP-1 de potência deve usar dados externos com alvo físico e unidade confirmados. Resultados, splits e métricas das duas trilhas serão reportados separadamente. Ver `ARCHITECTURE_DECISION_V1.md`.

## 11. Uso correto do PM100 após auditoria integral
PM100 v1 tem 231.238 sequências, 20 s de amostragem e alvo \`power_consumption\` agregado por job/nós (soma das duas PSUs de todos os nós alocados). 81.481 jobs GPU possuem pelo menos 30 pontos. Pode servir como benchmark secundário para previsão da trajetória agregada do job durante a execução. Cada job é uma sequência independente: janelas não podem cruzar jobs e a divisão de treino/validação/teste deve agrupar por job e respeitar a cronologia.

Não usar PM100 como potência isolada de GPU ou para validar transientes subsegundo. Existe antecedente de 2026 para previsão pré-execução de potência de jobs usando PM100/F-DATA; não comparar tarefas distintas nem reivindicar originalidade nessa formulação.

## 12. Resultado de baseline externa PM100
No benchmark causal PM100, a média móvel escolhida apenas na validação superou persistência no teste cronológico: skill micro 8,20–12,79%; macro por job 4,46–7,02%. Esse é um baseline de potência agregada por job/nós, não um resultado do ATRP-1 nem uma avaliação per-GPU. Usar MA(3)/MA(5) como comparadores fortes em qualquer modelo de trajetória intra-execução. Ver \`RESEARCH_EXTERNAL/PM100/PM100_TRAJECTORY_BASELINE_REPORT_V1.md\`.
