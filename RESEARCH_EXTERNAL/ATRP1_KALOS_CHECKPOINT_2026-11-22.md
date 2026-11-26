# ATOCIA / ATRP-1 — checkpoint experimental Kalos
**Data:** 22/11/2026  
**Status:** piloto de previsão temporal com resultado promissor, ainda não validação externa nem produto.

## 1. Resultado mais recente

A avaliação cronológica com oito janelas, usando o Huber Ridge de 13 atributos, obteve no recorte de teste de **30/08/2023**:

| Métrica | Persistência | ATRP-1 | Redução |
|---|---:|---:|---:|
| MAE | 58,736 W | 44,911 W | **23,54%** |
| RMSE | 122,844 W | 86,568 W | **29,53%** |

- 317.560 previsões no teste, 2.335 GPUs e 292 hosts.
- Horizonte: 15 segundos à frente, em amostragem de 15 segundos.
- Melhora média do MAE por host: 13,82 W.
- Bootstrap pareado por host: IC 95% de 12,26 a 15,40 W (2.000 reamostragens).
- 198 hosts melhoraram; 94 tiveram piora. Portanto, o ganho agregado não é universal.
- O baseline escolhido na validação de 29/08 foi persistência. O alpha escolhido na mesma validação foi 10, entre {10, 100, 1000}.
- 30/08 não foi usado para escolher os hiperparâmetros ou o baseline.

Este resultado substitui o papel de teste final do experimento anterior: 29/08 passou a ser validação/desenvolvimento após a ablação anterior. O dia 30/08 é o novo holdout temporal, mas ainda é apenas uma janela curta dentro do mesmo cluster Kalos.

## 2. Diagnóstico por utilização

| Utilização observada em t | N | MAE persistência | MAE modelo | RMSE persistência | RMSE modelo |
|---|---:|---:|---:|---:|---:|
| 0–10% | 76.903 | 5,138 W | 6,538 W | 34,757 W | 28,248 W |
| 10–50% | 6.953 | 39,911 W | 37,048 W | 86,562 W | 71,191 W |
| 50–90% | 16.335 | 30,449 W | 29,344 W | 69,461 W | 59,180 W |
| 90–100% | 217.369 | 80,426 W | 59,909 W | 144,972 W | 101,196 W |

**Exceção importante:** no grupo 0–10%, o MAE aumentou em 1,40 W, apesar de o RMSE cair. Aproximadamente 24,2% das previsões do teste estão nesse grupo. O ganho global é impulsionado principalmente por cargas altas; é necessário melhorar a calibração/estimativa no regime de baixa utilização e voltar a testar essa estratificação em mais datas.

Na distribuição por host, o intervalo de confiança positivo descreve a média da diferença pareada entre hosts; ele não significa que todos os hosts melhoraram. O percentil 5 da melhora por host foi -2,77 W.

## 3. Dados e procedência

- Dataset: AcmeTrace, cluster Kalos.
- Repositório de referência: https://github.com/InternLM/AcmeTrace
- Snapshot usado para as novas extrações: Hugging Face `Qinghao/AcmeTrace`, revisão `a484f7763a7812fc72eb49b8ba865b12fe7638e1`.
- A cópia Hugging Face `HuggingAGree/AcmeTrace` consultada tem os mesmos tamanhos e ETags dos três arquivos utilizados.
- O README oficial documenta coleta por DCGM/IPMI/Prometheus e cadência de 15 segundos para os logs de utilização.
- O código `data/utils.py` associa os nomes usados à telemetria DCGM. A documentação NVIDIA confirma as unidades: `DCGM_FI_DEV_POWER_USAGE` em W, `DCGM_FI_DEV_GPU_TEMP` em °C e `DCGM_FI_DEV_GPU_UTIL` em %.
- A licença CC BY 4.0 está incluída na distribuição do AcmeTrace; qualquer redistribuição exige atribuição e observância dos termos.

Fontes:
- AcmeTrace: https://github.com/InternLM/AcmeTrace
- NVIDIA DCGM Exporter Metrics: https://docs.nvidia.com/datacenter/dcgm/latest/reference/dcgm-exporter-metrics.html
- NVIDIA DCGM exporter metrics configuration: https://github.com/NVIDIA/dcgm-exporter/blob/main/deployment/templates/metrics-configmap.yaml

