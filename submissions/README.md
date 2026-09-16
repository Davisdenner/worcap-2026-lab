# Submissões

**Melhor score público: S07 — `submission_07.csv`, 1,73550.**
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

S07 incorpora temperaturas do Pacífico da NOAA, com defasagem de dois meses
para o alvo. RMSE histórico 1,768074, melhora nos oito anos contra S06.
A fonte é uma revisão histórica, não arquivo de publicações em tempo real.
Veja fonte, temporalidade, reprodução e limites na [rodada 7](../experiments/ROUND7.md).
Ganho público de 0,00955 sobre S06; diferença para o líder informado: 0,00629.
O objetivo 1,70 não é uma previsão de score. O manifesto registra as sete
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
