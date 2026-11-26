# ATOCIA — Hipótese de oportunidade: Grid Event Assurance

Data: 20/11/2026
Status: hipótese comercial e técnica; não é produto validado.

## 1. Problema observado

Em 22/07/2026, mais de 3 GW de carga de data centers desconectaram abruptamente na região da PJM após uma falha em linha de transmissão, com transferência para alimentação de backup.

O ponto de conexão (POI) registra o efeito elétrico, mas nem sempre identifica sua causa. Um artigo de 28/10/2026 demonstra que, em certas condições, uma queda de carga decorrente de mudança de workload e uma transferência/desconexão de equipamentos podem produzir os mesmos sinais quasi-estáticos de tensão e corrente no POI. A separação pode depender da resposta transitória, banda de gravação, ruído, dados de workload e calibração. O estudo indica que a potência na saída do UPS pode ser um sinal mais adequado do que a potência medida na entrada da instalação em determinados cenários.

A NERC publicou a família CLO-001/002/003, adotada pelo Board em 26/10/2026 e protocolada na FERC em 16/11/2026. Em 20/11/2026 estava pendente de aprovação regulatória, ainda não em vigor. Os padrões cobrem interconexão/modelos, dados operacionais/comunicações, proteção e monitoramento de perturbações.

## 2. Hipótese de produto

**ATOCIA Grid Event Assurance** — camada independente de análise pós-evento que liga evidências externas da rede e evidências internas do data center para reconstruir, com confiança quantificada, o que aconteceu.

Entradas possíveis:
- POI: tensão, corrente, potência real/reativa, waveform/DFR/FR/PMU;
- SER, estados de disjuntores e eventos de proteção/relés;
- UPS input/output, transferência para bateria/backup e estado de geradores;
- BMS/CDU/chiller/bombas/ventiladores;
- metadados de workload/GPU/scheduler/power caps;
- versões de modelos, configurações e firmware.

Saídas possíveis:
- linha do tempo sincronizada com incerteza de relógio e latência;
- hipóteses concorrentes: redução real de workload, desconexão parcial, transferência para backup, ação de proteção, anomalia de cooling ou sequência composta;
- fração estimada de carga que permaneceu conectada, somente quando identificável;
- confiança, limites de validade e dados que faltam;
- curvas de ramp-down, ride-through e recovery;
- comparação entre resposta observada e modelo dinâmico;
- pacote de evidências para engenheiros e atualização/reestudo do modelo.

Primeira aplicação: análise offline pós-evento e validação de modelos. Não deve controlar proteção, emitir comandos operacionais automáticos nem substituir o engenheiro responsável.

## 3. Por que existe dor

- Eventos de perda abrupta de grandes cargas podem alcançar escala de múltiplos GW.
- Pesquisa recente formaliza um problema de identificabilidade: POI sozinho pode não separar causas diferentes.
- NERC está estruturando requisitos próprios para grandes cargas computacionais.
- Dados operacionais podem ser proprietários, protegidos por firewall e sujeitos a NDA.
- PNNL aponta variações de protocolos, formatos, compressão, armazenamento, recuperação e integração operacional de waveform.

## 4. Concorrência e posicionamento

**GridStrong:** interconexão, modelos, estudos, eventos PMU/SER/DFR, compliance e análise de eventos. Não recriar seu sistema de conformidade. ATOCIA só tem espaço se provar uma junção específica entre dados elétricos e sinais internos de workload/UPS/cooling que o produto instalado não forneça.

**NVIDIA Minerva / DSX:** correlaciona infraestrutura, schedulers, workloads e telemetria de AI factory; DSX Flex/MaxLPS coordena targets de potência. Não construir AIOps, dashboard GPU, correlação genérica ou controle de flexibilidade.

**Emerald AI:** Conductor conecta grid e data centers, simula demanda, orquestra workloads/energia e verifica desempenho. Não construir um concorrente genérico de despacho, flexibilidade ou M&V.

**Reactive Technologies / SEL:** fornecedores especializados em medição e analytics elétrico. Não construir sensores, aquisição de waveform ou analytics elétrico genérico.

A combinação POI waveform + registros de proteção/UPS + workload telemetry + atribuição com limites de identificabilidade + validação do modelo não apareceu claramente como um produto turnkey na busca. Isso não prova ausência de concorrente: pode haver integração proprietária, consultoria ou função não divulgada.

