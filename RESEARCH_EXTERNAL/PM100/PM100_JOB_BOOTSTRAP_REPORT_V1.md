# PM100 — incerteza por job e estratificação por nós

**Data:** 22/11/2026  
**Fase:** validação estatística do benchmark causal PM100  
**Status:** concluída; aguarda confirmação para o próximo bloco  
**Natureza:** análise secundária de potência agregada por job; não é resultado per-GPU nem do ATRP-1.

## 1. Pergunta

A vantagem das médias móveis causais sobre persistência, observada no holdout cronológico do PM100, continua positiva quando a unidade de reamostragem é o job inteiro? O ganho também aparece em trabalhos que alocam diferentes quantidades de nós?

## 2. Integridade e protocolo preservado

- Dataset: PM100 v1, DOI 10.5281/zenodo.8129258.
- Arquivo: `job_table.parquet`.
- SHA-256: `10bc1ba948cd362657e97eea9b5f96ff16d77ac6e8e0e78894d60e2074d4fd89`.
- MD5 anteriormente confirmado contra Zenodo: `2a692d9b9dc4a6ee4bc5e3eb3d0fa6f5`.
- Unidade: Watts, potência agregada de entrada das PSUs de todos os nós alocados ao job.
- Cadência: 20 segundos.
- Jobs mantidos como sequências independentes; nenhum array foi concatenado.
- Split idêntico ao benchmark anterior: quantis cronológicos 70%/85% de `start_time`; jobs que cruzam os limites são descartados.
- Nenhuma janela ou baseline foi escolhida com base no teste.

O artigo do PM100 e a página oficial do Zenodo descrevem a seleção de jobs que executam sozinhos nos nós alocados, justamente para evitar atribuir a um job a potência de outro job concorrente. Este relatório usa a versão publicada do conjunto e não tenta reconstruir o filtro de exclusividade a partir dos logs brutos.

Fontes:
- Antici et al., “PM100: A Job Power Consumption Dataset of a Large-scale Production HPC System”, SC-W 2023, DOI 10.1145/3624062.3624263.
- Zenodo PM100 v1: https://zenodo.org/records/8129258

## 3. Método estatístico

Foi reconstruída a previsão de persistência e MA(3), MA(5), MA(10), respeitando os horizontes de 20, 40, 60 e 120 segundos.

A seleção feita anteriormente na validação foi mantida:

| Horizonte | Seleção micro | Seleção macro por job |
|---|---:|---:|
| 20 s | MA(3) | MA(3) |
| 40 s | MA(3) | MA(3) |
| 60 s | MA(5) | MA(3) |
| 120 s | MA(5) | MA(3) |

Foram calculados intervalos percentis de 95% com 5.000 reamostragens pareadas de jobs inteiros. Cada job sorteado leva junto todos os seus erros e previsões, preservando a dependência interna da sequência. Foram avaliadas duas métricas:

- **Micro:** todos os pontos de previsão recebem peso igual.
- **Macro:** primeiro calcula-se o MAE de cada job; depois cada job recebe o mesmo peso.

Os intervalos não tratam cada timestamp como observação independente.

## 4. Cobertura do teste

- 210.573 jobs GPU no universo usado para o split.
- 321 jobs descartados por cruzar fronteiras cronológicas.
- 10.842 jobs no horizonte de 20 s.
- 10.633 jobs no horizonte de 40 s.
- 10.506 jobs no horizonte de 60 s.
- 10.222 jobs no horizonte de 120 s.
- Entre 5,74 e 5,79 milhões de previsões por horizonte.

A diferença no número de jobs entre horizontes decorre do comprimento necessário da sequência para formar cada previsão.

## 5. Resultado e intervalos

| Horizonte | Baseline MAE micro | MA selecionada | MAE micro | Skill micro | IC 95% do skill micro |
|---|---:|---:|---:|---:|---:|
| 20 s | 184,54 W | MA(3) | 162,11 W | 12,15% | 10,46% a 13,55% |
| 40 s | 180,15 W | MA(3) | 165,39 W | 8,20% | 6,26% a 9,78% |
| 60 s | 196,19 W | MA(5) | 171,10 W | 12,79% | 9,99% a 14,99% |
| 120 s | 207,45 W | MA(5) | 184,63 W | 11,00% | 8,08% a 13,27% |

A análise macro, com a janela escolhida na validação macro (MA3 em todos os horizontes), também permaneceu positiva:

| Horizonte | MAE macro persistência | MAE macro MA(3) | Skill macro | IC 95% do skill macro |
|---|---:|---:|---:|---:|
| 20 s | 210,68 W | 196,60 W | 6,69% | 5,56% a 7,66% |
| 40 s | 212,28 W | 202,82 W | 4,46% | 3,40% a 5,43% |
| 60 s | 226,57 W | 210,67 W | 7,02% | 6,00% a 8,01% |
| 120 s | 257,54 W | 243,52 W | 5,44% | 4,69% a 6,18% |

