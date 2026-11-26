# Revisão rápida de concorrência e lacunas — ATOCIA
**Data:** 21/11/2026  
**Tipo:** varredura inicial; não é revisão sistemática nem busca exaustiva.

## Conclusão
A previsão de potência de GPU, a previsão térmica, modelos temporais multivariados e o uso de LSTM/TCN/Transformer já aparecem em pesquisas recentes. A ATOCIA não deve reivindicar novidade com base apenas em prever potência ou temperatura. A contribuição precisa ser formulada como uma hipótese mais delimitada, testada contra trabalhos comparáveis e validada fora das sessões usadas para desenvolvimento.

## Trabalhos e concorrentes relevantes

### 1. Sub-second GPU Power Forecasting with Federated Learning (20 Nov 2026)
Guohao Yang, Makafui Torkornoo e Miltiadis Alamaniotis, AI Engineering 2026, 1(3), 15. DOI: https://doi.org/10.3390/aieng1030015
- Dados de telemetria de potência de GPU de três nós do MIT SuperCloud, tratados como clientes/proxy silos.
- Um passo à frente em aproximadamente 0,1 s.
- Compara TCN centralizado, local, FedAvg e FedProx.
- Reporta MAE médio por nó: FedProx 7.72 ± 0.07 W; FedAvg 7.78 ± 0.11 W; Local 8.11 ± 0.12 W; Centralizado 7.60 ± 0.22 W.
- Usa partição cronológica e preserva limites (job_id, gpu_index), sem janelas cruzando jobs.
- Implicação: one-step sub-second GPU power forecasting e federação não são, isoladamente, uma novidade.
- Espaço possível: avaliação cross-hardware e cross-facility real, horizons multi-step e métricas de evento/decisão, sensores faltantes e robustez operacional — verificar trabalhos específicos antes de alegar lacuna.

### 2. Characterization of high-resolution AI data center training workloads (Scientific Data, 3 Jun 2026)
Elsayed, Al-Obaidi e Farag. DOI: https://doi.org/10.1038/s41597-026-07496-6
- Dataset com 32 sessões de nós de oito H100/B200 e 40 RTX 3060, mais de 1.8M amostras.
- 100 ms no setup single-machine e 20 ms no setup multi-GPU.
- Variáveis: potência, utilização, potência por GPU, memória e temperatura da GPU.
- Demonstração de forecasting: LSTM com 40 s de histórico e previsão de 4 s, testada em lotes não vistos.
- Licença: há divergência documental. A API Figshare para o DOI do dataset retorna CC BY 4.0, mas o README do repositório e o artigo apontam CC BY-NC-ND 4.0. Manter em quarentena até os autores confirmarem por escrito os direitos do arquivo de dados.
- Implicação: multivariate telemetry + H100/B200 + LSTM curto prazo já foi publicado. A existência do artigo é relevante mesmo que a licença do dataset seja esclarecida posteriormente.

### 3. Thermal-Guided Ensemble Reinforcement Learning (arXiv, 19 Nov 2026)
https://arxiv.org/abs/2611.26527
- Preprint propõe ensemble adaptativo com LSTM, TCN e Transformer, SAC para ajustar pesos e correção guiada por variáveis térmicas; inclui previsão probabilística.
- Reporta NMAE ~1% em MIT SuperCloud 1 Hz, sujeito a verificação crítica e reprodução independente.
- Status: preprint, não tratar como resultado estabelecido ou peer-reviewed.
- Implicação: “ensemble adaptativo” e “orientação térmica” também já são direções pesquisadas.

### 4. Co-optimization of thermal-aware workload scheduling with DRL cooling control (Energy, 1 Feb 2026)
https://doi.org/10.1016/j.energy.2026.139965
- DNN para prever temperatura de saída de servidores e DRL Soft Actor-Critic para coordenar scheduling IT e operação CRAC.
- O artigo reporta redução de até 8.6% no consumo de energia de refrigeração e queda de violações de limite térmico de 184 para 1, em seu cenário experimental.
- Implicação: previsão térmica + otimização de workload + controle de refrigeração também já existe.

### 5. Scheduled Sampling for Recursive Multi-Step GPU Temperature Forecasting (ICMLA 2024)
https://doi.org/10.1109/ICMLA61862.2024.00147
- Modelo híbrido CNN-LSTM para prever temperatura GPU em vários passos dentro de simulação de balanceamento de carga.
- Reporta redução RMSE de 2.54 para 0.73, comparado ao baseline térmico referido pelos autores.
- Implicação: previsão recursiva multi-step de temperatura GPU não é, sozinha, novidade.

