# ATOCIA — Sessão 3 e benchmark de baselines temporais

**Data:** 21/11/2026
**Equipamento:** Samsung NP550XDA-KS3BR — i7-1165G7 / Iris Xe TGL GT2
**Protocolo:** 30 s; 0,5 s nominal; baseline 10 s, pulso gráfico 8 s, recuperação 12 s.
**Perfil:** power-saver. **AC online:** 1 (conectado).

## 1. Integridade e repetição

- Sessão 3: 60 amostras, 58 colunas, coletor finalizado com código 0.
- Início UTC: 19:12:39.950; fim UTC: 19:13:10.623.
- Pulso gráfico UTC: 19:12:50.182–19:12:58.190.
- Renderizador confirmado: Mesa Intel Iris Xe (TGL GT2).
- Nenhuma configuração de hardware, energia, frequência, ventilação ou sysfs foi alterada.
- CSV: ATOCIA_PERTURBATION_RECOVERY_SESSION3_2026-11-21.csv
- Marcadores: ATOCIA_SESSION3_MARKERS_2026-11-21.txt
- Log: ATOCIA_SESSION3_COLLECTOR_2026-11-21.log

## 2. Resultado por fase — sessão 3

| Métrica | Baseline (n=19) | Pulso (n=16) | Recuperação (n=25) |
|---|---:|---:|---:|
| CPU total (%) | 1,053 | 4,708 | 2,342 |
| Package MSR (W) | 2,685 | 3,429 | 2,855 |
| PSys (W) | 9,165 | 9,473 | 8,316 |
| Proxy GT não-RC6 (%) | 6,808 | 18,354 | 7,455 |
| TCPU (°C) | 37,579 | 38,000 | 37,880 |
| Package x86 (°C) | 38,842 | 39,125 | 39,080 |

Na sessão 3, o proxy GT aumentou durante o pulso e retornou próximo da média inicial na recuperação. A potência package também subiu no pulso e recuou na recuperação. A temperatura variou pouco, como esperado para uma janela curta e um estímulo leve.

## 3. Comparação entre as três sessões

| Sessão | Proxy GT baseline | Proxy GT pulso | Proxy GT recuperação | Package MSR baseline | Package MSR pulso | Package MSR recuperação |
|---|---:|---:|---:|---:|---:|---:|
| S1 | 37,52% | 58,41% | 34,23% | 6,95 W | 7,92 W | 6,82 W |
| S2 | 6,39% | 16,30% | 8,77% | 2,74 W | 3,21 W | 3,08 W |
| S3 | 6,81% | 18,35% | 7,46% | 2,69 W | 3,43 W | 2,86 W |

S2 e S3 mostram resposta qualitativamente semelhante sob condições mais próximas: aumento do proxy GT durante o pulso e redução na recuperação. S1 começou com carga de fundo muito maior, logo suas magnitudes não são diretamente comparáveis. S2 e S3 ocorreram na mesma tarde, no mesmo equipamento e com poucos minutos entre elas; são repetições separadas, mas ainda não representam independência entre dias, máquinas ou ambientes.

## 4. Benchmark de previsão: baselines convencionais

Foi implementada uma avaliação causal simples, sem olhar para o futuro na construção da previsão. Para cada instante, foram comparados:
- Persistência: previsão igual à última observação.
- Média móvel de 3 amostras (aprox. 1,5 s).
- Média móvel de 5 amostras (aprox. 2,5 s).
- Média móvel de 10 amostras (aprox. 5 s).

Horizontes avaliados: 0,5 s, 1 s, 2 s e 5 s. Métricas: MAE e RMSE. Cada sessão foi avaliada separadamente; S3 foi tratada como sessão de avaliação reservada para comparação dos baselines.

### Resultados da sessão 3 reservada

| Alvo | Horizonte | Persistência MAE | Melhor média móvel MAE | Melhor janela |
|---|---:|---:|---:|---:|
| Package MSR (W) | 0,5 s | 0,827 | 0,492 | 3 amostras |
| Package MSR (W) | 1 s | 0,854 | 0,490 | 5 amostras |
| Package MSR (W) | 2 s | 0,850 | 0,543 | 3 amostras |
| Package MSR (W) | 5 s | 0,883 | 0,630 | 3 amostras |
| PSys (W) | 0,5 s | 2,444 | 1,427 | 3 amostras |
| PSys (W) | 1 s | 2,473 | 1,421 | 5 amostras |
| PSys (W) | 2 s | 2,473 | 1,548 | 3 amostras |
| PSys (W) | 5 s | 2,466 | 1,621 | 10 amostras |
| Proxy GT (%) | 0,5 s | 15,574 | 9,903 | 3 amostras |
| Proxy GT (%) | 1 s | 15,546 | 9,626 | 5 amostras |
| Proxy GT (%) | 2 s | 15,903 | 10,438 | 3 amostras |
| Proxy GT (%) | 5 s | 16,168 | 11,518 | 3 amostras |

Em S3, as médias móveis reduziram o MAE em relação à persistência para package, PSys e proxy GT nos quatro horizontes testados. Isso é uma referência inicial importante: qualquer método ATOCIA precisa superar essas referências em dados reservados, sem vazamento temporal.

## 5. Limitações importantes

- Nenhum modelo preditivo próprio da ATOCIA foi avaliado neste benchmark. O resultado não demonstra vantagem da ATOCIA.
- As médias móveis são filtros simples e podem atrasar mudanças abruptas; a comparação ainda é exploratória.
- O benchmark usa séries curtas, de um único equipamento, com estímulo gráfico leve e controlado apenas por duração.
- O proxy GT não-RC6 não é utilização direta da GPU; potência package e PSys não são potência isolada da GPU; temperaturas são sensores do sistema/CPU.
- A coleta tem 60 amostras por sessão e as sessões S2/S3 foram feitas próximas no tempo. Não há base para significância estatística ou generalização.
- A janela de previsão foi inferida por passos amostrais nominais de 0,5 s; pequenas variações de temporização existem.

## 6. Próxima etapa científica

1. Repetir em dias diferentes e registrar AC/bateria, perfil, temperatura ambiente aproximada e processos de fundo.
2. Coletar séries mais longas e estímulos com perfis variados, sem confundir proxy GT com potência GPU.
3. Definir alvos observáveis e horizontes antes de ajustar qualquer modelo.
4. Fazer divisão treino/validação/teste por sessão ou dia completo, nunca por linhas aleatórias da mesma série.
5. Comparar a hipótese/modelo ATOCIA contra persistência, médias móveis e pelo menos um modelo convencional simples, reportando MAE, RMSE e intervalos de incerteza.

**Conclusão:** três execuções curtas mostram um padrão exploratório repetível de resposta do proxy GT ao pulso gráfico, especialmente entre S2 e S3. O benchmark demonstra que médias móveis já são referências fortes neste conjunto pequeno. O próximo avanço não é alegar previsão, mas construir e testar um modelo próprio contra essas referências em sessões realmente reservadas.