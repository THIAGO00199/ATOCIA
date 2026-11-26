# ATOCIA — Fase 1B: avaliação de previsão multi-horizonte (2026-11-20)

Objetivo: avaliar sem nova carga de CPU se sinais atuais permitem prever a temperatura do pacote em 5, 10 e 20 s. Capturas inteiras ficam fora do treino durante cada teste (leave-one-trial-out).

Capturas: pulse_1, pulse_2, pulse_3, long. Mesmo notebook, sessões curtas, sensores quantizados (~1 °C), sem temperatura ambiente nem RPM de ventoinha. Avaliação exploratória.

Features: temperatura atual, inclinação nos últimos 5 s, potência atual, médias de potência de 5 s e 30 s. Nenhuma potência futura é usada.

| Horizonte | Persistência MAE/RMSE | Tendência MAE/RMSE | Ridge MAE/RMSE |
|---:|---:|---:|---:|
| 5s | 0.85/1.30 °C | 1.47/2.04 °C | 0.83/1.07 °C |
Detalhe: pulse_1: n=70, ridge MAE=0.91, RMSE=1.08°C; pulse_2: n=70, ridge MAE=0.90, RMSE=1.25°C; pulse_3: n=70, ridge MAE=0.85, RMSE=1.12°C; long: n=125, ridge MAE=0.72, RMSE=0.92°C
| 10s | 1.12/1.64 °C | 2.55/3.43 °C | 1.00/1.27 °C |
Detalhe: pulse_1: n=65, ridge MAE=1.07, RMSE=1.27°C; pulse_2: n=65, ridge MAE=0.99, RMSE=1.31°C; pulse_3: n=65, ridge MAE=1.01, RMSE=1.28°C; long: n=120, ridge MAE=0.96, RMSE=1.24°C
| 20s | 1.69/2.19 °C | 4.74/6.39 °C | 1.33/1.62 °C |
Detalhe: pulse_1: n=55, ridge MAE=1.14, RMSE=1.32°C; pulse_2: n=55, ridge MAE=1.04, RMSE=1.43°C; pulse_3: n=55, ridge MAE=1.20, RMSE=1.41°C; long: n=110, ridge MAE=1.64, RMSE=1.92°C

Interpretação:
- 5s: menor RMSE agregado = ridge (1.07 °C).
- 10s: menor RMSE agregado = ridge (1.27 °C).
- 20s: menor RMSE agregado = ridge (1.62 °C).
- Tendência pode extrapolar ruído/quantização; regressão pode aprender correlações específicas dos pulsos. Agregado não substitui validação em máquinas/sessões novas.
- Produto deve diferenciar previsão sob carga atual constante de previsão que também antecipa a carga futura.

Decisão: motor em modo sombra, sem alterar ventoinha, frequência, governor ou limites. Antes de chamar a previsão confiável: capturas longas/variadas, ambiente, RPM se disponível, estado AC/bateria, várias máquinas, validação por sessão e calibração de incerteza.

Próxima etapa: Fase 1C — protocolo de identificação térmica com durações variadas e recuperação longa; nova carga só com autorização quando o utilizador não estiver jogando/trabalhando. Fase 2 — previsão online e comparação contínua com baselines. Fase 3 — simulação de ações. Fase 4 — controle preditivo limitado e reversível, após validação.