### 6. Energy-Aware AI Infrastructure: Power and Thermal Prediction Based on PCA Workload Characterization (IEEE AANN 2026)
https://doi.org/10.1109/AANN71145.2026.11709166
- Cluster Ampere de dois nós/12 GPUs, 1 s, 10 h de telemetria.
- PCA de descritores de workload + gradient boosting para potência e temperatura de saída.
- Abstract reporta RMSE de 11.3 W para potência e 0.83 °C para temperatura.
- Implicação: previsão conjunta de potência e temperatura com features de carga também já existe.

### 7. Multi-horizon cooling-load forecasting / TS-DVGFormer (2026)
https://www.sciencedirect.com/science/article/pii/S037877882601501X
- Estrutura temporal com prior térmico, grafo dinâmico de variáveis e Transformer-GRU para previsão de carga de refrigeração.
- A página consultada reporta validação externa em Frontier HPC e ESIF HPC.
- Implicação: robustez e generalização inter-instalação em previsão de cooling load já têm trabalhos recentes; comparar cuidadosamente o escopo.

### 8. M100 ExaData / HazardNet
- M100 ExaData (Scientific Data 2023): dados holísticos de Marconi100, 980+ nós, monitoramento de nós e infraestrutura de refrigeração, por cerca de 2.5 anos.
- HazardNet (Future Generation Computer Systems 2024): dataset com entrada/saída de ar e potência de nós de 3.312 compute nodes, 2019; framework para previsão de risco térmico.
- Implicação: relações energia-temperatura e previsão de perigo térmico em HPC não são novas, mas os datasets possibilitam avaliação independente e análise de robustez.

## O que parece insuficiente como diferencial
- “Um modelo que prevê consumo de GPU.”
- “Usa IA para prever temperatura.”
- “Combina potência, uso e temperatura.”
- “Usa LSTM/TCN/Transformer.”
- “Faz previsão subsegundo.”
- “Usa federação ou ensemble” sem uma necessidade de sistema claramente demonstrada.

## Hipóteses de contribuição a testar (não reivindicar ainda)
1. **Robustez a sensores ausentes/irregulares:** manter skill de previsão e calibração sob perda controlada de canais e mudanças de cadência, comparando com baselines e modelos multivariados.
2. **Adaptação a mudança de regime:** detectar mudança de workload/estado térmico e adaptar previsão, comparando com modelo fixo e EWMA/TCN/LSTM.
3. **Generalização com teste agrupado:** treino em uma coleção de workloads/sessões e teste em sessões/arquiteturas/ambientes separados; medir queda de desempenho e custo de adaptação.
4. **Valor decisório:** medir antecipação de picos, erros em ramps, falsos alarmes, antecedência útil e custo esperado de decisão — sem implementar controle de hardware no primeiro ciclo.
5. **Eficiência e interpretabilidade:** testar se sinais causais mínimos, modelos compactos e explicação de regimes alcançam erro aceitável com menor custo computacional e menor dependência de sensores.

As hipóteses 1–5 precisam de busca de anterioridade específica, principalmente artigos de fault-tolerant forecasting, covariate shift, domain adaptation, concept drift, change-point detection, missing sensors, and cross-domain HPC/AI workload forecasting.

## Protocolo para reivindicar contribuição científica
- Pré-registrar pergunta, alvos, horizontes, split e baselines antes de olhar o holdout.
- Criar splits por sessão/job/dia/cluster/hardware; nunca random split por linha.
- Reportar métricas nativas (W, °C, %, segundos) e normalizadas; skill score em relação à persistência; resultados por entidade/regime.
- Fazer múltiplas seeds e intervalos de confiança por sessão/cluster, respeitando autocorrelação.
- Fazer ablation de canais e de módulos; reportar custo, latência, memória e taxa de atualização.
- Comparar contra baselines robustos: persistência, moving average causal, EWMA, linear/ridge, LightGBM/XGBoost se suportado e LSTM/TCN/Transformer quando o dataset justificar.
- Distinguir previsão, detecção, decisão e controle. Uma previsão melhor não prova economia de energia, redução de falhas ou melhoria operacional.
- Registrar reprodutibilidade, versões, hashes, licença e limitações de cada dataset.

