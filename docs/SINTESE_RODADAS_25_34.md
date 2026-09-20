# Síntese das rodadas 25 a 36: por que a S12 não foi superada

Documento de fechamento do ciclo que começou depois da S12. Registra o que
testei, o que descartei e, principalmente, as restrições estruturais que
explicam por que doze investigações seguidas chegaram ao mesmo lugar.

Escrevi este texto para ser lido por alguém que não acompanhou o projeto.
Os termos são definidos na primeira vez que aparecem e cada afirmação vem com
o número que a sustenta.

O nome do arquivo preserva o intervalo original de rodadas para não quebrar os
links já publicados. O conteúdo foi estendido até a rodada 36.

## Vocabulário mínimo

**Bloco.** Um ano de avaliação fora do treino. Uso seis: 2009, 2011, 2013,
2015, 2017 e 2019. Para cada bloco, o modelo é treinado apenas com alvos
anteriores a ele, o que evita olhar para o futuro.

**OOF, ou fora do treino.** Previsão feita para dados que o modelo nunca viu
no ajuste. É a validação honesta deste projeto.

**Oracle.** O melhor resultado possível de um método se alguém já soubesse a
resposta na hora de escolher o parâmetro. Serve como teto: nenhum estimador
real supera o próprio oracle. A distância entre oracle e resultado causal mede
quanto do sinal é aproveitável na prática.

**Causal.** O oposto do oracle. O parâmetro é estimado apenas com informação
disponível antes do período avaliado.

**Limiar de promoção.** A regra interna que decidia se uma variante substituía
a referência: ganho relativo de pelo menos 0,3%, mais estabilidade em 4 de 5
blocos, 7 de 10 anos e 67 de 120 meses.

## Onde o projeto chegou

A S12 marca **1,71456** no leaderboard público, em oitavo lugar. O líder está
em 1,49924, uma diferença de 0,215, ou **12,6%**. Entre o quarto e o oitavo
lugar existe um pelotão apertado, com apenas 0,033 de amplitude. Os três
primeiros estão progressivamente destacados.

A trajetória dos envios, todos com dado oficial a partir da S09:

| envio | público | observação |
| --- | ---: | --- |
| climatologia de 60 anos | 1,85468 | referência |
| S02 | 1,81543 | |
| S03 | 1,76467 | |
| S07 | 1,73550 | TSM do Pacífico, NOAA |
| S08 | 1,74606 | com Atlântico, NOAA; piorou |
| S09 | 1,72957 | somente oficial, daqui em diante |
| S12 | **1,71456** | melhor público |
| S13 | 1,71461 | |

Duas leituras importam aqui.

O dado externo funcionou uma vez, na S07, com ganho real de 0,55% sobre a S06.
Já a S08 passou na validação de desenvolvimento e na confirmação de 2021 e
2022, e mesmo assim **piorou** no leaderboard. Foi essa divergência entre
validação e teste que motivou a restrição `only_official_data` a partir da
Rodada 9.

A S12 vai melhor no teste (1,715) do que na própria validação OOF (1,756).
Isso significa que a validação é conservadora, não otimista. É raro, e protege
contra surpresa no conjunto privado: quando a validação promete menos do que
entrega, o risco de decepção no resultado final é menor.

**O leaderboard público mede apenas 2023 e o privado medirá 2024.** São
regimes ENSO opostos: 2023 no pico do El Niño e 2024 decaindo para La Niña.

## O que testei

| rodada | hipótese | resultado |
| --- | --- | ---: |
| 27 | gates logístico, ridge e HGB entre S12 e análogo | +0,075% |
| 28 | top-k de vitórias fortes | +0,040% |
| 30 | gate convolucional com contexto 2D | +0,078% |
| 31-diag | recalibração de amplitude da anomalia | +0,051% |
| diag | convergência de fluxo de umidade | teto de 0,08% |
| 32 | U-Net ponta a ponta sobre campos atmosféricos | −3,78% |
| diag | ENSO (ONI) sobre o resíduo | −1,21% causal |
| diag | janela de climatologia | +0,113% |
| 33 | volume de células no corretor, 10,7 vezes maior | −0,055% |
| 35 | persistência de precipitação | +0,049% |
| 36 | corretor máximo, início do treino em 1940 | +0,110% |
| diag | combinação de S10 com S12 | oracle de 0,000% |