Em todos os horizontes, os 5.000 replicados bootstrap produziram diferença positiva para as duas métricas e as duas seleções de janela. Isso significa que nenhum replicado sorteado apresentou perda no estimando correspondente; não é uma probabilidade literal de que o modelo seja superior em toda população futura.

## 6. Estratificação descritiva por quantidade de nós

A seleção micro da validação foi mantida em cada horizonte. Os valores abaixo são descritivos; ainda não foram calculados intervalos de confiança por subgrupo.

| Horizonte | Nós/job | Jobs | Skill micro |
|---|---|---:|---:|
| 20 s | 1 nó | 7.957 | 6,22% |
| 20 s | 2–4 nós | 808 | 14,20% |
| 20 s | 5+ nós | 2.077 | 13,45% |
| 40 s | 1 nó | 7.821 | 9,85% |
| 40 s | 2–4 nós | 776 | 13,36% |
| 40 s | 5+ nós | 2.036 | 6,87% |
| 60 s | 1 nó | 7.740 | 12,54% |
| 60 s | 2–4 nós | 753 | 15,42% |
| 60 s | 5+ nós | 2.013 | 12,47% |
| 120 s | 1 nó | 7.595 | 13,39% |
| 120 s | 2–4 nós | 678 | 17,20% |
| 120 s | 5+ nós | 1.949 | 9,47% |

A melhora pontual aparece nas três faixas de alocação. A magnitude, porém, varia: o grupo de 2–4 nós tem skill micro maior nos quatro horizontes, enquanto o grupo de 5+ nós apresenta skill macro menor em horizontes mais longos. Como os subgrupos não têm intervalos próprios nesta fase, não se deve interpretar essas diferenças como diferenças estatisticamente estabelecidas.

## 7. Auditoria adicional de proveniência

A página Zenodo e o artigo original descrevem PM100 como contendo somente jobs que executam isoladamente nos nós alocados. Isso é essencial para a interpretação física da potência agregada. O campo `shared` no Parquet apresenta categorias textuais heterogêneas (`OK`, `0`, `USER`) e não foi usado como substituto de uma verificação de sobreposição. A garantia de exclusividade aqui vem da metodologia declarada pelos autores e da proveniência do dataset, não de uma inferência a partir desse campo isolado.

O script original de extração também descreve a construção de tabelas por nó e timestamp para remover jobs concorrentes. O artigo esclarece que essa filtragem é necessária porque a potência de um nó compartilhado não pode ser atribuída com precisão a um job individual.

## 8. Limitações

1. O bootstrap reamostra jobs, mas não faz reamostragem em blocos de dias ou semanas. Jobs de um mesmo período podem compartilhar condições operacionais; a incerteza temporal comum ainda não está totalmente representada.
2. Os intervalos são condicionais ao holdout cronológico específico e ao Marconi100 de 2020.
3. A potência é agregada de todos os componentes dos nós alocados, não potência isolada de GPU.
4. O MAE em Watts cresce com a quantidade e configuração dos nós; comparar diretamente valores absolutos entre tamanhos de job não é apropriado sem normalização e contexto.
5. Médias móveis são baselines simples. O resultado não demonstra superioridade de um modelo ATOCIA, Ridge, árvore, rede neural ou método de estado da arte.
6. A estratificação por nós é exploratória; requer intervalos por subgrupo e controle de multiplicidade antes de conclusões inferenciais.
7. Não há inferência de economia de energia, redução de custo ou benefício operacional.

## 9. Conclusão da fase

**O benchmark de médias móveis no PM100 é estável à reamostragem pareada por job:** para os quatro horizontes, os intervalos de 95% permaneceram positivos tanto na métrica micro quanto na macro, usando escolhas de janela fixadas na validação.

O resultado reforça que existe sinal temporal na trajetória agregada de potência por job. Ele não é evidência de que a ATOCIA superou baselines, porque ainda não foi avaliado um modelo ATOCIA nesse conjunto. Tampouco deve ser confundido com o problema per-GPU do ATRP-1.

## 10. Artefatos e reprodutibilidade

- Script: `PM100/benchmark_job_bootstrap_v1.py`
- Saída integral: `PM100/audit/trajectory_job_bootstrap_v1.json`
- Este relatório: `PM100/PM100_JOB_BOOTSTRAP_REPORT_V1.md`

Execução:

`/home/iknowyou/ATOCIA/RESEARCH_EXTERNAL/PM100/.venv-audit/bin/python /home/iknowyou/ATOCIA/RESEARCH_EXTERNAL/PM100/benchmark_job_bootstrap_v1.py`

O script reusa o split e as seleções da validação, não treina modelo e não altera o Parquet original nem os relatórios anteriores.

**Fase encerrada. Aguardar confirmação antes do próximo bloco.**
