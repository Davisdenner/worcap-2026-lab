# Rodada 10 — correção residual da S09

Somente dados oficiais. RMSE local em 144 meses de 2009–2020; não é score do Kaggle.
Referência S09 histórica: **1.780988**.

| Candidata | RMSE | Ganho relativo | Blocos melhores | Anos melhores | Meses melhores | Aprovada |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| residual8_0.25 | 1.777298 | 0.207% | 6/6 | 11/12 | 84/144 | Não |
| residual4_0.25 | 1.778134 | 0.160% | 5/6 | 10/12 | 92/144 | Não |
| residual8_0.5 | 1.778328 | 0.149% | 3/6 | 8/12 | 76/144 | Não |
| residual2_0.25 | 1.778839 | 0.121% | 5/6 | 10/12 | 87/144 | Não |
| residual4_0.5 | 1.778932 | 0.115% | 4/6 | 7/12 | 76/144 | Não |
| residual2_0.5 | 1.779683 | 0.073% | 3/6 | 7/12 | 79/144 | Não |

Selecionada: **nenhuma**.
Se nenhuma passou, não gerar S10 e preservar os envios restantes. Não afrouxar critérios após os resultados.

## Limitações

Os resíduos de treino vêm de previsões com cortes temporais anteriores, e o corretor só usa blocos passados.
A arquitetura da S09 foi escolhida retrospectivamente. Os períodos de desenvolvimento são reutilizados.
2021–2022 já foi consumido nas rodadas 8/9; não é holdout inédito.
Nenhuma chuva oculta de 2023/2024 foi acessada. Nenhum score local garante 1,70 ou liderança.
Nenhum upload foi realizado.

[Protocolo](../../../experiments/ROUND10.md) · [Diagnóstico](diagnostic.json) · [Seleção](selection.json) · [Auditoria](audit.json)

## Decisão desta execução

Melhor candidata: residual8_0.25, ganho relativo 0.207%; mínimo exigido: 0,300%.
Não houve nova pontuação de 2021–2022, treino final, exportação S10 ou upload. S09 permanece a referência.
Diagnóstico histórico: 63,1% do erro quadrático na faixa de 10°S a 15°N, incluindo oceano e terra.
Esse diagnóstico não revela a distribuição dos erros ocultos do teste.
