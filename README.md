# WORCAP 2026 — previsão mensal de precipitação

Repositório dos experimentos da competição de previsão de precipitação sobre a
América do Sul. O objetivo é prever a chuva média do mês seguinte, em mm/dia,
usando os dados oficiais ERA5.

**Diretriz atual: somente dados fornecidos pela organização.** A referência
para os próximos experimentos é **S09 (1,72957)**. S07/S08 incorporam NOAA e
permanecem no histórico, sem uso direto ou indireto nas novas candidatas.
[Protocolo vigente](experiments/PROTOCOL.md). Nenhuma submissão anterior foi removida.

## S09 aceita — novo melhor score público: 1,72957

Score informado pelo usuário. Ganho de 0,01548 sobre S06 e 0,00593 sobre S07,
usando apenas os dados oficiais. A classificação atual e o score privado não
foram verificados. Nenhum novo treino ou envio foi iniciado com esse retorno.

[submission_09.csv](submissions/submission_09.csv) combina 75% S06 e 25% PLS16.
Desenvolvimento 2009–2020: RMSE 1,788894 → 1,780988, ganho de 0,442%, melhora nos
seis blocos. Confirmação 2021–2022, já utilizada anteriormente: 1,841795 → 1,834766,
com ganho nos dois anos. Esses números não são scores do Kaggle nem usam o
mesmo protocolo da tabela histórica abaixo. O upload foi feito pelo usuário.
[Experimento](experiments/ROUND9.md) e
[resultados detalhados](reports/competition/round9/RESULTS.md).

## Histórico — estado após o resultado da S08

**Melhor submissão nossa: `submission_07.csv`, RMSE público 1,73550.**
O usuário informou segundo lugar e líder com 1,72921; não houve consulta
independente ao leaderboard. Na rodada 8, 2021–2022 foi usado pela primeira vez
para uma checagem final: S08 melhorou o agregado e os dois anos contra S07,
sem ajustes posteriores. Esse período não é mais um holdout intocado.

| Versão | Solução | RMSE local, 2013–2020 | RMSE público, 2023 |
| --- | --- | ---: | ---: |
| S01 | Climatologia de 60 anos | 1,827393 | 1,85468 |
| S02 | Ensemble local e contexto atmosférico | 1,795066 | 1,81543 |
| **S03** | S02 + padrões regionais + regressão sazonal | **1,779464** | **1,76467** |
| **S04** | Memória atmosférica + pesos por estação/latitude | **1,775701** | **1,74906** |
| **S05** | Mistura experimental regional e não linear | **1,775177** | **1,74613** |
| **S06** | Memória atmosférica na regressão local sazonal | **1,772788** | **1,74505** |
| **S07** | Modos atmosféricos com informação oceânica da NOAA | **1,768074** | **1,73550** |
| S08 | Adição dos índices do Atlântico tropical | 1,765488 | 1,74606 |

S08 piorou o público em 0,01056 sobre S07, apesar de melhorar nos períodos
históricos avaliados. S07 permanece melhor submissão pública confirmada.

S05 melhorou o público em 0,00293 sobre S04, mas não passou pelo critério de
estabilidade histórica. S06 passou pelo critério histórico e melhorou o público
em 0,00108 sobre S05. S07 melhorou mais 0,00955, tornando-se a nova referência,
com ganho nos oito anos de desenvolvimento. Diferença para o líder informado:
0,00629. Os números
locais e públicos usam anos diferentes e não são diretamente comparáveis.
Os scores públicos foram informados pelo usuário; a fonte está no registro
[leaderboard_observations.json](reports/competition/leaderboard_observations.json).

## Onde encontrar cada coisa

| Caminho | Conteúdo |
| --- | --- |
| [docs/DIARIO_2026-09-14.md](docs/DIARIO_2026-09-14.md) | O que fizemos, resultados e decisões do dia |
| [docs/MODELO_ATUAL.md](docs/MODELO_ATUAL.md) | Referência S04 e composição histórica da S03 |
| [docs/REPRODUCAO.md](docs/REPRODUCAO.md) | Ambiente, dependências e sequência de execução |
| [experiments/NEXT.md](experiments/NEXT.md) | Roteiro para retomar amanhã |
| [experiments/PROTOCOL.md](experiments/PROTOCOL.md) | Validação temporal e regras de uso dos dados |
| [submissions/README.md](submissions/README.md) | Arquivos enviados, scores e integridade |
| [experiments/ROUND4.md](experiments/ROUND4.md) | Protocolo e resultados da rodada mais recente |

## Estrutura

```text
data/
  archive/       ZIP original, preservado localmente
  raw/           12 NetCDF oficiais
  interim/       Recortes de preparação; fora do pipeline da competição
  processed/     Caches, previsões locais e modelos derivados
docs/            Documentação atual e histórico de preparação
experiments/     Protocolos das rodadas e próximos passos
notebooks/       Exploração anterior à competição
reports/         Auditorias e resultados de desenvolvimento
scripts/         Inventário e verificação do repositório
src/             Pipelines das três rodadas e exportador CSV
submissions/     CSVs locais, metadados e registro consolidado
tests/           Testes de tempo, causalidade, métrica e formato
```

Dados, modelos binários e CSVs de submissão ficam fora do Git. Código, protocolos,
metadados e resultados pequenos ficam disponíveis para versionamento. As pastas
vazias de arquitetura inicial em `src/` foram preservadas; os pipelines executados
estão nos arquivos Python diretamente em `src/`.

## Verificação rápida, sem treinar nem submeter

No PowerShell, a partir da raiz:

```powershell
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/check_repository.py
```

Ambiente usado: Windows, Python 3.11.1, execução em CPU. Consulte a
[reprodução](docs/REPRODUCAO.md) antes de rodar os treinamentos. Os comandos de
exportação recusam sobrescrever CSVs existentes.

## Dados e avaliação

- Treino oficial: janeiro/1940 a dezembro/2022, 996 meses.
- Grade: 301 latitudes × 261 longitudes, de 60°S a 15°N e 90°O a 25°O.
- Teste: janeiro/2023 a dezembro/2024, 1.885.464 previsões.
- Público: 2023. Privado: 2024, conforme a descrição fornecida.
- Variáveis atmosféricas do mês anterior são atualizadas no teste; a chuva
  observada permanece em dezembro/2022. Não usamos chuva do teste como entrada.
- Os recortes de chuva de 2023 em `data/interim` são excluídos dos experimentos.

O `sample_submission.csv` foi adicionado ao pacote em 15/09 e está em `data/raw`.
Os 12 NetCDF continuam idênticos, por SHA-256. Os IDs e a ordem oficial coincidem
exatamente com S01, S02 e S03; não há necessidade de corrigir os arquivos enviados
nem recalcular modelos por essa atualização. As próximas exportações priorizam
o sample oficial. Nenhum script faz envio automático ao Kaggle.
Veja a [conferência da atualização](reports/competition/update_2026-09-15.json).

O [README de preparação](docs/history/README_preparacao_utf16.md) foi preservado
com seu conteúdo e codificação originais. Ele descreve a fase anterior, não o
pipeline oficial atual.
