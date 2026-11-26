# ATOCIA — Baseline físico térmico RC de um nó (v1)

**Status:** implementação inicial e testada matematicamente; ainda não ajustada nem validada contra telemetria real.

## Modelo

A primeira baseline é um sistema térmico concentrado de um nó:

\[
C_{th}\frac{dT}{dt}=P(t)-\frac{T(t)-T_a(t)}{R_{th}}
\]

- \(T\): temperatura do nó térmico (°C; diferenças em K).
- \(T_a\): temperatura ambiente/fluido de referência (°C).
- \(P\): potência térmica efetivamente injetada no nó (W), hipótese que precisa ser definida por equipamento.
- \(R_{th}\): resistência térmica equivalente (K/W).
- \(C_{th}\): capacitância térmica equivalente (J/K).
- \(\tau=R_{th}C_{th}\): constante de tempo (s).

Com potência e ambiente constantes durante um intervalo \(\Delta t\), usamos a solução analítica exata:

\[
T_{k+1}=T_{eq}+(T_k-T_{eq})e^{-\Delta t/\tau},\quad
T_{eq}=T_{a,k}+R_{th}P_k.
\]

Isso evita instabilidade de integração explícita para passos grandes. O código está em `thermal_physics.py`.

## Interpretação correta

A previsão é condicional: presume que potência e ambiente futuros permaneçam constantes no horizonte. Ela **não** prevê o workload futuro e não é ainda uma previsão ATOCIA validada. O modelo de um nó é uma baseline simples; racks, chips, cold plates, chassis, ar, líquido e facility podem exigir redes RC multi-nó ou modelos distribuídos.

## O que não foi inferido

Os experimentos locais atuais não medem temperatura ambiente, resistência/capacitância independentes, RPM da ventoinha nem fluxo térmico. Portanto, não ajustamos \(R_{th}\) e \(C_{th}\) a partir dos dados do notebook e não alegamos identificação física. Parâmetros de exemplo em testes são sintéticos.

## Próxima validação

1. Obter uma série sincronizada com tempo monotônico, temperatura do equipamento, potência e temperatura do ar de entrada.
2. Definir se a potência medida corresponde à potência dissipada no nó modelado; contabilizar limites e perdas.
3. Estimar parâmetros somente com excitação suficiente e intervalos de confiança; verificar identificabilidade e correlação entre parâmetros.
4. Comparar contra persistência, EMA e regressão simples em sessões inteiras não vistas.
5. Reportar MAE/RMSE, erro de pico, cobertura de intervalos e desempenho por regime.
6. Manter saída em modo sombra; nenhum controle de ventoinha, potência, frequência ou cooling nesta fase.

## Segurança e reprodutibilidade

Este módulo é offline e não lê nem escreve interfaces do sistema. Os testes usam valores sintéticos e não iniciam carga computacional. Nenhuma configuração do Garuda é alterada.
