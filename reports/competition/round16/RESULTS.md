# Rodada 16: correção espacial/sazonal S11

Referência histórica S11: 1.774622. Somente dados oficiais.
Ganho mínimo relativo: 0,3%, com todos os demais critérios de estabilidade.

| Candidata | RMSE | Ganho | Blocos | Anos | Meses | Aprovada |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| sazonal_s12_a0.5 | 1.774102 | 0.029% | 4/6 | 8/12 | 74/144 | False |
| anual_s12_a0.5 | 1.774515 | 0.006% | 4/6 | 8/12 | 74/144 | False |
| anual_s4_a0.5 | 1.774971 | -0.020% | 4/6 | 8/12 | 73/144 | False |
| sazonal_s4_a0.5 | 1.775065 | -0.025% | 4/6 | 5/12 | 72/144 | False |
| anual_s12_a1 | 1.778221 | -0.203% | 3/6 | 7/12 | 63/144 | False |
| sazonal_s12_a1 | 1.780535 | -0.333% | 2/6 | 3/12 | 62/144 | False |
| anual_s4_a1 | 1.781696 | -0.399% | 3/6 | 5/12 | 64/144 | False |
| sazonal_s4_a1 | 1.788036 | -0.756% | 2/6 | 5/12 | 57/144 | False |

Selecionada: nenhuma.
Correções aprendidas somente em blocos anteriores completos; 2005/2007 têm aquecimento causal descrito no protocolo.
Os períodos e a arquitetura foram reutilizados; não se trata de teste independente.
Nenhuma nova submissão CSV ou upload foi feito por este programa.

[Protocolo](../../../experiments/ROUND16.md) · [Seleção](selection.json) · [Diagnóstico](../s11_diagnostic/RESULTS.md)

Nenhuma candidata passou; confirmação e preparação final não foram executadas.
