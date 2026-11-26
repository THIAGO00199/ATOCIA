# ATRP-1 — reanálise de incerteza com dependência temporal e espacial

**Data:** 22/11/2026  
**Fase:** auditoria estatística dos holdouts congelados  
**Status:** concluída; aguarda autorização para o próximo bloco  
**Escopo:** somente reanálise dos resultados existentes. Sem treino, ajuste, seleção, calibração ou alteração de pesos.

## 1. Pergunta

Os ganhos de MAE do ATRP-1 contra persistência continuam sustentados quando a incerteza considera simultaneamente:

1. observações repetidas e correlacionadas dentro de cada host;
2. choques temporais compartilhados por GPUs e hosts no mesmo instante?

O bootstrap anteriormente registrado reamostrava hosts, mas não preservava explicitamente blocos temporais sincronizados. Como a telemetria tem amostragem de 15 segundos e as previsões usam janelas temporais sobrepostas, tratar timestamps como independentes seria inadequado.

## 2. Integridade e dados usados

Foi usado o mesmo NPZ congelado nas três avaliações:

- Modelo: `atrp1_huber_13f_train6_val29_test30_v1_model.npz`
- SHA-256: `4ea1584614de77ae97f5e5a00b29fa8d50d8338a23c2a7240d6f28954bfb21e9`
- Alpha: 10
- Baseline: persistência

Painéis e revisão de origem:

| Recorte | Painel | SHA-256 |
|---|---|---|
| Kalos, 30/08/2023 | `kalos_gpu_panel_8windows_v2.csv.gz` | `b52fc9898e52f19b8947c42453dedf22aaf7191fa87564070cdced04788485bc` |
| Kalos, 31/08/2023 | `kalos_gpu_panel_aug31_2023_holdout_v1.csv.gz` | `f81ff51fdb2edce239958d0422d8669c2989bc12600fe71f4ee4d2277b67e5a3` |
| Seren, 18/08/2023 | `seren_gpu_panel_aug18_2023_crosscluster_v1.csv.gz` | `a38e908b87fa80aca4b50a21502f473b6e3cecf4ac7580faf6e92eebce179e00` |

Os três painéis referem-se à revisão AcmeTrace `a484f7763a7812fc72eb49b8ba865b12fe7638e1`.

As previsões foram reconstruídas diretamente dos painéis com o NPZ existente. As métricas agregadas coincidem com os relatórios originais, com diferenças apenas de arredondamento numérico. Não houve leitura de um conjunto novo para escolher ou ajustar o modelo.

| Recorte | Previsões | Instantes efetivos | GPUs | Hosts |
|---|---:|---:|---:|---:|
| Kalos, 30/08 | 317.560 | 136 | 2.335 | 292 |
| Kalos, 31/08 | 366.595 | 157 | 2.335 | 292 |
| Seren, 18/08 | 362.624 | 187 | 1.960 | 245 |

## 3. Método

A diferença pareada por observação foi calculada como:

`d_{t,g}=|y_{t,g}-p_{t,g}^{base}|-|y_{t,g}-p_{t,g}^{ATRP1}|`

Valores positivos favorecem o ATRP-1.

As somas de erro e contagens foram agregadas por timestamp e host. Para cada replicação:

- foram sorteados blocos circulares contíguos de timestamps, aplicados sincronizadamente a todos os hosts;
- foram reamostrados hosts com reposição, como clusters;
- os pesos temporais e os pesos de host foram combinados para calcular a diferença média de MAE e a redução percentual de MAE.

Foram usados 3.000 replicados por tamanho de bloco, semente 20261122 e quatro comprimentos definidos antes de interpretar os resultados: 2, 4, 8 e 16 instantes, equivalentes a 30, 60, 120 e 240 segundos. Os intervalos são percentis 2,5 e 97,5 da distribuição bootstrap.

O relatório também calcula a autocorrelação da diferença média de MAE entre modelo e baseline, agregada por timestamp, nos lags de 15, 30, 60 e 120 segundos.

## 4. Resultados pontuais reconstruídos

| Avaliação | MAE persistência | MAE ATRP-1 | Redução relativa de MAE |
|---|---:|---:|---:|
| Kalos, 30/08 | 58,736 W | 44,911 W | **23,54%** |
| Kalos, 31/08 | 56,152 W | 44,403 W | **20,92%** |
| Seren, 18/08 | 41,471 W | 41,106 W | **0,88%** |

A diferença absoluta de MAE foi de 13,825 W, 11,749 W e 0,365 W, respectivamente.

## 5. Intervalos com dependência temporal e por host

A tabela mostra a sensibilidade dos intervalos ao comprimento do bloco. O intervalo de diferença é a melhoria média de MAE por host, em watts. O intervalo percentual é a redução micro de MAE contra persistência.

