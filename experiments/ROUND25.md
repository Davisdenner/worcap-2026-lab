# Rodada 25 — diagnóstico S12, dinâmica latente e análogos

Protocolo definido antes de medir os novos resultados. Pesquisa solicitada pelo
usuário em 17/09/2026. Referência fixa: S12 histórica, RMSE 1,770775491 em
2009–2020. Usar somente dados oficiais e previsões causais já arquivadas.
Nenhum CSV, submissão ou alteração de S10–S13 faz parte desta rodada.

## 1. Diagnóstico descritivo (H6 e H5)

Usar a grade inteira nos seis blocos de 24 meses, 2009–2020. Reportar erro
`previsão − observado` e participação no erro quadrático por latitude, região,
ano, mês, estação, intensidade observada, intensidade prevista, anomalia
observada, climatologia, dispersão dos cinco componentes, PCs continentais,
regime e concordância do sinal dos erros dos componentes. Para o regime
descritivo, KMeans com K=4, seed 20260917 e 20 reinicializações sobre os
primeiros oito PCs continentais do treino anterior ao corte; reportar também
se o regime mudou desde o mês anterior. Os grupos por alvo
observado servem apenas para descrição; nunca para escolher regras aplicáveis
em 2023/2024. Reportar tamanho de cada grupo. Não interpretar pixels como
réplicas temporais independentes. Não escolher novas regiões ou candidatos
depois de ver esses resultados nesta rodada.

Os componentes são S02, modos, ridge local sazonal, PLS continental e extensão
tropical exatamente como registrados na S12. Medir produtos cruzados dos erros
de cada componente com S12, frequência em que todos os cinco componentes
erram no mesmo sentido e fração de SSE da S12 nesses casos. Resumir também
os resultados por bloco e pelo norte (latitude >= 0).

## 2. Uma ablação da ordem dos PCs (H2)

Controle: `global31_dense` da rodada 20, sem retreinar nem alterar seus
parâmetros ou amostras. Treinar um único HGB direto com os mesmos 55 atributos
locais, primeiros 16 PCs continentais e 16 tropicais no mês M, médias causais
de três meses, e **somente** os mesmos 32 PCs de M−1 como informação adicional.
Total: 151 atributos. Os PCs e escalas de cada corte são os da rodada 20,
ajustados antes do bloco. `PC_{M-2}` e diferenças podem ser reconstruídos
dos atributos presentes; não adicionar colunas redundantes.

Reusar 1.536 pontos/mês da amostragem aninhada da rodada 20. HGB: 31 folhas,
300 iterações, taxa 0,05, mínimo 200 amostras/folha, L2 20, 128 bins,
early_stopping=False, seed 20260914, uma thread. Alvo: precipitação M+1
menos climatologia causal de 60 anos. Comparar previsor puro contra o controle
`global31_dense` e as misturas S12 + a × (novo − S12), a em {0,10; 0,25}.
Se não houver ganho no previsor puro e nenhuma mistura elegível, encerrar H2.

## 3. Análogos de estado atmosférico (H4 com avaliação H5)

Um único previsor: primeiros quatro PCs continentais e quatro tropicais do
estado atual, mais suas médias causais de três meses (16 coordenadas), todas
derivadas das PCAs da rodada 20 ajustadas antes do bloco. Distância euclidiana
nessas coordenadas já normalizadas pelos desvios dos PCs no treino. Permitir
apenas alvos históricos cujo mês do ano esteja a no máximo um mês circular do
mês-alvo previsto. Usar os dez vizinhos mais próximos, com peso uniforme.
Prever a média dos mapas de anomalia subsequente dos análogos e somar a
climatologia causal do mês-alvo; limitar chuva a zero. Nenhum alvo do bloco
avaliado pode constar da biblioteca. Reportar número de candidatos e distâncias.

Comparar o análogo puro com a climatologia e com S12. Misturas predefinidas:
S12 + a × (análogo − S12), a em {0,10; 0,25}. A decisão usa RMSE pareado na
grade inteira e blocos, anos, meses, região/estação, produto cruzado e
correlação dos resíduos. Correlação baixa isoladamente não aprova o modelo.
Não testar outros K, distâncias, meses ou pesos nesta rodada.

## 4. Critérios, validação e parada

Seis blocos de 24 meses: 2009–2010 até 2019–2020. Cada PCA, escala e
climatologia é ajustada apenas em alvos/entradas anteriores ao início do bloco.
H2/H4 são comparados à S12 nos mesmos pontos e meses. O controle individual
de H2 é comparado ao seu novo previsor para isolar informação temporal.

Aplicar integralmente os critérios de `experiments/PROTOCOL.md`: ganho relativo
>= 0,3% no agregado, segundos anos melhores, >=5/6 blocos, >=9/12 anos,
>=80/144 meses e pior degradação anual <=0,5%. Se nenhuma candidata passar,
parar sem confirmação, treino final, CSV ou upload. Se alguma passar, selecionar
somente o menor RMSE elegível entre as quatro misturas, depois confirmar apenas
essa candidata em 2021–2022, reconhecendo que esse período já foi reutilizado:
ganho >=0,1% e ambos os anos melhores. Mesmo aprovação não autoriza exportação.

Os períodos históricos já foram repetidamente usados para seleção. Registrar
todos os resultados, inclusive negativos, e não ajustar parâmetros após vê-los.
Não usar o leaderboard público 2023 nem qualquer alvo de 2023/2024 para seleção.
