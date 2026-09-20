# Índice das rodadas experimentais

O [resumo final](../docs/ENCERRAMENTO.md) consolida resultados e limites até a rodada 29; a [síntese das rodadas 25–34](../docs/SINTESE_RODADAS_25_34.md) explica por que o platô se manteve. Os documentos abaixo preservam hipóteses, protocolos e decisões contemporâneas. **S12** permanece a melhor submissão pública informada (1,71456).

| Rodada | Tema | Evidência principal |
| --- | --- | --- |
| 1 | Climatologia e modelos iniciais | [Resultados](../reports/competition/RESULTS.md) |
| [2](ROUND2.md) | Contexto espacial e temporal; S02 | [Resultados](../reports/competition/round2/RESULTS.md) |
| [3](ROUND3.md) | Padrões regionais e sazonalidade; S03 | [Resultados](../reports/competition/round3/RESULTS.md) |
| [4](ROUND4.md) | Memória e pesos regionais; S04 | [Seleção](../reports/competition/round4/selection.json) |
| [5](ROUND5.md) | Escala espacial e não linearidade; S05 | [Seleção](../reports/competition/round5/selection.json) |
| [6](ROUND6.md) | Memória atmosférica local; S06 | [Seleção](../reports/competition/round6/selection.json) |
| [7](ROUND7.md) | Regressão local/continental; S07 | [Seleção](../reports/competition/round7/selection.json) |
| [8](ROUND8.md) | Atlântico tropical; S08 | [Seleção](../reports/competition/round8/selection.json) |
| [9](ROUND9.md) | Linhagem só com dados oficiais; S09 | [Resultados](../reports/competition/round9/RESULTS.md) |
| [10](ROUND10.md) | Diagnóstico e representação atmosférica | [Resultados](../reports/competition/round10/RESULTS.md) |
| [11](ROUND11.md) | Modelo tropical fino; S10 | [Resultados](../reports/competition/round11/RESULTS.md) |
| [12](ROUND12.md) | Correção residual | [Resultados](../reports/competition/round12/RESULTS.md) |
| [13](ROUND13.md) | Componente tropical não linear | [Resultados](../reports/competition/round13/RESULTS.md) |
| [14](ROUND14.md) | Atributos físicos de umidade | [Resultados](../reports/competition/round14/RESULTS.md) |
| [15](ROUND15.md) | Recalibração conjunta; S11 experimental | [Resultados](../reports/competition/round15/RESULTS.md) · [exceção](../reports/competition/round15_experimental/RESULTS.md) |
| [16](ROUND16.md) | Correção espacial e sazonal | [Resultados](../reports/competition/round16/RESULTS.md) |
| [17](ROUND17.md) | Correção não linear; S12 experimental | [Resultados](../reports/competition/round17/RESULTS.md) · [exceção](../reports/competition/round17_experimental/RESULTS.md) |
| [18](ROUND18.md) | Memória tropical longa | [Resultados](../reports/competition/round18/RESULTS.md) |
| [19](ROUND19.md) | Histórico ampliado do corretor S12 | [Resultados](../reports/competition/round19/RESULTS.md) |
| [20](ROUND20.md) | Árvores diretas locais e globais | [Resultados](../reports/competition/round20/RESULTS.md) |
| [21](ROUND21.md) | Especialistas regionais | [Resultados](../reports/competition/round21/RESULTS.md) |
| [22](ROUND22.md) | Início do treino em 1940/1960/1981 | [Resultados](../reports/competition/round22/RESULTS.md) |
| [23](ROUND23.md) | Saída ampla e detalhe espacial | [Resultados](../reports/competition/round23/RESULTS.md) |
| [24](ROUND24.md) | Transporte de umidade; S13 experimental | [Resultados](../reports/competition/round24/RESULTS.md) · [exceção](../reports/competition/round24_experimental/RESULTS.md) |
| [25](ROUND25.md) | Diagnóstico S12, PCs e análogos | [Decisão](../reports/competition/round25/DECISION.md) |
| [26](ROUND26.md) | Previsibilidade do erro no norte | [Relatório](../reports/competition/round26/REPORT.md) |
| [27](ROUND27.md) | Seleção S12 × análogos | [Relatório](../reports/competition/round27/REPORT.md) · [CSV exploratório](S14_EXPERIMENTAL_ROUND27_GATE.md) |
| [28](ROUND28.md) | Magnitude da vantagem e top-k | [Relatório](../reports/competition/round28/REPORT.md) |
| [29](ROUND29.md) | Novas famílias e viabilidade CNN/U-Net | [Relatório](../reports/competition/round29/REPORT.md) |
| [30](ROUND30.md) | Gate convolucional com contexto 2D, treinado em GPU no Kaggle | [Relatório](../reports/competition/round30/REPORT.md) · [preparo](ROUND30_KAGGLE_SETUP.md) |
| [32](ROUND32.md) | U-Net ponta a ponta sobre os campos atmosféricos | [Relatório](../reports/competition/round32/REPORT.md) |
| [33](ROUND33.md) | Volume de células do corretor, 10,7× | [Relatório](../reports/competition/round33/REPORT.md) |
| [34](ROUND34.md) | Capacidade do corretor em número de folhas | [Protocolo congelado](../reports/competition/round34/protocol.json) |
| [35](ROUND35.md) | Persistência de precipitação como preditor | [Decisão](../reports/competition/round35/decision.json) |
| [36](ROUND36.md) | Corretor máximo: 127 atributos, 8.192 células, 255 folhas | [Decisão](../reports/competition/round36/decision.json) |

Não existe rodada 31: o número foi consumido por um diagnóstico de recalibração de amplitude, registrado em [slope_diagnostic](../reports/competition/slope_diagnostic/RESULTS.md) e citado na síntese como "31-diag".

## Diagnósticos fora da numeração

Investigações que mediram o tamanho de uma oportunidade **antes** de construir uma rodada, com o critério de decisão declarado por escrito antes da execução. Nenhuma treina modelo novo nem gera CSV.

| Diagnóstico | Pergunta | Resultado |
| --- | --- | --- |
| [slope](../reports/competition/slope_diagnostic/RESULTS.md) | A amplitude da anomalia está mal calibrada? | [RESULTS.md](../reports/competition/slope_diagnostic/RESULTS.md) |
| [mfc](../reports/competition/mfc_diagnostic/RESULTS.md) | A convergência de fluxo de umidade explica o resíduo? | [RESULTS.md](../reports/competition/mfc_diagnostic/RESULTS.md) |
| [oni](../reports/competition/oni_diagnostic/RESULTS.md) | O ENSO explica o resíduo? | [RESULTS.md](../reports/competition/oni_diagnostic/RESULTS.md) |
| [clim](../reports/competition/clim_diagnostic/RESULTS.md) | A janela de climatologia está no tamanho certo? | [RESULTS.md](../reports/competition/clim_diagnostic/RESULTS.md) |
| [persist](../reports/competition/persist_diagnostic/RESULTS.md) | A chuva observada na origem carrega sinal ausente? | [RESULTS.md](../reports/competition/persist_diagnostic/RESULTS.md) |

O [protocolo geral](PROTOCOL.md) define o gate histórico. O [registro cronológico](NEXT.md) contém a discussão de hipóteses e decisões, inclusive as direções que ainda estavam abertas quando foi escrito. Nenhuma rodada posterior à S12 produziu melhora pública registrada.
