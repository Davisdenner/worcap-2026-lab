# Rodada 30 — gate espacial convolucional entre S12 e o análogo H4

Protocolo registrado antes de calcular qualquer resultado novo. Referência
imutável: S12 e o análogo puro H4 (Rodada 25), ambos OOF já congelados.
Pergunta: um classificador com receptividade espacial real (patch 2D em
vez de atributos pontuais achatados) localiza melhor onde o análogo vence,
capturando mais do gap entre o oracle emparelhado (8,49% global, 9,00% no
norte, [Rodada 27](../reports/competition/round27/REPORT.md)) e o melhor
gate real já obtido (0,075%, `logistic_base_0.3`)? Esta rodada é uma
extensão direta da Rodada 27: mesma referência, mesmo escopo (norte,
0°–15°N), mesmos seis blocos causais, critério de promoção idêntico.
Nenhuma submissão, uso de alvos de 2023/2024, treino de um novo previsor
base ou ajuste da S12 é permitido aqui.

## Por que esta hipótese e não outra

A Rodada 28 mostrou que os classificadores tabulares (`logistic_full`,
`ridge_full`, `hgb_full`, todos sobre 108 atributos pontuais) já têm sinal
real — AUC de vitória forte até 0,92 — mas nenhum converteu isso em ganho
de RMSE estável acima do gate de 0,075%. Nenhum desses atributos inclui a
vizinhança espacial 2D bruta dos mapas: `local_context_7` e os PCs são
resumos já achatados em número. Esta rodada testa exatamente a peça que
faltava, sem tocar em mais nada do pipeline.

## Execução: só no Kaggle

Esta rodada exige PyTorch e GPU; o ambiente local (MX350, 2 GB, sem
CUDA/PyTorch) não é usado para treinar. O código roda em um notebook
Kaggle (ver `experiments/ROUND30_KAGGLE_SETUP.md`), com o dataset oficial
da competição anexado diretamente e os artefatos congelados enviados como
dataset privado por `scripts/package_round30_kaggle.py` +
`scripts/upload_round30_kaggle.py`. Os resultados (JSON, decisão) devem
retornar ao repositório em `reports/competition/round30/` antes de
qualquer decisão de promoção.

## Cortes, canais e orçamento

- Seis blocos OOF `round27.YEARS` = 2009–10, 2011–12, 2013–14, 2015–16,
  2017–18 e 2019–20; avaliação causal nos cinco blocos `round27.EVAL`
  (2011–2020), com o bloco 2009–2010 disponível só para treino, igual à
  Rodada 27. Nenhum alvo do próprio corte de avaliação entra no treino.
- Sete canais espaciais, todos mapas OOF já congelados de rodadas
  anteriores, sem retreinar nenhum: S12 (`round20.ART/{ano}_s12.npy`),
  análogo H4 (`round25.ART/{ano}_h4_prediction.npy`), e cinco componentes
  já usados no corretor da S12 e no oracle triplo da Rodada 28 — S02,
  modos regionais, árvore local+contexto (`local18`), PLS16 continental
  (`data/processed/round9`) e S09 (`data/processed/round10`). Todos em
  grade cheia 301×261 (`round25.LAT`/`round25.LON` confirmam eixo 0 =
  latitude crescente −60 a 15°, eixo 1 = longitude crescente −90 a −25°;
  o norte de `round26.NORTH` corresponde exatamente às linhas 240–300).
- Patch 15×15 (`PATCH=15`, meia-janela `HALF=7`), com espelhamento
  (`reflect`) nas bordas da grade cheia antes do recorte — não há
  wraparound de longitude nem contaminação de meses futuros: cada canal é
  o mapa do próprio mês-alvo, já causal por construção (os mapas S12/H4
  usados são OOF).
- Alvo: 1 se o análogo tiver erro quadrático menor que a S12 no ponto,
  igual à definição da Rodada 27. Treino amostra até 2.048 pontos do norte
  por mês (mesma ordem de grandeza do corretor da S12); avaliação usa
  **todos** os 15.921 pontos do norte de cada mês do bloco de teste, para
  comparação direta com a Rodada 27.
- Arquitetura fixa antes de qualquer resultado: duas convoluções 3×3 (32 e
  64 canais, ReLU), pooling global, uma camada densa de 32 com dropout
  0,3, saída logística. Adam, taxa 1e-3, weight decay 1e-4, 15 épocas,
  lote 512, semente 20260930. Duas configurações não serão testadas nesta
  rodada — arquitetura única, sem busca de hiperparâmetros.

## Métricas e paradas

Prevalência real vs. prevista, e a mesma aritmética de soft gating da
Rodada 27 (`altered = residual_norte − g·delta`, `g = gmax·P(análogo
melhor)`, S12 fora do norte), nas três capacidades já testadas lá
(`gmax` em 0,1; 0,2; 0,3). RMSE agregado, ganho relativo sobre S12,
blocos/anos/meses melhores nos mesmos cinco blocos 2011–2020.

Classificação predefinida, idêntica em espírito à das rodadas 27–29:

- **A**: alguma capacidade atinge ganho global ≥0,3% **e** ≥4/5 blocos,
  ≥7/10 anos e ≥67/120 meses melhores. Ainda não promove automaticamente
  — exige depois o mesmo protocolo completo (confirmação 2021–2022,
  limite de mudança, `src.round9.passes_gate`) de qualquer candidata.
- **D**: há ganho em alguma capacidade, mas sem a amplitude e a
  estabilidade de A — mesmo resultado do gate tabular da Rodada 27.
- **B**: toda capacidade piora a S12 (nenhum gate positivo).

Nenhuma S15, CSV ou envio é criado nesta rodada em nenhum cenário. Uma
classe A aqui abre uma rodada de confirmação separada, não uma promoção
direta.

## Limitações reconhecidas antes de ver qualquer resultado

Os blocos 2009–2020 já foram reutilizados extensivamente (rodadas 19–29);
há viés de seleção acumulado. Sete canais de sete famílias já usadas no
próprio pipeline não são informação nova sobre a atmosfera — apenas uma
forma nova de combiná-las espacialmente; um resultado nulo aqui não
descarta toda arquitetura convolucional, só esta escolha de canais e
patch. O código (`src/round30_cnn.py`) e este protocolo não foram
executados antes de congelados; qualquer erro de implementação encontrado
na primeira execução deve ser corrigido sem reabrir os critérios de
promoção acima.
