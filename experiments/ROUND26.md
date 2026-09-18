# Rodada 26 — previsibilidade do erro comum da S12 no norte

Protocolo científico fixado antes de qualquer métrica nova. O pedido é
diagnóstico: nenhuma candidata S14, nova mistura, peso regional, confirmação
2021–2022, previsão final, CSV ou upload é autorizada. Referência fixa S12.
Dados oficiais apenas. Faixa norte: latitude >=0° até 15°N, incluindo todos
os 261 longitudes e 61 latitudes. Resíduo: observado − S12.

## Cortes e limite de disponibilidade

Descrever o erro nos seis blocos históricos completos de 24 meses:
2009–2010, 2011–2012, 2013–2014, 2015–2016, 2017–2018 e 2019–2020.
As primeiras previsões S12 históricas OOF disponíveis começam em 2009.
Consequentemente, **não há conjunto anterior de resíduos S12 para ajustar um
previsor em 2009–2010**. Esse bloco entra integralmente no diagnóstico e no
treino dos blocos seguintes, mas não recebe escore preditivo inventado.
Testar previsibilidade em 2011–2020, cinco blocos completos, com treino
expansivo em blocos S12 OOF estritamente anteriores. Não usar resíduos de
S11/S10 como substitutos rotulados S12 nem retreinar uma S12 distinta para
fabricar anos anteriores.

Para cada corte, reusar as previsões S12 e dos cinco componentes produzidas
causalmente no próprio bloco. Ajustar climatologia, média das nove variáveis,
PCA continental/tropical, padronização e qualquer limiar exclusivamente antes
do início do bloco testado. Aplicar uma **única base PCA do corte em avaliação**
aos meses de treino e de validação; não misturar coordenadas PCA ajustadas em
cortes diferentes. Nunca usar chuva de 2023/2024.

## 1. Teste OOF do resíduo

Treinar modelos Ridge com penalidade 0,3 na covariância média das features
padronizadas (equivale a alpha = 0,3 × número de exemplos). Intercepto não
penalizado. Amostrar 512 células norte sem reposição em cada mês de treino,
semente determinística 20260926 + índice absoluto do mês observado. Mesma
amostra para todas as ablações; avaliar **todas** as 15.921 células norte e
24 meses de cada bloco. Evitar declarar células/mês independentes.

Base comum: latitude, longitude, seno/cosseno do mês-alvo, climatologia local,
S12 e anomalia S12−climatologia. Ablações aditivas:

| Grupo | Atributos adicionados à base |
| --- | --- |
| local | 50 atributos restantes da matriz contextual local: campos, anomalias, médias/diferenças causais, vizinhança e produtos |
| continental | primeiros 8 PCs continentais do mês M e respectivas médias causais de 3 meses |
| tropical | primeiros 8 PCs tropicais do mês M e respectivas médias causais de 3 meses |
| componentes | cinco desvios das previsões dos componentes em relação à S12 |
| dispersão | desvio padrão e amplitude dos cinco componentes |
| consenso | média, mínimo, máximo e desvio dos componentes, contagens acima/abaixo da climatologia, sinal majoritário, magnitude média da anomalia, e A=abs(média da anomalia)/(desvio+0,1) |
| local+continental | união dos dois grupos, além da base |
| local+tropical | união dos dois grupos, além da base |
| completo | união de local, continental, tropical, componentes e consenso |

Um HGB conservador somente para o grupo completo serve como checagem não
linear: 7 folhas, 100 iterações, taxa 0,03, mínimo 500 exemplos por folha,
L2=100, 128 bins, sem early stopping, seed 20260926. Não ajustar parâmetros
ou selecionar outra arquitetura depois de olhar resultados.

Métricas pareadas: correlação Pearson do resíduo previsto com o real, RMSE
residual, R² centrado usual e R² contra a previsão de resíduo zero
(1−SSE_novo/SSE_S12). Registrar por bloco e ano, e ganho incremental
contra a base comum. O modelo puro de resíduo é apenas uma sonda
diagnóstica; não somar previsões à S12 como nova candidata.

## 2. Geografia, calendário e intensidade dos erros

