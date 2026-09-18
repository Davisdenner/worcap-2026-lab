# Previsão mensal de precipitação — WORCAP 2026

Modelo para prever a precipitação média do mês seguinte na América do Sul,
em mm/dia. Código de treinamento, inferência, validação e rastreabilidade.

## Participação encerrada

A participação no hackathon terminou após a rodada 29. A [documentação de encerramento](docs/ENCERRAMENTO.md) reúne a trajetória, as submissões, os critérios de validação, o resultado final conhecido e os limites das conclusões. O [índice das 29 rodadas](experiments/README.md) permite consultar os experimentos em ordem.

| Versão | RMSE público informado | Situação |
| --- | ---: | --- |
| S10 | 1,71895 | Controle aprovado nos critérios históricos; preservado |
| S11 | 1,71718 | Referência anterior; exceção autorizada após reprovação histórica |
| S12 | **1,71456** | Melhor pública conhecida; reprodução verificada |
| S13 | 1,71461 | Piora de 0,00005; teste exploratório com duas exceções autorizadas |

Os scores são relatos do participante, registrados no
[histórico público](reports/competition/leaderboard_observations.json).
O score da S13 foi informado pelo usuário após envio manual; não foi verificado
independentemente. O score privado e a classificação final não são conhecidos.
S10, S11, S12 e S13 usam
somente dados oficiais; S07/S08, que usaram informação externa, não participam
desta linha de modelos.

## Primeiro acesso

1. Siga o [guia de reprodução](docs/REPRODUCAO.md): dados, instalação,
   treinamento, inferência, verificação e solução de problemas.
2. Leia a [metodologia](docs/METODOLOGIA.md) para entender os atributos,
   componentes e combinações. Este é o documento central do método.
3. Para interpretar as decisões da pesquisa, leia o [protocolo histórico](experiments/PROTOCOL.md).
   Ele exigia ganho mínimo de **0,3%**, estabilidade e confirmação; as exceções
   estão registradas nos respectivos relatórios.

Após preparar o ambiente e os dados oficiais em `data/raw`, execute na raiz:

```powershell
.\.venv\Scripts\python.exe -m src.reproducao listar
.\.venv\Scripts\python.exe -m src.reproducao preparar --versao s10
.\.venv\Scripts\python.exe -m src.reproducao treinar --versao s10
.\.venv\Scripts\python.exe -m src.reproducao prever --versao s10
.\.venv\Scripts\python.exe -m src.reproducao verificar --versao s10
```

Os componentes são compartilhados. Para reproduzir a melhor pública registrada,
depois desse treino, ajuste também o corretor da S12:

```powershell
.\.venv\Scripts\python.exe -m src.reproducao treinar --versao melhor
.\.venv\Scripts\python.exe -m src.reproducao prever --versao melhor
.\.venv\Scripts\python.exe -m src.reproducao verificar --versao melhor
```

`melhor` resolve atualmente para S12, a melhor pública e referência reproduzível;
não seleciona candidatas automaticamente. A S13 foi um teste
exploratório e sua [confirmação falhou](reports/competition/round24_experimental/RESULTS.md).
Reprodução não é promoção nem envio ao Kaggle.
As hipóteses de aprendizado direto, especialistas regionais, histórico-base
mais longo, decomposição espacial, transporte de umidade, dinâmica dos PCs e
análogos, previsibilidade do erro, seleção de especialistas, magnitude da vantagem e novas famílias de modelos foram avaliadas nas [rodadas 20–29](experiments/README.md), sem superar a S12. Um [CSV S14 exploratório](submissions/S14_experimental_round27_gate.md) foi gerado sem score público registrado.

## Organização

| Local | Conteúdo |
| --- | --- |
| [configs](configs/modelos.json) | Versões, hashes e caminhos de reprodução |
| [src](src/README.md) | Interface de reprodução e código científico histórico |
| [docs](docs/ENCERRAMENTO.md) | Encerramento, método e guias de reprodução |
| [experiments](experiments/README.md) | Índice e protocolos por rodada |
| [reports](reports/README.md) | Métricas e verificações |
| [submissions](submissions/README.md) | Metadados dos arquivos enviados |
| [delivery/s11](delivery/s11/README.md) | Evidências e pacote técnico anterior |
| [delivery/s12](delivery/s12/README.md) | Exemplos OOF oficiais congelados para retreinar o corretor |
| `data/raw` | Dados oficiais locais, fora do Git |
| `data/processed/reproducao` | Cache, modelos e saídas locais, fora do Git |

O fluxo retreina os componentes finais e refaz a inferência. Os pesos-base e
as estatísticas históricas de calibração e exemplos OOF da S12 são artefatos congelados incluídos no
repositório; **não se refaz toda a pesquisa histórica do zero**.

Consulte [conformidade e entrega](docs/CONFORMIDADE.md) para os requisitos
atendidos e as pendências: licença do código e identificação da equipe ainda
precisam de confirmação antes da entrega definitiva. Os dados brutos não são
redistribuídos; as evidências derivadas mantêm os termos dos dados oficiais.

Documentos de entrada anteriores foram preservados em
`docs/history/antes_da_organizacao_2026-09-16`; descrevem momentos passados,
não a política vigente. Os protocolos e resultados científicos originais
permanecem nos seus caminhos, sem renomear dependências congeladas.
