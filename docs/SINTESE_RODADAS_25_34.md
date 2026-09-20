# Síntese das Rodadas 25 a 34 — por que a S12 não foi superada

Documento de fechamento do ciclo iniciado após a S12. Registra o que foi
testado, o que foi descartado e — principalmente — as restrições estruturais
que explicam por que dez investigações consecutivas convergiram para o mesmo
lugar.

## Onde o projeto está

A S12 marca **1,71456** no leaderboard público, oitavo lugar. O líder está em
1,49924, uma diferença de 0,215 ou **12,6%**. Entre o quarto e o oitavo lugar
há um pelotão apertado de apenas 0,033 de amplitude; os três primeiros estão
progressivamente destacados.

A trajetória das submissões, todas com dado oficial a partir da S09:

| envio | público | |
| --- | ---: | --- |
| climatologia 60 anos | 1.85468 | referência |
| S02 | 1.81543 | |
| S03 | 1.76467 | |
| S07 | 1.73550 | TSM do Pacífico, NOAA |
| S08 | 1.74606 | + Atlântico, NOAA — piorou |
| S09 | 1.72957 | somente oficial, daqui em diante |
| S12 | **1.71456** | melhor público |
| S13 | 1.71461 | |

Dois pontos de leitura. O dado externo funcionou uma vez, na S07, com ganho
real de 0,55% sobre a S06; a S08 passou na validação de desenvolvimento e na
confirmação 2021–2022 e mesmo assim **piorou** no leaderboard, o que motivou a
adoção de `only_official_data` a partir da Rodada 9. E a S12 vai melhor no
teste (1,715) do que na própria validação OOF (1,756) — a validação é
conservadora, não otimista, o que é raro e protege contra surpresa no privado.

**O público mede apenas 2023; o privado medirá 2024.** São regimes ENSO
opostos: 2023 no pico do El Niño, 2024 decaindo para La Niña.

## O que foi testado

| rodada | hipótese | resultado |
| --- | --- | ---: |
| 27 | gates logístico, ridge e HGB entre S12 e análogo | +0,075% |
| 28 | top-k de strong wins | +0,040% |
| 30 | gate convolucional com patch 2D | +0,078% |
| 31-diag | recalibração de amplitude da anomalia | +0,051% |
| — | convergência de fluxo de umidade | teto 0,08% |
| 32 | U-Net ponta a ponta sobre campos atmosféricos | −3,78% |
| — | ENSO (ONI) sobre o resíduo | −1,21% causal |
| — | janela de climatologia | +0,113% |
| 33 | volume de células no corretor (10,7×) | −0,055% |
| 34 | capacidade do corretor (folhas) | em execução |

Dez investigações. Nenhuma passou o limiar de promoção de 0,3%.

## As cinco restrições estruturais

O valor duradouro deste ciclo não está em nenhuma rodada isolada, e sim nas
restrições que elas revelaram em conjunto.

### 1. O oracle emparelhado era miragem

A Rodada 27 mediu um oracle de 8,49% entre S12 e o análogo H4, e as Rodadas
25 a 30 perseguiram esse número. Ele não era capturável.

Para dois erros normais de variância semelhante e correlação ρ, o oracle que
escolhe ponto a ponto o menor erro **usando o observado** reduz o RMSE pelo
fator `√(1 − (2/π)·√(1−ρ²))`, mesmo que a diferença entre as duas previsões
seja ruído puro. Invertendo para 8,49%: **ρ ≈ 0,967**. Duas previsões
correlacionadas a 0,97, diferindo só por ruído imprevisível, produzem
exatamente aquele gap com zero sinal explorável.

Os próprios dados da Rodada 27 já diziam isso: taxa de vitória do análogo de
46,72%, quase a moeda justa, e variação de apenas 40% a 53% entre regimes.

O que distingue um oracle informativo de uma miragem é **quantos graus de
liberdade ele consome**. O da Rodada 27 escolhia ponto a ponto: milhões de
decisões livres. O do diagnóstico de amplitude consumia 24 parâmetros. Seis
ordens de grandeza de diferença.

### 2. A parede de estimação

Nove métodos, de famílias sem relação entre si, com contagens de parâmetros
que vão de **um** a **78.561**, todos aterrissaram entre −0,1% e +0,1%.
Simultaneamente, os oracles desses mesmos métodos mediram 0,30%, 0,40%, 0,76%
e 2,45% — sinal real, repetidamente.

A demonstração mais nítida está no diagnóstico de janela de climatologia. Ali
o estimador era **um escalar global**, um único parâmetro, desenhado assim
justamente como resposta às falhas de sobreparametrização anteriores. Os
alphas oracle ficaram estáveis entre 0,25 e 0,35; os causais oscilaram de
0,07 a 0,72, errando por um fator de dois.

**Cinco blocos de resíduo da S12, fortemente correlacionados no tempo e no
espaço, não contêm informação independente suficiente para calibrar nem um
parâmetro.** Qualquer correção que precise ser ajustada nesse conjunto está
condenada à faixa de ±0,1%, independentemente do método.

