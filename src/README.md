# Pipelines executados

| Arquivo | Função | Dependências locais principais |
| --- | --- | --- |
| [competition.py](competition.py) | Auditoria, cache, climatologias, ridge anual e resumo inicial | NetCDF oficiais |
| [atmospheric_trees.py](atmospheric_trees.py) | Árvores locais iniciais | Cache e seleção de climatologia |
| [round2.py](round2.py) | Contexto, validação ampliada e S02 | Rodada inicial e cache |
| [round3.py](round3.py) | Modos regionais, sazonalidade e S03 | Cache e previsões S02 |
| [submission.py](submission.py) | Exportação e verificação de CSV com coordenadas | NetCDF de previsões e grade oficial |

Os nomes e caminhos dos pipelines foram mantidos para preservar reprodução e
metadados. As pastas vazias `data`, `features`, `models`, `validation` e
`visualization` são do esqueleto inicial; não são módulos usados pelos scripts.

Os comandos completos estão em [docs/REPRODUCAO.md](../docs/REPRODUCAO.md).
