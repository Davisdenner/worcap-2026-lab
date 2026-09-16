# Terceira rodada: validação histórica

RMSE em mm/dia, 96 meses na grade completa. 2021–2022 não foi avaliado.

| Modelo | Agrupado | Segundos anos | Blocos melhores que S02 |
| --- | ---: | ---: | ---: |
| joint25_modes_seasonal | 1.779464 | 1.817407 | 4/4 |
| blend50_modes_0.3 | 1.783466 | 1.819911 | 3/4 |
| blend25_modes_0.3 | 1.784366 | 1.818495 | 4/4 |
| blend50_seasonal_0.3 | 1.784523 | 1.823762 | 3/4 |
| blend25_seasonal_0.3 | 1.786912 | 1.822692 | 4/4 |
| blend50_seasonal_3 | 1.787951 | 1.821962 | 3/4 |
| seasonal_3 | 1.790138 | 1.826097 | 2/4 |
| blend25_seasonal_3 | 1.790349 | 1.823524 | 3/4 |
| blend50_modes_3 | 1.791953 | 1.823075 | 2/4 |
| blend25_modes_3 | 1.792026 | 1.823726 | 3/4 |
| submission02 | 1.795066 | 1.827499 | 0/4 |
| seasonal_0.3 | 1.797074 | 1.843436 | 2/4 |
| modes_3 | 1.800695 | 1.831136 | 1/4 |
| modes_0.3 | 1.810965 | 1.853732 | 1/4 |

Selecionado: **joint25_modes_seasonal**.

Resultados usados para seleção, não um teste independente nem previsão do score público.
`modes`: 16 componentes principais de campos atmosféricos regionais e interações sazonais.
`seasonal`: regressão local ajustada em janelas circulares de cinco meses do calendário.
`blend25` e `blend50`: pesos de 25% e 50% do modelo novo, com o restante da submissão 02.
`joint25`: combinação exploratória de 50% S02 + 25% modos (0,3) + 25% sazonal (0,3).