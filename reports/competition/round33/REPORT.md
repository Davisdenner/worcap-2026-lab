# Rodada 33 — taxa de amostragem de células no corretor da S12

**Decisão predefinida: B.** Toda combinação piora a S12.

## Verificação da implementação

O braço de 768 células reproduz a configuração `global31` da Rodada 20 — mesmos 119 atributos, mesma árvore, mesmo alvo — variando apenas o sorteio de células, que usa outra semente.

| Bloco | RMSE Rodada 20 | RMSE Rodada 33 | Diferença |
| --- | ---: | ---: | ---: |
| 2009 | 1.895853 | 1.898745 | +0.002892 |
| 2011 | 1.803950 | 1.808434 | +0.004484 |
| 2013 | 1.732583 | 1.738219 | +0.005636 |
| 2015 | 1.824411 | 1.839576 | +0.015165 |
| 2017 | 1.825267 | 1.834454 | +0.009187 |
| 2019 | 1.833220 | 1.828878 | -0.004342 |

Média absoluta 0.0070, ou 0,39% relativo. A implementação está confirmada contra um resultado histórico do próprio projeto.

Essa tabela tem um segundo uso: ela mede o **piso de ruído amostral** desta família de modelos. Dois modelos idênticos em tudo menos no sorteio de 768 células diferem em cerca de 0,4% no RMSE direto. Propagado para a mistura nas frações 0,10 e 0,25, isso dá algo em torno de 0,1% na métrica de promoção — contra um limiar de 0,3%. A razão sinal-ruído do critério é de aproximadamente três para um, o que é apertado e ajuda a explicar por que resultados marginais nas rodadas anteriores não se sustentaram.

## Resultado

Janela 2011–2020, referência S12 = 1.756391.

| Variante | RMSE | Ganho vs S12 | Blocos | Anos | Meses |
| --- | ---: | ---: | ---: | ---: | ---: |
| s12 | 1.756391 | +0.000% | — | — | — |
| c8192_a0.1 | 1.757366 | -0.055% | 1/5 | 3/10 | 53/120 |
| c768_a0.1 | 1.757627 | -0.070% | 1/5 | 3/10 | 52/120 |
| c8192_a0.25 | 1.760462 | -0.232% | 1/5 | 3/10 | 49/120 |
| c768_a0.25 | 1.761240 | -0.276% | 1/5 | 2/10 | 45/120 |
| c8192_direto | 1.804805 | -2.756% | 0/5 | 0/10 | 25/120 |
| c768_direto | 1.810298 | -3.069% | 0/5 | 0/10 | 22/120 |

As linhas `_direto` são a previsão pura do corretor, sem mistura; são descritivas e não foram candidatas.

## O efeito de volume existe e foi medido

Multiplicar as células por 10,7 melhorou o corretor de 1.810298 para 1.804805, um ganho de **0,303%**. A direção se repete nas três linhas — direta, 0,10 e 0,25 — com o braço maior sempre à frente.

Essa comparação é **pareada**: as 768 células do braço pequeno são as 768 primeiras do mesmo sorteio de 8.192 em cada mês, de modo que os dois modelos veem os mesmos meses e as mesmas células iniciais. O ruído de 0,39% medido contra a Rodada 20 vem de sorteios independentes e não se aplica aqui. Sem o aninhamento, o efeito de 0,303% estaria dentro do ruído e seria ilegível.

## Por que isso não muda a S12

O corretor sozinho está 2,76% atrás da S12. A 0,30% por década de amostragem, usar a grade inteira — 78.561 células, mais 9,6 vezes — renderia cerca de 0,30% adicionais, chegando a −2,45%. Fechar 2,76% exigiria aproximadamente nove décadas adicionais de amostragem, e só existe uma.

A leitura é a prevista na seção de limitações do protocolo: com 31 folhas e 300 iterações a capacidade é fixa, e com 768 células por mês já há cerca de cem observações por folha. Mais dados refinam os valores das folhas, um ganho de segunda ordem, em vez de criar estrutura que o modelo não conseguia representar. **O limite é capacidade do modelo, não volume de dado.**

## Conclusão

**Classe B.** Nenhuma fração melhora a S12; o corretor permanece 2,8% atrás dela mesmo com 10,7 vezes mais células.

A rodada responde sua pergunta de forma quantitativa e encerra a hipótese: o efeito de volume é real, vale 0,3% por década de células, e é uma ordem de grandeza pequeno demais para importar. O caminho logicamente indicado — aumentar folhas junto com os dados — precisaria entregar perto de 3% apenas para o corretor empatar com a S12, e nada medido entre as Rodadas 27 e 33 sugere que exista 3% nessa família.

Os blocos 2009–2020 já foram reutilizados nas Rodadas 19 a 32; o viés de seleção acumulado permanece. Nenhuma S15, CSV, treino final ou submissão foi criado. [Protocolo](../../../experiments/ROUND33.md) · [Decisão](decision.json)
