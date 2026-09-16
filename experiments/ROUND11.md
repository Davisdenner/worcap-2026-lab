# Rodada 11 — representação tropical de maior resolução

Definido antes de medir qualquer candidata desta rodada. Somente dados oficiais;
referência S09 pública 1,72957. Não usar NOAA, S07/S08 ou data/interim.
Hipótese motivada pelo diagnóstico já observado da rodada 10: representação
regional pode explicar mais variabilidade tropical. Não afirmar independência
da escolha regional nem transferir o RMSE histórico para o público.

## Modelos fixos

Nove campos atmosféricos oficiais: filtro espacial 5x5 na grade original,
amostragem a cada quatro pontos (1 grau), faixa -20 a 15 graus de latitude,
todas as longitudes. Sem filtro temporal. PCA regional64, médias mensais e
escalas ajustadas somente nos meses de entrada do treino, desde 1981.
Concatenar aos 64 componentes da PCA continental congelada da S09, mantendo
contexto remoto dentro do domínio oficial. Estado atual e média causal de
três meses, com seno/cosseno do mês-alvo e interações sazonais.

Alvos: anomalias de chuva na faixa -15 a 15 graus, relativas à climatologia
de 60 anos anterior ao corte. PCA32 dos alvos; PLS16 ou PLS32, scale=False,
max_iter=1000, tol=1e-7. Ridge 0,3 dos escores normalizados para toda a faixa
alvo, intercepto não penalizado. Semente 20260917. Clipping não negativo.

Quatro candidatas: pesos 25% ou 50% do novo modelo contra S09 na faixa >=-10,
transição linear de peso zero em -15 até o peso nominal em -10. Ao sul de -15,
S09 permanece idêntica. Sem reaproveitar corretor residual reprovado da rodada 10.
Controle adicional: PCA regional64 da representação antiga (filtro9, passo8,
2 graus), PLS16, peso25%, mesmos demais parâmetros. Controle diagnóstico,
não elegível para submissão; não adicionar candidatas após os resultados.

## Validação e critérios congelados

Seis blocos de 24 meses: 2009, 2011, 2013, 2015, 2017, 2019. Treino de cada
bloco usa somente alvos anteriores ao primeiro mês previsto. Avaliação RMSE
uniforme da grade completa, inclusive oceano. S09 histórica idêntica à rodada 10.
Confirmar apenas a escolhida em 2021–2022, período já consumido nas rodadas
anteriores, não holdout novo. Escolha retrospectiva da arquitetura S09 e
reutilização dos períodos limitam a interpretação dos ganhos.

Promoção contra S09: ganho agrupado >=0,3%; segundos anos melhores; >=5/6
blocos, >=9/12 anos, >=55% dos 144 meses melhores; pior perda anual <=0,5%.
Escolher menor RMSE entre elegíveis. Na confirmação exigir >=0,1% agrupado e
melhora em ambos os anos. Se falhar, não trocar por outra candidata ou afrouxar
critérios. Final somente se aprovada, treino com alvos até dezembro/2022.
RMS da mudança em 2023 e em 2024, separadamente, <=2x RMS histórico da mudança.

Se aprovada, exportar o próximo arquivo ainda livre, submission_10.csv (rodada
10 não exportou arquivo), com sample oficial e validação independente. Nunca
sobrescrever CSV. Sem aprovação, nenhum CSV novo. Nenhum upload automático;
nenhuma garantia de 1,70 ou liderança. Verificar dados, integridade e causalidade.

## Reprodução

No PowerShell, definir OMP_NUM_THREADS, OPENBLAS_NUM_THREADS e MKL_NUM_THREADS
como 1 e PYTHONIOENCODING como utf-8. Executar com .venv/Scripts/python.exe:

```text
-m src.round11 prepare
-m src.round11 evaluate
-m src.round11 select
-m src.round11 confirm  # somente se selecionada
-m src.round11 final    # somente se confirmação aprovada
-m src.round11 summarize
```

Artefatos em data/processed/round11, relatórios em reports/competition/round11.
