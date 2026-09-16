# Rodada 8 — Atlântico tropical

Retomada autorizada após S07 público 1,73550, segundo lugar e líder informado
1,72921. O objetivo é melhorar; não há garantia de recuperar a liderança.

Hipótese: complementar a atmosfera e o Pacífico de S07 com os índices de
temperatura do Atlântico tropical TNA e TSA da NOAA PSL. Cada índice entra
com o último valor permitido e sua média causal de três meses. O mês mais
recente continua sendo alvo menos dois meses. Não há médias centradas.

Fontes públicas gratuitas:

- [TNA e TSA, descrição NOAA](https://psl.noaa.gov/data/climateindices/list/).
- [TNA mensal](https://psl.noaa.gov/data/correlation/tna.data).
- [TSA mensal](https://psl.noaa.gov/data/correlation/tsa.data).

Os índices usam climatologia 1971–2000, anterior a todos os blocos de avaliação.
Além disso, são recentrados pelas médias mensais de cada treino. Não se usa
precipitação externa ou observada nos blocos previstos. A fonte é uma revisão
histórica atual, não arquivo das publicações em tempo real. Defasagem de dois
meses não elimina essa limitação. Snapshots e SHA-256 preservados em data/external.

Busca definida antes de avaliar: ridge 0,3 e 3, substituição de metade ou todo
o componente oceânico/regional de S07. Quatro candidatos. Demais componentes
e pesos de mistura congelados. Exigir menor RMSE agrupado e nos segundos
anos, ganho em pelo menos três blocos e seis anos. Blocos de desenvolvimento:
2013–2014, 2015–2016, 2017–2018, 2019–2020. São blocos reutilizados para seleção,
não teste independente. 2021–2022 segue sem avaliação.

Antes da comparação, o novo código sem os índices atlânticos deve reproduzir
o componente de S07 no bloco 2013–2014. Tolerância máxima: 0,00002 mm/dia.

```powershell
# Rede necessária somente para obter os snapshots ausentes:
.venv/Scripts/python.exe scripts/download_atlantic.py
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.venv/Scripts/python.exe -m unittest discover -s tests
.venv/Scripts/python.exe -m src.round8 evaluate
.venv/Scripts/python.exe -m src.round8 select
.venv/Scripts/python.exe -m src.round8 holdout
.venv/Scripts/python.exe -m src.round8 final
.venv/Scripts/python.exe scripts/verify_candidate.py submissions/submission_08.csv data/processed/round8/submission_08_predictions.nc
```

O comando final exige aprovação no critério histórico e recusa sobrescrita.
Nenhum upload automático. Scores públicos anteriores e seus arquivos preservados.

## Seleção de desenvolvimento

Selecionada `atlantic_0.3_1`, RMSE **1,765488** contra **1,768074** de S07.
Segundos anos: 1,804932 contra 1,807901. Melhor em quatro blocos e sete anos.
O componente S07 foi reproduzido exatamente: erro máximo zero no bloco 2013.

## Primeira abertura de 2021–2022

Após fixar a candidata, foi decidido avaliar S07 e S08 no bloco reservado.
O protocolo é escrito antes de ler seus alvos para pontuação. Modelos-base
treinados somente até dezembro/2020 (origens até novembro/2020); pesos de
mistura congelados, estimados no desenvolvimento 2013–2020. Nenhum modelo
final treinado até 2022 é usado nessa checagem.

Critério fixo de aprovação: RMSE agrupado menor e RMSE menor em **ambos** os
anos individuais. Se falhar, não gerar S08 como melhoria aprovada. Não ajustar
hiperparâmetros após abrir o período. Uma única candidata é pontuada, além da
referência. Resultado em `reports/competition/round8/holdout_2021_2022.json`.
Após essa leitura, 2021–2022 deixa de ser holdout intocado e não deve ser
apresentado como teste independente para futuras rodadas ajustadas a ele.

## Resultado da checagem reservada

**Aprovada**, sem alteração de parâmetros após a abertura.

| Período | S07 | S08 |
| --- | ---: | ---: |
| 2021–2022 agrupados | 1,837746 | 1,834110 |
| 2021 | 1,832912 | 1,827219 |
| 2022 | 1,842567 | 1,840976 |

Modelos antigos foram reconstruídos com corte em 2021, não reutilizados do
treino final de 2023. A geração final de S08 volta a usar todos os alvos
permitidos até dezembro/2022, sem usar chuva de 2023/2024.
Arquivo: `submissions/submission_08.csv`.

## Retorno público posterior

Usuário informou **1,74606** para S08: piora de **0,01056** (cerca de 0,6085%)
contra S07, 1,73550. O ganho histórico não se transferiu ao público de 2023.
Isso não determina o resultado privado de 2024 nem demonstra por si só a causa
da regressão. Não recalibrar pesos exclusivamente para esse único score.
S07 permanece referência pública. S08 e seus metadados originais preservados.
2021–2022 continua consumido como validação final, não volta a ser intocado.
