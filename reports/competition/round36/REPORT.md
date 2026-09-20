# Rodada 36: corretor máximo

**Classificação D.** É o melhor resultado do projeto depois da S12 e o único
que passa todos os critérios de estabilidade. Não é entregável, por um motivo
que só apareceu quando fui montar a exportação, e que é o achado mais
importante desta rodada.

## Hipótese

A [síntese das rodadas](../../../docs/SINTESE_RODADAS_25_34.md) conclui que só
escapam da parede de estimação as intervenções que **não calibram nada nos
blocos de avaliação**: mais dado de treino, mais capacidade de modelo e
agregação por reamostragem. Todas as demais ficam presas na faixa de ±0,1%,
porque cinco blocos de resíduo correlacionados não sustentam a estimação nem
de um parâmetro.

A Rodada 36 leva as três ao limite ao mesmo tempo, com 127 atributos, 8.192
células por mês e 255 folhas, e compara dois inícios de treino: 1981 e 1940.
A comparação entre os dois braços é o teste direto da hipótese, porque a única
diferença entre eles é o volume de dados históricos.

## Execução

Seis blocos por braço. O braço de 1940 processou de 816 a 936 origens por
bloco, o que dá de 6,68 a 7,67 milhões de linhas, com ajuste entre 400 e 488
segundos por bloco.

## Resultado

Corretor direto, medido contra o alvo declarado de 1,765. "Direto" significa a
previsão do corretor sozinho, sem misturar com a S12:

| configuração | RMSE direto | contra o alvo | contra a S12 |
| --- | ---: | ---: | ---: |
| r33_119 | 1,804805 | +0,039805 | −2,756% |
| r35_124 | 1,793047 | +0,028047 | −2,087% |
| r36_s1981 | 1,794009 | +0,029009 | −2,142% |
| **r36_s1940** | **1,788355** | +0,023355 | −1,820% |

O corretor sozinho é sempre pior que a S12, e isso é esperado: ele aprende o
resíduo, não a previsão. O valor dele aparece quando entra como correção
parcial. Misturado à S12 pela fração α, sobre os cinco blocos de avaliação:

| variante | RMSE | ganho | blocos | anos | meses |
| --- | ---: | ---: | ---: | ---: | ---: |
| r36_s1940_a0.25 | 1,753711 | **0,153%** | 4/5 | 7/10 | 71/120 |
| r36_s1940_a0.1 | 1,754460 | 0,110% | **5/5** | **9/10** | 76/120 |
| r36_s1981_a0.1 | 1,755058 | 0,076% | 3/5 | 8/10 | 70/120 |
| r36_s1981_a0.25 | 1,755198 | 0,068% | 3/5 | 8/10 | 62/120 |
| r35_124_a0.1 | 1,755539 | 0,049% | 4/5 | 6/10 | 70/120 |
| r35_124_a0.25 | 1,756160 | 0,013% | 2/5 | 5/10 | 64/120 |
| s12 | 1,756391 | 0,000% | referência | | |
| r33_119_a0.1 | 1,757366 | −0,055% | 1/5 | 3/10 | 53/120 |
| r33_119_a0.25 | 1,760462 | −0,232% | 1/5 | 3/10 | 49/120 |

## Leitura

**A hipótese se confirmou.** Os 41 anos extras de treino melhoraram o corretor
direto de 1,794009 para 1,788355, e a variante misturada de +0,076% para
+0,110%. Mais dado de treino escapa da parede de estimação, exatamente como a
síntese previu. É a primeira confirmação positiva dessa previsão.

**O a0.1 é o achado, e não é o de maior ganho.** Com 5 de 5 blocos, 9 de 10
anos e 76 de 120 meses, ele passa todos os critérios de estabilidade do
protocolo e falha só na amplitude. Sob a hipótese nula de ruído puro, acertar
5 de 5 blocos tem probabilidade de 3,1% e 9 de 10 anos tem 1,07%. O efeito é
real, ainda que pequeno, e é o oposto do padrão das rodadas anteriores, em que
o ganho aparecia sem estabilidade.

A escolha entre a0.1 e a0.25 se resolve por aí. A diferença de ganho entre os
dois, de 0,043%, está bem abaixo do piso de ruído amostral de cerca de 0,1%
medido na Rodada 33. A diferença de estabilidade, 5 de 5 contra 4 de 5 e 9 de
10 contra 7 de 10, não está. Quando a amplitude não distingue duas variantes e
a estabilidade distingue, a estabilidade decide. O candidato é o **a0.1**.

## Por que não é entregável

Ao montar o caminho de exportação para o corte de 2023, a rodada esbarra numa
limitação que nenhuma medição anterior tinha exposto.

A função `persistence_rows` lê `f.tp[origin − k]` para k de 0 a 5 e k igual a
11, ou seja, a precipitação observada nos meses anteriores à origem. Nos seis
blocos OOF isso funciona, porque todas as origens estão dentro de 1940 a 2022.
No período de teste, não: **a precipitação oficial congela em dezembro de
2022.** É o campo `tp_ultima_obs`, que repete dezembro de 2022 nas 24 linhas,
verificado no [diagnóstico de contrato](../../../scripts/diag_contrato.py).
Para 23 dos 24 meses-alvo essas oito colunas de persistência não existem.

E sem elas a configuração é exatamente a `r33_119`, que mede **−0,055%**.
**Todo o ganho das rodadas 35 e 36 vem da persistência de precipitação.**

A única forma de obtê-la para o período de teste seria baixar a precipitação
do ERA5 de 2023 e 2024 no Copernicus CDS. Essa é a variável-alvo. A
organização confirmou publicamente que o arquivo é acessível e pediu por
escrito que não seja utilizado, por descaracterizar a tarefa. A linha está
fechada por conformidade, não por desempenho.

**Falha de projeto, registrada.** Ao propor a Rodada 35, verifiquei que a
persistência era legal pelo critério temporal e que `tp.npy` cobria todas as
origens dos blocos de validação; isso está no cabeçalho do `diag_persist.py`.
Não verifiquei se ela existiria no período de teste. Duas rodadas foram
construídas sobre um atributo não entregável, e isso só apareceu na
exportação. **A verificação de disponibilidade no teste deveria ter precedido
a construção**, e essa é a lição de método que fica.

## O que ficaria para quem retomar

Existe uma variante legal: retreinar a persistência no **lag que de fato
estará disponível**, ou seja, a chuva de dezembro de 2022 defasada de 1 a 24
meses conforme o alvo, que é o que o arquivo oficial entrega em
`tp_ultima_obs`. Usa somente dado da competição.

O sinal de persistência decai rápido com o lag, então o ganho médio nos 24
meses seria uma fração dos 0,651% que a Rodada 35 mediu em lag 1, e
provavelmente ficaria abaixo do piso de ruído. Não foi executada.

## Registro

Nenhum alvo de teste lido, nenhum dado externo, nenhum CSV gerado, nenhuma
submissão criada. A S12 permanece inalterada e continua a referência
reproduzível.

[protocolo](protocol.json) · [decisão](decision.json) ·
[código](../../../src/round36_max.py) · [experimento](../../../experiments/ROUND36.md)
