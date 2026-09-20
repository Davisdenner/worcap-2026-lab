# S10: controle aprovado e preservado

A S10 obteve RMSE público **1,71895** no envio. S11 obteve
1,71718 e é a melhor pública, mas permanece uma exceção aos critérios históricos.

## Identidade do artefato

CSV original local: `submissions/submission_10.csv`, 1.885.464 linhas,
colunas `id,tp_mm_day`, IDs na ordem oficial. Não sobrescrever.

```text
SHA-256: 57862493c62936b291c03cff3bd4c53fd486ab38a08108f908a8f74b5aada46e
```

[Metadados originais](../submissions/submission_10.json),
[manifesto](../submissions/manifest.json) e
[resultados públicos posteriores](../reports/competition/leaderboard_observations.json).
Os campos `uploaded=false`/`public_score=null` nos metadados originais retratam
o momento anterior ao envio; não devem ser reescritos para apagar essa história.

## Evidência de seleção

Desenvolvimento 2009 a 2020: S09 1,780988 → S10 **1,775343**, melhora em
6/6 blocos, 9/12 anos e 85/144 meses. Ganho relativo aproximado de 0,317%.
Confirmação reutilizada 2021 a 2022: 1,834766 → **1,830283**, ambos os anos melhores.
Esses valores não são scores Kaggle nem testes independentes de toda a pesquisa.

[Protocolo original](../experiments/ROUND11.md),
[resultados](../reports/competition/round11/RESULTS.md) e
[verificação original](../reports/competition/round11/verification.json).
S10 foi gerada na rodada 11; números de rodadas e submissões não são iguais.

A descrição única da composição está em [METODOLOGIA.md](METODOLOGIA.md).
Para retreinar e obter um CSV idêntico, siga [REPRODUCAO.md](REPRODUCAO.md)
com `--versao s10`. Não é necessário reexecutar as rodadas rejeitadas 12 a 15.
A exportação posterior S11 foi uma exceção documentada na
[rodada experimental](../experiments/ROUND15_EXPERIMENTAL.md).
