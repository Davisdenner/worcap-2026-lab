# Submissões e rastreabilidade

Melhor público informado: **S11, 1,71718**. Controle aprovado: **S10, 1,71895**.
S11 foi uma exceção autorizada; os [critérios](../experiments/PROTOCOL.md)
continuam ativos, incluindo ganho histórico mínimo de 0,3%.

O [manifesto](manifest.json) registra os arquivos, tamanhos, hashes, scores e
metadados. O [histórico público](../reports/competition/leaderboard_observations.json)
é a fonte dos resultados relatados após os envios. Os JSONs originais de geração
são snapshots anteriores ao envio; não atualizá-los retroativamente.

CSVs enviados ficam localmente nesta pasta e são ignorados pelo Git. Nunca
sobrescrevê-los. Um clone novo recebe metadados e hashes, não esses CSVs.
O [guia de reprodução](../docs/REPRODUCAO.md) retreina componentes e cria cópias
S10/S11 em `data/processed/reproducao/saidas_verificadas`, verificando seus hashes originais.

Todas as saídas têm cabeçalho `id,tp_mm_day`, 1.885.464 linhas e IDs do sample
oficial na ordem exata. O fluxo não exige renomear um CSV para uma avaliação
local; os nomes numerados são convenções internas de rastreabilidade.

S07/S08 permanecem no histórico, mas não são bases da linha restrita a dados
oficiais da organização. S09–S11 não usam direta ou indiretamente seus componentes
externos. Para o método, consulte [METODOLOGIA.md](../docs/METODOLOGIA.md).

Registrar próximas versões só após geração solicitada, validação e preservação
do artefato. Resultados públicos entram somente quando informados. Nenhum upload
é automático e nenhum score privado é inferido do público.
