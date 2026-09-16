# Rodada 2: contexto atmosférico e segunda submissão

Protocolo definido antes da comparação: manter climatologia de 60 anos, treino
desde 1981, semente 20260914 e amostragem de 768 pontos por mês. Acrescentar às
23 entradas anteriores:

- média das anomalias de M, M-1 e M-2, e mudança entre M e M-1;
- médias espaciais das anomalias em 9×9 e 25×25 células de 0,25°;
- produtos de umidade específica pelos ventos u e v.

As médias espaciais usam somente o campo atmosférico daquele mês, com extensão
constante na borda do domínio. Não há filtro temporal que alcance o futuro.
Comparar árvores de 150 e 300 iterações, isoladas e em combinação 50/50 com o
ensemble anterior. Manter as demais configurações das árvores fixas.

Avaliar 2017–18 e 2019–20; confirmar a comparação em 2013–14 e 2015–16.
Selecionar por RMSE agrupado nos quatro blocos, reportando os segundos anos.
São blocos de desenvolvimento; não constituem teste independente após seleção.
2021–22 continua sem avaliação. No treino final, usar alvos até dezembro/2022.

```powershell
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe src/round2.py evaluate --years 2017 2019
.\.venv\Scripts\python.exe src/round2.py evaluate --years 2013 2015
.\.venv\Scripts\python.exe src/round2.py select
.\.venv\Scripts\python.exe src/round2.py verify
.\.venv\Scripts\python.exe src/round2.py final
```

O CSV final preserva a ordem de IDs da primeira submissão aceita pelo Kaggle,
caso o sample oficial não esteja disponível. Nenhum envio automático é feito.
Uma thread permite executar dentro do ambiente restrito do Windows, sem exigir
as permissões adicionais usadas inicialmente para as threads do scikit-learn.
As entradas do teste são alinhadas por mês de origem; dezembro/2022 aparece no
treino e no teste e deve ser contado uma única vez ao construir o histórico.
