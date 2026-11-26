# ATOCIA — revisão internacional e hipótese de diferenciação (21/11/2026)

## Síntese executiva
A previsão de potência/carga de data centers e GPUs já é uma área internacional ativa. A ATOCIA não deve reivindicar ter inventado previsão multivariada, quantis, transferência entre workloads ou modelos térmicos RC informados por física. Há trabalhos diretamente relacionados, inclusive um PI-DLinear apresentado no KDD 2026.

A oportunidade deve ser tratada como hipótese de produto e pesquisa: testar se uma implementação leve, auditável e de baixo custo consegue combinar memória temporal multiescala, adaptação entre workloads e incerteza calibrada em dados heterogêneos, com validação externa e implantação em modo sombra. A originalidade só pode ser afirmada após revisão bibliográfica sistemática e comparação técnica.

## Técnicas internacionais relevantes

### 1. Previsão orientada à incerteza — CUFF (UMass Amherst + IBM, ACM e-Energy 2023)
CUFF estima demanda de GPU e explicita incerteza por quantis, permitindo ajustar decisões operacionais conforme o risco de subdimensionamento. O paper reporta resultados em traces de GPU e discute trade-off entre eficiência e desempenho.
Fonte: https://lass.cs.umass.edu/papers/pdf/eEnergy2023-cuff.pdf

### 2. Transferência entre workloads — TGCP (IEEE Transactions on Cloud Computing, 2025)
TGCP usa multi-source transfer Gaussian Process Regression para transferir informação de workloads com mais dados para um workload-alvo com poucos dados, enfrentando domain shift entre CPU, memória e I/O.
Relevância ATOCIA: testar se um previsor treinado em determinadas cargas se adapta a uma GPU/workload novo com poucos dados. Não assumir que transferência funciona; comparar contra treinamento local e modelos sem transferência.
DOI: https://doi.org/10.1109/TCC.2025.3575790

### 3. Modelo físico-informado para potência GPU — PI-DLinear (KDD 2026)
Saleh et al. propõem PI-DLinear, acoplando DLinear a uma rede térmica RC multi-nó e equações que conectam potência, utilização compute/memória e temperatura. O estudo reporta ganhos sobre modelos avaliados e comportamento coerente em throttling e transientes.
Relevância ATOCIA: antecedente muito próximo da integração entre RC térmico e previsão de potência. ATOCIA precisa comparar com essa linha e não apresentar "RC + temperatura + utilização" como novidade própria.
DOI: https://doi.org/10.1145/3770855.3818033
Página institucional: https://elmi.hbku.edu.qa/en/publications/a-physics-aware-framework-for-short-term-gpu-power-forecasting-of-2/

### 4. Observabilidade correlacionada — NVIDIA DSX
A documentação descreve pipeline que correlaciona métricas, logs e traces com timestamps, IDs de recursos e IDs de trace, incluindo telemetria GPU via DCGM Exporter.
Relevância ATOCIA: contexto operacional e sincronização multi-sinal são requisitos de sistema; o diferencial não pode ser apenas "juntar telemetria".
Fonte: https://docs.nvidia.com/dsx/ncp/part-1-software-reference-guide/telemetry-and-observability

## Contexto brasileiro — leitura preliminar, não censo
- O estudo Cetic.br/NIC.br (novembro de 2025) registra escassez de dados públicos, sistemáticos e comparáveis para mapear e avaliar data centers no Brasil. O levantamento inicial foca facilities e indica aprofundamento futuro. Isso aponta uma dificuldade de dados e benchmarking abertos, não prova ausência de pesquisa ou tecnologia nas empresas.
  Fonte: https://nic.br/media/docs/publicacoes/6/pt-br/20251209175312/psi-a17-n4-data_centers_no_brasil.pdf
- O BNDES (setembro de 2025) discute infraestrutura computacional para IA, energia, conectividade, mão de obra e governança de eficiência. É um panorama estratégico setorial, não uma comparação técnica de algoritmos de previsão GPU.
  Fonte: https://web.bndes.gov.br/bib/jspui/bitstream/1408/29008/3/Infraestrutura%20computacional_216916_vf.pdf
