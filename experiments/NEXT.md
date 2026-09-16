# Retomada após S04 em 15/09/2026

## Último retorno do usuário — S07 aceita

S07 atingiu **1,73550**, segundo lugar; líder informado **1,72921**.
Nova referência pública e histórica. Ganho de 0,00955 sobre S06; diferença
para o líder 0,00629. Não iniciar outra rodada automaticamente com esse relato.
Preservar S07, snapshot NOAA e modelos. 2021–2022 segue sem avaliação.
Os trechos abaixo de S07 ainda sem score são histórico anterior a esse retorno.

## Rodada 7 — candidata com informação oceânica

S07 preparada com temperaturas mensais do Pacífico da NOAA, atrasadas dois
meses em relação ao alvo. RMSE local 1,768074, melhora nos oito anos contra
S06. Ainda sem score público. [Protocolo e limitações](ROUND7.md).
S06 (1,74505) permanece a referência pública até novo retorno do usuário.
2021–2022 segue sem avaliação. Nenhuma execução agendada ou upload automático.

## Último resultado confirmado

S06 aceita com **1,74505**, informada pelo usuário. Nova referência pública
e histórica. Melhora de 0,00108 sobre S05. O último score conhecido do líder
é 1,72921; sua classificação atual não foi reconfirmada. Não há execução agendada.
As informações de S06 sem score nas seções abaixo são histórico anterior ao retorno.

## Retomada mais recente — rodada 6

Usuário confirmou S05 com 1,74613, segundo lugar, líder 1,72921. Melhor
resultado público é S05; ainda há risco histórico registrado para essa versão.
Rodada 6 adicionou memória à regressão local sazonal e atingiu 1,772788 local,
com melhora nos quatro blocos contra S04 e S05. [Protocolo](ROUND6.md).
S06 preparada para envio manual, ainda sem score público. Aguardar resultado
antes de registrar nova referência pública. 2021–2022 continua sem avaliação.
As seções seguintes preservam o histórico anterior, não são tarefas pendentes.

## Encerramento experimental de 15/09

S05 é o último arquivo solicitado para hoje. Candidata experimental, sem
promoção: pequeno ganho local, mas só quatro dos oito anos melhores que S04.
[Rodada 5](ROUND5.md). Aguardar score do usuário; S04 (1,74906) continua
referência. Não há treino, upload nem monitoramento de concorrentes agendado.
O usuário pretende analisar os concorrentes depois deste envio.

## Atualização mais recente

S04 aceita com **1,74906** e manutenção do primeiro lugar, conforme relato do
usuário. É a nova referência pública. S03 permanece preservada. Memória de
três meses e pesos por estação/latitude já foram testados e incorporados:
[rodada 4](ROUND4.md). O roteiro abaixo registra o plano anterior à rodada 4;
não repetir esses experimentos como se ainda estivessem pendentes.

## Estado preservado

- Submissões de 14/09 encerradas por decisão do usuário; não há execução agendada.
- Referência: **S03**, público **1,76467**, local **1,779464** nos quatro blocos.
- Melhor modelo: `joint25_modes_seasonal`.
- Código e parâmetros: [modelo atual](../docs/MODELO_ATUAL.md).
- CSV e metadados: [registro de submissões](../submissions/README.md).
- O bloco 2021–2022 continua sem avaliação. O privado de 2024 permanece desconhecido.
- Atualização de 15/09: sample oficial importado; os 12 NetCDF são idênticos e
  os IDs/ordem de S01–S03 coincidem exatamente com o sample. Nenhum retreino necessário.

## Antes de experimentar amanhã

1. Executar os testes e `scripts/check_repository.py` para conferir o estado salvo.
2. Confirmar o leaderboard atual; não assumir que o último score de concorrente
   mostrado ainda é o líder.
3. Usar S03 como referência local e manter seus CSV, previsões e metadados intactos.

## Prioridades experimentais

1. Diagnosticar erros mensais e regionais de S03 contra S02, incluindo a estabilidade
   dos segundos anos. Não tratar pontos espaciais como amostras independentes.
2. Testar uma hipótese por vez nos modos regionais: histórico temporal adicional
   ou representação espacial. Manter os demais parâmetros e blocos fixos.
3. Investigar a estabilidade dos pesos do ensemble entre blocos, com poucos
   candidatos e pesos conservadores, evitando busca extensa nos mesmos 96 meses.
4. Só depois de selecionar poucos candidatos, decidir quando abrir 2021–2022 para
   avaliação final local. Após a abertura, registrar que deixou de ser intocado.

Dados externos ainda não foram usados. Uma eventual frente externa deve verificar
cobertura histórica, regras e disponibilidade no instante da previsão antes
de influenciar o pipeline.

## Critérios de promoção

- RMSE agregado menor que S03 na mesma grade e nos mesmos blocos.
- Preferir ganhos em pelo menos três blocos e no agregado dos segundos anos.
- Registrar degradações; ganho pequeno não garante melhora no público ou privado.
- Gerar nova versão com nome distinto; nunca sobrescrever um CSV enviado.

O [plano após a primeira rodada](history/NEXT_round1.md) foi arquivado como
histórico. Ele não representa os próximos passos atuais.
