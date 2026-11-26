# Registro de datasets externos — ATOCIA
**Data da auditoria:** 21/11/2026  
**Status:** triagem documental; não equivale a validação científica.

## Decisão executiva
Não existe um único dataset público que cubra, ao mesmo tempo, potência GPU isolada, utilização, temperatura da GPU, temperatura do ar, potência de refrigeração, cargas de produção e diferentes arquiteturas com licença comercial clara. A estratégia recomendada é uma validação em camadas, sem misturar sistemas ou inventar correspondência entre sensores.

1. **PM100 v1** — piloto leve de previsão de potência no nível do nó por trabalho, com licença CC BY 4.0 verificada nos metadados Zenodo. Não mede potência de GPU separadamente.
2. **HazardNet** — candidato a estudo térmico multivariado (temperaturas de entrada/saída + potência de nós), sujeito à conferência final da licença no registro e auditoria do timestamp/schema.
3. **M100 ExaData** — candidato de maior profundidade operacional para relacionar nós, sensores térmicos, GPU e infraestrutura de refrigeração; acesso seletivo obrigatório devido ao volume.
4. **H100/B200 high-resolution traces** — excelente benchmark técnico de GPU, mas sob CC BY-NC-ND 4.0; não usar como base para desenvolvimento comercial, redistribuição de derivados ou alegação de liberdade comercial.
5. **AcmeTrace** — rica telemetria de dois clusters, mas a licença precisa ser lida no arquivo LICENSE do repositório antes de qualquer uso além de avaliação acadêmica. O visualizador HF atual falha por incompatibilidade de colunas; isso não torna os arquivos brutos inválidos.

## Fichas de datasets

### PM100 v1 — piloto operacional
- Registro: https://zenodo.org/records/8129258
- DOI: 10.5281/zenodo.8129258
- Licença confirmada na API oficial do Zenodo: **CC BY 4.0**.
- Arquivo: `job_table.parquet`, 105,940,147 bytes (105.9 MB).
- Checksum MD5 publicado: `2a692d9b9dc4a6ee4bc5e3eb3d0fa6f5`.
- Escala: 231.238 trabalhos executados no Marconi100, maio–outubro de 2020.
- Amostragem declarada: 20 s; potência no nível do nó, incluindo contribuição de GPU, CPU, memória e demais componentes.
- Schema publicado: `node_power_consumption`, `cpu_power_consumption`, `mem_power_consumption` são listas; existem também `job_id`, `start_time`, `end_time`, `run_time`, `num_gpus_alloc`, `num_nodes_alloc`, etc.
- Adequado para: benchmark de previsão de potência de nó por sequência/trabalho; estudar relação entre recursos alocados e consumo.
- Não adequado para: afirmar previsão de potência exclusiva de GPU, temperatura ou refrigeração.
- Atenção metodológica: não concatenar trabalhos em uma só série; preservar limites de job. Criar divisões cronológicas por trabalho e evitar janelas que atravessem jobs. A unidade alvo inicial é node_power_consumption (W a confirmar no conteúdo e no código oficial).
- Código de referência: https://github.com/francescoantici/PM100-data
- Dicionário: https://raw.githubusercontent.com/francescoantici/PM100-data/main/documentation/job_features.md

### HazardNet — validação térmica
- Registro: https://zenodo.org/records/10050368
- DOI: 10.5281/zenodo.10050368
- Licença **CC BY 4.0 confirmada diretamente na API oficial do Zenodo** em 21/11/2026.
- Sistema: Marconi A2 / CINECA.
- Cobertura declarada: 3.312 nós; 14/01/2019 a 31/12/2019.
- Arquivos: temperatura de ar de entrada (~226.8 MB gzip), temperatura de saída (~301.8 MB gzip), consumo de potência (~492.3 MB gzip).
- Adequado para: forecasting e detecção antecipada de situações térmicas no nível de nó.
- Limites: não é uma base de potência isolada de GPU; antes de qualquer benchmark, verificar licença Zenodo diretamente, alinhar timestamp/node IDs, identificar periodicidade, ausências, unidades e política de rótulos.
- Código/artigo: https://github.com/MSKazemi/HazardNet

