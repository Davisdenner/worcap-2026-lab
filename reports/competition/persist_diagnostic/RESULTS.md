# Diagnóstico de persistência de precipitação

**Resultado: aprovado com folga.** R² conjunto de 0,0281 no trópico contra um limiar declarado de 0,006, teto de 1,4% de RMSE.

## Contexto

O organizador esclareceu o critério de validade: para prever o mês T vale qualquer dado que em tese estaria disponível até o fim de T−1, incluindo dados externos, escala diária ou semanal, índices climáticos e informação de fora do domínio. O que não vale é usar o próprio mês T para estimar T.

Isso libera a precipitação observada em T−1 como preditor, e o pipeline **nunca a usou**. `round2.Features.matrix` tem 55 colunas sem nenhuma de chuva; `round6.local_memory` usa as nove variáveis *atmosféricas* em três defasagens, como o docstring declara. Em trinta e quatro rodadas a precipitação apareceu apenas como rótulo.

## Método e conformidade

Somente dado oficial. O `tp.npy` cobre 1940 a 2022, então todas as origens dos seis blocos já têm chuva observada e nenhum download foi necessário. Cinco atributos na origem `o`, todos em anomalia contra `f.climo` (climatologia causal de 60 anos), correlacionados com o resíduo da S12, que é, por definição, o que o pipeline não explicou. Reporta-se também o **R² conjunto** dos cinco, que é o que importa quando os atributos são correlacionados entre si.

Critério declarado antes de rodar: o teto de RMSE de um preditor com R² conjunto vale `1 − √(1−R²)`; para os 0,3% do limiar de promoção é preciso **R² ≥ 0,006**.

## Resultado

| grupo | anom_o | média3 | suave3x3 | suave9x9 | tendência | R² conj |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| DJF/lat<-30 | 0.032 | 0.042 | 0.031 | 0.032 | −0.011 | 0.0154 |
| DJF/-30a-10 | −0.024 | 0.022 | −0.028 | −0.036 | −0.058 | 0.0206 |
| DJF/lat>=-10 | 0.103 | 0.065 | 0.105 | **0.112** | 0.079 | 0.0232 |
| MAM/lat<-30 | 0.047 | 0.010 | 0.047 | 0.048 | 0.039 | 0.0093 |
| MAM/-30a-10 | 0.107 | 0.057 | 0.109 | **0.114** | 0.056 | 0.0231 |
| MAM/lat>=-10 | 0.154 | 0.096 | 0.157 | **0.164** | 0.115 | **0.0494** |
| JJA/lat<-30 | 0.056 | 0.075 | 0.056 | 0.053 | 0.025 | 0.0255 |
| JJA/-30a-10 | −0.083 | −0.064 | −0.087 | −0.097 | −0.036 | 0.0342 |
| JJA/lat>=-10 | **0.126** | 0.079 | 0.121 | 0.115 | 0.087 | 0.0247 |
| SON/lat<-30 | 0.006 | 0.031 | 0.006 | 0.004 | −0.061 | 0.0392 |
| SON/-30a-10 | −0.004 | 0.084 | −0.007 | −0.010 | −0.092 | 0.0838 |
| SON/lat>=-10 | 0.067 | 0.068 | 0.065 | 0.061 | 0.016 | 0.0152 |

R² conjunto médio na faixa tropical: **0,0281**, teto de RMSE **1,417%**. Em todos os grupos: 0,0303, teto de 1,527%.

## Três propriedades que sustentam o achado

**A suavização espacial vence no trópico.** Em MAM/lat≥−10 a correlação sobe de 0,154 sem suavizar para 0,157 com 3×3 e 0,164 com 9×9; em DJF tropical, de 0,103 para 0,112. Essa é a assinatura de um sinal espacialmente coerente: filtrar reduz ruído sem destruir estrutura. No teste sintético de validação, onde o campo plantado era espacialmente branco, a suavização diluía o sinal, o comportamento oposto, e o esperado naquele caso.

**O sinal mais forte está onde o erro mora.** MAM/lat≥−10 tem o maior R² entre os grupos tropicais, 0,0494, e é o grupo que carrega a maior fatia isolada do erro quadrático total, 18,9%, conforme a radiografia do [diagnóstico de amplitude](../slope_diagnostic/RESULTS.md).

**Há confirmação externa.** Uma equipe pública da mesma competição reportou a média 3×3 da anomalia de precipitação como o atributo mais importante do modelo dela.

## Por que é diferente dos nove diagnósticos anteriores

Todos os anteriores morreram na parede de estimação: eram correções calibradas em cinco blocos de resíduo. Persistência não é correção, é **atributo do modelo base**, ajustado em 335 a 455 meses de treino. Está do lado certo da restrição.

## Ressalvas

O teto de 1,4% pressupõe exploração linear perfeita do resíduo; uma árvore realiza menos, ainda que possa ganhar em interações com os atributos atmosféricos.

E o ganho OOF não é transferível ao leaderboard sem verificação: no treino a persistência vem do `tp.npy` oficial, mas no teste viria de fonte externa, já que a competição congela a chuva em dezembro de 2022. Se o produto, a grade ou as unidades divergirem, o atributo mede coisas diferentes nos dois lados. A verificação obrigatória é comparar dezembro de 2022 da fonte externa com `tp[-1]`, que a competição entrega como `tp_ultima_obs`. Foi exatamente esse modo de falha que derrubou a S08, aprovada na validação e pior no leaderboard.

Nenhuma candidata, CSV ou submissão foi criada. [persist.json](persist.json) · [Rodada 35](../../../experiments/ROUND35.md)
