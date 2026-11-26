# ATOCIA — Pesquisa de datasets e plano de benchmark
Data: 2026-11-20
Objetivo: selecionar dados reais para estudar oscilações de potência, workload, temperatura, propagação temporal e relações entre infraestrutura computacional e cooling.

## Descoberta A — High-resolution AI Data Center Training Workloads (2026)
Paper: Elsayed, Al-Obaidi & Farag, Scientific Data (2026), DOI 10.1038/s41597-026-07496-6.
Dataset: figshare DOI 10.6084/m9.figshare.31654879.v1.
Código/documentação: https://github.com/Ahmed-Elsayed95/High-resolution-AI-Data-Center-Training-Workloads-Dataset

Escopo divulgado:
- 32 sessões em nós com 8 GPUs H100/B200 e 40 sessões RTX 3060.
- Mais de 1,8 milhão de amostras.
- Sessões de 15 minutos; amostragem de 100 ms em single-machine e 20 ms em nós multi-GPU.
- Métricas incluem potência CPU/GPU, utilização, memória e temperatura de GPU nos nós.
- Cargas incluem forecasting, classificação, reinforcement learning, geração de texto e imagem.
- É uma fonte prioritária para estudar padrões sub-segundo de workload e potência e a resposta térmica observada nas GPUs.

Limitações:
- Não inclui temperatura ambiente nem configuração do sistema de refrigeração.
- Não representa diretamente a dinâmica de um data center inteiro nem comprova oscilações de dezenas de megawatts.
- Licença indicada no repositório: CC BY-NC-ND 4.0. Tratar como material de pesquisa não comercial; não redistribuir nem criar derivados distribuíveis. Obter orientação/permissão antes de qualquer uso comercial ou incorporação em produto.

## Descoberta B — M100 ExaData / Marconi100 (CINECA)
Paper: Borghesi et al., Scientific Data (2023), DOI 10.1038/s41597-023-02174-3.
Dataset principal: https://zenodo.org/records/10533504
Dataset agregado para anomalias: https://zenodo.org/records/7541722
Código de apoio: https://gitlab.com/ecs-lab/exadata

Escopo divulgado:
- Supercomputador Marconi100, mais de 980 nós, telemetria de aproximadamente 2,5 anos.
- Métricas de nós: carga, temperaturas, frequências, energia/potência, ventoinhas e uso de GPU.
- Métricas de instalação: infraestrutura de refrigeração líquida, ar-condicionado, fontes de alimentação, scheduler/jobs, alertas e previsão do tempo.
- Dataset agregado para anomalias contém períodos de 15 minutos, estatísticas agregadas e labels Nagios; Zenodo informa 24,8 GB para os tarballs desse registro.
- O artigo descreve a coleção completa como 49,9 TB descompactados, distribuídos em conjuntos e períodos distintos.

Limitações:
- A versão agregada de 15 minutos não serve para previsão de oscilações de poucos segundos.
- A coleção completa é grande; não baixar em massa para o laptop.
- Auditar metadados, licença, timestamps, nomes de sensores, frequência de amostragem e mapeamento espacial antes de usar. Não presumir que todo sinal de facility esteja alinhado a cada nó.

## Decisão de pesquisa
Usar o dataset de H100/B200 como primeira fonte para dinâmica rápida de carga/potência e temperatura de GPU.
Usar M100 ExaData como fonte complementar para relações de longo prazo e infraestrutura de cooling/facility, após auditar os dados e selecionar apenas subconjuntos pequenos.
Não misturar os dois datasets como se fossem uma única instalação ou um único relógio. Fazer validações independentes e explicitar diferenças de hardware, frequência, topologia e sensores.

## Plano de benchmark em etapas
### Etapa 1 — Auditoria dos dados (sem treinar modelos)
- Inventariar arquivos, tamanhos, formatos, licença e estrutura.
- Identificar colunas, unidades, timestamps, amostragem real, lacunas, duplicatas e sensores.
- Verificar sessões e workloads disponíveis.
- Estimar memória/disco necessários antes de qualquer extração.
- Preservar dados originais; trabalhar em subconjuntos e saídas derivadas separadas.

