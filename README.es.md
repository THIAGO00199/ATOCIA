# ATOCIA — inteligencia temporal para infraestructura informática

Investigación y desarrollo de métodos para observar, modelar y anticipar variaciones de potencia y dinámica térmica en sistemas informáticos, con enfoque a largo plazo en GPU, clústeres de IA y HPC.

**Estado:** laboratorio de investigación y prototipos experimentales. No es un controlador de centro de datos ni un sistema listo para producción.

## Dos líneas técnicas relacionadas, pero distintas

### 1. ATRP-1 — predicción de potencia de GPU

Se implementó y evaluó un primer modelo predictivo ligero para estimar la potencia de la GPU con 15 segundos de anticipación, utilizando telemetría histórica de potencia, temperatura y utilización.

- Huber Ridge con corrección residual sobre persistencia.
- 13 atributos causales derivados de las tres muestras anteriores.
- Entrenamiento con ventanas del clúster Kalos; el hiperparámetro se seleccionó únicamente con datos de validación.
- Artefacto del modelo congelado y verificado mediante hash antes de la evaluación.

**Resultados registrados para el mismo modelo congelado:**

| Evaluación | Reducción de MAE frente a persistencia | Reducción de RMSE |
|---|---:|---:|
| Kalos, holdout temporal 30/08 | 23,54% | 29,53% |
| Kalos, holdout temporal 31/08 | 20,92% | 27,41% |
| Seren, transferencia zero-shot | 0,88% | 13,75% |

Los dos holdouts temporales de Kalos mantuvieron una mejora positiva de MAE en el análisis que considera la dependencia temporal y entre hosts. En Seren, la mejora de MAE es pequeña y los intervalos de confianza incluyen cero: no existe evidencia convincente de una mejora en esta métrica entre clústeres. La reducción de RMSE es una observación independiente y no cambia esa conclusión.

**Interpretación:** los resultados muestran una señal temporal prometedora dentro de Kalos; la transferencia entre clústeres sigue siendo el principal desafío. No demuestran generalización a otras arquitecturas, ahorro energético, reducción de costos, seguridad térmica ni preparación operativa.

### 2. Física térmica e instrumentación local

- Recolectores pasivos de telemetría Linux para potencia disponible, temperatura, frecuencia y estado del sistema.
- Una baseline térmica RC convencional y pruebas matemáticas offline.
- Observaciones repetidas de carga y recuperación en un único portátil Intel.
- 38 pruebas offline aprobadas en la suite local verificada el 25/11/2026.

Los experimentos locales muestran una respuesta cualitativa repetible de la potencia de package y la temperatura ante pulsos cortos de CPU. Todavía no identifican de forma robusta los parámetros térmicos físicos: la temperatura ambiente, el comportamiento del ventilador y otras variables no están suficientemente observados. Esta línea no valida el comportamiento de GPU en un rack o centro de datos.

### 3. Benchmarks externos exploratorios

La investigación también incluye análisis de telemetría agregada por trabajo y detección de cambios de potencia. En el análisis PM100 V2, las intervenciones son sintéticas: la detección incremental es modesta para cambios solo de media y más visible en algunos escenarios de varianza/dispersión y cambios mixtos. Las tasas absolutas siguen siendo bajas en los escenarios seleccionados. No hay etiquetas de cambios físicos reales ni evidencia de idoneidad operativa.

## Relación con la TDT

La Teoría de la Deuda Temporal (TDT) es una hipótesis de investigación relacionada con la motivación conceptual del proyecto. La conexión matemática entre la TDT y los modelos térmicos o predictivos todavía no está establecida. Los modelos RC y ATRP-1 deben evaluarse según sus propias hipótesis, baselines y métricas; sus resultados no deben atribuirse a la TDT.

## Arquitectura de validación

1. Instrumentación observacional y auditoría de calidad de las señales.
2. Baselines simples y modelos físicos de orden reducido.
3. Predicción con evaluación temporal y comparación con persistencia.
4. Pruebas de transferencia, sensores ausentes, muestreo irregular y regímenes no vistos.
5. Simulación y modo sombra antes de cualquier recomendación operativa.

No hay control de hardware habilitado. Los recolectores locales son observacionales y no modifican límites de potencia, frecuencia, governor, EPP, ventiladores, firmware ni servicios.

## Documentos para empezar

- `RESEARCH_EXTERNAL/ATRP1_EXECUTIVE_SUMMARY_2026-11-22.md` — pregunta experimental, modelo y resultados.
- `RESEARCH_EXTERNAL/ATRP1_DEPENDENCE_AWARE_REANALYSIS_2026-11-22.md` — intervalos que consideran la dependencia temporal y entre hosts.
- `MODEL_V1/ATRP1_SPEC.md` — especificación del modelo.
- `MODEL_V1/EXPERIMENT_PROTOCOL_V1.md` — protocolo de evaluación y prevención de fugas.
- `THERMAL_PHYSICS_BASELINE_V1.md` — baseline física local e hipótesis.
- `RESEARCH_EXTERNAL/PM100/PM100_RAW_POWER_CHANGE_DETECTION_V2.md` — benchmark de detección con intervenciones sintéticas.

## Datos, reproducibilidad y atribución

Los benchmarks externos utilizan conjuntos de datos publicados por terceros. Los paneles derivados, archivos brutos y conjuntos completos no deben redistribuirse automáticamente. Cualquier publicación debe conservar la atribución, los términos de licencia y la procedencia de cada conjunto. Los scripts, los resultados derivados y los datos originales deben tratarse por separado.

Los holdouts ya observados no deben reutilizarse como pruebas intactas para seleccionar futuras variantes. Las nuevas versiones necesitan divisiones independientes de entrenamiento/validación y un holdout separado.

---

[Português](README.md) · [English](README.en.md)

## Public repository data policy

Raw local telemetry captures, collector logs, complete third-party datasets, and source metadata dumps are intentionally not included in this public repository. See DATA_PROVENANCE.md for dataset attribution and redistribution notes.
