# Rodada 34 — capacidade do corretor: número de folhas

Protocolo registrado antes de calcular qualquer resultado novo. Referência
imutável: S12. Somente dados oficiais. Nenhuma submissão é criada aqui.

## Por que esta hipótese

A Rodada 33 mediu o efeito de volume e o encerrou: multiplicar as células
por 10,7 melhorou o corretor em 0,303%, um ganho real mas de segunda ordem,
e a leitura registrada foi que **o limite é capacidade do modelo, não volume
de dado** — com 31 folhas e cerca de cem observações por folha, mais dados
refinam valores em vez de criar estrutura.

`round20.MODELS` contém quatro configurações: `local15`, `global15`,
`global31` e `global31_dense`. Elas usam **15 ou 31 folhas**. Em trinta e
três rodadas nenhuma árvore maior foi testada. Para 119 atributos e 3,7
milhões de linhas de treino, 31 folhas é uma árvore pequena, e a restrição
vinha de um regime de 768 células onde mais folhas não se sustentariam.

Esta rodada varia apenas a capacidade, mantendo as 8.192 células que a
Rodada 33 já mostrou serem melhores.

## Alvo quantitativo, declarado antes de rodar

Dos números da Rodada 33: o corretor tem RMSE 1,804805 contra 1,756391 da
S12, e a correlação entre os dois vetores de erro, deduzida do ganho
observado na fração 0,10, é de aproximadamente **0,979**.

Com correlação tão alta, a mistura `S12 + a(previsão − S12)` só produz
ganho relevante se o corretor chegar perto da S12 em RMSE. Pela aritmética
da combinação linear ótima, um ganho de 0,3% exige que o corretor alcance
cerca de **0,5% da S12**, isto é, RMSE em torno de **1,765**. A capacidade
precisaria entregar aproximadamente 2,3% de melhora sobre os 1,804805
atuais.

Esse é o número a olhar na coluna `_direto`. Se as árvores maiores ficarem
em 1,79 ou acima, o ganho na mistura será desprezível e a linha se encerra
sem necessidade de discutir as frações.

## Desenho: uma única variável

Reaproveita integralmente o aparato da Rodada 33 — `round33_scale.build_block`
e `round33_scale.predict_block`, mesma semente, mesmo sorteio de células,
mesmos 119 atributos, mesmo alvo, mesmas frações 0,10 e 0,25. Varia apenas
`max_leaf_nodes`:

| braço | folhas | origem |
| --- | ---: | --- |
| L31 | 31 | reaproveitado da Rodada 33 (`c8192`), sem retreinar |
| L127 | 127 | novo |
| L511 | 511 | novo |

`min_samples_leaf=100`, `l2_regularization=10`, `learning_rate=0.05`,
`max_iter=300`, `max_bins=128` — todos inalterados em relação a
`round20.MODELS['global31']`. Como a semente e o sorteio de células são os
mesmos da Rodada 33, a comparação entre os três braços é **pareada**: os
modelos veem exatamente os mesmos meses e as mesmas células.

Com 3,7 milhões de linhas, `min_samples_leaf=100` continua sustentável mesmo
com 511 folhas: são cerca de 7.300 observações por folha na média.

## Cortes e causalidade

Seis blocos `round27.YEARS`; avaliação nos cinco de `round27.EVAL`
(2011–2020, referência S12 = 1,756391). O treino usa `Features.idx`, que já
garante que o alvo `o+1` precede o início do bloco. Nenhum alvo do bloco
avaliado entra no treino nem na escolha de fração. Nenhum parâmetro é
calibrado nos blocos de avaliação.

## Classificação predefinida

- **A**: alguma combinação de folhas e fração atinge ganho global >= 0,3%
  **e** >= 4/5 blocos, >= 7/10 anos e >= 67/120 meses melhores. Não promove
  automaticamente: exige depois confirmação 2021–2022 e
  `src.round9.passes_gate`.
- **D**: há ganho, sem amplitude e estabilidade de A.
- **B**: toda combinação piora a S12.

As linhas `_direto` são descritivas e não são candidatas.

## Limitações reconhecidas antes de ver qualquer resultado

Os blocos 2009–2020 já foram reutilizados nas Rodadas 19 a 33; o viés de
seleção acumulado permanece. A Rodada 33 mediu o piso de ruído amostral
desta família em 0,39% no RMSE direto, o que se propaga para cerca de 0,1%
na métrica de promoção — a razão sinal-ruído do limiar de 0,3% é de
aproximadamente três para um, e resultados marginais devem ser lidos com
essa margem em mente. Árvores maiores sobreajustam com mais facilidade;
`l2_regularization` e `min_samples_leaf` ficam fixos de propósito, para que
a capacidade seja a única variável, mas se L511 piorar em relação a L127 a
interpretação natural é sobreajuste, não ausência de valor na capacidade.
Três valores de folhas não são uma busca de hiperparâmetros e não serão
ampliados depois de ver o resultado.
