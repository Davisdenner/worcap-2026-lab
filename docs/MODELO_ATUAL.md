# Modelo de referência — S10, somente dados oficiais

Composição, métricas e integridade reunidas em [S10_BASELINE.md](S10_BASELINE.md).
Rodada15 sem promoção: recalibração conjunta ganhou apenas 0,041% no agregado,
com melhora em 4/6 blocos e 6/12 anos. S10 permanece intacta; nenhum CSV S11.
[Resultados](../reports/competition/round15/RESULTS.md).

Rodada 14 sem promoção: atributos de transporte/convergência derivados dos
dados oficiais não melhoraram o RMSE total em nenhuma das quatro candidatas.
S10 intacta; nenhum CSV S11. [Resultados](../reports/competition/round14/RESULTS.md).

Rodada 13 encerrada sem promoção: melhor kernel tropical ganhou 0,082%, mas
melhorou apenas 4/6 blocos e 7/12 anos. Pesos S10 preservados durante a comparação.
Nenhum CSV S11 ou upload. [Resultados](../reports/competition/round13/RESULTS.md).

Rodada 12 encerrada sem promoção: melhor correção residual ganhou 0,154% no
desenvolvimento, abaixo do mínimo de 0,3%. S10 permanece intacta; nenhum CSV
S11 gerado. [Resultados](../reports/competition/round12/RESULTS.md).

## S10 aceita — público 1,71895

Score informado pelo usuário. Melhora de 0,01062 sobre S09; nova referência
pública. Classificação atual não reconfirmada, privado desconhecido.

Rodada 11 aprovada nos critérios históricos: S09 combinada com PLS32 tropical,
usando PCA64 regional de campos amostrados a 1° e PCA64 continental da S09.
Peso tropical de 25%, transição de 15°S a 10°S e S09 intacta ao sul. Sem NOAA.
Desenvolvimento: 1,780988 → 1,775343; confirmação reutilizada: 1,834766 → 1,830283.
CSV conferido; upload feito pelo usuário. Modelos e metadados de geração
preservados; nenhum novo treino iniciado com o retorno. [S10](../submissions/submission_10.csv),
[protocolo](../experiments/ROUND11.md) e [resultados](../reports/competition/round11/RESULTS.md).

Rodada 10 encerrada sem promoção: o melhor corretor PLS residual ganhou
0,207% no desenvolvimento, abaixo do mínimo de 0,3% fixado previamente.
S09 permaneceu inalterada; nenhum CSV foi gerado naquela rodada.
[Resultados da rodada 10](../reports/competition/round10/RESULTS.md).

## Histórico — S09 aceita com 1,72957

Resultado informado pelo usuário: novo melhor score público, 0,01548 abaixo
de S06 e 0,00593 abaixo de S07. Classificação atual não reconfirmada; privado
desconhecido. Modelos e metadados originais de geração permanecem preservados.

Combinação de 75% da S06 com 25% de PLS16 treinada apenas nos arquivos oficiais.
PCA64 da atmosfera atual e média de três meses, interações sazonais, seleção
supervisionada PLS16 usando 32 EOFs de chuva do treino e regressão ridge 0,3
para toda a grade. Treino final 1981–2022, climatologia de 60 anos; nenhuma informação externa.
O corretor por árvores também foi testado, mas não compõe a candidata selecionada.
[Protocolo](../experiments/ROUND9.md), [resultados](../reports/competition/round9/RESULTS.md)
e [CSV](../submissions/submission_09.csv). O usuário fez o upload e informou
o ganho público. S09 passa a ser a referência da linha somente oficial.

## Histórico — referência anterior S06

Por decisão do usuário após S08, a nova linha usa exclusivamente os arquivos
da organização. **S06, público 1,74505**, foi a referência anterior compatível.
S07/S08 usam NOAA e ficam preservadas apenas como histórico, sem compor
as novas previsões ou seus alvos de correção. [Protocolo vigente](../experiments/PROTOCOL.md).

## Histórico — S07, melhor score público registrado

Resultado mais recente confirmado: **S07, público 1,73550**, segundo lugar
informado pelo usuário; líder 1,72921. Diferença: 0,00629.
S07 mantém S06 e substitui o componente de modos regionais por modos
atmosféricos com temperaturas mensais do Pacífico da NOAA, ridge 0,3.
Os dados oceânicos têm defasagem de dois meses para o alvo. Pesos regionais
de mistura são preservados. RMSE histórico: 1,768074, melhor nos oito anos.
Fonte e limitação de revisão histórica: [protocolo S07](../experiments/ROUND7.md).

## Histórico — S06 e referências anteriores

Resultado mais recente confirmado: **S06, público 1,74505**. Regressão local
sazonal com estado atual e média atmosférica de três meses, ridge 0,3,
substituindo integralmente esse componente de S04 e preservando seus pesos.
RMSE histórico: 1,772788. [Protocolo S06](../experiments/ROUND6.md).
As seções abaixo preservam as referências anteriores.

Atualização: melhor score público confirmado é **S05, 1,74613**, segundo
lugar informado pelo usuário (líder: 1,72921). S04 permanece referência
histórica conservadora. A candidata S06 passou pelo critério local contra
ambas, mas ainda não tem resultado público. Veja [rodada 6](../experiments/ROUND6.md).
Os detalhes abaixo preservam a referência S04 e sua composição anterior.

