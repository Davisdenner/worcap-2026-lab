# Diagnóstico de convergência de fluxo de umidade

**Resultado: encerrado por magnitude.** O sinal é consistente mas o teto é de 0,08%.

## Pergunta

A convergência de fluxo de umidade, `−div(q·V)` a 850 hPa, é o diagnóstico físico padrão de precipitação tropical e uma combinação **não-linear** de três variáveis que o pipeline já usa separadamente (`shum_850`, `u_850`, `v_850`). Nem PLS nem árvore sobre campos brutos a constroem sozinhas.

O resíduo da S12 é, por definição, o que o pipeline não explicou. Se a MFC do mês de origem correlaciona com esse resíduo no mês seguinte, é informação nova — não há risco de medir redundância.

## Resultado

Correlação média dos seis blocos entre cada campo e o resíduo da S12:

| grupo | shum_850 | u_850 | v_850 | mfc | mfc mesmo sinal |
| --- | ---: | ---: | ---: | ---: | ---: |
| DJF/lat<-30 | 0.013 | 0.027 | −0.013 | −0.003 | 4/6 |
| DJF/-30a-10 | −0.029 | −0.031 | 0.064 | −0.006 | 5/6 |
| DJF/lat>=-10 | 0.018 | 0.034 | 0.025 | 0.024 | 6/6 |
| MAM/lat<-30 | 0.037 | 0.023 | −0.036 | 0.008 | 3/6 |
| MAM/-30a-10 | 0.074 | 0.013 | −0.035 | 0.033 | 5/6 |
| MAM/lat>=-10 | 0.064 | 0.048 | 0.002 | 0.039 | 5/6 |
| JJA/lat<-30 | −0.022 | 0.066 | −0.022 | −0.000 | 3/6 |
| JJA/-30a-10 | −0.060 | 0.026 | 0.036 | −0.011 | 5/6 |
| JJA/lat>=-10 | 0.035 | 0.049 | 0.016 | 0.065 | 6/6 |
| SON/lat<-30 | −0.017 | 0.027 | 0.000 | −0.020 | 3/6 |
| SON/-30a-10 | 0.007 | −0.048 | 0.002 | −0.014 | 4/6 |
| SON/lat>=-10 | 0.009 | −0.007 | −0.027 | 0.032 | 5/6 |

Faixa tropical: melhor variável crua |r| = 0,031; MFC |r| = 0,040.

## Conclusão

Pela letra do critério declarado — superar as variáveis cruas e manter o sinal em ≥5/6 blocos — a MFC passa: é positiva nos quatro grupos tropicais, com 6/6 em DJF e JJA.

**Mas o critério estava mal formulado**, ancorado em consistência de sinal e não em magnitude. Uma correlação de 0,040 explica 0,16% da variância do resíduo, e o teto de RMSE que isso permite, com exploração linear perfeita, é `1 − √(1−0,040²)` = **0,08%**. Tomando só o melhor grupo, JJA tropical com r = 0,065 sobre 13,7% do erro quadrático, sai 0,03% global. Está na mesma faixa de tudo o mais.

O achado maior não é sobre a MFC. `shum_850`, `u_850` e `v_850` também ficam entre 0,03 e 0,07 em todos os doze grupos: **o resíduo da S12 é quase ortogonal a tudo que se extrai dos campos de 850 hPa por via linear e pontual, com um mês de antecedência.**

Duas ressalvas sobre o que isso não prova. A medida é **pontual e linear**, ponto a ponto; uma relação não-linear e espacialmente estruturada pode existir com correlação pontual próxima de zero — foi o que motivou a Rodada 32. E o resíduo medido é o da S12; um preditor base diferente teria outro.

A partir deste diagnóstico todo critério subsequente passou a ser ancorado em magnitude, com o limiar derivado antes da execução. Nenhuma candidata, CSV ou submissão foi criada. [mfc.json](mfc.json)
