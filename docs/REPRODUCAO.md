# Reprodução e operação local

## Ambiente

Usado no dia: Windows, Python 3.11.1, CPU e uma thread. A GPU MX350 de 2 GB não
foi usada para treinar. `requirements.txt` lista dependências diretas;
`requirements-lock-windows.txt` registra as versões instaladas no ambiente ao
fechamento do dia. É um snapshot desse ambiente, não uma instalação limpa já
testada em outro computador.

Para um novo ambiente Windows com Python 3.11, instalar as dependências do lock.
Para o ambiente existente, não há necessidade de reinstalar tudo.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock-windows.txt
```

Em todos os comandos seguintes, usar a raiz do repositório como diretório atual:

```powershell
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
```

## Entradas

Os 12 NetCDF oficiais e o `sample_submission.csv` devem estar em `data/raw`.
O ZIP atualizado de 15/09 contém o sample; os NetCDF são idênticos aos do pacote
anterior preservado em `data/archive`. Download/autenticação não fazem
parte da reprodução local. Os recortes preparatórios em `data/interim` não são
fontes do pipeline atual.

O cache inicial ocupa aproximadamente 3,1 GB. Previsões locais e outros caches
adicionam espaço em disco. Eles não estão no Git e precisam ser regenerados em
um clone novo.

## Conferir o fechamento sem recalcular modelos

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/check_repository.py
```

O segundo comando confere os arquivos locais listados no manifesto contra seus
hashes. Em um clone sem os CSVs ignorados, esses arquivos serão reportados como
ausentes, não como uma falha de modelo. Use `--allow-missing-artifacts` para
verificar somente a estrutura e os metadados nesse caso.

## Reconstrução completa, em diretório de trabalho novo

Não executar a sequência abaixo apenas para conferir os resultados já salvos.
Os CSVs atuais não são sobrescritos; uma reconstrução completa deve ocorrer em
outro clone/cópia com os dados oficiais, sem CSVs de saída preexistentes.

### 1. Auditoria e rodada inicial

```powershell
.\.venv\Scripts\python.exe src/competition.py audit
.\.venv\Scripts\python.exe src/competition.py baselines
.\.venv\Scripts\python.exe src/competition.py ridge
.\.venv\Scripts\python.exe src/atmospheric_trees.py
.\.venv\Scripts\python.exe src/competition.py summarize
.\.venv\Scripts\python.exe src/submission.py --baseline --output submissions/climatologia_60anos.csv
```

### 2. Contexto espacial/temporal e S02

```powershell
.\.venv\Scripts\python.exe src/round2.py evaluate --years 2017 2019
.\.venv\Scripts\python.exe src/round2.py evaluate --years 2013 2015
.\.venv\Scripts\python.exe src/round2.py select
.\.venv\Scripts\python.exe src/round2.py verify
.\.venv\Scripts\python.exe src/round2.py final
```

### 3. Padrões regionais, sazonalidade e S03

```powershell
.\.venv\Scripts\python.exe src/round3.py prepare
.\.venv\Scripts\python.exe src/round3.py evaluate
.\.venv\Scripts\python.exe src/round3.py select
.\.venv\Scripts\python.exe src/round3.py final
```

Há dependências reais: S03 usa as previsões finais da S02; a S02 utiliza o cache
oficial e previsões de desenvolvimento da rodada inicial; o exportador preserva
a ordem dos IDs do CSV anterior. A ordem dos comandos acima contempla isso.

Resultados numéricos devem ser comparados com os relatórios salvos. Não é
garantido que bibliotecas, plataformas ou rotinas numéricas diferentes produzam
arquivos byte a byte idênticos. A conferência de hash serve para os CSVs originais.

## Exportar novamente previsões existentes com outro nome

```powershell
.\.venv\Scripts\python.exe src/submission.py --predictions data/processed/round3/submission_03_predictions.nc --template data/raw/sample_submission.csv --output submissions/submission_03_reexport.csv
```

Isso não treina modelos nem envia ao Kaggle. Não altera a referência S03 atual.

## Atualizar inventários intencionalmente

```powershell
.\.venv\Scripts\python.exe scripts/snapshot_environment.py
.\.venv\Scripts\python.exe scripts/check_repository.py --refresh-manifest
```

O refresh registra somente submissões já presentes nas observações públicas e
recusa hashes divergentes dos metadados de geração que contenham hash. O snapshot
do ambiente deve ser atualizado apenas após uma alteração intencional das
dependências. Não há tokens nos comandos ou nos arquivos de configuração.