No norte, acumular SSE, contagem, RMSE e viés por latitude de 5°,
longitude de 10°, cruzamento 5°×10°, mês, estação DJF/MAM/JJA/SON, ano,
setores oeste (−90:−70°), centro (−70:−50°) e leste (−50:−25°),
intensidade observada [0,.5,2,5,10,20,+inf] e magnitude da anomalia
observada [0,.5,1,2,4,+inf] mm/dia. Calcular concentração de SSE nos
1%, 5% e 10% maiores |resíduos|. Alvo observado pode classificar erros
apenas em diagnóstico; não define uma regra disponível em inferência.
Gerar mapa de SSE, mapa de viés, matriz ano×mês, tabela lat×lon e perfis
de intensidade e estação.

## 3. Direção do erro

Usar r>0 para subestimação e r<0 para superestimação. Para 2011–2020,
estimar P(r>0|X) em bins fixos de mês, estação, latitude, longitude e em
quintis cujos limites são aprendidos apenas no treino anterior de cada
corte para climatologia, anomalia prevista, PCs continentais/tropicais,
cada uma das nove variáveis atmosféricas, dispersão e A. Registrar tamanho,
taxa e mudança em relação à taxa-base do próprio bloco.

Como teste preditivo, uma regressão Ridge binária com as features do grupo
completo fornece probabilidades limitadas a [0,01;0,99]. Reportar AUC, Brier
e diferença frente à probabilidade constante estimada no treino anterior,
por bloco e ano. Isto é diagnóstico de sinal, não calibração de candidata.

## 4. Casos críticos

Para cada corte, definir Q90 e Q95 de |r| usando **todos os pontos norte dos
blocos S12 anteriores**. Comparar as distribuições de climatologia,
anomalia prevista, dispersão, A, quatro PCs continentais/tropicais e
variáveis locais entre casos acima de Q90 e casos normais; reportar
diferença padronizada de média e frequências por quintil. Uma Ridge
binária com grupo completo estima P(|r|>Q90_treino|X) OOF. Medir AUC,
average precision, Brier, prevalência e lift no decil superior, por
bloco e ano. Repetir descrição para Q95, sem treinar outro classificador.
Não criar gating ou correção nesta rodada.

## 5. Consenso excessivo

Calcular média, desvio, amplitude, mínimo, máximo, contagens acima/abaixo
da climatologia, sinal majoritário, magnitude média de anomalia e A com
epsilon fixo 0,1 mm/dia. Comparar risco de Q90, direção e SSE por faixas
fixas de A [0,1,2,4,8,+inf]. Estratificar a associação de A pelo nível
da climatologia [0,2,5,10,+inf] e pela magnitude da anomalia prevista
[0,.5,1,2,+inf]. A concordância do sinal dos **erros** dos componentes usa
o alvo observado e é descritiva, nunca entrada do modelo.

## Interpretação predefinida

**A — erro comum previsível:** ao menos um grupo excede R² contra zero
de 0,5% no conjunto OOF, melhora a base em 0,2 ponto percentual, é
positivo em >=4/5 blocos e >=7/10 anos; sinal de direção ou evento Q90
também supera sua referência em >=4/5 blocos. Modelos lineares e a
checagem não linear devem ser coerentes quanto à existência do sinal.
Isso justificaria somente desenhar um experimento futuro separado.

**B — parcialmente previsível:** não satisfaz A, mas há ganho positivo
OOF concentrado em setor ou estação predefinidos que represente >=10%
dos pontos norte e se repita em >=3/5 blocos e >=6/10 anos. Informar
exatamente onde existe e desaparece; não extrapolar para todo o norte.

**C — essencialmente não previsível com estas features:** nenhum padrão
satisfaz A ou B; efeito limitado a bins raros, anos isolados ou ao
treino; direção/criticidade sem discriminação estável. Nesse caso,
priorizar nova representação ou fonte física, não mais um corretor
semelhante.

Os limites são critérios de pesquisa, **não** substituem o gate de promoção
de experiments/PROTOCOL.md. Blocos e arquiteturas já foram reutilizados
repetidamente: todas as conclusões são exploratórias, sem p-valores
ingênuos por pixel e sem consulta ao leaderboard 2023. Se o único ganho
vier de subconjuntos pequenos ou instáveis, não generalizar para 0–15°N.