### Etapa 2 — Fenômenos e baselines
- Detectar transientes e oscilações de potência por GPU/nó.
- Medir amplitude, duração, frequência dominante e alinhamento entre GPUs.
- Testar se a agregação de GPUs em nó produz reforço ou cancelamento de oscilações.
- Prever potência em 1, 5, 10, 30 e 60 segundos, respeitando a resolução de cada sessão.
- Baselines: persistência, média móvel/EMA, regressão autoregressiva, modelos lineares com lags e gradient boosting.
- Separar sessões inteiras entre treino e teste; nunca dividir aleatoriamente amostras temporais da mesma sessão.

### Etapa 3 — Explicação e causalidade
- Criar hipóteses sobre workload, utilização, memória, sincronização e potência.
- Usar precedência temporal, ablação de variáveis e comparações entre sessões.
- Diferenciar claramente associação, previsão e causalidade.
- Sem logs de scheduler/dependências suficientes, limitar a conclusão a fatores associados; não afirmar causa raiz.

### Etapa 4 — Acoplamento térmico
- Modelar potência e temperatura como sinais com atrasos diferentes.
- Avaliar previsão de temperatura e hotspot a 1, 5, 10, 30 e 60 segundos.
- Testar modelos físicos simples e híbridos contra persistência/EMA/ML.
- Não extrapolar temperatura de GPU para sala, rack ou cooling plant quando essas medidas não existem.

### Etapa 5 — Propagação e escala
- Com M100, investigar relações entre nós, rack, cooling e facility apenas quando os timestamps e mapeamentos permitirem.
- Construir grafos de dependência temporal e espacial.
- Testar transferência de modelos e robustez fora da instalação de origem.

## Ambiente atual e decisão operacional
O usuário está jogando no Garuda. O processo do jogo observado consumia aproximadamente 96% de CPU no instante da inspeção. Portanto:
- Não executar benchmarks pesados, estresse, treinamento de ML ou extração grande agora.
- Não baixar datasets grandes nem instalar dependências.
- Trabalho atual deve ser documental, de arquitetura e auditoria leve.
- O notebook continua sendo laboratório de apoio, não proxy de um data center.

## Fontes
- Paper H100/B200: https://www.nature.com/articles/s41597-026-07496-6
- Dataset H100/B200: https://doi.org/10.6084/m9.figshare.31654879.v1
- Repositório H100/B200 e licença: https://github.com/Ahmed-Elsayed95/High-resolution-AI-Data-Center-Training-Workloads-Dataset
- Paper M100: https://www.nature.com/articles/s41597-023-02174-3
- Registro M100: https://zenodo.org/records/10533504
- M100 agregado: https://zenodo.org/records/7541722
- ExaData tools: https://gitlab.com/ecs-lab/exadata

## Lacuna de dados observada
As duas fontes são complementares, mas não equivalentes:
- H100/B200: resolução alta para workload, potência e temperatura de GPU, mas sem ambiente e configuração de cooling.
- M100: visão muito mais ampla de nós, workload e facility/cooling, porém a versão agregada de 15 minutos não captura transientes de poucos segundos; a coleção completa exige seleção cuidadosa e pode ser muito pesada.

Hipótese de pesquisa resultante: existe uma dificuldade prática em validar, com dados públicos sincronizados, a cadeia completa workload → potência rápida → resposta térmica → cooling/facility. Isso não prova que não existam dados privados em operadores nem que exista demanda comercial não atendida. Mas define uma pergunta científica concreta para a ATOCIA: quanto da dinâmica rápida pode ser explicada e prevista com telemetria de workload/potência, e como conectar essa previsão à resposta térmica e à infraestrutura quando dados multi-escala estão disponíveis?

A primeira prova deve ser limitada e honesta: prever a dinâmica de potência no dataset H100/B200; prever temperatura GPU separadamente; depois avaliar se padrões aprendidos se transferem ou se relacionam com a dinâmica de facility no M100, sem fingir que os relógios ou sistemas são os mesmos.
