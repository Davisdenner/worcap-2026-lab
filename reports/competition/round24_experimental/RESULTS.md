# S13 experimental — confirmação dispensada para teste público

O usuário autorizou gerar uma S13 de teste apesar do ganho histórico de
0,0078% ficar abaixo do mínimo de 0,3%. A primeira exceção dispensou apenas
esse mínimo. A candidata preservada é `transporte_lag_norte_b0.5`.

Na confirmação reutilizada de 2021–2022, treinando somente com alvos até
dezembro/2020, o RMSE S12 foi **1,821386** e o da candidata **1,821341**:
ganho relativo de **0,00247%**, abaixo dos 0,1% exigidos. Em 2021 houve
melhora (1,807099 → 1,806934), mas 2022 piorou
(1,835561 → 1,835635). A confirmação **falhou**.

O usuário autorizou em mensagem posterior prosseguir para um **teste exploratório**
apesar dessa reprovação. A [dispensa registrada](confirmation_waiver.json) não
altera o resultado da confirmação nem o mínimo histórico de 0,3% para
promoção de modelos futuros. O corretor final usou apenas alvos até
dezembro/2022 e os dados oficiais da competição.

O RMS da mudança em relação à S12 foi **0,004644** em 2023 e **0,005210**
em 2024; ambos abaixo do limite predefinido de **0,014905**. O CSV S13 foi
gerado e conferido: **1.885.464** linhas, `id,tp_mm_day`, IDs exatamente na
ordem do sample oficial, valores finitos e não negativos. SHA-256:
`9d907d42d3950bc4faa0f0051655a00a082d25021e207a2596e5745ff9815ecb`.
O pipeline **não fez upload**. O usuário informou que enviou manualmente a S13
e obteve score público **1,71461**, corrigindo relato anterior de 1,71456.
Isso é **0,00005 pior** que a S12 no público. O resultado não foi verificado
independentemente; classificação atual e score privado seguem desconhecidos.
A S12 permanece a referência reproduzível. A reprovação da confirmação da
S13 e os critérios históricos continuam registrados sem alteração.

[Resultado da confirmação](confirmation.json) · [Autorização original](authorization.json) · [Metadados da S13](../../../submissions/submission_13.json)