### M100 ExaData — telemetria holística de HPC
- Artigo: https://www.nature.com/articles/s41597-023-02174-3
- Registro principal: https://zenodo.org/records/7541722
- DOI: 10.5281/zenodo.7541722
- Cobertura: mais de 980 nós e cerca de 2,5 anos (março/2020–setembro/2022).
- Inclui, conforme o artigo: cargas, temperaturas, frequências, operações de memória, energia/potência de CPU, ventiladores, detalhes de uso de GPU, infraestrutura de refrigeração líquida, ar-condicionado, UPS, scheduler, alertas e clima.
- Tamanho: cerca de 49.9 TB descomprimidos no artigo; catálogo indica cerca de 24.78 GB de arquivos depositados.
- Licença **CC BY 4.0 confirmada na API oficial do Zenodo** para o registro consultado; conferir o registro específico e a cobertura de eventuais materiais de terceiros antes de redistribuir.
- Adequado para: estudo de relações entre carga computacional, estado térmico do nó e infraestrutura.
- Limites: não baixar o dataset inteiro; mapear primeiro os 12 registros/partições e as tabelas/sensores necessários. Requer auditoria de sensor, resolução, sincronização, localização física e mapeamento de control volumes.

### H100/B200 high-resolution training traces
- Artigo: https://pmc.ncbi.nlm.nih.gov/articles/PMC13538459/
- Dataset DOI: https://doi.org/10.6084/m9.figshare.31654879.v1
- Repositório: https://github.com/Ahmed-Elsayed95/High-resolution-AI-Data-Center-Training-Workloads-Dataset
- 32 sessões em nós de oito H100/B200 e 40 sessões RTX 3060; mais de 1.8 milhão de amostras.
- Sessões de 15 min; 100 ms no setup single-GPU e 20 ms no setup multi-GPU.
- Registra demanda de potência, uso de CPU/GPU, potência por GPU, memória e temperatura da GPU.
- **Conflito de licença ainda não resolvido:** a API oficial do Figshare para o DOI do dataset retorna CC BY 4.0; porém o README do repositório do dataset e a licença do artigo científico indicam CC BY-NC-ND 4.0. Não presumir que uma declaração prevalece sobre a outra. Manter em quarentena para treinamento, adaptação, redistribuição e desenvolvimento comercial até confirmação escrita dos autores/curadores.
- O artigo já demonstra LSTM com 40 s de histórico para prever 4 s de potência futura em lotes não vistos. Logo, essa configuração não constitui novidade da ATOCIA por si só.

### AcmeTrace
- Hugging Face: https://huggingface.co/datasets/HuggingAGree/AcmeTrace
- GitHub: https://github.com/InternLM/AcmeTrace
- 6 meses (março–agosto de 2023), 2 clusters, 880.740 jobs no total e 470.497 GPU jobs; versão ampla indicada como ~80 GB.
- Arquivos listados incluem potência GPU via IPMI (GPU_AB_Power, GPU_C_Power) e métricas DCGM/Prometheus, como GPU_TEMP, GPU_UTIL, POWER_USAGE, SM_ACTIVE, memória e CPU.
- O viewer HF declara falha de cast porque arquivos têm esquemas distintos. Ler arquivos de forma isolada por cluster/métrica.
- O arquivo LICENSE.txt do repositório oficial InternLM/AcmeTrace foi inspecionado e inicia com “Attribution 4.0 International” (CC BY 4.0). A cópia Hugging Face também disponibiliza LICENSE.txt com a mesma licença. Reutilizar com atribuição e preservar a referência da versão/origem.
- Adequado potencialmente para estudar produção e mudança de regime, sujeito a resolver formato, timestamps, cadência e licença.

