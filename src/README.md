# Código-fonte

Para o primeiro acesso, use [REPRODUCAO.md](../docs/REPRODUCAO.md).
A explicação central dos modelos está em [METODOLOGIA.md](../docs/METODOLOGIA.md).

| Arquivo | Função |
| --- | --- |
| [reproducao.py](reproducao.py) | Interface em português para listar, preparar, treinar, prever e verificar S10/S11/S12 |
| [s12_delivery.py](s12_delivery.py) | Retreino do corretor a partir de evidências OOF oficiais e reprodução S12 |
| [round19.py](round19.py) | Duas variantes de histórico ampliado, com critérios estritos contra S12 |
| [round19_history.py](round19_history.py) | Geração causal dos blocos adicionais 1997–2004 e construção dos 23 atributos |
| [round20.py](round20.py) | Árvores de aprendizado direto local/global; comparações controladas contra S12 |
| [round21.py](round21.py) | Especialistas regionais não lineares, âncora global e transições suaves; sem promoção |
| [round22_23.py](round22_23.py) | Testes controlados de início 1940/1960/1981 e saída ampla + detalhe; sem promoção |
| [round24.py](round24.py) | Fluxos q·u/q·v, convergência e lags de 850 hPa em ablação causal contra S12 |
| [round25.py](round25.py) | Diagnóstico S12, ablação da ordem dos PCs e análogos sazonais; sem promoção |
| [round26.py](round26.py) | Sondas OOF para o resíduo S12 em 0–15°N, geografia do SSE, direção, Q90/Q95 e consenso; sem nova candidata |
| [round27.py](round27.py) | Oracle S12 × análogos, vantagem D, previsão OOF do vencedor e soft gating diagnóstico; sem S14 |
| [round28.py](round28.py) | Decomposição de G, regressão/ranking OOF, strong wins, top-k e oracles de componentes congelados; sem candidata |
| [round29.py](round29.py) | ExtraTrees, LightGBM, RRR e CCA sobre mapas OOF; CNN/U-Net verificada apenas quanto à viabilidade do ambiente |
| [diagnose_s11.py](diagnose_s11.py) | Diagnóstico de erro por região, estação e intensidade, sem exportação |
| [diagnose_s12.py](diagnose_s12.py) | Diagnóstico histórico da S12 em grade integral; somente descritivo |
| [round16.py](round16.py) | Correção espacial/sazonal causal; oito candidatas reprovadas |
| [round17.py](round17.py) | Correção não linear causal; quatro candidatas reprovadas |
| [round17_experimental.py](round17_experimental.py) | Exceção autorizada para S12 conservadora; confirmação e limite de mudança obrigatórios |
| [round18.py](round18.py) | Memória longa no PLS tropical; quatro candidatas reprovadas |
| [s11_delivery.py](s11_delivery.py) | Motor compartilhado de treino final e inferência; S11 continua sendo o padrão da interface antiga |
| [submission.py](submission.py) | Exportação de CSV preservando coordenadas e ordem do sample |
| [competition.py](competition.py) | Auditoria, climatologia e rotinas iniciais |
| [round2.py](round2.py) | Atributos locais/contextuais e árvores |
| [round3.py](round3.py) | Sazonalidade e modelos regionais |
| [round4.py](round4.py) | Memória e grupos da combinação |
| [round9.py](round9.py) | Linha oficial S09, pesos causais e critério de promoção |
| [round10.py](round10.py) | Representação atmosférica e PLS continental |
| [round11.py](round11.py) | PLS tropical e combinação S10 |
| [round15.py](round15.py) | Recalibração conjunta com restrições |
| [round15_experimental.py](round15_experimental.py) | Registro da exceção que gerou S11 |

Os nomes históricos são preservados porque existem dependências e hashes
registrados. Não renomear ou modificar módulos congelados apenas para organizar
pastas. O motor novo importa suas rotinas numéricas, não executa suas etapas
de pesquisa automaticamente. Diretórios vazios do esqueleto inicial não são
pipelines alternativos.

Reprodução verifica versões conhecidas, não promove candidatas. Os testes
cobrem o limite histórico de 0,3%, estabilidade, evidências e catálogo. Os
[critérios completos](../experiments/PROTOCOL.md) continuam obrigatórios.
