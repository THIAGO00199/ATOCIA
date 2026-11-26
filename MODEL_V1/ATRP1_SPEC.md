# ATOCIA — especificação do previsor próprio V1
**Nome de trabalho:** ATOCIA Temporal Response Predictor (ATRP-1)  
**Estado:** desenho experimental; ainda não treinado nem validado.

## 1. Pergunta científica
Com sinais passados de potência, utilização e temperatura, o ATRP-1 consegue prever a potência futura de uma GPU (ou nó, conforme o dataset) com erro menor que baselines estatísticos e modelos convencionais, em blocos de dados que não participaram do desenvolvimento?

A unidade de previsão, o alvo físico e o horizonte devem ser fixados por dataset. Não misturar potência de nó com potência individual de GPU.

## 2. Hipótese testável
Uma representação temporal multiescala, que mantenha separadas a resposta rápida da carga e a memória lenta do estado térmico, pode reduzir o erro de previsão de potência em workloads com mudanças de regime, sem depender de modelos grandes.

A hipótese será rejeitada se o ATRP-1 não superar de forma consistente o melhor baseline no holdout, ou se o ganho desaparecer em outras GPUs/workloads.

## 3. Arquitetura candidata: memória multiescala + correção residual
Para cada série alinhada por dispositivo e timestamp, formar um vetor de sinais observados:
- potência atual e lags;
- utilização atual e lags;
- temperatura atual e lags;
- diferenças/derivadas causais entre observações;
- médias móveis exponenciais rápidas e lentas por sinal;
- variação recente e dispersão local;
- horizonte de previsão.

Duas memórias exponenciais são mantidas por sinal:
- estado rápido: acompanha alterações recentes de workload;
- estado lento: representa contexto persistente, incluindo resposta térmica mais demorada.

O previsor parte de uma referência simples e auditável (baseline causal selecionado somente no conjunto de validação) e aprende uma correção:
previsão(t+h) = baseline(t,h) + correção_aprendida(estado_temporal(t), h)

A correção inicial deve ser pequena e interpretável: Ridge ou HistGradientBoostingRegressor, escolhida por validação temporal. Não começar com Transformer/LSTM; primeiro provar que a representação temporal agrega valor.

## 4. Incerteza
Versão inicial deve estimar intervalos preditivos (quantis 10%, 50%, 90%) ou, se a amostra for insuficiente, fornecer intervalo empírico de erro calibrado no conjunto de validação. Medir cobertura e largura dos intervalos. Nunca chamar um intervalo de "confiança" sem calibração.

## 5. Comparadores obrigatórios
1. Persistência (último valor).
2. Médias móveis trailing 3, 5 e 10 observações.
3. EWMA, com parâmetro escolhido na validação.
4. Regressão autoregressiva linear/Ridge.
5. Modelo tabular convencional (HistGradientBoosting ou equivalente).
6. ATRP-1 completo.
7. Ablação: ATRP-1 sem estado lento; sem estado rápido; sem sinais cruzados; sem correção residual.

Todos os modelos recebem a mesma informação disponível no instante de previsão. Nenhum usa valores futuros, nem estatísticas calculadas sobre o conjunto completo.

## 6. Alvos e horizontes
- AcmeTrace/Kalos: série documentada em intervalos de 15 s; testar primeiro potência GPU em 15 s e 30 s à frente. 60 s apenas se houver continuidade suficiente.
- PM100: potência de nó, amostragem declarada de 20 s; alvo distinto e análise separada.
- Telemetria local do notebook: serve para instrumentação e exploração, não para alegar generalização a data center.

Os horizontes finais dependem da auditoria completa de qualidade e da unidade confirmada.

