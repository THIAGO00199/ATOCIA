# ATOCIA — decisão de arquitetura integrada V1
**Data:** 21/11/2026  
**Estado:** decisão de desenho baseada em auditoria documental; nenhum novo treino foi executado nesta revisão.

## 1. Decisão principal: separar dois problemas preditivos
A revisão do laboratório existente encontrou um modelo térmico RC físico e uma avaliação Ridge de temperatura que antecedem o ATRP-1. Eles devem ser reaproveitados como baselines, mas não misturados com o alvo de potência GPU.

### Trilha A — previsão do estado térmico
- Alvo: temperatura futura do sensor/equipamento explicitamente identificado.
- Baselines já existentes: persistência, extrapolação de tendência, Ridge temporal e projeção RC condicional.
- Resultado local existente: Ridge teve MAE/RMSE agregados de 0,83/1,07 °C (5 s), 1,00/1,27 °C (10 s) e 1,33/1,62 °C (20 s), contra persistência 0,85/1,30 °C, 1,12/1,64 °C e 1,69/2,19 °C, respectivamente.
- Interpretação: resultado exploratório no mesmo notebook, com sensores quantizados e sem ambiente/RPM. É evidência preliminar de previsão térmica local, não validação em GPU/data center nem prova de superioridade geral.
- O RC de um nó é uma projeção física sob potência e ambiente futuros constantes. Não é um previsor de workload e não deve ser comparado como se antecipasse potência futura desconhecida.

### Trilha B — previsão de potência
- Alvo primário candidato: potência individual de GPU em AcmeTrace/Kalos, somente após confirmar unidades, continuidade e identidade do sensor.
- Baselines locais já existentes para sinais do notebook: persistência e médias móveis causais. Na sessão local reservada, médias móveis reduziram MAE frente à persistência para package power, PSys e proxy de atividade GT; isso não valida potência individual de GPU.
- ATRP-1 será desenvolvido para esse alvo apenas depois da auditoria do dataset. PM100 é trilha secundária de potência registrada no nível do job/nó, não potência isolada de GPU e sem temperatura GPU.

## 2. Arquitetura candidata após a auditoria
Não criar uma rede neural grande por padrão. Começar com um benchmark causal reprodutível:
1. Persistência, médias móveis trailing e EWMA.
2. Ridge autoregressivo com lags e diferenças causais.
3. HistGradientBoosting, se o volume e a validação justificarem.
4. ATRP-1: estado rápido + estado lento por canal, variação recente e correção residual sobre a melhor baseline escolhida apenas na validação.
5. Ablações para verificar se a memória rápida/lenta e os sinais cruzados realmente agregam valor.

A trilha térmica pode avaliar um módulo RC como baseline física e um Ridge de temperatura como baseline estatística. A trilha de potência não herda automaticamente os resultados da trilha térmica.

## 3. Protocolo e generalização
- Congelar alvo, unidade, frequência, horizonte, entidades e split antes do ajuste.
- Fazer split cronológico agrupado por GPU/job/sessão. Nunca criar janelas que atravessem fronteiras.
- Manter holdout intocado; se o modelo for alterado após ver o holdout, reservar novo teste.
- Reportar MAE/RMSE, skill contra persistência e melhor baseline, resultados por entidade/regime, cobertura/largura de intervalos, latência e memória.
- Testar separadamente robustez a sensores ausentes, cadência irregular e mudança de workload; não incluir tudo na primeira versão sem dados suficientes.
- Uma melhoria preditiva não demonstra economia de energia nem autoriza controle de hardware.

## 4. Auditorias de dados — achados e bloqueios
### AcmeTrace/Kalos
- Prefixos inspecionados: 62 timestamps alinhados a cada 15 s, 2.344 IDs GPU e apenas 4 IDs com >=80% de triplas completas nesse trecho.
- Um ID teve 62/62 triplas completas, mas isso não demonstra continuidade no arquivo inteiro.
- Unidades ainda não confirmadas pelo schema consultado. Valores brutos não podem ser rotulados como W, °C ou % até confirmação documental.
- Os três CSVs somam cerca de 2,62 GB. Não baixar tudo de uma vez; ampliar a auditoria seletivamente por Range/recortes ou por um subconjunto escolhido.

### PM100 v1
- Parquet local de ~106 MB; o script de auditoria está pronto e limita DuckDB a 1 thread e 512 MB.
- A auditoria ainda não foi executada: não há resumo de qualidade, checksum revalidado nesta etapa, distribuição nem amostras verificadas pelo script.
- Documentação do dataset descreve séries de potência por job no nível do nó; a tabela de features declara listas inteiras e intervalo de 20 s. A unidade física ainda precisa ser confirmada antes de rotular valores em watts.
- O script de extração original combina leituras dos sockets de entrada de energia dos nós alocados. Isso reforça que não se deve interpretar o alvo como potência GPU isolada.

