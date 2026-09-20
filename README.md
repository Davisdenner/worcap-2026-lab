# Previsão mensal de precipitação: WORCAP 2026

Modelo para prever a precipitação média do mês seguinte na América do Sul,
em mm/dia. Código de treinamento, inferência, validação e rastreabilidade.

Código sob licença MIT. Os dados oficiais não são redistribuídos e mantêm os
termos da competição e a atribuição Copernicus.

## Situação

| Versão | RMSE público informado | Situação |
| --- | ---: | --- |
| S10 | 1,71895 | Controle aprovado nos critérios históricos; preservado |
| S11 | 1,71718 | Referência anterior; exceção autorizada após reprovação histórica |
| S12 | **1,71456** | Melhor pública conhecida; reprodução verificada em clone vazio |
| S13 | 1,71461 | Piora de 0,00005; teste exploratório com duas exceções autorizadas |

Os scores públicos abaixo são os que obtive nos envios, registrados no
[histórico público](reports/competition/leaderboard_observations.json). Não os
verifiquei de forma independente no leaderboard. **O leaderboard público mede apenas 2023; o privado medirá
2024**, que são regimes ENSO opostos. O score privado e a classificação final não são
conhecidos. S10, S11, S12 e S13 usam somente dados oficiais; S07/S08, que
usaram informação externa, não participam desta linha de modelos.

A busca por uma sucessora da S12 seguiu por duas etapas. As rodadas 20 a 29
esgotaram as hipóteses de aprendizado direto, especialistas regionais,
histórico mais longo, transporte de umidade, análogos, previsibilidade do erro
e novas famílias de modelos. Depois de um esclarecimento do organizador sobre o
uso de dados externos, as rodadas 30 a 36 retomaram a investigação com redes
convolucionais, escala e capacidade do corretor, e persistência de
precipitação. Nenhuma produziu ganho promovível. A
[síntese das rodadas](docs/SINTESE_RODADAS_25_34.md) reúne as seis
restrições estruturais que explicam o platô; o [índice das
rodadas](experiments/README.md) permite consultar cada uma em ordem, e a
[documentação de encerramento](docs/ENCERRAMENTO.md) cobre a trajetória até a
rodada 29.

## Reprodução verificada

A S12 foi reproduzida **byte a byte a partir de um clone vazio**, em 6,1
minutos de execução, com todos os arquivos necessários presentes no clone e
nenhum artefato copiado de fora. O teste está automatizado em
[scripts/verificar_clone_limpo.ps1](scripts/verificar_clone_limpo.ps1) e o
resultado em
[reproducao_clone_limpo.json](reports/competition/reproducao_clone_limpo.json).
A [documentação de entrega](docs/ENTREGA_S12.md) descreve o modelo, os
atributos, o treino, o ambiente e os limites do que é afirmado.

## Primeiro acesso

1. Siga o [guia de reprodução](docs/REPRODUCAO.md): dados, instalação,
   treinamento, inferência, verificação e solução de problemas.
2. Leia a [metodologia](docs/METODOLOGIA.md) para entender os atributos,
   componentes e combinações. Este é o documento central do método.
3. Para interpretar as decisões da pesquisa, leia o [protocolo histórico](experiments/PROTOCOL.md).
   Ele exigia ganho mínimo de **0,3%**, estabilidade e confirmação; as exceções
   estão registradas nos respectivos relatórios.

Ambiente, com os dados oficiais já extraídos em `data/raw`:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

Use `requirements.txt`, que tem as versões exatas. `requirements-pesquisa.txt`
e `requirements-lock-windows.txt` são registros do ambiente de desenvolvimento
e **não** servem para reproduzir uma submissão; cada um explica isso no
próprio cabeçalho.

Para reproduzir a melhor pública direto, na raiz:

```powershell
.\.venv\Scripts\python.exe -m src.reproducao listar
.\.venv\Scripts\python.exe -m src.reproducao preparar --versao s12
.\.venv\Scripts\python.exe -m src.reproducao treinar --versao s12
.\.venv\Scripts\python.exe -m src.reproducao prever --versao s12
.\.venv\Scripts\python.exe -m src.reproducao verificar --versao s12
```

Troque por `--versao s10` ou `--versao s11` para as outras versões; os
componentes-base são compartilhados, então quem já treinou a S10 pode ir direto
ao corretor com `--versao melhor`. `melhor` resolve atualmente para S12 e não
seleciona candidatas automaticamente. A S13 foi um teste exploratório e sua
[confirmação falhou](reports/competition/round24_experimental/RESULTS.md); um
[CSV S14 exploratório](submissions/S14_experimental_round27_gate.md) foi gerado
sem score público registrado. Reprodução não é promoção nem envio ao Kaggle.

## Organização

| Local | Conteúdo |
| --- | --- |
| [configs](configs/modelos.json) | Versões, hashes e caminhos de reprodução |
| [src](src/README.md) | Interface de reprodução e código científico histórico |
| [docs](docs/ENTREGA_S12.md) | Entrega, encerramento, método e guias de reprodução |
| [experiments](experiments/README.md) | Índice e protocolos por rodada |
| [reports](reports/README.md) | Métricas e verificações |
| [submissions](submissions/README.md) | Metadados dos arquivos enviados |
| [scripts](scripts/verificar_clone_limpo.ps1) | Auditorias, diagnósticos, empacotamento e verificação |
| `tests` | Testes do limite de 0,3%, estabilidade, evidências e catálogo |
| [delivery/s11](delivery/s11/README.md) | Evidências e pacote técnico anterior |
| [delivery/s12](delivery/s12/README.md) | Exemplos OOF oficiais congelados para retreinar o corretor |
| `output/pdf` | Resumo técnico da S11 em inglês, complemento histórico |
| `data/raw` | Dados oficiais locais, fora do Git |
| `data/processed/reproducao` | Cache, modelos e saídas locais, fora do Git |

O fluxo retreina os componentes finais e refaz a inferência. Os pesos-base, as
estatísticas históricas de calibração e os exemplos OOF da S12 são artefatos
congelados incluídos no repositório; **não se refaz toda a pesquisa histórica
do zero**.

Consulte [conformidade e entrega](docs/CONFORMIDADE.md) para os requisitos
atendidos e as pendências. Documentos de entrada anteriores foram preservados
em `docs/history/antes_da_organizacao_2026-09-16`; descrevem momentos passados,
não a política vigente. Os protocolos e resultados científicos originais
permanecem nos seus caminhos, sem renomear dependências congeladas.
