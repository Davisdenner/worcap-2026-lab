# Evidências e reprodução S12

A melhor pública informada é S12, 1,71456. Seu corretor é retreinável a partir
de nove arquivos `evidence/*_samples.npz` (aproximadamente 34,6 MB no total).
São 442.368 exemplos fora do treino derivados exclusivamente dos dados oficiais,
com 23 atributos e resíduo-alvo, não um modelo previamente ajustado. O
[manifesto](evidence/manifest.json) registra hashes, cortes e fontes oficiais.

Essas evidências devem acompanhar o código no commit/pacote técnico; os NC brutos
continuam obtidos pelo participante na competição. Os exemplos são dados
derivados e não recebem automaticamente a licença do código. Respeitar os termos
dos dados na distribuição do pacote. Nenhuma publicação ou push foi feito.

Use [REPRODUCAO.md](../../docs/REPRODUCAO.md). Não é preciso obter o CSV original,
modelos salvos ou caches de pesquisa para iniciar o fluxo. Ele treina os
componentes S11 a partir dos NC e o corretor a partir destas evidências; não
regenera toda a pesquisa OOF. A geração das evidências originais está nos códigos
`round16`/`round17`; o empacotador `scripts/package_s12_evidence.py` é uma ferramenta
do mantenedor e depende do ambiente histórico, não uma etapa do primeiro acesso.

O hash esperado do CSV está no catálogo, independentemente da execução:
`bba1f8b279447868170b6b2f9b18ee2cc723b891c25627c91438c7725d3aead8`.
Usar Python 3.11.1 e as dependências fixadas da entrega S11. Nenhuma dependência
foi adicionada para S12. A inferência só carrega modelos verificados e a atmosfera
oficial; não lê alvos ocultos nem requer credenciais.
