# PM100 — combinação de detectores por janelas (V1)

**Status:** comparação exploratória; estatística combinada e limiar calibrados exclusivamente na validação.

## Pergunta e protocolo

A combinação de alterações na média e na dispersão pode melhorar a sensibilidade sem simplesmente duplicar a taxa nominal de alertas?

Foram mantidos os horizontes, janelas e erros EWMA da fase anterior. Os detectores isolados usam os respectivos percentis 95 dos máximos por job na validação. Para o combinado, em cada instante calculamos max(média / limiar individual da média, variância / limiar individual da variância); o limiar final é o percentil 95 dos máximos desse escore por job na validação. Assim, os três métodos têm a mesma meta nominal de excedência por job na validação, não uma soma de dois limiares de 5%.

Os quartis de duração, os limiares e os parâmetros EWMA são definidos na validação e congelados antes do teste. Os três métodos usam os mesmos jobs e as mesmas perturbações sintéticas. O teste não é usado para selecionar um vencedor.

Jobs vistos: validação 17,998; teste 10,278. Amostra sintética: até 250 jobs por quartil e horizonte; cenários: 25.

## Alertas naturais no teste

Cada valor é a fração de jobs com ao menos um alerta, não uma taxa de falsos positivos. Os resultados são exibidos por quartil de duração.

### Horizonte 20 s — janela de 10 amostras

| Método | Q1 | Q2 | Q3 | Q4 |
|---|---:|---:|---:|---:|
| mean | 5.9% | 7.1% | 4.3% | 6.0% |
| variance | 2.5% | 3.1% | 3.8% | 4.5% |
| combined | 3.7% | 6.4% | 4.5% | 5.3% |

### Horizonte 40 s — janela de 10 amostras

| Método | Q1 | Q2 | Q3 | Q4 |
|---|---:|---:|---:|---:|
| mean | 4.0% | 3.0% | 4.0% | 3.3% |
| variance | 2.0% | 3.4% | 4.2% | 5.0% |
| combined | 3.0% | 3.1% | 3.9% | 4.4% |

### Horizonte 60 s — janela de 10 amostras

| Método | Q1 | Q2 | Q3 | Q4 |
|---|---:|---:|---:|---:|
| mean | 3.1% | 1.8% | 3.2% | 2.4% |
| variance | 2.8% | 4.2% | 5.2% | 5.0% |
| combined | 2.7% | 2.8% | 4.0% | 4.4% |

### Horizonte 120 s — janela de 10 amostras

| Método | Q1 | Q2 | Q3 | Q4 |
|---|---:|---:|---:|---:|
| mean | 3.4% | 2.3% | 3.5% | 5.4% |
| variance | 2.5% | 4.7% | 5.2% | 5.4% |
| combined | 3.2% | 3.6% | 4.0% | 6.6% |

## Mudanças sintéticas — janela de 10 amostras

Detecção após a mudança / pré-alerta antes dela. Os intervalos de Wilson e atrasos estão no JSON.

A designação sd_x2 significa multiplicar os desvios em torno da média anterior por 2; antes do truncamento em zero, isso equivale a multiplicar a variância por 4, não por 2.

### Horizonte 20 s

| Cenário | Média | Variância | Combinado |
|---|---:|---:|---:|
| step_up_s2_cp50 | 25.3% / 2.8% (n=1000) | 1.7% / 0.8% (n=1000) | 17.6% / 2.5% (n=1000) |
| step_down_s2_cp50 | 3.7% / 2.8% (n=1000) | 26.8% / 0.8% (n=1000) | 17.8% / 2.5% (n=1000) |
| ramp_up_s2_cp50 | 15.7% / 2.8% (n=1000) | 1.6% / 0.8% (n=1000) | 12.7% / 2.5% (n=1000) |
| ramp_down_s2_cp50 | 2.4% / 2.8% (n=1000) | 23.5% / 0.8% (n=1000) | 15.2% / 2.5% (n=1000) |
| sd_x2_cp50 | 2.3% / 2.8% (n=1000) | 25.1% / 0.8% (n=1000) | 18.6% / 2.5% (n=1000) |

### Horizonte 40 s

| Cenário | Média | Variância | Combinado |
|---|---:|---:|---:|
| step_up_s2_cp50 | 14.5% / 1.5% (n=1000) | 1.1% / 1.8% (n=1000) | 11.1% / 1.3% (n=1000) |
| step_down_s2_cp50 | 1.9% / 1.5% (n=1000) | 25.6% / 1.8% (n=1000) | 17.6% / 1.3% (n=1000) |
| ramp_up_s2_cp50 | 10.6% / 1.5% (n=1000) | 1.0% / 1.8% (n=1000) | 8.0% / 1.3% (n=1000) |
| ramp_down_s2_cp50 | 1.9% / 1.5% (n=1000) | 22.1% / 1.8% (n=1000) | 15.1% / 1.3% (n=1000) |
| sd_x2_cp50 | 1.5% / 1.5% (n=1000) | 24.0% / 1.8% (n=1000) | 19.3% / 1.3% (n=1000) |

### Horizonte 60 s

