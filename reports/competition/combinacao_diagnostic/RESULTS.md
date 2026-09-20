# Diagnóstico de combinação — a S10 é a S12 mais ruído ortogonal

**Resultado: oracle de 0,000%.** Não pequeno: zero. E a razão é estrutural,
não numérica.

## A pergunta

As 36 rodadas mexeram todas no mesmo lugar — o corretor que se soma à S11.
Uma direção nunca testada: combinar previsões que já existem. A S10 difere da
S12 em **duas** coisas, a recalibração conjunta de pesos (S10 → S11) e o
corretor não linear (S11 → S12), enquanto todas as variantes testadas nas
rodadas 19 a 36 diferem só na segunda.

Para dois preditores com erros de desvio `e₁`, `e₂` e correlação `ρ`, a
combinação linear ótima tem erro

```
e² = e₁²·e₂²·(1 − ρ²) / (e₁² + e₂² − 2·ρ·e₁·e₂)
```

## Critérios declarados antes de rodar

1. Ganho **oracle** (peso ajustado sabendo o alvo) ≥ 0,3%, o limiar de
   promoção do projeto. Abaixo disso não há o que perseguir.
2. **Estabilidade do peso**: amplitude máxima de 0,5 entre blocos e todos
   dentro de [0, 1,5].
3. Ganho **causal** positivo em ao menos 4 dos 5 blocos avaliados.

Uma versão anterior deste critério encerrava a linha se `ρ ≥ 0,99`. Isso
estava errado e foi corrigido antes da execução: o ganho **não é monótono em
ρ**. Perto da colinearidade a combinação ótima extrapola para fora do
segmento entre os dois modelos — peso 1,774 na S12 em ρ=0,999 — e volta a
"ganhar" muito. É a miragem da Rodada 27 outra vez: ganho disponível apenas
com um peso que não se tem como saber. ρ alto não encerra a linha sozinho e
ρ baixo não a aprova; o que decide é se o peso é estimável.

## Resultado

| bloco | RMSE S12 | RMSE S11 | RMSE S10 | ρ(S12,S10) | peso ótimo | oracle |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2009 | 1,841011 | **1,839800** | 1,887820 | 0,9802 | 1,120 | 1,840458 |
| 2011 | **1,752162** | 1,760803 | 1,771460 | 0,9784 | 0,753 | 1,749817 |
| 2013 | **1,695158** | 1,701708 | 1,724282 | 0,9836 | 1,016 | 1,695151 |
| 2015 | **1,760122** | 1,761861 | 1,803237 | 0,9783 | 1,049 | 1,760027 |
| 2017 | **1,810436** | 1,812522 | 1,836824 | 0,9845 | 0,962 | 1,810396 |
| 2019 | **1,762162** | 1,767824 | 1,803707 | 0,9808 | 1,103 | 1,761795 |

Agregado: RMSE S12 **1,770775**, RMSE S10 **1,805271**, ρ **0,9809**, peso
ótimo na S12 **1,0010**, oracle **1,770775**, ganho **0,000%**.

Causal, com o peso ajustado apenas em blocos anteriores: 1,756391 para
1,757055, ganho **−0,038%**, positivo em 1 de 5 blocos. Os pesos por bloco
ficaram entre 0,753 e 1,120, amplitude 0,367 — estáveis pelo critério 2. A
linha foi encerrada pelo critério 1, antes de a estabilidade importar.

## Por que zero

Dois números coincidem até a quarta casa:

```
ρ(S12, S10)            = 0,9809
RMSE(S12) / RMSE(S10)  = 1,770775 / 1,805271 = 0,98089
```

Isso não é acaso. A condição `w* = 1` é exatamente `ρ = e₁/e₂`, que por sua
vez equivale a `cov(e₁, e₂ − e₁) = 0`:

```
w = (e₂² − ρe₁e₂) / (e₁² + e₂² − 2ρe₁e₂) = 1
  ⟺ e₂² − ρe₁e₂ = e₁² + e₂² − 2ρe₁e₂
  ⟺ ρe₁e₂ = e₁²
  ⟺ ρ = e₁/e₂
  ⟺ cov(e₁, e₂ − e₁) = 0
```

**O erro da S10 é o erro da S12 mais um componente ortogonal a ele.** A S10
não é um modelo diferente que erra em lugares diferentes; é a S12 mais ruído.
Não há informação a extrair porque não existe informação ali. Isso é a
assinatura de uma melhoria estritamente aninhada: a S12 removeu uma
componente do erro e o que sobrou é o que a S10 já tinha.

## Correção de uma estimativa anterior

Antes de executar, este diagnóstico foi motivado por uma tabela construída
sobre os **scores públicos** — S12 em 1,71456 e S10 em 1,71895, separados por
0,26% — que sugeria ganhos de 0,003 a 0,007 na faixa de ρ entre 0,98 e 0,985.
A fórmula estava certa; a premissa, não. Na validação OOF a separação entre
S10 e S12 é **1,95%**, sete vezes maior, e nessa distância ρ = 0,98 não deixa
nada. O ganho da combinação depende tanto da razão `e₂/e₁` quanto de ρ, e
extrapolar a razão do split público de um único ano foi um erro de método.

## Consequência para a escolha das submissões finais

O diagnóstico foi feito para avaliar uma combinação, mas o resultado mais útil
é outro: **a S10 perde para a S12 em 6 de 6 blocos, e a S11 ganha em 1 de 6**
(2009). Uma recomendação anterior de marcar S12 e S10 como submissões finais
foi baseada em distância de previsão e em a S10 ser a única versão sem exceção
autorizada no protocolo — argumentos construídos antes de os resultados por
bloco serem consultados. Os resultados apontam o contrário, e agora com
explicação estrutural para o porquê. O par escolhido é **S12 e S11**.

## Validação

O diagnóstico reproduziu dois números registrados independentemente antes
dele: **1,770775** para a S12 nos seis blocos de desenvolvimento, idêntico ao
do [relatório da Rodada 17](../round17_experimental/RESULTS.md), e
**1,756391** no subconjunto de avaliação, idêntico à baseline da
[Rodada 36](../round36/REPORT.md).

Somente dado oficial. Nenhum modelo treinado, nenhum alvo de teste lido,
nenhum CSV gerado, nenhuma submissão criada.
[combinacao.json](combinacao.json) · [script](../../../scripts/diag_combinacao.py)
