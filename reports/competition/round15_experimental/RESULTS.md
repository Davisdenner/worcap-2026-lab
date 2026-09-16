# S11 experimental — joint1, solicitada pelo usuário

## Retorno público posterior à geração

Usuário informou **1,71718**, melhora de 0,00177 (0,103%) sobre S10 (1,71895).
S11 passa a ser a melhor pública confirmada. Isso não altera a reprovação
histórica, não demonstra significância estatística e não informa o privado.
O upload foi feito pelo usuário. CSV, metadados e avaliações originais
preservados; aceitação registrada separadamente no ledger e manifesto.
Nenhuma nova candidata ou envio iniciado com esse retorno.

## Registro original de geração

S11 exportada por autorização explícita após a reprovação da rodada 15.
Não houve alteração dos critérios, escolha de outro modelo ou ajuste posterior
ao diagnóstico. S10 permanece a melhor pública confirmada (1,71895).
Nenhum upload foi realizado; score público e privado da S11 são desconhecidos.

## Evidência e risco

Desenvolvimento 2009–2020: RMSE **1,775343 → 1,774622**, ganho **0,041%**,
melhora em **4/6 blocos e 6/12 anos**. Reprovada nos critérios de ganho,
blocos e anos. A seleção original continua `selected: null`.

Diagnóstico adicional no período já reutilizado de 2021–2022:

| Período | S10 | S11 experimental |
| --- | ---: | ---: |
| 2021 | 1,820079 | 1,816627 |
| 2022 | 1,840430 | 1,841992 |
| Agregado | 1,830283 | 1,829353 |

O agregado melhorou, mas **2022 piorou**; a confirmação também não atingiu
os critérios originais. Não é um holdout independente e não garante melhora
no Kaggle. Não há base para prometer 1,70.

RMS da mudança contra S10: histórico 0,051990; 2023 0,035527; 2024 0,041895.
As duas mudanças ficaram abaixo do limite original de duas vezes o histórico.
Isso verifica magnitude, não qualidade nas respostas ocultas.

## Artefatos e reprodução

- [CSV S11](../../../submissions/submission_11.csv) e [metadados](../../../submissions/submission_11.json).
- [Autorização e escopo](../../../experiments/ROUND15_EXPERIMENTAL.md).
- [Diagnóstico](confirmation.json), [magnitude](test_shift.json) e [verificação](verification.json).
- Exportador: `python -m src.round15_experimental --user-authorized`.

Cinco componentes oficiais existentes, lambda 1, 12 grupos fixos, pesos
convexos limitados a 0,10 de mudança do prior S10. Calibração final com blocos
2005–2022, sem chuva oculta de 2023/2024 e sem fontes externas.
1.885.464 linhas, colunas `id,tp_mm_day`, ordem oficial do sample, valores
finitos e não negativos. Previsões reconstruídas integralmente dos componentes
e pesos salvos; S10 e seleção original preservadas por hash.

Gerar novas submissões somente quando o usuário pedir. Aguardar resultado
informado pelo usuário; não promover S11 nem consumir envios automaticamente.
