# Retomada após S04 em 15/09/2026

## Rodada 15 concluída — organização S10 e recalibração conjunta

Referência consolidada em [S10_BASELINE.md](../docs/S10_BASELINE.md): composição,
scores, hashes e limitações. Índices de código, resultados e protocolo geral
atualizados para S10 e para o fato de 2021–2022 já ter sido avaliado.

Cinco componentes recalibrados conjuntamente: S02, regional com memória,
local sazonal com memória, PLS continental e tropical estendido por S09 fora
do trópico. Prior reproduz S10. Doze grupos existentes, pesos não negativos,
soma1 e variação máxima de 0,10 por componente. Quatro lambdas: 0,1; 0,3; 1; 3.
Calibração só com blocos completos anteriores ao corte e prior também causal.

Melhor joint1: **1,774622**, contra **1,775343** da S10 em 2009–2020; ganho
**0,041%**, 4/6 blocos, 6/12 anos e 81/144 meses melhores. Não passou pelos
critérios de ganho, blocos e anos. Não afrouxar limites ou ajustar pesos pelo
leaderboard. Nenhuma confirmação adicional 2021–2022, calibração final, CSV S11
ou upload. S10 e seus modelos intactos; 61 testes passaram.
[Protocolo](ROUND15.md), [resultados](../reports/competition/round15/RESULTS.md)
e [verificação](../reports/competition/round15/verification.json).

Último público S10 informado:1,71895; líder:1,71488. Último saldo informado:
um envio hoje. A execução não consumiu envios; não assumir que saldo/ranking
continuarão iguais em outro momento. Nenhuma próxima rodada iniciada.
Não recomendar envio desta recalibração. Abaixo, histórico.

## Rodada 14 concluída — hipótese física não confirmada

Quatro candidatas com proxies de transporte/convergência de umidade em 850 hPa,
derivados exclusivamente dos arquivos oficiais. Famílias flux e fluxconv,
PCA16 ou PCA32, concatenadas às entradas S10. PLS32 reajustado, pesos mantidos.
Produtos das médias mensais não são fluxos instantâneos ou integrados na coluna.
Pressão superficial e vizinhança mascaram novos indicadores abaixo do terreno;
unidades ERA5 padrão assumidas a partir das faixas, ausentes dos atributos NetCDF.

Todas pioraram o agregado 2009–2020. Melhor fluxconv32: **1,775455** contra
**1,775343** da S10, piora relativa de 0,0063%; só 3/6 blocos, 5/12 anos e
67/144 meses melhores. Hipótese não confirmada nesta configuração, sem concluir
que todo atributo físico seja inútil. Não ajustar parâmetros após observar resultados.

Nenhuma confirmação adicional 2021–2022, treino final, CSV S11 ou upload.
S10 (público 1,71895) permanece intacta. Último líder informado 1,71488 e saldo
de um envio hoje; esta rodada não consumiu envios, não assumir saldo atualizado
em outro momento. Auditoria, reprodução do controle S10 e 56 testes passaram;
exportação sem aprovação bloqueada e verificada.
[Protocolo](ROUND14.md), [resultados](../reports/competition/round14/RESULTS.md)
e [verificação](../reports/competition/round14/verification.json).

Não recomendar envio das candidatas físicas. Nenhuma nova rodada iniciada;
evitar busca interminável nos mesmos anos ou inferir ganho público dos ajustes.
As seções seguintes preservam o histórico.

## Rodada 13 concluída — preservar S10 e o envio restante

Kernel Ridge gaussiano substituindo somente a regressão de saída do componente
tropical S10: quatro configurações, parâmetros e gates congelados previamente.
PLS32, representação atmosférica, climatologia e pesos preservados. Treino direto
com todos os pares anteriores ao corte, sem usar correções residuais reprovadas.

Melhor `rbf_h2_a0.3`: RMSE 2009–2020 **1,775343 → 1,773881**, ganho **0,082%**;
4/6 blocos, 7/12 anos e 86/144 meses melhores. Falhou nos critérios de ganho
(mínimo 0,3%), blocos (mínimo 5) e anos (mínimo 9). As outras três pioraram o RMSE
agrupado. Não ajustar largura, regularização ou pesos depois desses resultados.

Não houve nova pontuação de 2021–2022, treino final, CSV S11 ou upload. S10
(público 1,71895) intacta; último líder informado 1,71488, diferença 0,00407.
Último saldo informado: um envio hoje; esta execução não consumiu envios.
Auditoria e controle linear aprovados, 51 testes passaram, bloqueio de exportação
sem aprovação verificado. [Protocolo](ROUND13.md),
[resultados](../reports/competition/round13/RESULTS.md) e
[verificação](../reports/competition/round13/verification.json).

Recomendação: manter S10 hoje, sem gastar o envio nessas candidatas. Não fazer
busca interminável nos mesmos períodos; não inferir que arquitetura mais complexa
garantirá melhora. Nenhuma próxima rodada foi iniciada. Abaixo, histórico.

## Rodada 12 concluída — preservar o último envio informado

