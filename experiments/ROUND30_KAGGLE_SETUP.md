# Passo a passo — treinar o gate CNN (rodada 30) no Kaggle

Este guia cobre só a parte de infraestrutura: como sair do computador local
(sem RAM/GPU suficiente) e treinar no Kaggle, mantendo os artefatos e o
código de volta neste repositório. Não substitui um protocolo científico
(hipótese, blocos, critérios) nos moldes de `experiments/ROUND*.md` — esse
protocolo formal deve ser escrito antes de rodar qualquer treino real,
como em todas as rodadas anteriores.

## 0. Pré-requisitos (uma vez só)

1. Conta no Kaggle vinculada ao mesmo login usado na competição.
2. Gerar um token de API: kaggle.com → ícone de perfil → **Settings** →
   seção **API** → **Create New Token**. Isso baixa `kaggle.json`.
3. Colocar o arquivo em `C:\Users\Davis Denner\.kaggle\kaggle.json`
   (crie a pasta `.kaggle` se não existir). Alternativa: definir as
   variáveis de ambiente `KAGGLE_USERNAME` e `KAGGLE_KEY`.
4. Confirmar que `kagglehub` está instalado no venv do projeto (já está em
   `requirements.txt`): `.\.venv\Scripts\python.exe -c "import kagglehub"`.

## 1. Empacotar os artefatos congelados localmente

Na raiz do repositório:

```powershell
.\.venv\Scripts\python.exe scripts\package_round30_kaggle.py
```

Isso cria `kaggle_bundle/round30/` com o código de `src/` necessário para
reconstruir os atributos (round9, round20, round25–28, competition,
atmospheric_trees), os OOF congelados de `data/processed/round27` e
`data/processed/round28` (probabilidade/vencedor/vantagem no norte), os
exemplos OOF do corretor S12 (`delivery/s12/evidence`) e `configs/modelos.json`.
Um `MANIFEST.json` com SHA-256 de cada arquivo é gravado junto, no mesmo
espírito dos manifestos que já existem em `delivery/*/evidence`.

**Não inclui dados brutos oficiais.** Isso é proposital — ver a seção 3.

## 2. Subir como Kaggle Dataset privado

```powershell
.\.venv\Scripts\python.exe scripts\upload_round30_kaggle.py SEU_USUARIO_KAGGLE
```

Isso cria (ou versiona) `SEU_USUARIO_KAGGLE/worcap-round30-artefatos` como
dataset **privado**. Confirme manualmente em kaggle.com que a visibilidade
ficou privada antes de seguir — os exemplos OOF são dados derivados dos
oficiais e devem seguir os mesmos termos (ver `docs/CONFORMIDADE.md`).

## 3. Criar o notebook no Kaggle

1. kaggle.com → **Code** → **New Notebook**.
2. **Add Input** (painel direito):
   - o dataset oficial da competição (anexar diretamente; não fazer upload
     manual dos NetCDF — evita redistribuir dado bruto por fora do Kaggle);
   - `SEU_USUARIO_KAGGLE/worcap-round30-artefatos`, criado no passo 2.
3. **Settings** (menu à direita): Accelerator → **GPU T4 x2** (ou P100);
   Internet → **On** (o PyTorch já vem instalado na imagem padrão do
   Kaggle, então internet só é necessária se precisar de algum pacote extra).
4. Anote a cota: cerca de 30 h de GPU por semana, sessões de até 9 h
   contínuas. Salve checkpoints em `/kaggle/working/` periodicamente para
   não perder progresso se a sessão cair.

## 4. Dentro do notebook

Estrutura mínima de células:

```python
import sys
sys.path.append("/kaggle/input/worcap-round30-artefatos/code")

import numpy as np
import torch

# Exemplo: carregar o OOF do bloco 2011 do round27 (norte)
d = np.load("/kaggle/input/worcap-round30-artefatos/artifacts/round27/2011_winner_oof.npz")
probability = d["probability"]  # (4 modelos, 24 meses, 15921 pontos do norte)
winner = d["winner"]            # (24 meses, 15921) — 1 = análogo venceu
advantage = d["advantage"]      # (24, 15921) — G = perda S12 - perda Analog
```

A partir daqui entra a parte científica: reconstruir os patches espaciais
2D em torno de cada ponto (usando a máscara do norte e a grade oficial de
`src/competition.py`), montar o classificador convolucional e validar nos
mesmos 5 blocos causais 2011–2020, comparando contra o gate de 0,075% já
obtido na rodada 27 e contra `src.round9.passes_gate`. Essa parte eu ainda
não fechei em código — antes de rodar de verdade, vale eu ler
`src/round27.py` por completo para confirmar a ordem exata dos 15.921
pontos do norte (para não montar os patches com o índice espacial errado)
e então escrever o protocolo formal da rodada 30.

## 5. Trazer o resultado de volta

```python
# ainda no Kaggle, ao final do treino
import json
with open("/kaggle/working/round30_metrics.json", "w") as f:
    json.dump(metricas, f, indent=2)
```

Baixe pela aba **Output** do notebook, ou suba como nova versão do dataset
e puxe localmente:

```powershell
.\.venv\Scripts\python.exe -c "import kagglehub; print(kagglehub.dataset_download('SEU_USUARIO_KAGGLE/worcap-round30-artefatos'))"
```

Encaixe os resultados em `reports/competition/round30/`, com os mesmos
hashes SHA-256 e o mesmo formato de `REPORT.md` das rodadas 26–29, antes de
decidir promoção conforme `experiments/PROTOCOL.md`.
