# S14_experimental_round27_gate — protocolo congelado

Submission exploratória de leaderboard, sem promoção. S12 permanece a referência
oficial. A configuração foi escolhida na Rodada 27, antes de observar qualquer
resultado de leaderboard desta submission: `logistic_base_0.3`.

- Referência: S12 reproduzida, SHA-256 do CSV `bba1f8b279447868170b6b2f9b18ee2cc723b891c25627c91438c7725d3aead8`.
- Alternativa: Analog puro H4 da Rodada 25, com 4 PCs atuais e 4 de média de
  três meses por região, vizinhos sazonais ±1 mês, 10 vizinhos, média uniforme
  das anomalias históricas, climatologia de 60 anos e clipping a zero.
- Gate: regressão logística `C=0.3`, `solver=lbfgs`, `max_iter=200`,
  `tol=1e-4`, com média e desvio do treino. Sete atributos na ordem das
  colunas `[0,1,2,3,4,5,106]` da Rodada 27: latitude, longitude, seno/cosseno
  do mês alvo, climatologia, S12, Analog menos S12.
- Treino final: 512 células do norte por mês com o mesmo amostrador da Rodada
  26; blocos OOF 2009–2020 congelados e bloco 2021–22 OOF calculado pelo
  mesmo H4, com transformações e alvos somente anteriores a 2021. A
  climatologia e padronização do gate final são ajustadas no corte 2023.
  Nenhum alvo posterior a dezembro de 2022 é permitido.
- Inferência: `p=P(Analog vence S12)`, `g=0.3*p` nas 15.921 células de latitude
  ≥0°; `S12 + g*(Analog-S12)` no norte e S12 exatamente nas demais células.
  Nenhum clipping adicional, pois ambos os especialistas e o blend convexo
  são não negativos.
- Exportação: `tp_mm_day` com oito casas decimais, IDs e ordem do
  `data/raw/sample_submission.csv` oficial.
- Auditoria obrigatória: reproduzir Analog histórico, conferir S12, treinar
  somente em histórico permitido, recalcular fórmula a partir dos artefatos
  finais, validar pesos, IDs, ordem, valores e hashes.
- Sem oracle, reajuste de parâmetros, novas variantes, consulta ao leaderboard
  na geração, upload ou promoção automática.

Esta submission não altera a referência oficial S12 e não satisfaz o gate histórico de promoção.
