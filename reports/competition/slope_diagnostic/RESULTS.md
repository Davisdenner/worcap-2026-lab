# Diagnóstico de amplitude: a anomalia da S12 está calibrada?

**Resultado: não há ganho causal.** O sinal existe e o teto é de 0,401%, mas nenhum estimador causal sobrevive a cinco blocos.

## Pergunta

A amplitude da anomalia prevista pela S12 corresponde à skill que ela tem? Se o slope de `observado − climatologia` contra `previsto − climatologia` for menor que 1, amortecer a anomalia reduz o RMSE. O pooling de `round4.fit_weights` não pode capturar esse ganho: ele impõe soma de pesos igual a 1, piso de 0,1 por componente e nenhum intercepto, o que proíbe por construção qualquer encolhimento líquido em direção à climatologia.

## Hipótese descartada

Os slopes não são sistematicamente menores que 1, eles orbitam 1 e espalham de −0,17 a 1,85. Cruzando com a correlação (0,001 a 0,521), a explicação aparece: com slope ≈ 1 e correlação ≈ 0,2, a amplitude da anomalia prevista já é cerca de um quinto da observada. **O pipeline já é fortemente amortecido**, e não há superdispersão global a corrigir.

## Radiografia por grupo (blocos 2011 a 2020)

Doze grupos, três bandas de latitude por quatro estações, os mesmos de `round4.groups()`.

| grupo | %SSE | RMSE s12 | RMSE clim | clim vence | slope | lambda |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| DJF/lat<-30 | 4.5% | 1.175 | 1.189 | 0/5 | 0.996 | 0.08 |
| DJF/-30a-10 | 9.3% | 2.081 | 2.140 | 0/5 | 1.004 | 0.06 |
| DJF/lat>=-10 | 15.7% | 2.400 | 2.598 | 0/5 | 1.067 | 0.62 |
| MAM/lat<-30 | 4.8% | 1.216 | 1.232 | 0/5 | 1.002 | 0.05 |
| MAM/-30a-10 | 4.5% | 1.440 | 1.461 | 0/5 | 0.997 | 0.05 |
| MAM/lat>=-10 | 18.9% | 2.636 | 2.777 | 0/5 | 1.015 | 0.21 |
| JJA/lat<-30 | 4.9% | 1.229 | 1.241 | 2/5 | 0.934 | 0.35 |
| JJA/-30a-10 | 1.9% | 0.950 | 0.944 | 3/5 | 0.380 | 0.87 |
| JJA/lat>=-10 | 13.7% | 2.244 | 2.450 | 0/5 | 1.319 | 0.93 |
| SON/lat<-30 | 3.5% | 1.048 | 1.072 | 0/5 | 1.052 | 0.37 |
| SON/-30a-10 | 4.2% | 1.400 | 1.444 | 1/5 | 1.184 | 0.65 |
| SON/lat>=-10 | 14.1% | 2.280 | 2.393 | 0/5 | 1.001 | 0.05 |

Dois achados estruturais saem daqui e são reutilizados nas rodadas seguintes.

**A climatologia praticamente nunca vence a S12**, 0/5 blocos em nove dos doze grupos. A S12 agrega valor real sobre climatologia em quase todo o domínio, o que fecha a ideia de encolhimento.

**62,4% de todo o erro quadrático mora na faixa lat ≥ −10**, que são 101 das 301 linhas da grade. Um terço do mapa concentra quase dois terços da perda, com RMSE de 2,2 a 2,6 contra 1,0 a 1,4 no sul.

## Estimadores

| variante | RMSE | ganho | blocos | anos | meses |
| --- | ---: | ---: | ---: | ---: | ---: |
| s12 | 1.756391 | +0.000% | - | - | - |
| slope único global (causal) | 1.755733 | +0.037% | 4/5 | 7/10 | 71/120 |
| 12 grupos, sem encolher | 1.757338 | −0.054% | 3/5 | 4/10 | 60/120 |
| 12 grupos, encolhido | 1.756424 | −0.002% | 3/5 | 6/10 | 60/120 |
| só grupos consistentes | 1.755496 | +0.051% | 3/5 | 7/10 | 23/120 |
| oracle por grupo (teto) | 1.749340 | +0.401% | 5/5 | 9/10 | 76/120 |

Quando a variante deixa um grupo intacto (`a = 1`), a previsão fica idêntica à S12 e conta como "não melhorou"; por isso a contagem de meses das variantes conservadoras subestima.

## Conclusão

O teto de 0,401% é real e os padrões são fisicamente coerentes: JJA na faixa −30 a −10 tem slope 0,380 com lambda 0,87, e JJA no trópico tem 1,319 com lambda 0,93, amortecer onde não há skill, amplificar onde há. Mas nenhum estimador causal converte isso. O primeiro diagnóstico, com intercepto livre e sem truncamento, chegou a exibir teto de 0,760%; metade daquilo era artefato de parametrização, e o valor honesto sempre foi 0,4%.

O diagnóstico decisivo está nos alphas: para `clim_50y` o causal deu 0,722 contra 0,346 do oracle. **Isso é um único escalar global, um parâmetro, e mesmo ele não se deixa estimar a partir de cinco blocos anteriores.** Essa observação é a origem da "parede de estimação" descrita na síntese do projeto.

Nenhuma candidata, CSV ou submissão foi criada. [slope.json](slope.json) · [shrink.json](shrink.json)
