# Comandos do pacote autônomo S11

Este documento descreve a interface anterior, preservada para o ZIP de entrega.
No repositório atual, prefira o [guia S10/S11](../../docs/REPRODUCAO.md).
O ZIP é um snapshot separado e não incorpora automaticamente mudanças posteriores.

## Inferência com modelos já treinados

Na raiz do pacote extraído, ajuste `SETTINGS.json` e execute:

```powershell
.\.venv\Scripts\python.exe -m src.s11_delivery predict --settings SETTINGS.json
```

Requer modelos do pacote e `teste_features.nc`/`sample_submission.csv` oficiais
no diretório `raw`. Gera `s11_reproduction.csv`, NetCDF e componentes na pasta
`output`, sem sobrescrever CSV existente. Não é uma nova candidata.

## Retreinar os componentes finais

Na configuração, escolha pastas novas para cache, modelos e saídas. Preserve
`evidence` e a origem oficial dos dados.

```powershell
.\.venv\Scripts\python.exe -m src.s11_delivery prepare --settings SETTINGS.json
.\.venv\Scripts\python.exe -m src.s11_delivery train --settings SETTINGS.json
.\.venv\Scripts\python.exe -m src.s11_delivery predict --settings SETTINGS.json
```

Preparação lê os arquivos oficiais; treinamento refaz os componentes finais.
A calibração usa estatísticas históricas fora do treino já arquivadas. Não
reexecuta seleção de modelos ou todos os blocos históricos desde os dados brutos.
Execute cada etapa somente após a anterior terminar sem erro.

No repositório, os comandos equivalentes usam
`--settings delivery/s11/SETTINGS.json` a partir da raiz. Esses diretórios podem
já conter resultados; prefira o fluxo atual e pastas novas para uma repetição.

## Conferir o pacote fechado

Na raiz do ZIP extraído, que contém `PACKAGE_MANIFEST.json`:

```powershell
.\.venv\Scripts\python.exe check_delivery.py
.\.venv\Scripts\python.exe check_delivery.py --predictions work/output/s11_reproduction.csv
```

O caminho final deve coincidir com `output` na configuração. O manifesto do
pacote é gerado ao construir o ZIP; esse verificador não se aplica diretamente
à pasta `delivery/s11` sem o manifesto. No repositório, use `src.reproducao verificar`.
Não altere previsões ou hashes esperados para encobrir diferenças numéricas.
