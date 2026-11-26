# ATOCIA — Notas de concorrência e lacuna possível
Data: 2026-11-20
Status: leitura inicial de materiais públicos; não é due diligence competitiva completa.

## Descoberta central: Google já resolve uma parte — e diz que o ecossistema precisa de parceiros

O artigo técnico do Google Cloud de 11/02/2025 descreve uma abordagem full-stack para oscilações de potência e temperatura em infraestrutura de ML:
- instrumentação no compilador TPU para reconhecer sinais ligados a flutuações, como flags de sincronização;
- balanceamento dinâmico da atividade de blocos de computação;
- mitigação proativa no nível de workload/hardware, com sobrecusto de desempenho descrito como pequeno;
- visão de co-design entre chip, software, hardware e data center.

O mesmo artigo enumera riscos em retificadores, transformadores, geradores, cabos, busways, UPS e concessionárias. E, muito importante para a tese comercial, o Google pede colaboração do ecossistema: utilities para métricas padronizadas de qualidade de energia; fornecedores de energia e refrigeração para robustez; fabricantes e projetistas para soluções de rack; desenvolvedores de modelos para mitigações de software.

Implicação: a ATOCIA não deve se vender como "a solução que ensina o Google a suavizar suas TPUs". O Google já tem instrumentação e controle próprios. A oportunidade mais realista é uma camada complementar e interoperável para operadores, utilities, fabricantes e instalações heterogêneas que não têm o mesmo controle vertical de um hyperscaler.

Fonte: https://cloud.google.com/blog/topics/systems/mitigating-power-and-thermal-fluctuations-in-ml-infrastructure

## Intel também já tem monitoramento e gestão

Materiais públicos da Intel descrevem:
- Intel Data Center Manager: saúde, potência, temperatura, utilização, inventário e firmware; gestão por servidor, rack e data center.
- Intel Application Energy Telemetry e Platform Monitoring Technology: visibilidade de energia e telemetria de plataforma.
- RAPL/Platform RAPL e recursos de gestão de potência.

Implicação: não competir em dashboard, inventário, leitura básica de sensores, alertas triviais ou controle de potência de servidor. A ATOCIA precisa demonstrar algo que as plataformas atuais não entregam sozinhas: previsão temporal multiescala, caracterização de oscilação, alinhamento IT/OT e diagnóstico causal com validação rigorosa, ou integração entre ecossistemas heterogêneos.

Fontes:
https://www.intel.com/content/www/us/en/server-management/intel-server-management.html
https://www.intel.com/content/www/us/en/content-details/929781/data-center-sustainability-and-energy-efficiency-guide.html

## OCP revela onde o mercado está tentando padronizar

A iniciativa Open Data Centers for AI lista como prioridades:
- energia e conexão com a rede;
- SLAs abertos;
- telemetria e gestão;
- métodos de estimativa de potência;
- designs de referência para facilities de IA.

O projeto de Data Center Telemetry destaca a fronteira entre dados OT (BMS/PMS) e redes IT dos clientes. OCP Cooling Environments trabalha com interfaces e padronização de CDUs, cold plates e sistemas líquidos.

Implicação: interoperabilidade, timestamps, qualidade de dados, segurança OT/IT e interfaces são requisitos de produto, não detalhes para depois. ATOCIA deveria nascer como camada analítica de leitura e integração, respeitando os sistemas existentes e sem assumir controle direto de equipamentos.

## Lacuna de produto a testar

Hipótese: existe espaço para um "temporal intelligence layer" independente de fabricante que:
1. ingere séries temporais de workload, servidor, potência e facility;
2. reconcilia relógios, atrasos e granularidades diferentes;
3. detecta e classifica oscilações e eventos;
4. prevê potência e demanda térmica em múltiplos horizontes;
5. associa padrões a workloads e condições de infraestrutura;
6. informa incerteza, evidência e hipóteses concorrentes;
7. oferece API/relatórios para DCIM, BMS, PMS, utilities e ferramentas de planejamento;
8. opera primeiro em modo somente leitura/shadow mode.

Isto ainda é uma hipótese. Pode já haver fornecedores que façam partes relevantes. É necessário comparar com Siemens/Vigilent, EkkoSense, Schneider Electric, plataformas DCIM, ferramentas de power quality e PNNL RATLLE.

## Ponto de entrada comercial provável

