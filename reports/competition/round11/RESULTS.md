# Rodada 11: resolução atmosférica tropical

Somente dados oficiais; RMSE da grade completa em 2009 a 2020, não score Kaggle.
Referência S09: 1.780988.

| Candidata | RMSE | Ganho | Blocos | Anos | Meses | Aprovada |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| fine32_0.25 | 1.775343 | 0.317% | 6/6 | 9/12 | 85/144 | True |
| fine16_0.5 | 1.776240 | 0.267% | 6/6 | 8/12 | 82/144 | False |
| fine16_0.25 | 1.776491 | 0.252% | 6/6 | 9/12 | 88/144 | False |
| coarse16_0.25 | 1.776961 | 0.226% | 6/6 | 10/12 | 86/144 | False |
| fine32_0.5 | 1.777544 | 0.193% | 4/6 | 7/12 | 77/144 | False |

Selecionada: fine32_0.25.
coarse16_0.25 é controle diagnóstico, não elegível para exportação.
Critérios definidos antes dos resultados; mínimo de ganho agregado de 0,3%.
Períodos e arquitetura S09 reutilizados; 2021 a 2022 não é holdout novo.
Nenhuma chuva oculta de 2023/2024 foi acessada. Nenhum upload ou garantia de 1,70.

[Protocolo](../../../experiments/ROUND11.md) · [Seleção](selection.json) · [Auditoria](audit.json)

Confirmação reutilizada 2021 a 2022: 1.834766 → 1.830283; aprovada: True.
