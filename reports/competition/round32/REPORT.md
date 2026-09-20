# Rodada 32: U-Net causal sobre os campos atmosféricos oficiais

**Decisão predefinida: B.** Toda variante piora a S12.

## Escopo

Primeiro previsor base novo desde a S12, e a única rodada do projeto que não recombina mapas congelados. A rede recebe os nove campos atmosféricos oficiais em anomalia padronizada nos meses `o`, `o−1` e `o−2`, mais climatologia, latitude e mês-alvo, 31 canais, e emite o resíduo de precipitação do mês `o+1`. Nenhum mapa OOF de rodada anterior entra como canal.

A distinção em relação à Rodada 30 é essencial: lá a rede era um **classificador escolhendo entre dois mapas prontos** e só podia rearranjar previsões existentes. Aqui ela lê campos brutos e emite precipitação.

Treinada no Kaggle em GPU T4, em recortes aleatórios 64×64, a correção para o problema de amostra pequena, já que tratar cada mês como uma amostra dá cerca de 450 exemplos por corte.

## Resultado

| variante | RMSE | ganho vs S12 | blocos | anos | meses |
| --- | ---: | ---: | ---: | ---: | ---: |
| s12 | 1.756391 | +0.000% | - | - | - |
| unet | 1.822838 | −3.783% | 0/5 | 0/10 | 24/120 |
| blend_0.5 | 1.776054 | −1.119% | 0/5 | 0/10 | 36/120 |
| blend_causal | 1.756391 | +0.000% | 0/5 | 0/10 | 0/120 |

Os pesos de mistura causal colapsaram para exatamente 0,0 nos cinco blocos.

## Leitura

O número que interpreta o resultado não está na tabela. Ponderando a radiografia por grupo do [diagnóstico de amplitude](../slope_diagnostic/RESULTS.md) pelas frações de cada banda e estação, **o RMSE da climatologia pura nestes cinco blocos é 1,8360**, a mesma ponderação aplicada às colunas da S12 devolve 1,7565 contra o valor real de 1,756391, o que valida o cálculo na quarta casa.

| | RMSE | ganho sobre climatologia |
| --- | ---: | ---: |
| climatologia | 1.8360 | - |
| U-Net | 1.8228 | 0,72% |
| S12 | 1.7564 | 4,34% |

**A U-Net não aprendeu algo pior que a S12. Ela praticamente não aprendeu**, ficando a 0,7% da climatologia e capturando um sexto da habilidade que o pipeline extrai. Os pesos de mistura em zero confirmam que ela não agrega nem como componente.

Há corroboração externa: uma equipe pública da mesma competição reportou CNN espacial em 1,8018, também essencialmente climatologia. Duas tentativas convolucionais independentes, com implementações e equipes diferentes, aterrissando no mesmo lugar.

## Limitação não resolvida

A execução registrou `best_inner_valid` e `epochs_run` por bloco em `data/processed/round32/{ano}_unet.json`, mas esses campos nunca foram examinados. Eles distinguem duas explicações com consequências opostas: se a rede convergiu e parou cedo, a arquitetura é inadequada para este volume; se bateu no teto de 25 épocas ainda melhorando, o orçamento de dez mil passos foi pequeno demais e a conclusão "rede convolucional não funciona aqui" não está demonstrada.

**Esta rodada deve ser considerada inconclusiva quanto à arquitetura até que esses logs sejam lidos.** O que está demonstrado é que *esta* configuração, com este orçamento, não supera a climatologia de forma significativa.

O volume de treino é de 335 a 455 meses por corte, fortemente correlacionados. Os blocos 2009 a 2020 já foram reutilizados nas Rodadas 19 a 31. Nenhuma S15, CSV, treino final ou submissão foi criado. [Protocolo](../../../experiments/ROUND32.md) · [Decisão](decision.json)
