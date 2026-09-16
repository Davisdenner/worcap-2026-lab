# Índice dos resultados

Melhor pública informada: **S11, 1,71718**, uma exceção autorizada aos critérios.
S10, 1,71895, permanece como controle aprovado. Veja a
[metodologia central](../docs/METODOLOGIA.md) e o
[guia de reprodução](../docs/REPRODUCAO.md).

| Registro | Período de avaliação | Finalidade |
| --- | --- | --- |
| [Reprodução S10/S11](reproducao/README.md) | Treino final e inferência 2023–2024 | CSVs e previsões idênticos aos originais; 72 testes |
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
As seleções antigas são históricas. S10 é o controle aprovado; S11 é a melhor
pública, sem aprovação retroativa. A exceção está documentada nos
[resultados da S11](competition/round15_experimental/RESULTS.md).

O relatório inicial permanece como registro daquela etapa. Sua referência à
ausência de submissões descreve o momento da geração. Para o estado atual,
consultar o registro público e [submissions/README.md](../submissions/README.md).

2021–2022 já foi avaliado e reutilizado nas confirmações. Os resultados locais
e arquiteturas foram usados para seleção; não são uma estimativa independente
do privado. Relatos antigos de holdout intocado descrevem apenas aquele momento.
