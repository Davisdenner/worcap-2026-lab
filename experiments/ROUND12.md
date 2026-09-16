# Rodada 12 — correção residual da S10

Protocolo definido antes dos resultados. Usuário autorizou a rodada e informou
um envio restante hoje; não fazer upload. S10 pública 1,71895, líder informado
1,71488. Esses valores não entram no ajuste dos modelos ou pesos.

Somente dados oficiais. Preservar S10, S09, protocolos e metadados. Não usar
NOAA, S07/S08, data/interim, pesos externos nem chuva oculta de 2023/2024.

## Hipótese e seis candidatas fixas

Resíduo = chuva observada menos previsão histórica S10. A previsão S10 usada
em cada resíduo vem de ajuste com alvos anteriores ao respectivo bloco. Para
prever um bloco, o corretor só aprende com resíduos de blocos já encerrados.
Não treinar sobre resíduos de previsões ajustadas aos próprios alvos.

Entradas: as PCA64 continental e PCA64 tropical fina da S10, do corte externo
correspondente, ajustadas em atmosfera anterior ao corte. Estado atual e média
causal de três meses, com interações sazonais, conforme round11.weather_design.
Refazer escalas das entradas somente nas linhas de treino do corretor.
Alvos: 16 EOFs dos resíduos de toda a grade, sem padronizar cada ponto de chuva.
Reutilizar núcleo numérico round10.fit_residual: PLS 2, 4 ou 8 componentes,
scale=False, max_iter1000, tol1e-7, ridge1, intercepto não penalizado, semente
20260916. Não reutilizar modelos ou correções já ajustados aos resíduos S09.

Intensidades 25% e 50%, total seis candidatas. Predição = máximo(S10 +
intensidade vezes correção, zero). Sem novos candidatos após os resultados.

## Temporalidade e limites da evidência

Sementes 2005–2006 e 2007–2008. Gerar somente os modelos tropicais faltantes
dessas bases no cache round11, com código congelado. Reaproveitar e conferir
bases S10 de 2009–2022; saída final S10 já salva para 2023–2024.
Desenvolvimento: seis blocos de 24 meses iniciados em 2009, 2011, 2013, 2015,
2017 e 2019. Primeira correção tem 48 meses de resíduos anteriores. Sem alvo
do próprio bloco na estimação do corretor. A transformação atmosférica do
corte externo é não supervisionada e usa apenas atmosfera anterior ao corte.

Arquitetura S10 e região tropical foram escolhidas retrospectivamente. Períodos
de desenvolvimento reutilizados; validação causal não apaga viés de seleção.
2021–2022 já foi consumido: não chamar de holdout inédito. Só avaliar nesse
período a candidata escolhida e congelada. Sem ajuste posterior.

## Critérios de promoção contra S10

RMSE uniforme em todos os pontos e meses: ganho agrupado >=0,3%, segundos
anos melhores, >=5/6 blocos, >=9/12 anos, >=55% dos 144 meses melhores, pior
perda anual <=0,5%. Escolher menor RMSE entre elegíveis. Sem elegível, parar
e não gerar S11. Não afrouxar critérios para gastar o último envio.

Confirmação 2021–2022: ganho agrupado >=0,1% e melhora em ambos os anos.
Se falhar, não testar outra candidata nessa confirmação. Treino final apenas
após aprovação, usando resíduos até dezembro/2022. Para 2023 e 2024 separados,
RMS da mudança <=2x RMS histórico da mudança. Caso contrário, não exportar.

Se aprovada, gerar submissions/submission_11.csv usando o sample oficial,
recusando sobrescrita. Conferir ordem, valores, datas, hashes e reconstrução
integral pelo modelo salvo. Nenhum upload; nenhum score 1,70 garantido.

## Reprodução

PowerShell: definir OMP_NUM_THREADS, OPENBLAS_NUM_THREADS e MKL_NUM_THREADS
como 1 e PYTHONIOENCODING como utf-8. Usar .venv/Scripts/python.exe:

```text
-m src.round12 prepare
-m src.round12 evaluate
-m src.round12 select
-m src.round12 confirm   # somente se selecionada
-m src.round12 final     # somente se confirmação aprovada
-m src.round12 summarize
```

Modelos em data/processed/round12; relatórios em reports/competition/round12.