## Formulação provisória da pergunta de pesquisa
“Em que condições um sistema temporal leve e adaptativo consegue manter previsões calibradas de potência e estado térmico de infraestrutura computacional sob mudança de regime, diferenças entre ambientes e indisponibilidade parcial de sensores, superando baselines causais e modelos de referência em testes agrupados por sessão e instalação?”

Essa pergunta ainda não prova originalidade. Ela organiza um programa experimental cuja contribuição dependerá dos resultados.

## Nota de auditoria de licenças (21/11/2026)
- AcmeTrace: LICENSE.txt do repositório oficial começa com Creative Commons Attribution 4.0 International. A cópia Hugging Face examinada também traz CC BY 4.0. Os arquivos podem ser candidatos a uso inclusive comercial, respeitando atribuição e termos CC BY; manter citações de versão e proveniência.
- HazardNet, M100 e PM100 v3: metadados consultados diretamente na API Zenodo reportam CC BY 4.0.
- H100/B200 Figshare: API retorna CC BY 4.0, em conflito com o README do repositório e a licença do artigo (CC BY-NC-ND 4.0). Não assumir direito de uso comercial/adaptação até resolução.

## Atualização de anterioridade — revisão adicional (21/11/2026)

### 9. A Dynamic GPU Power Prediction Framework for Production HPC Applications
Fatih Acun, Zhengji Zhao, Ermal Rrapaj, Brian Austin, Ayse K. Coskun e Nicholas J. Wright (Boston University / Lawrence Berkeley National Laboratory). Manuscrito técnico disponível em: https://www.bu.edu/peaclab/files/2026/04/pap124s3-file1.pdf
- Usa telemetria DCGM leve e contínua em Perlmutter (NERSC), com GPUs NVIDIA A100; amostra DCGM em intervalos de 10 s.
- Prevê potência por GPU em horizontes curtos indicados como 10–30 s; utiliza LSTM genérico e modelos específicos por aplicação.
- O resumo reporta RMSE médio de 50 W para o modelo genérico; modelos especializados reduzem erro em até 48% em relação ao genérico, e canais DCGM além do histórico de potência reduzem RMSE em até 15,8% em relação a modelos somente de potência.
- Reporta inferência do modelo de cerca de 3 µs; a discussão descreve aquisição, pré-processamento e execução de ponta a ponta.
- Dados abrangem aplicações de produção (Chroma, VASP, E3SM, ATLAS, Espresso). Os autores destacam que mudança do mix de aplicações pode degradar modelos e que a portabilidade entre fornecedores ainda requer avaliação.
- Implicação para a ATOCIA: previsão leve por GPU, uso de telemetria operacional e adaptação específica por workload já têm antecedentes fortes. Não reivindicar isso como novidade.

### 10. Grid-Oriented Probabilistic Load Forecasting for AI Data Centers
Qingyi Yao, Ding Lin, Tianqiao Zhao, Meng Yue e Jianhui Wang, preprint arXiv de 06/11/2026: https://arxiv.org/abs/2611.08929
- Propõe benchmark aberto com telemetria GPU e logs de scheduler do MIT Supercloud TX-Gaia, cluster de 448 GPUs; tarefas de 1 h, 4 h e 24 h.
- Combina previsão quantílica, calibração online condicionada ao regime, geração de cenários temporais e dimensionamento de reserva.
- Um modelo LightGBM com intervalo nominal de 90% chegou a 63,4% de cobertura no horizonte de 24 h; calibração online elevou a 87,3%.
- A amostragem independente de quantis distorceu rampas e picos; reconstruir dependência temporal reduziu o custo de reserva reportado em 7,4–10,6%.
- Implicação: incerteza calibrada, dependência temporal e métricas de decisão já são exploradas. ATOCIA precisa comparar diretamente com esse benchmark quando aplicável, e não vender apenas “previsão com incerteza”.

### 11. Antecedentes de adaptação e mudança de domínio
- Mo et al., “Learning from imbalance: Cross-server power prediction in large data centers via domain adaptation regression”, Expert Systems with Applications, 2025, DOI 10.1016/j.eswa.2025.127845. Trata explicitamente da heterogeneidade entre servidores e mudança de distribuição.
- Mo et al., TGCP, IEEE Transactions on Cloud Computing, 2025, DOI 10.1109/TCC.2025.3575790. Transfere conhecimento entre workloads para prever potência em um workload-alvo com poucos dados.
- He, Chang e Sun, “Cross-Cloud Transfer Learning for AI Training Capacity Forecasting under Workload and Topology Distribution Shift”, 2024, DOI 10.69987/JACS.2024.40108. Trata mudança de domínio em previsão de capacidade GPU; alvo é capacidade, não potência instantânea, portanto é antecedente metodológico, não comparação direta.
- Um estudo de 2026 sobre previsão de utilização GPU multi-horizonte no MIT Supercloud avalia heterogeneidade entre dispositivos e mascaramento de entradas, mas explicita que não prova generalização entre clusters: https://www.mdpi.com/2079-9292/15/17/3798.

