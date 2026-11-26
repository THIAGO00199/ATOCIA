# PM100 — bootstrap pareado dos modelos online V2

**Réplicas:** 10,000 por estimativa  |  **Seed:** 20261123  |  **Data:** 23/11/2026

Parâmetros EWMA congelados conforme a seleção na validação V2. Nenhum hiperparâmetro foi reajustado. Diferença = MAE do comparador − MAE EWMA; valores positivos favorecem EWMA.

O bootstrap por job estima incerteza sobre jobs do holdout; o bootstrap por data preserva agrupamento de jobs pela data de início. O holdout contém poucas datas, portanto o intervalo por data é sensível ao pequeno número de clusters.

## Horizonte 20 s

EWMA α congelado: 0.70.
### EWMA vs MA3

- Jobs: 10,278; datas de início: 11.
- Diferença pontual micro (MAE MA3 − EWMA): **-5.048 W**.
- IC95% job bootstrap micro: [-6.930, -3.141] W.
- IC95% cluster por data micro: [-10.365, -1.037] W.
- Diferença pontual macro: **1.884 W**.
- IC95% job bootstrap macro: [0.039, 4.027] W.
- IC95% cluster por data macro: [-3.679, 10.159] W.

### EWMA vs MA5

- Jobs: 10,278; datas de início: 11.
- Diferença pontual micro (MAE MA5 − EWMA): **-7.030 W**.
- IC95% job bootstrap micro: [-10.566, -3.210] W.
- IC95% cluster por data micro: [-16.178, -0.230] W.
- Diferença pontual macro: **11.275 W**.
- IC95% job bootstrap macro: [7.066, 15.855] W.
- IC95% cluster por data macro: [-3.639, 36.177] W.


## Horizonte 40 s

EWMA α congelado: 0.50.
### EWMA vs MA3

- Jobs: 10,222; datas de início: 11.
- Diferença pontual micro (MAE MA3 − EWMA): **2.956 W**.
- IC95% job bootstrap micro: [2.316, 3.680] W.
- IC95% cluster por data micro: [2.189, 3.856] W.
- Diferença pontual macro: **4.399 W**.
- IC95% job bootstrap macro: [3.361, 5.535] W.
- IC95% cluster por data macro: [1.366, 7.504] W.

### EWMA vs MA5

- Jobs: 10,222; datas de início: 11.
- Diferença pontual micro (MAE MA5 − EWMA): **2.314 W**.
- IC95% job bootstrap micro: [0.463, 4.909] W.
- IC95% cluster por data micro: [0.643, 3.984] W.
- Diferença pontual macro: **14.092 W**.
- IC95% job bootstrap macro: [11.007, 17.502] W.
- IC95% cluster por data macro: [1.288, 32.982] W.


## Horizonte 60 s

EWMA α congelado: 0.30.
### EWMA vs MA3

- Jobs: 10,185; datas de início: 11.
- Diferença pontual micro (MAE MA3 − EWMA): **3.568 W**.
- IC95% job bootstrap micro: [0.984, 5.479] W.
- IC95% cluster por data micro: [0.921, 6.098] W.
- Diferença pontual macro: **0.158 W**.
- IC95% job bootstrap macro: [-1.969, 2.161] W.
- IC95% cluster por data macro: [-8.285, 6.837] W.

### EWMA vs MA5

- Jobs: 10,185; datas de início: 11.
- Diferença pontual micro (MAE MA5 − EWMA): **1.597 W**.
- IC95% job bootstrap micro: [1.101, 2.018] W.
- IC95% cluster por data micro: [1.023, 2.172] W.
- Diferença pontual macro: **8.770 W**.
- IC95% job bootstrap macro: [7.205, 10.493] W.
- IC95% cluster por data macro: [1.034, 19.156] W.


## Horizonte 120 s

EWMA α congelado: 0.30.
### EWMA vs MA3

- Jobs: 9,844; datas de início: 11.
- Diferença pontual micro (MAE MA3 − EWMA): **4.553 W**.
- IC95% job bootstrap micro: [2.224, 6.250] W.
- IC95% cluster por data micro: [1.987, 7.184] W.
- Diferença pontual macro: **3.259 W**.
- IC95% job bootstrap macro: [-0.321, 6.754] W.
- IC95% cluster por data macro: [-4.080, 10.183] W.

### EWMA vs MA5

- Jobs: 9,844; datas de início: 11.
- Diferença pontual micro (MAE MA5 − EWMA): **1.754 W**.
- IC95% job bootstrap micro: [1.341, 2.129] W.
- IC95% cluster por data micro: [0.898, 2.586] W.
- Diferença pontual macro: **11.033 W**.
- IC95% job bootstrap macro: [8.856, 13.332] W.
- IC95% cluster por data macro: [0.682, 24.758] W.


## Interpretação e limites

- Intervalos que incluem zero não sustentam diferença clara entre os modelos no nível de confiança nominal de 95%.
- O bootstrap por job não preserva dependência temporal/calendária entre jobs; o cluster bootstrap por data tenta preservar choques compartilhados dentro de cada data, mas há poucos clusters.
- O intervalo por data não equivale a validação em novos períodos: o holdout cobre somente 11 datas de início.
- A análise compara apenas previsões de teste dos parâmetros V2 já congelados; não seleciona novos modelos.
- O alvo continua sendo potência agregada dos nós por job, não potência GPU individual.
