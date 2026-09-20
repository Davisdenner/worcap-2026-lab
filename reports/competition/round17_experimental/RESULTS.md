# S12 experimental: variante conservadora autorizada

## Resultado público posterior à geração

O envio devolveu **1,71456 e segundo lugar**. Melhora de 0,00262 (0,153%)
contra S11. É a nova melhor pública informada, sem verificação independente
do leaderboard. Se o último score do líder, 1,70328, permanecer, faltam 0,01128.
O resultado não altera a reprovação automática nem informa o desempenho privado.
Os metadados de geração e o registro original abaixo foram preservados.

## Registro da geração

CSV gerado em 16/09/2026, sem upload. Candidata fixa `meta15_a0.25`, correção
não linear de resíduos da S11 com fração 0,25 e somente dados oficiais.

## Evidência antes do envio

| Período | RMSE S11 | RMSE S12 | Resultado |
| --- | ---: | ---: | --- |
| Desenvolvimento 2009 a 2020 | 1,774621760 | 1,770775491 | Ganho 0,216737%; abaixo de 0,3% |
| Confirmação 2021 a 2022 | 1,829353225 | 1,821385840 | Ganho 0,435530%; passou |
| 2021 | 1,816626645 | 1,807099476 | Melhorou |
| 2022 | 1,841991876 | 1,835561015 | Melhorou |

Desenvolvimento: 5/6 blocos, 10/12 anos e 88/144 meses melhores; pior perda
anual de 0,351990%, dentro do limite de 0,5%. A autorização dispensa somente
o mínimo de ganho de desenvolvimento para esta exportação. A seleção original
continua `selected: null`; **não houve promoção automática**. O critério geral
de 0,3% continua ativo. A confirmação 2021 a 2022 é reutilizada, não independente.

Não se ajustaram candidata, fração ou hiperparâmetros depois da confirmação.
O corretor de confirmação usou alvos até dezembro de 2020. O final usou
442.368 exemplos em blocos históricos até dezembro de 2022.

## Limite de mudança e verificações

RMS histórico da mudança: 0,076332551 mm/dia; teto por ano: 0,152665103.
RMS em 2023: 0,061363309; em 2024: 0,059454632. Ambos passaram. Esses valores
medem distância entre previsões, **não erro contra os alvos ocultos**.

- Modelo final recarregado: previsões idênticas em todos os pontos dos 24 meses.
- Valores do NetCDF idênticos após leitura; exportador verificou todo o CSV.
- Verificação independente: 1.885.464 linhas, duas colunas, IDs únicos e ordem
  integral do sample oficial, valores finitos/não negativos e hash correto.
- Conferência independente adicional de 130 coordenadas/valores contra o NetCDF.
- S10, S11, metadados originais e seleção original preservados por hash.
- 85 testes passaram com `python -m unittest discover -s tests -q`.

Arquivo: `submissions/submission_12.csv`, 63.346.800 bytes.
SHA-256: `bba1f8b279447868170b6b2f9b18ee2cc723b891c25627c91438c7725d3aead8`.
Score público desconhecido. A melhor pública informada continua S11, 1,71718.
Não há garantia de melhora no Kaggle, de 1,70 ou de liderança.

## Proveniência

- [Autorização e proteção dos originais](authorization.json).
- [Confirmação](confirmation.json).
- [Limite de mudança](test_shift.json).
- [Verificação de geração](verification.json).
- [Metadados completos da submissão](../../../submissions/submission_12.json).
- [Método, execução e limites atuais de reprodução](../../../docs/S12_EXPERIMENTAL.md).
- [Protocolo da exceção](../../../experiments/ROUND17_EXPERIMENTAL.md).

O fluxo atual depende de artefatos históricos locais de pesquisa. A reprodução
completa em clone vazio da S12 ainda não foi integrada à interface S10/S11;
não confundir a inferência recarregada e verificada com essa integração pendente.
