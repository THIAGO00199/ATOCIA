# PM100 — bootstrap temporal por blocos de datas de início

**Data:** 22/11/2026  
**Fase:** sensibilidade temporal da incerteza do benchmark de baselines  
**Status:** concluída; aguarda confirmação para o próximo bloco  
**Natureza:** análise de baselines causais sobre potência agregada por job; não é resultado do ATRP-1 nem de um modelo ATOCIA.

## 1. Pergunta

Os ganhos das médias móveis sobre persistência permanecem positivos quando jobs iniciados em datas próximas são reamostrados juntos, em vez de tratar cada job como unidade independente?

## 2. Protocolo

- Dataset: PM100 v1, arquivo `job_table.parquet`.
- SHA-256: `10bc1ba948cd362657e97eea9b5f96ff16d77ac6e8e0e78894d60e2074d4fd89`.
- Split cronológico original preservado: quantis 70%/85% de `start_time`; somente jobs do teste já definido.
- Escolhas feitas na validação e congeladas: micro MA(3), MA(3), MA(5), MA(5) para 20/40/60/120 s; macro MA(3) nos quatro horizontes.
- Reamostragem circular de blocos consecutivos de datas de início, com comprimentos de 1, 2 e 3 dias; 5.000 replicações por comprimento; seed 20261122.
- Cada job permanece inteiro e pareado entre persistência e média móvel. Jobs que começam na mesma data recebem a mesma multiplicidade na replicação.
- Métricas: skill percentual micro (todos os forecasts com peso igual) e macro (cada job com peso igual).
- Nenhum ajuste, seleção ou treinamento foi feito no teste. O Parquet e os relatórios anteriores não foram modificados.

## 3. Cobertura temporal

O holdout contém **11 datas de início consecutivas**, de 2020-10-03 a 2020-10-13. O número de jobs válidos varia de 10.222 a 10.842 conforme o horizonte.

Essa duração é curta para inferência temporal: blocos de três dias deixam poucas unidades efetivas de reamostragem. Por isso, os resultados abaixo devem ser lidos como análise de sensibilidade, não como estimativa precisa da variabilidade entre períodos longos.

## 4. Intervalos de 95% — blocos de três dias

| Horizonte | Skill micro | IC 95% micro | Skill macro | IC 95% macro |
|---|---:|---:|---:|---:|
| 20 s | 12,15% | 7,73% a 15,79% | 6,69% | 3,16% a 12,67% |
| 40 s | 8,20% | 5,41% a 9,87% | 4,46% | 1,84% a 8,20% |
| 60 s | 12,79% | 7,52% a 16,34% | 7,02% | 3,59% a 12,37% |
| 120 s | 11,00% | 7,05% a 13,58% | 5,44% | 3,50% a 9,68% |

## 5. Sensibilidade ao comprimento do bloco

Em todos os quatro horizontes, os limites inferiores dos intervalos de skill permaneceram acima de zero para os três comprimentos avaliados (1, 2 e 3 dias), tanto para micro quanto para macro.

O caso mais próximo de zero foi a métrica macro em 40 s, cujo limite inferior foi **0,52%** com blocos de um dia. Com blocos de dois e três dias, os limites inferiores foram 1,21% e 1,84%, respectivamente.

Isso sustenta a conclusão restrita de que o ganho das médias móveis não desapareceu nesta análise de sensibilidade temporal. Não significa probabilidade de superioridade em qualquer período futuro, nem elimina dependências que o desenho não capturou.

## 6. Limitações importantes

1. O holdout tem apenas 11 datas. O bootstrap circular com blocos de 3 dias tem poucas unidades temporais efetivas; os intervalos podem ser instáveis.
2. A atribuição de cada job ao bloco usa sua data de início. Um job longo pode atravessar dias e compartilhar condições com jobs iniciados em outras datas; essa dependência não é inteiramente preservada.
3. O procedimento é uma sensibilidade de agrupamento temporal, não um bootstrap temporal perfeito da série operacional.
4. O resultado é condicionado ao holdout específico do Marconi100 em outubro de 2020.
5. O alvo é potência agregada de entrada dos nós alocados ao job, não potência isolada de GPU.
6. Médias móveis são baselines simples. Nenhum modelo ATOCIA foi avaliado nesta fase.

## 7. Conclusão

**A vantagem das médias móveis sobre persistência permaneceu positiva sob reamostragem por blocos de 1–3 dias, nos quatro horizontes e nas métricas micro e macro.**

A evidência é encorajadora, mas limitada pela curta extensão temporal do teste e pela forma como jobs que atravessam dias são agrupados. O próximo estudo não deve transformar esses intervalos em alegação de generalização temporal ampla.

## 8. Artefatos

- Script: `PM100/benchmark_timeblock_bootstrap_v1.py`
- Resultado integral: `PM100/audit/trajectory_timeblock_bootstrap_v1.json`
- Este relatório: `PM100/PM100_TIMEBLOCK_BOOTSTRAP_REPORT_V1.md`

O script recalcula as métricas usando o split e as escolhas de janela já existentes, escreve somente o novo JSON e não altera o Parquet nem os resultados anteriores.

**Fase encerrada. Aguardar confirmação antes do próximo bloco.**
