# Rodada 24 — transporte de umidade de 850 hPa

Protocolo fixado antes de avaliar as candidatas. Somente variáveis oficiais da
competição. Nenhum dado externo, chuva-alvo de 2023–2024, CSV ou upload.
Referência S12 imutável. Desenvolvimento: seis blocos de 24 meses em 2009–2020,
todos os 78.561 pontos e meses. Os períodos foram reutilizados anteriormente;
não são teste independente nem estimativa confiável do privado.

## Hipótese e controles

O corretor S12 global HGB15 usa 23 atributos, entre eles umidade específica q,
vento u/v em 850 hPa, mas não a **convergência espacial** do fluxo q·vento nem
seus lags. Reusar exatamente os exemplos OOF de resíduos S11 e a árvore
global original da S12. Ajustar três HGB15 com os mesmos exemplos, semente e
parâmetros da rodada 17, mudando apenas os atributos:

1. `produtos`: 23 + q·u, q·v (controle de mera interação não linear);
2. `convergencia`: 23 + produtos + `−div(q·u,q·v)` do mês M;
3. `transporte_lag`: 23 + convergência de M, M−1 e média M/M−1/M−2,
   mais diferença de q a 2° a montante na direção oposta ao vento médio de M.

A divergência é uma proxy bidimensional no nível de 850 hPa, não transporte
verticalmente integrado. Derivadas centrais com distância zonal corrigida por
`cos(latitude)`, distância meridional da grade 0,25° e bordas unilaterais;
multiplicar a convergência por 10⁶ para escala numérica. Em `q` a montante,
deslocar oito células (2°) em cada eixo contra o sinal de u/v, limitado à
grade. Os campos M−1 e M−2 são observados antes de M+1; não usar chuva futura.

Árvores: `HistGradientBoostingRegressor` squared_error, 15 folhas, 200
iterações, learning_rate 0,03, min_samples_leaf 300, L2 100, 128 bins,
early_stopping=False, semente 20260918. Treino em blocos anteriores completos
com os mesmos 2.048 pontos/mês da S12, reconstituídos e conferidos contra
latitude/longitude das amostras congeladas. Climatologia e componentes S11
herdados de seus cortes causais originais. O modelo `produtos` é ablação;
nenhuma de suas misturas pode ser selecionada.

## Oito candidatas fixas

Para `convergencia` e `transporte_lag`, substituir parcialmente a correção
global original da S12 por `delta_novo`, usando beta 0,25 ou 0,50.
Aplicar a substituição (a) em toda a grade ou (b) ao norte, com transição
linear de beta=0 em latitude −5° a beta pleno em 0° e acima. A máscara norte
vem do diagnóstico da S12; não será movida por desempenho de validação.
Previsão `max(S11+0,25*(delta_S12+beta*mascara*(delta_novo−delta_S12)),0)`.
Verificar beta zero reproduz S12. Não escolher pesos/áreas por bloco.

## Gate e decisão

Ganho RMSE >=0,3% sobre S12; segundo ano agregado melhor; >=5/6 blocos,
>=9/12 anos, >=80/144 meses melhores; pior perda anual <=0,5%. Selecionar
somente a menor RMSE elegível. Se nenhuma passar, parar antes da confirmação,
previsão final e CSV. Caso passe, confirmação em 2021–22 já reutilizado:
ganho >=0,1% e ambos os anos melhores. Mesmo assim, exportação somente com
pedido explícito. Medir separadamente SSE e RMSE na faixa 0°–15°N e fora
dela, sem usar esses resultados para mudar as oito candidatas.