Não começar tentando vender para Google como se fôssemos substituir sistemas internos. Um caminho mais plausível:
- pesquisa reproduzível com datasets públicos;
- prova de conceito em dados de laboratório ou parceiro autorizado;
- demonstração offline para especialistas em data center power/cooling;
- integração de leitura com um sistema existente;
- piloto shadow-mode com métricas e operador responsável;
- só então avaliar contrato e escala.

Compradores potenciais de entrada: integradores de infraestrutura, fornecedores de monitoramento/telemetria, operadores de colocation/neocloud e utilities que precisem caracterizar grandes cargas. O comprador e o orçamento ainda precisam ser confirmados.

## Fontes-chave

Google Cloud (2025): https://cloud.google.com/blog/topics/systems/mitigating-power-and-thermal-fluctuations-in-ml-infrastructure
Intel Server Management: https://www.intel.com/content/www/us/en/server-management/intel-server-management.html
Intel Sustainability and Energy Efficiency Guide: https://www.intel.com/content/www/us/en/content-details/929781/data-center-sustainability-and-energy-efficiency-guide.html
OCP Open Data Centers for AI: https://www.opencompute.org/projects/strategic-initiatives/open-data-centers-for-ai/
OCP Data Center Telemetry: https://www.opencompute.org/projects/data-center-facility/data-center-telemetry/
OCP Cooling Environments: https://www.opencompute.org/projects/cooling-environments/
DOE Oscillation Monitoring: https://www.energy.gov/oe/articles/monitoring-oscillations-large-data-centers
PNNL RATLLE paper: https://www.pnnl.gov/publications/methodology-evaluate-grid-reliability-impact-oscillations-induced-large-loads


## Atualização da investigação — 20 Nov 2026 (rodada adicional)

### Novas descobertas que reduzem o espaço competitivo

1. NVIDIA Minerva (lançada em 22 Oct 2026)
- Observabilidade AIOps para AI factories.
- Ingere telemetria de GPUs, Spectrum-X, NVLink, SuperNICs, DPUs, schedulers e workloads; usa knowledge graph, ML, detecção de anomalias, correlação topológica e análise de causa provável.
- DSX OS/Minerva Collector pode correlacionar sinais de infraestrutura com sinais de facility.
- Consequência: não construir observabilidade genérica, correlação GPU/job/rede, alertas de falha ou RCA genérico.
- Fonte: https://blogs.nvidia.com/blog/minerva-platform-infrastructure/ e https://www.nvidia.com/en-us/networking/products/software/minerva/

2. Reactive Technologies / Nyquist
- XMU2 declara 24-bit, 512 kS/s por canal, 8 canais, GPS time sync sub-microsecond e análise de supraharmonics de 2–150 kHz.
- Em piloto próximo a uma conexão de data center, a empresa relata emissões em 76.3 kHz, com bursts recorrentes.
- Nyquist já oferece licenciamento OEM de medição, DSP, edge AI, infraestrutura de dados, correlação temporal/espacial, oscilação, qualidade de energia e supraharmonics.
- Consequência: não competir em sensor, captura de waveform, sincronização, analytics elétrico genérico, nem presumir que correlação temporal de eventos elétricos esteja vaga. Possível rota futura: parceria/licenciamento como consumidor/integração de software, mas só se existir contribuição distinta e direitos de integração.
- Fontes: https://reactive-technologies.com/nyquist-xmu2-on-data-centre-supraharmonics/ ; https://reactive-technologies.com/nyquist/

3. Inertiafy OneKernel DC
- Produto comercial para modelos de data centers em PSCAD e PSS/E compilados do mesmo kernel, com settings compartilhados, perfis TSO, estudos e suporte de integração/validação.
- Alvos declarados: hyperscalers, desenvolvedores de data centers, fabricantes UPS, TSOs e utilities.
- A página diz que a validação HIL ou contra hardware específico é escopo separado; a comparação publicada é simulação entre plataformas, não certificação física.
- Consequência: não construir outro modelo genérico de ride-through PSCAD/PSS/E nem duplicar settings manager. Possível espaço: dados/telemetria reais para calibrar e manter modelos site-specific ao longo do ciclo de vida, mas verificar fornecedores e exigência de acesso a dados.
- Fonte: https://inertiafy.com/

4. Sandia/UT Austin measurement-informed load modeling
- Framework padroniza traces públicos de GPU (MIT SuperCloud, NLR, York University), combina workloads e adiciona cooling, conversão e auxiliares para formar perfis de carga facility/grid.
- Ainda está em andamento a validação contra medições de instalações em escala real.
- Consequência: a ponte trace→perfil grid-facing já existe em pesquisa; não alegar novidade. A questão de generalização/validação em instalações reais pode permanecer, mas requer parceria e dados reais.
- Fonte: https://www.nationalacademies.org/projects/CAST-PSSI-26-01/resources

