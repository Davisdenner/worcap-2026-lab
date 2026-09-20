# Rodada 35 — persistência de precipitação como atributo do corretor

Protocolo registrado antes de calcular qualquer resultado novo. Referência
imutável: S12. Nenhuma submissão é criada aqui.

## Por que esta hipótese

O organizador esclareceu o critério de validade: para prever o mês T vale
qualquer dado que em tese estaria disponível até o fim de T−1, incluindo
dados externos, escala diária ou semanal, índices climáticos e informação de
fora do domínio; o que não vale é usar o próprio mês T para estimar T.

Isso libera a precipitação observada em T−1 como preditor — e o pipeline
**nunca a usou**. `round2.Features.matrix` tem 55 colunas sem nenhuma de
chuva, e `round6.local_memory` usa as nove variáveis *atmosféricas* em três
defasagens, como o próprio docstring diz. Em trinta e quatro rodadas a
precipitação apareceu apenas como rótulo.

O [diagnóstico de persistência](../reports/competition/persist_diagnostic/RESULTS.md)
mediu o tamanho da lacuna com dado exclusivamente oficial: R² conjunto de
**0,0281** na faixa tropical e 0,0303 no agregado, contra um limiar declarado
de 0,006 — cinco vezes acima. O teto implícito de RMSE é de 1,4% a 1,5%.

Três propriedades desse diagnóstico sustentam a hipótese. As versões
suavizadas espacialmente vencem no trópico (MAM/lat≥−10: 0,154 sem suavizar,
0,164 com 9×9), o que é a assinatura de um sinal fisicamente coerente e não
de ruído. O grupo de maior R², MAM/lat≥−10 com 0,0494, é o que carrega a
maior fatia isolada do erro quadrático, 18,9%. E uma equipe pública da mesma
competição reportou a média 3×3 da anomalia de precipitação como o atributo
mais importante do modelo dela.

**Esta é a primeira hipótese do ciclo que não esbarra na parede de
estimação.** Persistência não é uma correção calibrada nos cinco blocos de
avaliação: é um atributo do modelo base, ajustado em 335 a 455 meses de
treino.

## Desenho: uma única variável

Reproduz a configuração `c8192` da Rodada 33 sem nenhuma alteração — mesmas
8.192 células, mesma semente e portanto **exatamente o mesmo sorteio**, mesma
árvore de 31 folhas, mesmo alvo, mesmas frações 0,10 e 0,25 — e acrescenta
cinco colunas, passando de 119 para 124 atributos:

| coluna | definição, na origem `o`, em anomalia contra `f.climo` |
| --- | --- |
| `anom_o` | anomalia de precipitação em `o` |
| `anom_media3` | média das anomalias em `o`, `o−1`, `o−2` |
| `anom_suave3x3` | anomalia em `o` com filtro uniforme 3×3 |
| `anom_suave9x9` | anomalia em `o` com filtro uniforme 9×9 |
| `tendencia` | anomalia em `o` menos anomalia em `o−1` |

As cinco são exatamente as declaradas no diagnóstico, antes de ver qualquer
resultado. Nenhuma foi escolhida depois, e nenhuma foi descartada — incluir
todas evita seleção de atributos sobre os blocos de avaliação.

O braço de 119 atributos da Rodada 33 é o controle pareado: mesmos meses,
mesmas células, mesma árvore, diferindo só pelas cinco colunas.

## Escopo: validação OOF, sem submissão

No treino e nos seis blocos causais a persistência vem do `tp.npy` oficial,
que cobre 1940–2022. **Esta rodada não usa nenhum dado externo e não produz
submissão.**

Aplicar o atributo ao teste exigiria a precipitação observada nas 24 origens
de 2022-12 a 2024-11, das quais só a primeira está no pacote oficial. Essa é
uma decisão separada, posterior, e condicionada a uma verificação de
consistência de produto: baixar dezembro de 2022 da fonte externa e comparar
com `tp[-1]`, que a competição entrega como `tp_ultima_obs`. Se o produto, a
grade ou as unidades divergirem, o atributo mede coisas diferentes no treino
e no teste e o ganho não se realiza — foi o modo de falha da S08, que passou
na validação e piorou no leaderboard.

## Cortes e causalidade

Seis blocos `round27.YEARS`; avaliação nos cinco de `round27.EVAL`
(2011–2020, referência S12 = 1,756391). O treino usa `Features.idx`, que
garante que o alvo `o+1` precede o início do bloco. A persistência é lida em
`o`, `o−1` e `o−2`, todos anteriores ao alvo. `f.climo` já é causal por
construção. Nenhum parâmetro é calibrado nos blocos de avaliação.

## Classificação predefinida

- **A**: alguma fração atinge ganho global >= 0,3% **e** >= 4/5 blocos,
  >= 7/10 anos e >= 67/120 meses melhores. Não promove automaticamente:
  exige confirmação 2021–2022 e `src.round9.passes_gate`, e além disso a
  verificação de consistência de produto descrita acima.
- **D**: há ganho, sem amplitude e estabilidade de A.
- **B**: toda fração piora a S12.

A linha `_direto` é descritiva e não é candidata.

## Limitações reconhecidas antes de ver qualquer resultado

Os blocos 2009–2020 já foram reutilizados nas Rodadas 19 a 34. O teto de 1,4%
do diagnóstico pressupõe exploração linear perfeita do resíduo; uma árvore
realiza menos, ainda que possa ganhar em interações com os atributos
atmosféricos. O piso de ruído amostral desta família é 0,39% no RMSE direto,
cerca de 0,1% na métrica de promoção. O ganho medido aqui é OOF e não é
transferível ao leaderboard sem a verificação de produto; enquanto ela não
for feita, um resultado de classe A autoriza apenas a rodada de confirmação,
nunca um envio.
