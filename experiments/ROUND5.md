# Rodada 5 — escala espacial e não linearidade

Última candidata de 15/09/2026, a pedido do usuário. Referência: S04,
RMSE público 1,74906. Nenhum upload nem monitoramento automático.

## Diagnóstico e hipóteses

O diagnóstico de S04 nos 96 meses de desenvolvimento atribui cerca de 63%
do erro quadrático à faixa de 10°S a 15°N, incluindo todos os pontos de terra
e oceano. Isso não autoriza mudar a métrica ou excluir outras regiões.
Detalhes: [diagnóstico](../reports/competition/round5/diagnostics.json).

Três candidatos, cada um com substituição de metade ou de todo o componente
regional de S04, mantendo os pesos regionais/sazonais previamente estimados:

- `broad16`: suavização espacial 3×3 sobre os campos já reduzidos, seguida
  de PCA com 16 componentes. Nenhuma mistura de meses ou variáveis.
- `detail32`: mesma grade reduzida de S04, com 32 componentes em vez de 16.
  Aumenta a capacidade da representação, não a resolução dos dados originais.
- `rbf16`: mesmos 16 componentes com memória de três meses, usando kernel
  gaussiano em vez da regressão linear. Não utiliza árvores. Comprimento de
  escala definido pela mediana das distâncias quadráticas do treino,
  regularização fixa de 0,3 e intercepto não penalizado.

Todas as configurações preservam o estado atual, a média dos últimos três
meses e as interações seno/cosseno do mês-alvo. Nenhuma entrada de chuva no
período previsto. Médias, escalas, PCA e kernel ajustados só no treino de cada
bloco. Dados externos não utilizados.

## Seleção e limites

Blocos: 2013–2014, 2015–2016, 2017–2018 e 2019–2020. Seis candidatos.
Exigir menor RMSE agregado e nos segundos anos, melhora em pelo menos três
blocos e seis anos. Não retunar a busca depois de observar o público.
Os pesos herdados de S04 foram ajustados deixando de fora o bloco avaliado,
mas o conjunto de experimentos é seleção retrospectiva, não teste independente.
2021–2022 permanece sem avaliação para uma futura checagem de finalistas.

## Reprodução

## Extensão exploratória e decisão final

Os seis candidatos iniciais não passaram pelo critério. Testamos depois um
modelo com oito componentes continentais e oito por faixa de latitude, com
halo fixo de dez graus, em duas proporções. Também foi avaliada uma mistura
igual das candidatas regional e não linear com substituição de metade do
componente regional. Total: nove candidatos. Essas extensões foram motivadas
pelos resultados locais, não são um protocolo inteiramente pré-registrado.

A melhor mistura (`complement_0.5`) atingiu **1,775177** contra **1,775701**
de S04, e **1,813542** contra **1,814847** nos segundos anos. Melhorou três
blocos, mas somente quatro anos. **Não passou pelo critério de promoção.**
S04 continua referência. S05 foi exportada a pedido do usuário como candidata
experimental, com risco de regressão e ganho local pequeno (cerca de 0,03%).
Não alegar superioridade validada nem registrar score antes do retorno do usuário.

## Comandos atualizados

```powershell
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.venv/Scripts/python.exe -m unittest discover -s tests
.venv/Scripts/python.exe -m src.round5 diagnostic
.venv/Scripts/python.exe -m src.round5 evaluate
.venv/Scripts/python.exe -m src.round5 regional
.venv/Scripts/python.exe -m src.round5 complement
.venv/Scripts/python.exe -m src.round5 select
.venv/Scripts/python.exe -m src.round5 final --experimental
```

Requer caches e artefatos anteriores. O comando final recusa sobrescrever
`submissions/submission_05.csv`. Sem `--experimental`, recusa gerar se nenhum
candidato passar. Com essa opção, exporta o melhor ganho numérico e registra
explicitamente que ele não foi promovido.
O sample oficial define IDs e ordem. O exportador verifica todos os registros.
