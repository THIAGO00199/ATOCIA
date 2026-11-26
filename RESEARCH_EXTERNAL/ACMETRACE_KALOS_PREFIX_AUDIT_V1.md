# AcmeTrace / Kalos — auditoria preliminar de prefixos
**Data da auditoria:** 21/11/2026  
**Status:** inspeção de prefixos limitados; não é auditoria do conjunto inteiro nem benchmark preditivo.

## Acesso, origem e licença
- Distribuição: https://huggingface.co/datasets/HuggingAGree/AcmeTrace
- Repositório oficial de projeto: https://github.com/InternLM/AcmeTrace
- Release dos workloads: março a agosto de 2023, dois clusters, 880.740 trabalhos (470.497 GPU jobs), 80 GB para todos os arquivos de utilização segundo README.
- Licença: arquivo LICENSE.txt do repositório oficial e cópia consultada no Hugging Face declaram Creative Commons Attribution 4.0 (CC BY 4.0). Exige atribuição e preservação de notices/licença.
- O visualizador automático do Hugging Face falha porque os arquivos CSV não compartilham um schema tabular único; os arquivos originais devem ser carregados individualmente.

## Descoberta de estrutura
O cluster Kalos contém três matrizes com telemetria por identificador GPU:
- `POWER_USAGE.csv`: 929.567.543 bytes (~0,93 GB)
- `GPU_TEMP.csv`: 845.136.147 bytes (~0,85 GB)
- `GPU_UTIL.csv`: 843.403.137 bytes (~0,84 GB)
- Total para as três matrizes: aproximadamente 2,62 GB.
- O README documenta timestamp `Time` com intervalo de 15 segundos e informa coleta de métricas de utilização por DCGM, IPMI e Prometheus.
- O prefixo de 256 KiB de cada matriz tinha 2.345 colunas, incluindo `Time`, e exatamente os mesmos 2.344 identificadores GPU nas três tabelas.
- Os 62 registros completos obtidos por matriz tinham timestamps idênticos, de 2023-08-15 15:30:15 a 2023-08-15 15:45:30 (+08:00), em passos exatos de 15 segundos.
- Portanto, o alinhamento por `Time` e identificador GPU é tecnicamente viável no trecho inspecionado. A ordem das colunas não deve ser presumida igual sem validar os cabeçalhos; o script alinha por identificador.

## Amostra e qualidade observada
A amostra é só o primeiro prefixo de cada arquivo (256 KiB); não representa seis meses completos:
- Mediana por linha: 278/2.344 células presentes em potência, 310/2.344 em temperatura e 317/2.344 em utilização.
- Somente 4 identificadores tiveram 80% ou mais de triplas simultaneamente preenchidas no trecho de 62 registros.
- Um identificador de GPU teve 62/62 triplas preenchidas, o que é suficiente para comprovar que há ao menos uma sequência sincronizada nesse pequeno trecho — não prova que a cobertura continue no restante do período.
- Valores brutos observados no prefixo: POWER_USAGE 56,8–511,4; GPU_TEMP 27–78; GPU_UTIL 0–100. Esses intervalos são compatíveis com métricas usuais de GPU, mas **não atribuímos unidades** sem confirmação formal do schema/metadados. Não converter ou rotular como W/°C/% nos resultados ainda.

## Consequência para a ATOCIA
AcmeTrace/Kalos é o candidato mais direto encontrado para estudo multivariado GPU (potência + temperatura + utilização) em cluster de produção. Porém:
1. 15 s é resolução muito mais lenta que a telemetria H100/B200 de 20–100 ms; não serve para validar oscilações subsegundo.
2. Os arquivos de Kalos totalizam ~2,62 GB e têm muitas células vazias; baixar tudo e procurar uma GPU com histórico completo é uma tarefa seletiva.
3. A amostra inicial comprova correspondência de cabeçalho e timestamp, mas não continuidade temporal nem disponibilidade em todo o período.
4. A série IPMI `GPU_AB_Power.csv` em Seren (290,3 MB) contém colunas PSU, potência do sistema/CPU/memória e nó, com timestamps observados a cada 5 min em um prefixo. Não deve ser tratada como potência individual de GPU sem documentação adicional.
5. Usar AcmeTrace como trilha complementar para regime de carga e dinâmica térmica mais lenta. Preservar os dados H100/B200 como referência principal para fenômenos subsegundo, sujeito à divergência de licença documentada no registro de datasets.

## Artefatos reprodutíveis
- `metadata/acmetraces_samples/*.prefix`: prefixos de 256 KiB por arquivo, baixados com HTTP Range.
- `acmetraces_prefix_audit.py`: auditor local que verifica headers, timestamps, completude e cobertura por GPU; não acessa a internet.
- `metadata/acmetraces_prefix_quality_report.json`: resumo da execução deste auditor.
- `metadata/acmetraces_schema_notes.txt`: sizes e headers HTTP.
- `metadata/AcmeTrace_README.md`: snapshot do README oficial.

## Referências
- README e schema do dataset: https://github.com/InternLM/AcmeTrace
- Registro de dados: https://huggingface.co/datasets/HuggingAGree/AcmeTrace
- Paper de workload characterization: https://www.usenix.org/conference/nsdi24/presentation/hu
