# Rodada 22 — hipótese 3: início do treino dos modelos-base

Protocolo fixado antes de avaliar candidatas. Somente arquivos oficiais e
previsões históricas OOF. Nenhum CSV ou envio. Referência S12.

O teste controlado usa a família-base de árvores locais/contextuais, não
refaz todos os componentes da S12. Três inícios predefinidos: março/1940
(os dois meses anteriores são necessários ao contexto), janeiro/1960 e
janeiro/1981. Mesmo desenho, amostras, corte, climatologia causal de 60 anos,
atributos e hiperparâmetros em todos os inícios. A climatologia não se alonga
com o início do treino. O alvo é chuva de M+1 menos climatologia do mês alvo.
Os 55 atributos de `round2.Features` e as médias atmosféricas são ajustados
somente com meses anteriores ao corte. Sorteio determinístico por mês de
origem, 512 células sem reposição, igual nos meses comuns entre variantes.

Árvore HGB: squared_error, 15 folhas, 150 iterações, learning_rate 0,05,
min_samples_leaf 100, L2 10, 128 bins, early_stopping=False, semente
20260914, uma thread. Duas misturas fixas com S12: 0,10 e 0,25. O controle
1981 usa precisamente a mesma rotina. Comparar modelos puros para isolar
efeito da data; avaliar seis misturas contra S12 sem inferir que o ganho
isolado melhora a combinação final.

Desenvolvimento: seis blocos 2009–2020 de 24 meses, grade toda, RMSE. Exigir
ganho >=0,3%, segundos anos melhores, >=5/6 blocos, >=9/12 anos,
>=80/144 meses, pior perda anual <=0,5%. Escolher só candidata elegível.
Se nenhuma passar, não confirmar nem gerar S13. Se passar, confirmar no
2021–2022 reutilizado com ganho >=0,1% e ambos os anos melhores. Este teste
não autoriza promoção automática nem atesta que todos os componentes da S12
se beneficiariam do histórico anterior a 1981.
