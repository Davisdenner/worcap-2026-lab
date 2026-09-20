# Segunda submissão: seleção local

RMSE em mm/dia, grade completa. Período reservado 2021 a 2022 não avaliado.

| Modelo | 2013 a 14 | 2015 a 16 | 2017 a 18 | 2019 a 20 | Agrupado | Segundos anos |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| blend_context_300 | 1.724317 | 1.818349 | 1.827790 | 1.807918 | 1.795066 | 1.827499 |
| previous_ensemble | 1.727005 | 1.813265 | 1.832125 | 1.809236 | 1.795863 | 1.828830 |
| blend_context_150 | 1.727864 | 1.818357 | 1.829042 | 1.808987 | 1.796508 | 1.828305 |
| context_300 | 1.726338 | 1.831570 | 1.828495 | 1.812334 | 1.800197 | 1.832381 |
| context_150 | 1.732030 | 1.829301 | 1.829495 | 1.812867 | 1.801375 | 1.832203 |
| clim_60y | 1.750749 | 1.861463 | 1.848138 | 1.847074 | 1.827393 | 1.848494 |

Selecionado: **blend_context_300**.

São resultados de desenvolvimento, utilizados para a seleção; não são scores do Kaggle.
Os atributos de contexto usam média e variação de anomalias de três meses, médias espaciais
em janelas de 9×9 e 25×25 células e produtos de umidade específica por vento.
As transformações e os modelos são ajustados antes de cada bloco; nenhum alvo do bloco entra como atributo.
As árvores mantêm a mesma configuração da rodada anterior, comparando 150 e 300 iterações.
`blend_context` combina 50% do novo modelo e 50% do ensemble anterior.
