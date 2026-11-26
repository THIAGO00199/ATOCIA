# PM100 — detectores por comparação de janelas e mudanças sintéticas (V1)

**Status:** comparação exploratória com limiares congelados na validação; intervenções sintéticas não são mudanças físicas observadas.

## Pergunta

Comparar duas janelas adjacentes do erro absoluto da EWMA consegue sinalizar alterações de nível ou dispersão com mais sensibilidade e menor atraso que os detectores cumulativos explorados antes?

## Protocolo

Foram avaliadas janelas de 5, 10 e 20 amostras (100, 200 e 400 s). A estatística de média compara a diferença entre médias adjacentes, normalizada pela variabilidade observada nas duas janelas. A estatística de variância compara o logaritmo da razão entre variâncias adjacentes. Cada limiar é o percentil 95 dos máximos por job na validação, separado por horizonte, largura, estatística e quartil de duração. Tudo foi congelado antes do teste.

No teste natural, medimos incidência de alertas por quartil. Para os testes sintéticos, foi usada uma amostra reprodutível de até 250 jobs por quartil e horizonte. Foram injetados degraus para cima/baixo, rampas graduais e expansão da escala dos desvios (SD); intensidades e posições de mudança são discriminadas no JSON. Um alerta antes do ponto injetado é contado como pré-alerta, não como detecção.

Jobs vistos: validação 17,998; teste 10,278. Amostras sintéticas por horizonte/quartil: até 250.

## Alertas naturais no teste

Percentuais por quartil de duração. São incidências de alerta, não taxas de falso positivo, pois não há rótulos independentes.

### Horizonte 20 s

| Estatística | Janela | Q1 | Q2 | Q3 | Q4 |
|---|---:|---:|---:|---:|---:|
| mean | 5 (100s) | 5.9% | 6.8% | 3.9% | 4.4% |
| variance | 5 (100s) | 3.4% | 3.9% | 4.9% | 7.5% |
| mean | 10 (200s) | 5.9% | 7.1% | 4.3% | 6.0% |
| variance | 10 (200s) | 2.5% | 3.1% | 3.8% | 4.5% |
| mean | 20 (400s) | 5.8% | 6.3% | 3.9% | 6.4% |
| variance | 20 (400s) | 2.7% | 2.5% | 3.9% | 4.9% |

### Horizonte 40 s

| Estatística | Janela | Q1 | Q2 | Q3 | Q4 |
|---|---:|---:|---:|---:|---:|
| mean | 5 (100s) | 4.3% | 3.8% | 4.0% | 7.5% |
| variance | 5 (100s) | 3.9% | 4.3% | 3.4% | 5.8% |
| mean | 10 (200s) | 4.0% | 3.0% | 4.0% | 3.3% |
| variance | 10 (200s) | 2.0% | 3.4% | 4.2% | 5.0% |
| mean | 20 (400s) | 4.7% | 3.7% | 4.6% | 5.2% |
| variance | 20 (400s) | 2.7% | 3.4% | 5.0% | 4.7% |

### Horizonte 60 s

| Estatística | Janela | Q1 | Q2 | Q3 | Q4 |
|---|---:|---:|---:|---:|---:|
| mean | 5 (100s) | 3.4% | 3.2% | 4.5% | 6.9% |
| variance | 5 (100s) | 2.6% | 3.7% | 4.1% | 6.3% |
| mean | 10 (200s) | 3.1% | 1.8% | 3.2% | 2.4% |
| variance | 10 (200s) | 2.8% | 4.2% | 5.2% | 5.0% |
| mean | 20 (400s) | 3.3% | 2.9% | 4.4% | 4.3% |
| variance | 20 (400s) | 3.0% | 4.0% | 5.4% | 5.2% |

### Horizonte 120 s

| Estatística | Janela | Q1 | Q2 | Q3 | Q4 |
|---|---:|---:|---:|---:|---:|
| mean | 5 (100s) | 1.3% | 3.8% | 2.8% | 4.6% |
| variance | 5 (100s) | 2.2% | 4.0% | 4.2% | 5.3% |
| mean | 10 (200s) | 3.4% | 2.3% | 3.5% | 5.4% |
| variance | 10 (200s) | 2.5% | 4.7% | 5.2% | 5.4% |
| mean | 20 (400s) | 3.5% | 3.5% | 5.9% | 6.7% |
| variance | 20 (400s) | 3.3% | 4.3% | 5.1% | 5.2% |

## Testes sintéticos no ponto médio

