# S14_experimental_round27_gate — leaderboard probe

Submission **experimental / não promovida**. A referência oficial permanece S12.
O objetivo é obter uma observação externa depois de várias rodadas históricas reutilizadas;
nenhum score de leaderboard foi consultado durante a geração.

## Evidência e escolha congelada

Na janela OOF 2011–2020 da Rodada 27, S12 teve RMSE 1,756391 e
`logistic_base_0.3` teve 1,755065: ganho 0,075%, 4/5 blocos,
6/10 anos e 67/120 meses positivos. O gate histórico exigia pelo
menos 0,3% global, além de estabilidade. O ganho observado foi
insuficiente; a classificação permaneceu D. O melhor valor veio de
uma tabela de alternativas, com viés de seleção acumulado.
O score público conhecido de S12 é 1,71456, relatado pelo usuário;
nenhum score público desta probe está disponível no momento.

## Configuração final

- Analog: H4 puro da Rodada 25, 10 vizinhos sazonais, média uniforme
  das anomalias, climatologia de 60 anos. A reconstrução de 2019–20
  foi idêntica ao arquivo congelado.
- Gate: regressão logística L2 `C=0.3`, `lbfgs`, 200 iterações no
  máximo, tolerância `1e-4`; latitude, longitude, seno/cosseno do mês,
  climatologia, S12 e Analog−S12; padronização pelo treino.
- Treino final: 86.016 linhas (512 células norte × 24 meses × 7 blocos),
  OOF 2009–2022. O Analog 2021–22 foi gerado com o mesmo H4 e corte 2021.
  Toda climatologia e padronização final usa informação disponível
  até dezembro de 2022. Os alvos de 2023–24 no arquivo oficial são NaN.
- Inferência: `g=0.3×P(Analog vence S12)` apenas nas 15.921 células
  de 0–15°N; no restante, S12 exatamente. A saída é um blend convexo
  de previsões não negativas, sem clipping adicional.

## Arquivo e validações

- CSV: `submissions/S14_experimental_round27_gate.csv`
- SHA-256: `f2926c6cf6b75a702a9623b41108713b9004126792d490177cd0fd2680d20d28`
- Linhas: 1,885,464; IDs únicos na ordem exata do sample oficial.
- Previsão: mínimo 0.000000, máximo 104.637842, média 3.533258, desvio 3.496703 mm/dia.
- Quantis: `{"0": 0.0, "0.01": 0.03135909994396886, "0.05": 0.20242865726564788, "0.25": 1.1145195642219372, "0.5": 2.7079474994457593, "0.75": 4.460715995960245, "0.95": 10.670679018067815, "0.99": 15.321377406480755, "1": 104.63784241128418}`
- Pesos no norte: mínimo 0.00236711, máximo 0.28324986; limite 0,3.
- Ausência de NaN, infinito, IDs duplicados e valores negativos confirmada.
- O auditor refez o treino a partir das linhas históricas, ajustou
  novamente a logística, refez probabilidades e fórmula, e comparou
  cada valor do CSV com a saída formatada em oito casas decimais.

| Período e região | RMS mudança (mm/dia) | Máx. absoluta | Fração alterada |
| --- | ---: | ---: | ---: |
| all_global | 0.075252 | 4.213347 | 20.2640% |
| 2023_global | 0.076926 | 3.692915 | 20.2643% |
| 2024_global | 0.073540 | 4.213347 | 20.2637% |
| all_north | 0.167162 | 4.213347 | 99.9911% |
| all_rest | 0.000000 | 0.000000 | 0.0000% |
| 2023_north | 0.170881 | 3.692915 | 99.9927% |
| 2023_rest | 0.000000 | 0.000000 | 0.0000% |
| 2024_north | 0.163359 | 4.213347 | 99.9895% |
| 2024_rest | 0.000000 | 0.000000 | 0.0000% |

| Faixa de latitude | Células | RMS mudança (mm/dia) | Média absoluta (mm/dia) |
| --- | ---: | ---: | ---: |
| -60:-45° | 15,660 | 0.000000 | 0.000000 |
| -45:-30° | 15,660 | 0.000000 | 0.000000 |
| -30:-15° | 15,660 | 0.000000 | 0.000000 |
| -15:0° | 15,660 | 0.000000 | 0.000000 |
| 0:5° | 5,220 | 0.210810 | 0.129353 |
| 5:10° | 5,220 | 0.172663 | 0.120156 |
| 10:15.01° | 5,481 | 0.102230 | 0.072732 |

Os quantis completos e a distribuição espacial em precisão integral
constam em `data/processed/S14_experimental_round27_gate/validation.json`.

## Rastreabilidade e limites

- Protocolo SHA-256: `6162f5ecd60d00fa4d5f02b46d0c3bdb4d42d866c154da29ed18166ede5b1edc`
- Código de geração SHA-256: `862df18ae043310163bb0b9edb678348b2eb99a687211ea5883fec9195d0a7a2`
- Manifesto SHA-256: `4ba270b92c3aaee6acc1a9831f6bfd6e521507199c1326e860030432b4b1fbad`
- Auditoria SHA-256: `a8f26b08e1add07da25fd45e7d0afc818e0786c56b3c0627552d9b871fb4126a`
- S12 oficial SHA-256: `bba1f8b279447868170b6b2f9b18ee2cc723b891c25627c91438c7725d3aead8`; reprodução byte a byte confirmada.
- Geração UTC: 2026-09-18T00:10:32.151608+00:00.
- O manifesto lista hashes das previsões, treino, modelo, transformações
  PCA, dados oficiais, códigos e CSV. Não houve upload automático.
- A probe pública é informação exploratória sujeita ao conjunto
  visível e ao histórico de escolhas. Melhora pública não promove
  automaticamente a candidata, nem altera o gate histórico.

Esta submission não altera a referência oficial S12 e não satisfaz o gate histórico de promoção.
