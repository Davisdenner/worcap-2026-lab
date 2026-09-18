# Registro histórico da pesquisa — rodadas 20–28

**Arquivo de contexto:** a participação terminou após a rodada 29. Consulte
[encerramento](../docs/ENCERRAMENTO.md) e [índice completo](README.md). As
propostas de passos seguintes abaixo são registros da época, não um plano ativo.
O CSV S14 exploratório foi gerado posteriormente ao diagnóstico da rodada 27;
seu [registro](S14_EXPERIMENTAL_ROUND27_GATE.md) não contém score público.

S12 tem o melhor score público informado, 1,71456; S13 marcou 1,71461,
piorando 0,00005. A classificação atual não foi informada. S10 permanece
o controle aprovado, 1,71895. Ganho público de 0,00262 contra S11 (1,71718).
Em novo relato, o usuário informou 1º lugar 1,57591, 2º 1,58124 e 3º
1,69966. As diferenças da S12 são 0,13865 para o 1º e 0,01490 para o 3º.
Esses scores não foram verificados independentemente; o privado é desconhecido.
O resultado não aprova retroativamente S12 no critério histórico de 0,3%.

## Rodada 28 — magnitude da vantagem S12 × Analog

O [protocolo 28](ROUND28.md) decompôs G = perda S12 − perda Analog antes
dos novos ajustes. Os 10% maiores |G| concentram 65,0% do benefício global
do oracle, mas misturam grandes vitórias e grandes derrotas do Analog.
Nenhum regressor de G passou o critério OOF de vantagem **líquida** positiva
no top 10% em 4/5 blocos. Strong wins tiveram AUC alta e lift consistente,
mas o top-k predefinido ganhou no máximo 0,040% global em 2011–2020,
abaixo dos 0,075% do gate da rodada 27; expected-gain gating foi parado
sem teste porque G bruto não passou seu critério. Analog teve o maior
oracle **pareado** entre os segundos especialistas congelados, enquanto
cada oracle triplo adicionou >1 ponto percentual, acionando a classe
predefinida **D** para um conjunto mais amplo. Isso é diagnóstico, não
ganho operacional. Nenhuma candidata foi criada. Ver [relatório]
(../reports/competition/round28/REPORT.md) e [auditoria]
(../reports/competition/round28/audit.json).

## Rodada 27 — seleção S12 versus análogos

O [protocolo 27](ROUND27.md) testou se atributos disponíveis podem indicar
qual dos dois previsores terá menor erro, sem corrigir diretamente a S12.
O oracle, que usa o observado e é apenas diagnóstico, reduziu o RMSE em
8,49% global e 9,00% no norte. O risco Q90 da rodada 26 **não** separou
de modo estável as vitórias do análogo. Classificadores do vencedor tiveram
sinal em parte dos cortes, permitindo o teste predefinido de soft gating.
O melhor ganho global do gating foi 0,075% em 2011–2020, ante 0,062% da
mistura fixa global de 10% no mesmo período, mas com só 6/10 anos melhores.
Conclusão **D — sinal aparente instável**, abaixo do ganho mínimo de 0,3%.
Nenhuma S14 ou submissão foi criada. Ver [relatório](../reports/competition/round27/REPORT.md)
e [auditoria](../reports/competition/round27/audit.json).

## Rodada 26 — erro comum S12 no norte

O [protocolo 26](ROUND26.md) investigou 0–15°N sem gerar candidata. Os seis
blocos 2009–2020 entraram no diagnóstico. A previsão temporalmente OOF do
resíduo usou cinco blocos 2011–2020, pois não há resíduos S12 OOF anteriores
a 2009 para treinar o primeiro corte. Todos os grupos testados tiveram R²
agregado contra resíduo zero negativo; o melhor foi dispersão (−1,11%). A
direção do erro não teve ganho estável. O risco de erro >Q90 teve AUC
0,820–0,868 e lift de 3,72–4,46 no decil de maior risco, mas quase toda
a ordenação já aparecia na climatologia e no valor S12. Resultado **C para
o valor do resíduo**, com sinal parcial para criticidade. Não houve gating,
correção, nova candidata, confirmação ou envio. Veja o [relatório científico]
(../reports/competition/round26/REPORT.md) e a [auditoria]
(../reports/competition/round26/audit.json).

## Rodada 25 — diagnóstico, ordem dos PCs e análogos

Após auditoria científica do pipeline, o usuário pediu executar os três
primeiros passos: completar o diagnóstico da S12, testar uma ablação
estrita da dinâmica dos PCs e medir diversidade de um previsor por análogos.
O [protocolo 25](ROUND25.md) foi fixado antes das novas métricas.

O diagnóstico confirmou que 0–15°N concentra 47,38% do erro quadrático.
Os cinco componentes erram no mesmo sentido em 75,58% dos pontos, onde se
concentra 98,90% do SSE da S12. Isso é descritivo e não demonstra
previsibilidade do erro comum. Mudança de regime KMeans não concentrou erro.