Cada célula mostra detecção após a mudança / pré-alerta antes dela. O JSON contém ICs de Wilson de 95%, medianas de atraso, resultados por quartil e cenários nas posições 25%, 50% e 75%.

Na janela de 20 amostras, a amostra efetiva cai para n=842–846 porque são necessários ao menos 80 erros para posicionar duas janelas completas antes e depois da mudança. Nas janelas de 5 e 10 amostras, n=1.000. O teto de 250 por quartil não garante 250 casos elegíveis em todas as configurações.

### Horizonte 20 s

| Estatística | Janela | Degrau +2σ | Degrau −2σ | Rampa +2σ | Rampa −2σ | Escala SD ×2 (variância ×4*) |
|---|---:|---:|---:|---:|---:|---:|
| mean | 5 (100s) | 4.7% / 3.3% (n=1000) | 1.0% / 3.3% (n=1000) | 4.4% / 3.3% (n=1000) | 1.7% / 3.3% (n=1000) | 3.6% / 3.3% (n=1000) |
| variance | 5 (100s) | 2.6% / 2.1% (n=1000) | 24.2% / 2.1% (n=1000) | 2.5% / 2.1% (n=1000) | 21.2% / 2.1% (n=1000) | 29.4% / 2.1% (n=1000) |
| mean | 10 (200s) | 25.3% / 2.8% (n=1000) | 3.7% / 2.8% (n=1000) | 15.7% / 2.8% (n=1000) | 2.4% / 2.8% (n=1000) | 2.3% / 2.8% (n=1000) |
| variance | 10 (200s) | 1.7% / 0.8% (n=1000) | 26.8% / 0.8% (n=1000) | 1.6% / 0.8% (n=1000) | 23.5% / 0.8% (n=1000) | 25.1% / 0.8% (n=1000) |
| mean | 20 (400s) | 51.4% / 2.6% (n=842) | 10.3% / 2.6% (n=842) | 24.7% / 2.6% (n=842) | 4.2% / 2.6% (n=842) | 1.9% / 2.6% (n=842) |
| variance | 20 (400s) | 1.7% / 1.3% (n=842) | 29.7% / 1.3% (n=842) | 1.7% / 1.3% (n=842) | 23.4% / 1.3% (n=842) | 24.2% / 1.3% (n=842) |

### Horizonte 40 s

| Estatística | Janela | Degrau +2σ | Degrau −2σ | Rampa +2σ | Rampa −2σ | Escala SD ×2 (variância ×4*) |
|---|---:|---:|---:|---:|---:|---:|
| mean | 5 (100s) | 3.7% / 2.4% (n=1000) | 0.9% / 2.4% (n=1000) | 3.5% / 2.4% (n=1000) | 1.5% / 2.4% (n=1000) | 1.9% / 2.4% (n=1000) |
| variance | 5 (100s) | 1.1% / 1.8% (n=1000) | 24.5% / 1.8% (n=1000) | 1.2% / 1.8% (n=1000) | 21.8% / 1.8% (n=1000) | 29.0% / 1.8% (n=1000) |
| mean | 10 (200s) | 14.5% / 1.5% (n=1000) | 1.9% / 1.5% (n=1000) | 10.6% / 1.5% (n=1000) | 1.9% / 1.5% (n=1000) | 1.5% / 1.5% (n=1000) |
| variance | 10 (200s) | 1.1% / 1.8% (n=1000) | 25.6% / 1.8% (n=1000) | 1.0% / 1.8% (n=1000) | 22.1% / 1.8% (n=1000) | 24.0% / 1.8% (n=1000) |
| mean | 20 (400s) | 38.9% / 2.0% (n=845) | 6.7% / 2.0% (n=845) | 16.8% / 2.0% (n=845) | 2.0% / 2.0% (n=845) | 1.5% / 2.0% (n=845) |
| variance | 20 (400s) | 2.1% / 1.4% (n=845) | 26.6% / 1.4% (n=845) | 1.8% / 1.4% (n=845) | 22.7% / 1.4% (n=845) | 23.1% / 1.4% (n=845) |

### Horizonte 60 s

