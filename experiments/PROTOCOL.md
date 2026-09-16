# WORCAP: protocolo de desenvolvimento

## Objetivo e métrica

Prever precipitação média mensal em mm/dia em toda a grade oficial (301 × 261).
O RMSE agrega os erros quadráticos de todos os pontos e meses, sem ponderação
por área ou máscara continental. Essa é a interpretação da descrição fornecida;
o código de avaliação do organizador ainda não foi disponibilizado.

## Separação temporal

| Uso | Meses-alvo | Última chuva observada disponível |
| --- | --- | --- |
| Desenvolvimento 1 | 2013-01 a 2014-12 | 2012-12 |
| Desenvolvimento 2 | 2015-01 a 2016-12 | 2014-12 |
| Desenvolvimento 3 | 2017-01 a 2018-12 | 2016-12 |
| Desenvolvimento 4 | 2019-01 a 2020-12 | 2018-12 |
| Avaliação reservada | 2021-01 a 2022-12 | 2020-12 |
| Competição | 2023-01 a 2024-12 | 2022-12 |

O treino e qualquer ajuste de atributos precedem cada bloco. Para aprender
M → M+1, o último par permitido no treino é novembro → dezembro do ano anterior.
O estado atmosférico de dezembro pode ser usado para prever janeiro, mas seu alvo
não pode entrar no treino. As nove variáveis atmosféricas são atualizadas a cada
mês; os alvos de precipitação do bloco são acessados exclusivamente para pontuar.

Não fazer divisão aleatória de pontos de grade. Não usar os arquivos preparatórios
de precipitação de 2023 em `data/interim`. Não avaliar 2021–2022 nesta primeira
rodada. Uma vez aberto o bloco reservado, ele deixa de ser um teste intocado.

## Rodada inicial

1. Auditar todos os arquivos: coordenadas, meses, valores ausentes, deslocamento
   exato do alvo e consistência entre dezembro/2022 e as entradas do teste.
2. Comparar climatologias por ponto e mês usando todo o passado e janelas de
   60, 40, 30, 20 e 10 anos. Selecionar por RMSE agrupado dos dois blocos de
   desenvolvimento, registrando também cada ano e mês separadamente.
3. Treinar regressão ridge local (nove coeficientes por ponto), desde 1981,
   sobre anomalias das nove variáveis atmosféricas do mês anterior. As médias
   mensais e escalas são ajustadas apenas nas entradas de treino de cada bloco.
   Comparar penalidades 0,1, 1 e 10 sobre X'X/n. Nenhuma chuva do bloco entra
   como atributo. Coeficientes são compartilhados entre as estações nesta rodada.
4. Guardar previsões de desenvolvimento para estudar combinações e comparar
   erros por mês, sem atribuir independência estatística aos pontos espaciais.

Os resultados usados para escolher candidatos são resultados de desenvolvimento,
não uma estimativa final independente. A climatologia é selecionada nos mesmos
blocos; isso deve ser considerado ao interpretar a melhoria posterior.

## Critério de próxima rodada

Priorizar melhorias que apareçam em vários blocos e nos segundos anos. Investigar
degradações mensais, em vez de escolher somente pela média. Introduzir árvores,
contexto espacial e dados externos um de cada vez. Toda fonte externa deve ter
disponibilidade compatível com o instante da previsão e cumprir as regras.

## Execução

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe src/competition.py audit
.\.venv\Scripts\python.exe src/competition.py baselines
.\.venv\Scripts\python.exe src/competition.py ridge
.\.venv\Scripts\python.exe src/atmospheric_trees.py
.\.venv\Scripts\python.exe src/competition.py summarize
```

As entradas vêm exclusivamente de `data/raw`. O cache derivado em
`data/processed/official` ocupa aproximadamente 3,1 GB e evita descomprimir os
NetCDF a cada experimento. Relatórios ficam em `reports/competition`, previsões
locais em `data/processed/validation`. A leitura do modelo é feita em faixas de
latitude para limitar memória. Não há download, autenticação ou submissão nesses
scripts.

### Experimento não linear inicial

HistGradientBoostingRegressor com 150 iterações, 15 folhas e taxa 0,05,
ajustado sobre resíduos da climatologia. Usa localização, mês-alvo cíclico,
climatologia e nove variáveis atmosféricas brutas e como anomalias mensais.
Treino amostra 768 pontos uniformes sem reposição por mês (semente 20260914);
a pontuação usa todos os pontos. Early stopping aleatório está desabilitado.
Testar também média 50/50 com a combinação ridge/climatologia da primeira rodada.

O pacote oficial não contém `sample_submission.csv`. Após o usuário confirmar o
formato, `src/submission.py` permite construir os IDs a partir das coordenadas do
NetCDF: mês-alvo, latitude e longitude, com longitude variando mais rápido. A
ordem não foi comparada com o modelo oficial. Se esse arquivo estiver disponível,
o exportador preserva sua ordem e valida que os IDs cobrem exatamente a grade.

```powershell
.\.venv\Scripts\python.exe src/submission.py --baseline --output submissions/climatologia_60anos.csv
```

Esse comando gera uma referência de climatologia de 60 anos, não o ensemble.
Para previsões de um modelo, usar `--predictions arquivo.nc` contendo a variável
`tp_mm_day` com coordenadas `time`, `lat`, `lon`. CSVs existentes não são
sobrescritos. O exportador verifica o arquivo gravado e salva um relatório JSON.

Atualização de fechamento: S01 foi aceita pelo Kaggle, e S02/S03 preservaram seus
IDs e ordem. O sample oficial continua ausente, mas não bloqueia a exportação.
Os scores e o estado posterior aos envios estão em
`reports/competition/leaderboard_observations.json`.
