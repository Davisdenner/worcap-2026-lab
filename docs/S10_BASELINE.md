# S10 — referência consolidada e preservada

## Resultado confirmado

Público **1,71895**, informado pelo usuário. S09: 1,72957; ganho absoluto
0,01062 (aproximadamente 0,614%). Último líder informado: 1,71488, diferença
0,00407. Classificação não consultada independentemente; privado desconhecido.
Não estimar o score privado nem prometer 1,70 a partir desses valores.

## Artefato oficial de trabalho

- [CSV enviado](../submissions/submission_10.csv): 1.885.464 linhas, colunas
  id e tp_mm_day, exatamente na ordem do sample oficial.
- SHA-256: `57862493c62936b291c03cff3bd4c53fd486ab38a08108f908a8f74b5aada46e`.
- [Metadados originais](../submissions/submission_10.json): snapshot de geração,
  anterior ao envio, por isso uploaded=false e public_score=null são históricos.
- [Resultado posterior](../reports/competition/leaderboard_observations.json)
  e [manifesto](../submissions/manifest.json) registram a aceitação informada.
- Gerada na rodada11; a rodada10 não exportou arquivo. Nenhum arquivo enviado
  pode ser sobrescrito. Todos os componentes da S10 são derivados de dados oficiais.

## Composição exata

S06 combina três previsores: S02 (ensemble local/contexto), modos atmosféricos
regionais com memória e regressão local sazonal com memória. Seus pesos variam
por três faixas de latitude e quatro estações. S09 = 75% S06 + 25% PLS continental16.

S10 = (1 - 0,25 t) S09 + 0,25 t PLS tropical32, onde t=0 ao sul de 15°S,
cresce linearmente de 0 a1 entre 15°S e10°S e vale1 ao norte de10°S.
De 10°S para norte, equivale a 56,25% S06 + 18,75% PLS continental + 25% PLS tropical.
Ao sul de15°S, S10 é exatamente S09. A saída mantém a grade oficial de0,25°.

O tropical utiliza PCA64 continental e PCA64 de campos amostrados a1°, estado
atual + média causal3 e interações sazonais, PLS32 e ridge0,3. Treino final com
503 pares desde1981 até alvo dezembro2022; climatologia anterior de60 anos.
Não usa chuva observada de2023/2024, NOAA, S07/S08 ou recortes data/interim.

## Evidência histórica e limitações

Desenvolvimento 2009–2020: S09 1,780988 → S10 **1,775343**; 6/6 blocos,
9/12 anos e85/144 meses melhores. Confirmação já reutilizada 2021–2022:
1,834766 → **1,830283**, melhora em ambos os anos. Esses números não são scores
do Kaggle. Arquiteturas e períodos foram selecionados retrospectivamente; não
representam teste independente. Os pesos históricos S06 usados na comparação
foram estimados somente com blocos anteriores ao corte.

[Protocolo da geração](../experiments/ROUND11.md),
[resultados](../reports/competition/round11/RESULTS.md),
[reconstrução verificada](../reports/competition/round11/verification.json).

## Rodadas que não substituíram S10

| Rodada | Hipótese | Melhor RMSE 2009–2020 | Decisão |
| --- | --- | ---: | --- |
| 12 | Correção residual PLS | 1,772613 | Ganho 0,154%, abaixo do mínimo |
| 13 | Saída tropical com kernel | 1,773881 | Ganho e estabilidade insuficientes |
| 14 | Transporte/convergência de umidade | 1,775455 | Todas pioraram o agregado |
| 15 | Recalibração conjunta dos cinco componentes | 1,774622 | Ganho 0,041% e estabilidade insuficientes |

Nenhuma dessas rodadas gerou S11 ou consumiu um envio. Modelos experimentais
permanecem separados da referência. A rodada15 avaliou somente recalibração
conjunta dos componentes existentes, sem incorporar candidatas rejeitadas.
Não foi promovida. [Resultados](../reports/competition/round15/RESULTS.md).
