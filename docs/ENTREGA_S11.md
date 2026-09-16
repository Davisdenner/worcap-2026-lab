# Entrega S11 e fluxo atual de reprodução

S11 original preservada, RMSE público informado **1,71718**. Melhor pública,
mas exceção autorizada após reprovação histórica. Ganho mínimo de 0,3% e demais
[critérios](../experiments/PROTOCOL.md) continuam vigentes.

Para reproduzir S10 ou S11 no repositório atual, use [REPRODUCAO.md](REPRODUCAO.md).
O método foi centralizado em [METODOLOGIA.md](METODOLOGIA.md), sem duplicar aqui
a descrição dos modelos. O catálogo permite selecionar `s10`, `s11` ou `melhor`.

## Material da entrega anterior

- [Guia do pacote técnico](../delivery/s11/README.md).
- [Comandos da interface anterior](../delivery/s11/entry_points.md).
- [Dependências fixadas](../delivery/s11/requirements.txt).
- [Comparação anterior com a S11 original](../delivery/s11/verification/reproduction_comparison.json).
- [Licenças de terceiros](../delivery/s11/THIRD_PARTY_NOTICES.md).
- [Identificação da equipe](../delivery/s11/TEAM_INFO.json).

O ZIP `delivery/s11_delivery_draft.zip` é um snapshot técnico anterior, local,
fora do Git. Não foi sobrescrito pela organização da documentação. As edições
posteriores no repositório não alteram seu conteúdo. Seu inventário permanece
em [s11_archive.json](../delivery/s11_archive.json).

O treino final e a inferência foram reproduzidos; a calibração usa estatísticas
históricas e pesos-base congelados. Não foi reexecutada toda a pesquisa histórica.
Os wheels offline foram reempacotados das distribuições instaladas, não baixados
originalmente dos editores; não estão incluídos automaticamente em um clone.

A entrega definitiva ainda precisa de licença confirmada, dados da equipe e
revisão do pacote da versão final. Consulte [CONFORMIDADE.md](CONFORMIDADE.md).
Não houve nova candidata, commit, publicação ou envio por este fluxo.
