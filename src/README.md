# Código-fonte

Para o primeiro acesso, use [REPRODUCAO.md](../docs/REPRODUCAO.md).
A explicação central dos modelos está em [METODOLOGIA.md](../docs/METODOLOGIA.md).

São 45 módulos, dos quais **quatro** participam de reproduzir uma submissão. O
restante é a pesquisa histórica, preservada com os nomes originais. A tabela
está separada por essa fronteira, porque é ela que importa para quem clonou.

## Reprodução e entrega

| Arquivo | Função |
| --- | --- |
| [reproducao.py](reproducao.py) | Interface em português para listar, preparar, treinar, prever e verificar S10/S11/S12 |
| [s11_delivery.py](s11_delivery.py) | Motor compartilhado de treino final e inferência |
| [s12_delivery.py](s12_delivery.py) | Retreino do corretor a partir de evidências OOF oficiais e reprodução S12 |
| [submission.py](submission.py) | Exportação de CSV preservando coordenadas e ordem do sample |

Esses quatro importam rotinas numéricas dos módulos de pesquisa abaixo, mas não
executam as etapas de pesquisa deles.

## Base do método

| Arquivo | Função |
| --- | --- |
| [competition.py](competition.py) | Auditoria, climatologia e rotinas iniciais |
| [round2.py](round2.py) | Atributos locais/contextuais e árvores |
| [round3.py](round3.py) | Sazonalidade e modelos regionais |
| [round4.py](round4.py) | Memória e grupos da combinação |
| [round5.py](round5.py) | Escala espacial e não linearidade |
| [round6.py](round6.py) | Memória atmosférica local em três defasagens |
| [round7.py](round7.py) | Regressão local e continental; primeira TSM externa |
| [round8.py](round8.py) | Atlântico tropical; última versão com dado externo |
| [round9.py](round9.py) | Linha oficial S09, pesos causais e critério de promoção |
| [round10.py](round10.py) | Representação atmosférica e PLS continental |
| [round11.py](round11.py) | PLS tropical e combinação S10 |
| [atmospheric_trees.py](atmospheric_trees.py) | Árvores sobre campos atmosféricos, usada pelas rodadas iniciais |

## Caminho até a S12

| Arquivo | Função |
| --- | --- |
| [round12.py](round12.py) | Correção residual |
| [round13.py](round13.py) | Componente tropical não linear |
| [round14.py](round14.py) | Atributos físicos de umidade |
| [round15.py](round15.py) | Recalibração conjunta com restrições |
| [round15_experimental.py](round15_experimental.py) | Registro da exceção que gerou S11 |
| [round16.py](round16.py) | Correção espacial/sazonal causal; oito candidatas reprovadas |
| [round17.py](round17.py) | Correção não linear causal; quatro candidatas reprovadas |
| [round17_experimental.py](round17_experimental.py) | Exceção autorizada para S12 conservadora; confirmação e limite de mudança obrigatórios |
| [round18.py](round18.py) | Memória longa no PLS tropical; quatro candidatas reprovadas |

## Investigações depois da S12

Nenhuma produziu ganho promovível. A [síntese](../docs/SINTESE_RODADAS_25_34.md)
explica o padrão em conjunto.

| Arquivo | Função |
| --- | --- |
| [round19.py](round19.py) | Duas variantes de histórico ampliado, com critérios estritos contra S12 |
| [round19_history.py](round19_history.py) | Geração causal dos blocos adicionais de 1997 a 2004 e construção dos 23 atributos |
| [round20.py](round20.py) | Árvores de aprendizado direto local/global; comparações controladas contra S12 |
| [round21.py](round21.py) | Especialistas regionais não lineares, âncora global e transições suaves |
| [round22_23.py](round22_23.py) | Testes controlados de início 1940/1960/1981 e saída ampla + detalhe |
| [round24.py](round24.py) | Fluxos q·u/q·v, convergência e lags de 850 hPa em ablação causal contra S12 |
| [round24_experimental.py](round24_experimental.py) | Exceção que gerou a S13; confirmação falhou |
| [round25.py](round25.py) | Diagnóstico S12, ablação da ordem dos PCs e análogos sazonais |
| [round26.py](round26.py) | Sondas OOF para o resíduo S12 entre 0 e 15°N, geografia do SSE, direção, Q90/Q95 e consenso |
| [round27.py](round27.py) | Oracle S12 × análogos, vantagem D, previsão OOF do vencedor e soft gating |
| [round28.py](round28.py) | Decomposição de G, regressão/ranking OOF, strong wins, top-k e oracles congelados |
| [round29.py](round29.py) | ExtraTrees, LightGBM, RRR e CCA sobre mapas OOF; viabilidade de CNN/U-Net |
| [round30_cnn.py](round30_cnn.py) | Gate convolucional com contexto 2D, treinado em GPU no Kaggle |
| [round32_unet.py](round32_unet.py) | U-Net ponta a ponta sobre os campos atmosféricos |
| [round33_scale.py](round33_scale.py) | Volume de células do corretor, 10,7×, em comparação pareada |
| [round34_capacity.py](round34_capacity.py) | Capacidade do corretor em número de folhas; protocolo congelado |
| [round35_persist.py](round35_persist.py) | Precipitação observada na origem como preditor do corretor |
| [round36_max.py](round36_max.py) | Corretor máximo: 127 atributos, 8.192 células, 255 folhas, início 1981 e 1940 |

## Diagnósticos

| Arquivo | Função |
| --- | --- |
| [diagnose_s08.py](diagnose_s08.py) | Por que a S08 melhorou na validação e piorou no teste |
| [diagnose_s11.py](diagnose_s11.py) | Erro por região, estação e intensidade, sem exportação |
| [diagnose_s12.py](diagnose_s12.py) | Diagnóstico histórico da S12 em grade integral; somente descritivo |

Diagnósticos adicionais, que medem o tamanho de uma oportunidade antes de
construir uma rodada, vivem em `scripts/diag_*.py` e estão indexados no
[README das rodadas](../experiments/README.md).

---

Os nomes históricos são preservados porque existem dependências e hashes
registrados. Não renomear ou modificar módulos congelados apenas para organizar
pastas. Diretórios vazios do esqueleto inicial (`data`, `features`, `models`,
`validation`, `visualization`) não são pipelines alternativos.

Reprodução verifica versões conhecidas, não promove candidatas. Os testes
cobrem o limite histórico de 0,3%, estabilidade, evidências e catálogo. Os
[critérios completos](../experiments/PROTOCOL.md) continuam obrigatórios.
