# Rodada 13: componente tropical não linear

Somente dados oficiais; RMSE em toda a grade de 2009 a 2020, não score Kaggle.
Referência histórica S10: 1.775343; público informado 1,71895.

| Candidata | RMSE | Ganho | Blocos | Anos | Meses | Aprovada |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| rbf_h2_a0.3 | 1.773881 | 0.082% | 4/6 | 7/12 | 86/144 | False |
| rbf_h0.5_a0.3 | 1.776199 | -0.048% | 3/6 | 5/12 | 70/144 | False |
| rbf_h2_a3 | 1.777894 | -0.144% | 0/6 | 2/12 | 56/144 | False |
| rbf_h0.5_a3 | 1.778787 | -0.194% | 1/6 | 2/12 | 63/144 | False |

Selecionada: nenhuma.
Regressão de saída tropical substituída por kernel; pesos, PLS32 e representação S10 preservados.
Controle linear reproduzido. Parâmetros e mínimo de ganho 0,3% fixados antes dos resultados.
Arquitetura e períodos reutilizados; 2021 a 2022 não é holdout inédito.
Nenhuma chuva oculta 2023/2024, fonte externa, upload ou garantia de 1,70.

[Protocolo](../../../experiments/ROUND13.md) · [Seleção](selection.json) · [Auditoria](audit.json)

Sem nova confirmação, treino final ou CSV. S10 preservada e nenhum envio consumido.
