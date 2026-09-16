# WORCAP: protocolo de desenvolvimento

## Referência atual — S10, público 1,71895

Somente dados oficiais. Composição, resultados, hashes e limitações reunidos
em [S10_BASELINE.md](../docs/S10_BASELINE.md). CSV, modelos e snapshots de geração
devem ser preservados. A rodada15 testa recalibração conjunta com pesos causais
e protocolo próprio; não altera a referência pública sem novo resultado confirmado.
2021–2022 já foi utilizado e não é holdout inédito. Os experimentos anteriores
e critérios antigos abaixo são histórico, não autorizações para retreinar.

## Histórico — retorno público da S09

**S09, público 1,72957**, informado pelo usuário, passa a ser a referência para
as próximas candidatas: 75% S06 + 25% PLS16, apenas dados oficiais. Nenhum
novo experimento foi iniciado com o relato do score. A restrição abaixo continua
vigente; as menções à S06 registram a referência anterior à rodada 9.

## Restrição vigente — somente dados fornecidos pela organização

Por decisão explícita do usuário após S08, as próximas candidatas devem usar
exclusivamente os arquivos oficiais e atributos derivados deles. Não usar NOAA
ou outras fontes externas, nem modelos pré-treinados em dados externos.
Também não usar previsões, resíduos, pseudoalvos ou combinações de S07/S08
como entradas ou base de correção: essas versões incorporam informação externa.
Bibliotecas de software não são fontes de dados; seu uso continua sujeito às licenças.

A referência compatível passa a ser **S06, público 1,74505**. S07 (1,73550)
continua sendo o melhor resultado histórico registrado, mas não é a base da
nova linha restrita. Preservar arquivos e scores anteriores para rastreabilidade;
esta decisão não declara irregularidade nem altera submissões já enviadas.

O próximo experimento proposto é a correção não linear de S06, com previsões
históricas fora do treino, atmosfera local/regional e memória causal derivadas
somente dos arquivos oficiais. Verificar a proveniência de cada cache utilizado.
Nenhuma chuva oculta de 2023/2024 pode entrar no desenvolvimento, inclusive
arquivos preparatórios fora do pacote oficial. 2021–2022 já foi avaliado.
Esta atualização registra a restrição; não executa treino ou upload.

## Atualização após a rodada 8

O bloco 2021–2022 foi aberto **uma única vez** para comparar S07 e a candidata
S08 já congelada. S08 melhorou o RMSE agregado e os dois anos individualmente.
Ele não é mais um holdout intocado para futuras rodadas. Não ajustar modelos
nesse período e continuar chamando seu resultado de teste independente.
Protocolo e valores: [rodada 8](ROUND8.md).
O texto abaixo preserva o protocolo original das primeiras rodadas.

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