Corolário prático: só escapam dessa parede intervenções que **não calibram
nada nos blocos de avaliação** — mais dado de treino, mais capacidade de
modelo, agregação por reamostragem.

### 3. O piso de ruído amostral

A Rodada 33 mediu, sem procurar: dois corretores idênticos em tudo menos no
sorteio de 768 células diferem em **0,39%** no RMSE direto. Propagado para a
mistura nas frações 0,10 e 0,25, isso dá cerca de 0,1% na métrica de
promoção, contra um limiar de 0,3%.

A razão sinal-ruído do critério é de aproximadamente **três para um**. É
apertado, e ajuda a explicar por que resultados marginais não se sustentaram.

### 4. Onde mora o erro

Da radiografia por grupo: **62,4% de todo o erro quadrático está na faixa
lat ≥ −10**, que são 101 das 301 linhas da grade. Um terço do mapa concentra
quase dois terços da perda, com RMSE de 2,2 a 2,6 contra 1,0 a 1,4 no sul.

Uma equipe pública da mesma competição chegou independentemente à mesma
estrutura: ganho de 12,6% sobre climatologia na Amazônia, 0,3% no Brasil
central, 1,4% na Patagônia.

Corolário: qualquer melhoria precisa acontecer no trópico, ou não importa.

### 5. O canal pontual está esgotado, e o limite é capacidade

O resíduo da S12 correlaciona entre 0,03 e 0,07 com **todas** as variáveis de
850 hPa, em todos os doze grupos — e a convergência de fluxo de umidade,
uma combinação não-linear delas, chega a apenas 0,040. A medida é pontual e
linear, célula contra célula, que é exatamente como `round2.Features.matrix`
constrói suas 55 colunas.

A Rodada 33 então separou volume de capacidade: multiplicar as células por
10,7 melhorou o corretor em **0,303%** numa comparação pareada. Real, mas de
segunda ordem. Com 31 folhas e cem observações por folha, mais dados refinam
valores em vez de criar estrutura. `round20.MODELS` nunca testou mais de 31
folhas — daí a Rodada 34.

## Contrato do teste, verificado

`teste_features.nc` entrega, para cada um dos 24 meses-alvo de 2023-01 a
2024-12, o estado atmosférico **real** do mês imediatamente anterior
(`time_origem` de 2022-12 a 2024-11, todas as entradas distintas, correlação
entre a primeira e a última caindo a 0,705 em `cloud_cover`). A tarefa é
uniformemente de **um mês de antecedência**, e a convenção OOF do pipeline
está alinhada com ela.

`lag_meses`, que vai de 1 a 24, mede a distância até a última precipitação
observada, não o horizonte atmosférico: `tp_ultima_obs` é o campo de
dezembro de 2022 repetido 24 vezes. A precipitação congela ali.

`Features.matrix` não tem nenhuma coluna de precipitação, o que mantém treino
e teste alinhados e explica por que a validação é conservadora.

## A fronteira do dado externo

A Seção 2.6 das regras permite Dados Externos de domínio público, gratuitos e
igualmente acessíveis. A fronteira aplicada neste projeto:

**Permitido** — variáveis que não são o alvo. O ONI é temperatura de
superfície do mar no Pacífico; foi baixado com proveniência registrada
(URL, sha256, política temporal) e testado sob critério causal estrito.

**Fora** — a precipitação do período de teste, em qualquer formulação. O
argumento de que se poderia usar a chuva do *mês de origem* como preditor
não sobrevive à aritmética: o conjunto de origens é {2022-12, …, 2024-11} e
o de alvos é {2023-01, …, 2024-12}. **A interseção são 23 meses.** Buscar as
origens é buscar 23 das 24 respostas, deslocadas de uma linha. Não existe
versão dessa ideia que seja engenharia de atributos em vez de recuperação de
rótulo.

## O que permanece aberto

**Os logs da Rodada 32.** `best_inner_valid` e `epochs_run` por bloco estão
gravados e nunca foram lidos. Se a U-Net bateu no teto de 25 épocas ainda
melhorando, o orçamento foi pequeno demais e a conclusão sobre arquitetura
convolucional não está demonstrada. É a única questão em aberto com tamanho
compatível com o gap de 12,6%.

**A reprodução da S12 em clone vazio**, registrada como pendência nas
anotações de leaderboard e exigida pela Seção 2.8 caso haja premiação.

**A escolha das submissões finais.** O privado mede 2024. S12 e S13 diferem
em 0,00005 e errarão juntas; marcar as duas desperdiça a diversificação.

## Avaliação honesta

Dez investigações sem ganho promovível é um resultado desconfortável, mas não
é um resultado vazio. O ciclo produziu uma explicação estrutural para o platô
— e a explicação é verificável, quantificada e reprodutível a partir dos JSON
depositados em `reports/competition/`.

A diferença de 12,6% para o líder não foi explicada. Nenhuma das hipóteses
testadas tem tamanho para ela, e o projeto não descobriu o que falta. Isso
fica registrado como pergunta aberta, não como conclusão.
