# Rodada 36 — tentativa máxima: persistência estendida, capacidade e histórico

Protocolo registrado antes de calcular qualquer resultado novo. Referência
imutável: S12. Somente dados oficiais. Nenhuma submissão é criada aqui.

## Mudança deliberada de método

As trinta e cinco rodadas anteriores variaram uma coisa por vez. **Esta não.**
Ela combina três alavancas simultaneamente. Se funcionar, não saberemos qual
parte funcionou — é troca consciente de atribuição por magnitude, feita uma
única vez e registrada aqui para não ser confundida com descuido.

## Por que agora

A Rodada 35 produziu o primeiro resultado positivo do ciclo: cinco colunas de
persistência valeram **+0,651%** no corretor direto, medidos de forma pareada,
e inverteram o sinal da mistura de −0,055% para **+0,049%** com 4/5 blocos. A
forma estava certa; o tamanho, não.

A conta que define o alvo: com correlação de erro de 0,979 entre corretor e
S12, a mistura só rende 0,3% quando o corretor chega a cerca de 0,5% da S12,
RMSE perto de 1,765. Saímos de 1,8048, chegamos a 1,7930 — 30% do caminho.
**Faltam cerca de 1,4%.**

## Assimetria estrutural que restringe o desenho

S12 e seus componentes congelados (S02, modos, local18, PLS16, S09) existem
apenas nos seis blocos. Qualquer modelo que os receba como entrada fica
limitado a 144 meses e volta a esbarrar na parede de estimação documentada na
[síntese](../docs/SINTESE_RODADAS_25_34.md). Somente atmosfera e precipitação
existem em 1940–2022.

Daí o desenho: construir o melhor preditor possível **a partir de dado bruto**,
com treino em histórico cheio, e enfrentá-lo com a S12 pela mistura já
estabelecida. A S12 não é modificada, e sua cadeia de reprodução permanece
intacta.

## As três alavancas

**Persistência estendida.** Às cinco colunas da Rodada 35 somam-se três, no
mesmo espírito e escolhidas pelo mecanismo, não pelos resultados por grupo:
`anom_suave15x15` (a suavização venceu no trópico em todos os grupos, e 9×9
era o maior raio testado), `anom_media6` (memória de seis meses, contra os
três atuais) e `anom_ano_anterior` (anomalia no mesmo mês-calendário do ano
anterior ao alvo, índice `o−11`). Total de oito colunas de persistência, 127
atributos.

**Capacidade.** `max_leaf_nodes` de 31 para **255**. A Rodada 33 concluiu que
o limite era capacidade e não volume; `round20.MODELS` nunca testou mais de
31 folhas. Com 3,7 a 7,7 milhões de linhas, `min_samples_leaf=100` continua
sustentável.

**Histórico.** Dois braços, `s1981` e `s1940`. O segundo dobra o volume de
treino; o ERA5 pré-satélite tem qualidade inferior, e o protocolo arbitra.

Tudo o mais é herdado sem alteração: 8.192 células, mesma semente e portanto
mesmo sorteio da Rodada 33, mesmo alvo (observado menos climatologia do
mês-alvo), mesmas frações 0,10 e 0,25, `l2_regularization=10`,
`learning_rate=0.05`, `max_iter=300`, `max_bins=128`.

## Escopo: OOF, dado oficial, sem submissão

A persistência de treino vem do `tp.npy` oficial, que cobre 1940–2022.
**Nenhum dado externo é usado e nenhuma submissão é criada.** Aplicar ao teste
exigiria a chuva observada nas 24 origens e a verificação de consistência de
produto descrita na Rodada 35 — decisão separada e posterior.

## Cortes e causalidade

Seis blocos `round27.YEARS`; avaliação nos cinco de `round27.EVAL` (referência
S12 = 1,756391). Origens exigem índice ≥ 11 por causa de `anom_ano_anterior`.
A persistência é lida em `o`, `o−1`, …, `o−11`, todos anteriores ao alvo
`o+1`. `f.climo` é causal por construção. Nenhum parâmetro é calibrado nos
blocos de avaliação.

## Classificação predefinida

- **A**: alguma fração atinge ganho global >= 0,3% **e** >= 4/5 blocos,
  >= 7/10 anos e >= 67/120 meses. Não promove: exige confirmação 2021–2022,
  `src.round9.passes_gate` e a verificação de produto.
- **D**: há ganho sem amplitude e estabilidade de A.
- **B**: toda fração piora a S12.

Reporta-se também o RMSE direto contra o alvo de **1,765**, que é o número que
decide se a linha continua.

## Limitações reconhecidas antes de ver qualquer resultado

Os blocos 2009–2020 já foram reutilizados nas Rodadas 19 a 35; o viés
acumulado permanece. Três mudanças simultâneas impedem atribuição. Árvores de
255 folhas sobreajustam com mais facilidade e `l2` fica fixo de propósito. O
piso de ruído amostral desta família é 0,39% no RMSE direto, cerca de 0,1% na
métrica de promoção. Se o braço de 1940 piorar, a leitura natural é qualidade
do ERA5 pré-satélite, não ausência de valor no histórico. E mesmo um resultado
de classe A aqui é OOF: não é transferível ao leaderboard sem a verificação de
consistência de produto, que foi o modo de falha da S08.