Contexto atualizado pelo usuário: S10 **1,71895**, líder **1,71488**, diferença
0,00407; um envio disponível hoje no início desta rodada. Não consultado no
Kaggle, nem assumir que esse saldo ou liderança persistirão em outro dia.

Seis correções PLS dos resíduos S10, apenas dados oficiais, foram testadas.
Melhor `residual8_0.25`: RMSE 2009–2020 **1,775343 → 1,772613**, ganho **0,154%**,
5/6 blocos, 9/12 anos e 87/144 meses melhores, pior perda anual 0,465%.
Não atingiu o mínimo pré-fixado de 0,3%. Nenhuma promoção; não afrouxar critérios.
2021–2022 não foi novamente pontuado. Sem treino final, CSV S11 ou upload.
S10 e seus modelos continuam intactos. Auditoria e 47 testes passaram; bloqueio
de confirmação/exportação sem aprovação conferido.
[Protocolo](ROUND12.md), [resultados](../reports/competition/round12/RESULTS.md)
e [verificação](../reports/competition/round12/verification.json).

Não usar esta candidata para gastar o envio por pressão de prazo. Não aumentar
pesos com base no público nem estender a busca depois dos resultados desta rodada.
Uma nova hipótese requer nova rodada explicitamente definida; não foi iniciada.
As seções abaixo são histórico.

## Retorno mais recente — S10 aceita com 1,71895

Usuário confirmou o score público S10: **1,71895**, novo melhor com somente
dados oficiais. Ganho de 0,01062 sobre S09 (0,614%); faltam 0,01895 para 1,70.
Supera o último score de líder informado (1,72921), mas não afirmar liderança
atual sem reconfirmação. Resultado privado desconhecido. Preservar S10 e usar
como nova referência. Não aumentar pesos com base somente no retorno público.
Score registrado no ledger e manifesto, sem alterar snapshots de geração.
Nenhum treino, nova candidata ou envio iniciado com esse relato. Confirmar
classificação e saldo de envios antes de planejar outra rodada. Abaixo, histórico.

## Rodada 11 concluída — S10 pronta para envio manual

Gerada `submissions/submission_10.csv`, candidata `fine32_0.25`. O número da
rodada é 11, mas o arquivo é S10 porque a rodada anterior não exportou CSV.
Somente dados oficiais. PLS32 tropical, contexto continental64 e regional64
com filtro5/passo4 (1°); saídas na grade original. Mistura de 25% com S09 ao
norte de 10°S, transição linear desde 15°S e preservação exata ao sul de 15°S.

Quatro candidatas e um controle avaliados. Desenvolvimento 2009–2020:
**1,780988 → 1,775343** (0,317%); 6/6 blocos, 9/12 anos e 85/144 meses melhores;
pior perda anual 0,251%. Única candidata aprovada. Confirmação reutilizada
2021–2022: **1,834766 → 1,830283**, ambos os anos melhores, sem ajustes posteriores.
RMS da mudança: histórico 0,118107, 2023 0,132353, 2024 0,138975, dentro do limite.

Controle regional antigo PLS16/peso25: 1,776961; equivalente fino: 1,776491.
O ganho isolado da resolução é pequeno nesse controle; não atribuir todo o ganho
da candidata PLS32 à resolução. Nenhuma previsão de score 1,70 é sustentada.

CSV: 1.885.464 linhas, IDs/ordem oficiais, valores finitos/não negativos, hash,
130 coordenadas e reconstrução integral pelo modelo salvo conferidos. 44 testes
passaram. Nenhum upload. Aguardar score do usuário antes de outra rodada ou de
promover referência pública; S09 (1,72957) permanece a melhor confirmada.
[Protocolo](ROUND11.md), [resultados](../reports/competition/round11/RESULTS.md)
e [reconstrução](../reports/competition/round11/verification.json).
As seções abaixo preservam o histórico.

## Rodada 10 concluída — sem nova submissão

Correção PLS dos resíduos históricos da S09 implementada e avaliada em seis
candidatas, somente com dados oficiais. Melhor: PLS8 com intensidade 25%,
RMSE 2009–2020 **1,780988 → 1,777298** (0,207%). Melhorou 6/6 blocos,
11/12 anos e 84/144 meses, mas não atingiu o mínimo pré-fixado de 0,3%.
Não reduzir esse limite depois do resultado. Nenhuma candidata promovida;
2021–2022 não foi novamente pontuado, não houve treino final, CSV S10 ou upload.
S09 (público 1,72957) permanece a referência. Auditoria passou e 40 testes passaram.
[Protocolo congelado](ROUND10.md) e [resultados](../reports/competition/round10/RESULTS.md).

O diagnóstico histórico atribui 63,1% do erro quadrático à faixa de 10°S a
15°N, incluindo todos os pontos da grade nessa faixa, não apenas terra.
Isso não localiza os erros ocultos de 2023/2024. Hipótese para uma próxima
rodada, ainda não executada: representação atmosférica regional mais detalhada,
comparada à S09 na grade completa, com poucos parâmetros e protocolo próprio
definido antes de medir resultados. Não presumir que o ganho possível seja
suficiente para 1,70. Não reutilizar dados ou previsões NOAA.