Doze investigações. Nenhuma passou o limiar de promoção de 0,3%.

## As seis restrições estruturais

O valor duradouro deste ciclo não está em nenhuma rodada isolada, e sim nas
restrições que elas revelaram em conjunto.

### 1. O oracle emparelhado era miragem

A Rodada 27 mediu um oracle de 8,49% entre a S12 e um análogo, e as rodadas 25
a 30 perseguiram esse número. Ele não era capturável, e dá para provar isso.

Para dois erros normais de variância parecida e correlação `ρ`, o oracle que
escolhe ponto a ponto o menor erro **usando o observado** reduz o RMSE pelo
fator `√(1 − (2/π)·√(1−ρ²))`, mesmo que a diferença entre as duas previsões
seja ruído puro. Invertendo a fórmula para 8,49%, chega-se a `ρ ≈ 0,967`. Ou
seja: duas previsões correlacionadas a 0,97, diferindo apenas por ruído
imprevisível, produzem exatamente aquele gap, com zero sinal explorável.

Os próprios dados da Rodada 27 já diziam isso. A taxa de vitória do análogo
foi de 46,72%, quase uma moeda justa, variando só de 40% a 53% entre regimes.

O que distingue um oracle informativo de uma miragem é **quantos graus de
liberdade ele consome**. O da Rodada 27 escolhia ponto a ponto, o que são
milhões de decisões livres. O do diagnóstico de amplitude consumia 24
parâmetros. Seis ordens de grandeza de diferença.

### 2. A parede de estimação

Nove métodos, de famílias sem relação entre si, com contagens de parâmetros
que vão de **um** a **78.561**, aterrissaram todos entre −0,1% e +0,1%. Ao
mesmo tempo, os oracles desses mesmos métodos mediram 0,30%, 0,40%, 0,76% e
2,45%. O sinal existe e se repete; o que falha é a estimação.

A demonstração mais nítida está no diagnóstico de janela de climatologia. Ali
o estimador era **um escalar global**, um único parâmetro, desenhado assim
justamente como resposta às falhas de sobreparametrização anteriores. Os
alphas oracle ficaram estáveis entre 0,25 e 0,35, enquanto os causais
oscilaram de 0,07 a 0,72, errando por um fator de dois.

A conclusão é desconfortável e vale escrever por extenso: **cinco blocos de
resíduo da S12, fortemente correlacionados no tempo e no espaço, não contêm
informação independente suficiente para calibrar nem um parâmetro.** Qualquer
correção que precise ser ajustada nesse conjunto está condenada à faixa de
±0,1%, seja qual for o método.

O corolário prático orientou as últimas rodadas: só escapam dessa parede as
intervenções que **não calibram nada nos blocos de avaliação**, ou seja, mais
dado de treino, mais capacidade de modelo e agregação por reamostragem.

A Rodada 36 confirmou essa previsão pela primeira vez. Ampliar o início do
treino de 1981 para 1940, o que acrescenta 41 anos de dados, levou o corretor
direto de 1,794009 para 1,788355 e a variante misturada de +0,076% para
+0,110%, com 5 de 5 blocos e 9 de 10 anos positivos.

### 3. O piso de ruído amostral

A Rodada 33 mediu isso sem estar procurando: dois corretores idênticos em tudo
menos no sorteio de 768 células diferem em **0,39%** no RMSE direto. Propagado
para a mistura nas frações 0,10 e 0,25, isso dá cerca de 0,1% na métrica de
promoção, contra um limiar de 0,3%.

A razão sinal-ruído do critério é de aproximadamente **três para um**. É
apertado, e ajuda a explicar por que resultados marginais não se sustentaram.

É também por isso que a estabilidade importa tanto quanto a amplitude. Um
ganho de 0,110% com 5 de 5 blocos positivos é mais confiável que um de 0,153%
com 4 de 5: sob ruído puro, acertar 5 de 5 tem probabilidade de 3,1% e 9 de 10
anos tem 1,07%, enquanto a diferença de 0,043% entre os dois ganhos está
inteiramente dentro do piso.

### 4. Onde mora o erro

Da radiografia por grupo: **62,4% de todo o erro quadrático está na faixa de
latitude maior ou igual a −10**, que corresponde a 101 das 301 linhas da
grade. Um terço do mapa concentra quase dois terços da perda, com RMSE de 2,2
a 2,6 contra 1,0 a 1,4 no sul.

