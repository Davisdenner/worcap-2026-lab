# Rodada 6 — memória atmosférica local

Retomada autorizada pelo usuário após informar segundo lugar e líder com
1,72921. Referência pública confirmada: S04, 1,74906. Score de S05 ainda não
informado no início desta rodada. Esses valores não foram verificados na web.

Durante a execução, o usuário confirmou S05 aceita com **1,74613**.
A seleção passa a exigir ganho também sobre S05, além do critério contra S04.
As previsões novas continuam sendo mudanças isoladas sobre S04 para permitir
atribuição do efeito da memória local, sem alterar o treino em andamento.

Hipótese: adicionar à regressão local sazonal a média causal de três meses
das nove variáveis atmosféricas, além do mês mais recente. São 18 atributos
locais, ajustados na mesma janela sazonal circular de cinco meses.
Médias, escalas, interceptos e regressões usam apenas o treino de cada bloco.
Nenhuma precipitação do período previsto entra como atributo.

Busca delimitada antes de avaliar: penalidades 0,3 e 3; substituição de metade
ou todo o componente local sazonal de S04. Quatro candidatos. Os demais
componentes e os pesos cruzados regionais/sazonais de S04 ficam inalterados.

Blocos: 2013–2014, 2015–2016, 2017–2018, 2019–2020. Exigir RMSE agrupado e
dos segundos anos menores, ganho em pelo menos três blocos e seis anos.
Não usar 1,72921 como alvo de ajuste dos parâmetros. Esses blocos já foram
reutilizados para seleção; não são teste independente. 2021–2022 permanece
sem avaliação. Nenhum upload ou monitoramento automático autorizado.

```powershell
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.venv/Scripts/python.exe -m src.round6 evaluate
.venv/Scripts/python.exe -m src.round6 select
.venv/Scripts/python.exe -m src.round6 final
```

## Resultado

Selecionado `memory_0.3_1`: substituição integral do componente local sazonal
de S04 pelo modelo com memória, ridge 0,3. Não altera o componente regional
nem incorpora a mistura experimental de S05.

| Referência | RMSE agrupado | Segundos anos |
| --- | ---: | ---: |
| S04 | 1,775701 | 1,814847 |
| S05 | 1,775177 | 1,813542 |
| S06 | 1,772788 | 1,811989 |

S06 melhora os quatro blocos e seis dos oito anos contra ambas as referências.
O ganho local sobre S05 é de cerca de 0,135%. Não extrapolar esse percentual
para o público. Não há evidência para prometer superar o líder de 1,72921.

O CSV S06 é gerado com o sample oficial e recusa sobrescrita. Metadados e
SHA-256 ficam ao lado do CSV; relatório de seleção em
`reports/competition/round6/selection.json`. Nenhum upload automático.
