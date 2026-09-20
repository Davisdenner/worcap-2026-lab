# Rodada 14: transporte e convergência de umidade

Somente dados oficiais; RMSE em toda a grade de 2009 a 2020, não score Kaggle.
Referência histórica S10: 1.775343; público informado 1,71895.

| Candidata | RMSE | Ganho | Blocos | Anos | Meses | Aprovada |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| fluxconv32 | 1.775455 | -0.006% | 3/6 | 5/12 | 67/144 | False |
| flux32 | 1.775715 | -0.021% | 2/6 | 7/12 | 65/144 | False |
| fluxconv16 | 1.775737 | -0.022% | 1/6 | 3/12 | 70/144 | False |
| flux16 | 1.775808 | -0.026% | 2/6 | 3/12 | 64/144 | False |

Selecionada: nenhuma.
Novos atributos físicos concatenados à representação S10; PLS32 reajustado e pesos preservados.
Produtos de médias mensais em um nível são proxies, não fluxos reais integrados na coluna.
Máscara de pressão e vizinhança evita usar indicadores abaixo do terreno; unidades ERA5 assumidas.
Controle S10 reproduzido. Arquitetura e períodos reutilizados; 2021 a 2022 não é holdout inédito.
Nenhuma chuva oculta 2023/2024, fonte externa, upload ou garantia de 1,70.

[Protocolo](../../../experiments/ROUND14.md) · [Seleção](selection.json) · [Auditoria](audit.json)

Sem nova confirmação, treino final ou CSV. S10 preservada e nenhum envio consumido.