## 4. Painel temporal montado

O painel expandido contém oito janelas separadas, sem criar lags que atravessem os intervalos:

1. 17/08/2023 — treino
2. 22/08/2023 — treino
3. 25/08/2023 — treino
4. 26/08/2023 — treino
5. 27/08/2023 — treino
6. 28/08/2023 — treino
7. 29/08/2023 — validação
8. 30/08/2023 — teste final do experimento v1

- 2.351.503 tripletos completos de 2.397.912 posições possíveis: 98,06% de cobertura no conjunto de oito recortes.
- 2.344 identificadores de GPU e 293 hosts no conjunto.
- A expansão adicionou quatro janelas válidas com somente 24 MiB de ranges HTTP; não houve download integral dos CSVs de vários centenas de MB.
- As janelas de 23 e 24/08 foram excluídas porque os três arquivos de métricas não tinham timestamps comuns nos ranges amostrados.
- O painel cobre somente amostras curtas. Não representa cobertura contínua ou amostra representativa de todos os seis meses.

**Privacidade:** os identificadores de host/IP e GPU foram transformados em SHA-256 truncado sem salt. Isso é pseudonimização, não anonimização garantida. Manter o painel interno; antes de qualquer publicação externa, substituir por identificadores com chave/salt protegido ou remover os IDs persistentes.

## 5. Modelo e protocolo de avaliação

- Alvo: potência da GPU por dispositivo em t+15 s.
- 13 variáveis: três lags para potência, temperatura e utilização, além das diferenças de potência e das mudanças recentes de temperatura/utilização.
- Modelo: Huber IRLS com correção residual sobre persistência.
- Padronização de atributos calculada somente no treino.
- Treino: janelas 1–6, 1.701.112 previsões.
- Validação: 29/08, 278.936 previsões.
- Teste: 30/08, 317.560 previsões.
- Janelas não são conectadas; a amostra de teste não participou da seleção de alpha/baseline.
- O artefato NPZ guarda coeficientes, médias/desvios do treino, alpha, delta de Huber, nomes dos atributos e baseline.

## 6. Histórico experimental que deve permanecer visível

- Primeiro Ridge residual: falhou em MAE no teste de 29/08 (59,29 W contra 55,95 W para persistência), apesar de RMSE menor. É um resultado negativo e deve permanecer no histórico.
- Huber Ridge de 16 atributos, com três interações: MAE de 49,117 W em 29/08, redução de 12,21% contra persistência.
- Ablação sem as interações, 13 atributos: MAE de 49,102 W, redução de 12,24%. As interações não trouxeram benefício prático; a versão mais simples foi mantida.
- Como o teste de 29/08 foi consultado na ablação, não deve mais ser chamado de teste intocado. Ele foi reutilizado como validação no experimento com oito janelas.
- Experimento atual com treino ampliado: novo teste de 30/08, redução de MAE de 23,54% e de RMSE de 29,53% contra persistência.

## 7. Limitações e interpretação

1. Uma janela curta de 30/08, no mesmo cluster Kalos e em GPUs/hosts já observados no treino. É evidência de generalização temporal limitada, não de generalização entre clusters ou arquiteturas.
2. Só um horizonte (15 s) e uma cadência de 15 s; não há avaliação de transientes subsegundo.
3. 94 hosts pioraram em MAE; o grupo de utilização 0–10% também piorou em MAE.
4. Bootstrap por host não elimina dependência temporal, correlação espacial ou efeitos do dia/cluster.
5. Previsão melhor não demonstra economia de energia, redução de custo, segurança térmica ou benefício operacional.
6. Ainda não há reivindicação de novidade científica, superioridade universal, validação de produção, parceria institucional ou prontidão comercial.

## 8. Artefatos reproduzíveis

