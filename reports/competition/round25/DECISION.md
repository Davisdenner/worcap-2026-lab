# Decisão científica — rodada 25

Referência imutável S12: 1,770775491 de RMSE histórico em seis blocos de
24 meses, 2009–2020. Protocolo registrado antes da avaliação em
experiments/ROUND25.md. Todos os períodos de desenvolvimento foram usados
anteriormente em outras decisões; os resultados não são teste independente.

## O que revelou o diagnóstico

- A faixa 0–15°N mantém 47,38% do erro quadrático em 20,27% dos pontos.
- Anomalias observadas de magnitude >=4 mm/dia somam 4,47% dos pontos e
  54,29% do erro quadrático. Esse grupo depende do alvo oculto e **não pode**
  definir uma regra de inferência. A subestimação dos maiores valores
  observados, isoladamente, não prova viés corrigível sob RMSE.
- Dispersão entre componentes >=0,5 mm/dia ocorre em 12,66% dos pontos e
  reúne 44,88% do erro quadrático. É um sinal disponível na inferência,
  mas também pode refletir clima médio e intensidade; requer ablação causal
  antes de orientar uma correção.
- Os cinco componentes erram no mesmo sentido em 75,58% dos pontos; nesses
  casos concentram 98,90% do erro quadrático da S12. Os produtos cruzados e
  correlações dos erros individuais com a S12 são altos (0,971–0,982 no
  agregado). Concordância do sinal depende do alvo observado, portanto é
  descritiva e não demonstra que o erro comum seja previsível. Os componentes
  também compartilham entradas, e a extensão tropical herda S09 fora do
  trópico; não são cinco previsores independentes.
- Os quatro regimes descritivos KMeans variam entre cortes, embora os rótulos
  tenham sido ordenados pelo centro em PC1. Mudança de regime não concentrou
  erro: 56,25% dos pontos e 55,55% do SSE. O diagnóstico não justifica
  especialistas por regime agora.

Detalhes por ano, estação, intensidade, climatologia e PCs estão em
DIAGNOSTIC.md e diagnostic.json.

## Ablação H2 — ordem dos PCs

O modelo direto global31_dense da rodada 20 teve RMSE puro 1,816897; a
mesma árvore com os 32 PCs do mês anterior teve 1,819411. Melhorou o previsor
puro em apenas dois dos seis blocos, um deles quase empate. A mistura de 10%
com S12 piorou para 1,771140 (−0,0206% de ganho); a de 25% piorou mais.
Correlação global dos erros com a S12: 0,9725. **Abandonar essa formulação de
lag1**; acrescentar diferenças algebraicamente redundantes não a resgata.

## H4/H5 — análogos e diversidade

O previsor puro por análogos obteve 1,847297, ante 1,856557 da climatologia
e 1,770775 da S12. Sua correlação global de erros com a S12 foi 0,9487,
menor que a da H2, e o produto cruzado foi 3,103465. Portanto há alguma
diversidade útil, mas insuficiente nesta configuração.

A mistura predefinida de 10% reduziu o RMSE histórico da S12 para
**1,769921448**: ganho de **0,0482%**, com 4/6 blocos, 8/12 anos e 79/144
meses melhores. Falhou o mínimo de 0,3% e os critérios de estabilidade.
A mistura de 25% piorou. A contribuição de 10% foi observada sobretudo no
norte (RMSE 2,707666 → aproximadamente 2,704863); no sul houve praticamente
empate. Esse recorte foi observado depois da avaliação e não autoriza escolher
peso ou região retroativamente.

As métricas de cada mistura foram refeitas independentemente a partir das
previsões salvas; hashes, cortes e anos dos análogos passaram na auditoria
diversity_audit.json. DIVERSITY.md resume RMSE, correlação e produto
cruzado dos erros por área. A fração ótima analítica calculada a posteriori
serve apenas para descrição; não gerou nova candidata.

## Decisão

Nenhuma das quatro misturas passou o gate vigente. Portanto nenhuma
candidata foi selecionada, 2021–2022 não foi consultado nesta rodada,
não houve treino final, CSV ou upload, e S12 continua como referência
reproduzível. Não repetir H2 com colunas equivalentes nem ajustar K, distância,
fração ou região dos análogos sobre esses blocos reutilizados. A próxima
hipótese estrutural precisaria trazer representação espacial ou temporal
genuinamente ausente, com protocolo próprio antes de medir.
