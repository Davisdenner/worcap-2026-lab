# Submissões

## S09 aceita — público 1,72957, informado pelo usuário

[submission_09.csv](submission_09.csv): 75% S06 + 25% PLS16, somente dados oficiais.
1.885.464 linhas e ordem do sample oficial conferidas. Hash SHA-256:
`3acf387d07ebf7d9977122d9c41465472236d66f16ad740bd273cead307800ff`.
Novo melhor score público confirmado. Ganho de 0,01548 sobre S06 e de 0,00593
sobre S07. Classificação atual e resultado privado não verificados.
[Metadados de geração](submission_09.json) e
[validação temporal](../reports/competition/round9/RESULTS.md).
O manifesto mantém os nove resultados informados pelo usuário e registra S09
como melhor pública. Metadados de geração são snapshots anteriores ao upload;
o score posterior está no ledger de observações, sem modificar esses snapshots.

**Referência para novas candidatas com somente dados oficiais: S09, 1,72957.**
Restrição solicitada pelo usuário após S08. S07/S08 usam dados externos NOAA;
seus arquivos e scores são preservados como histórico, não como componentes
das novas candidatas. Nenhum envio anterior foi retirado ou alterado.

**Referência pública anterior: S07 — `submission_07.csv`, 1,73550.**
S07 também passou pelo critério de estabilidade histórica. Segundo lugar e líder
com 1,72921 reconfirmados pelo usuário junto ao resultado S07, sem verificação independente.
As submissões de 14/09 foram encerradas por decisão do usuário.
Em 15/09, o usuário informou S04 aceita com 1,74906 e manutenção do primeiro lugar.

| Versão | CSV local | Score público | Situação |
| --- | --- | ---: | --- |
| S01 | `climatologia_60anos.csv` | 1,85468 | Aceita, conforme screenshot |
| S02 | `submission_02.csv` | 1,81543 | Aceita, score informado pelo usuário |
| S03 | `submission_03.csv` | **1,76467** | Aceita, score informado pelo usuário |
| **S04** | `submission_04.csv` | **1,74906** | Aceita; score e primeiro lugar informados pelo usuário |
| S05 | `submission_05.csv` | **1,74613** | Aceita; score informado pelo usuário, segundo lugar |
| **S06** | `submission_06.csv` | **1,74505** | Aceita; score informado pelo usuário |
| **S07** | `submission_07.csv` | **1,73550** | Aceita; score e segundo lugar informados pelo usuário |
| S08 | `submission_08.csv` | 1,74606 | Aceita; pior que S07 no público, conforme relato do usuário |
| **S09** | `submission_09.csv` | **1,72957** | Aceita; novo melhor público, somente dados oficiais |

S08 adiciona TNA/TSA (Atlântico tropical) à S07. Desenvolvimento: 1,765488,
melhor em quatro blocos e sete anos. Primeira checagem reservada de 2021–2022:
1,837746 (S07) → 1,834110 (S08), com ganho nos dois anos. Nenhum parâmetro
foi ajustado após essa checagem. [Protocolo e fontes](../experiments/ROUND8.md).
O público de S08 foi **1,74606**, piora de 0,01056 sobre S07. O ganho histórico
não se repetiu em 2023. S07 permanece a referência pública; o privado é desconhecido.

S07 incorpora temperaturas do Pacífico da NOAA, com defasagem de dois meses
para o alvo. RMSE histórico 1,768074, melhora nos oito anos contra S06.
A fonte é uma revisão histórica, não arquivo de publicações em tempo real.
Veja fonte, temporalidade, reprodução e limites na [rodada 7](../experiments/ROUND7.md).
Ganho público de 0,00955 sobre S06; diferença para o líder informado: 0,00629.
O objetivo 1,70 não é uma previsão de score. O manifesto registra as oito
submissões com scores conhecidos.

S06 passou pelo critério histórico contra S04 e S05: RMSE 1,772788, melhora
em quatro blocos e seis dos oito anos. O ganho público confirmado foi 0,00108
sobre S05. Isso não garante melhora no privado.
Protocolo: [rodada 6](../experiments/ROUND6.md).

S05 não passou pelo critério de estabilidade: RMSE local 1,775177, mas melhora
em apenas quatro dos oito anos. S04 foi mantida como referência naquela rodada. A exportação de S05
atende ao pedido de uma candidata para hoje, sem alegação de superioridade
robusta. Detalhes e limitações: [rodada 5](../experiments/ROUND5.md).

S04 adiciona memória atmosférica de três meses e pesos por estação/faixa de
latitude. RMSE retrospectivo de desenvolvimento: 1,775701, sem garantia de
ganho no Kaggle. Veja o [protocolo da rodada 4](../experiments/ROUND4.md).
O manifesto consolidado registra S01–S06 com resultados públicos conhecidos.
Os metadados de geração de S04 foram preservados; o resultado posterior está
no registro de observações públicas.

Todos têm 1.885.464 linhas, colunas `id,tp_mm_day`, IDs únicos, valores finitos
não negativos e ordem consistente entre versões. S01 confirmou que essa ordem
era aceita pelo Kaggle. Os scripts nunca fazem submissão automática.

## Registro e integridade

Em 15/09, o sample oficial foi adicionado. A comparação confirmou que os IDs e a
ordem de todos os três CSVs são exatamente iguais aos do modelo oficial. Os CSVs
e seus metadados originais foram preservados; a verificação posterior está no
[relatório da atualização](../reports/competition/update_2026-09-15.json).

- [manifest.json](manifest.json): inventário consolidado com score, tamanho e SHA-256.
- [Observações públicas](../reports/competition/leaderboard_observations.json): fonte dos scores posteriores ao envio.
- Os arquivos `.json` ao lado dos CSVs são metadados da geração local. Campos
  `uploaded: false` ou `public_score: null` nesses arquivos refletem aquele
  momento, não o estado atual no Kaggle. Eles foram preservados.

Os CSVs são grandes e ignorados pelo Git; devem ser preservados ou copiados
separadamente para outra máquina. O manifesto e os metadados são versionáveis.
Não sobrescrever o arquivo de uma versão já enviada ao experimentar outra.

Para verificar os arquivos atuais, executar na raiz:

```powershell
.\.venv\Scripts\python.exe scripts/check_repository.py
```