A ablação direta de 32 PCs do mês anterior piorou o RMSE puro
1,816897 → 1,819411; suas duas misturas com S12 também pioraram.
Análogos sazonais de baixa dimensão tiveram RMSE puro 1,847297 e correlação
de erros 0,9487 com S12. A mistura predefinida de 10% reduziu o RMSE
histórico de 1,770775 para **1,769921** (ganho **0,0482%**), mas obteve só
4/6 blocos, 8/12 anos e 79/144 meses melhores: reprovada pelo mínimo de
0,3% e pela estabilidade. A mistura de 25% piorou. Uma auditoria separada
refez as métricas e conferiu hashes e cortes.

**Nenhuma candidata foi promovida.** Sem confirmação 2021–2022, treino
final, CSV ou upload nesta rodada. S12 continua como referência. Ver
[resultados e decisão](../reports/competition/round25/DECISION.md).

## Pesquisa executada nesta retomada

Em 17/09, o usuário autorizou testar a hipótese 1: árvores com atributos locais
e estado atmosférico continental/tropical. O [protocolo 20](ROUND20.md) fixa
quatro modelos, amostragem aninhada e duas misturas por modelo contra S12.
Nenhum CSV ou upload automático está autorizado por este pedido de pesquisa.
Critérios de 0,3%, estabilidade e confirmação continuam obrigatórios.

A hipótese 1 foi concluída: a melhor mistura teve RMSE 1,770937 contra
1,770775 da S12, piora de 0,009%, e melhorou apenas 2/6 blocos.
Com autorização do usuário, a hipótese 2 testou especialistas regionais
não lineares com referência global e transições suaves. Antes do treino,
atualizamos o [diagnóstico da S12](../reports/competition/s12_diagnostic/RESULTS.md):
a latitude 0°–15°N responde por 47,38% do erro quadrático com 20,27% dos
pontos. O [protocolo 21](ROUND21.md) fixou quatro candidatas antes de medir
seus resultados. A melhor teve RMSE 1,770455 (ganho de 0,018%), 5/6 blocos,
7/12 anos e 80/144 meses melhores. Falhou o ganho mínimo e a estabilidade
por ano. A verificação integral refez métricas e seleção; **nenhuma foi
promovida**. Não fizemos confirmação 2021–2022 nem criamos S13.

Esses blocos já foram reutilizados em várias rodadas e não são teste
independente. Não tentar contornar os critérios escolhendo a região ou os
pesos depois de observar essas quatro candidatas. A S12 segue como melhor
submissão pública informada. Ver [rodada 20](../reports/competition/round20/RESULTS.md)
e [rodada 21](../reports/competition/round21/RESULTS.md).

## Hipóteses 3 e 4 — 17/09/2026

O usuário pediu testar treino-base mais antigo e decomposição espacial da
saída. Fixamos [protocolo 22](ROUND22.md) e [protocolo 23](ROUND23.md) antes
de medir os resultados. A comparação controlada da família de árvores locais
usou inícios 1940, 1960 e 1981, com parâmetros e amostras comuns nos meses
sobrepostos. O melhor candidato antigo misturado à S12 piorou 0,037%, com
3/6 blocos e 4/12 anos melhores. O modelo puro iniciado em 1981 (1,823403)
também superou 1960 (1,824310) e 1940 (1,825636).

A saída ampla 9×9 somada ao detalhe local foi avaliada na grade original.
Seu melhor peso misturado à S12 piorou 0,030%, com 2/6 blocos e 4/12 anos.
O modelo decomposto puro (1,947678) ficou atrás do controle direto (1,823403).
As previsões salvas, métricas e seleções foram recalculadas em verificação
separada. **Nenhuma candidata passou; não há S13 ou confirmação nova.**
Os ensaios limitam-se a uma família de árvores-base e uma decomposição 9×9;
não alegar que todas as variantes de PLS ou multiescala foram exauridas.
Ver [resultados 22](../reports/competition/round22/RESULTS.md) e
[resultados 23](../reports/competition/round23/RESULTS.md).

## Rodada 24 — transporte de umidade

Após as hipóteses anteriores, o usuário autorizou testar proxies derivados
somente dos campos oficiais de umidade específica e vento de 850 hPa.
O [protocolo 24](ROUND24.md) comparou produtos q·u/q·v, convergência espacial
e lags/a montante, mantendo iguais as amostras, árvores e S12 de referência.
As oito candidatas, pesos e aplicação global/norte foram fixados antes da
avaliação. A melhor reduziu o RMSE histórico de 1,770775 para **1,770637**
(ganho de **0,0078%**), melhorando 6/6 blocos, 10/12 anos e 89/144 meses.
É um sinal pequeno e consistente, porém cerca de 38 vezes inferior ao
mínimo de 0,3%; **nenhuma passou**. A ablação sugere que os lags ajudam mais
que a convergência isolada, sem impacto bastante para promoção.
Ver [resultados e verificação](../reports/competition/round24/RESULTS.md).
Nenhuma confirmação 2021–22, S13, CSV ou upload foi executado.

