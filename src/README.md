# Código-fonte

Para o primeiro acesso, use [REPRODUCAO.md](../docs/REPRODUCAO.md).
A explicação central dos modelos está em [METODOLOGIA.md](../docs/METODOLOGIA.md).

| Arquivo | Função |
| --- | --- |
| [reproducao.py](reproducao.py) | Interface em português para listar, preparar, treinar, prever e verificar S10/S11 |
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
