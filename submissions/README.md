# Submissões e rastreabilidade

A participação foi encerrada após a rodada 29. O [resumo final](../docs/ENCERRAMENTO.md) reúne todos os resultados públicos conhecidos.

Melhor público informado: **S12, 1,71456**. A S13 marcou **1,71461**,
0,00005 acima em RMSE; classificação final não informada.
Controle aprovado: **S10, 1,71895**. S11 e S12 foram exceções autorizadas; os [critérios](../experiments/PROTOCOL.md)
foram aplicados historicamente, incluindo ganho mínimo de 0,3%.

S12 melhorou o score público em 0,00262 contra S11 (1,71718). Consulte os
[metadados originais](submission_12.json) e o [guia da S12](../docs/S12_EXPERIMENTAL.md).
O catálogo executável inclui S12 em seu atalho `melhor`, usando evidências OOF
congeladas para retreinar o corretor. Nenhum upload é automático; não inferir resultado privado.

O [manifesto](manifest.json) registra os arquivos, tamanhos, hashes, scores e
metadados. O [histórico público](../reports/competition/leaderboard_observations.json)
é a fonte dos resultados relatados após os envios. Os JSONs originais de geração
são snapshots anteriores ao envio; não atualizá-los retroativamente.

CSVs enviados ficam localmente nesta pasta e são ignorados pelo Git. Nunca
sobrescrevê-los. Um clone novo recebe metadados e hashes, não esses CSVs.
O [guia de reprodução](../docs/REPRODUCAO.md) retreina componentes e cria cópias
S10/S11/S12 em `data/processed/reproducao/saidas_verificadas`, verificando seus hashes originais.

Todas as saídas têm cabeçalho `id,tp_mm_day`, 1.885.464 linhas e IDs do sample
oficial na ordem exata. O fluxo não exige renomear um CSV para uma avaliação
local; os nomes numerados são convenções internas de rastreabilidade.

S07/S08 permanecem no histórico, mas não são bases da linha restrita a dados
oficiais da organização. S09–S11 não usam direta ou indiretamente seus componentes
externos. Para o método, consulte [METODOLOGIA.md](../docs/METODOLOGIA.md).

Registrar próximas versões só após geração solicitada, validação e preservação
do artefato. Resultados públicos entram somente quando informados. Nenhum upload
é automático e nenhum score privado é inferido do público.

A S13 experimental foi gerada para teste por pedido expresso do usuário,
dispensando pontualmente o mínimo histórico de 0,3% e a confirmação
2021–2022 reprovada. O resultado negativo da confirmação foi preservado e o
limite de mudança no teste passou. Consulte o [relatório](../reports/competition/round24_experimental/RESULTS.md)
e os [metadados de geração](submission_13.json). O usuário informou o envio
manual e score público **1,71461**, corrigindo relato anterior de 1,71456.
O [manifesto](manifest.json) registra esse relato sem modificar o snapshot
de geração; score privado e classificação final permanecem desconhecidos.
O atalho de reprodução `melhor` continua em S12, não em S13.

Um [CSV S14 exploratório](S14_experimental_round27_gate.md) foi produzido após
a rodada 27, sem upload automático e sem score público registrado. Seu registro
de geração é separado do manifesto de submissões com resultado informado.
