# Diagnóstico de combinação: a S10 é a S12 mais ruído ortogonal

**Resultado: oracle de 0,000%.** Não pequeno: zero. E a razão é estrutural,
não numérica.

## A pergunta

As 36 rodadas mexeram todas no mesmo lugar, que é o corretor somado à S11.
Uma direção nunca testada: combinar previsões que já existem. A S10 difere da
S12 em **duas** coisas, a recalibração conjunta de pesos (S10 para S11) e o
corretor não linear (S11 para S12), enquanto todas as variantes testadas nas
rodadas 19 a 36 diferem só na segunda.

A ideia por trás de combinar dois modelos é simples: se eles erram em lugares
diferentes, a média dos dois erra menos que qualquer um. Formalmente, para
dois preditores com erros de desvio `e₁`, `e₂` e correlação `ρ`, a combinação
linear ótima tem erro

```
e² = e₁²·e₂²·(1 − ρ²) / (e₁² + e₂² − 2·ρ·e₁·e₂)
```

Quanto menor a correlação entre os erros, mais a combinação ganha. O papel
deste diagnóstico é medir essa correlação em vez de supô-la.

## Critérios declarados antes de rodar

1. Ganho **oracle**, com o peso ajustado sabendo o alvo, de pelo menos 0,3%,
   que é o limiar de promoção do projeto. Abaixo disso não há o que
   perseguir, porque o resultado causal nunca supera o próprio oracle.
2. **Estabilidade do peso**: amplitude máxima de 0,5 entre blocos, e todos
   dentro do intervalo de 0 a 1,5.
3. Ganho **causal**, com o peso ajustado apenas em blocos anteriores,
   positivo em ao menos 4 dos 5 blocos avaliados.

Uma versão anterior deste critério encerrava a linha se `ρ ≥ 0,99`. Corrigi
isso antes de executar, porque estava errado: o ganho **não é monótono em
ρ**. Perto da colinearidade, a combinação ótima extrapola para fora do
segmento entre os dois modelos, com peso 1,774 na S12 quando `ρ = 0,999`, e
volta a "ganhar" muito. É a miragem da Rodada 27 outra vez, ou seja, ganho
disponível apenas com um peso que não se tem como saber. Correlação alta não
encerra a linha sozinha e correlação baixa não a aprova; o que decide é se o
peso é estimável.

## Resultado

| bloco | RMSE S12 | RMSE S11 | RMSE S10 | ρ(S12,S10) | peso ótimo | oracle |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2009 | 1,841011 | **1,839800** | 1,887820 | 0,9802 | 1,120 | 1,840458 |
| 2011 | **1,752162** | 1,760803 | 1,771460 | 0,9784 | 0,753 | 1,749817 |
| 2013 | **1,695158** | 1,701708 | 1,724282 | 0,9836 | 1,016 | 1,695151 |
| 2015 | **1,760122** | 1,761861 | 1,803237 | 0,9783 | 1,049 | 1,760027 |
| 2017 | **1,810436** | 1,812522 | 1,836824 | 0,9845 | 0,962 | 1,810396 |
| 2019 | **1,762162** | 1,767824 | 1,803707 | 0,9808 | 1,103 | 1,761795 |

Agregado: RMSE da S12 **1,770775**, RMSE da S10 **1,805271**, correlação
**0,9809**, peso ótimo na S12 **1,0010**, oracle **1,770775**, ganho
**0,000%**.

Um peso ótimo de 1,0010 significa que a combinação ideal coloca todo o peso na
S12 e praticamente nada na S10. A combinação ótima *é* a S12 sozinha.

No teste causal, com o peso ajustado apenas em blocos anteriores, o RMSE foi
de 1,756391 para 1,757055, um ganho de **−0,038%**, positivo em 1 de 5 blocos.
Os pesos por bloco ficaram entre 0,753 e 1,120, com amplitude de 0,367, o que
é estável pelo critério 2. A linha foi encerrada pelo critério 1, antes de a
estabilidade chegar a importar.

## Por que zero

Dois números coincidem até a quarta casa decimal:

```
ρ(S12, S10)            = 0,9809
RMSE(S12) / RMSE(S10)  = 1,770775 / 1,805271 = 0,98089
```

Isso não é acaso. A condição para que o peso ótimo seja exatamente 1 é
`ρ = e₁/e₂`, que por sua vez equivale a dizer que a diferença entre os erros é
descorrelacionada do erro menor:

```
w = (e₂² − ρe₁e₂) / (e₁² + e₂² − 2ρe₁e₂) = 1
  ⟺ e₂² − ρe₁e₂ = e₁² + e₂² − 2ρe₁e₂
  ⟺ ρe₁e₂ = e₁²
  ⟺ ρ = e₁/e₂
  ⟺ cov(e₁, e₂ − e₁) = 0
```

Em palavras: **o erro da S10 é o erro da S12 mais um componente ortogonal a
ele.** A S10 não é um modelo diferente que erra em lugares diferentes; é a S12
mais ruído. Não há informação a extrair porque não existe informação ali.

Essa é a assinatura de uma melhoria estritamente aninhada. A S12 removeu uma
componente do erro, e o que sobrou na S10 é justamente o que a S12 já tinha,
acrescido de ruído que a S12 eliminou.

## Correção de uma estimativa anterior

Antes de executar, motivei este diagnóstico com uma tabela construída sobre os
**scores públicos**, com a S12 em 1,71456 e a S10 em 1,71895, separadas por
0,26%. Aquela tabela sugeria ganhos de 0,003 a 0,007 na faixa de correlação
entre 0,98 e 0,985.

A fórmula estava certa; a premissa, não. Na validação OOF a separação entre
S10 e S12 é de **1,95%**, sete vezes maior, e nessa distância uma correlação
de 0,98 não deixa nada. O ganho depende tanto da razão `e₂/e₁` quanto da
correlação, e extrapolar essa razão a partir do split público de um único ano
foi um erro de método.

## Consequência para a escolha das submissões finais

Fiz o diagnóstico para avaliar uma combinação, mas o resultado mais útil é
outro: **a S10 perde para a S12 em 6 de 6 blocos, e a S11 ganha em 1 de 6**,
no bloco de 2009.

Uma recomendação anterior de marcar S12 e S10 como submissões finais foi
baseada em distância entre previsões e em a S10 ser a única versão sem exceção
autorizada no protocolo. Eram argumentos construídos antes de consultar os
resultados por bloco. Os resultados apontam o contrário, e agora com
explicação estrutural para o porquê. O par escolhido é **S12 e S11**.

## Validação

O diagnóstico reproduziu dois números registrados independentemente antes
dele: **1,770775** para a S12 nos seis blocos de desenvolvimento, idêntico ao
do [relatório da Rodada 17](../round17_experimental/RESULTS.md), e
**1,756391** no subconjunto de avaliação, idêntico à baseline da
[Rodada 36](../round36/REPORT.md). Dois números independentes batendo na casa
decimal são a evidência de que o script está medindo o que diz medir.

Somente dado oficial. Nenhum modelo treinado, nenhum alvo de teste lido,
nenhum CSV gerado, nenhuma submissão criada.
[combinacao.json](combinacao.json) · [script](../../../scripts/diag_combinacao.py)
