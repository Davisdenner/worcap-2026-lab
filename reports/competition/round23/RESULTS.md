# Rodada 23: saída ampla + detalhe local

S12 histórica: 1.770775 mm/dia.
Somente dados oficiais. Períodos reutilizados; sem teste independente.

| Candidata | RMSE | Ganho | Blocos | Anos | Meses | Aprovada |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| decomposed9_a0.1 | 1.771312 | -0.030% | 2/6 | 4/12 | 75/144 | False |
| decomposed9_a0.25 | 1.779610 | -0.499% | 0/6 | 3/12 | 46/144 | False |

Selecionada: nenhuma.
Nenhuma confirmação, previsão final, CSV ou upload foi realizado.

## Controle da decomposição

Com os mesmos exemplos e parâmetros, o modelo direto puro obteve RMSE
1,823403, e a reconstrução com campo amplo 9×9 mais detalhe obteve 1,947678.
A pequena mistura de 10% melhorou alguns blocos, mas piorou o agregado e só
venceu em 2/6 blocos. A avaliação sempre usou a grade oficial **sem suavizar
o alvo**. Isso reprova esta implementação 9×9; não demonstra que toda
decomposição espacial ou arquitetura multiescala falharia.

[Protocolo](../../../experiments/ROUND23.md) · [Seleção](selection.json) ·
[Verificação independente](verification.json)
