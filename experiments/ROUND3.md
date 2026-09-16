# Rodada 3: informação regional e sazonalidade

Comparar com a submissão 02 em 2013–14, 2015–16, 2017–18 e 2019–20.
Não acessar os alvos de 2021–22 para avaliação nem usar precipitação de teste.

Hipóteses pré-definidas:

1. Reduzir espacialmente as nove variáveis atmosféricas e ajustar 16 componentes
   principais às anomalias mensais padronizadas, apenas no treino de cada bloco.
   Usar os componentes e interações seno/cosseno do mês-alvo para prever o campo
   de anomalias de chuva com ridge.
2. Ajustar regressões locais diferentes ao longo do ano, usando para cada mês-alvo
   exemplos daquele mês e seus dois vizinhos de cada lado, com distância circular.

Ambas as famílias com penalidades 0,3 e 3 sobre X'X/n. Comparar isoladamente e com
pesos fixos de 25% e 50% em combinação com S02. Selecionar por RMSE agrupado,
exigindo melhora em pelo menos três blocos e no agrupamento dos segundos anos.
Se nenhum candidato atender, não gerar um CSV duplicado ou sabidamente pior.

```powershell
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe src/round3.py prepare
.\.venv\Scripts\python.exe src/round3.py evaluate
.\.venv\Scripts\python.exe src/round3.py select
.\.venv\Scripts\python.exe src/round3.py final
```

A redução espacial é uma operação independente por mês. Sua preparação pode
incluir o teste, mas médias, escalas, PCA e regressões são ajustados exclusivamente
nas linhas anteriores ao bloco. A matriz de alvos de treino só contém meses
anteriores ao bloco. No ajuste final, alvos até dezembro/2022 são permitidos.

Extensão exploratória após observar os resultados individuais: testar também
50% S02 + 25% modos com penalidade 0,3 + 25% sazonal com penalidade 0,3, para
verificar complementaridade. Essa extensão utiliza os mesmos blocos de
desenvolvimento e não deve ser interpretada como um teste independente.
