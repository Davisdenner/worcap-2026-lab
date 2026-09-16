# Pipelines executados

Referência pública atual: **S10, 1,71895**. Consulte a
[composição consolidada](../docs/S10_BASELINE.md). Os scripts antigos são
dependências congeladas; não editar para experimentar nem sobrescrever modelos.

| Pipeline atual | Função |
| --- | --- |
| [round9.py](round9.py) | S09 oficial e pesos históricos com cortes temporais |
| [round11.py](round11.py) | Componente tropical fino e geração da S10 |
| [round12.py](round12.py) | Reconstrução das bases S10; correção residual rejeitada |
| [round15.py](round15.py) | Recalibração conjunta dos cinco componentes, sem upload |

## Pipelines iniciais e dependências

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
