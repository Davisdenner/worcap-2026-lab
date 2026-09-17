# Rodada 22 — início do treino-base

S12 histórica: 1.770775 mm/dia.
Somente dados oficiais. Períodos reutilizados; sem teste independente.

| Candidata | RMSE | Ganho | Blocos | Anos | Meses | Aprovada |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| start1940_a0.1 | 1.771425 | -0.037% | 3/6 | 4/12 | 65/144 | False |
| start1960_a0.1 | 1.771537 | -0.043% | 2/6 | 4/12 | 67/144 | False |
| start1940_a0.25 | 1.774447 | -0.207% | 0/6 | 3/12 | 56/144 | False |
| start1960_a0.25 | 1.774622 | -0.217% | 1/6 | 3/12 | 62/144 | False |

Selecionada: nenhuma.
Nenhuma confirmação, previsão final, CSV ou upload foi realizado.

## Controle da família-base sem mistura

Os modelos puros, com atributos, amostras e hiperparâmetros iguais, tiveram
RMSE de 1,823403 (início 1981), 1,824310 (1960) e 1,825636 (1940).
Portanto, o histórico anterior não ajudou **esta família de árvores locais**.
Não houve retreino de todos os componentes S12; o resultado não descarta
benefício em PLS, ridge ou outra arquitetura. As misturas acima foram medidas
contra S12 e submetidas ao gate vigente, sem escolher anos favoráveis.

[Protocolo](../../../experiments/ROUND22.md) · [Seleção](selection.json) ·
[Verificação independente](verification.json)
