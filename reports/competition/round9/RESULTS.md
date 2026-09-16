# Rodada 9 — resultados com dados oficiais

RMSE em mm/dia, 144 meses de 2009–2020, grade inteira e pesos uniformes.
Referência S06-forward: componentes da S06, pesos calibrados somente no passado.
Não comparar estes números diretamente ao score público de 2023.

Referência agrupada: **1.788894**; segundos anos: **1.807350**.

| Candidata | RMSE | Ganho relativo | Segundos anos | Blocos melhores | Anos melhores | Meses melhores | Passou? |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| pls16_0.25 | 1.780988 | 0.442% | 1.796871 | 6/6 | 10/12 | 88/144 | Sim |
| pls8_0.5 | 1.781142 | 0.433% | 1.796958 | 5/6 | 9/12 | 77/144 | Não |
| pls16_0.5 | 1.781356 | 0.421% | 1.795049 | 5/6 | 9/12 | 75/144 | Não |
| pls8_0.25 | 1.782197 | 0.374% | 1.799155 | 5/6 | 11/12 | 88/144 | Sim |
| tree15_0.5 | 1.785170 | 0.208% | 1.804190 | 4/6 | 9/12 | 84/144 | Não |
| tree15_0.25 | 1.785349 | 0.198% | 1.803851 | 5/6 | 9/12 | 97/144 | Não |
| tree7_0.5 | 1.785824 | 0.172% | 1.806075 | 5/6 | 8/12 | 83/144 | Não |
| tree7_0.25 | 1.786090 | 0.157% | 1.805264 | 6/6 | 10/12 | 93/144 | Não |

## Decisão

Candidata selecionada no desenvolvimento: **pls16_0.25**.
Se nenhuma candidata passou, não gerar submissão nem gastar envio.

## Resultado por bloco

| Bloco | S06-forward | Melhor entre as oito (seleção retrospectiva) | RMSE |
| --- | ---: | --- | ---: |
| 2009–2010 | 1.857270 | pls8_0.5 | 1.835412 |
| 2011–2012 | 1.782766 | tree15_0.5 | 1.768763 |
| 2013–2014 | 1.709222 | tree15_0.5 | 1.697323 |
| 2015–2016 | 1.774118 | pls8_0.5 | 1.761442 |
| 2017–2018 | 1.820857 | pls16_0.25 | 1.817036 |
| 2019–2020 | 1.785689 | pls16_0.5 | 1.771543 |

A melhor candidata de cada bloco acima não é um modelo selecionável em tempo real.
A decisão usa uma única configuração entre todos os blocos, não escolhe um vencedor por ano.

## Limitações e conformidade

- Caches oficiais conferidos contra todos os valores dos NetCDF; cache espacial reproduzido exatamente.
- Sem NOAA, S07/S08, modelos externos ou chuva oculta do teste.
- Corretores treinados somente em blocos anteriores de previsões fora do treino.
- Seleção anterior de arquitetura e desenvolvimento reutilizado impedem alegar teste inteiramente independente.
- 2021–2022 já foi consumido na rodada 8. Se usado aqui, serve apenas como confirmação adicional.
- Nenhum RMSE local garante score 1,70, liderança pública ou resultado privado.
- Nenhum upload automático foi realizado.

[Protocolo congelado](../../../experiments/ROUND9.md) · [Seleção detalhada](selection.json) · [Auditoria](audit.json)

## Confirmação 2021–2022 (período previamente utilizado)

pls16_0.25: 1.841795 → 1.834766.
Passou: sim. Nenhum ajuste posterior autorizado pelo protocolo.
