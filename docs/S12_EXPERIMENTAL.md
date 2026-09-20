# S12 experimental: correção não linear da S11

A S12 aplica 25% de uma correção de resíduos por árvores à S11:
`máximo(S11 + 0,25 × corretor, 0)`. Usa somente dados oficiais. O método
base continua descrito em [METODOLOGIA.md](METODOLOGIA.md); os atributos,
parâmetros e cortes do corretor estão no [protocolo 17](../experiments/ROUND17.md).

## Decisão e limites

No desenvolvimento 2009 a 2020, a variante fixa `meta15_a0.25` melhorou o RMSE
de 1,774621760 para 1,770775491 (0,216737%). Passou nos critérios de estabilidade,
mas **não atingiu o mínimo de 0,3%**. A seleção automática permanece reprovada.
Autorizei [uma exceção restrita](../experiments/ROUND17_EXPERIMENTAL.md)
para gerar esta versão, condicionada à confirmação e ao limite de mudança.

Na confirmação reutilizada de 2021 a 2022, passou de 1,829353225 para 1,821385840
(0,435530%), melhorando ambos os anos. Essa janela já foi consultada anteriormente:
não é uma avaliação independente, nem permite prometer um score público ou privado.
O limiar geral de 0,3% não foi desativado.

## Treinamento e inferência

O corretor final usa 442.368 exemplos históricos fora do treino dos modelos-base,
de blocos completos de 2005 a 2022. São 2.048 pontos amostrados por mês, 23 atributos,
200 iterações e até 15 folhas por árvore. Nenhum alvo oculto de 2023/2024 é usado.
As variáveis atmosféricas de entrada correspondem ao mês anterior ao alvo.

O ambiente é o mesmo da [reprodução S10/S11](REPRODUCAO.md): Python 3.11.1,
[dependências fixadas](../delivery/s11/requirements.txt), CPU e uma thread numérica.
O código-fonte de treino é [round17.py](../src/round17.py), funções `samples`
e `fitted`; a inferência está em `matrix`/`correction`. A exportação condicionada
e suas verificações estão em [round17_experimental.py](../src/round17_experimental.py).

Execução utilizada, na raiz do ambiente de pesquisa existente:

```powershell
.\.venv\Scripts\python.exe -m src.round17_experimental confirm --user-authorized
.\.venv\Scripts\python.exe -m src.round17_experimental export --user-authorized
.\.venv\Scripts\python.exe scripts/verify_candidate.py submissions/submission_12.csv data/processed/round17_experimental/submission_12_predictions.nc
```

**Pré-requisitos adicionais:** arquivos oficiais em `data/raw`, caches oficiais
em `data/processed/official`, componentes e referências históricos das rodadas
9 a 11 e 15, protocolos/seleções preservados e originais S10/S11 para conferência
de integridade. Esses artefatos locais não estão todos no Git. Os comandos acima
não são os comandos recomendados para um clone novo. A interface
`src.reproducao` agora oferece `--versao s12`, usando os NC oficiais e as
[evidências OOF empacotadas](../delivery/s12/README.md), sem esses caches de
pesquisa. Consulte o [guia de primeiro acesso](REPRODUCAO.md). Ela retreina os
modelos finais, mas reutiliza os exemplos históricos OOF: não refaz toda a pesquisa.

O modelo final serializado fica em `data/processed/round17/2023_meta15.joblib`;
seus metadados e hash são copiados para o JSON da submissão. A geração recarrega
o modelo e compara novamente todas as previsões do corretor. O exportador recusa
sobrescrever uma saída existente: não apague os originais para repetir uma execução.

## Artefatos e envio

- CSV local: `submissions/submission_12.csv`.
- [Metadados imutáveis de geração](../submissions/submission_12.json).
- Previsões com coordenadas: `data/processed/round17_experimental/submission_12_predictions.nc`.
- [Resultados e evidências](../reports/competition/round17_experimental/RESULTS.md).

Envio manual, somente do CSV. O nome S12 é uma convenção interna. Nenhum upload
é feito pelo pipeline. Depois da geração, o envio devolveu **1,71456 e segundo
lugar**, o que tornou a S12 a melhor pública conhecida. O resultado foi registrado no
[histórico de scores](../reports/competition/leaderboard_observations.json), sem
alterar os metadados originais de geração. O catálogo executável e seu atalho
`melhor` passam a incluir S12, sem alterar sua condição de exceção histórica.