| Estatística | Janela | Degrau +2σ | Degrau −2σ | Rampa +2σ | Rampa −2σ | Escala SD ×2 (variância ×4*) |
|---|---:|---:|---:|---:|---:|---:|
| mean | 5 (100s) | 3.1% / 1.5% (n=1000) | 1.6% / 1.5% (n=1000) | 3.0% / 1.5% (n=1000) | 2.3% / 1.5% (n=1000) | 2.5% / 1.5% (n=1000) |
| variance | 5 (100s) | 2.4% / 2.2% (n=1000) | 23.3% / 2.2% (n=1000) | 2.4% / 2.2% (n=1000) | 19.5% / 2.2% (n=1000) | 26.0% / 2.2% (n=1000) |
| mean | 10 (200s) | 5.7% / 0.8% (n=1000) | 1.1% / 0.8% (n=1000) | 4.2% / 0.8% (n=1000) | 1.3% / 0.8% (n=1000) | 1.8% / 0.8% (n=1000) |
| variance | 10 (200s) | 1.7% / 1.9% (n=1000) | 29.0% / 1.9% (n=1000) | 1.3% / 1.9% (n=1000) | 23.2% / 1.9% (n=1000) | 24.0% / 1.9% (n=1000) |
| mean | 20 (400s) | 22.1% / 1.8% (n=846) | 3.7% / 1.8% (n=846) | 13.5% / 1.8% (n=846) | 2.0% / 1.8% (n=846) | 1.7% / 1.8% (n=846) |
| variance | 20 (400s) | 3.2% / 1.5% (n=846) | 27.2% / 1.5% (n=846) | 3.0% / 1.5% (n=846) | 24.2% / 1.5% (n=846) | 25.7% / 1.5% (n=846) |

### Horizonte 120 s

| Estatística | Janela | Degrau +2σ | Degrau −2σ | Rampa +2σ | Rampa −2σ | Escala SD ×2 (variância ×4*) |
|---|---:|---:|---:|---:|---:|---:|
| mean | 5 (100s) | 2.2% / 0.9% (n=1000) | 2.9% / 0.9% (n=1000) | 1.9% / 0.9% (n=1000) | 3.1% / 0.9% (n=1000) | 2.8% / 0.9% (n=1000) |
| variance | 5 (100s) | 2.2% / 2.0% (n=1000) | 22.7% / 2.0% (n=1000) | 2.2% / 2.0% (n=1000) | 18.8% / 2.0% (n=1000) | 24.4% / 2.0% (n=1000) |
| mean | 10 (200s) | 3.5% / 1.8% (n=1000) | 1.5% / 1.8% (n=1000) | 3.8% / 1.8% (n=1000) | 1.7% / 1.8% (n=1000) | 2.0% / 1.8% (n=1000) |
| variance | 10 (200s) | 2.6% / 1.6% (n=1000) | 28.4% / 1.6% (n=1000) | 2.4% / 1.6% (n=1000) | 24.4% / 1.6% (n=1000) | 22.8% / 1.6% (n=1000) |
| mean | 20 (400s) | 9.9% / 1.9% (n=846) | 2.7% / 1.9% (n=846) | 10.8% / 1.9% (n=846) | 3.1% / 1.9% (n=846) | 3.0% / 1.9% (n=846) |
| variance | 20 (400s) | 3.7% / 2.1% (n=846) | 27.2% / 2.1% (n=846) | 2.5% / 2.1% (n=846) | 23.0% / 2.1% (n=846) | 23.9% / 2.1% (n=846) |

## Leitura e limites

- Comparações de janelas detectam mudanças locais; a janela mais longa tende a exigir mais observações após a mudança, enquanto a janela curta pode responder mais rápido e oscilar mais.
- A calibração por quartil reduz uma fonte conhecida de heterogeneidade, mas as taxas de alerta no teste devem ser lidas diretamente; não se presume que permaneçam em 5%.
- O teste sintético avalia somente a mecânica dos detectores sobre erros absolutos observados. Não comprova que os mesmos padrões ocorram no consumo de energia real nem que alertas naturais indiquem mudanças verdadeiras.
- Degraus descendentes são truncados em zero; expansões de variância também são centradas na janela anterior e truncadas em zero. Essas perturbações não reproduzem perfeitamente processos físicos.
- Não foi escolhido um vencedor com base no teste. Uma escolha operacional exigiria critérios prévios, rótulos independentes e validação temporal em períodos adicionais.
- PM100 mede potência agregada por job/nó, não potência exclusivamente da GPU. Nada nesta fase valida ATOCIA ou ATRP-1.

## Artefatos

- window_comparison_synthetic_v1.py
- audit/window_comparison_synthetic_v1.json
- PM100_WINDOW_COMPARISON_SYNTHETIC_V1.md

O Parquet original, resultados V2, ATRP-1 e relatórios anteriores não foram alterados.

**Fase encerrada; aguardar autorização antes da próxima.**