## 5. Compradores possíveis

1. Owner/operator de data center de grande porte.
2. Utilities, transmission owners/planners, balancing authorities e reliability coordinators.
3. Consultorias de sistemas de potência, EPCs e OEMs.
4. Seguradoras/financiadores, futuramente (hipótese mais especulativa).

O valor não é simplesmente um relatório: reduzir o tempo de investigação, evitar interpretação errada de um evento grande, apoiar conformidade, melhorar modelos de estudos e evitar ajustes baseados em premissas erradas.

Ainda não há preço, budget confirmado ou disposição de pagar para essa camada. Mercado enorme não significa TAM capturável enorme.

## 6. Diferenciação a testar

- Sincronização multi-domínio com tratamento explícito de latência e incerteza de relógio.
- Identificação causal com abstenção: dizer “não identificável com os dados atuais” em vez de inventar causa.
- Processamento local: manter sinais sensíveis no ambiente do data center e compartilhar somente descritores mínimos autorizados.
- Validação de modelo site-specific contra eventos reais e versionamento de drift.
- Evidência reproduzível e exportável para ferramentas existentes.

A TDT pode inspirar modelagem de estados residuais e propagação multi-escala, mas não deve ser anunciada como diferencial antes de mostrar ganho contra baselines físicos/estatísticos.

## 7. Primeiro experimento

1. Simular três causas de queda de carga: redução de workload, transferência para UPS/backup e desconexão parcial.
2. Gerar canais POI e canais internos (UPS output, workload, breaker status) com atrasos, ruído e drift de relógio.
3. Medir quando POI sozinho identifica e quando dados adicionais tornam a causa identificável.
4. Criar estimador com confiança e estado explícito “indeterminado”.
5. Medir acurácia, falsos diagnósticos, calibração de confiança, robustez a ruído/latência e dados mínimos necessários.
6. Comparar com regras e modelos simples antes de incorporar TDT.
7. Só depois buscar parceiro com logs sincronizados reais e permissão. Simulação não comprova eficácia em data center.

## 8. Portões de decisão

**GO para protótipo** se existir cenário com ground truth, o método diferenciar causas que POI sozinho não separa, a confiança for calibrada e os resultados superarem baseline simples.

**GO para piloto comercial** somente se 3–5 engenheiros/operadores confirmarem a dor, ao menos um dono de dados disponibilizar caso real anonimizado/sincronizado, houver patrocinador e budget owner, e a solução for complementar aos fornecedores existentes.

**NO-GO/pivot** se a camada for apenas integração que fornecedores instalados já entregam, o acesso a dados for bloqueado ou a causa não puder ser identificada na prática.

## 9. Conclusão

Esta é a hipótese ATOCIA mais concreta nesta rodada: perícia temporal e validação de modelos unindo a visão elétrica externa ao comportamento interno do data center. Ela combina problema físico real, evento de escala sistêmica, requisitos regulatórios em desenvolvimento e uma fronteira entre stacks de fornecedores diferentes.

Ainda não é uma “pilha de dinheiro” comprovada. É uma oportunidade séria para teste, com concorrência significativa, acesso a dados como maior risco e necessidade de validação comercial antes de investir em produto.

## Fontes
- NERC CLO-001: https://www.nerc.com/standards/reliability-standards/clo/clo-001-1
- NERC CLO-002: https://www.nerc.com/standards/reliability-standards/clo/clo-002-1
- NERC CLO-003: https://www.nerc.com/standards/reliability-standards/clo/clo-003-1
- NERC standards filing: https://www.publicpower.org/periodical/article/nerc-seeks-ferc-approval-proposed-reliability-standards-tied-integration-computational-loads
- Load attribution paper: https://arxiv.org/abs/2610.38216
- PJM multi-GW event: https://www.reuters.com/business/energy/massive-disconnect-power-roiled-largest-us-electric-grid-2026-07-22/
- GridStrong: https://www.gridstrong.ai/large-load ; https://www.gridstrong.ai/platform
- NVIDIA Minerva: https://www.nvidia.com/en-us/networking/products/software/minerva/
- NVIDIA DSX Flex: https://docs.nvidia.com/dsx/flex/overview
- Emerald AI: https://www.emeraldai.cc/
- PNNL waveform report: https://www.pnnl.gov/publications/synchro-waveform-measurements-survey-industry-readiness-deployment-trends-and-state