5. Pesquisa de previsão probabilística de carga orientada à rede (arXiv 2611.08929, 6 Nov 2026)
- Benchmark com telemetria medida de cluster AI de 448 GPUs.
- Mostra que intervalos marginais de previsão podem ficar mal calibrados após mudança de regime; calibração online por regime melhora cobertura.
- Reconstruir dependência temporal dos erros melhora realismo das rampas e reduz custo de reserva realizado em 7.4–10.6% nos três problemas estudados.
- Consequência: forecast de potência isolado é insuficiente. O valor operacional está em calibração de incerteza, dependência temporal, cenários de rampas e custo de decisão.
- Fonte: https://arxiv.org/abs/2611.08929

6. Sub-second federated GPU power forecasting (20 Nov 2026)
- Estudo com três nós MIT Supercloud como proxy-silos; horizonte one-step de ~0.1s; FedProx reduz MAE médio 4.8% vs local, ficando 1.6% pior que centralizado.
- Não é forecast de forma de onda AC nem previsão multi-step/decisão operacional.
- Consequência: forecast de GPU subsecond e federated learning já têm trabalho publicado. Diferenciação precisa estar em decisão/integração, robustez de regime e escala/site, não só arquitetura ML.
- Fonte: https://www.mdpi.com/3042-8831/1/3/15

7. Inertiafy e GridStrong competem em modelos e compliance
- GridStrong oferece automação de testes, gestão de modelos, regras de operador e evidência de compliance.
- Inertiafy vende modelo dinâmico para PSCAD/PSS/E.
- Consequência: não construir generic model validator, NERC report automation ou generic PSCAD model.

### Lacunas candidatas após esta rodada

A. Model-to-reality lifecycle — hipótese ainda não validada
- Serviço/software que compara continuamente o modelo dinâmico site-specific usado em PSCAD/PSS/E com eventos e medições reais (PMU/POW/SCADA/UPS/IT telemetry), quantifica desvio por regime, recomenda recalibração e mantém rastreabilidade entre firmware, configuração, workload e modelo.
- Diferenciação pretendida: não apenas teste estático do modelo; medir drift ao longo da vida operacional e sob regimes reais de workload.
- Risco: GridStrong cobre model management/verification e Inertiafy customiza modelos; Reactive cobre dados/analytics. Pode haver concorrente fazendo a combinação por consultoria.
- Prova necessária: entrevistas com 5–10 engenheiros de estudos/operadores/OEM; obter exemplo de modelo e evento real; verificar se atualização contínua é dor com orçamento.

B. Probabilistic workload-to-grid scenarios — hipótese ainda não validada
- Converter previsão probabilística de workload GPU em cenários temporais de potência facility/grid, incluindo sincronização de jobs, cooling/UPS auxiliares, limites de rampas e dependência temporal entre erros.
- Entregar cenários auditáveis para estudos de conexão, reserva e operação, com exportação para ferramentas existentes, não substituí-las.
- Diferenciação pretendida: calibração e cenários temporais ligados a decisões, com validação em dados de site.
- Risco: Sandia/UT framework, papers de previsão, Inertiafy, ferramentas de consultoria e fornecedores de simulação já cobrem partes importantes.
- Prova necessária: benchmark independente, comparação com modelos existentes e demonstração de impacto em decisões reais.

C. Industrial flexible capacity digital twin — adjacência fora de AI data centers
- Estimar flexibilidade firme por processo industrial/cogeração, considerando estado, rampas, duração, recuperação, sazonalidade e custo produtivo.
- Pode ter comprador mais próximo no Brasil (agregadores, consumidores industriais, comercializadoras), mas a AXIA já oferece plataforma de agregação e simulação.
- Não construir calculadora de oferta; investigar se falta previsão de disponibilidade por processo com risco de não entrega e recuperação.
- Requer dados reais de planta e expertise de processo/energia.

### Decisão provisória

A melhor hipótese técnica restante é A ou B, não ATOCIA genérica. Não há ainda pilha de dinheiro confirmada. A existência de padrões, capex e concorrentes prova importância do problema, não disposição de pagar por nosso produto.

Próximo passo mais valioso: validar comprador e dor por entrevistas técnicas antes de mais engenharia. Para manter progresso científico, montar benchmark offline que compare:
- previsões determinísticas e probabilísticas;
- calibração de intervalos por mudança de regime;
- geração de trajetórias temporais/rampas;
- modelos simples vs ML;
- agregação de múltiplos traces com sincronização e atrasos;
- métricas de custo de decisão (reserva, margem, violação, desperdício), não apenas MAE.