- Painel: `ACMETRACE_KALOS_PILOT/kalos_gpu_panel_8windows_v2.csv.gz`
- Relatório de extração: `ACMETRACE_KALOS_PILOT/kalos_gpu_panel_8windows_v2_report.json`
- Script de extração: `extract_acmetraces_kalos_8windows_v2.py`
- Script de avaliação: `atrp1_huber_13f_eightwindow_eval.py`
- Métricas: `ACMETRACE_KALOS_PILOT/atrp1_huber_13f_train6_val29_test30_v1.json`
- Parâmetros treinados: `ACMETRACE_KALOS_PILOT/atrp1_huber_13f_train6_val29_test30_v1_model.npz`

SHA-256:
- Modelo NPZ: `4ea1584614de77ae97f5e5a00b29fa8d50d8338a23c2a7240d6f28954bfb21e9`
- Painel CSV.gz: `b52fc9898e52f19b8947c42453dedf22aaf7191fa87564070cdced04788485bc`

## 9. Próximos passos recomendados

1. Preservar os holdouts de 30/08, 31/08 e Seren como resultados já observados; não voltar a usá-los para escolher versões futuras.
2. Investigar o erro de baixa utilização e a perda de MAE na transferência para Seren.
3. Desenvolver uma nova variante com adaptação de domínio somente usando janelas de Seren separadas para treino/validação; reservar outra data ou cluster intocado como teste final.
4. Auditar metadados de hardware por cluster. O resumo público obtido registra estatísticas de jobs, mas não identifica claramente os modelos de GPU por host.
5. Comparar contra uma cesta pré-especificada de baselines adicionais e documentar todas as seleções.
6. Testar intervalos de previsão calibrados, robustez a sensores ausentes e, depois, preparar o pacote técnico para discussão com universidade/laboratório.

## 10. Segundo holdout congelado — 31/08/2023

Após gerar e congelar os parâmetros do modelo (SHA-256 idêntico ao artefato da avaliação de 30/08), o mesmo modelo foi aplicado a um recorte separado de 31/08, sem retreino, ajuste, calibração ou seleção.

| Métrica | Persistência | ATRP-1 congelado | Redução |
|---|---:|---:|---:|
| MAE | 56,152 W | 44,403 W | **20,92%** |
| RMSE | 120,789 W | 87,684 W | **27,41%** |

- 366.595 previsões, 2.335 GPUs e 292 hosts.
- Janela: 07:20:15–08:00:00 (Asia/Shanghai), 160 timestamps de entrada; 157 timestamps de previsão.
- Melhora média do MAE por host: 11,74 W; bootstrap pareado por host, IC 95%: 10,44–13,00 W.
- 192 hosts melhoraram; 100 pioraram.
- O recorte acontece em horário diferente daquele de 30/08 e não participou do treino nem da validação.
- O mesmo artefato NPZ foi usado, sem alteração: SHA-256 `4ea1584614de77ae97f5e5a00b29fa8d50d8338a23c2a7240d6f28954bfb21e9`.

### Diagnóstico do segundo holdout

| Utilização em t | N | MAE persistência | MAE modelo | RMSE persistência | RMSE modelo |
|---|---:|---:|---:|---:|---:|
| 0–10% | 95.739 | 3,347 W | 3,905 W | 28,488 W | 22,602 W |
| 10–50% | 6.133 | 39,827 W | 35,668 W | 84,649 W | 69,058 W |
| 50–90% | 15.817 | 28,892 W | 27,240 W | 68,449 W | 57,038 W |
| 90–100% | 248.906 | 78,597 W | 61,286 W | 143,882 W | 103,938 W |

O grupo de 0–10% voltou a apresentar uma pequena piora no MAE (0,56 W), mesmo com melhoria do RMSE. Isso reforça que a próxima iteração precisa abordar explicitamente o regime de baixa utilização, sem ajustar o modelo usando os holdouts já observados.

### Artefatos do holdout de 31/08

- Painel: `ACMETRACE_KALOS_PILOT/kalos_gpu_panel_aug31_2023_holdout_v1.csv.gz`
- Auditoria de extração: `ACMETRACE_KALOS_PILOT/kalos_gpu_panel_aug31_2023_holdout_v1_report.json`
- Avaliação congelada: `ACMETRACE_KALOS_PILOT/atrp1_frozen_model_aug31_holdout_eval_v1.json`
- Extrator: `extract_aug31_tail_holdout_v1.py`
- Avaliador: `atrp1_apply_frozen_model_aug31.py`
- SHA-256 do painel de 31/08: `f81ff51fdb2edce239958d0422d8669c2989bc12600fe71f4ee4d2277b67e5a3`

