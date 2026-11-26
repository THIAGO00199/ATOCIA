# ATOCIA — Mapa de oportunidades industriais
Data: 2026-11-20
Status: pesquisa estratégica inicial; hipóteses comerciais, não validação de mercado.

## Resumo executivo

A oportunidade mais forte identificada até aqui não é um monitor de temperatura de servidores. É uma camada de inteligência temporal para cargas computacionais e infraestrutura elétrica de alta densidade: observar, caracterizar, antecipar e explicar oscilações e eventos que atravessam workload, consumo elétrico, distribuição de energia e refrigeração.

O DOE publicou em maio de 2026 uma análise específica de oscilações de carga em grandes data centers de IA. O PNNL publicou em setembro de 2026 uma metodologia e ferramenta pública para avaliar riscos de oscilações de grandes cargas em redes elétricas. Isso confirma que o problema existe e está sendo tratado por instituições técnicas. Não demonstra, por si só, que a ATOCIA tenha vantagem ou que exista demanda contratável para um novo fornecedor.

## Ranking preliminar de oportunidades

### 1. Observabilidade e previsão de oscilações elétricas em AI data centers
- Dor: workloads sincronizados produzem flutuações de potência; certas dinâmicas podem ser mal representadas por medições convencionais; há desafios de armazenamento e processamento de medições de alta resolução.
- Compradores possíveis: operadores hyperscale/neocloud/colocation, utilities, operadores de transmissão, integradores elétricos e fabricantes de sistemas de monitoramento.
- ATOCIA possível: detecção de regimes oscilatórios, previsão multi-horizonte, caracterização de frequência/amplitude/fase, associação temporal com workloads e explicações com incerteza.
- Prova exigida: dados sincronizados de carga e medições elétricas; comparação com métodos existentes; falsos alarmes baixos; lead time útil; validação em mais de um site/topologia.
- Prioridade: MUITO ALTA. É a correspondência mais direta com a tese original.

### 2. Inteligência temporal integrada de energia + workload + cooling
- Dor: telemetria IT e OT costuma estar distribuída entre BMS, PMS, servidores, CDUs, chillers, bombas e sistemas de workload. Sem alinhamento temporal, é difícil distinguir causa, consequência e atraso.
- Compradores possíveis: operadores de data centers, integradores de infraestrutura, OEMs de refrigeração e plataformas DCIM/BMS.
- ATOCIA possível: alinhar eventos, modelar atrasos e acoplamentos, prever demanda térmica/elétrica e explicar anomalias.
- Prova exigida: conectores interoperáveis, segurança OT/IT, qualidade temporal, integração com padrões e sistemas existentes; valor incremental demonstrado frente a plataformas atuais.
- Prioridade: MUITO ALTA, mas integração comercial é difícil.

### 3. Diagnóstico preditivo de infraestrutura crítica de energia
- Alvos: UPS, baterias estacionárias, transformadores, switchgear, geradores de backup, conversores e distribuição elétrica.
- Dor: falhas e degradação podem causar indisponibilidade, manutenção urgente e capacidade ociosa.
- ATOCIA possível: detectar assinaturas temporais precursoras e separar degradação lenta de eventos transitórios.
- Prova exigida: séries históricas de falhas/manutenção, dados de sensores e validação com fabricantes/operadores; precisão e explicabilidade.
- Prioridade: ALTA como adjacência; concorre com plataformas maduras de condition monitoring.

### 4. Previsão e coordenação de demanda flexível entre data center e rede
- Dor: conexão à rede, capacidade firme, variabilidade de carga e requisitos de estabilidade tornam-se restrições para expansão.
- ATOCIA possível: prever perfis de carga e cenários; recomendar janelas ou limites operacionais em conjunto com sistemas de gestão existentes.
- Prova exigida: integração com scheduling e sistemas elétricos, avaliação de custo/risco, governança e validação em ambiente simulado antes de qualquer piloto.
- Prioridade: ALTA estrategicamente, mas depende de dados e autoridade operacional que a ATOCIA não possui hoje.

### 5. Otimização temporal de refrigeração líquida e recuperação de calor
- Dor: maior densidade de racks amplia exigência sobre CDUs, circuitos líquidos, trocadores, bombas e integração com facility cooling; água e energia são restrições.
- ATOCIA possível: antecipar demanda térmica e transientes, detectar desvios e prever resposta de loops térmicos.
- Prova exigida: telemetria de fluxo, pressão, temperaturas de ida/retorno, estados de válvulas/bombas, carga dos equipamentos e condições ambientais.
- Prioridade: ALTA como módulo complementar, não como identidade central.

### 6. Usinas, geração distribuída e infraestrutura nuclear
- Dor potencial: confiabilidade, disponibilidade, manutenção preditiva, coordenação com cargas variáveis e integração de armazenamento/geração.
- ATOCIA possível: análise temporal de séries de sensores e previsão de anomalias em subsistemas não-safety-critical, em parceria com operador/OEM.
- Barreiras: certificação, segurança funcional, cibersegurança, dados proprietários, ciclo de venda longo e responsabilidade elevada. Sistemas nucleares têm exigências regulatórias e de segurança muito superiores às de um produto de analytics comum.
- Prioridade: BAIXA para entrada inicial; manter como expansão de longo prazo, sem propor controle autônomo.

