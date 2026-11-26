# ATOCIA — Hipótese de produto e posicionamento
Data: 2026-11-20
Status: tese estratégica e hipótese técnica; ainda sem validação comercial ou industrial.

## Produto
ATOCIA é uma plataforma de inteligência temporal e causal para infraestruturas computacionais de grande escala: data centers, clusters de IA, HPC, servidores, aceleradores, distribuição elétrica e refrigeração.

Ela busca antecipar oscilações e perturbações energéticas/térmicas, investigar os mecanismos que as produzem, estimar consequências e apoiar decisões operacionais seguras.

Não é um utilitário para computador pessoal, nem apenas um monitor de temperatura, nem somente um controlador de refrigeração.

## Problema de entrada
Treinamentos e serviços de IA podem apresentar fases coordenadas de computação e comunicação. A agregação dessas fases pode gerar variações rápidas de potência. Essas variações propagam-se pela infraestrutura elétrica e térmica, com atrasos e respostas diferentes em GPUs, servidores, racks, circuitos de cooling e instalação.

A ATOCIA pretende responder:
- Qual perturbação está se formando?
- Quando pode ocorrer, com que amplitude e incerteza?
- Quais sinais e processos estão associados à sua formação?
- Que mecanismos provavelmente explicam a perturbação?
- Como ela pode se propagar entre camadas?
- Quais decisões poderiam reduzir risco/custo sem comprometer throughput, latência ou confiabilidade?

## Relação com a TDT
A TDT é a base teórica do projeto. A ATOCIA procura transformar a visão de transformações, irreversibilidade e débito temporal acumulado em representações matemáticas testáveis para sistemas físicos e computacionais.

A conexão não está demonstrada. Não se pode igualar débito temporal a energia, entropia, dissipação, temperatura ou envelhecimento. A ponte entre esses conceitos deve ser explicitada, medida e comparada a modelos convencionais. O valor da TDT na ATOCIA dependerá de evidência empírica.

## Arquitetura proposta
1. Ingestão e sincronização: workload, scheduler, comunicação, CPU/GPU, potência, temperaturas, cooling, facility e rede.
2. Memória temporal: estado histórico, transientes, atrasos, regimes e efeitos persistentes.
3. Predição: potência, temperatura, demanda térmica e eventos em múltiplos horizontes.
4. Diagnóstico: hipóteses concorrentes e identificação de fatores contribuintes.
5. Causalidade: testes de precedência, ablação, contrafactuais e intervenções em simulação quando os dados permitirem.
6. Propagação: projetar efeitos entre chip, servidor, rack, cluster, cooling e rede elétrica.
7. Otimização: comparar intervenções com métricas e incerteza.
8. Governança: modo sombra, auditoria, aprovação humana, limites e fallback.

## Mercado e concorrência
Google DeepMind, Siemens/Vigilent, EkkoSense, Schneider Electric e grupos acadêmicos já atuam em partes desse espaço: otimização de cooling, previsão térmica, análise de workloads, controle e gestão energética.

Portanto, ATOCIA não pode alegar ser a primeira a prever temperatura ou otimizar cooling. A oportunidade precisa ser uma vantagem mensurável na integração entre previsão rápida de perturbações, explicação de mecanismos, memória temporal inspirada na TDT e propagação multi-escala.

## Hipóteses de diferenciação a refutar
- Predição conjunta workload → potência → efeitos térmicos com alinhamento temporal fino.
- Detecção antecipada de oscilações e padrões sincronizados.
- Diagnóstico de fatores contribuintes além de correlação simples.
- Representação explícita de memória, atraso e irreversibilidade.
- Transferência entre diferentes GPUs, arquiteturas, racks e instalações.
- Incerteza calibrada e explicações estáveis.
- Otimização conjunta de computação, energia, refrigeração, água e desempenho.

## Evidência atual
O Garuda/Samsung é um laboratório inicial de telemetria e desenvolvimento. Além de testes passivos de CPU e modelos exploratórios de temperatura, foi integrado um leitor Intel GT/RC6 e executado um ensaio gráfico leve com captura sincronizada de energia e temperatura do host. Isso é instrumentação exploratória local, não validação preditiva, não medição isolada da GPU e não demonstra comportamento de cluster, rack, data center, refrigeração líquida ou oscilações em escala de megawatts.

Nenhuma economia, vantagem comercial, causa raiz, capacidade de controle ou generalização está comprovada.

## Validação
- Auditar datasets públicos de workloads H100/B200 e HPC.
- Estabelecer baselines fortes e splits por sessão/equipamento/site.
- Prever potência em escalas rápidas e temperatura em horizontes adequados.
- Testar explicações por ablação e intervenções simuladas.
- Validar incerteza, transferibilidade e robustez.
- Só depois testar digital twin, otimização e pilotos em infraestrutura real.

## Monetização futura
Possíveis caminhos, ainda não validados:
- licença enterprise por instalação, cluster ou capacidade monitorada;
- software de previsão/diagnóstico integrado a DCIM, BMS, scheduler e plataformas de observabilidade;
- parceria OEM/ODM e integração com fabricantes de silício, servidores e cooling;
- piloto pago com métrica de valor operacional verificada.

A fase comercial só começa depois de demonstrar benefício mensurável, segurança e integração repetível. Não há receita ou parceria presumida.

## Regra de controle
Simulação → modo sombra → recomendação humana → piloto limitado e autorizado. Nunca controlar infraestrutura crítica sem limites rígidos, interlocks, logs, rollback e supervisão do operador.
