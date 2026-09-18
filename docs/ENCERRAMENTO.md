# Encerramento da participação — WORCAP 2026

**Estado em 18/09/2026:** participação encerrada por decisão do participante. A melhor submissão pública registrada foi a **S12, RMSE 1,71456**. As rodadas posteriores não a superaram. O score privado e a classificação final não constam dos registros.

Os scores públicos abaixo foram informados pelo participante após os envios; não foram verificados diretamente no leaderboard. Menor RMSE é melhor. Os experimentos locais usam validação histórica e não equivalem ao score público.

## Resultado das submissões

| Arquivo | RMSE público informado | Registro |
| --- | ---: | --- |
| Climatologia inicial | 1,85468 | Referência de partida |
| S02 | 1,81543 | Contexto espacial e temporal |
| S03 | 1,76467 | Padrões regionais e sazonalidade |
| S04 | 1,74906 | Combinação com memória atmosférica |
| S05 | 1,74613 | Escala espacial e não linearidade |
| S06 | 1,74505 | Memória local |
| S07 | 1,73550 | Linha com informação externa |
| S08 | 1,74606 | Linha com informação externa |
| S09 | 1,72957 | Retorno à linha restrita a dados oficiais |
| S10 | 1,71895 | Controle aprovado na validação histórica |
| S11 | 1,71718 | Exceção experimental autorizada |
| **S12** | **1,71456** | **Melhor resultado público registrado** |
| S13 | 1,71461 | Experimento posterior; 0,00005 acima da S12 |

Da climatologia inicial à S12, a queda registrada foi de 0,14012 RMSE (cerca de 7,56%). A S07/S08 permanece no histórico, mas seus componentes externos não integram a linhagem S09–S13. O [histórico de observações](../reports/competition/leaderboard_observations.json) e o [manifesto das submissões](../submissions/manifest.json) guardam os valores e metadados originais.

## Percurso da pesquisa

1. **Base e primeiras melhorias (rodadas 1–6).** A climatologia, modelos locais e contexto atmosférico estabeleceram o problema. Memória, sazonalidade, padrões regionais e escala espacial reduziram o erro público progressivamente até a S06.
2. **Dados externos e retorno aos dados oficiais (7–9).** S07 e S08 exploraram uma linha externa. A S09 recomeçou a linhagem oficial e alcançou 1,72957, sem depender daqueles componentes.
3. **Refinamento do modelo oficial (10–18).** A representação tropical fina gerou a S10, controle aprovado. Correções posteriores não passaram integralmente pelo protocolo histórico; S11 e S12 foram geradas mediante exceções explícitas. A S12 combinou a S11 com 25% de um corretor residual e se tornou a melhor pública.
4. **Busca além da S12 (19–24).** Foram avaliados histórico mais longo, árvores diretas, especialistas regionais, saída espacial ampliada e transporte de umidade em 850 hPa. Nenhum candidato passou o critério de promoção. A S13, teste exploratório com exceções registradas, piorou ligeiramente no público.
5. **Diagnóstico de erros e seleção adaptativa (25–28).** Análogos sazonais e um seletor entre S12 e análogos revelaram potencial *oracle*, mas os ganhos operacionais foram pequenos e instáveis: 0,0482% na mistura fixa da rodada 25, cerca de 0,075% no melhor gate da 27 e até 0,040% no top-k da 28, todos abaixo do mínimo histórico de 0,3%. Foi produzido um [CSV S14 exploratório](../submissions/S14_experimental_round27_gate.md) após a rodada 27; não há score público registrado para ele.
6. **Última rodada (29).** ExtraTrees, LightGBM, regressão de posto reduzido e CCA foram testados sobre mapas OOF auditados. Nenhum trouxe benefício estável frente à S12. CNN/U-Net ficou sem avaliação preditiva por limitação do ambiente (MX350 com 2 GB e ausência de PyTorch), portanto não há conclusão de desempenho dessa família. [Relatório e decisão](../reports/competition/round29/REPORT.md).

O [índice das rodadas](../experiments/README.md) aponta para protocolos, métricas e decisões de cada etapa. Os relatórios antigos registram o estado do projeto na data em que foram escritos; este documento consolida o encerramento.

## Como os resultados foram julgados

A validação de desenvolvimento foi temporal e fora da amostra (*OOF*), com blocos históricos de 2009–2020. O protocolo exigia ganho global mínimo de **0,3%** sobre a referência, estabilidade por blocos e anos e confirmação em 2021–2022. Essa confirmação foi reutilizada em alguns experimentos e não deve ser tratada como teste independente. Os anos de 2023–2024 foram destinados à inferência; seus rótulos não foram usados nos experimentos. O score público de 2023 serviu como observação após envio, não como prova de generalização ao privado.

As exceções da S11, S12 e S13 estão documentadas em seus relatórios. A melhor posição pública da S12 não muda retroativamente o julgamento dos gates internos. O [protocolo](../experiments/PROTOCOL.md) e a [metodologia](METODOLOGIA.md) preservam critérios e detalhes técnicos.

## Artefatos e reprodução

- [Guia de reprodução](REPRODUCAO.md): ambiente, dados oficiais, treino, previsão e verificação da S12 por `--versao melhor`.
- [Evidência da S12](../reports/reproducao/S12.md) e [pacote técnico](../delivery/s12/README.md): CSV reproduzido byte a byte e valores NetCDF equivalentes. SHA-256 do CSV original: `bba1f8b279447868170b6b2f9b18ee2cc723b891c25627c91438c7725d3aead8`.
- [Configuração dos modelos](../configs/modelos.json): versões, caminhos e hashes. [Índice de submissões](../submissions/README.md): metadados dos CSVs. Os CSVs e dados brutos locais são ignorados pelo Git.
- [Índice de relatórios](../reports/README.md): métricas, auditorias e decisões; [código-fonte](../src/README.md): implementação histórica e interface de reprodução.

Um clone novo exige os dados oficiais para retreinar e prever; o repositório preserva código, evidências derivadas e metadados, sem redistribuir os dados brutos. A [página de conformidade](CONFORMIDADE.md) registra pendências formais de licença e identificação da equipe para uma eventual entrega definitiva.

## Fechamento

A participação termina com a S12 como melhor resultado público conhecido. As rodadas finais ajudaram a distinguir sinais diagnósticos de ganhos confiáveis, mesmo sem melhorar a submissão. Foi um desafio empolgante e divertido, e os experimentos, decisões negativas e limites ficaram registrados para que o trabalho possa ser compreendido e reproduzido.