Arquivo atual: `submissions/submission_04.csv`. Público **1,74906**, primeiro
lugar informado pelo usuário em 15/09/2026, sem verificação independente.
S04 combina S02, modos regionais com estado atual e média de três meses
(ridge 0,3), e regressão local sazonal. Os pesos variam por estação e faixa de
latitude. Protocolo e reprodução: [rodada 4](../experiments/ROUND4.md).
Pesos exatos: [calibração](../reports/competition/round4/calibration.json).
RMSE retrospectivo de desenvolvimento: 1,775701; não é teste independente.

## Referência anterior preservada — S03

Arquivo: `submissions/submission_03.csv`. Modelo: `joint25_modes_seasonal`.
Score público informado: **1,76467**. RMSE local de desenvolvimento: **1,779464**.

## Composição exata

```text
S03 = 0,50 × S02 + 0,25 × modos regionais + 0,25 × ridge sazonal
S02 = 0,50 × árvores de contexto + 0,25 × árvores locais
    + 0,125 × ridge local anual + 0,125 × climatologia
```

Expandindo a S03:

| Componente | Peso final |
| --- | ---: |
| Árvores com contexto espacial/temporal, 300 iterações | 25% |
| Árvores locais, 150 iterações | 12,5% |
| Ridge local anual, penalidade 0,1 | 6,25% |
| Climatologia de 60 anos | 6,25% |
| Modos regionais, penalidade 0,3 | 25% |
| Ridge sazonal, penalidade 0,3 | 25% |

As previsões de cada modelo são limitadas inferiormente a zero antes das
combinações. Não há limite superior artificial.

## Dados e corte temporal

Nove entradas atmosféricas: t2, cloud_cover, shum_850, surface_pressure, u_850,
v_850, temperature_850, rel_hum_850 e geopotential_850.

- Regressões e árvores: entradas desde janeiro/1981 até novembro/2022, alvos
  correspondentes de fevereiro/1981 até dezembro/2022, 503 pares mensais finais.
- Climatologia final: 1963–2022, uma média por ponto e mês do calendário.
- Previsões finais: janeiro/2023 a dezembro/2024, usando atmosfera observada até
  o mês anterior a cada alvo.
- Nenhuma precipitação observada de 2023/2024 foi usada como entrada ou alvo de treino.

## Componentes

### Árvores locais e de contexto

HistGradientBoostingRegressor: taxa 0,05; 15 folhas; mínimo de 100 amostras por
folha; L2 = 10; perda quadrática; early stopping desabilitado; semente 20260914.
Amostragem uniforme sem reposição de 768 pontos por mês no treino. Avaliação e
inferência usam toda a grade.

Entradas locais: latitude, longitude, seno/cosseno do mês-alvo, climatologia e
nove variáveis brutas e como anomalias mensais, totalizando 23 atributos.
Contexto adiciona média de três meses, diferença entre os dois últimos meses,
médias espaciais de seis variáveis em janelas 9 × 9 e 25 × 25 e q×u/q×v, chegando
a 55 atributos. O treinamento de contexto usa a sequência de 150 e 300 iterações
com warm start, igualmente na validação e no ajuste final.

### Ridge local anual

Nove coeficientes por ponto, compartilhados entre as estações. Anomalias mensais
padronizadas com estatísticas só do treino; intercepto não penalizado e
penalidade 0,1 adicionada a X'X/n.

### Modos regionais

Cada campo é filtrado espacialmente em 9 × 9 células e amostrado com passo 8.
O filtro não mistura meses. Médias mensais e escalas são ajustadas apenas nas
entradas de treino. PCA com 16 componentes, solver randomized e semente 20260914.

Os componentes padronizados, suas interações com seno/cosseno do mês-alvo e um
intercepto formam 51 entradas para ridge que prevê o campo de anomalias de chuva.
Penalidade 0,3 sobre X'X/n, sem penalizar o intercepto.

### Ridge sazonal

Para cada mês-alvo e ponto, a regressão é ajustada usando esse mês do calendário
e os dois vizinhos de cada lado. A janela é circular: dezembro e janeiro são
vizinhos. Usa nove anomalias atmosféricas, padronizadas dentro da janela, e
penalidade 0,3 sobre X'X/n.

## Artefatos e reprodução

- Código principal: [round3.py](../src/round3.py), com dependências das rodadas anteriores.
- Previsões finais: `data/processed/round3/submission_03_predictions.nc`.
- Modelo de modos: `data/processed/round3/final_modes.joblib`.
- Modelos de árvores da S02: `data/processed/round2/final_*.joblib`.
- As regressões locais podem ser reconstruídas pelos scripts a partir do cache;
  não há um único binário que dispense todas as etapas anteriores.
- Metadados e hash do CSV: [submission_03.json](../submissions/submission_03.json).
- [Sequência completa de reprodução](REPRODUCAO.md).

O hash registrado no momento da geração identifica o script daquela execução.
O registro consolidado de submissões verifica os hashes dos CSVs. Metadados
originais com `uploaded: false` descrevem a geração local; o estado posterior de
aceitação e score é mantido no registro de observações públicas.