Os dois testes de 30 e 31/08 oferecem evidência repetida de ganho temporal no Kalos com o mesmo modelo congelado. Ainda assim, são duas janelas curtas de um único cluster, não uma validação independente em outro cluster, fabricante ou arquitetura.

**Conclusão:** o ATRP-1 tem dois resultados temporais positivos no Kalos (MAE -23,54% e -20,92%) com o mesmo modelo congelado. Isso sustenta continuar a investigação, mas ainda não sustenta uma promessa comercial nem generalização ampla.

## 11. Transferência zero-shot para o cluster Seren

O modelo treinado apenas no Kalos foi aplicado à janela Seren de 18/08/2023, sem ajuste, calibração, seleção ou retreino. Os dois clusters são identificados pelo repositório AcmeTrace como clusters GPU independentes. Este é um teste espacial de transferência dentro do mesmo dataset, não uma avaliação em uma organização externa.

| Métrica | Persistência | Modelo Kalos aplicado em Seren | Redução |
|---|---:|---:|---:|
| MAE | 41,471 W | 41,106 W | **0,88%** |
| RMSE | 99,028 W | 85,408 W | **13,75%** |

- 362.624 previsões, 1.960 GPUs e 245 hosts.
- Janela: 07:12:45–08:00:00 (Asia/Shanghai), 190 timestamps; horizonte de 15 segundos.
- Melhora média por host: 0,35 W; bootstrap pareado por host, IC 95%: -0,12 a 0,86 W. O intervalo inclui zero.
- 111 hosts melhoraram e 134 tiveram MAE maior.
- O modelo não produziu previsões negativas.
- O RMSE caiu de forma mais clara que o MAE, sugerindo redução de erros grandes sem redução consistente do erro absoluto típico.
- Na faixa de utilização 0–10%, o MAE piorou de 3,37 W para 4,27 W, embora o RMSE tenha caído de 25,26 W para 21,85 W.
- Nas faixas de 10–50%, 50–90% e 90–100%, o MAE melhorou apenas de forma modesta.

### Leitura de transferência

O resultado de Seren é **inconclusivo para MAE**: uma queda de 0,88% é pequena e o intervalo de confiança por host inclui zero. O ganho de RMSE de 13,75% merece investigação, mas não substitui uma melhora consistente do MAE. Assim, a vantagem forte observada no Kalos não se transferiu de forma convincente para o Seren.

As médias padronizadas dos atributos de nível ficaram relativamente próximas das estatísticas de treino (por exemplo, z médio de temperatura +0,29 e de utilização +0,19; desvios-padrão de 1,03 e 0,90). Isso não revela um deslocamento marginal extremo, mas também não exclui mudanças de relação entre telemetria e potência, distribuição de workloads, hardware ou efeitos de host.

O README oficial descreve Kalos e Seren como dois clusters GPU independentes. O `cluster_summary.csv` público consultado resume cargas e estatísticas de jobs, mas não identifica claramente o modelo de GPU por host. Portanto, ainda não é correto atribuir a diferença de transferência a uma arquitetura específica.

### Artefatos Seren

- Painel: `ACMETRACE_KALOS_PILOT/seren_gpu_panel_aug18_2023_crosscluster_v1.csv.gz`
- Relatório de extração: `ACMETRACE_KALOS_PILOT/seren_gpu_panel_aug18_2023_crosscluster_v1_report.json`
- Avaliação congelada: `ACMETRACE_KALOS_PILOT/atrp1_frozen_kalos_model_on_seren_crosscluster_eval_v1.json`
- Extrator: `extract_seren_crosscluster_v1.py`
- Avaliador: `atrp1_apply_frozen_model_seren_crosscluster.py`
- SHA-256 do painel: `a38e908b87fa80aca4b50a21502f473b6e3cecf4ac7580faf6e92eebce179e00`

O Seren é agora um holdout de transferência já observado. Não deve ser usado para ajustar retrospectivamente o modelo e depois apresentado como teste independente dessa nova versão. Qualquer adaptação futura precisa de outro conjunto de teste intocado.
