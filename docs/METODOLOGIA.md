# Metodologia — da atmosfera observada à previsão de chuva

Este documento reúne a explicação do método usado em S10 e S11. Para executar,
use [REPRODUCAO.md](REPRODUCAO.md); para decidir sobre uma nova candidata,
use o [protocolo vigente](../experiments/PROTOCOL.md). Protocolos de rodadas
e metadados preservam os detalhes históricos, sem substituir esta visão geral.

## 1. Problema e informação disponível

A tarefa é prever a precipitação média em mm/dia do mês M+1 usando a atmosfera
observada no mês M. A grade oficial de 0,25° contém 301 latitudes e 261 longitudes:
78.561 pontos por mês, de 60°S a 15°N e de 90°O a 25°O. A latitude é crescente.

O treino contém janeiro de 1940 a dezembro de 2022. O teste contém 24 meses-alvo,
janeiro de 2023 a dezembro de 2024. Em `teste_features.nc`, `time` é o mês-alvo
e `time_origem` é o mês da atmosfera observada, um mês antes. O público avalia
2023 e o privado 2024. Não temos a precipitação observada desses alvos.

São usadas nove variáveis oficiais: temperatura a 2 m, nuvens, pressão de
superfície, umidade específica, umidade relativa, temperatura, geopotencial e
componentes zonal/meridional do vento em 850 hPa. A chuva histórica oficial
fornece os alvos e a climatologia. Não se usa chuva de 2023/2024 como entrada,
nem se trata a chuva de dezembro de 2022 como se fosse a observação mais recente
de todos os meses futuros. A atmosfera do teste é atualizada mensalmente.

S10/S11 não usam NOAA, modelos S07/S08, pseudoalvos derivados deles ou arquivos
preparatórios de `data/interim`. Bibliotecas são ferramentas de cálculo, não
fontes adicionais de observações meteorológicas.

## 2. Métrica e validação temporal

Calculamos RMSE = raiz da média de `(previsão − observado)²`, agregando todos
os pontos e meses com pesos uniformes, inclusive oceano. Não usamos máscara
continental nem ponderação pela área das células. Essa é a implementação local
da métrica descrita na competição; não temos o avaliador privado do organizador.

A avaliação de desenvolvimento atual contém seis blocos de 24 meses:
2009–2010, 2011–2012, 2013–2014, 2015–2016, 2017–2018 e 2019–2020.
Em cada bloco, treino e pré-processamento usam apenas alvos anteriores ao corte.
Para prever janeiro de um ano, dezembro anterior pode ser entrada de inferência,
mas não um par de treino cujo alvo seria o próprio janeiro avaliado.

O treino dos modelos finais usa 503 pares: entradas de janeiro de 1981 a
novembro de 2022, com alvos de fevereiro de 1981 a dezembro de 2022. Climatologia
mensal por ponto usa os 60 anos completos anteriores ao corte. Médias, escalas,
PCA e PLS são ajustados exclusivamente no treinamento permitido.

Os pesos históricos são aprendidos em blocos anteriores completos. Não se usa
divisão aleatória de pontos espaciais para simular generalização temporal.
2021–2022 é uma confirmação **já reutilizada**, não um teste independente.
Arquiteturas e decisões foram escolhidas usando os períodos históricos; ganhos
nesses períodos têm viés de seleção. Muitos pontos correlacionados não equivalem
a milhões de experimentos independentes nem garantem significância estatística.

## 3. Ideia central: corrigir a climatologia e combinar escalas

Os componentes aprendem anomalias em relação à chuva média de cada mês/local.
Somamos a anomalia prevista à climatologia e limitamos a chuva a valores não
negativos. A combinação inclui informação local, contexto espacial e padrões
continentais/tropicais. A motivação é aproveitar erros complementares; não há
garantia de que um componente complexo seja melhor isoladamente.