## 7. Divisão de dados sem vazamento
- Separar cronologicamente treino, validação e teste.
- Não dividir linhas aleatoriamente.
- Manter janelas inteiras dentro de uma única GPU/job; nunca concatenar séries de dispositivos diferentes.
- Congelar o teste antes de escolher features, hiperparâmetros ou arquitetura.
- Depois da avaliação temporal, realizar teste adicional por GPU ou workload não visto, se a cobertura permitir.
- Ajustar escalas, imputação, seleção de features e hiperparâmetros somente no treino/validação.
- Registrar explicitamente todas as exclusões e lacunas.

## 8. Métricas e regra de sucesso
Reportar MAE, RMSE, MASE ou skill score contra persistência, erro por horizonte e por entidade, cobertura dos intervalos, latência de inferência e tamanho do modelo.

Skill vs melhor baseline = 1 - MAE_ATRP1 / MAE_melhor_baseline.
Valor positivo significa erro menor; negativo significa pior desempenho.

Critério preliminar para continuar: ganho positivo no holdout para o alvo primário, em mais de um horizonte, sem degradação material em subgrupos relevantes. Reportar também resultados em que o ATRP-1 perde. Não declarar superioridade com base em um único recorte.

## 9. Limites
O previsor não controla hardware, não altera frequência, potência, ventilação ou políticas do cluster. Previsão melhor não prova economia de energia. Economia exige experimento operacional separado, com restrições de segurança e desempenho.

## 10. Referências técnicas iniciais
- Mammen et al., CUFF, ACM e-Energy 2023: previsão de demanda de GPU orientada à incerteza.
- Mo et al., "A Cross-Workload Power Prediction Method Based on Transfer Gaussian Process Regression in Cloud Data Centers", IEEE Transactions on Cloud Computing, 2025, DOI 10.1109/TCC.2025.3575790.
- NVIDIA DSX, Telemetry and Observability: correlação de métricas, logs e traces em infraestrutura de IA.

## 11. Estado atual e próximo passo
Ainda não há ATRP-1 implementado, treinado ou avaliado. Antes do código de treino:
1. concluir auditoria limitada de PM100;
2. ampliar a auditoria de cobertura do AcmeTrace sem baixar os ~2,6 GB de matrizes inteiras de uma vez;
3. confirmar unidades e identificar uma série GPU com continuidade suficiente;
4. congelar o protocolo e só então implementar o benchmark.

## 12. Integração com modelos ATOCIA já existentes
A auditoria do laboratório encontrou uma trilha térmica anterior: `thermal_physics.py` (RC físico condicional) e avaliação Ridge multi-horizonte em `PREDICTION_HORIZON_EVAL_2026-11-20.md`. Esses resultados pertencem à previsão de temperatura e não demonstram previsão de potência GPU. Ver `ARCHITECTURE_DECISION_V1.md` para a decisão de manter trilhas e alvos separados. O ATRP-1 continua condicionado à confirmação de unidades e continuidade do dataset externo.

## 13. Hipótese revisada após busca de anterioridade
A memória multiescala + correção residual permanece como implementação candidata simples, mas não é reivindicada como novidade. A pergunta principal passa a ser: o previsor mantém skill e calibração quando parte dos canais some, a cadência varia e o regime/workload/hardware de teste difere do treino?

A avaliação deve conter, quando os dados permitirem:
- cenário íntegro de referência;
- mascaramento de canais em padrões controlados e realistas, sem alterar o alvo;
- cadência irregular e atrasos simulados de observação, com regra de reamostragem causal;
- teste por workload/GPU/cluster não visto;
- avaliação de rampas, picos, erro em transições e antecedência útil, além de MAE/RMSE;
- calibração de intervalos e dependência temporal dos erros, sem alegar benefício decisório até testar um simulador de decisão.

A hipótese será rejeitada se o modelo não superar baselines robustos sob os cenários definidos, se a calibração degradar, ou se o custo/complexidade superar o benefício. A busca adicional identificou antecedentes em previsão DCGM per-GPU, adaptação cross-workload, domain adaptation e calibração probabilística; portanto, esta direção requer revisão sistemática e comparação direta antes de alegar originalidade.
