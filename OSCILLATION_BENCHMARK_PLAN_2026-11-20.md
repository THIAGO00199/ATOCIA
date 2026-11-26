# ATOCIA — Plano de benchmark de oscilações
Data: 2026-11-20
Status: especificação de pesquisa; ainda não executado.

## Objetivo

Verificar se a ATOCIA consegue acrescentar valor mensurável na observação, previsão e explicação de oscilações de potência associadas a workloads computacionais sincronizados. O benchmark começa em dados offline e não controla hardware, rede elétrica ou refrigeração.

## Pergunta primária

Com telemetria temporal de workloads e potência, a ATOCIA consegue prever a evolução de potência agregada e detectar oscilações com antecedência útil, mantendo erro e falsos alarmes inferiores ou competitivos com baselines?

## Perguntas secundárias

1. Quais sinais de workload antecedem ou acompanham oscilação de potência?
2. A sincronização entre GPUs/nós explica parte da amplitude ou periodicidade observada?
3. A resposta térmica segue a potência com atrasos mensuráveis e dependentes do regime?
4. Uma memória temporal inspirada na TDT melhora desempenho ou explicabilidade em dados não vistos?
5. O padrão transfere entre sessões, modelos de GPU e máquinas?

## Dados e limites

### Dataset H100/B200 de alta resolução (2026)
- Usar primeiro apenas metadados e uma pequena amostra autorizada.
- Taxas de amostragem declaradas: 100 ms em algumas sessões e 20 ms em nós multi-GPU.
- Métricas declaradas: potência, utilização, memória, temperaturas e dados de CPU/GPU.
- Licença informada no repositório: CC BY-NC-ND 4.0. Tratar como pesquisa não comercial e não redistribuir/derivar para distribuição sem autorização jurídica explícita.
- Não representa uma instalação inteira de dezenas de MW; não tem, pelo que foi identificado, telemetria completa de facility/rede.

### M100 ExaData / CINECA
- Dados de longa duração e múltiplas camadas: nós, facility, refrigeração e energia.
- Agregações de 15 minutos são úteis para comportamento de facility, mas não capturam ciclos de poucos segundos.
- Auditar metadados, licença, timestamps, sensores e estrutura antes de qualquer download. Não baixar dezenas de GB para o notebook.

### Regra essencial
Os dois datasets não são sincronizados nem pertencem ao mesmo site. Analisar em experimentos separados; nunca concatenar como se fossem uma instalação única.

## Definição de evento

Separar classes em vez de chamar tudo de oscilação:
- Spike: excursão curta sem repetição estável.
- Step: mudança de patamar.
- Oscilação quase-periódica: alternância repetida com frequência/amplitude relativamente estáveis.
- Oscilação não estacionária: frequência ou amplitude muda no tempo.
- Regime sincronizado: múltiplos dispositivos apresentam alinhamento temporal consistente.
- Anomalia de sensor: salto impossível, flatline, timestamp irregular ou valor ausente.

A detecção deve declarar janela, limiar, banda de frequência e confiança. Esses parâmetros devem ser selecionados em treino/validação, nunca ajustados olhando o teste final.

## Métricas

### Previsão
- MAE e RMSE por horizonte.
- Erro de pico e de amplitude.
- Erro de frequência/período.
- Lead time antes de cruzar um limite.
- Cobertura de intervalos de previsão e largura média.
- Desempenho por sessão, GPU, modelo de workload e regime.

### Detecção
- Precisão, recall e F1 por evento.
- Falsos alarmes por hora.
- Eventos perdidos.
- Atraso entre início real e detecção.

### Explicação
- Estabilidade das variáveis associadas entre sessões.
- Precedência temporal e robustez a confundidores.
- Resultados de ablação.
- Intervenções/experimentos controlados, quando os dados permitirem.
- Não rotular correlação ou precedência como causalidade demonstrada.

## Baselines obrigatórios

1. Persistência (último valor).
2. Média móvel / EMA.
3. Regressão autoregressiva.
4. Regressão com lags de potência e utilização.
5. Gradient boosting, se o conjunto e ambiente justificarem.
6. Modelo físico simples, apenas quando houver variáveis e parâmetros identificáveis.

A ATOCIA só demonstra contribuição se superar baselines adequados fora da amostra ou entregar uma explicação/garantia útil que eles não oferecem.

## Protocolo contra vazamento

- Dividir por sessão/dispositivo/site, não por linhas aleatórias.
- Manter blocos temporais contíguos no teste.
- Normalizadores e seleção de features ajustados apenas no treino.
- Nenhuma variável futura pode entrar como preditor.
- Horizontes fixos definidos antes do teste.
- Relatar todos os testes relevantes, inclusive resultados negativos.

## Hipótese TDT testável

Implementar uma representação de memória temporal que capture efeitos persistentes e irreversibilidade operacional sem presumir equivalência com energia, entropia ou temperatura.

Comparar:
A. baselines sem estado TDT;
B. modelo com estado/memória temporal adicional;
C. ablação removendo esse estado;
D. avaliação em sessões/dispositivos não vistos.

A TDT só acrescenta valor técnico se a representação melhorar previsões, estabilidade, explicações ou transferência de domínio de forma reproduzível. Se não melhorar, revisar ou rejeitar essa parte da hipótese.

## Marcos de validação

- M0 — Auditoria de dados: licença, schema, relógios, missingness, amostragem, unidade e qualidade.
- M1 — Caracterização: espectro, autocorrelação, eventos, amplitude, frequência e sincronização.
- M2 — Previsão: baselines e avaliação multi-horizonte sem leakage.
- M3 — Explicação: lags, ablações, hipóteses concorrentes e confundidores.
- M4 — Generalização: sessão, GPU e hardware não vistos.
- M5 — Integração de dados de facility/rede, apenas com dados compatíveis e alinhados.
- M6 — Shadow mode com operador e sem controle automático, somente após validação e autorização.

## Critério de parada

Parar ou reformular se:
- dados não têm resolução ou sincronização suficientes;
- os resultados não superam baselines simples;
- desempenho desaparece em sessões não vistas;
- falsos alarmes inviabilizam uso operacional;
- explicações mudam radicalmente com pequenas alterações;
- licença não permite o uso planejado.

## Próxima ação segura

Enquanto o usuário joga, apenas revisar documentação, schemas e desenhar scripts offline. Não baixar datasets grandes, instalar dependências, treinar modelos ou executar testes de carga. A primeira execução de benchmark será pequena, limitada a uma amostra, após auditoria da licença e do formato.
