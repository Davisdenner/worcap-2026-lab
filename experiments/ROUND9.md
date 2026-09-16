# Rodada 9 — somente dados oficiais, correção temporal e PLS

Protocolo definido antes de executar os novos experimentos. Objetivo aspiracional:
RMSE público 1,70, sem promessa ou ajuste de pesos pelo leaderboard.
Referência compatível com a restrição do usuário: S06, público 1,74505.

## Dados e referência

Somente data/raw e caches rastreáveis desses arquivos. Proibidos dados NOAA,
pesos externos, previsões/resíduos S07/S08 e arquivos preparatórios em data/interim.
Auditar igualdade dos caches oficiais com os NetCDF e reconstrução do cache
atmosférico reduzido antes de experimentar. Precipitação-alvo limitada a 2022.
Não usar chuva observada dentro dos blocos previstos como atributo.

As previsões retrospectivas antigas de S06 usavam pesos que excluíam o bloco
avaliado, mas podiam usar outros blocos posteriores. Não servem diretamente
para a nova correção temporal. Reconstruir os três componentes S02, modos
atmosféricos mean3/ridge0,3 e regressão local memory/ridge0,3.
Usar o prior fixo [0,5;0,25;0,25] antes de haver calibração anterior a 2013.
Depois, estimar pesos com a regra original S04 e somente blocos 2013–2020
inteiramente anteriores ao alvo. A calibração mantém o componente local9
original; a previsão o substitui por local18, como S06. No ajuste final, os
pesos devem reproduzir os da S06. Nomear essa referência histórica S06-forward;
seus scores não são diretamente os mesmos da antiga validação retrospectiva.

## Blocos e candidatos fixados

- 2005–2006 e 2007–2008: sementes de previsões fora do treino para o corretor.
- 2009–2010, 2011–2012, 2013–2014, 2015–2016, 2017–2018, 2019–2020:
  seis blocos de desenvolvimento, 144 meses, grade completa.
- 2021–2022: confirmação da única candidata selecionada; já consumido na S08,
  portanto não é holdout inédito. Não ajustar a candidata após essa checagem.
- Treino dos modelos-base desde 1981, climatologia de 60 anos, corte antes de
  cada bloco. Correção treinada só em previsões fora do treino de blocos anteriores.

As escolhas de arquitetura anteriores foram influenciadas por 2013–2022.
A nova execução impede vazamento de parâmetros e rótulos entre cortes, mas
não apaga esse histórico de seleção. 2009–2012 amplia a diversidade temporal;
não alegar teste independente de toda a pesquisa.

1. Correção HistGradientBoosting: 150 iterações, taxa0,05, 7 ou 15 folhas,
   mínimo200 amostras/folha, L2=20, sem early stopping aleatório. Mistura
   de 25% ou 50% da correção. Quatro candidatos. 2048 pontos uniformes/mês
   no treino do corretor; inferência e métrica em toda a grade. Entradas:
   contexto55 oficial, média6 de anomalias, médias atmosféricas em três faixas
   fixas de latitude, componentes S06, sua previsão e diferenças entre eles.
2. PLS: PCA atmosférica64, estado atual+mean3 e interações sazonais; alvos
   reduzidos a32 EOFs de chuva aprendidos só no treino. PLS8 ou16 componentes,
   seguido de ridge0,3 dos escores padronizados para anomalias de toda a grade.
   Misturas25% ou50% do modelo PLS com S06-forward. Quatro candidatos.

Total oito candidatos, sem busca adicional automática ou combinações escolhidas
depois de ver scores. Derivadas/médias usam somente meses anteriores ou iguais
à origem. Toda estatística, PCA e PLS é ajustada dentro do corte de treino.

## Critérios antes de gerar uma submissão

Escolher menor RMSE entre candidatos com redução relativa agrupada >=0,3%,
melhora nos segundos anos, >=5/6 blocos, >=9/12 anos, >=55% dos144 meses,
e nenhuma piora anual relativa superior a0,5% contra S06-forward.
Na confirmação2021–2022, exigir melhora em ambos os anos e redução agrupada
>=0,1%. Se falhar, encerrar sem substituir por outra candidata nessa checagem.
Na previsão2023, RMS da mudança contra S06 não pode superar duas vezes o
RMS histórico agrupado da mudança. Esse limite é um alarme, não uma garantia.

Somente após aprovação: criar S09 distinta, validar IDs/ordem oficiais,
datas, finitude, não negatividade e hash. Nunca sobrescrever S01–S08.
Nenhum upload automático. Se não houver candidata aprovada, preservar os envios.

## Reprodução

```powershell
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
.venv/Scripts/python.exe -m src.round9 audit
.venv/Scripts/python.exe -m src.round9 evaluate
.venv/Scripts/python.exe -m src.round9 select
.venv/Scripts/python.exe -m src.round9 confirm
.venv/Scripts/python.exe -m src.round9 final
```

Os comandos confirm/final recusam candidatas não aprovadas. Modelos e caches
novos ficam em data/processed/round9; resultados em reports/competition/round9.