## Retorno mais recente — S09 aceita com 1,72957

Usuário confirmou **S09 em 1,72957**, novo melhor público e nova referência
com dados exclusivamente oficiais. Ganho de 0,01548 sobre S06 (cerca de 0,887%)
e 0,00593 sobre S07. Distância de 0,00036 para o último score do líder informado,
1,72921; não assumir classificação atual. Score privado desconhecido.
Preservar S09, modelos, protocolo congelado e metadados de geração. O retorno
foi registrado separadamente no ledger e manifesto. Nenhum novo treino ou upload
iniciado com esse relato. Não ajustar pesos exclusivamente à distância do líder.
Se não houve outros envios, restam dois dos três anteriormente informados;
confirmar o saldo antes de planejar novas submissões. As seções abaixo são histórico.

## Rodada 9 concluída — S09 disponível, público desconhecido

Gerada `submissions/submission_09.csv`: **75% S06 + 25% PLS16**, somente dados
oficiais. Oito candidatas avaliadas segundo o [protocolo congelado](ROUND9.md).
S06-forward reconstrói pesos apenas com blocos anteriores. Desenvolvimento
2009–2020: **1,788894 → 1,780988** (ganho de 0,442%), melhora em 6/6 blocos,
10/12 anos e 88/144 meses. Árvores não passaram pelo critério de promoção.
Confirmação previamente consumida 2021–2022: **1,841795 → 1,834766**, melhora
nos dois anos, sem ajustes posteriores. Não alegar holdout inédito.
[Resultados completos](../reports/competition/round9/RESULTS.md).

Auditoria dos caches oficiais aprovada; nenhum artefato NOAA usado. Reconstrução
final S06: diferença máxima de 6,42e-8. RMS da mudança em 2023: 0,115285, abaixo de
duas vezes o histórico de 0,121515. CSV validado independentemente: 1.885.464 IDs
na ordem oficial, valores finitos/não negativos, hash e 130 coordenadas conferidos.
36 testes passaram. Nenhum upload realizado. Os três envios informados pelo
usuário não foram consumidos por esta execução. Aguardar decisão/score do usuário;
S06 (1,74505) continua referência pública com dados oficiais. Não prometer 1,70.
As próximas seções preservam o histórico anterior.

## Diretriz mais recente — somente dados oficiais

Usuário decidiu excluir dados externos das próximas candidatas. Usar **S06
(1,74505)** como referência compatível, não S07/S08. O plano de correção não
linear deve ser adaptado para S06, usando apenas atmosfera, contexto espacial
e histórico causal oficiais. Não aproveitar previsões/resíduos de modelos NOAA
nem misturá-los ao novo modelo. Auditar a origem dos caches antes de treinar.
[Restrição e protocolo](PROTOCOL.md). Preservar os artefatos anteriores e seus
scores, sem exclusão ou alteração no Kaggle. Nenhum novo treino/CSV/upload
foi executado ao registrar a preferência. Os trechos abaixo são histórico.

## Estado atual — auditoria S08 concluída, três envios restantes

S07 permanece a referência pública em **1,73550**. Auditoria não identificou
erro de exportação nem de reprodução da combinação S08. A mudança em 2023
foi 2,04 vezes maior que a histórica; ganhos mensais ocorreram em 67/120 meses.
Não confundir a localização das mudanças com a localização dos erros ocultos.
Misturas convexas positivas das previsões S07/S08 também pioram o público,
assumindo RMSE uniforme sobre todo 2023, conforme o protocolo informado.
[Diagnóstico e critérios para os próximos envios](../reports/competition/s08_diagnostic/RESULTS.md).
Não houve novo treino, CSV ou upload nesta auditoria. Antes de nova candidata,
pré-definir testes de robustez temporal e magnitude das correções; não ajustar
pesos diretamente ao feedback público. 2021–2022 já foi consumido na S08.
As seções seguintes são histórico, não autorização para executar novas rodadas.

## Rodada 8 — estado mais recente

S08 incorpora Atlântico tropical ao modelo de S07. Desenvolvimento 1,765488,
melhor em quatro blocos e sete anos. Após congelar a candidata, 2021–2022 foi
aberto pela primeira vez: 1,837746 → 1,834110, com melhora em ambos os anos.
Nenhum ajuste após a abertura. **2021–2022 não é mais holdout intocado.**
[Rodada 8](ROUND8.md). Usuário confirmou S08 em **1,74606**, piora de 0,01056
sobre S07. Não promover S08 como melhor pública. Investigar o desencontro entre
validação e público antes de outra mudança, sem assumir sua causa ou usar o
score público isolado para ajustar pesos. Nenhum novo treino iniciado com esse relato.
S07 (1,73550) continua referência pública. Não há upload ou execução agendada.
Os trechos abaixo que descrevem 2021–2022 como intocado são histórico anterior.

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