Após pedido explícito de S13 experimental, a confirmação de 2021–2022 foi
executada com a candidata fixa. O ganho foi apenas 0,00247% (mínimo 0,1%) e
2022 piorou. O primeiro pedido dispensava somente o mínimo histórico de 0,3%,
e a exportação parou. O usuário posteriormente autorizou também dispensar a
confirmação para gerar a [S13 exploratória](../reports/competition/round24_experimental/RESULTS.md).
O limite de mudança no teste passou e o CSV foi gerado. O usuário informou
envio manual e score público corrigido de 1,71461: piora de 0,00005 contra
S12 (1,71456). S12 continua a
referência reproduzível; o resultado privado segue desconhecido.

Diagnóstico da S11 em 2009–2020 e 16 candidatas, em três protocolos congelados:

| Rodada | Hipótese | Melhor ganho histórico | Decisão |
| --- | --- | ---: | --- |
| 16 | Correção espacial/sazonal dos resíduos | 0,029% | Reprovada |
| 17 | Correção não linear por componentes e atmosfera | 0,248% | Reprovada |
| 18 | Memória longa no PLS tropical | 0,006% | Reprovada |

Nenhuma passou conjuntamente os critérios de promoção automática. Posteriormente,
o usuário autorizou uma exceção para `meta15_a0.25`: dispensar apenas o mínimo
de desenvolvimento para uma S12 experimental. A confirmação reutilizada 2021–2022
passou (ganho de 0,436%, ambos os anos melhores), assim como o limite de mudança
por ano de teste. Os critérios gerais de 0,3% e estabilidade continuam ativos.
Veja os [resultados da exceção](../reports/competition/round17_experimental/RESULTS.md).

## Direção com melhor evidência para estudar a seguir

A integração S12 foi implementada: retreino do corretor sobre exemplos OOF
oficiais empacotados e inferência completa reconstruíram o CSV original.
Modelos-base vieram da reprodução já verificada de S10/S11; não se repetiu toda
a pesquisa OOF. Consulte o [relatório](../reports/reproducao/S12.md).

A ampliação do histórico abaixo foi testada na rodada 19, após autorização:
196.608 exemplos adicionais de 1997–2004 e duas ponderações predefinidas.
A melhor ficou em 1,770779761 contra 1,770775491 da S12, com 4/6 blocos,
6/12 anos e 74/144 meses melhores. **Nenhuma passou; S13 não foi gerada.**
Confirmação e treino final dessas candidatas não foram executados.
Veja os [resultados completos](../reports/competition/round19/RESULTS.md).

Não ampliar automaticamente a busca de pesos nem aumentar a fração da correção
para aproveitar envios disponíveis. Uma próxima rodada exige nova hipótese e
protocolo antes de olhar seus resultados, com o mesmo limiar de 0,3% contra S12
e estabilidade. Não há candidata aprovada aguardando exportação.

A rodada 17 foi a mais promissora. O corretor com 15 folhas e fração 0,5 ganhou
0,248%, mas teve perda anual máxima de 1,032%. Com fração 0,25 ganhou 0,217%,
melhorou 5/6 blocos e 10/12 anos, com pior perda anual de 0,352%: passou nas
condições de estabilidade, mas não no ganho mínimo. Nenhuma foi promovida
automaticamente; a exportação experimental conservadora é uma exceção documentada.

Uma hipótese levantada antes da rodada 19 era ampliar a base de previsões históricas
fora do treino que alimenta o corretor, hoje iniciada em 2005. O primeiro
bloco de avaliação dispõe de apenas quatro anos para aprender a correção.
Isso poderia ajudar a explicar sua instabilidade, mas não foi demonstrado. A
rodada 19 mostrou que a ampliação e as ponderações testadas não bastaram.

Antes de novos resultados, registrar em outro protocolo os blocos adicionais,
a disponibilidade de treinamento dos modelos-base, o tratamento do aquecimento,
a comparação controle e o conjunto finito de candidatas. Não alterar os protocolos
16–18, escolher períodos favoráveis ou remover 2009–2010 para fazer passar o ganho.

## Registros

- [Resumo da retomada](../reports/competition/s11_followup_2026-09-16.md).
- [Diagnóstico](../reports/competition/s11_diagnostic/RESULTS.md).
- [Rodada 16](../reports/competition/round16/RESULTS.md).
- [Rodada 17](../reports/competition/round17/RESULTS.md).
- [Rodada 18](../reports/competition/round18/RESULTS.md).
- [Rodada 19](../reports/competition/round19/RESULTS.md).
- [Protocolo geral vigente](PROTOCOL.md).

A reprodução S10/S11 já foi concluída e documentada. Licença e identificação
da equipe continuam pendências para a entrega formal. Os documentos históricos
anteriores estão em `docs/history/antes_da_organizacao_2026-09-16`.
