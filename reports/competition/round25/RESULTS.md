# Rodada 25: diagnóstico, PCs com ordem e análogos

S12 histórica: 1.770775491. Seis blocos 2009 a 2020 reutilizados.

| Candidata | RMSE | Ganho relativo | Blocos | Anos | Meses | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| h4_a0.1 | 1.769921448 | 0.0482% | 4/6 | 8/12 | 79/144 | False |
| h2_a0.1 | 1.771140013 | -0.0206% | 2/6 | 4/12 | 66/144 | False |
| h4_a0.25 | 1.772253325 | -0.0835% | 2/6 | 6/12 | 68/144 | False |
| h2_a0.25 | 1.773587071 | -0.1588% | 1/6 | 4/12 | 61/144 | False |

Selecionada: nenhuma.

## Modelos puros por bloco

| Bloco | H2 controle | H2 lag1 | Climatologia | H4 análogos |
| --- | ---: | ---: | ---: | ---: |
| 2009 a 2010 | 1.892886 | 1.898134 | 1.975282 | 1.936753 |
| 2011 a 2012 | 1.807620 | 1.803721 | 1.849763 | 1.806235 |
| 2013 a 2014 | 1.734047 | 1.737126 | 1.750749 | 1.779481 |
| 2015 a 2016 | 1.823734 | 1.823654 | 1.861463 | 1.816725 |
| 2017 a 2018 | 1.824154 | 1.825563 | 1.848138 | 1.885788 |
| 2019 a 2020 | 1.815413 | 1.824614 | 1.847074 | 1.854264 |

O diagnóstico completo está em DIAGNOSTIC.md e diagnostic.json.
Produtos cruzados e correlações de erros por bloco/região/estação constam nos JSON de cada bloco.
Nenhum alvo de 2023 a 2024 foi lido. Nenhum CSV ou upload foi gerado.
