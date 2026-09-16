# Reprodução verificada de S10 e S11

Em 16/09/2026 foram preparados novos arrays dos arquivos oficiais, retreinados
todos os componentes finais e executada a inferência para ambas as versões.
Os artefatos históricos de calibração foram preservados, não regenerados em
uma nova pesquisa de blocos. O [relatório estruturado](2026-09-16.json) registra
hashes, ambiente, tempos, memória, escopo e comparações.

| Verificação | S10 | S11 |
| --- | --- | --- |
| CSV idêntico ao enviado | Sim | Sim |
| Valores do NetCDF idênticos ao original | Sim | Sim |
| Diferença máxima nas previsões | 0 | 0 |
| Linhas e ordem oficial | 1.885.464, verificadas | 1.885.464, verificadas |

Preparação: aproximadamente 71 s. Treino final: 103 s, pico de processo de
aproximadamente 2,3 GiB. Inferência: 103 s (S10) e 98 s (S11). Esses tempos
se referem ao host Windows de referência, não são requisitos universais.

Passaram 72 testes unitários e a auditoria dos 11 registros de submissões.
As verificações dos dois CSVs também foram repetidas no ambiente Python
separado já instalado. Não foi realizado novo upload, busca de modelos ou
alteração dos CSVs enviados. O critério mínimo histórico de 0,3% continua ativo.

A primeira tentativa detectou arredondamento diferente em duas linhas da S10.
Recarregar as transformações PCA após serializar, como no fluxo original,
eliminou a diferença. Não foram corrigidos valores manualmente nem mudados
hashes esperados. As tentativas locais ficam fora do Git, em `data/processed`.

Use o [guia atual](../../docs/REPRODUCAO.md) para repetir a execução. A explicação
do modelo está em [METODOLOGIA.md](../../docs/METODOLOGIA.md). Licença, identificação
da equipe e revisão do pacote final ainda são pendências de entrega.