## 5. Próximas ações ordenadas
1. Em janela sem jogo/carga interativa, executar auditoria limitada PM100 (20.000 jobs, 1 thread, 512 MB) e ler o dicionário/código para resolver unidade e semântica do alvo.
2. Ampliar a auditoria AcmeTrace sem download integral, procurando séries com continuidade suficiente e confirmando unidades.
3. Escolher um alvo primário e congelar o protocolo específico do dataset.
4. Implementar baselines causais primeiro; verificar métricas e vazamento.
5. Implementar ATRP-1 e ablações.
6. Avaliar uma única vez no holdout intocado; se não superar os comparadores, registrar o resultado e revisar a hipótese.

## 6. Decisão de execução nesta revisão
O processo Sober/Roblox estava ativo com uso elevado de CPU. Esta revisão foi somente leitura e documentação; não foram executados downloads, instalações, auditorias computacionais, treino ou benchmarks. Nenhuma configuração do Garuda foi alterada.

## 7. Efeito da revisão internacional adicional
A revisão de 21/11/2026 encontrou Acun et al. (BU/LBNL), que já fazem previsão per-GPU em produção com DCGM, LSTM, adaptação por aplicação e inferência muito rápida; e Yao et al. (arXiv:2611.08929), que avaliam calibração probabilística, dependência temporal e custo de reserva em cluster de 448 GPUs. Assim, memória multiescala, baixo custo, sinais cruzados e incerteza não são diferenciais exclusivos por si só.

A hipótese mais forte a investigar é robustez sob sensores ausentes/cadência irregular e generalização entre regimes, workloads e plataformas não vistos, acompanhada de avaliação de rampas/picos e valor decisório. Deve ser confrontada com métodos de domain adaptation, transfer learning, calibração online e baselines de sequência. Não alegar pioneirismo brasileiro: a busca pública encontrou pesquisa nacional em previsão energética de data centers em escalas mais agregadas, mas não permite concluir que operadores brasileiros não usem sistemas proprietários equivalentes.

## 8. Resultado da auditoria completa PM100
A auditoria integral concluiu: 231.238 jobs, 65.173.805 amostras, 210.573 jobs com GPU alocada e 81.481 jobs GPU com pelo menos 30 amostras (10 min a 20 s). Mediana de comprimento de sequência = 10 amostras. MD5 do Parquet confirmado. O schema real usa \`power_consumption\` (\`INTEGER[]\`), não \`node_power_consumption\`.

PM100 agrega, a cada 20 s, a potência de entrada das duas PSUs de todos os nós alocados a cada job; a unidade W é sustentada pelo mapeamento das métricas M100. É adequado para uma trilha secundária de previsão online da potência agregada do job durante a execução, mas não para previsão individual per-GPU ou temperatura GPU.

Um artigo de 2026 já usa PM100 e F-DATA para previsão pré-execução de potência de jobs (mínimo/média/máximo). Logo, essa tarefa não pode ser reivindicada como novidade. A previsão online intra-execução da trajetória temporal é uma pergunta diferente, a validar com split por job e sem concatenar séries.

## 9. Benchmark PM100: baselines causais de trajetória intra-execução
Foi executado benchmark completo no PM100 v1 para jobs GPU, com divisão cronológica por start_time (treino/validação/teste), jobs que cruzavam fronteiras excluídos e sequências nunca concatenadas. Foram usados persistência e MA(3/5/10), com janelas escolhidas na validação.

No teste, o melhor MA selecionado por validação teve skill micro de 8,20–12,79% frente à persistência (20–120 s). Como jobs longos poderiam dominar, também foi calculada métrica macro com peso igual por job; escolhendo MA(3) pela validação macro, a melhora no teste ficou entre 4,46–7,02%. Teste: 10.222–10.842 jobs por horizonte e 5,74–5,79 milhões de previsões por horizonte.

Isso demonstra apenas que uma média móvel causal supera persistência neste alvo agregado de potência por job/nós, em um holdout cronológico. Não testa ATRP-1, não é potência individual de GPU e não demonstra vantagem da ATOCIA. Relatório: \`RESEARCH_EXTERNAL/PM100/PM100_TRAJECTORY_BASELINE_REPORT_V1.md\`; script: \`PM100/benchmark_job_trajectory_baselines.py\`; saída integral: \`PM100/audit/trajectory_baselines_v1.json\`.
