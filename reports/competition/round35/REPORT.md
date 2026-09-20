# Rodada 35: persistência de precipitação

**Classificação D.** A primeira variante do projeto a superar a S12, e a
descoberta do único sinal novo encontrado depois dela. O ganho na mistura é
pequeno; o ganho no corretor é grande e é o que importa entender.

## Por que esta rodada existe

O organizador esclareceu o critério temporal: para prever o mês T vale
qualquer dado que em tese estaria disponível até o fim de T−1. Isso libera a
precipitação observada na origem como preditor.

E o pipeline **nunca** a tinha usado. O `round2.Features.matrix` tem 55 colunas
e nenhuma é chuva; a memória local de `round6` usa as nove variáveis
atmosféricas. A precipitação só aparecia como rótulo. Depois de 34 rodadas
mexendo em como combinar os mesmos preditores, esta foi a primeira a
acrescentar um preditor de natureza diferente.

O [diagnóstico de persistência](../persist_diagnostic/RESULTS.md) mediu o teto
antes da construção, com critério declarado por escrito, e autorizou seguir.

## O que foi construído

Cinco colunas de persistência somadas às 119 do corretor ampliado, todas lidas
na origem e em anomalia contra a climatologia causal: anomalia do mês de
origem, média dos três últimos meses, duas suavizações espaciais (3 por 3 e
9 por 9) e a tendência entre os dois últimos meses. Total de 124 atributos,
contra 8.192 células por mês.

O braço de controle, `c8192_119`, é idêntico em tudo menos nas cinco colunas.
A comparação entre os dois isola o efeito da persistência.

## Resultado

| variante | RMSE | ganho | blocos | anos | meses |
| --- | ---: | ---: | ---: | ---: | ---: |
| persist_124_a0.1 | 1,755539 | **0,049%** | 4/5 | 6/10 | 70/120 |
| persist_124_a0.25 | 1,756160 | 0,013% | 2/5 | 5/10 | 64/120 |
| s12 | 1,756391 | 0,000% | referência | | |
| c8192_119_a0.1 | 1,757366 | −0,055% | 1/5 | 3/10 | 53/120 |
| c8192_119_a0.25 | 1,760462 | −0,232% | 1/5 | 3/10 | 49/120 |
| persist_124_direto | 1,793047 | −2,087% | 0/5 | 0/10 | 32/120 |
| c8192_119_direto | 1,804805 | −2,756% | 0/5 | 0/10 | 25/120 |

**No corretor direto, a persistência vale 0,651%** em comparação pareada:
1,804805 sem ela, 1,793047 com ela, mesma semente e mesmas células. Está acima
do piso de ruído de 0,39% medido na Rodada 33, então é sinal, não sorteio.

## Por que 0,651% no corretor vira 0,049% na mistura

Esta é a lição da rodada, e ela é aritmética, não empírica.

O corretor entra na previsão final com peso 0,1. Ele não é um modelo
concorrente da S12; é uma correção de resíduo, e sozinho marca 1,793 contra
1,756 da S12. Uma melhora de 0,651% dentro de um componente que responde por
um décimo do resultado chega diluída ao fim.

Isso não é defeito desta rodada. É o teto da família inteira de
corretor-mistura, que a análise de correlação estimou em cerca de 0,53% mesmo
com um corretor perfeito.

## Consequência

A Rodada 36 nasceu daqui: se a persistência é sinal real e mais dado de treino
escapa da parede de estimação, valia combinar as duas coisas. Ela ampliou as
colunas de persistência de cinco para oito e o início do treino de 1981 para
1940, e chegou a +0,110% com 5 de 5 blocos, o melhor resultado do projeto
depois da S12.

**Nenhuma das duas é entregável**, e a razão está detalhada no
[relatório da Rodada 36](../round36/REPORT.md): a precipitação oficial congela
em dezembro de 2022, então as colunas de persistência não existem para 23 dos
24 meses-alvo. O ganho é real na validação e indisponível no teste.

## Registro

Somente dado oficial. Nenhum alvo de teste lido, nenhum CSV gerado, nenhuma
submissão criada. A S12 permanece inalterada.

[protocolo](protocol.json) · [decisão](decision.json) ·
[código](../../../src/round35_persist.py) ·
[experimento](../../../experiments/ROUND35.md) ·
[diagnóstico prévio](../persist_diagnostic/RESULTS.md)
