# Guia de reprodução para o primeiro acesso

Reproduza S10, S11 ou S12 sem consumir envios, pesquisar novos modelos ou alterar
as submissões originais. O método está em [METODOLOGIA.md](METODOLOGIA.md);
as regras de seleção estão no [protocolo](../experiments/PROTOCOL.md).
A S13 marcou 1,71461 contra 1,71456 da S12 no público e é um teste exploratório
que falhou na confirmação e ainda não está integrada a esta interface de
reprodução. O atalho `melhor` continua fixado na S12 reproduzível.

## 1. Código e dados

Clone e execute os comandos na raiz do repositório:

```powershell
git clone https://github.com/Davisdenner/worcap-2026-lab.git
cd worcap-2026-lab
git rev-parse HEAD
git status --short
```

Use o commit que contém este guia e `configs/modelos.json`. Alterações ainda
não publicadas pelo mantenedor não aparecem automaticamente no clone. Registre
o commit e eventuais alterações locais ao documentar uma reprodução.

Aceite as regras e obtenha o pacote atualizado na
[página oficial dos dados](https://www.kaggle.com/competitions/previsao-climatica-de-precipitacao-sobre-a-america-do-sul/data).
Extraia diretamente em `data/raw`, sem pasta intermediária:

```text
data/raw/
  sample_submission.csv
  teste_features.nc
  treino_tp.nc
  treino_tp_alvo.nc
  treino_cloud_cover.nc
  treino_geopotential_850.nc
  treino_rel_hum_850.nc
  treino_shum_850.nc
  treino_surface_pressure.nc
  treino_t2.nc
  treino_temperature_850.nc
  treino_u_850.nc
  treino_v_850.nc
```

O treino final deriva o alvo por deslocamento de `treino_tp.nc`.
`treino_tp_alvo.nc` é usado na auditoria original, mas não nesse retreino.
O sample atualizado é obrigatório. Não é necessário token de API no pipeline
local. Nunca coloque credenciais ou dados brutos no Git.

## 2. Ambiente

Referência verificada: Windows x64, Python **3.11.1**, Intel i5-1135G7,
4 núcleos físicos/8 lógicos e 16 GB RAM. CPU com uma thread numérica, sem GPU.
Reserve aproximadamente 8 GB livres para dados, cache, modelos e saídas, com
margem extra para conservar várias execuções. Isso não é uma medição de
requisito mínimo universal.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r delivery/s11/requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

Use as [dependências fixadas](../delivery/s11/requirements.txt), não o arquivo
exploratório sem versões na raiz. `py -3.11` seleciona o Python 3.11 instalado;
para comparação estrita de bytes, use a versão 3.11.1 de referência.
Outras plataformas e implementações BLAS podem produzir diferenças numéricas.

### Instalação offline

O índice disponível na máquina de referência não resolveu todas as versões.
Foi verificada uma instalação em ambiente novo com wheels locais. Eles **não
estão no Git**: obtenha o pacote técnico do mantenedor para usar esta opção.

```powershell
.\.venv\Scripts\python.exe -m pip install --no-index --find-links delivery/s11/wheels -r delivery/s11/requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

São distribuições instaladas reempacotadas localmente, não downloads originais
dos editores. Origem e hashes: [provenance.json](../delivery/s11/wheels/provenance.json).
Licenças acompanham os pacotes. Não substitua versões silenciosamente.

## 3. Caminhos e versão

[configs/reproducao.json](../configs/reproducao.json) centraliza os caminhos.
Todos são relativos ao próprio arquivo de configuração:

| Chave | Diretório padrão e finalidade |
| --- | --- |
| `raw` | `data/raw`, somente leitura |
| `cache` | `data/processed/reproducao/cache`, arrays derivados do treino |
| `models` | `data/processed/reproducao/modelos_serializados`, componentes serializados |
| `output` | `data/processed/reproducao/saidas_verificadas`, subpasta por versão |
| `evidence` | `delivery/s11/evidence`, calibração histórica congelada |
| `s12_evidence` | `delivery/s12/evidence`, exemplos históricos OOF do corretor |

```powershell
.\.venv\Scripts\python.exe -m src.reproducao listar
```

O [catálogo](../configs/modelos.json) distingue S10 (controle aprovado), S11
(referência anterior) e S12 (melhor pública e referência reproduzível, exceção autorizada). `--versao melhor`
resolve atualmente para S12; versões desconhecidas são rejeitadas. Para diretórios diferentes, copie
a configuração, ajuste os caminhos e passe `--settings caminho/configuracao.json`
em **todos** os comandos. Prefira caminhos absolutos nessa cópia.

## 4. Preparar, treinar e prever a S10

```powershell
.\.venv\Scripts\python.exe -m src.reproducao preparar --versao s10
.\.venv\Scripts\python.exe -m src.reproducao treinar --versao s10
.\.venv\Scripts\python.exe -m src.reproducao prever --versao s10
.\.venv\Scripts\python.exe -m src.reproducao verificar --versao s10
```

Execute uma etapa por vez e só prossiga se terminar sem erro:

1. **Preparar:** verificar arquivos, coordenadas, meses e hashes; regenerar
   arrays de treinamento e representações espaciais a partir dos dados oficiais.
2. **Treinar:** retreinar árvores, regressões e PCA/PLS; salvar pré-processamento,
   coeficientes e modelos. Os pesos-base são preservados e os pesos conjuntos
   da S11 são recalculados das estatísticas históricas fora do treino arquivadas.
3. **Prever:** carregar modelos e atmosfera oficial do teste; aplicar a combinação
   escolhida e exportar. Não lê chuva de treino nem alvos ocultos. Já executa a
   verificação do CSV automaticamente.
4. **Verificar:** comparar com o hash original independente; conferir colunas,
   1.885.464 linhas, IDs e ordem oficial, valores finitos e não negativos.

Todos os componentes finais são retreinados; não se repetem a pesquisa de
hiperparâmetros nem todos os blocos históricos de calibração. O treino usa
503 pares com alvos até dezembro de 2022. A inferência atende ao esquema oficial
de 24 meses; não é um serviço meteorológico para datas arbitrárias.

## 5. Reproduzir a melhor pública (S12)

Com os componentes do passo 4 já treinados, o comando de treino S12 verifica
e reutiliza esses componentes, treinando apenas o corretor adicional:

```powershell
.\.venv\Scripts\python.exe -m src.reproducao treinar --versao melhor
.\.venv\Scripts\python.exe -m src.reproducao prever --versao melhor
.\.venv\Scripts\python.exe -m src.reproducao verificar --versao melhor
```

Para começar diretamente pela S12, execute as quatro etapas do passo 4 com
`--versao s12`. Nesse caso os componentes-base também são treinados. Para S11,
use `--versao s11`. Não são necessários CSVs anteriores em `submissions` nem
caches de experimentos antigos.

S12 requer os nove NPZ e o manifesto de `delivery/s12/evidence`, incluídos no
repositório/pacote. O corretor é retreinado sobre 442.368 exemplos OOF congelados;
a reprodução não refaz os nove blocos históricos dos modelos-base. A integridade
é verificada pelo manifesto e pelo hash das previsões de treino do corretor
original, seguido da comparação integral do CSV de teste. Veja o
[escopo das evidências](../delivery/s12/README.md).

## 6. Saídas e resultados esperados

| Versão | CSV reproduzido |
| --- | --- |
| S10 | `data/processed/reproducao/saidas_verificadas/s10/s10_reproduction.csv` |
| S11 | `data/processed/reproducao/saidas_verificadas/s11/s11_reproduction.csv` |
| S12 | `data/processed/reproducao/saidas_verificadas/s12/s12_reproduction.csv` |

As pastas também recebem NetCDF, arrays dos componentes, metadados,
`verificacao.json` e medições de tempo, memória e dependências. São cópias de
reprodução, não novas submissões numeradas.

SHA-256 S10:

```text
57862493c62936b291c03cff3bd4c53fd486ab38a08108f908a8f74b5aada46e
```

SHA-256 S11:

```text
8b871e4fa982045ee1c59abb19ff9e4954444aaf96de22052daa3de22e64b26f
```

SHA-256 S12:

```text
bba1f8b279447868170b6b2f9b18ee2cc723b891c25627c91438c7725d3aead8
```

São hashes dos arquivos enviados, registrados antes da reprodução, e não hashes
calculados apenas para declarar sucesso da nova saída. O score Kaggle não pode
ser recalculado localmente sem os alvos ocultos de 2023/2024.

A execução verificada de S10/S11, incluindo comparação numérica, tempos e
limitações, está em [reports/reproducao](../reports/reproducao/README.md).

## 7. Testes e auditoria

```powershell
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/check_repository.py --allow-missing-artifacts
```

O segundo comando permite a ausência dos CSVs históricos que não estão no Git,
mas continua verificando metadados, links e hashes dos arquivos presentes.
Ausência de artefato não é reprodução bem-sucedida. Não carregue `joblib` de
origem desconhecida: é uma serialização executável. Os modelos produzidos aqui
são verificados por hash antes da inferência.

## 8. Problemas frequentes

- **Modelo ou CSV já existe:** proteção contra sobrescrita. Para repetir, use
  pastas novas na configuração. Não apague os originais enviados.
- **Hash de entrada diferente:** confira pacote oficial, extração e nomes.
  Não mude o hash esperado apenas para contornar a proteção.
- **CSV diferente:** investigue dependências, Python e bibliotecas numéricas.
  Não ignore a falha nem declare equivalência sem medir a diferença.
- **Versão indisponível no índice:** obtenha o pacote offline documentado.
  Um clone não contém automaticamente wheels, modelos ou ZIP de entrega.
- **Recursos:** cada etapa registra medições. A reprodução anterior S11 levou
  cerca de 1–2 minutos por etapa principal, com pico de processo próximo de
  2,3 GiB no treino na máquina de referência; não é garantia de desempenho.

A reprodução inclui os artefatos históricos de calibração congelados. Não
regenera toda a pesquisa do zero. Escopo e pendências formais:
[CONFORMIDADE.md](CONFORMIDADE.md).

## 9. Próximas versões

Antes de experimentar, congele a referência e o [protocolo](../experiments/PROTOCOL.md).
Depois de autorização explícita e geração: preserve código, configuração,
artefatos de calibração, modelos, métricas, metadados e hash do CSV; registre
a versão no catálogo e implemente/teste sua reprodução. Nova arquitetura exige
um motor correspondente: adicionar uma linha JSON não basta.

Atualize manifesto e histórico público com resultados confirmados. Mude
`melhor_publica` somente após score informado e reprodução verificada; mantenha
as versões anteriores. Reexecute testes e este guia em pastas novas. Assim,
`--versao melhor` continua sendo uma escolha registrada e auditável.

### Nota ao mantenedor: publicação desta organização

`.gitattributes` protege PDFs/arrays como binários e fixa finais de linha das
evidências com hashes. Três arquivos históricos têm finais de linha mistos,
embora o índice Git anterior os tenha normalizado. Antes de publicar esta
organização, confira suas alterações e inclua as regras; depois reaplique
somente a normalização desses arquivos, preservando seus bytes locais:

```powershell
git add .gitattributes
git add --renormalize src/round2.py experiments/ROUND2.md delivery/s11/evidence/leaderboard_observations.json
```

Isso é uma orientação para o commit do mantenedor, não uma etapa de treinamento
para quem acabou de clonar. Não execute normalização global em fontes congeladas.
Os demais arquivos já preparados para commit precisam receber novamente `git add`
se foram editados depois de adicionados. A organização não faz commit nem push.
