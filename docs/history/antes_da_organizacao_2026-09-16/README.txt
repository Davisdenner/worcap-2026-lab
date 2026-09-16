# WORCAP 2026 — previsão mensal de precipitação

Repositório dos experimentos da competição de previsão de precipitação sobre a
América do Sul. O objetivo é prever a chuva média do mês seguinte, em mm/dia,
usando os dados oficiais ERA5.

**Diretriz atual: somente dados fornecidos pela organização.** A referência
de melhor score público é **S11 (1,71718)**, mantendo S10 como controle de
validação aprovado. S07/S08 incorporam NOAA e
permanecem no histórico, sem uso direto ou indireto nas novas candidatas.
[Protocolo vigente](experiments/PROTOCOL.md). Nenhuma submissão anterior foi removida.

**Referência consolidada:** [S10 — composição, resultados e integridade](docs/S10_BASELINE.md).
**Entrega S11:** [reprodução, documentação e limitações](docs/ENTREGA_S11.md).
Os registros abaixo preservam a sequência histórica; uma candidata local não
substitui a melhor pública sem resultado confirmado pelo usuário.

## S11 aceita — público 1,71718 informado pelo usuário

Nova melhor marca pública: redução de 0,00177 (0,103%) sobre S10.
O ganho público não altera a reprovação nos critérios históricos nem garante
ganho no privado. CSV e metadados de geração preservados; resultado posterior
registrado no ledger e manifesto. Nenhum novo experimento ou envio iniciado.
Novas submissões somente mediante pedido. Abaixo, histórico da geração.

## S11 experimental gerada a pedido do usuário

[submission_11.csv](submissions/submission_11.csv) usa `joint1`, a melhor
recalibração da rodada 15, apesar da reprovação nos critérios. Ganho histórico
de 0,041%; diagnóstico reutilizado 2021–2022 melhorou no agregado, mas piorou
em 2022. Somente dados oficiais, sem upload e sem garantia de ganho no Kaggle.
S10 permanece a referência pública. [Relatório](reports/competition/round15_experimental/RESULTS.md).
Novas submissões só serão geradas quando solicitadas. Abaixo, histórico.

## Rodada 15 concluída — S10 organizada e preservada

Quatro níveis de regularização da combinação conjunta dos cinco componentes
foram avaliados com pesos aprendidos somente em blocos anteriores. Melhor RMSE
histórico: **1,775343 → 1,774622**, ganho de 0,041%, com melhora em 4/6 blocos e
6/12 anos. Não atingiu os critérios pré-fixados; nenhum CSV S11 ou upload.
S10 intacta, documentação consolidada e índices atualizados. Auditoria e 61 testes
passaram. [Resultados](reports/competition/round15/RESULTS.md) e
[protocolo](experiments/ROUND15.md).

## Rodada 14 concluída — atributos físicos sem ganho

Quatro candidatas com transporte/convergência de umidade derivados dos arquivos
oficiais foram avaliadas. Todas pioraram o RMSE agrupado; melhor resultado
**1,775455**, contra **1,775343** da S10. Hipótese não confirmada nesta configuração.
Nenhum CSV S11 ou upload; S10 intacta. Auditoria e 56 testes passaram, incluindo
fórmula esférica, máscara de pressão e causalidade.
[Resultados](reports/competition/round14/RESULTS.md) e [protocolo](experiments/ROUND14.md).

## Rodada 13 concluída — kernel tropical não aprovado

Quatro versões não lineares do componente tropical avaliadas, mantendo os pesos
e a representação da S10. Melhor RMSE histórico: **1,775343 → 1,773881**,
ganho de 0,082%, com melhora em 4/6 blocos e 7/12 anos. Abaixo dos critérios
pré-fixados; nenhum CSV S11 ou upload. S10 e seus modelos permanecem intactos.
Auditoria, reprodução do controle linear e 51 testes passaram.
[Resultados](reports/competition/round13/RESULTS.md) e [protocolo](experiments/ROUND13.md).

## Rodada 12 concluída — sem nova submissão

Seis correções residuais da S10 avaliadas com dados oficiais. Melhor resultado
histórico: **1,775343 → 1,772613**, ganho de 0,154%, abaixo do mínimo pré-fixado
de 0,3%. Nenhuma candidata aprovada, nenhum CSV S11 ou upload. S10 preservada.
Auditoria e 47 testes passaram. O usuário informou líder com 1,71488 e um envio
restante hoje; esta rodada não consumiu esse envio.
[Resultados](reports/competition/round12/RESULTS.md) e [protocolo](experiments/ROUND12.md).

## S10 aceita — novo melhor público: 1,71895

Score informado pelo usuário: melhora de 0,01062 sobre S09 (cerca de 0,614%).
Faltam 0,01895 para 1,70. A classificação atual e o privado não foram verificados.
CSV, modelos e metadados de geração preservados; retorno registrado no ledger.

[submission_10.csv](submissions/submission_10.csv) adiciona à S09 um modelo
tropical com entradas atmosféricas de 1°, contexto continental e PLS32.
Peso de 25% ao norte de 10°S, transição de 15°S a 10°S; ao sul, S09 preservada.
Somente dados oficiais. Desenvolvimento: **1,780988 → 1,775343** (0,317%),
melhora nos seis blocos. Confirmação já utilizada 2021–2022:
**1,834766 → 1,830283**, melhora nos dois anos. Não são scores do Kaggle.
Arquivo e reprodução conferidos; 44 testes passaram na geração. Upload feito
pelo usuário. S10 passa a ser a referência; nenhum novo treino ou envio iniciado
com esse retorno.
[Protocolo](experiments/ROUND11.md) e [resultados](reports/competition/round11/RESULTS.md).

## Histórico — rodada 10 concluída sem exportação

Seis correções PLS dos resíduos da S09 foram testadas somente com dados oficiais.
A melhor reduziu o RMSE histórico de 1,780988 para 1,777298 (0,207%), abaixo
do mínimo pré-fixado de 0,3%. Nenhuma candidata promovida; nenhum CSV S10 ou
upload. Auditoria aprovada e 40 testes passaram.
[Resultados](reports/competition/round10/RESULTS.md) e [próxima hipótese](experiments/NEXT.md).

## Histórico — S09 aceita com 1,72957

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
| [docs/S10_BASELINE.md](docs/S10_BASELINE.md) | S10: composição, métricas, hashes e limites da evidência |
| [docs/MODELO_ATUAL.md](docs/MODELO_ATUAL.md) | Referência atual e histórico dos modelos |
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