| Cenário | Média | Variância | Combinado |
|---|---:|---:|---:|
| step_up_s2_cp50 | 5.7% / 0.8% (n=1000) | 1.7% / 1.9% (n=1000) | 4.3% / 1.4% (n=1000) |
| step_down_s2_cp50 | 1.1% / 0.8% (n=1000) | 29.0% / 1.9% (n=1000) | 20.8% / 1.4% (n=1000) |
| ramp_up_s2_cp50 | 4.2% / 0.8% (n=1000) | 1.3% / 1.9% (n=1000) | 3.1% / 1.4% (n=1000) |
| ramp_down_s2_cp50 | 1.3% / 0.8% (n=1000) | 23.2% / 1.9% (n=1000) | 17.0% / 1.4% (n=1000) |
| sd_x2_cp50 | 1.8% / 0.8% (n=1000) | 24.0% / 1.9% (n=1000) | 18.3% / 1.4% (n=1000) |

### Horizonte 120 s

| Cenário | Média | Variância | Combinado |
|---|---:|---:|---:|
| step_up_s2_cp50 | 3.5% / 1.8% (n=1000) | 2.6% / 1.6% (n=1000) | 3.7% / 1.8% (n=1000) |
| step_down_s2_cp50 | 1.5% / 1.8% (n=1000) | 28.4% / 1.6% (n=1000) | 21.0% / 1.8% (n=1000) |
| ramp_up_s2_cp50 | 3.8% / 1.8% (n=1000) | 2.4% / 1.6% (n=1000) | 3.3% / 1.8% (n=1000) |
| ramp_down_s2_cp50 | 1.7% / 1.8% (n=1000) | 24.4% / 1.6% (n=1000) | 18.3% / 1.8% (n=1000) |
| sd_x2_cp50 | 2.0% / 1.8% (n=1000) | 22.8% / 1.6% (n=1000) | 18.5% / 1.8% (n=1000) |

## Síntese quantitativa

A excedência empírica na validação ficou entre 4.96% e 5.00% nos quatro horizontes, três janelas e quatro quartis, para os três métodos. Isso confirma a calibração nominal conjunta dentro da própria validação; não garante a taxa no teste.

Taxa de jobs alertados no teste, ponderada pelo número de jobs em cada quartil, para janela de 10 amostras:

| Horizonte | Média | Variância | Combinado |
|---:|---:|---:|---:|
| 20 s | 5.77% | 3.47% | 4.94% |
| 40 s | 3.57% | 3.61% | 3.58% |
| 60 s | 2.61% | 4.30% | 3.48% |
| 120 s | 3.62% | 4.37% | 4.31% |

Nos dados naturais, a fusão ficou próxima da incidência dos métodos individuais, mas a heterogeneidade por duração persiste; por exemplo, no horizonte de 120 s, o quartil mais longo teve 6,62% de alertas combinados na janela de 10 amostras.

Nos cenários sintéticos de referência, a fusão normalmente ficou abaixo do detector especializado no tipo de mudança correspondente. O quadro abaixo compara detecção combinada com o método isolado mais sensível para cada cenário; são proporções descritivas, não diferenças com intervalo de confiança pareado.

| Horizonte | Degrau positivo +2 SD: combinado / média | Degrau descendente +2 SD: combinado / variância | Escala SD ×2: combinado / variância |
|---:|---:|---:|---:|
| 20 s | 17.6% / 25.3% | 17.8% / 26.8% | 18.6% / 25.1% |
| 40 s | 11.1% / 14.5% | 17.6% / 25.6% | 19.3% / 24.0% |
| 60 s | 4.3% / 5.7% | 20.8% / 29.0% | 18.3% / 24.0% |
| 120 s | 3.7% / 3.5% | 21.0% / 28.4% | 18.5% / 22.8% |

A exceção numérica pequena foi o degrau positivo no horizonte de 120 s (3,7% combinado contra 3,5% no detector de média); sem comparação pareada de incerteza, isso não sustenta superioridade. Em geral, a fusão troca parte da sensibilidade de cada especialista por uma resposta intermediária aos diferentes tipos de alteração.

A designação sd_x2 significa desvio-padrão multiplicado por 2 (variância nominal ×4 antes do truncamento em zero). Degraus descendentes são aplicados à série de erro absoluto, não à potência física; o truncamento pode criar uma alteração de dispersão.

## Interpretação e limites

- A regra combinada é OR-like: pode sinalizar uma alteração localizada em qualquer uma das duas estatísticas. O limiar conjunto corrige a duplicação da taxa nominal na validação, mas não garante a mesma taxa no teste.
- Um aumento de detecção não basta para escolher o método: é preciso ponderar pré-alertas, atraso, incidência natural e estabilidade entre durações.
- Degraus descendentes são truncados em zero. A expansão sd_xN multiplica o desvio-padrão por N (variância nominal por N² antes do truncamento). São intervenções em erros absolutos, não medições de transições físicas.
- Sem rótulos independentes de mudanças reais, não podemos estimar precisão, recall ou falsos positivos reais. Uma única divisão cronológica não demonstra generalização temporal.
- PM100 mede potência agregada do job/nó. Nada nesta análise valida ATOCIA, ATRP-1, economia de energia ou segurança térmica.

## Artefatos

- combined_window_detectors_v1.py
- audit/combined_window_detectors_v1.json
- PM100_COMBINED_WINDOW_DETECTORS_V1.md

Os dados Parquet e os modelos anteriores não foram alterados.

**Fase encerrada; aguardar autorização antes de iniciar a próxima.**
