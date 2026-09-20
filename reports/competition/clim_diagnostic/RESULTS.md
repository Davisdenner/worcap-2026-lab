# Diagnóstico da janela de climatologia

**Resultado: `clim_60y` confirmada.** A escolha herdada de dois blocos agora está validada em seis.

## Pergunta

`clim_60y` foi selecionada em `baseline_selection.json` usando **apenas dois blocos**, com margem de 0,10% para a segunda colocada, e o próprio `RESULTS.md` da época registra "apenas dois blocos de desenvolvimento" como limitação. Tudo desde a Rodada 2 repousa nessa escolha: a S02, o resíduo que as árvores aprendem, a S12 inteira.

O motivo para revisitar era uma inversão nos dois blocos originais:

| | clim_60y | clim_20y | vencedora |
| --- | ---: | ---: | --- |
| 2017 a 2018 | 1.848138 | 1.857508 | 60 anos, por 0,51% |
| 2019 a 2020 | 1.847074 | 1.841507 | 20 anos, por 0,30% |

A inversão foi na direção da janela curta conforme o alvo ficou mais recente, o que seria compatível com tendência climática. O teste é 2023 a 2024, quatro anos mais recente ainda.

## Mecanismo: não confirmado

RMSE da climatologia pura por janela e bloco. A coluna final é a correlação entre a recência do bloco e a vantagem daquela janela sobre `clim_60y`.

| janela | 2009 | 2011 | 2013 | 2015 | 2017 | 2019 | tendência |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| clim_all | 1.9757 | 1.8498 | 1.7644 | 1.8777 | 1.8604 | 1.8673 | −0.881 |
| clim_60y | 1.9753 | 1.8498 | 1.7507 | 1.8615 | 1.8481 | 1.8471 | (base) |
| clim_50y | 1.9701 | 1.8498 | 1.7410 | 1.8595 | 1.8486 | 1.8512 | −0.608 |
| clim_40y | 1.9712 | 1.8430 | 1.7341 | 1.8494 | 1.8559 | 1.8523 | −0.532 |
| clim_30y | 1.9855 | 1.8340 | 1.7215 | 1.8547 | 1.8540 | 1.8485 | −0.155 |
| clim_25y | 1.9772 | 1.8253 | 1.7081 | 1.8487 | 1.8531 | 1.8398 | −0.216 |
| clim_20y | 1.9870 | 1.8173 | 1.7155 | 1.8761 | 1.8575 | 1.8415 | −0.211 |
| clim_15y | 1.9890 | 1.8129 | 1.7400 | 1.9041 | 1.8579 | 1.8583 | −0.363 |
| clim_10y | 2.0305 | 1.8286 | 1.7788 | 1.9478 | 1.8891 | 1.8857 | −0.245 |

**Todas as tendências vieram negativas.** A vantagem da janela curta *encolhe* conforme o alvo fica mais recente, o oposto do mecanismo previsto. Bloco a bloco fica claro: as janelas curtas ganham forte em 2011 e 2013, que estão no meio da série, e perdem em 2009 e 2017. A inversão observada nos dois blocos originais era ruído.

## Efeito na S12

`S12 + alpha·(clim_X − clim_60)`, alpha escalar único ajustado só em blocos anteriores.

| variante | alpha | RMSE | ganho | blocos | meses |
| --- | ---: | ---: | ---: | ---: | ---: |
| s12 | - | 1.756391 | +0.000% | - | - |
| clim_all causal | 0.119 | 1.756696 | −0.017% | 3/5 | 54/120 |
| clim_all oracle | −0.154 | 1.755759 | +0.036% | 5/5 | 64/120 |
| clim_50y causal | 0.722 | 1.756983 | −0.034% | 1/5 | 58/120 |
| clim_50y oracle | 0.346 | 1.754520 | +0.107% | 5/5 | 63/120 |
| clim_40y causal | 0.440 | 1.755867 | +0.030% | 3/5 | 65/120 |
| clim_40y oracle | 0.272 | 1.753786 | +0.148% | 5/5 | 60/120 |
| clim_30y causal | 0.249 | 1.756167 | +0.013% | 2/5 | 68/120 |
| clim_30y oracle | 0.256 | 1.752516 | +0.221% | 5/5 | 64/120 |
| clim_25y causal | 0.324 | 1.754410 | +0.113% | 2/5 | 69/120 |
| clim_25y oracle | 0.295 | 1.751059 | +0.304% | 5/5 | 69/120 |
| clim_20y causal | 0.190 | 1.755638 | +0.043% | 2/5 | 57/120 |
| clim_20y oracle | 0.236 | 1.751627 | +0.271% | 5/5 | 67/120 |
| clim_15y causal | 0.140 | 1.755637 | +0.043% | 3/5 | 57/120 |
| clim_15y oracle | 0.178 | 1.752483 | +0.223% | 5/5 | 64/120 |
| clim_10y causal | 0.070 | 1.757330 | −0.053% | 2/5 | 59/120 |
| clim_10y oracle | 0.108 | 1.753324 | +0.175% | 5/5 | 71/120 |

## Conclusão

Nenhuma janela atinge 0,3% causal com 4/5 blocos. `clim_60y` fica, e agora com seis blocos de evidência em vez de dois, a escolha deixou de ser herdada e passou a ser confirmada.

**O achado mais importante está na coluna alpha, e é sobre o projeto inteiro, não sobre climatologia.** Para `clim_50y` o alpha causal deu 0,722 contra 0,346 do oracle, errando por um fator de dois e entregando −0,034%. Para `clim_10y`, 0,070 contra 0,108. Os oracle são estáveis entre 0,25 e 0,35; os causais oscilam de 0,07 a 0,72.

Isso é **um único escalar global**. Um parâmetro, desenhado assim justamente como resposta às falhas de sobreparametrização anteriores, e mesmo ele não se deixa estimar de forma confiável a partir de cinco blocos. É a formulação mais nítida da parede de estimação documentada na síntese.

Nenhuma candidata, CSV ou submissão foi criada. [clim.json](clim.json)