### Data Center Flexibility Dataset — candidato futuro
- Página: https://site-stg.jlse.anl.gov/projects/benchmarking/data-center-flexibility-dataset
- Projeto do Argonne National Laboratory/JLSE descreve um testbed H100/B200 com séries temporais de potência/energia, clock, uso, temperatura e qualidade de serviço por requisição.
- A página consultada parece descrever a campanha/projeto, não comprova ainda um release público completo. Monitorar; não contar como dataset disponível até confirmar dados e termos.

## Protocolo mínimo de validação
1. Ingestão reproduzível e checksums; guardar dados brutos sem modificá-los.
2. Auditoria de colunas, unidades, intervalo amostral, fuso horário, duplicatas, ausências, lacunas, qualidade e alinhamento temporal.
3. Construir sequência por entidade correta: job, GPU, nó ou sensor — nunca concatenar entidades sem separação.
4. Dividir treino/validação/teste por sessão/job/período completo; nunca dividir linhas aleatoriamente quando janelas sobrepostas podem vazar contexto.
5. Baselines mínimos: persistência, média móvel causal (3/5/10 amostras), EWMA e regressão simples. Em multi-horizonte: 0.5/1/2/5/10/30/60 s conforme cadência.
6. Avaliar MAE, RMSE, MASE/skill vs persistence; por entidade, regime e horizonte. Informar intervalo de confiança por sessão/job, não por amostra autocorrelacionada.
7. Ablations: só potência; potência + utilização; multivariado com temperatura; sensores faltantes; mudanças de regime; transferência entre sessões/hardware quando houver suporte.
8. Não alegar redução de energia ou segurança térmica sem teste de decisão/controle e evidência operacional.

## Resumo de direitos de uso
- **PM100 v1:** CC BY 4.0 confirmado via API oficial do Zenodo.
- **H100/B200:** CC BY-NC-ND 4.0; restritivo para produto/comercial.
- **HazardNet:** CC BY 4.0 confirmado pela API oficial do Zenodo.
- **M100 ExaData:** CC BY 4.0 confirmado pela API oficial do Zenodo para o registro consultado.
- **AcmeTrace:** CC BY 4.0 confirmado no LICENSE.txt do repositório oficial e na cópia Hugging Face consultada.
- **Argonne/JLSE:** dataset ainda não confirmado como release público.

## Fontes consultadas
- Zenodo PM100 v1: https://zenodo.org/records/8129258
- Zenodo PM100 v3: https://zenodo.org/records/10127767
- PM100 schema: https://raw.githubusercontent.com/francescoantici/PM100-data/main/documentation/job_features.md
- Nature M100 ExaData: https://www.nature.com/articles/s41597-023-02174-3
- Zenodo HazardNet: https://zenodo.org/records/10050368
- Scientific Data H100/B200: https://pmc.ncbi.nlm.nih.gov/articles/PMC13538459/
- MDPI federated GPU power forecasting (20/11/2026): https://www.mdpi.com/3042-8831/1/3/15
- AcmeTrace HF: https://huggingface.co/datasets/HuggingAGree/AcmeTrace

## Atualização de auditoria (21/11/2026)
- A API Figshare para o dataset H100/B200 devolve `license: CC BY 4.0` (dataset DOI 10.6084/m9.figshare.31654879.v1; arquivo ZIP de 209,685,111 bytes). Contudo, o README e o artigo associado declaram CC BY-NC-ND 4.0. Divergência não resolvida: manter em quarentena de licença e não assumir permissões comerciais.
- A API Zenodo confirmou CC BY 4.0 para HazardNet (10050368), M100 (7541722) e PM100 v3 (10127767). PM100 v1 já estava confirmado.
- A LICENSE.txt do repositório oficial InternLM/AcmeTrace começa com Creative Commons Attribution 4.0 International; a distribuição Hugging Face consultada também contém LICENSE.txt com CC BY 4.0.
- A versão PM100 v1 está sendo obtida localmente para auditoria de schema e primeiro baseline, com taxa de download limitada para reduzir impacto na rede.
