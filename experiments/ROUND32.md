# Rodada 32 — U-Net causal sobre os campos atmosféricos oficiais

Protocolo registrado antes de calcular qualquer resultado novo. Esta rodada
não recombina mapas congelados: ela treina um **previsor base novo**, o
primeiro desde a S12, a partir apenas dos nove campos atmosféricos oficiais.

## Por que esta hipótese

As Rodadas 25 a 31 testaram seis formas independentes de recombinar os mapas
OOF já existentes — gate logístico, ridge, HGB, top-k de strong wins, gate
convolucional de seleção e recalibração de amplitude. Todas aterrissaram
entre +0,04% e +0,08% sobre a S12. Essa convergência, entre famílias de
método sem relação entre si, indica que os mapas congelados estão esgotados.

O diagnóstico de fluxo de umidade
([mfc_diagnostic](../reports/competition/mfc_diagnostic/mfc.json)) mostrou que
o resíduo da S12 correlaciona apenas 0,03 a 0,07 com as variáveis
atmosféricas de 850 hPa — mas essa medida é **pontual e linear**, célula
contra célula. E `round2.Features.matrix` constrói exatamente assim: as 55
colunas leem as nove variáveis na própria célula da grade, com PCs e PLS
entrando só como resumos continentais já achatados em número. Nenhuma etapa
do pipeline representa o padrão espacial bruto do campo atmosférico.

A radiografia por grupo
([slope_diagnostic](../reports/competition/slope_diagnostic/shrink.json))
localizou 62,4% de todo o erro quadrático na faixa lat >= -10, um terço das
linhas da grade, onde convecção e circulação são fenômenos essencialmente
não-locais.

Hipótese: o sinal restante é não-local e não-linear, e uma rede totalmente
convolucional imagem-para-imagem o extrai, enquanto a família de mistura
linear atual não consegue representá-lo.

## Distinção explícita em relação à Rodada 30

A Rodada 30 também usou uma rede convolucional e falhou. Ela era um
**classificador escolhendo entre dois mapas prontos** (S12 e análogo H4),
recebendo previsões congeladas como canais; por construção só podia
rearranjar previsões existentes. Esta rodada recebe **campos atmosféricos
brutos** e emite precipitação. O fluxo de informação é outro.

## Contrato do teste, verificado

`teste_features.nc` entrega, para cada um dos 24 meses-alvo de 2023-01 a
2024-12, o estado atmosférico real do mês imediatamente anterior
(`time_origem` de 2022-12 a 2024-11, todas as 24 entradas distintas). A
tarefa é uniformemente de um mês de antecedência. `lag_meses` mede a
distância até a última precipitação observada (2022-12), não o horizonte
atmosférico. Nenhuma feature de precipitação recente entra nesta rodada,
o que mantém treino e teste alinhados.

## Dados, cortes e arquitetura

- Somente dados oficiais. Nenhum índice externo, nenhum alvo de 2023-2024,
  nenhum artefato de rodada anterior entra como canal.
- Seis blocos causais `round27.YEARS` = 2009-10, 2011-12, 2013-14, 2015-16,
  2017-18 e 2019-20. Para o corte Y, treino usa apenas origens `o` com
  `o + 1` estritamente anterior ao início do bloco, via
  `competition.training_pairs`, que também impõe o início em 1981-01 já
  adotado pelo resto do pipeline. Isso dá entre 335 e 455 meses de treino
  conforme o corte. Climatologia, médias e desvios de padronização são
  recalculados por corte, só com meses anteriores.
- 31 canais de entrada: as nove variáveis oficiais padronizadas em anomalia
  nos meses `o`, `o-1` e `o-2` (27), mais a climatologia de precipitação do
  mês-alvo, a latitude e o seno e cosseno do mês-alvo (4).
- Alvo: o resíduo `tp[o+1] − climatologia(mês-alvo)`, padronizado. Otimizar
  erro quadrático sobre o resíduo é otimizar o RMSE diretamente.
- U-Net com dois níveis de pooling: 32, 64 e 128 canais, dois blocos
  convolucionais 3x3 por nível, GroupNorm e ReLU, conexões de salto, cabeça
  1x1. Padding reflexivo de 301x261 para 304x264 na inferência, recorte de
  volta em seguida.
- Treino em recortes aleatórios 64x64, que é a correção para o problema de
  amostra pequena: tratar cada mês como uma amostra dá ~950 exemplos e a rede
  não treina; recortes dão dezenas de milhares. Adam, taxa 1e-3, weight decay
  1e-4, lote 32, 400 passos por época, máximo de 25 épocas, semente 20261001.
- Os últimos 24 meses de treino de cada corte, estritamente anteriores ao
  bloco, formam a validação interna para seleção do melhor checkpoint. O
  bloco avaliado nunca participa de nenhuma decisão de treino.
- Arquitetura e hiperparâmetros únicos, congelados aqui. Nenhuma busca.

## Métricas e classificação predefinida

RMSE na grade cheia, comparado à S12, nos cinco blocos `round27.EVAL`
(2011-2020, referência S12 = 1,756391), com o número de seis blocos
reportado em paralelo. Três variantes: a U-Net sozinha, a mistura
`0,5·S12 + 0,5·U-Net`, e a mistura com peso ajustado causalmente nos blocos
anteriores.

- **A**: alguma variante atinge ganho global >= 0,3% **e** >= 4/5 blocos,
  >= 7/10 anos e >= 67/120 meses melhores. Não promove automaticamente:
  exige depois confirmação 2021-2022 e `src.round9.passes_gate`, como
  qualquer candidata.
- **D**: há ganho, mas sem amplitude e estabilidade de A.
- **B**: toda variante piora a S12.

Nenhuma S15, CSV ou envio é criado nesta rodada em nenhum cenário.

## Limitações reconhecidas antes de ver qualquer resultado

Os blocos 2009-2020 já foram reutilizados nas Rodadas 19 a 31; há viés de
seleção acumulado, e esta rodada não o remove. O volume de treino é modesto
para uma rede convolucional mesmo com recortes: de 335 a 455 meses por corte,
fortemente correlacionados no tempo e no espaço, o que limita a capacidade
útil da arquitetura. Manter o início em 1981 preserva a convenção do
pipeline, mas deixa de fora 1940-1980, que existe no cache oficial; se esta
rodada mostrar sinal, estender o início é a primeira variação a testar, em
rodada separada.
Uma equipe pública da mesma competição reportou CNN espacial em 1,8018,
pior que suas próprias árvores, atribuindo o resultado a amostras
insuficientes; a estratégia de recortes desta rodada é exatamente a resposta
a esse modo de falha, mas não há garantia de que baste. Um resultado nulo
aqui descarta esta arquitetura e este conjunto de canais, não toda
modelagem espacial.