Uma equipe pública da mesma competição chegou à mesma estrutura de forma
independente: ganho de 12,6% sobre a climatologia na Amazônia, 0,3% no Brasil
central e 1,4% na Patagônia.

O corolário é direto: qualquer melhoria precisa acontecer no trópico, ou não
importa.

### 5. O canal pontual está esgotado

O resíduo da S12 correlaciona entre 0,03 e 0,07 com **todas** as variáveis de
850 hPa, em todos os doze grupos. A convergência de fluxo de umidade, que é
uma combinação não linear dessas variáveis, chega a apenas 0,040. A medida é
pontual e linear, célula contra célula, que é exatamente como
`round2.Features.matrix` constrói suas 55 colunas.

A Rodada 33 separou volume de capacidade: multiplicar as células por 10,7
melhorou o corretor em **0,303%** numa comparação pareada. É real, mas de
segunda ordem. Com 31 folhas e cem observações por folha, mais dados refinam
valores em vez de criar estrutura.

### 6. As submissões antigas não carregam informação nova

O diagnóstico de combinação testou a única direção que nenhuma rodada tinha
tentado: em vez de mexer no corretor, combinar previsões que já existem. A
S10 difere da S12 em duas coisas, a recalibração conjunta de pesos e o
corretor não linear, enquanto todas as variantes testadas diferem só na
segunda.

O oracle deu **0,000%**, e o motivo é estrutural. Dois números coincidem até a
quarta casa: `ρ(S12, S10) = 0,9809` e `RMSE(S12)/RMSE(S10) = 0,98089`. A
condição `w* = 1`, que significa peso total na S12, é exatamente `ρ = e₁/e₂`,
que por sua vez equivale a `cov(e₁, e₂ − e₁) = 0`.

Em palavras: **o erro da S10 é o erro da S12 mais um componente ortogonal a
ele.** A S10 não é um modelo diferente que erra em lugares diferentes; é a S12
mais ruído. Não há informação a extrair porque não existe informação ali.

## Contrato do teste, verificado

O arquivo `teste_features.nc` entrega, para cada um dos 24 meses-alvo de
2023-01 a 2024-12, o estado atmosférico **real** do mês imediatamente
anterior. O campo `time_origem` vai de 2022-12 a 2024-11, todas as entradas
são distintas, e a correlação entre a primeira e a última cai a 0,705 em
`cloud_cover`. A tarefa é uniformemente de **um mês de antecedência**, e a
convenção OOF do pipeline está alinhada com ela.

O campo `lag_meses`, que vai de 1 a 24, mede a distância até a última
precipitação observada, não o horizonte atmosférico: `tp_ultima_obs` é o campo
de dezembro de 2022 repetido 24 vezes. **A precipitação congela ali**, e esse
detalhe tem consequência prática, tratada na seção seguinte.

`Features.matrix` não tem nenhuma coluna de precipitação, o que mantém treino
e teste alinhados e explica por que a validação é conservadora.

## A fronteira do dado externo

A Seção 2.6 das regras permite Dados Externos de domínio público, gratuitos e
igualmente acessíveis. A fronteira aplicada neste projeto:

**Permitido.** Variáveis que não são o alvo. O ONI é temperatura da superfície
do mar no Pacífico; baixei com proveniência registrada (URL, sha256 e política
temporal) e testei sob critério causal estrito.

**Fora.** A precipitação observada do **mês-alvo**, em qualquer formulação e
de qualquer fonte. O alvo é a precipitação mensal do ERA5, que está publicada
no Copernicus CDS e cobre 2023 e 2024. Baixá-la é recuperar o gabarito, não
prever. A organização confirmou que o arquivo é público e pediu
explicitamente que não seja usado.

### Correção de um argumento anterior

Uma versão anterior deste documento afirmava que usar a chuva do *mês de
origem* já seria recuperação de rótulo, porque o conjunto de origens e o de
alvos se sobrepõem em 23 dos 24 meses. O argumento estava errado.

O critério do organizador é outro: para prever o mês T vale qualquer dado que
em tese estaria disponível até o fim de T−1, e a interseção entre os dois
conjuntos não é o teste. A chuva de T−1 é observável antes de T e portanto é
preditor legítimo. Foi sobre essa base que a Rodada 35 foi construída. O que
não vale é usar o próprio mês T para estimar T.

