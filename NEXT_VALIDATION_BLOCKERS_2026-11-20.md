# ATOCIA — Bloqueios de validação em escala de infraestrutura
Data: 2026-11-20
Este documento substitui a lista anterior orientada a diagnóstico de computadores pessoais.

## Escopo
ATOCIA pesquisa inteligência temporal e causal para data centers, clusters de IA e HPC. O laptop do fundador é apenas ambiente de desenvolvimento e instrumentação inicial.

## Bloqueios científicos e técnicos
1. **Dados reais de GPU/cluster:** precisamos auditar datasets públicos de cargas H100/B200 e traces HPC antes de desenhar experimentos adicionais.
2. **Resolução temporal:** os dados precisam preservar a escala de milissegundos/segundos para oscilações rápidas; dados agregados em 15 minutos não servem para esse objetivo.
3. **Sincronização:** timestamps de workload, potência, temperatura e cooling devem ser alinhados e suas diferenças documentadas.
4. **Causalidade:** logs de workload e scheduler precisam permitir formular e testar hipóteses; correlação isolada não prova causa.
5. **Escala espacial:** precisamos conhecer mapeamentos GPU→nó→rack→loop de cooling quando disponíveis.
6. **Generalização:** validação por sessões, hardware e, futuramente, sites diferentes.
7. **Incerteza:** previsões devem incluir intervalos calibrados, não somente estimativas pontuais.
8. **Referências:** comparar contra persistência, EMA, modelos estatísticos, ML convencional e abordagens físico-informadas.

## O que o laboratório local já demonstrou
- Coletor passivo Linux, auditorias de telemetria e testes automatizados.
- Experimentos curtos em um único notebook Intel.
- Resultados exploratórios de previsão térmica em horizontes de 5, 10 e 20 segundos.
- Nada disso demonstra desempenho em GPU, rack, data center, refrigeração líquida ou rede elétrica.

## Próximas entradas de pesquisa
- Dataset H100/B200 de 2026: alta resolução de potência, utilização e temperatura de GPU; verificar licença NC-ND e não usar comercialmente sem orientação/permissão.
- M100 ExaData: dados de nós e facility/cooling; escolher amostra pequena após inspeção de metadados e licenças.
- Possível colaboração acadêmica: HPC, sistemas térmicos, engenharia elétrica, sistemas distribuídos e controle.

## Limites operacionais do Garuda
- Não executar stress test, treino de modelos, extração em massa ou download grande enquanto o usuário estiver jogando.
- Não instalar pacotes nem alterar kernel, firmware, governor, energia, ventoinhas ou serviços sem necessidade e consentimento específico.
- Não alterar partições, bootloader, configurações de segurança ou arquivos fora de /home/iknowyou/ATOCIA.
- Priorizar trabalho leve e reversível.

## Critério para avançar
Só iniciar a análise computacional dos datasets depois de conhecer tamanho, formato, licença, espaço disponível e memória necessária. Começar por um subconjunto pequeno e documentado. Nenhuma alegação comercial ou causal será feita sem validação apropriada.
