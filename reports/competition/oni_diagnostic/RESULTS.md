# Diagnóstico de ENSO — primeiro uso de dado externo desde a Rodada 8

**Resultado: encerrado pelo critério causal.** O maior teto do projeto, 2,45%, e nenhum estimador que o alcance.

## Conformidade

A Seção 2.6 das regras permite Dados Externos "de domínio público e igualmente acessíveis a todos os Participantes, sem custo". O ONI do NOAA Climate Prediction Center qualifica: obra do governo dos EUA, domínio público, publicação gratuita. Fonte `oni.ascii.txt`, sha256 `93f8c86c7a660f46318abe33b38c0479d184812d95a479a1fe869c0c2363a9e4`, 876 de 996 meses cobertos.

O ONI é temperatura de superfície do mar no Pacífico — **uma variável diferente do alvo**. Esse é o critério que separa preditor legítimo de recuperação de rótulo, e ele é respeitado aqui.

## Causalidade

O ONI centrado no mês `m` usa TSM de `m−1`, `m` e `m+1`, logo só existe ao fim de `m+1`. Para uma origem `o` o valor mais recente legítimo é o centrado em `o−1`. Usar `ONI[o]` seria vazamento silencioso. As três variantes respeitam esse limite.

## Critério declarado antes de rodar

O ganho máximo de RMSE de um preditor com correlação `r` é `1 − √(1−r²)`. Para os 0,3% do limiar de promoção é preciso **|r| ≥ 0,077**.

## Resultado

Correlação temporal por célula entre ONI e o resíduo da S12, média dos seis blocos:

| grupo | oni_lag1 | oni_lag3 | oni_tendência |
| --- | ---: | ---: | ---: |
| DJF/lat<-30 | 0.007 | −0.006 | 0.025 |
| DJF/-30a-10 | −0.024 | −0.016 | −0.031 |
| **DJF/lat>=-10** | **−0.180** | −0.164 | −0.168 |
| MAM/lat<-30 | −0.072 | −0.085 | 0.065 |
| MAM/-30a-10 | −0.008 | −0.014 | 0.034 |
| MAM/lat>=-10 | −0.019 | −0.026 | 0.036 |
| JJA/lat<-30 | 0.007 | −0.064 | 0.097 |
| JJA/-30a-10 | −0.051 | −0.062 | 0.035 |
| JJA/lat>=-10 | −0.036 | −0.017 | −0.004 |
| SON/lat<-30 | 0.033 | 0.002 | 0.072 |
| SON/-30a-10 | −0.040 | −0.052 | 0.006 |
| **SON/lat>=-10** | **−0.137** | −0.112 | −0.107 |

Correção por célula, `S12 + beta·ONI`, com beta ajustado só em blocos anteriores:

| variante | RMSE | ganho | blocos | anos | meses |
| --- | ---: | ---: | ---: | ---: | ---: |
| s12 | 1.756391 | +0.000% | — | — | — |
| oni_lag1 causal | 1.777702 | −1.213% | 1/5 | 2/10 | 48/120 |
| oni_lag1 oracle | 1.718997 | +2.129% | 5/5 | 10/10 | 91/120 |
| oni_lag3 causal | 1.789174 | −1.866% | 0/5 | 0/10 | 37/120 |
| oni_lag3 oracle | 1.717031 | +2.241% | 5/5 | 10/10 | 88/120 |
| oni_tendência causal | 1.768930 | −0.714% | 1/5 | 1/10 | 48/120 |
| oni_tendência oracle | 1.713435 | +2.446% | 5/5 | 10/10 | 99/120 |

## Conclusão

**O sinal é real e fisicamente correto.** O maior |r| é 0,180, em DJF no trópico, **negativo** — El Niño associado a menos chuva no norte da América do Sul no verão austral, a teleconexão de livro-texto, no sinal certo, na região certa e no trimestre em que o ENSO atinge o pico. SON tropical repete com −0,137. Os oito grupos extratropicais ficam abaixo de 0,10. Ruído não escolhe o trópico, nem o sinal fisicamente correto, nem a estação certa.

**E o oracle é o maior de todo o projeto: 2,45%**, com 5/5 blocos e 10/10 anos nas três variantes — oito vezes o limiar de promoção.

O estimador causal quebra, e a razão é identificável: ele ajusta **um beta por célula da grade**, 78.561 parâmetros, a partir de no máximo cinco blocos anteriores. E o que limita não são os 120 meses: é que 120 meses contêm cinco ou seis eventos ENSO independentes. Para o bloco de 2011 há um único bloco anterior, praticamente um estado de ENSO.

O conserto natural seria estimar o padrão de teleconexão em `tp − climatologia` sobre todo o histórico, onde há quinze a vinte ciclos, e ajustar apenas um escalar de amplitude nos blocos da S12. Essa via não foi executada: o diagnóstico de janela de climatologia, feito em seguida, mostrou que mesmo **um escalar global** não se deixa estimar de forma confiável com cinco blocos, o que retira a base do conserto.

Registre-se também o contexto do período de teste: o El Niño de 2023/24 teve teleconexões a 15–30% da intensidade típica, com anomalias de chuva no Pacífico tropical em torno de um terço do usual, neutralizadas por aquecimento simultâneo do Índico e do Atlântico. Um modelo condicionado à resposta canônica aplicaria essa resposta em excesso justamente em 2023–2024.

Nenhuma candidata, CSV ou submissão foi criada. [oni.json](oni.json)