### A armadilha do arquivo de teste

Essa distinção tem consequência prática, porque o `teste_features.nc` a viola
sozinho se for lido de través. Cada linha traz o estado atmosférico do mês
anterior ao seu alvo, e os 24 alvos são consecutivos. Logo, os campos do
mês-alvo da linha *i* reaparecem como campos de origem da linha *i+1*:

| linha | mês-alvo | campos que a linha contém |
| --- | --- | --- |
| 1 | 2023-01 | atmosfera de 2022-12 |
| 2 | 2023-02 | atmosfera de 2023-01, que é o alvo da linha 1 |
| 3 | 2023-03 | atmosfera de 2023-02, que é o alvo da linha 2 |

Para 23 dos 24 meses existe, dentro do arquivo oficial, a nuvem e a umidade do
mês que deveria ser previsto. Como nuvem e umidade têm relação direta com a
chuva daquele mês, cruzar linhas transforma previsão em estimativa sem
precisar de nenhum dado externo.

Este pipeline não cruza linhas: `round19_history.feature_rows` indexa
`fields[j][origin, cells]` com um escalar e `s12_delivery.predict` passa
`origin = month`. A afirmação é verificável sem ler o código, por
[testar_vazamento_temporal.py](../scripts/testar_vazamento_temporal.py), que
embaralha as demais linhas do arquivo oficial e exige que a previsão do mês
preservado saia bit a bit idêntica, com controle negativo para garantir que o
teste tenha poder de detecção.

### O ganho que não é entregável

A limitação mais cara do ciclo apareceu tarde, ao montar a exportação da
Rodada 36, e vale registrar como aprendizado de método.

As rodadas 35 e 36 foram as únicas a superar a S12, e todo o ganho delas vem
de oito colunas de persistência de precipitação lidas na origem. Nos seis
blocos OOF isso funciona, porque todas as origens estão dentro de 1940 a 2022.
No período de teste, não: a precipitação oficial congela em dezembro de 2022,
como a seção do contrato mostra. Para 23 dos 24 meses-alvo essas colunas não
existem.

Sem elas, a configuração é a `r33_119`, que mede **−0,055%**. A única forma de
obtê-las seria baixar a precipitação do ERA5 de 2023 e 2024, que é o alvo.

Verifiquei, ao propor a Rodada 35, que a persistência era legal pelo critério
temporal e que `tp.npy` cobria todas as origens dos blocos de validação. Não
verifiquei se ela existiria no período de teste. **A verificação de
disponibilidade no teste deveria ter precedido a construção**, e não o
contrário.

## O que permanece aberto

**Os logs da Rodada 32.** Os campos `best_inner_valid` e `epochs_run` por
bloco estão gravados e nunca foram lidos. Se a U-Net bateu no teto de 25
épocas ainda melhorando, o orçamento foi pequeno demais e a conclusão sobre
arquitetura convolucional não está demonstrada. É a única questão em aberto
com tamanho compatível com o gap de 12,6%.

**Previsão dinâmica sazonal.** É a hipótese que melhor explica um líder 12,6%
à frente. Modelos como NMME e ECMWF SEAS5, inicializados no mês de origem,
carregam informação sobre o mês-alvo que nenhum método estatístico sobre a
reanálise consegue recuperar, porque ela não está lá. É permitido pelas regras
e não foi tentado.

**A persistência em lag realista.** Retreinar as colunas de persistência no
lag que de fato estará disponível, ou seja, a chuva de dezembro de 2022
defasada de 1 a 24 meses conforme o alvo. Usa somente dado da competição. O
sinal decai rápido com o lag, então o ganho médio seria uma fração dos 0,651%
medidos em lag 1.

## Avaliação honesta

Doze investigações sem ganho promovível é um resultado desconfortável, mas não
é um resultado vazio. O ciclo produziu uma explicação estrutural para o platô,
e essa explicação é verificável, quantificada e reprodutível a partir dos JSON
depositados em `reports/competition/`.

A diferença de 12,6% para o líder não foi explicada. Nenhuma das hipóteses
testadas tem tamanho para ela, e o projeto não descobriu o que falta. Isso
fica registrado como pergunta aberta, não como conclusão.
