# Rodada 29: famílias fora do HistBoost

Comparação OOF causal nos seis blocos 2009 a 2020, sempre contra a S12
inalterada. Dados e transformações de cada corte foram ajustados antes
do bloco avaliado. Nenhum alvo 2023/24, submission ou score público foi usado.

## Tabela principal

O oracle escolhe o menor erro por pixel **com acesso ao observado**:
é limite diagnóstico, não previsão operacional. Ensemble é o blend
fixo 90% S12 + 10% novo modelo, sem ajuste após os folds.

| Modelo | RMSE | Corr(e,S12) | Cov(e,S12) | Oracle RMSE | Blend 10% (ganho) | Blocos/anos melhores | Custo treino+pred (s) | Classe |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| s12 | 1.770775 | 1.0000 | 3.1346 | 1.770775 | +0.000% | 0/6, 0/12 | 0.0 | ref. |
| pls16_existing | 1.806777 | 0.9816 | 3.1398 | 1.685292 | -0.035% | 0/6, 0/12 | 0.0 | controle |
| extratrees_64 | 1.825387 | 0.9730 | 3.1436 | 1.670423 | -0.058% | 0/6, 0/12 | 666.7 | C |
| extratrees_96 | 1.818640 | 0.9745 | 3.1369 | 1.671619 | -0.035% | 0/6, 1/12 | 1399.0 | C |
| lightgbm_15 | 1.817741 | 0.9732 | 3.1308 | 1.668901 | -0.018% | 0/6, 0/12 | 101.1 | C |
| lightgbm_31 | 1.816119 | 0.9739 | 3.1304 | 1.669429 | -0.015% | 0/6, 1/12 | 176.0 | C |
| rrr_4 | 1.820055 | 0.9697 | 3.1239 | 1.664022 | +0.002% | 0/6, 1/12 | 1.1 | C |
| rrr_8 | 1.829410 | 0.9669 | 3.1306 | 1.662680 | -0.024% | 0/6, 0/12 | 1.1 | C |
| rrr_16 | 1.843312 | 0.9612 | 3.1363 | 1.655079 | -0.047% | 0/6, 0/12 | 1.1 | C |
| rrr_32 | 1.859425 | 0.9524 | 3.1340 | 1.643926 | -0.051% | 0/6, 0/12 | 1.2 | C |
| cca_4 | 1.810051 | 0.9761 | 3.1278 | 1.674178 | -0.003% | 0/6, 0/12 | 2.3 | C |
| cca_8 | 1.808319 | 0.9769 | 3.1273 | 1.676901 | -0.000% | 0/6, 0/12 | 2.2 | C |
| cca_16 | 1.810028 | 0.9761 | 3.1275 | 1.674949 | -0.002% | 0/6, 1/12 | 2.3 | C |
| cca_32 | 1.817700 | 0.9739 | 3.1339 | 1.672167 | -0.025% | 0/6, 1/12 | 2.2 | C |

## Estabilidade, regiões e modos

As métricas completas por bloco, ano, norte e faixa de latitude
estão em `summary.json`; os mapas e hashes individuais ficam em
`data/processed/round29`. Os números abaixo são por configuração
fixada, não escolha de um fold para ajustar o próximo.

### ExtraTrees

- `extratrees_64`: RMSE global 1.825387 (-3.084% vs S12); norte 2.814978; oracle +5.67%; blend 10% -0.058% em 2/6 blocos. Blocos (individual/blend): 2009: -3.57%/+0.01%, 2011: -3.74%/-0.15%, 2013: -2.71%/-0.09%, 2015: -3.63%/-0.06%, 2017: -1.12%/+0.06%, 2019: -3.75%/-0.13%.
- `extratrees_96`: RMSE global 1.818640 (-2.703% vs S12); norte 2.803654; oracle +5.60%; blend 10% -0.035% em 2/6 blocos. Blocos (individual/blend): 2009: -3.21%/+0.04%, 2011: -3.19%/-0.12%, 2013: -2.52%/-0.09%, 2015: -3.24%/-0.04%, 2017: -0.87%/+0.07%, 2019: -3.22%/-0.09%.

### LightGBM

- `lightgbm_15`: RMSE global 1.817741 (-2.652% vs S12); norte 2.801988; oracle +5.75%; blend 10% -0.018% em 2/6 blocos. Blocos (individual/blend): 2009: -3.12%/+0.05%, 2011: -2.70%/-0.05%, 2013: -2.13%/-0.05%, 2015: -3.68%/-0.06%, 2017: -0.72%/+0.10%, 2019: -3.57%/-0.11%.
- `lightgbm_31`: RMSE global 1.816119 (-2.561% vs S12); norte 2.799858; oracle +5.72%; blend 10% -0.015% em 2/6 blocos. Blocos (individual/blend): 2009: -2.74%/+0.09%, 2011: -2.70%/-0.06%, 2013: -2.12%/-0.06%, 2015: -3.69%/-0.06%, 2017: -0.77%/+0.09%, 2019: -3.38%/-0.11%.

### RRR

