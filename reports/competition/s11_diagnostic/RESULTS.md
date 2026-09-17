# Diagnóstico histórico S11 — 2009–2020

Previsões fora do treino, períodos já reutilizados na seleção. Somente dados oficiais.
RMSE: 1.774622; viés médio: 0.027293 mm/dia.

## Faixas de latitude

| Grupo | RMSE | Viés previsão − observado | % do erro quadrático | % das amostras |
| --- | ---: | ---: | ---: | ---: |
| 0:15.01 | 2.7133 | 0.0580 | 47.38% | 20.27% |
| -15:0 | 1.7715 | -0.0145 | 19.86% | 19.93% |
| -60:-30 | 1.1733 | -0.0144 | 17.43% | 39.87% |
| -30:-15 | 1.5564 | 0.1211 | 15.33% | 19.93% |

## Estações

| Grupo | RMSE | Viés previsão − observado | % do erro quadrático | % das amostras |
| --- | ---: | ---: | ---: | ---: |
| MAM | 1.9166 | 0.0056 | 29.16% | 25.00% |
| DJF | 1.9014 | 0.0377 | 28.70% | 25.00% |
| SON | 1.6558 | 0.0409 | 21.76% | 25.00% |
| JJA | 1.6022 | 0.0250 | 20.38% | 25.00% |

## Intensidade observada

| Grupo | RMSE | Viés previsão − observado | % do erro quadrático | % das amostras |
| --- | ---: | ---: | ---: | ---: |
| 10:20 | 3.7153 | -2.1014 | 27.36% | 6.24% |
| 5:10 | 2.2224 | -0.4974 | 24.76% | 15.78% |
| 2:5 | 1.2903 | 0.2121 | 18.20% | 34.43% |
| 20:inf | 9.3936 | -6.6409 | 16.51% | 0.59% |
| 0.5:2 | 1.1726 | 0.6067 | 11.18% | 25.60% |
| 0:0.5 | 0.6012 | 0.2753 | 1.99% | 17.35% |

## Intensidade prevista

| Grupo | RMSE | Viés previsão − observado | % do erro quadrático | % das amostras |
| --- | ---: | ---: | ---: | ---: |
| 5:10 | 2.5939 | 0.0638 | 33.00% | 15.45% |
| 2:5 | 1.4918 | 0.0400 | 29.52% | 41.78% |
| 10:20 | 3.9733 | -0.2457 | 28.54% | 5.69% |
| 0.5:2 | 0.7660 | 0.0576 | 4.43% | 23.78% |
| 20:inf | 7.4590 | 0.8586 | 4.29% | 0.24% |
| 0:0.5 | 0.2305 | -0.0081 | 0.22% | 13.06% |

## Regiões com maior participação no erro

| Grupo | RMSE | Viés previsão − observado | % do erro quadrático | % das amostras |
| --- | ---: | ---: | ---: | ---: |
| lat 0:15, lon -90:-80 | 3.2214 | 0.1402 | 10.23% | 3.11% |
| lat 0:15, lon -40:-30 | 3.1739 | -0.0517 | 9.93% | 3.11% |
| lat 0:15, lon -80:-70 | 3.0021 | 0.3611 | 8.89% | 3.11% |
| lat 0:15, lon -50:-40 | 2.4634 | 0.0556 | 5.98% | 3.11% |
| lat 0:15, lon -30:-25 | 3.0533 | 0.0438 | 4.83% | 1.63% |
| lat -30:-15, lon -60:-50 | 2.1259 | 0.2525 | 4.38% | 3.05% |
| lat -15:0, lon -50:-40 | 2.0986 | 0.1468 | 4.27% | 3.05% |
| lat 0:15, lon -60:-50 | 2.0478 | -0.1416 | 4.14% | 3.11% |
| lat -30:-15, lon -40:-30 | 2.0203 | 0.1284 | 3.96% | 3.05% |
| lat -30:-15, lon -50:-40 | 1.9672 | 0.2181 | 3.75% | 3.05% |

Classes de chuva observada usam o alvo apenas para análise; não são atributos disponíveis na inferência.
Subestimação condicionada a valores observados altos não prova, por si só, que multiplicar todas as previsões melhora o RMSE.
Nenhuma nova candidata ou submissão foi produzida pelo diagnóstico.
