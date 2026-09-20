# Rodada 20: árvores locais/globais, hipótese 1

Referência S12: RMSE 1.770775491. Somente dados oficiais.

| Candidata | RMSE | Ganho | Blocos | Anos | Meses | Passou |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| global31_dense_a0.1 | 1.770936811 | -0.0091% | 2/6 | 4/12 | 68/144 | False |
| global31_a0.1 | 1.771067115 | -0.0165% | 2/6 | 3/12 | 65/144 | False |
| global15_a0.1 | 1.771255586 | -0.0271% | 2/6 | 4/12 | 67/144 | False |
| local15_a0.1 | 1.771427653 | -0.0368% | 2/6 | 4/12 | 67/144 | False |
| global31_dense_a0.25 | 1.773056889 | -0.1288% | 2/6 | 4/12 | 62/144 | False |
| global31_a0.25 | 1.773454138 | -0.1513% | 2/6 | 3/12 | 61/144 | False |
| global15_a0.25 | 1.773887611 | -0.1757% | 1/6 | 3/12 | 61/144 | False |
| local15_a0.25 | 1.774324212 | -0.2004% | 1/6 | 4/12 | 63/144 | False |

Selecionada: nenhuma.

## Comparações controladas dos modelos individuais

| Mudança | Controle | RMSE novo | RMSE controle | Ganho | Blocos |
| --- | --- | ---: | ---: | ---: | ---: |
| global15 | local15 | 1.820817 | 1.822656 | 0.101% | 4/6 |
| global31 | global15 | 1.819849 | 1.820817 | 0.053% | 5/6 |
| global31_dense | global31 | 1.816897 | 1.819849 | 0.162% | 4/6 |

Os resultados individuais explicam a hipótese; a promoção exige melhora da mistura contra S12.
Critérios de 0,3% e estabilidade preservados. Períodos reutilizados, não teste independente.
Nenhum CSV novo, previsão final ou upload foi autorizado por esta rodada.
[Protocolo](../../../experiments/ROUND20.md) · [Seleção](selection.json) · [Auditoria](audit.json)

Nenhuma candidata aprovada: confirmação e treino final não executados.