| Componente | Representação | Ajuste principal |
| --- | --- | --- |
| Árvores locais | 23 atributos locais e sazonais | HistGradientBoosting, 150 iterações |
| Árvores de contexto | 55 atributos com memória e vizinhança | HistGradientBoosting, 300 iterações |
| Ridge local anual | 9 anomalias atmosféricas | Penalidade 0,1 por ponto |
| Ridge local sazonal | 18 atributos: estado e média causal de 3 meses | Penalidade 0,3 por ponto/mês-alvo |
| Modos regionais | PCA16 da atmosfera continental reduzida | Memória, sazonalidade e ridge 0,3 |
| PLS continental | PCA64 da atmosfera e EOF32 dos alvos | PLS16 e ridge de saída 0,3 |
| PLS tropical fino | PCA64 continental + PCA64 tropical | PLS32 e ridge de saída 0,3 |

### Árvores e S02

Os 23 atributos são latitude, longitude, seno/cosseno do mês-alvo, climatologia,
nove campos brutos e nove anomalias mensais. A versão de contexto acrescenta
32 atributos: nove médias causais de três meses, nove diferenças temporais,
12 resumos de vizinhança (seis campos, janelas 9×9 e 25×25) e dois produtos
umidade–vento. A memória nunca inclui um mês posterior à entrada prevista.

As árvores usam taxa de aprendizado 0,05, até 15 folhas, mínimo de 100 amostras
por folha, regularização L2 10 e erro quadrático. Não há parada antecipada por
divisão aleatória. Cada mês de treino amostra 768 pontos sem reposição, semente
20260914. A árvore de contexto é treinada em 150 iterações e estendida a 300.
A avaliação usa a grade inteira, não apenas a amostra de treinamento.

Denotando árvore local por L, árvore de contexto por C, ridge anual por R e
climatologia por K:

```text
legado = 0,50 L + 0,25 R + 0,25 K
S02    = 0,50 C + 0,50 legado
```

Portanto os pesos totais são 0,50 para C, 0,25 para L e 0,125 para R e K.
O código preserva a ordem dessas operações em float32 para reproduzir os bytes.

### Regressão local e modos regionais

A regressão local sazonal recebe nove anomalias do mês observado e as respectivas
médias causais de três meses. Para cada ponto e mês-alvo, ajusta coeficientes
com amostras dos meses dentro de uma janela circular de ±2 meses. O ridge anual
usa nove anomalias e compartilha coeficientes entre os meses. Médias, escalas,
interceptos e coeficientes são serializados.

Os modos regionais usam campos suavizados por filtro 9×9, amostrados a cada oito
pontos da grade (2°). PCA16 reduz a dimensão; a representação inclui estado,
memória causal de três meses e interações com seno/cosseno sazonais. Uma regressão
ridge prevê anomalias em toda a grade. A semente da PCA é 20260914.

S06 combina S02, modos regionais e regressão local sazonal com memória. Há
12 grupos fixos: três faixas de latitude (cortes em 30°S e 10°S) e quatro
estações meteorológicas. Os pesos convexos históricos são preservados; sua
calibração original usava a versão local anterior, e a posterior substituição
pelo modelo local de memória não recalibrou esses pesos. A referência inicial
da combinação era `(0,50; 0,25; 0,25)`. Os valores efetivos por grupo estão em
[frozen_weights.json](../delivery/s11/evidence/frozen_weights.json), `base_weights`.

### PLS continental e S09

A representação continental reduzida passa por PCA64. A previsão usa estado,
memória causal e interações sazonais. PCA32 nos alvos de chuva fornece os modos
de precipitação (EOFs) usados para aprender PLS com 16 componentes. Uma ridge
de penalidade 0,3 mapeia os escores para a grade completa, com intercepto não
penalizado. Semente 20260916; PLS sem escalonamento automático, até 1.000
iterações e tolerância 1e-7. O escalonamento é explícito no pipeline.

```text
S09 = 0,75 S06 + 0,25 PLS_continental
```

### Representação tropical e S10

