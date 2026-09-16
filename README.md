# Previsão mensal de precipitação — WORCAP 2026

Modelo para prever a precipitação média do mês seguinte na América do Sul,
em mm/dia. Código de treinamento, inferência, validação e rastreabilidade.

## Estado atual

| Versão | RMSE público informado | Situação |
| --- | ---: | --- |
| S10 | 1,71895 | Controle aprovado nos critérios históricos; preservado |
| S11 | **1,71718** | Melhor pública; exceção autorizada após reprovação histórica |

Os scores são relatos do participante, registrados no
[histórico público](reports/competition/leaderboard_observations.json).
O score privado e a classificação final não são conhecidos. S10 e S11 usam
somente dados oficiais; S07/S08, que usaram informação externa, não participam
desta linha de modelos.

## Primeiro acesso

1. Siga o [guia de reprodução](docs/REPRODUCAO.md): dados, instalação,
   treinamento, inferência, verificação e solução de problemas.
2. Leia a [metodologia](docs/METODOLOGIA.md) para entender os atributos,
   componentes e combinações. Este é o documento central do método.
3. Antes de experimentar, leia o [protocolo vigente](experiments/PROTOCOL.md).
   O ganho mínimo histórico de **0,3% continua ativo**, junto com os demais
   critérios de estabilidade e confirmação.

Após preparar o ambiente e os dados oficiais em `data/raw`, execute na raiz:

```powershell
.\.venv\Scripts\python.exe -m src.reproducao listar
.\.venv\Scripts\python.exe -m src.reproducao preparar --versao s10
.\.venv\Scripts\python.exe -m src.reproducao treinar --versao s10
.\.venv\Scripts\python.exe -m src.reproducao prever --versao s10
.\.venv\Scripts\python.exe -m src.reproducao verificar --versao s10
```

Os componentes são compartilhados. Para reproduzir a melhor pública registrada,
depois desse treino:

```powershell
.\.venv\Scripts\python.exe -m src.reproducao prever --versao melhor
.\.venv\Scripts\python.exe -m src.reproducao verificar --versao melhor
```

`melhor` resolve atualmente para S11; não seleciona candidatas automaticamente.
Reprodução não é promoção nem envio ao Kaggle. Novas candidatas continuam
dependendo de pedido explícito; exceções precisam ser informadas e autorizadas.

## Organização

| Local | Conteúdo |
| --- | --- |
| [configs](configs/modelos.json) | Versões, hashes e caminhos de reprodução |
| [src](src/README.md) | Interface de reprodução e código científico histórico |
| [docs](docs/REPRODUCAO.md) | Guias atuais em português |
| [experiments](experiments/PROTOCOL.md) | Política vigente e protocolos por rodada |
| [reports](reports/README.md) | Métricas e verificações |
| [submissions](submissions/README.md) | Metadados dos arquivos enviados |
| [delivery/s11](delivery/s11/README.md) | Evidências e pacote técnico anterior |
| `data/raw` | Dados oficiais locais, fora do Git |
| `data/processed/reproducao` | Cache, modelos e saídas locais, fora do Git |

O fluxo retreina os componentes finais e refaz a inferência. Os pesos-base e
as estatísticas históricas de calibração são artefatos congelados incluídos no
repositório; **não se refaz toda a pesquisa histórica do zero**.

Consulte [conformidade e entrega](docs/CONFORMIDADE.md) para os requisitos
atendidos e as pendências: licença do código e identificação da equipe ainda
precisam de confirmação antes da entrega definitiva. Dados não são redistribuídos.

Documentos de entrada anteriores foram preservados em
`docs/history/antes_da_organizacao_2026-09-16`; descrevem momentos passados,
não a política vigente. Os protocolos e resultados científicos originais
permanecem nos seus caminhos, sem renomear dependências congeladas.
