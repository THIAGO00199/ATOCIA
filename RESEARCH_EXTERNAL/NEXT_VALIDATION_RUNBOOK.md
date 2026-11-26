# Próxima execução — ATOCIA com dados públicos
**Status:** ingestão e auditoria documental em andamento. Nenhum modelo ATOCIA validado ainda.

## Agora
1. Finalizar download do PM100 v1 e comparar MD5 com o checksum publicado no Zenodo.
2. Executar `inspect_pm100.py` com `--max-rows 20000` e limites de 1 thread / 512 MB, somente quando o notebook não estiver sob carga de jogo.
3. Conferir unidade física, distribuição, comprimento das sequências, valores ausentes e relação entre amostras e duração do job. Se o dicionário não bastar, ler os scripts originais do projeto PM100.
4. Construir baselines causais por job: persistência, moving average 3/5/10 e EWMA. Separar trabalhos cronologicamente e nunca misturar janelas entre jobs.
5. Não comparar PM100 com a série GPU do notebook como se fossem o mesmo alvo físico; PM100 é potência do nó.

## Depois
- Identificar um subconjunto de AcmeTrace que contenha GPU power + GPU temperature + GPU utilization, com timestamps alinháveis. A distribuição ampla está indicada em ~80 GB; não baixar o conjunto completo. Usar arquivos individuais e verificar tamanho/cobertura antes.
- Preparar HazardNet como validação térmica em separado, inicialmente com um único recorte de nós/período; três arquivos totalizam aproximadamente 1.02 GB comprimidos. A licença CC BY 4.0 foi confirmada na API Zenodo.
- Tratar o dataset H100/B200 como pendente de esclarecimento de licença: a API do Figshare reporta CC BY 4.0, mas o repositório e o artigo reportam CC BY-NC-ND 4.0.

## Critério para avançar
Só treinar o candidato ATOCIA depois que alvo, amostras, cadence, dados ausentes, split e baselines estiverem registrados. Reservar holdout por sessões/trabalhos/cluster; nada de random split por linha. Publicar MAE/RMSE/MASE/skill versus persistence por horizonte e entidade.
