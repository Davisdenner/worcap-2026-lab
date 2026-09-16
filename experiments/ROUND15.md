# Rodada 15 — recalibração conjunta regularizada da S10

Protocolo definido antes de avaliar as candidatas. Referência S10, público
1,71895; último líder informado1,71488 e último saldo informado um envio hoje.
Não usar esses valores no ajuste. Somente dados oficiais; sem NOAA, S07/S08,
modelos rejeitados nas rodadas12–14 ou data/interim. Nenhum upload automático.

## Cinco componentes e reprodução da referência

1. S02 local/contexto (mantido como um componente, não reabrir suas árvores).
2. Modos atmosféricos regionais com memória3.
3. Regressão local sazonal com memória3.
4. PLS continental16 da S09.
5. PLS tropical32 da S10, estendido por E=(1-t)*S09+t*T, com o mesmo t espacial
   da S10: zero ao sul de15S, linear até10S, um ao norte de10S. A extensão S09
   não acrescenta informação tropical fora da região disponível.

Se b são os três pesos S06 do corte, o prior conjunto é
(0,5625*b0, 0,5625*b1, 0,5625*b2, 0,1875, 0,25).
Sua soma é1 e sua previsão reproduz exatamente S10, inclusive a transição.
O quinto componente contém a S09 nas regiões sem PLS tropical; portanto estes
são pesos da base estendida, não cinco pesos físicos independentes fora do trópico.
Correlações/colinearidade motivam regularização e limites. Prior b de cada corte
é o forward_weights original, apenas com calibração anterior, nunca pesos finais
usados retrospectivamente. Aceitar erro de reconstrução numérica <=1e-10.

## Aprendizado de pesos

Mesmos12 grupos existentes: três faixas de latitude [-60,-30),[-30,-10),[-10,15]
e quatro estações. Não criar novos cortes. Em cada grupo minimizar
w' C w + lambda*||w-prior||², com C a média por bloco das matrizes de produtos
dos erros dos cinco componentes. Covariâncias calculadas com todos os pontos
e meses do grupo, com blocos de24 meses igualmente ponderados. Não tratar pontos
espaciais como amostras estatisticamente independentes para alegar significância.

Restrições: soma dos pesos1, pesos>=0 e cada peso a no máximo0,10 do prior,
respeitando também [0,1]. SLSQP com gradiente analítico, ftol1e-12, max_iter1000;
falha numérica bloqueia execução, não relaxar restrições após resultados.
Quatro lambdas: 0,1; 0,3; 1; 3. Sem busca adicional. Nenhum modelo-base retreinado.

Sementes2005–2006 e2007–2008. Para prever corteY, usar somente blocos completos
que terminam antes deY. Primeiro corte2009 tem48 meses de calibração. O prior
do corte também é causal. Arquitetura S10 foi selecionada retrospectivamente;
esta temporalidade não elimina seleção anterior nem torna desenvolvimento independente.

## Avaliação e critérios congelados

Seis blocos:2009,2011,2013,2015,2017,2019, cada um com24 meses. Métrica RMSE
uniforme de toda a grade. Contra S10: ganho agrupado>=0,3%, segundos anos melhores,
>=5/6 blocos, >=9/12 anos, >=55% dos144 meses melhores, pior perda anual<=0,5%.
Escolher menor RMSE elegível. Se nenhuma passar, parar sem gerar S11.

Confirmar só a escolhida em2021–2022, período já consumido: ganho>=0,1% agrupado
e melhora nos dois anos. Não trocar candidata ou ajustar após confirmação.
Final somente após aprovação: calibrar com blocos até2021–2022, e usar modelos
finais da S10. Nenhuma chuva oculta de2023/24. RMS da mudança de2023 e2024,
separadamente, <=2x RMS histórico da mudança. Caso contrário, não exportar.

Se aprovada, gerar submission_11.csv, sem sobrescrever arquivos, com sample
oficial. Conferir IDs, valores, hashes, soma/limites dos pesos e reprodução
integral com pesos salvos. S10 e snapshots originais permanecem preservados.
Somente o usuário decide o upload. Nenhuma promessa de1,70 ou liderança.

## Organização e reprodução

Referência consolidada em docs/S10_BASELINE.md. Caches pequenos de covariâncias,
pesos e previsões em data/processed/round15, relatórios em reports/competition/round15.
No PowerShell: OMP_NUM_THREADS, OPENBLAS_NUM_THREADS, MKL_NUM_THREADS=1;
PYTHONIOENCODING=utf-8. Com .venv/Scripts/python.exe:

```text
-m src.round15 prepare
-m src.round15 evaluate
-m src.round15 select
-m src.round15 confirm  # apenas se selecionada
-m src.round15 final    # apenas se confirmação aprovada
-m src.round15 summarize
```