### 12. Contexto brasileiro — o que a busca permite afirmar
- Ferreira et al. (UFPE, UFRPE, UFAM e Bergische Universität), 2019, DOI 10.3390/info10030113, propõem ANN para estimar consumo energético de data center e impactos/custos ambientais em escala mensal/anual. É pesquisa brasileira relevante em energia de data centers, mas não é previsão de potência individual de GPU em alta frequência.
- A varredura encontrou também trabalhos brasileiros sobre previsão de carga elétrica geral, DVFS e energia de aplicações paralelas. Não encontrou, nesta busca preliminar, evidência pública diretamente equivalente à linha de previsão operacional per-GPU com telemetria DCGM em HPC de produção.
- Isso NÃO prova ausência de uso por operadores brasileiros, empresas, laboratórios ou sistemas proprietários. A conclusão defensável é que a disponibilidade pública de benchmarks comparáveis e estudos abertos específicos ainda parece limitada; isso requer revisão sistemática, busca de patentes e entrevistas antes de qualquer alegação de pioneirismo nacional.
- O relatório Cetic.br/NIC.br e o estudo do BNDES tratam de infraestrutura, transparência e padronização de dados do setor, não provam ausência de modelos preditivos privados.

## Revisão da hipótese de contribuição
A combinação “potência + utilização + temperatura”, “memória rápida/lenta”, “modelo leve”, “previsão multi-horizonte”, “transferência entre workloads” ou “intervalo de incerteza” não deve ser tratada isoladamente como novidade.

A hipótese de pesquisa mais defensável para testar passa a ser:
**robustez operacional e generalização sob observabilidade imperfeita** — manter previsões úteis e calibradas quando canais de sensores faltam, a cadência muda, há mudança de regime e o hardware/workload de teste não foi visto no treino; além de medir se isso melhora previsão de rampas/picos e decisões em modo sombra.

Essa formulação é uma direção experimental, não uma reivindicação de originalidade. Há antecedentes adjacentes em adaptação de domínio, missingness e calibração; será necessária revisão sistemática mais ampla e comparação direta com implementações disponíveis.

## 13. PM100 audit integral e antecedente de previsão pré-execução
A auditoria completa do PM100 v1 (Parquet 105.940.147 bytes) foi concluída com checksum MD5 confirmado. O schema real contém \`power_consumption\` como lista de inteiros, e não \`node_power_consumption\`. Foram inspecionados 231.238 jobs e 65.173.805 leituras de potência; 210.573 jobs têm GPU alocada e 81.481 jobs GPU têm pelo menos 30 amostras (10 min na cadência declarada de 20 s). Mediana de sequência: 10 amostras. Todos os registros têm sequência não vazia.
- Semântica: soma de \`ps0_input_power + ps1_input_power\` nos nós alocados ao job, a cada 20 s. O mapeamento M100 identifica \`psX_input_power\` em Watts. Portanto, é potência agregada dos nós/PSUs do job, não potência isolada de GPU nem telemetria térmica GPU.
- Relatório reproduzível: \`RESEARCH_EXTERNAL/PM100/PM100_AUDIT_REPORT_V1.md\`; resumo JSON e schema em \`PM100/audit/\`.
- Antecedente próximo: “An online algorithm for power consumption prediction of HPC workload”, Future Generation Computer Systems 175 (fev. 2026), DOI 10.1016/j.future.2025.108064, usa PM100 e F-DATA para prever mínimo/média/máximo de potência de jobs antes da execução; o resumo reporta erro abaixo de 22% no PM100. Não reivindicar novidade para previsão pré-execução de potência de jobs com metadados de submissão.
- A pergunta online intra-execução — prever a trajetória futura a partir de leituras de potência já observadas — é distinta, mas requer protocolo separado, sem concatenar sequências de jobs e com holdout agrupado por job.

O PM100 passa a ser um conjunto secundário viável para previsão de potência agregada do job durante a execução; não substitui AcmeTrace ou outro conjunto com alvo per-GPU para a pergunta principal ATRP-1.
