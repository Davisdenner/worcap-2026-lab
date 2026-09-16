# Índice dos resultados

Referência pública atual: **S10, 1,71895**, conforme retorno do usuário.
[Composição e resultados consolidados](../docs/S10_BASELINE.md).

| Registro | Período de avaliação | Finalidade |
| --- | --- | --- |
| [Auditoria](competition/audit.json) | Arquivos oficiais | Integridade, coordenadas e alinhamento |
| [Atualização 15/09](competition/update_2026-09-15.json) | ZIP atualizado | NetCDF idênticos e sample compatível com S01–S03 |
| [Rodada inicial](competition/RESULTS.md) | 2017–2020, 48 meses | Climatologias, ridge anual e árvores locais |
| [Rodada 2](competition/round2/RESULTS.md) | 2013–2020, 96 meses | Contexto espacial/temporal e seleção da S02 |
| [Rodada 3](competition/round3/RESULTS.md) | 2013–2020, 96 meses | Padrões regionais, sazonalidade e seleção da S03 |
| [Scores públicos](competition/leaderboard_observations.json) | 2023 | Scores informados após envio ao Kaggle |
| [Geração S10](competition/round11/RESULTS.md) | 2009–2020; confirmação 2021–2022 reutilizada | Modelo tropical fino aprovado |
| [Correção residual](competition/round12/RESULTS.md) | 2009–2020 | Não promovida |
| [Kernel tropical](competition/round13/RESULTS.md) | 2009–2020 | Não promovido |
| [Atributos físicos](competition/round14/RESULTS.md) | 2009–2020 | Não promovidos |
| [Recalibração conjunta](competition/round15/RESULTS.md) | 2009–2020 | Pesos causais, não promovida |

Cada rodada mantém JSON/CSV com métricas agregadas e por ano; os JSON incluem
RMSE mensal. Arquivos `selection.json` registram a decisão daquela rodada.
As seleções antigas são históricas; a referência atual é S10.

O relatório inicial permanece como registro daquela etapa. Sua referência à
ausência de submissões descreve o momento da geração. Para o estado atual,
consultar o registro público e [submissions/README.md](../submissions/README.md).

2021–2022 já foi avaliado e reutilizado nas confirmações. Os resultados locais
e arquiteturas foram usados para seleção; não são uma estimativa independente
do privado. Relatos antigos de holdout intocado descrevem apenas aquele momento.
