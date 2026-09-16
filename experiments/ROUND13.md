# Rodada 13 — componente tropical não linear da S10

Protocolo definido antes dos resultados desta rodada. Somente dados oficiais;
S10 pública 1,71895, líder informado 1,71488, último saldo informado de um
envio hoje. Esses scores não entram nos ajustes. Nenhum upload automático.

## Hipótese e quatro configurações

Substituir somente a regressão de saída do componente tropical da S10 por
Kernel Ridge gaussiano. Preservar PCA64 continental + PCA64 tropical fina,
entradas atuais/média causal3, interações sazonais, PLS32 e climatologia da S10,
todos ajustados antes do corte temporal. O kernel recebe os 32 escores PLS
normalizados pela escala de treino já salva. Sem chuva observada no teste.

Treinar diretamente as anomalias de chuva na faixa -15 a 15 graus, usando
todos os pares de treino desde 1981 (503 no ajuste final), não os poucos
resíduos de previsões históricas. Os escores PLS são supervisionados, mas
treinados somente nos alvos anteriores ao bloco previsto. Não usar rótulos
do bloco para aprender representações, escalas ou largura do kernel.

Kernel K(i,j)=exp(-distância_quadrática(i,j)/h), com h igual à mediana das
distâncias quadráticas entre pares distintos do treino multiplicada por 0,5
ou 2. Regularização alpha=0,3 ou 3 na matriz K+alpha*I (não dividida por n).
Intercepto não penalizado. Quatro candidatas; sem busca adicional após resultados.
Se todas as distâncias forem zero ou houver dados não finitos, interromper.

A saída tropical continua não negativa. Preservar exatamente o peso25% da S10
ao norte de 10°S e a transição linear entre 15°S e 10°S. Ao sul de 15°S, manter
S10 idêntica. Não aplicar peso25% adicional sobre a S10: substituir seu componente
tropical, mantendo os 75% da base S09 nessa faixa. Nenhum ajuste de pesos.

Kernel já foi testado na rodada5 com representação diferente e resultados
fracos. Esta rodada não presume novidade da técnica nem ganho garantido.
Não usar NOAA, S07/S08, data/interim, modelos externos ou chuva oculta 2023/24.

## Validação e gates congelados

Desenvolvimento: 2009–2010, 2011–2012, 2013–2014, 2015–2016, 2017–2018,
2019–2020. RMSE uniforme em toda a grade. Reproduzir o componente linear S10
como controle, conferindo igualdade com os artefatos já salvos, sem promoção
do controle. Arquitetura e períodos reutilizados; não é teste independente.

Critérios contra S10: ganho agrupado >=0,3%, segundos anos melhores, >=5/6
blocos, >=9/12 anos, >=55% dos144 meses melhores, pior perda anual <=0,5%.
Escolher menor RMSE entre elegíveis. Nenhuma elegível: parar sem S11.
Confirmação somente da candidata congelada em 2021–2022 (já utilizado, não
holdout inédito): ganho agrupado >=0,1% e melhora nos dois anos. Se falhar,
não trocar candidata nem reajustar parâmetros. Não reduzir gates após resultados.

Final somente após aprovação, com alvos até dezembro/2022. RMS da alteração
em 2023 e 2024, separadamente, <=2x RMS histórico da alteração. Caso contrário,
bloquear exportação. Se aprovada, gerar submission_11.csv distinta, com sample
oficial, conferir IDs, valores, datas, hash e reconstrução integral pelo modelo.
Recusar sobrescrita e não enviar ao Kaggle. Sem garantia de 1,70 ou liderança.

## Reprodução

PowerShell: OMP_NUM_THREADS, OPENBLAS_NUM_THREADS, MKL_NUM_THREADS iguais a 1;
PYTHONIOENCODING=utf-8. Com .venv/Scripts/python.exe executar:

```text
-m src.round13 prepare
-m src.round13 evaluate
-m src.round13 select
-m src.round13 confirm  # apenas se selecionada
-m src.round13 final    # apenas se confirmação aprovada
-m src.round13 summarize
```

Artefatos em data/processed/round13; relatórios em reports/competition/round13.
