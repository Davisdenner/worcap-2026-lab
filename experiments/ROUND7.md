# Rodada 7 — regressão conjunta local e continental

Solicitação: melhorar S06 e preparar S07, com objetivo público de 1,70.
Esse objetivo não é promessa nem critério de ajuste. Referência pública: S06,
1,74505. Referência local: 1,772788.

Hipótese: estimar conjuntamente a precipitação com 18 atributos locais da S06
(atmosfera atual e média de três meses) e oito atributos continentais (os
quatro primeiros componentes da PCA atmosférica e suas médias de três meses).
Os coeficientes locais são ajustados em janela sazonal de cinco meses.

Médias, PCA, escalas, interceptos e regressões usam somente dados anteriores
ao início do bloco previsto. PCA mantém o algoritmo e semente de S04.
Não há entrada de precipitação observada nos blocos de validação ou teste.
São informações oficiais já distribuídas, combinadas de uma forma nova;
nenhum dado externo foi incorporado.

Busca inicial delimitada: ridge 0,3 ou 3; mistura de 25% ou 50% do modelo
conjunto com S06. Quatro candidatos, mesma grade inteira e pesos uniformes
na métrica. Critério: menor RMSE agregado e nos segundos anos, melhor em
pelo menos três blocos e seis anos. Blocos 2013–2014, 2015–2016, 2017–2018,
2019–2020 reutilizados para seleção, não teste independente. 2021–2022
permanece sem avaliação. Não buscar parâmetros pelo score do líder.

```powershell
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.venv/Scripts/python.exe -m src.round7 evaluate
.venv/Scripts/python.exe -m src.round7 select
.venv/Scripts/python.exe -m src.round7 final
```

O exportador usa IDs e ordem do sample oficial. Recusa sobrescrever S07.
S01–S06 preservadas. Nenhum upload automático.

## Extensão: informação oceânica externa

Os quatro candidatos locais/continentais não passaram pelo critério. Foi
então testada uma fonte externa complementar, permitida pelo trecho de regras
enviado pelo usuário: dados públicos igualmente acessíveis e gratuitos.

Fonte: [NOAA CPC, índices mensais ERSSTv5](https://www.cpc.ncep.noaa.gov/data/indices/ersst5.nino.mth.91-20.ascii).
Arquivo imutável: `data/external/ersst5.nino.mth.91-20.ascii`, com URL,
data de obtenção e SHA-256 no JSON adjacente. Snapshot obtido em 15/09/2026.

Usadas apenas temperaturas brutas de Niño 1+2, Niño 3, Niño 4 e Niño 3.4.
Colunas de anomalias publicadas foram ignoradas; as médias mensais são
estimadas dentro de cada treino. O mês oceânico mais recente é **alvo menos
dois meses**; inclui-se também a média causal dos três meses encerrados nessa
data. Não se usa média centrada. Somente datas até outubro/2024 são consumidas.

Limitação: a fonte é uma revisão histórica atual, não um arquivo das versões
disponíveis em cada data de previsão. A defasagem extra não garante uma
simulação de disponibilidade em tempo real. Não foram obtidos alvos de chuva
externos ou usados alvos de validação/teste como atributos.

Esses oito atributos oceânicos complementam os 16 modos atmosféricos, seu
histórico de três meses e interações sazonais. Duas penalidades (0,3 e 3) e
substituição de metade ou todo o componente regional de S06: quatro candidatos
adicionais, oito ao todo. A extensão foi escolhida após os resultados iniciais;
não apresentar a rodada inteira como pré-registrada.

## Resultado e S07

Selecionado **ocean_0.3_1**: mantém S06 e substitui integralmente seu componente
de modos regionais pelo modelo com índices oceânicos, ridge 0,3. Pesos de
mistura regionais/sazonais herdados de S04 não foram reajustados.

| Modelo | RMSE agrupado | Segundos anos |
| --- | ---: | ---: |
| S06 | 1,772788 | 1,811989 |
| S07 | 1,768074 | 1,807901 |

Ganho em quatro blocos e **oito dos oito anos**. Redução local de cerca de
0,266%. O público é desconhecido; não há evidência para prometer 1,70.
O período 2021–2022 continua sem avaliação.

Comandos adicionais após a avaliação inicial:

```powershell
# Apenas na ausência do snapshot, com acesso à rede:
.venv/Scripts/python.exe scripts/download_nino.py
.venv/Scripts/python.exe -m src.round7 ocean
.venv/Scripts/python.exe -m src.round7 select
.venv/Scripts/python.exe -m src.round7 final
.venv/Scripts/python.exe scripts/verify_candidate.py submissions/submission_07.csv data/processed/round7/submission_07_predictions.nc
```

A reprodução exata deve usar o snapshot salvo, não uma versão posterior do site.

## Retorno público posterior

Usuário confirmou **1,73550** para S07, mantendo segundo lugar, com líder em
1,72921. Ganho de 0,00955 (0,5473%) contra S06; diferença restante de 0,00629.
Esses valores são relatos do usuário, não consulta independente ao leaderboard.
S07 passa a ser a referência pública. Os metadados de geração foram preservados;
o resultado posterior está no registro de observações públicas.
