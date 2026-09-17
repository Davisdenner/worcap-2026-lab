# Pesquisa atual — rodadas 20–24 avaliadas, sem promoção

S12 tem o melhor score público informado, 1,71456; S13 marcou 1,71461,
piorando 0,00005. A classificação atual não foi informada. S10 permanece
o controle aprovado, 1,71895. Ganho público de 0,00262 contra S11 (1,71718).
O último score do líder informado foi 1,63223: a diferença é 0,08233, equivalente
a uma redução de aproximadamente 4,80% do nosso RMSE. Não houve verificação independente.
O resultado não aprova retroativamente S12 no critério histórico de 0,3%.

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
