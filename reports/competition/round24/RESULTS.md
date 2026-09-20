# Rodada 24: transporte de umidade de 850 hPa

S12 histórica: 1.770775 mm/dia.
Somente dados oficiais. Períodos reutilizados; sem teste independente.

| Candidata | RMSE | Ganho | Blocos | Anos | Meses | Norte | Aprovada |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| transporte_lag_norte_b0.5 | 1.770637 | 0.008% | 6/6 | 10/12 | 89/144 | 2.7073 | False |
| transporte_lag_global_b0.5 | 1.770645 | 0.007% | 6/6 | 8/12 | 82/144 | 2.7073 | False |
| convergencia_norte_b0.5 | 1.770698 | 0.004% | 4/6 | 9/12 | 81/144 | 2.7074 | False |
| transporte_lag_norte_b0.25 | 1.770702 | 0.004% | 6/6 | 10/12 | 89/144 | 2.7075 | False |
| transporte_lag_global_b0.25 | 1.770705 | 0.004% | 6/6 | 9/12 | 84/144 | 2.7075 | False |
| convergencia_global_b0.5 | 1.770712 | 0.004% | 5/6 | 8/12 | 79/144 | 2.7074 | False |
| convergencia_norte_b0.25 | 1.770734 | 0.002% | 5/6 | 10/12 | 83/144 | 2.7075 | False |
| convergencia_global_b0.25 | 1.770740 | 0.002% | 5/6 | 9/12 | 80/144 | 2.7075 | False |

Selecionada: nenhuma.
Nenhuma confirmação, previsão final, CSV ou upload foi realizada.

## Ablação controlada

Os três corretores usam as mesmas amostras OOF, 23 atributos originais e
parâmetros da S12. Com substituição integral da correção dentro da fórmula
da S12 (apenas diagnóstico, não candidata registrada), os RMSE foram:

| Atributos adicionais | RMSE | Blocos melhores que só produtos |
| --- | ---: | ---: |
| q·u, q·v | 1,770647 | controle |
| produtos + convergência de M | 1,770679 | 2/6 |
| convergência + lags e q a montante | 1,770558 | 5/6 |

Há um sinal pequeno nos lags além dos produtos, mas a melhor **candidata
predefinida** ganhou só 0,0078% da S12, cerca de 38 vezes menos que o mínimo
de 0,3%. Seu RMSE no norte passou de 2,707666 para 2,707290 mm/dia;
isso não basta para alterar substancialmente o RMSE global. Como os blocos
foram reutilizados, a estabilidade histórica não é confirmação independente.
Não aumentar o peso retrospectivamente para tentar satisfazer o limiar.

[Protocolo](../../../experiments/ROUND24.md) · [Seleção](selection.json) ·
[Verificação integral](verification.json)
