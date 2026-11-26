# ATOCIA — Roadmap: inteligência temporal e causal para data centers
Data: 2026-11-20

## Missão
Desenvolver uma plataforma que antecipe perturbações energéticas e térmicas em infraestruturas computacionais, investigue os mecanismos que as produzem, projete suas consequências e apoie decisões seguras.

A ATOCIA é fundamentada na pesquisa da TDT. O notebook é somente laboratório inicial; o mercado-alvo é data centers, clusters de IA, HPC e infraestrutura de grande escala.

## Fases técnicas

| Fase | Nome | Resultado | Critério de saída |
|---|---|---|---|
| 0 | Instrumentação e integridade dos dados | Coleta passiva, sensores, timestamps, unidades, qualidade e testes | Capturas auditáveis e reproduzíveis |
| 1 | Caracterização temporal | Identificar padrões, transientes, ciclos e atrasos em workloads e potência | Fenômenos reproduzidos em sessões independentes |
| 2 | Previsão de perturbações | Prever potência e eventos em 1–60 s e horizontes adequados | Superar baselines em sessões não vistas |
| 3 | Diagnóstico explicativo | Identificar fatores contribuintes e testar hipóteses | Explicações estáveis, ablações e evidência contra alternativas |
| 4 | Núcleo temporal TDT | Formalizar variáveis e hipóteses de memória/débito temporal | Definições matemáticas e ganho testável contra modelos convencionais |
| 5 | Acoplamento energético-térmico | Relacionar workload, potência, dissipação, temperatura e atraso | Previsões calibradas em dados independentes |
| 6 | Propagação multi-escala | Modelar GPU→servidor→rack→cluster→cooling/facility | Correspondência validada com dados e topologia |
| 7 | Gêmeo digital e contrafactuais | Simular cenários e comparar intervenções | Simulação calibrada e limites conhecidos |
| 8 | Otimização preditiva supervisionada | Recomendar escalonamento e cooling sob restrições | Benefício reproduzível sem piorar segurança/desempenho |
| 9 | Piloto industrial | Validar com operador, servidor GPU e depois rack/site | Replicação independente, segurança e benefício medido |
| 10 | Produto enterprise e escala | Integrações, segurança, suporte, licenças e parcerias | Cliente recorrente, integração repetível e economia unitária sustentável |

## Estado atual
- Fase 0: base de instrumentação local existente.
- Fase 1: exploração inicial em um notebook, não representativa de GPU ou data center.
- Fases 2–10: não validadas em escala-alvo.
- Dataset H100/B200 2026 e M100 ExaData identificados como fontes para a próxima etapa de pesquisa; consultar `ATOCIA_DATASET_RESEARCH_2026-11-20.md`.

## Primeiro sprint externo
1. Auditar estrutura, licença, timestamps e amostragem do dataset H100/B200.
2. Selecionar uma sessão multi-GPU e construir um subconjunto pequeno.
3. Medir amplitude, duração, frequência e alinhamento de oscilações de potência.
4. Criar previsões de potência com persistência, EMA, modelos autoregressivos e gradient boosting.
5. Avaliar temperatura GPU separadamente e respeitar o atraso térmico.
6. Investigar causas candidatas usando ablação e precedência temporal, sem alegar causalidade sem teste.
7. Só então testar a contribuição de uma memória temporal inspirada na TDT.

## Realidade competitiva
Google DeepMind, Siemens/Vigilent, EkkoSense, Schneider Electric e pesquisas acadêmicas já abordam partes da previsão térmica, otimização de cooling, workloads e energia. ATOCIA não deve alegar pioneirismo genérico. O diferencial precisa ser demonstrado por benchmark.

## Google e Intel
Google é referência de hyperscaler e possível destino de apresentação, colaboração ou carreira. Intel é referência de silício, plataformas, telemetria e infraestrutura de computação. O objetivo é construir evidência técnica reproduzível, não presumir parceria.

## Fase comercial de escala
A escala comercial depende de pilotos com valor operacional comprovado, contratos enterprise, integrações, segurança, suporte, distribuição e margens sustentáveis. Não há garantia de receita ou valuation.

## Segurança
Simulação → modo sombra → recomendação humana → piloto limitado, autorizado e supervisionado. Nenhuma ação autônoma em infraestrutura crítica sem interlocks, limites rígidos, auditoria, fallback e rollback.
