# Estado atual do modelo

| Papel | Versão | RMSE público informado |
| --- | --- | ---: |
| Controle aprovado na validação histórica | S10 | 1,71895 |
| Melhor resultado público registrado | S11 | 1,71718 |

S11 é uma exceção autorizada, não uma candidata aprovada pelos critérios.
Seu ganho histórico foi aproximadamente 0,041%, abaixo dos 0,3% exigidos,
com melhora em 4/6 blocos e 6/12 anos. O critério continua ativo.
Os scores públicos são relatos do usuário; o privado permanece desconhecido.

- [Método completo, centralizado](METODOLOGIA.md).
- [Reprodução do zero do treino final e inferência](REPRODUCAO.md).
- [Política vigente de seleção](../experiments/PROTOCOL.md).
- [Catálogo de versões e hashes](../configs/modelos.json).
- [Registro dos scores públicos](../reports/competition/leaderboard_observations.json).
- [Escopo técnico e pendências formais](CONFORMIDADE.md).

S10/S11 usam somente dados oficiais, sem componentes S07/S08. Nenhuma mudança
de documentação promove uma nova versão. O relato cronológico anterior deste
documento está preservado em `docs/history/antes_da_organizacao_2026-09-16`.