- `rrr_4`: RMSE global 1.820055 (-2.783% vs S12); norte 2.806079; oracle +6.03%; blend 10% +0.002% em 3/6 blocos. Blocos (individual/blend): 2009: -1.32%/+0.21%, 2011: -3.63%/-0.05%, 2013: -4.00%/-0.13%, 2015: -1.15%/+0.15%, 2017: -2.15%/+0.01%, 2019: -4.67%/-0.20%. Sobreposição média de subespaço com PLS16: 0.983.
- `rrr_8`: RMSE global 1.829410 (-3.311% vs S12); norte 2.807736; oracle +6.10%; blend 10% -0.024% em 2/6 blocos. Blocos (individual/blend): 2009: -1.95%/+0.17%, 2011: -4.34%/-0.06%, 2013: -4.67%/-0.16%, 2015: -2.06%/+0.09%, 2017: -2.64%/-0.02%, 2019: -4.46%/-0.19%. Sobreposição média de subespaço com PLS16: 0.948.
- `rrr_16`: RMSE global 1.843312 (-4.096% vs S12); norte 2.817468; oracle +6.53%; blend 10% -0.047% em 2/6 blocos. Blocos (individual/blend): 2009: -2.26%/+0.21%, 2011: -5.53%/-0.12%, 2013: -5.99%/-0.23%, 2015: -2.78%/+0.07%, 2017: -3.45%/-0.06%, 2019: -4.87%/-0.19%. Sobreposição média de subespaço com PLS16: 0.776.
- `rrr_32`: RMSE global 1.859425 (-5.006% vs S12); norte 2.837529; oracle +7.16%; blend 10% -0.051% em 1/6 blocos. Blocos (individual/blend): 2009: -3.00%/+0.23%, 2011: -6.11%/-0.05%, 2013: -6.54%/-0.20%, 2015: -4.70%/-0.02%, 2017: -4.49%/-0.11%, 2019: -5.50%/-0.19%. Sobreposição média de subespaço com PLS16: 0.872.

### CCA regularizada

- `cca_4`: RMSE global 1.810051 (-2.218% vs S12); norte 2.790445; oracle +5.46%; blend 10% -0.003% em 3/6 blocos. Blocos (individual/blend): 2009: -1.93%/+0.09%, 2011: -3.56%/-0.12%, 2013: -2.21%/-0.05%, 2015: -1.23%/+0.10%, 2017: -1.34%/+0.04%, 2019: -3.10%/-0.10%. Sobreposição média de subespaço com PLS16: 0.966.
- `cca_8`: RMSE global 1.808319 (-2.120% vs S12); norte 2.786185; oracle +5.30%; blend 10% -0.000% em 3/6 blocos. Blocos (individual/blend): 2009: -1.80%/+0.09%, 2011: -3.23%/-0.10%, 2013: -2.76%/-0.10%, 2015: -0.65%/+0.17%, 2017: -1.38%/+0.03%, 2019: -3.00%/-0.11%. Sobreposição média de subespaço com PLS16: 0.913.
- `cca_16`: RMSE global 1.810028 (-2.217% vs S12); norte 2.777088; oracle +5.41%; blend 10% -0.002% em 2/6 blocos. Blocos (individual/blend): 2009: -0.67%/+0.24%, 2011: -3.19%/-0.08%, 2013: -3.35%/-0.14%, 2015: -1.40%/+0.08%, 2017: -1.81%/-0.01%, 2019: -3.10%/-0.13%. Sobreposição média de subespaço com PLS16: 0.723.
- `cca_32`: RMSE global 1.817700 (-2.650% vs S12); norte 2.783180; oracle +5.57%; blend 10% -0.025% em 2/6 blocos. Blocos (individual/blend): 2009: -0.96%/+0.22%, 2011: -3.41%/-0.08%, 2013: -3.50%/-0.13%, 2015: -2.28%/+0.03%, 2017: -2.30%/-0.06%, 2019: -3.66%/-0.16%. Sobreposição média de subespaço com PLS16: 0.907.

## Decisão

- **ExtraTrees: C.**
- **LightGBM: C.**
- **RRR: C.**
- **CCA regularizada: C.**
- **CNN/U-Net: D.**

A classe C significa que as configurações testadas não entregaram
ganho individual nem complementar estável. Os oracles de 5 a 7%
mostram diferenças pontuais, mas dependem do observado e não se
converteram no blend fixo causal. Não provam ausência de qualquer
estrutura nova em arquiteturas ou decisões ainda não testadas.
O melhor LightGBM isolado ficou em RMSE 1.816119 contra 1.770775 da S12; seu blend mudou o RMSE em -0.015%. Não há justificativa empírica para
outra rodada de tuning de boosting com estes atributos. ExtraTrees
também perdeu e teve custo substancialmente maior. RRR/CCA
diversificaram um pouco os resíduos, mas sem ganho operacional
estável; os modos dominantes têm grande sobreposição com PLS16.

Famílias para aprofundar na próxima rodada: nenhuma por enquanto.
A classe D de CNN/U-Net reflete apenas viabilidade: MX350 com 2 GB
e ausência de PyTorch/CUDA no ambiente do projeto. Não é resultado
de validação preditiva. LightGBM foi instalado apenas no ambiente
virtual local; nenhuma outra família de boosting foi adicionada.

## Limitações e rastreabilidade

Os blocos 2009 a 2020 já foram reutilizados em várias decisões; a
melhor linha de uma pequena grade ainda sofre viés de seleção.
Correlação e oracle por pixel descrevem diversidade, mas pixels
de um mesmo mês não são observações temporais independentes.
O custo tabelado inclui ajuste e previsão do modelo; preparação
comum dos atributos e PCs não está atribuída a cada configuração.
Nenhum modelo foi promovido e nenhuma submission foi criada.

- Protocolo SHA-256: `b415399807609c9d0d67866d4edc2d8ba81d3c1767e303bba5b599a5a302f5ee`
- Código de geração SHA-256: `372a57308dc1ec1e7486410fe6b692f2994da7e5c6245b16c7303c9c88a0e442`
- Síntese SHA-256: `b7898d49b896beee236a457501aa5a065cae3e825f971a3146e0daed06239527`
- Ambiente: Python 3.11.1, NumPy 2.4.6, scikit-learn 1.9.0, LightGBM 4.6.0.
- Auditoria: 84 mapas OOF com hashes e métricas refeitas.
