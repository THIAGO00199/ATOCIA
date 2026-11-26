# ATOCIA — Tese central e arquitetura de pesquisa
Data: 2026-11-20
Status: documento de referência; substitui interpretações anteriores orientadas a diagnóstico de PC doméstico.

## Definição
ATOCIA é uma plataforma de inteligência temporal e causal para infraestruturas computacionais de grande escala. Seu objetivo é antecipar perturbações energéticas e térmicas, investigar os mecanismos que as produzem, projetar suas consequências e apoiar decisões operacionais seguras.

Mercado-alvo: data centers, clusters de IA, HPC, servidores, aceleradores, redes de energia e sistemas de refrigeração. O notebook do fundador é somente um laboratório inicial de instrumentação e desenvolvimento.

## Problema central
Cargas computacionais sincronizadas ou correlacionadas podem produzir variações rápidas e agregadas de potência. Essas perturbações propagam-se por diferentes camadas: acelerador, servidor, rack, distribuição elétrica, circuito de refrigeração e instalação. A resposta de cada camada tem atrasos, inércia, limites e efeitos persistentes próprios.

ATOCIA deve responder:
1. O que está mudando?
2. O que provavelmente mudará a seguir, em qual horizonte e com qual incerteza?
3. Quais processos e interações contribuíram para a mudança?
4. Quais consequências energéticas, térmicas e operacionais são esperadas?
5. Quais intervenções candidatas reduziriam o risco ou custo sem prejudicar desempenho e confiabilidade?

## Relação com a TDT
A TDT é o fundamento teórico que inspira o tratamento de transformações, irreversibilidade e débito temporal acumulado. ATOCIA é uma aplicação tecnológica e experimental dessa visão em sistemas computacionais físicos.

A ponte matemática ainda precisa ser construída e validada. Não se deve equiparar débito temporal, energia armazenada, entropia, dissipação, degradação ou temperatura. São conceitos distintos. A pesquisa deve propor variáveis e relações explícitas e testar se a representação temporal inspirada na TDT acrescenta poder preditivo ou explicativo em relação a baselines convencionais.

## Pipeline conceitual
1. Observação multimodal e alinhamento temporal: workload/scheduler, CPU/GPU, potência, rede, temperatura, fluxo, pressão, cooling e facility.
2. Estado temporal: representação do histórico relevante, transientes, atrasos, memória e condições de contorno.
3. Detecção e previsão: previsão multi-horizonte de potência, temperatura, demanda térmica e eventos.
4. Diagnóstico causal: hipóteses concorrentes, precedência temporal, dependências e testes por intervenção/simulação quando possível.
5. Propagação: projetar como uma perturbação se propaga entre chip, servidor, rack, cluster, cooling e rede elétrica.
6. Otimização: comparar decisões possíveis, custos, riscos e incerteza.
7. Governança: modo sombra, explicabilidade, auditoria, aprovação humana e fallback.

## Camadas de observação
- Acelerador/chip: potência, temperatura, hotspot, clocks, utilização, memória, throttling, atividade por domínio.
- Servidor: CPU/GPU, inlet/outlet, ventiladores, bombas locais, workload, comunicação e fila.
- Rack: potência agregada, temperatura de entrada/saída, pressão, fluxo e topologia.
- Refrigeração: temperatura de supply/return, vazão, pressão, CDU, bombas, chillers e rejeição de calor.
- Instalação/rede: demanda agregada, PUE/WUE, clima, limites elétricos, tarifa e eventos de rede.

## Hipóteses a testar — não diferenciais já comprovados
- Modelar a cadeia workload → potência → calor → resposta térmica com alinhamento temporal fino.
- Identificar causas e interações de oscilações, distinguindo causa, correlação e coincidência.
- Aprender memória e atraso entre escalas temporais, com consistência física.
- Transferir modelos entre hardware, topologias e instalações com pouca recalibração.
- Quantificar incerteza e alertar com antecedência útil.
- Otimizar conjuntamente carga computacional, energia, cooling, água e desempenho.

## Métricas
Previsão: MAE/RMSE, erro de pico, erro de amplitude/frequência de oscilações, antecedência útil e cobertura de intervalos.
Detecção: precisão/recall, falsos alarmes, tempo de detecção e eventos perdidos.
Causalidade: estabilidade das explicações, testes de ablação/intervenção, consistência entre sessões e ausência de vazamento temporal.
Operação: energia de computação/cooling, água, throughput, latência, violações térmicas/elétricas, disponibilidade e custo.

## Critério científico
A ATOCIA só poderá alegar vantagem quando superar baselines fortes em dados não vistos, com divisão por sessão/equipamento/site, ablações, incerteza calibrada e replicação. Melhor previsão não prova causalidade; explicação causal exige evidência adicional.

## Segurança
Nenhum controle automático em infraestrutura real nesta fase. Sequência obrigatória: simulação → modo sombra → recomendação humana → piloto limitado e aprovado. Interlocks, limites, logs, rollback e supervisão são requisitos.
