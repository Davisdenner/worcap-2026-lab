# Rodada 23 — hipótese 4: saída ampla + detalhe local

Protocolo fixado antes de avaliar candidatas, com os mesmos dados oficiais,
amostragem de 512 células/mês, treino desde janeiro/1981, 55 atributos,
climatologia causal e hiperparâmetros da rodada 22. Referência S12 e mesmo
controle direto de 1981. Períodos já reutilizados, não teste independente.

Em cada alvo histórico completo, suavizar **somente no espaço** a precipitação
com filtro uniforme 9×9, borda `nearest`. O modelo amplo aprende
`suavizar(chuva) − suavizar(climatologia)`; o modelo local aprende
`chuva − suavizar(chuva)`. Ambos usam exclusivamente o estado atmosférico
de M ou anterior. Na inferência, reconstruir
`suavizar(climatologia) + previsão_ampla + previsão_detalhe`, limitar a zero
e pontuar na grade original de 0,25°. Não suavizar o alvo de validação na
avaliação, nem usar chuva do mês-alvo como atributo. Aprender as duas parcelas
nos mesmos exemplos e meses do controle direto.

Avaliar modelo decomposto puro e misturas `S12 + a*(decomposto−S12)` com
`a=0,10` e `0,25`. O controle direto usa exatamente os mesmos atributos,
amostras, iterações e misturas. Exigir, contra S12, o mesmo gate: ganho
>=0,3%, segundos anos melhores, >=5/6 blocos, >=9/12 anos,
>=80/144 meses, pior perda anual <=0,5%. Se não passar, nenhuma confirmação
ou submissão. Caso passe, confirmar uma única escolhida em 2021–2022
reutilizado, ganho >=0,1% e ambos os anos melhores. Este ensaio de árvores
locais não é uma prova de que nenhuma outra arquitetura multiescala funcionaria.