Não afirmar causalidade de workload→evento elétrico sem sincronização de relógios, telemetria de workload e evidência de intervenção ou mecanismo físico.


## Atualização adicional — validação de modelos e alternativa industrial

### D. Model-to-reality / digital twin — concorrência e risco

- Literatura recente sobre co-simulação e validação de redes com eletrônica de potência descreve workflow offline EMT → SIL/CHIL/PHIL → campo; identifica ajuste de parâmetros, firmware oculto, parasitas, ruído e atrasos de sensores como fontes de divergência; defende feedback de medições de campo e recalibração contínua.
- Guia público WECC de validação de modelos IBR descreve comparar simulação com medições reais, coletar eventos repetíveis e perturbações reais e ajustar parâmetros quando há discrepâncias.
- Há artigo 2026 de digital twin para manutenção de data centers conectados à rede com modelagem, detecção de anomalias e RCA. Isso impede chamar a proposta ampla de inédita.
- Possível lacuna comercial não é digital twin genérico: seria automação de workflow para comparar um modelo específico com eventos físicos reais, versionar mudanças e produzir evidência reproduzível para o engenheiro. Mesmo isso precisa de entrevistas e concorrência mais profunda.
- Fontes:
  https://link.springer.com/article/10.1007/s43236-026-01394-1
  https://www.wecc.org/sites/default/files/documents/meeting/2026/IBR%20Power%20Plant%20Modeling%20and%20Validation%20Guideline.pdf
  https://www.sciencedirect.com/science/article/pii/S3050744826000137

### E. Flexibilidade industrial — oportunidade adjacente, mas concorrência presente

- EPE reporta que o mecanismo brasileiro de Resposta da Demanda contratou 344 MW no 3º Mecanismo Competitivo de julho de 2026; segmentos incluem metalurgia, alumínio, madeira, papel/celulose e química.
- A EPE descreve avaliação de flexibilidade por processo considerando tempo de resposta, duração, frequência de acionamentos, recuperação, impacto na produção e restrições operacionais. Empresas tendem a preferir deslocamento de produção ou geração própria a cortes que destruam produção.
- ABB Ability EMS já oferece monitoramento, previsão, planejamento e otimização, incluindo peak shaving, load shedding e deslocamento de produção com base em flexibilidade de processo.
- InAnalytics anuncia um modelo integrado mercado→máquina, conectando preços, energia, planos de produção, estados de equipamento, restrições de processo, CHP, armazenamento e previsão.
- Pesquisas acadêmicas também modelam buffers, sequenciamento, materiais e produção para otimização de resposta à demanda.
- Conclusão: não criar software de gestão energética industrial genérico. Um possível micro-nicho seria estimar a capacidade firme de flexibilidade por processo e risco de não entrega com dados reais, mas precisamos achar um agregador ou indústria que confirme uma lacuna não coberta.
- Fontes:
  https://www.epe.gov.br/sites-pt/publicacoes-dados-abertos/publicacoes/PublicacoesArquivos/publicacao-1000/EPE-DEA-DEE-SEE-SGR-NT-01-2026.pdf
  https://new.abb.com/industrial-software/sustainability/energy-management-system-ems/complete-energy-flow
  https://www.inanalytics.io/energy-intelligence
  https://www.sciencedirect.com/science/article/pii/S036054422601978X

### Avaliação atualizada

A evidência mais clara de orçamento e adoção está no mercado de modelos dinâmicos de grandes cargas, monitoramento de qualidade de energia e otimização de flexibilidade. Porém, cada camada já possui fornecedores especializados. Não há base para afirmar que a ATOCIA encontrou um espaço sem concorrência.

A melhor estratégia é uma prova estreita que complemente ferramentas existentes:
1. importar dados públicos e traces GPU;
2. construir cenários probabilísticos de carga com incerteza e dependência temporal;
3. comparar com os perfis e modelos públicos de ERCOT/Texas A&M, NLR e trabalhos Sandia;
4. gerar artefatos exportáveis e relatórios reproduzíveis para um engenheiro avaliar;
5. procurar feedback de engenheiros de estudos, utilities, consultorias, OEMs ou agregadores antes de desenvolver conectores comerciais.

Não investir agora em dashboard, sensores, monitoramento GPU genérico, compliance genérico, controle de cooling, modelo PSCAD genérico ou plataforma de despacho de flexibilidade.
