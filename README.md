# ATOCIA — inteligência temporal para infraestrutura computacional

Pesquisa e desenvolvimento de métodos para observar, modelar e antecipar variações de potência e dinâmica térmica em sistemas computacionais, com foco de longo prazo em GPUs, clusters de IA e HPC.

**Estado:** laboratório de pesquisa e protótipos experimentais. Não é um controlador de data center nem um sistema pronto para produção.

## Duas frentes técnicas relacionadas, mas distintas

### 1. ATRP-1 — previsão de potência GPU

Foi implementado e avaliado um primeiro modelo preditivo leve para estimar a potência da GPU 15 segundos à frente, usando telemetria histórica de potência, temperatura e utilização.

- Huber Ridge com correção residual sobre persistência.
- 13 atributos causais derivados de três amostras anteriores.
- Modelo treinado em janelas do cluster Kalos, com hiperparâmetro selecionado somente na validação.
- Artefato congelado e verificado por hash antes das avaliações.

**Resultados registrados para o mesmo modelo congelado:**

| Avaliação | Redução de MAE vs. persistência | Redução de RMSE |
|---|---:|---:|
| Kalos, holdout temporal 30/08 | 23,54% | 29,53% |
| Kalos, holdout temporal 31/08 | 20,92% | 27,41% |
| Seren, transferência zero-shot | 0,88% | 13,75% |

Os dois holdouts temporais de Kalos mantiveram melhora positiva de MAE na reanálise que considera dependência temporal e por host. Em Seren, a melhora de MAE é pequena e os intervalos de confiança atravessam zero: não há evidência convincente de ganho nessa métrica entre clusters. A redução de RMSE é uma observação separada, não substitui essa conclusão.

**Interpretação:** há um sinal promissor de previsão temporal dentro de Kalos; a transferência entre clusters continua sendo o principal desafio. Os resultados não demonstram generalização para outras arquiteturas, economia de energia, redução de custo, segurança térmica ou prontidão operacional.

### 2. Física térmica e instrumentação local

- Coletores passivos de telemetria Linux para potência disponível, temperatura, frequência e estado do sistema.
- Baseline térmica RC convencional e testes matemáticos offline.
- Ensaios repetidos de carga e recuperação em um único notebook Intel.
- 38 testes offline aprovados na suíte local verificada em 25/11/2026.

Os ensaios locais mostram uma resposta qualitativa repetível de potência de package e temperatura a pulsos curtos de CPU. Ainda não identificam de forma robusta os parâmetros térmicos reais: temperatura ambiente, ventilação e outras variáveis não estão suficientemente observadas. Essa trilha não valida comportamento de GPU em rack ou data center.

### 3. Benchmarks externos exploratórios

A pesquisa também contém análises de telemetria agregada por job e detecção de mudanças de potência. Na análise PM100 V2, as intervenções são sintéticas: a detecção incremental é modesta para mudanças apenas de média e mais evidente em alguns cenários de dispersão/variância e mudanças mistas. As taxas absolutas permanecem baixas nos cenários estudados. Não há rótulos de mudança física real nem evidência de adequação operacional.

## Relação com a TDT

A Teoria do Débito Temporal é uma hipótese de pesquisa relacionada à motivação conceitual do projeto. A ligação matemática entre a TDT e os modelos térmicos ou preditivos ainda não foi estabelecida. Os modelos RC e ATRP-1 devem ser avaliados pelas próprias hipóteses, baselines e métricas, sem atribuir seus resultados à TDT.

## Arquitetura de validação

1. Instrumentação observacional e auditoria de qualidade dos sinais.
2. Baselines simples e modelos físicos reduzidos.
3. Previsão com avaliação temporal e comparação contra persistência.
4. Testes de transferência, sensores ausentes, cadência irregular e regimes não vistos.
5. Simulação e modo sombra antes de qualquer recomendação operacional.

Não há controle de hardware habilitado. Os coletores locais são observacionais e não alteram limites de potência, frequência, governor, EPP, ventoinhas, firmware ou serviços.

## Documentos para começar

- `RESEARCH_EXTERNAL/ATRP1_EXECUTIVE_SUMMARY_2026-11-22.md` — pergunta experimental, modelo e resultados.
- `RESEARCH_EXTERNAL/ATRP1_DEPENDENCE_AWARE_REANALYSIS_2026-11-22.md` — intervalos considerando dependência temporal e por host.
- `MODEL_V1/ATRP1_SPEC.md` — especificação do modelo.
- `MODEL_V1/EXPERIMENT_PROTOCOL_V1.md` — protocolo de avaliação e prevenção de vazamento.
- `THERMAL_PHYSICS_BASELINE_V1.md` — baseline física local e hipóteses.
- `RESEARCH_EXTERNAL/PM100/PM100_RAW_POWER_CHANGE_DETECTION_V2.md` — benchmark de detecção com intervenções sintéticas.

## Dados, reprodução e atribuição

Os benchmarks externos usam dados publicados por terceiros. Os painéis derivados, arquivos brutos e conjuntos completos não devem ser redistribuídos automaticamente. Antes de qualquer publicação, preserve a atribuição, os termos de licença e a proveniência de cada conjunto. Scripts, resultados derivados e dados originais devem ser tratados separadamente.

Os holdouts já observados não devem ser reutilizados como testes intocados para selecionar variantes futuras. Novas versões precisam de divisões de treino/validação e holdout independentes.

---

[English](README.en.md) · [Español](README.es.md)

## Public repository data policy

Raw local telemetry captures, collector logs, complete third-party datasets, and source metadata dumps are intentionally not included in this public repository. See DATA_PROVENANCE.md for dataset attribution and redistribution notes.
