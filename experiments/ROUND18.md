# Rodada 18 — memória longa no componente tropical da S11

Protocolo definido antes de avaliar as candidatas desta rodada, durante a
execução independente da rodada 17. Não inclui correções das rodadas 16 ou 17.
Referência fixa: S11. Diagnóstico: 47,38% do erro quadrático em 2009–2020
ocorre entre 0 e 15°N. Hipótese: contexto atmosférico com memória mais longa
pode acrescentar informação ao componente tropical já existente.

Memória de seis meses já foi testada em modelo regional anterior na rodada 4;
aqui a alteração é no PLS tropical multiescala da S11. Não é uma alegação de
novidade científica nem de independência dos períodos já reutilizados.

## Alteração congelada

Preservar PCA64 continental e PCA64 tropical de cada corte, ajustadas apenas
no seu treino histórico. Para cada uma das duas representações, concatenar
estado atual, média causal de três meses e média causal de L meses, L=6 ou 12.
Aplicar as mesmas interações sazonais do modelo tropical original. Nunca usar
meses posteriores à origem, inclusive ao prever 2023/2024.

Treinar PCA32 dos alvos tropicais e PLS32, seguido de ridge de saída 0,3,
intercepto não penalizado, semente 20260917, scale=False, max_iter=1000 e
tol=1e-7. Treino com entradas desde 1981 e apenas alvos anteriores ao corte;
climatologia de 60 anos. Mesma faixa de saída 15°S a 15°N e grade de 0,25°.

Aplicar somente a diferença entre o novo tropical e o tropical original:
`máximo(S11 + fração × peso_tropical_S11 × taper × (T_novo − T_original), 0)`.
O taper é o original: 0 em 15°S, 1 em 10°S, transição linear. Ao sul de 15°S,
S11 fica idêntica. As frações são 0,5 e 1,0. Total: **quatro candidatas**.
Os pesos S11 usados em cada bloco foram calibrados somente no passado.

## Critérios e execução

Seis blocos de 24 meses 2009–2010 até 2019–2020. Métrica uniforme da grade
completa. Ganho >=0,3% contra S11, segundos anos melhores, >=5/6 blocos,
>=9/12 anos, >=80/144 meses melhores e pior degradação anual <=0,5%.
Escolher menor RMSE entre elegíveis. Se nenhuma passar, encerrar a rodada.

Confirmar somente a escolhida em 2021–2022, período reutilizado: ganho >=0,1%
e ambos os anos melhores. Sem trocar candidata depois da confirmação.
Se aprovada, conferir RMS da mudança em cada ano de teste <=2× RMS histórico
e preparar previsão interna. Não exportar CSV ou fazer upload sem pedido explícito.
Nenhum dado NOAA, S07/S08, data/interim ou precipitação oculta é permitido.

```powershell
.\.venv\Scripts\python.exe -m src.round18 evaluate
.\.venv\Scripts\python.exe -m src.round18 select
.\.venv\Scripts\python.exe -m src.round18 confirm
.\.venv\Scripts\python.exe -m src.round18 prepare_final
.\.venv\Scripts\python.exe -m src.round18 summarize
```

Etapas posteriores dependem da aprovação anterior. Resultados em
`reports/competition/round18`; modelos e previsões internas em
`data/processed/round18`. Dados espaciais derivados oficiais são verificados
contra os hashes das auditorias já existentes, sem alterar os artefatos originais.
