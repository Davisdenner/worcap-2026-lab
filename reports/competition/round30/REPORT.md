# Rodada 30: gate espacial convolucional entre S12 e o análogo H4

**Decisão predefinida: D.** Há ganho em algumas capacidades, mas nenhuma atinge simultaneamente a amplitude (≥0,3%) e a estabilidade (≥4/5 blocos, ≥7/10 anos, ≥67/120 meses) exigidas pela classe A.

## Execução

Treinado no Kaggle (GPU Tesla T4), fora do ambiente local (sem CUDA), conforme `experiments/ROUND30_KAGGLE_SETUP.md`. Cinco cortes causais, 2011, 2013, 2015, 2017, 2019, os mesmos `round27.EVAL`, avaliados nos 15.921 pontos do norte de cada mês do bloco de teste. Arquitetura, canais, patch e hiperparâmetros foram congelados em `experiments/ROUND30.md` antes de qualquer resultado; nenhum ajustado após ver a primeira execução.

## Prevalência real vs. prevista

Fração de pontos em que o análogo teve erro quadrático menor que a S12 (real) contra a probabilidade média prevista pela CNN, por corte:

| Bloco | Prevalência real | Prevalência prevista (média) |
| --- | ---: | ---: |
| 2011 | 49,11% | 51,61% |
| 2013 | 47,05% | 49,08% |
| 2015 | 48,01% | 47,84% |
| 2017 | 47,06% | 50,40% |
| 2019 | 45,26% | 43,65% |

A CNN não está sistematicamente enviesada em nenhuma direção, superestima em três cortes e subestima em dois, todos dentro de poucos pontos percentuais.

## Soft gating OOF

Mesma aritmética de soft gating da Rodada 27 (`altered = residual_norte − g·delta`, `g = gmax·P(análogo melhor)`, S12 fora do norte). Janela comparável, 2011 a 2020.

| Método | RMSE global | Ganho vs S12 | Blocos | Anos | Meses |
| --- | ---: | ---: | ---: | ---: | ---: |
| s12 | 1.756391 | +0,000% | - | - | - |
| logistic_base_0.3 (Rodada 27, tabular) | 1.755065 | +0,075% | 4/5 | 6/10 | 67/120 |
| cnn_gate_0.1 | 1.755722 | +0,038% | 5/5 | 8/10 | 71/120 |
| cnn_gate_0.2 | 1.755263 | +0,064% | 4/5 | 8/10 | 70/120 |
| cnn_gate_0.3 | 1.755016 | +0,078% | 4/5 | 8/10 | 67/120 |

Nenhuma das três capacidades passou nas duas exigências simultâneas de A. Nenhuma ficou classificada como estável pelo critério pré-fixado (`stable_gates` vazio).

## Conclusão

**Classe D.** O gate convolucional com patch 15×15 real (sete canais espaciais: S12, análogo H4, S02, modos regionais, `local18`, PLS16 e S09, todos em grade cheia) obteve, no melhor caso (`cnn_gate_0.3`), ganho de 0,078% sobre a S12, estatisticamente indistinguível do melhor gate tabular já obtido na Rodada 27 (0,075%, `logistic_base_0.3`) e muito abaixo do limiar de promoção de 0,3%.

A receptividade espacial explícita (patch 2D em vez de atributos pontuais achatados) não se converteu em ganho adicional mensurável dentro do orçamento testado. Isso não descarta toda arquitetura convolucional, só esta escolha de canais, patch e hiperparâmetros, conforme já registrado como limitação em `experiments/ROUND30.md`, mas é evidência de que o gargalo não é a ausência de contexto espacial bruto: os atributos pontuais já usados nas Rodadas 27 a 28 (incluindo `local_context_7`, um resumo já achatado da vizinhança) pareciam capturar quase toda a informação espacial relevante contida nestes sete canais. Do gap teórico de 8,49% global / 9,00% norte identificado pelo oracle emparelhado da Rodada 27, o melhor gate real segue capturando menos de um décimo de ponto percentual, com ou sem CNN.

Os blocos 2011 a 2020 já foram reutilizados extensivamente (Rodadas 19 a 29); há viés de seleção acumulado. Nenhuma S15, CSV, treino final ou submissão foi criado. [Protocolo](../../../experiments/ROUND30.md).