- Há produção brasileira relacionada a energia e GPUs, incluindo estudos de DVFS e energia de aplicações paralelas; portanto, seria incorreto dizer que o tema não é pesquisado no país.
  Exemplo: https://cradrs.github.io/eradrs2025/pdfs/resumos/S7R2.pdf
- Também há pesquisa brasileira sobre previsão de impacto ambiental de data centers, como Ferreira et al. (2019), com autores vinculados à UFPE, UFRPE, UFAM e universidade alemã. O recorte não é o mesmo que previsão temporal multi-sinal de potência GPU.
  DOI: https://doi.org/10.3390/info10030113

Conclusão provisória: a busca aberta encontrou trabalho brasileiro em eficiência energética, DVFS e impacto ambiental, mas não permite afirmar que empresas ou grupos brasileiros não usem previsão multi-sinal de potência GPU. A lacuna mais defensável para a proposta é a falta de benchmarking público comparável e reproduzível no recorte específico, a ser confirmada por revisão sistemática.

## Diferenciação experimental a investigar
1. **Baixo custo computacional:** inferência CPU, pequena memória e baixa latência; comparar custo/erro, não apenas precisão.
2. **Memória temporal multiescala:** separar resposta rápida do workload e estado lento/thermal lag, com ablação de cada componente.
3. **Adaptação entre workloads/dispositivos:** testar transfer learning ou atualização com poucos exemplos, usando splits por workload/GPU e não por linhas aleatórias.
4. **Incerteza calibrada:** previsões quantílicas e avaliação de cobertura, largura e falhas em transientes.
5. **Generalização:** holdout temporal intocado, depois holdout por GPU/workload/cluster se os dados permitirem.
6. **Modo sombra:** mostrar previsão e risco sem controlar hardware; só estudar ação operacional após validação separada.

## Decisão técnica para ATRP-1
A especificação inicial em MODEL_V1/ATRP1_SPEC.md continua como desenho de candidato, mas deverá incluir PI-DLinear como antecedente e, se uma implementação reproduzível estiver disponível, como baseline. O primeiro modelo próprio deve permanecer simples e eficiente: baseline causal + correção residual com estados rápidos/lentos; a transferência e a previsão quantílica entram como extensões testáveis, não como complexidade presumida.

## Limitações da pesquisa
Busca preliminar em fontes acadêmicas, documentação técnica e relatórios setoriais; não é revisão sistemática. Não avaliou patentes, soluções proprietárias, produtos comerciais fechados ou trabalhos ainda não indexados. Não sustenta alegação de novidade nacional ou mundial.

## Atualização crítica de anterioridade — 21/11/2026

A busca adicional identificou um antecedente de grande proximidade: Acun et al. (Boston University / Lawrence Berkeley National Laboratory), “A Dynamic GPU Power Prediction Framework for Production HPC Applications” (manuscrito técnico: https://www.bu.edu/peaclab/files/2026/04/pap124s3-file1.pdf). O trabalho usa DCGM de baixa sobrecarga em Perlmutter/NERSC, previsão per-GPU com LSTM, modelos genéricos e específicos por aplicação, horizonte curto de 10–30 s, RMSE médio genérico de 50 W, ganhos de até 48% com especialização por aplicação, até 15,8% com sinais DCGM adicionais e latência de inferência reportada de 3 µs. Isso elimina como diferenciais exclusivos “modelo leve”, “multissinal” e “previsão operacional per-GPU”.

Também foi localizado o preprint “Grid-Oriented Probabilistic Load Forecasting for AI Data Centers” (Yao et al., arXiv:2611.08929, 06/11/2026; https://arxiv.org/abs/2611.08929). Usa um benchmark de 448 GPUs do MIT Supercloud e avalia previsão quantílica, calibração online por regime, cenários temporais e reserva. O resultado reforça que a calibração marginal sozinha não basta: a dependência temporal dos erros importa para rampas, picos e custos de decisão.

A diferenciação ATRP-1 deve, portanto, ser reformulada como hipótese de robustez operacional/generalização sob observabilidade imperfeita: sensores ausentes, cadência irregular, mudança de workload/regime e hardware/cluster não visto, com incerteza calibrada e métricas de eventos/decisão. Isso ainda não é uma novidade comprovada. O comparador TCN/LSTM deve ser incluído quando houver dados, implementação reproduzível e orçamento computacional; não é obrigatório começar com arquitetura pesada no notebook.