## Sinais de mercado e referências

1. IEA, Powering AI (2026): hyperscalers devem investir mais de US$ 700 bilhões em capex em 2026; redes, equipamentos, localização e visibilidade temporal da demanda são restrições relevantes. Também destaca que flexibilidade computacional é difícil porque o operador nem sempre controla os workloads dos clientes.
   https://www.iea.org/reports/powering-artificial-intelligence/executive-summary

2. Uptime Institute Global Data Center Survey 2026: custos, disponibilidade de energia, previsão de capacidade, confiabilidade da rede e falta de profissionais estão entre as pressões do setor.
   https://intelligence.uptimeinstitute.com/resource/uptime-institute-global-data-center-survey-2026

3. DOE, Monitoring Oscillations from Large Data Centers (28 May 2026): workloads sincronizados de AI geram oscilações; PMUs têm limitações de banda/filtros para parte das dinâmicas; medições point-on-wave capturam mais detalhe, mas criam desafios de volume e processamento.
   https://www.energy.gov/oe/articles/monitoring-oscillations-large-data-centers

4. PNNL, Measurement Adequacy for Monitoring Data Center Oscillations (16 Apr 2026):
   https://www.pnnl.gov/publications/measurement-adequacy-monitoring-data-center-oscillations

5. PNNL, RATLLE / Methodology to Evaluate Grid Reliability Impact of Oscillations Induced by Large Loads (22 Sep 2026): metodologia pública de triagem, simulação e avaliação de risco de oscilações de grandes cargas.
   https://www.pnnl.gov/publications/methodology-evaluate-grid-reliability-impact-oscillations-induced-large-loads

6. Open Compute Project, Open Data Centers for AI: prioridades incluem soluções de energia e rede, SLAs, telemetria/gestão e métodos de estimativa de potência.
   https://www.opencompute.org/projects/strategic-initiatives/open-data-centers-for-ai/

7. Open Compute Project, Data Center Telemetry: destaca coleta e análise de métricas elétricas, térmicas e mecânicas, detecção proativa de falhas, PUE/WUE e fronteira segura entre OT e IT.
   https://www.opencompute.org/projects/data-center-facility/data-center-telemetry/

8. Open Compute Project, Cooling Environments: padronização de cold plates, CDUs, trocadores e tecnologias de resfriamento líquido.
   https://www.opencompute.org/projects/cooling-environments/

## O que pode diferenciar a ATOCIA

Não afirmar que "ninguém faz isso". Já existem DCIM, BMS, predictive maintenance, cooling optimization, power-quality analytics e ferramentas de avaliação de rede. A hipótese de diferenciação precisa ser testada:
- memória temporal explícita de transientes, atrasos e efeitos persistentes;
- previsão acoplada workload → potência → resposta térmica, em horizontes distintos;
- detecção e caracterização de oscilações com explicações e incerteza;
- transferência entre hardware/sites com pouca recalibração;
- avaliação de causas candidatas sem confundir correlação com causalidade;
- trilha auditável que funcione em shadow mode e não exija controle autônomo.

## Relação com a TDT

A TDT é a hipótese teórica que inspira a memória de irreversibilidade temporal da ATOCIA. Ela ainda não é teoria física validada. O produto não deve assumir que "débito temporal" equivale a energia, entropia, calor, desgaste ou temperatura. O teste científico é operacional: uma representação temporal inspirada na TDT precisa melhorar previsões, explicações ou transferência de domínio contra baselines fortes, com ablações que mostrem qual componente acrescenta valor.

## Próximo bloco de trabalho

1. Mapear datasets públicos e licenças para workload, potência, qualidade de energia e facility telemetry.
2. Construir benchmark offline de oscilações: segmentação, espectro, amplitude, periodicidade, sincronização e previsão multi-horizonte.
3. Comparar com baselines simples e modelos estabelecidos; split por sessão/dispositivo/site, nunca aleatório por amostra temporal.
4. Fazer matriz competitiva: o que já existe em DeepMind/Google, Siemens/Vigilent, EkkoSense, Schneider, PNNL/RATLLE e DCIM vendors.
5. Escolher uma única prova de conceito de alto valor e baixo risco; operar primeiro em análise offline e shadow mode.
6. Conversar com especialistas/operadores e validar linguagem de compra, dados disponíveis, custo do problema e processo de aquisição antes de construir uma solução comercial completa.

## Critério para dizer "achamos uma oportunidade de dinheiro"

Só avançar para tese comercial quando houver:
- comprador identificável e orçamento/dono do problema;
- perda ou custo mensurável que o problema causa;
- dados que permitam provar o problema;
- desempenho superior a alternativas relevantes em validação externa;
- integração e segurança compatíveis com o ambiente do cliente;
- piloto pago ou compromisso verificável de avaliação.
