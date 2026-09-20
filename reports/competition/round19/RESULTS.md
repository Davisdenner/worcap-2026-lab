# Rodada 19: histórico ampliado: nenhuma candidata aprovada

Referência fixa S12 `meta15_a0.25`, RMSE histórico **1,770775491**.
Foram adicionados 196.608 exemplos OOF oficiais de 1997 a 2004. O conjunto final
potencial teria 26 anos, mas **não houve treinamento final para uma S13**.
As duas configurações foram congeladas antes de avaliar resultados.

## Desenvolvimento completo: 2009 a 2020

| Candidata | RMSE | Ganho relativo contra S12 | Blocos melhores | Anos melhores | Meses melhores |
| --- | ---: | ---: | ---: | ---: | ---: |
| Histórico ampliado, recência com meia-vida de 8 anos | 1,770779761 | −0,000241% | 4/6 | 6/12 | 74/144 |
| Histórico ampliado, pesos iguais | 1,770868709 | −0,005264% | 4/6 | 6/12 | 71/144 |

Ganho negativo significa piora. A diferença da primeira candidata é praticamente
um empate numérico, não uma melhoria demonstrada. Nenhuma alcançou o mínimo de
0,3%, cinco blocos, nove anos ou 80 meses melhores. Ambas também pioraram o
RMSE agregado dos segundos anos contra 1,784610989 da S12. A pior degradação
anual ficou abaixo de 0,5%, mas isso não compensa os demais critérios reprovados.

| Bloco | S12 | Pesos iguais | Recência 8 anos |
| --- | ---: | ---: | ---: |
| 2009 a 2010 | 1,841011 | 1,839862 | 1,840477 |
| 2011 a 2012 | 1,752162 | 1,754141 | 1,753591 |
| 2013 a 2014 | 1,695158 | 1,695639 | 1,695034 |
| 2015 a 2016 | 1,760122 | 1,759923 | 1,759923 |
| 2017 a 2018 | 1,810436 | 1,810062 | 1,809916 |
| 2019 a 2020 | 1,762162 | 1,762075 | 1,762175 |

## Decisão

- `selected: null`, sem exceção ao critério de 0,3%.
- Não consultar confirmação 2021 a 2022 para escolher outra configuração.
- Não treinar candidata final nem gerar previsão/CSV S13.
- Nenhum upload ou consumo de envio pelo assistente.
- S12 continua a melhor pública informada: 1,71456; seu CSV não foi alterado.

A hipótese testada não produziu ganho robusto. Isso não prova que todo uso de
histórico antigo seja inútil: antes de 2005 usamos aquecimento causal com prior
S10 fixo, e o desenho testou apenas duas ponderações predefinidas. Não ampliar
essa busca ou alterar frações retroativamente para tentar fazer passar os critérios.

## Reprodução e auditoria

Os 196.608 exemplos adicionais foram conferidos contra a atmosfera oficial em
todas as colunas amostradas e contra os alvos oficiais, respeitando a quantização
float32 de referência e resíduo. Os modelos-base de cada bloco só usaram alvos
anteriores ao corte. A auditoria está em [history_audit.json](history_audit.json).

```powershell
.\.venv\Scripts\python.exe -m src.round19_history
.\.venv\Scripts\python.exe scripts/audit_round19_history.py
.\.venv\Scripts\python.exe -m src.round19 evaluate
.\.venv\Scripts\python.exe -m src.round19 select
```

Esses comandos são de pesquisa e dependem dos caches históricos oficiais das
rodadas anteriores; não são o guia de primeiro acesso para reproduzir S12.
Para isso, use o [fluxo de reprodução](../../../docs/REPRODUCAO.md), agora com
S12 integrada. O corretor S12 foi retreinado e o CSV reconstruído ficou
idêntico ao original: [relatório](../../reproducao/S12.md).

Registros congelados: [protocolo](../../../experiments/ROUND19.md),
[hashes de código e protocolo](protocol.json), [seleção completa](selection.json)
e JSON de cada bloco nesta pasta. Períodos e arquitetura reutilizados: não
alegar significância estatística ou garantia de desempenho privado.
