# Modelo de referência ao encerrar a participação

| Papel | Versão | RMSE público informado |
| --- | --- | ---: |
| Controle aprovado na validação histórica | S10 | 1,71895 |
| Melhor resultado público registrado | S12 | 1,71456 |
| Teste posterior | S13 | 1,71461 |

S11 e S12 foram exceções autorizadas ao critério histórico de 0,3%.
S13 também foi exploratória e ficou 0,00005 acima da S12 no público.
A busca por uma sucessora foi até a rodada 36, sem resultado promovível; a
[síntese das rodadas](SINTESE_RODADAS_25_34.md) explica por quê. Os scores públicos são os que obtive
nos envios; o privado e a classificação final permanecem desconhecidos.

- [Método completo, centralizado](METODOLOGIA.md).
- [Reprodução do zero do treino final e inferência](REPRODUCAO.md).
- [Documentação de entrega da S12, Seção 2.8](ENTREGA_S12.md).
- [Encerramento e trajetória](ENCERRAMENTO.md).
- [Protocolo histórico de seleção](../experiments/PROTOCOL.md).
- [Catálogo de versões e hashes](../configs/modelos.json).
- [Registro dos scores públicos](../reports/competition/leaderboard_observations.json).
- [Escopo técnico e pendências formais](CONFORMIDADE.md).

S10/S11 usam somente dados oficiais, sem componentes S07/S08. Nenhuma mudança
de documentação promove uma nova versão. O relato cronológico anterior deste
documento está preservado em `docs/history/antes_da_organizacao_2026-09-16`.
