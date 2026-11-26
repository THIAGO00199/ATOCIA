# PM100 v1 — ATOCIA
Fonte oficial: https://zenodo.org/records/8129258  
DOI: 10.5281/zenodo.8129258  
Licença: CC BY 4.0 (confirmada nos metadados da API Zenodo em 21/11/2026).  
Arquivo: job_table.parquet (105,940,147 bytes).  
MD5 esperado: 2a692d9b9dc4a6ee4bc5e3eb3d0fa6f5.

Este conjunto cobre 231.238 jobs no Marconi100 entre maio e outubro de 2020. O schema real do Parquet v1 contém `power_consumption` (lista de inteiros), além de `num_gpus_alloc`, `nodes`, `start_time`, `end_time` e metadados do job. A série registra a soma, em cada timestamp, das potências de entrada das duas PSUs de cada nó alocado ao job; o intervalo é 20 s. A unidade W é sustentada pelo mapeamento de métricas M100, que identifica `psX_input_power` em Watts.

**Não é potência isolada da GPU e não contém temperatura GPU na tabela PM100.** Usar como benchmark secundário de previsão da trajetória de potência agregada do job/nós durante a execução, não como benchmark primário per-GPU. Preservar sequências por job; não concatenar arrays de diferentes jobs. A pesquisa de 2026 sobre previsão pré-execução de potência de jobs já utiliza PM100 e F-DATA; comparar com esse antecedente se a tarefa de previsão for pré-execução.

O arquivo original deve permanecer intacto. Resultados derivados devem registrar versão do script, checksum e atribuição.

## Auditoria e benchmark da ATOCIA
- `PM100_AUDIT_REPORT_V1.md`: auditoria estrutural completa, integridade e cobertura.
- `benchmark_job_trajectory_baselines.py`: comparadores causais para previsão online intra-execução, sem concatenar jobs.
- `PM100_TRAJECTORY_BASELINE_REPORT_V1.md`: resultados micro e macro no holdout cronológico.
- `audit/trajectory_baselines_v1.json`: saída numérica integral do benchmark.
