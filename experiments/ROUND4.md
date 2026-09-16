# Rodada 4 — memória atmosférica e pesos regionais

Data: 15/09/2026. Referência pública preservada: S03, RMSE 1,76467.

## Protocolo

- Blocos de desenvolvimento: 2013–2014, 2015–2016, 2017–2018 e 2019–2020.
- Nenhuma avaliação de 2021–2022. Esses anos entram apenas no treino final.
- Mesma PCA de 16 componentes, ajustada exclusivamente antes de cada bloco.
- Três representações: estado atual + média de três meses; três estados
  consecutivos; estado atual + média de seis meses + diferença de dois meses.
- Duas penalizações ridge (0,3 e 3). Substituição de metade ou de todo o
  componente de modos regionais de S03 (pesos 0,125 e 0,25).
- Promoção: menor RMSE total e nos segundos anos, ganho em pelo menos três
  dos quatro blocos e seis dos oito anos. Doze candidatos, sem busca adicional.
- Nenhuma precipitação observada no bloco previsto é usada como entrada.

## Seleção

A representação escolhida combina o estado atual com a média dos últimos
três meses, ridge 0,3, substituindo os 25% de modos regionais de S03.
RMSE de desenvolvimento: **1,776612**, contra **1,779464** de S03.

Uma segunda experiência ajusta a mistura de S02, modos com memória e regressão
local sazonal por três faixas de latitude (cortes em -30 e -10 graus) e quatro
estações (DJF, MAM, JJA, SON). Não há máscara de terra nem ponderação por área.
Pesos somam um, ficam entre 0,1 e 0,7 e são penalizados em direção à mistura
original [0,5; 0,25; 0,25], com intensidade fixa 0,5.

Cada bloco é avaliado com pesos estimados nos outros três blocos completos.
O resultado foi **1,775701**, com segundos anos **1,814847**, e melhora contra
a candidata sem calibração em três blocos e seis anos. A calibração foi promovida.
Para a submissão, os pesos são ajustados nos quatro blocos de desenvolvimento.

**Limitação:** essa calibração é retrospectiva, não uma validação temporal
progressiva. O candidato-base também foi escolhido nos mesmos blocos. Logo,
esses resultados não são um teste independente nem previsão do score Kaggle.
O período reservado continua intocado. Não há garantia de superar S03 no público.

## Reprodução

Executar na raiz, com caches e artefatos das rodadas anteriores disponíveis:

```powershell
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.venv/Scripts/python.exe -m unittest discover -s tests
.venv/Scripts/python.exe -m src.round4 evaluate
.venv/Scripts/python.exe -m src.round4 select
.venv/Scripts/python.exe -m src.round4 calibrate
.venv/Scripts/python.exe -m src.round4 final
```

O último comando recusa sobrescrever `submissions/submission_04.csv`.
O exportador usa IDs e ordem do sample oficial e relê o CSV inteiro.
Relatórios em `reports/competition/round4`, modelo e previsões em
`data/processed/round4`. O arquivo JSON ao lado do CSV registra pesos,
parâmetros, validação, SHA-256 e situação não enviada.

S01–S03 e seus metadados não foram alterados. Nenhum upload automático.
