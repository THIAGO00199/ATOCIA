# PM100 v1 — auditoria completa do Parquet

**Executado:** 21/11/2026  
**Método:** DuckDB 1.5.6, uma thread, limite de memória 512 MB; prioridade reduzida (nice/ionice). Nenhum treinamento executado.  
**Arquivo original preservado:** \`job_table.parquet\`.

## Integridade e schema
- Tamanho: 105.940.147 bytes.
- MD5 esperado e calculado: \`2a692d9b9dc4a6ee4bc5e3eb3d0fa6f5\` — confirmado.
- SHA-256: \`10bc1ba948cd362657e97eea9b5f96ff16d77ac6e8e0e78894d60e2074d4fd89\`.
- 231.238 registros.
- O schema real tem a coluna \`power_consumption\` como \`INTEGER[]\`; não tem \`node_power_consumption\`. O auditor foi corrigido para o schema real.
- Todos os 231.238 registros inspecionados têm sequência de potência não vazia.

## Cobertura temporal observada
- 65.173.805 valores de potência.
- 210.573 jobs têm \`num_gpus_alloc > 0\`.
- Comprimento das sequências: mínimo 1, mediana 10, média 281,85, máximo 6.255 amostras.
- 117.165 jobs têm pelo menos 10 amostras (200 s).
- 85.534 jobs têm pelo menos 30 amostras (600 s).
- 71.268 jobs têm pelo menos 60 amostras (1.200 s).
- 81.481 jobs GPU têm pelo menos 30 amostras.

## Semântica física
O artigo PM100 descreve uma amostra a cada 20 s, obtida somando, para cada nó alocado ao job, \`ps0_input_power + ps1_input_power\`. O mapeamento de métricas M100 identifica \`psX_input_power\` em Watts. Assim, \`power_consumption\` representa potência agregada, em W, de entrada das PSUs de todos os nós alocados ao job — não potência isolada de GPU. A série é por job e não deve ser concatenada entre jobs.

## Decisão de uso
PM100 é viável como conjunto secundário para previsão da trajetória temporal de potência agregada do job/nós durante a execução, com divisão por job e teste temporal apropriado. Não é o conjunto primário para previsão per-GPU multissinal porque não inclui telemetria GPU individual nem temperatura GPU no Parquet PM100.

Há ainda um antecedente de 2026 para previsão pré-execução de potência de jobs que utiliza PM100 e F-DATA. A ATOCIA não deve reivindicar novidade para previsão pré-execução de potência de jobs com metadados de submissão. A pergunta distinta que podemos estudar aqui é previsão online da trajetória de potência durante a execução, com histórico temporal observado, e robustez a mudanças de regime — desde que o protocolo compare com baselines e métodos pertinentes.

## Artefatos
- \`inspect_pm100.py\` — auditor de baixa prioridade, 1 thread e 512 MB.
- \`audit/schema.json\` — schema Parquet efetivamente observado.
- \`audit/audit_summary.json\` — resumo integral da auditoria.
- \`audit/sample_sequences.csv\` — três sequências exemplificativas; não usar como amostra estatística representativa.

## Limitações
- Auditoria estrutural e de cobertura; não é avaliação de desempenho preditivo.
- A média/min/max dos valores agregados dependem da quantidade e configuração de nós alocados ao job; não comparar diretamente jobs sem normalização/contexto.
- O conjunto é de Marconi100 (CINECA), 2020, com amostragem de 20 s; não representa GPU atual nem transientes subsegundo.