O ramo tropical suaviza os campos em janela 5×5 e amostra a cada quatro pontos
(1°), de 20°S a 15°N, preservando todas as longitudes. PCA64 tropical é
concatenada à PCA64 continental. Usam-se novamente estado, memória causal e
interações sazonais. Os alvos cobrem 15°S a 15°N, com PCA32, PLS32 e ridge
de saída 0,3; semente 20260917. A saída continua na grade original de 0,25°.

Se T é o previsor tropical e `t = clip((latitude + 15) / 5, 0, 1)`:

```text
S10 = (1 − 0,25 t) S09 + 0,25 t T
```

Ao sul de 15°S, S10 é S09. Entre 15°S e 10°S a influência tropical cresce
linearmente; ao norte de 10°S chega a 25%. Não se exige T fora da sua região.

## 4. O que mudou na S11

A S11 não acrescentou um novo previsor. Recalibrou conjuntamente cinco
componentes: S02, modos regionais, ridge local sazonal, PLS continental e uma
extensão do tropical `E = (1−t) S09 + t T`.

Para os três pesos históricos `b` da S06, o vetor de referência conjunto é:

```text
prior = (0,5625 b0; 0,5625 b1; 0,5625 b2; 0,1875; 0,25)
```

Esse vetor reconstrói S10, incluindo a transição espacial, até arredondamento
numérico. E contém S09 fora do trópico; não se devem interpretar os cinco pesos
como contribuições físicas independentes em todas as latitudes.

Em cada um dos 12 grupos, minimiza-se `wᵀ C w + λ ||w−prior||²`, onde C é
a média por bloco das matrizes de produtos dos erros fora do treino, sem centrar
esses erros. O código as chama de covariâncias. Restrições: soma 1, pesos
não negativos e desvio máximo absoluto 0,10 em relação ao prior. O otimizador
é SLSQP, tolerância 1e-12 e até 1.000 iterações, com gradiente analítico.

Foram comparados λ em 0,1; 0,3; 1 e 3. O melhor histórico foi λ=1. Para o
corte final de 2023, a calibração contém nove blocos completos, 2005–2006 até
2021–2022, sem alvos de 2023/2024. Pesos-base e estatísticas estão congelados
em `delivery/s11/evidence`, com proveniência e hashes.

## 5. Resultados e decisão

| Comparação | Desenvolvimento 2009–2020 | Melhora relativa | Estabilidade |
| --- | --- | ---: | --- |
| S09 → S10 | 1,780988 → 1,775343 | aproximadamente 0,317% | 6/6 blocos; 9/12 anos |
| S10 → S11 | 1,775343 → 1,774622 | aproximadamente 0,041% | 4/6 blocos; 6/12 anos |

Na confirmação reutilizada 2021–2022, S10 obteve 1,830283 contra 1,834766 da
S09, melhorando ambos os anos. S11 obteve 1,829353 no agregado, mas piorou 2022
e não atingiu o ganho mínimo de confirmação. **S11 não passou nos critérios.**
Foi gerada e enviada por autorização explícita do usuário, sem apagar essa decisão.

Os scores públicos informados foram 1,71895 (S10) e 1,71718 (S11). O ganho
público de 0,00177 não transforma a reprovação histórica em aprovação e não
garante melhora no privado. O critério de 0,3% permanece vigente.

## 6. Reprodutibilidade, artefatos e limites

O fluxo novo retreina todos os componentes finais dos arquivos oficiais e salva
árvores, médias, escalas, regressões, PCA/PLS e histórico atmosférico necessário.
A inferência usa esses modelos e o teste oficial, sem ler a chuva de treino.
Mantêm-se sementes, precisão, ordem de cálculo e uma thread numérica.

Os pesos-base já aprendidos são reutilizados. Os pesos conjuntos da S11 são
recalculados a partir das estatísticas históricas arquivadas. Isso reproduz
treino final e inferência, **não toda a pesquisa histórica desde os dados brutos**.
Os artefatos de calibração não são observações externas: derivam dos blocos
oficiais de treinamento. A proveniência está em
[manifest.json](../delivery/s11/evidence/manifest.json).

