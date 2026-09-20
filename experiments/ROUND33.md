# Rodada 33 — taxa de amostragem de células no corretor da S12

Protocolo registrado antes de calcular qualquer resultado novo. Referência
imutável: S12. Somente dados oficiais. Nenhuma submissão é criada aqui.

## Por que esta hipótese

Nove diagnósticos consecutivos (Rodadas 27 a 32, mais os diagnósticos de
amplitude, fluxo de umidade, ENSO e janela de climatologia) produziram
oracles reais — 0,40%, 0,76%, 2,45%, 0,30% — e estimadores causais que
aterrissaram todos em ±0,1%, com doze parâmetros, com 78.561 e com **um**
escalar global. O gargalo comum não é o método: cinco blocos de resíduo da
S12, fortemente correlacionados, não contêm informação independente
suficiente para calibrar praticamente nada.

Esta rodada testa a única classe de mudança que escapa dessa parede:
**mais dado de treino, sem nenhum parâmetro calibrado nos blocos de
avaliação.**

A restrição nunca revisitada está em `round20.MODELS`, cujo terceiro campo
é a contagem de células: `global31 = (True, 31, 768, 100, 10.)`. Os
corretores por trás da S12 treinam com **768 das 78.561 células por mês**,
ou **0,98% da grade**. Precipitação é fortemente assimétrica e o RMSE é
dominado pelos extremos; amostrar 1% das células vê 1% dos extremos, que
são exatamente o que define a métrica. O motivo dessa taxa é memória da
máquina local, a mesma limitação que levou esta competição ao Kaggle.

## Desenho: uma única variável

Reproduz `global31` da Rodada 20 **sem nenhuma alteração** — os mesmos 119
atributos (55 locais de `round2.Features.matrix` mais 64 globais de
`round20.context`, chamando o código original), a mesma árvore
(`max_leaf_nodes=31`, `min_samples_leaf=100`, `l2_regularization=10`,
`learning_rate=0.05`, `max_iter=300`, `max_bins=128`), o mesmo alvo
(observado menos a climatologia do mês-alvo) e as mesmas frações de mistura
(0,10 e 0,25, aplicadas como `S12 + fração × (previsão − S12)`).

Varia exatamente uma coisa: **768 células por mês contra 8.192**, um fator
de 10,7. A amostra de 768 é **aninhada** na de 8.192 — são as 768 primeiras
da mesma extração por mês — o que isola a taxa de amostragem sem ruído de
reamostragem e permite montar a matriz de atributos uma única vez por
bloco.

O início do treino continua em 1981 via `Features.idx`, inalterado. A
hipótese de estender para 1940 foi descartada deste desenho: o ERA5
pré-satélite tem qualidade inferior, e misturar as duas mudanças impediria
atribuir o efeito.

## Verificação externa da implementação

O braço de 768 células deve **reproduzir** a linha `global31` já registrada
em `reports/competition/round20/{ano}_direct.json`. `control_check()` faz
essa comparação automaticamente e ela é reportada dentro de
`decision.json`. Diferenças pequenas confirmam a implementação; diferenças
grandes invalidam toda a tabela e nenhum outro número deve ser lido.

## Cortes e causalidade

Seis blocos `round27.YEARS`; avaliação nos cinco de `round27.EVAL`
(2011–2020, referência S12 = 1,756391). O treino usa `Features.idx`, que já
garante que o alvo `o+1` precede o início do bloco. Nenhum alvo do bloco
avaliado entra no treino nem na escolha de fração.

## Classificação predefinida

- **A**: alguma fração atinge ganho global >= 0,3% **e** >= 4/5 blocos,
  >= 7/10 anos e >= 67/120 meses melhores. Não promove automaticamente:
  exige depois confirmação 2021–2022 e `src.round9.passes_gate`.
- **D**: há ganho, sem amplitude e estabilidade de A.
- **B**: toda fração piora a S12.

A linha `_direto` de cada braço (previsão pura, sem mistura) é reportada
como descrição e não é candidata.

## Limitações reconhecidas antes de ver qualquer resultado

Os blocos 2009–2020 já foram reutilizados nas Rodadas 19 a 32; o viés de
seleção acumulado permanece. A árvore tem capacidade fixa e modesta — 31
folhas, 300 iterações — e com 768 células por mês já há cerca de cem
observações por folha; multiplicar os dados por dez refina os valores das
folhas, o que é ganho de segunda ordem, e não cria estrutura que o modelo
não conseguia representar antes. Se o efeito for nulo, a leitura correta é
que a capacidade, e não o volume, era o limite. Oito mil células ainda são
10,4% da grade, escolhidas por caber em memória, não por serem ótimas.
