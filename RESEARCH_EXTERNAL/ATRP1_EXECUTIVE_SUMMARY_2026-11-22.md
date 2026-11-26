# ATOCIA / ATRP-1 — resumo executivo de pesquisa
**Atualizado em:** 22/11/2026  
**Classificação:** protótipo experimental; não é sistema de produção.

## Pergunta experimental

Usando apenas telemetria histórica de potência, temperatura e utilização, um modelo leve consegue prever a potência da GPU 15 segundos à frente e superar uma baseline de persistência?

## Modelo avaliado

- Huber Ridge com correção residual sobre persistência.
- 13 atributos causais construídos a partir de três amostras anteriores de potência, temperatura e utilização.
- Treino e padronização feitos somente com janelas do cluster Kalos.
- Alpha selecionado na validação de 29/08; valor final 10.
- Horizonte de previsão: 15 segundos.
- Pesos e escalas do modelo foram salvos em NPZ e verificados por SHA-256.

## Resultados

| Avaliação | Origem do modelo | Holdout | Redução MAE vs. persistência | Redução RMSE vs. persistência |
|---|---|---|---:|---:|
| Temporal 1 | Kalos | 30/08, 2.335 GPUs, 292 hosts | **23,54%** | **29,53%** |
| Temporal 2 | Mesmo modelo congelado | Kalos, 31/08, 2.335 GPUs, 292 hosts | **20,92%** | **27,41%** |
| Transferência zero-shot | Mesmo modelo treinado em Kalos | Seren, 18/08, 1.960 GPUs, 245 hosts | **0,88%** | **13,75%** |

Nos dois holdouts temporais do Kalos, a melhora média de MAE por host foi positiva e o intervalo bootstrap de 95% ficou acima de zero. No Seren, a melhora média por host foi de apenas 0,35 W, com IC 95% de -0,12 a 0,86 W: não há evidência convincente de ganho em MAE entre clusters. O RMSE, porém, caiu 13,75%.

## O que aprendemos

1. **Generalização temporal dentro de Kalos:** promissora em dois recortes posteriores, inclusive com o mesmo artefato congelado.
2. **Transferência para Seren:** MAE praticamente empatado com persistência; a vantagem de Kalos não se transferiu de forma convincente. O ganho de RMSE indica que o modelo ainda pode reduzir erros grandes.
3. **Baixa utilização:** o MAE piorou no grupo 0–10% nos três recortes de teste. Essa é uma limitação repetida e uma prioridade técnica.
4. **Distribuição por host:** nem todos melhoraram. No teste de 30/08, 198/292 hosts melhoraram; em 31/08, 192/292; em Seren, 111/245.

## Estado da evidência

**O que podemos afirmar:** o ATRP-1 superou persistência em MAE e RMSE em duas janelas temporais posteriores do Kalos. Aplicado sem adaptação a Seren, reduziu RMSE, mas não demonstrou ganho consistente de MAE.

**O que ainda não podemos afirmar:** generalização entre hardware, economia de energia, redução de custo, segurança operacional, novidade científica ampla ou prontidão comercial.

Os holdouts de 30/08, 31/08 e Seren já foram observados. Não devem ser reutilizados como testes intocados de futuras variantes. Uma versão nova precisa de treino/validação próprios e de novo holdout independente.

## Próxima hipótese de pesquisa

Investigar **adaptação de domínio com poucos dados de calibração**, junto de um tratamento específico para baixa utilização. O próximo experimento deve comparar:
- modelo Kalos zero-shot em Seren (resultado já registrado);
- calibração de baixo custo usando apenas um subconjunto de treino de Seren;
- teste posterior em outra janela Seren ainda não utilizada.

O teste final precisa permanecer intocado até que arquitetura, baseline e hiperparâmetros estejam definidos. Antes de alegar transferência entre arquiteturas, será necessário identificar os modelos de GPU de cada cluster; o resumo público do AcmeTrace consultado não fornece o SKU por host.

## Dados e rastreabilidade

AcmeTrace é o dataset público do Shanghai AI Lab. O README do projeto descreve dois clusters GPU independentes e telemetria com cadência de 15 segundos. As unidades foram verificadas pelo mapeamento dos campos DCGM e documentação da NVIDIA. Os CSVs completos não foram baixados: os painéis foram montados por faixas HTTP limitadas.

Fontes:
- https://github.com/InternLM/AcmeTrace
- https://docs.nvidia.com/datacenter/dcgm/latest/reference/dcgm-exporter-metrics.html
- https://github.com/NVIDIA/dcgm-exporter/blob/main/deployment/templates/metrics-configmap.yaml

## Arquivos principais

- Relatório técnico detalhado: `ATRP1_KALOS_CHECKPOINT_2026-11-22.md`
- Modelo congelado e parâmetros: `ACMETRACE_KALOS_PILOT/atrp1_huber_13f_train6_val29_test30_v1_model.npz`
- Resultados Kalos (30/08): `ACMETRACE_KALOS_PILOT/atrp1_huber_13f_train6_val29_test30_v1.json`
- Resultado Kalos (31/08): `ACMETRACE_KALOS_PILOT/atrp1_frozen_model_aug31_holdout_eval_v1.json`
- Resultado Seren: `ACMETRACE_KALOS_PILOT/atrp1_frozen_kalos_model_on_seren_crosscluster_eval_v1.json`

**Síntese:** há um resultado temporal interessante, mas a transferência entre clusters ainda é o gargalo. ATOCIA tem agora um problema de pesquisa concreto, mensurável e honesto para levar a uma discussão acadêmica.
