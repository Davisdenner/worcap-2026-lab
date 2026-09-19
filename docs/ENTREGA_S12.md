# Entrega da S12 — documentação da Seção 2.8

Documento de entrega da versão **S12**, a melhor submissão pública conhecida
deste projeto (**1,71456**). Existe um equivalente para a versão anterior em
[ENTREGA_S11.md](ENTREGA_S11.md); este documento cobre a versão que
efetivamente seria entregue.

A estrutura segue as [diretrizes oficiais de documentação de modelos
vencedores](https://www.kaggle.com/WinningModelDocumentationGuidelines). Ele
não substitui nada: o método completo está em [METODOLOGIA.md](METODOLOGIA.md),
o passo a passo de execução em [REPRODUCAO.md](REPRODUCAO.md), o escopo e as
pendências formais em [CONFORMIDADE.md](CONFORMIDADE.md), e a decisão que
produziu a S12 em [S12_EXPERIMENTAL.md](S12_EXPERIMENTAL.md). O que este
documento acrescenta é a visão de entrega: o que é preciso para que um terceiro,
recebendo apenas o pacote, regenere o CSV enviado.

## A1. Identificação

Participação individual, sem equipe. Os campos formais de identificação ainda
não foram preenchidos: [TEAM_INFO.json](../delivery/s11/TEAM_INFO.json) segue
com os campos em branco e a licença OSI do código não foi atribuída. As duas
coisas são pendências registradas em [CONFORMIDADE.md](CONFORMIDADE.md) e
precisam ser resolvidas antes de qualquer entrega ao organizador; não foram
preenchidas aqui para não inventar dados.

## A2. Resumo do modelo

A previsão final é

```text
S12 = máximo(S11 + 0,25 × corretor, 0)
```

onde a **S11** é um conjunto de modelos-base sobre os campos atmosféricos
oficiais, e o **corretor** é um modelo de árvores treinado sobre os resíduos da
S11 em exemplos fora do treino. A fração 0,25 é fixa, escolhida no
desenvolvimento e não reajustada depois.

Três características definem o sistema:

**A referência é a climatologia, não zero.** Toda a modelagem trabalha em
anomalia contra uma climatologia causal de 60 anos, reconstruída para cada
bloco a partir apenas do que estaria disponível antes daquele bloco. A
climatologia sozinha marca 1,85468 no público; o pipeline inteiro entrega
1,71456, um ganho de 7,6%.

**Só dados oficiais.** A partir da versão S09 o pipeline opera sob
`only_official_data`. As versões S07 e S08 usaram temperatura de superfície do
mar da NOAA; a S07 ganhou 0,55% e a S08, que passou na validação de
desenvolvimento e na confirmação de 2021–2022, **piorou** no leaderboard. Essa
divergência entre validação e teste motivou a restrição, que nunca foi
revertida. A S12 não contém nenhum componente externo.

**A precipitação nunca é preditora.** `round2.Features.matrix` tem 55 colunas e
nenhuma delas é chuva; a memória local de `round6` usa as nove variáveis
atmosféricas, não a precipitação. A chuva aparece apenas como rótulo. Isso
mantém treino e teste alinhados com o contrato do `teste_features.nc`, e é uma
das razões pelas quais a validação deste projeto é **conservadora**: a S12 vai
melhor no teste público (1,715) do que na própria validação OOF (1,756).

## A3. Atributos

Os atributos do corretor S12 são 23 colunas derivadas dos campos atmosféricos
oficiais do mês imediatamente anterior ao alvo, mais descritores de posição e
de época do ano. A lista exata, os cortes e os parâmetros estão no
[protocolo 17](../experiments/ROUND17.md); não são reproduzidos aqui para que
exista uma fonte única.

Os modelos-base da S11 usam as 55 colunas de `round2.Features.matrix`, que
combinam os nove campos atmosféricos em defasagens, reduções por PCA/PLS e
descritores espaciais. O detalhamento está em [METODOLOGIA.md](METODOLOGIA.md).

Nenhuma seleção de atributos foi feita sobre os blocos de avaliação: os cortes
foram congelados antes da medição, conforme o
[protocolo](../experiments/PROTOCOL.md).

## A4. Treinamento

O corretor final usa **442.368 exemplos** históricos fora do treino dos
modelos-base, de blocos completos de 2005 a 2022: 2.048 pontos amostrados por
mês, 200 iterações, até 15 folhas por árvore. Nenhum alvo de 2023 ou 2024 entra
em qualquer etapa.

O treino dos modelos-base usa 503 pares com alvos até dezembro de 2022.

O código de treino é [round17.py](../src/round17.py), funções `samples` e
`fitted`; a inferência está em `matrix` e `correction`. O caminho de entrega,
que é o que um terceiro executa, é [s12_delivery.py](../src/s12_delivery.py),
orquestrado por [reproducao.py](../src/reproducao.py).

**O que a reprodução refaz e o que ela reutiliza.** Este é o ponto em que é
fácil prometer demais, então vale ser explícito. A reprodução retreina todos os
componentes finais — árvores, regressões, PCA/PLS e o corretor — e regenera o
CSV. Ela **não** refaz a pesquisa de hiperparâmetros nem regenera os nove blocos
históricos de previsões fora do treino; esses estão congelados em
`delivery/s12/evidence` como nove NPZ mais um manifesto, verificados por
sha256 antes do uso. Sem eles não há reprodução da S12, apenas dos
componentes-base.

## A5. Ambiente

Referência verificada: Windows x64, **Python 3.11.1**, Intel i5-1135G7, quatro
núcleos físicos e oito lógicos, 16 GB de RAM, CPU com uma thread numérica, sem
GPU. Reserve cerca de 8 GB de disco livre.

As dependências fixadas estão em
[delivery/s11/requirements.txt](../delivery/s11/requirements.txt); o arquivo
sem versões na raiz é exploratório e não serve para reprodução estrita. Há uma
opção de instalação offline com wheels locais, que **não estão no Git** — são
distribuições instaladas reempacotadas, não downloads originais dos editores, e
isso está registrado em [provenance.json](../delivery/s11/wheels/provenance.json).

Outras plataformas e implementações de BLAS podem produzir diferenças
numéricas. A comparação byte a byte só é esperada no ambiente de referência.

## A6. Execução

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r delivery/s11/requirements.txt

.\.venv\Scripts\python.exe -m src.reproducao listar
.\.venv\Scripts\python.exe -m src.reproducao preparar --versao s12
.\.venv\Scripts\python.exe -m src.reproducao treinar  --versao s12
.\.venv\Scripts\python.exe -m src.reproducao prever   --versao s12
.\.venv\Scripts\python.exe -m src.reproducao verificar --versao s12
```

Os dados oficiais vão em `data/raw`, extraídos sem pasta intermediária, com os
doze arquivos listados em [REPRODUCAO.md](REPRODUCAO.md). Não é necessário
token de API. Nenhuma credencial deve integrar o pacote.

Saída: `data/processed/reproducao/saidas_verificadas/s12/s12_reproduction.csv`,
com sha256 esperado

```text
bba1f8b279447868170b6b2f9b18ee2cc723b891c25627c91438c7725d3aead8
```

registrado em [configs/modelos.json](../configs/modelos.json) **antes** da
reprodução — é o hash do arquivo que foi enviado, não um hash calculado depois
para declarar sucesso.

A etapa `verificar` confere, além do hash: as colunas `['id','tp_mm_day']`,
1.885.464 linhas, a ordem dos ids contra o `sample_submission.csv` oficial, e
valores finitos e não negativos. A etapa `treinar` da S12 ainda reconfere as
previsões de treino do corretor recém-treinado contra o
`training_prediction_sha256` do corretor original, de modo que uma divergência
aparece no treino e não só no fim.

Tempos: a reprodução verificada da S11 levou cerca de 1 a 2 minutos por etapa
principal, com pico de processo próximo de 2,3 GiB no treino. A medição
equivalente para a S12 a partir de clone vazio é o que o script da seção
seguinte produz.

## A7. Verificação a partir de clone vazio

Toda a descrição acima pressupõe um repositório de trabalho. A pergunta da
Seção 2.8 é diferente: **um terceiro que receba apenas o repositório consegue
regenerar o CSV?** Isso nunca tinha sido testado, e estava registrado como
pendência nas anotações de leaderboard.

[scripts/verificar_clone_limpo.ps1](../scripts/verificar_clone_limpo.ps1)
executa exatamente esse teste:

```powershell
.\scripts\verificar_clone_limpo.ps1
```

Ele clona o repositório num diretório novo, lista **quais arquivos exigidos pela
reprodução não vieram no clone**, liga `data/raw` por junção de diretório (os
dados brutos não são copiados nem redistribuídos), monta um `.venv` limpo com
`py -3.11` a partir das dependências fixadas de `delivery/s11/requirements.txt`,
fixa as bibliotecas numéricas em uma thread, roda as quatro etapas com
cronometragem e compara o sha256 final. O relatório sai em
`reports/competition/reproducao_clone_limpo.json`.

O diagnóstico decisivo é o segundo: se os NPZ de `delivery/s12/evidence`
estiverem fora do controle de versão, a entrega da Seção 2.8 estaria incompleta
mesmo com o código inteiramente correto, e é melhor descobrir isso agora do que
depois de uma eventual premiação. O script segue a execução copiando o que
faltou, mas registra a ressalva no relatório e não apaga a distinção entre
"reproduziu" e "reproduziu com arquivos de fora do clone".

## A8. Achados relevantes

Três resultados deste projeto têm valor independente do placar.

**O oracle emparelhado da Rodada 27 era miragem.** Mediu-se um ganho potencial
de 8,49% entre a S12 e um análogo, e cinco rodadas o perseguiram. Para dois
erros normais de variância semelhante e correlação ρ, o oracle que escolhe
ponto a ponto o menor erro **usando o observado** reduz o RMSE pelo fator
`√(1 − (2/π)·√(1−ρ²))` mesmo que a diferença entre as duas previsões seja ruído
puro. Invertendo para 8,49%: ρ ≈ 0,967 — exatamente a correlação observada. O
gap inteiro era explicado sem nenhum sinal explorável.

**A parede de estimação.** Nove métodos, de famílias sem relação entre si, com
contagens de parâmetros de **um** a **78.561**, todos aterrissaram entre −0,1% e
+0,1%, enquanto os oracles desses mesmos métodos mediam 0,30% a 2,45%. O caso
mais nítido é o da janela de climatologia, em que o estimador era um único
escalar global: os alphas oracle ficaram estáveis entre 0,25 e 0,35 e os causais
oscilaram de 0,07 a 0,72. Cinco blocos de resíduo fortemente correlacionados não
contêm informação independente suficiente para calibrar nem um parâmetro.

**Onde mora o erro.** 62,4% de todo o erro quadrático está em lat ≥ −10, que são
101 das 301 linhas da grade. Um terço do mapa concentra quase dois terços da
perda. Uma equipe pública da mesma competição chegou independentemente à mesma
estrutura.

O registro completo, com os JSON de suporte, está em
[SINTESE_RODADAS_25_34.md](SINTESE_RODADAS_25_34.md).

## A9. Modelo simples alternativo

A climatologia causal de 60 anos marca **1,85468** e custa segundos para
computar. Ela é a linha de base honesta: qualquer discussão sobre o valor deste
pipeline é a diferença entre 1,85468 e 1,71456.

Entre esse extremo e a S12, a versão **S10** é o controle que passou na
validação histórica sem exceção autorizada, marcando 1,71895 — a 0,26% da S12.
Quem quiser o sistema mais defensável, e não o de melhor score, deve usar a S10;
ela é reproduzível pela mesma interface, com `--versao s10`.

## A10. Limites do que é afirmado aqui

Os scores públicos são relatos do participante; o leaderboard público mede
apenas 2023, e o privado medirá 2024 — regimes ENSO opostos, com 2023 no pico
do El Niño e 2024 decaindo para La Niña. O resultado privado e a classificação
final são desconhecidos.

A S11 e a S12 foram exceções autorizadas ao critério interno de 0,3%, que é
política de seleção deste projeto e não regra da competição. Isso está
documentado como exceção e não afrouxa a política.

Esta é uma verificação técnica do que o repositório oferece, não uma
certificação de elegibilidade pelo organizador. As diretrizes da Kaggle pedem
resumo em Word ou PDF, normalmente em inglês; a documentação deste repositório
é em português por decisão do participante, e essa escolha precisa ser
confirmada com o organizador.
