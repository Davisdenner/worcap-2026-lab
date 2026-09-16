# Primeira rodada de desenvolvimento

RMSE em mm/dia, grade completa. Menor é melhor. Nenhuma avaliação de 2021–2022 foi executada.

| Modelo | 2017–2018 | 2019–2020 | Agrupado | 2018 | 2020 |
| --- | ---: | ---: | ---: | ---: | ---: |
| half_trees_half_prior | 1.832125 | 1.809236 | 1.820717 | 1.899532 | 1.846897 |
| half_ridge_0.1_clim_60y | 1.833584 | 1.812849 | 1.823246 | 1.895624 | 1.852360 |
| ridge_1_clim_60y | 1.841117 | 1.808887 | 1.825073 | 1.910341 | 1.854523 |
| trees_150 | 1.838864 | 1.815350 | 1.827145 | 1.910265 | 1.851109 |
| half_ridge_1_clim_60y | 1.837198 | 1.819492 | 1.828367 | 1.893989 | 1.859693 |
| ridge_0.1_clim_60y | 1.848211 | 1.812872 | 1.830627 | 1.926847 | 1.858020 |
| ridge_10_clim_60y | 1.844032 | 1.831862 | 1.837957 | 1.899889 | 1.876513 |
| half_ridge_10_clim_60y | 1.844032 | 1.837487 | 1.840763 | 1.893671 | 1.877348 |
| clim_60y | 1.848138 | 1.847074 | 1.847606 | 1.891222 | 1.881994 |
| clim_20y | 1.857508 | 1.841507 | 1.849525 | 1.942204 | 1.870255 |
| clim_30y | 1.853953 | 1.848451 | 1.851204 | 1.920142 | 1.887831 |
| clim_40y | 1.855938 | 1.852266 | 1.854103 | 1.907882 | 1.889409 |
| clim_all | 1.860401 | 1.867259 | 1.863833 | 1.904729 | 1.896300 |
| clim_10y | 1.889086 | 1.885748 | 1.887418 | 1.980437 | 1.948822 |

Melhor candidato nesta rodada: `half_trees_half_prior`.

As escolhas foram feitas nesses mesmos blocos: os números são de desenvolvimento, não de teste independente.
`half_ridge_` representa média simples entre o modelo ridge e a climatologia selecionada.
`half_trees_half_prior` usa 50% árvores + 25% ridge (penalidade 0,1) + 25% climatologia.
As penalidades ridge são aplicadas a X'X/n; `clim_all` usa todo o histórico anterior ao bloco.

## Limitações e próximo experimento

- Apenas dois blocos de desenvolvimento; confirmar a estabilidade em outros anos antes da seleção final.
- Verificar a coluna 2018: a combinação pode melhorar os blocos completos e ainda degradar um segundo ano.
- Ridge local usa relações lineares e coeficientes comuns entre estações; investigar contexto espacial e sazonalidade.
- Não foi utilizada chuva observada de nenhum bloco como entrada, nem dados externos.
- Nenhuma submissão foi enviada. Falta o sample_submission.csv oficial.
- Relatórios JSON/CSV guardam também os 24 RMSE mensais por execução (mensais no JSON).