| Recorte | Bloco | Melhora por host, IC 95% (W) | Redução micro de MAE, IC 95% |
|---|---:|---:|---:|
| Kalos 30/08 | 30 s | 11,84 a 15,82 | 21,15% a 25,70% |
| Kalos 30/08 | 60 s | 11,49 a 16,15 | 20,62% a 26,09% |
| Kalos 30/08 | 120 s | 11,42 a 16,25 | 20,32% a 26,49% |
| Kalos 30/08 | 240 s | 11,36 a 16,37 | 20,39% a 26,53% |
| Kalos 31/08 | 30 s | 10,08 a 13,44 | 18,84% a 22,83% |
| Kalos 31/08 | 60 s | 9,94 a 13,50 | 18,67% a 23,00% |
| Kalos 31/08 | 120 s | 10,05 a 13,59 | 18,82% a 22,98% |
| Kalos 31/08 | 240 s | 9,99 a 13,54 | 18,81% a 22,87% |
| Seren 18/08 | 30 s | -0,65 a 1,30 | -1,56% a 3,12% |
| Seren 18/08 | 60 s | -0,74 a 1,46 | -1,82% a 3,43% |
| Seren 18/08 | 120 s | -0,80 a 1,61 | -2,07% a 3,83% |
| Seren 18/08 | 240 s | -0,90 a 1,67 | -2,36% a 3,90% |

### Comparação com o bootstrap anterior por host

Os intervalos anteriores, que reamostravam hosts sem blocos de tempo, eram:

- Kalos 30/08: 12,26 a 15,40 W;
- Kalos 31/08: 10,44 a 13,00 W;
- Seren 18/08: -0,12 a 0,86 W.

Ao preservar blocos temporais sincronizados, os intervalos se alargam. Isso é esperado quando a dependência temporal é reconhecida. A conclusão qualitativa não muda: os dois ganhos no Kalos permanecem acima de zero; o resultado de MAE no Seren continua atravessando zero.

## 6. Evidência de dependência temporal

Autocorrelação da diferença média de MAE por timestamp:

| Recorte | Lag 15 s | Lag 30 s | Lag 60 s | Lag 120 s |
|---|---:|---:|---:|---:|
| Kalos 30/08 | 0,804 | 0,533 | 0,087 | 0,037 |
| Kalos 31/08 | 0,709 | 0,260 | -0,231 | -0,107 |
| Seren 18/08 | 0,630 | 0,324 | 0,201 | 0,056 |

A autocorrelação de lag 1 é alta nos três recortes. Portanto, milhares de previsões no mesmo instante não equivalem a milhares de observações temporais independentes. Esse diagnóstico sustenta a necessidade dos blocos sincronizados.

A autocorrelação é descritiva e calculada em janelas curtas; não deve ser tratada como prova isolada de estacionariedade ou como estimativa de dependência de longo prazo.

## 7. Interpretação

### Kalos

A redução de MAE permanece positiva nos dois holdouts temporais para todos os comprimentos de bloco testados, inclusive 4 minutos. A evidência do ganho dentro dessas duas janelas é, portanto, mais robusta do que a análise exclusivamente por host sugeria.

Isso ainda é evidência condicional às janelas observadas. Não demonstra generalização para outros dias, outros clusters, GPUs não vistas ou organizações externas.

### Seren

A melhora pontual de MAE é pequena, 0,88%. Todos os intervalos que incorporam blocos temporais incluem zero. A conclusão permanece: **não há evidência convincente de ganho em MAE na transferência zero-shot para Seren**. O resultado de RMSE previamente observado continua sendo uma pista separada, não uma substituição dessa conclusão.

### O que mudou com esta fase

O bootstrap por host não era inútil: ele descrevia a variação entre hosts naquela janela. O problema era interpretá-lo como se removesse também a dependência temporal comum. A nova análise corrige parcialmente essa lacuna e produz intervalos mais amplos e metodologicamente mais cautelosos.

## 8. Limitações que permanecem

1. Cada holdout continua sendo uma única janela curta: 136, 157 e 187 instantes efetivos.
2. Os blocos circulares conectam artificialmente o fim ao início da janela. Essa escolha é uma aproximação do moving-block bootstrap e deve ser lembrada ao interpretar os intervalos.
3. Com blocos de 4 minutos, cada recorte contém apenas cerca de 9 a 12 blocos efetivos. Assim, os intervalos são uma análise de sensibilidade, não uma garantia de precisão assintótica.
4. A reamostragem de hosts não cria novas organizações, dias ou populações de hardware.
5. As GPUs e hosts de Kalos são repetidos em relação ao treino; não há teste de generalização para entidades inteiramente novas.
6. A vantagem do Kalos está concentrada principalmente em utilizações altas; a piora de MAE na faixa de 0–10% continua registrada nos três recortes.
7. Melhor previsão de potência não demonstra economia de energia, redução de custo, segurança térmica ou benefício operacional.

## 9. Conclusão da fase

**Conclusão:** a evidência de melhoria de MAE do ATRP-1 em Kalos sobrevive à análise de dependência temporal e espacial nos dois holdouts observados. A transferência zero-shot para Seren continua inconclusiva para MAE. A análise anterior por host subestimava a incerteza temporal.

O resultado é suficiente para manter a hipótese de pesquisa e planejar uma validação mais ampla. Não é suficiente para reivindicar generalização ampla ou prontidão de produção.

## 10. Reprodutibilidade e estado dos arquivos

Script read-only criado para reproduzir a análise:

`RESEARCH_EXTERNAL/atrp1_dependence_bootstrap_v1.py`

Execução:

`python3 /home/iknowyou/ATOCIA/RESEARCH_EXTERNAL/atrp1_dependence_bootstrap_v1.py`

O script imprime os resultados em JSON e não grava avaliações, não retreina e não ajusta o modelo.

Arquivos originais preservados. Nenhum peso, painel, relatório anterior ou configuração foi alterado. Nenhum download adicional foi feito.

**Fase encerrada. Aguardar confirmação antes de iniciar o próximo bloco de pesquisa.**
