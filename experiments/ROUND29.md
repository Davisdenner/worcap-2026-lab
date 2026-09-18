# Rodada 29 — famílias fora do HistBoost

Protocolo registrado antes de calcular qualquer resultado novo. Referência
imutável: S12 OOF. Pergunta: ExtraTrees, LightGBM ou regressão multivariada de
rank reduzido/CCA regularizada capturam estrutura útil, individualmente ou
como especialistas de erros diferentes? Nenhuma submission, uso de alvos
2023/24, promoção automática ou ajuste da S12.

## Cortes, atributos e orçamento

- Seis blocos OOF 2009–10, 2011–12, 2013–14, 2015–16, 2017–18 e 2019–20,
  grade completa, sempre com treino expanding-window anterior ao bloco.
  Os mesmos arquivos S12 congelados são a referência em cada bloco.
- ExtraTrees e LightGBM recebem os mesmos 119 atributos elegíveis do
  HistBoost principal da Rodada 20: 55 atributos locais e 64 PCs/contexto
  atmosférico. Treinam sobre as primeiras 768 células de cada origem geradas
  pelo amostrador `round20.nested_cells`, com alvo de anomalia em relação à
  climatologia de 60 anos. A avaliação é na grade completa, 24 meses/bloco.
  Nada do bloco de avaliação entra nas transformações ou no treino.
- ExtraTrees: `n_estimators=64`, `max_features=0.5`, `min_samples_leaf=8`,
  `max_depth=24`; e `n_estimators=96`, `max_features=0.75`,
  `min_samples_leaf=16`, `max_depth=24`. `bootstrap=False`, seed 20260929,
  quatro threads. Duas configurações fixas; não expandir a busca.
- LightGBM 4.6.0: 300 árvores, profundidade limitada a 8, learning rate
  0,05, 15 folhas, mínimo 100 por folha, feature fraction 0,8, bagging
  fraction 0,8/frequência 1, L2 10, L1 0; segunda configuração com 400
  árvores, learning rate 0,03, 31 folhas, mínimo 200, mesmas frações,
  L2 20, L1 0,1. Seed 20260929, quatro threads, deterministic/force_col_wise.
  É controle da família boosting, sem Optuna.
- RRR usa os mesmos 64 PCs/contexto atmosférico causal da Rodada 20 e o alvo
  de anomalia de precipitação em toda a grade. Centralizar X/Y no treino,
  branquear X com covariância do treino e ajustar ridge com penalidade 0,3;
  truncar a matriz de coeficientes por SVD para ranks {4,8,16,32}.
- CCA regularizada: obter 32 PCs do alvo **somente no treino** por SVD
  randomizada (seed 20260929, 8 oversamples, 2 power iterations),
  padronizar X e os scores do alvo pelo treino, usar regularização de
  covariância 0,3 em ambos os lados, reter {4,8,16,32} pares canônicos,
  decodificar os scores de chuva com ridge 0,3. Comparar com PLS16 OOF
  existente nos mesmos cortes, incluindo semelhança dos modos espaciais.
- CNN/U-Net pequena só seria executada com GPU e infraestrutura de treino
  razoáveis. A única GPU detectada é NVIDIA MX350 de 2 GB; PyTorch/CUDA não
  está instalado. O custo de preparar e treinar 6 folds espaciais nesse
  dispositivo não é razoável nesta rodada. Registrar D por inviabilidade de
  infraestrutura, sem inferir desempenho científico da família.

## Métricas e paradas

Calcular na grade completa RMSE agregado, por bloco, ano, latitude e norte;
correlação/covariância de resíduos com S12; oracle pareado que conhece o alvo
(diagnóstico apenas); mistura operacional fixa 10% do novo especialista com
90% S12; blocos/anos positivos; tempo de treino e inferência. O baseline S12
é reavaliado nos mesmos arquivos e meses. A tabela principal inclui RMSE,
correlação, oracle, estabilidade e custo. Não interpretar pixels como
replicações temporais independentes.

Parada predefinida após três blocos para uma família tabular somente se **todas**
as configurações tiverem RMSE >3% pior que S12 em cada bloco, correlação de
resíduos >0,995, oracle <1% de ganho e mistura 10% sem ganho em cada bloco.
Caso contrário completar seis blocos. RRR/CCA seguem até seis blocos, salvo
falha técnica real. Nunca escolher configuração olhando um fold para alterar
o treino dos folds seguintes.

Classificação exploratória predefinida por configuração nos seis blocos:

- A: RMSE agregado pelo menos 0,3% menor que S12, 4/6 blocos e 7/12 anos
  melhores. Ainda não promove automaticamente.
- B: se não A, mistura fixa 10% melhora pelo menos 0,1% global e em 4/6
  blocos, e oracle ganha pelo menos 1% global.
- C: demais configurações concluídas sem sinal individual/complementar
  suficiente, em especial resíduos muito correlacionados e custo maior.
- D: infraestrutura indisponível ou custo inviável, sem alegação de derrota
  preditiva não medida.

Selecionar no máximo duas famílias para investigação posterior, com base em
RMSE, estabilidade e diversidade. Reconhecer viés de seleção acumulado nos
mesmos blocos históricos. Nenhum score público entra na decisão desta rodada.