Arquivos relevantes: [treino e inferência](../src/s11_delivery.py),
[interface de reprodução](../src/reproducao.py),
[protocolo original S10](../experiments/ROUND11.md),
[recalibração original](../experiments/ROUND15.md) e
[exceção S11](../experiments/ROUND15_EXPERIMENTAL.md).

Para novas versões, mantenha esta explicação central atualizada e arquive a
configuração de cada versão; nunca modifique a história para fazer uma candidata
reprovada parecer aprovada. Não se promete RMSE 1,70, liderança ou significância
estatística com base apenas na validação reutilizada ou no leaderboard público.

## 7. Extensão S12 — corretor não linear de resíduos

S12 mantém a S11 e acrescenta uma correção limitada:

```text
S12 = máximo(S11 + 0,25 × corretor(atmosfera, componentes, espaço, mês), 0)
```

O corretor é um HistGradientBoostingRegressor com perda quadrática, 200 iterações,
taxa 0,03, até 15 folhas, mínimo de 300 exemplos por folha, L2=100 e 128 bins.
Parada antecipada desativada; semente 20260918. Aprende `observado − previsão
causal` em 2.048 pontos amostrados por mês, semente de amostragem somada ao ano
do bloco. O treino final contém 442.368 exemplos dos blocos 2005–2022.

Os 23 atributos são latitude/longitude, seno/cosseno do mês-alvo, climatologia,
S11, cinco desvios dos componentes em relação à S11, dispersão e amplitude
dos componentes, anomalia S11 menos climatologia e as nove variáveis atmosféricas
oficiais do mês anterior ao alvo. Não se fornece intensidade observada do alvo.
O primeiro bloco usa prior S10, pois não há bloco anterior para calibrar S11;
os demais usam calibração somente em blocos anteriores completos.

Na validação 2009–2020, S12 obteve 1,770775 contra 1,774622 da S11: ganho de
0,217%, abaixo do mínimo de 0,3%, apesar de passar na estabilidade. O usuário
autorizou uma exceção apenas a esse mínimo. Na confirmação reutilizada 2021–2022,
obteve 1,821386 contra 1,829353, melhorando ambos os anos. O score público
informado foi 1,71456. Esses resultados não removem sua classificação experimental.

O [motor S12](../src/s12_delivery.py) retreina o corretor a partir dos exemplos
OOF congelados em [delivery/s12](../delivery/s12/README.md) e refaz a inferência.
A reprodução foi [verificada por igualdade integral](../reports/reproducao/S12.md).
Não se regenera toda a pesquisa OOF, nem se usam fontes externas. A rodada 19
investigou mais histórico e pesos de recência; suas candidatas não passaram
nos critérios e não fazem parte da S12.

## 8. S13 — transporte de umidade, teste exploratório

A S13 parte da S12 e substitui parcialmente a correção no norte por um modelo
com seis atributos derivados exclusivamente da umidade específica e dos ventos
em 850 hPa oficiais: dois fluxos horizontais, convergência atual e defasada,
média de três convergências e umidade a montante. O peso regional é 0,5.
Fórmula, máscara e treinamento estão no [protocolo específico](../experiments/ROUND24_EXPERIMENTAL.md).

Na validação 2009–2020, o RMSE caiu de 1,770775 para 1,770637, ganho de
**0,0078%**, insuficiente para o mínimo de 0,3%. Na confirmação reutilizada
2021–2022, o ganho foi **0,00247%**, abaixo de 0,1%, e 2022 piorou. O usuário
autorizou pontualmente dispensar ambos os critérios para conhecer o score
público. O limite predefinido de mudança nas previsões de 2023 e 2024 passou.
O score público informado, após correção pelo usuário, foi **1,71461**,
0,00005 pior que a S12 (1,71456). A S13 não é uma candidata
aprovada pelo protocolo, o privado é desconhecido e o atalho `melhor` continua
em S12. Veja o [resultado completo](../reports/competition/round24_experimental/RESULTS.md).
