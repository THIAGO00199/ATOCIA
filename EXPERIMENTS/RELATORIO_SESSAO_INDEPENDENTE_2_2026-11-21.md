# ATOCIA — Sessão independente 2: pulso gráfico e recuperação

**Data:** 21/11/2026
**Equipamento:** Samsung NP550XDA-KS3BR — Intel Core i7-1165G7 / Intel Iris Xe (Tiger Lake GT2)
**Protocolo:** 30 s de telemetria, intervalo nominal de 0,5 s; baseline de 10 s, pulso gráfico leve de 8 s e recuperação de 12 s.
**Perfil observado:** power-saver. Estado AC não foi identificado pelo caminho consultado, portanto alimentação pela tomada/bateria não está confirmada.

## Integridade da sessão
- 60 amostras gravadas em CSV; 58 colunas.
- Início: 19:10:18.231 UTC; fim: 19:10:48.920 UTC.
- Pulso gráfico: 19:10:28.476–19:10:36.485 UTC.
- Coletor terminou com código 0.
- GLX disponível e renderizador Intel Iris Xe/Mesa confirmado por glxinfo -B após a sessão.
- Nenhuma alteração de governor, EPP, frequência, power cap, fan, firmware ou sysfs foi feita.
- Dados brutos: ATOCIA_PERTURBATION_RECOVERY_SESSION2_2026-11-21.csv
- Marcadores: ATOCIA_SESSION2_MARKERS_2026-11-21.txt
- Log: ATOCIA_SESSION2_COLLECTOR_2026-11-21.log

## Médias por fase

| Métrica | Baseline (n=19) | Pulso (n=16) | Recuperação (n=25) |
|---|---:|---:|---:|
| CPU total (%) | 1,042 | 4,323 | 4,149 |
| Potência package MSR (W) | 2,738 | 3,210 | 3,079 |
| Potência PSys (W) | 8,110 | 9,123 | 8,976 |
| Proxy GT não-RC6 (%) | 6,387 | 16,302 | 8,773 |
| Temperatura TCPU (°C) | 40,211 | 40,375 | 40,160 |
| Temperatura package x86 (°C) | 41,053 | 41,375 | 40,760 |

MSR e MMIO são leituras alternativas do domínio package e não devem ser somadas. PSys é outro domínio e também não deve ser somado ao package. O proxy GT não-RC6 indica atividade/residência estimada, não é uma medição direta de utilização da GPU. Não foram expostos sensores diretos de potência, temperatura ou utilização da GPU.

## Comparação qualitativa com a sessão 1

A sessão 1 também apresentou aumento do proxy GT e da potência do sistema durante a janela de renderização. Nesta segunda sessão, o proxy GT médio subiu de 6,39% para 16,30% durante o pulso e caiu para 8,77% na recuperação. A potência package média subiu de 2,74 W para 3,21 W e ficou em 3,08 W na recuperação.

O sentido da resposta durante o pulso é compatível entre as duas sessões, mas os valores absolutos diferem bastante porque a carga de fundo e as condições do equipamento não foram rigidamente controladas. Nesta sessão, o proxy e a potência também não retornaram completamente às médias de baseline dentro dos 12 segundos observados. Isso deve ser tratado como observação, não como uma constante física ou um tempo de recuperação caracterizado.

## Interpretação e limites

**Resultado exploratório positivo:** foi possível repetir a coleta e observar uma elevação temporal do proxy de atividade GT e das leituras de energia/potência do sistema na janela do pulso gráfico, seguida de redução na recuperação.

**O que ainda não foi demonstrado:** causalidade isolada da GPU; previsão de potência ou temperatura; vantagem sobre baselines; economia energética; identificação de modelo térmico; generalização para outras máquinas ou data centers.

O processo gráfico também consome CPU. As leituras de potência são do package/plataforma, não da GPU isoladamente. A temperatura medida é de sensores térmicos do sistema/CPU, não da GPU. O número de sessões ainda é muito pequeno para inferência estatística.

## Próximo passo

Executar mais sessões em ocasiões separadas, com alimentação e perfil de energia registrados, marcadores de fase automáticos e carga de fundo documentada. Depois, avaliar previsões em sessões inteiras não usadas no ajuste, comparando com persistência e médias móveis. ATOCIA ainda está na fase de instrumentação e validação exploratória.