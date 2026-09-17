# Rodada 20 — hipótese 1: árvores locais com estado continental/tropical

Pedido de 17/09/2026: testar a hipótese 1. Pesquisa apenas, sem exportar S13 ou
enviar ao Kaggle. Referência imutável S12, público informado 1,71456. Terceiro
lugar e líder 1,63223 são relatos do usuário, não objetivos numéricos do treino.
Somente dados oficiais; nenhuma informação de S07/S08 ou alvos ocultos.

## Aprendizado direto

Aprender precipitação de M+1 menos climatologia causal de 60 anos, com pares
de entrada desde janeiro de 1981 e alvos estritamente anteriores a cada corte.
Não aprender somente resíduos das previsões históricas S12. Somar climatologia
e limitar a saída a zero. Manter grade e métrica uniformes, inclusive oceano.

Controle local: 55 atributos de `round2.Features.matrix(context=True)`, incluindo
estado atmosférico, anomalias, médias/variações de três meses e vizinhança espacial.
Contexto global adicional: primeiros 16 escores de cada PCA64 continental e
tropical já ajustada antes do corte, normalizados pelas escalas do respectivo
treino. Concatenar estado atual e média causal de três meses: 64 atributos
adicionais, total 119. Não usar escores PLS supervisionados como atributos dos
mesmos alvos usados para ajustar suas representações.

Os PCA continentais são extraídos dos artefatos PLS existentes, mas somente
PCA/médias/escalas atmosféricas são usados. Nenhum coeficiente supervisionado
PLS, previsão S12 ou precipitação futura entra nos atributos. Verificar hashes
e médias/escalas por corte contra os índices temporais de treino.

## Quatro modelos, oito misturas predefinidas

| Nome | Contexto | Folhas | Pontos/mês | Mínimo por folha | L2 |
| --- | --- | ---: | ---: | ---: | ---: |
| local15 | 55 atributos locais | 15 | 768 | 100 | 10 |
| global15 | local + 64 atributos globais | 15 | 768 | 100 | 10 |
| global31 | local + global | 31 | 768 | 100 | 10 |
| global31_dense | local + global | 31 | 1536 | 200 | 20 |

HistGradientBoostingRegressor, perda quadrática, taxa 0,05, 300 iterações,
128 bins, early_stopping=False, warm_start=False, semente 20260914, uma thread.
Na variante densa, mínimo por folha e L2 dobrados para manter as escalas relativas
de regularização. Não buscar taxas, iterações, PCs ou frações adicionais.

Sortear 1.536 pontos sem reposição por mês com gerador de semente 20260914;
os primeiros 768 formam a amostra menor. Todos os modelos de um corte usam
amostragem aninhada. Este é um controle novo e não uma reprodução bit a bit
das árvores antigas (128 bins e desenho amostral explicitados).

Registrar desempenho individual e misturas `S12 + a × (modelo − S12)`,
`a` em 0,10 e 0,25. Oito candidatas avaliadas, incluindo misturas do controle.
O controle permite atribuir eventual ganho: se ele vencer, não afirmar que
o contexto global foi responsável. Comparar global15 versus local15, global31
versus global15 e dense versus global31 com todos os demais fatores fixos.

## Critérios e limites

Seis blocos de desenvolvimento 2009–2020, toda a grade. Exigir contra S12:
ganho >=0,3%, segundos anos melhores, >=5/6 blocos, >=9/12 anos, >=80/144 meses,
pior perda anual <=0,5%. Selecionar o menor RMSE elegível entre as oito misturas.
Registrar se cada mudança superou seu controle, sem selecionar parâmetros por ano.

Se nenhuma passar, encerrar sem confirmação ou previsão final. Se alguma passar,
confirmar somente a selecionada em 2021–2022 já reutilizado: ganho >=0,1% e
ambos os anos melhores. Sem substituir candidata ou ajustar após confirmação.
Nesta rodada não gerar CSV nem treinar para 2023/2024 automaticamente. Uma futura
exportação requer pedido e o limite de mudança <=2× RMS histórico por ano de teste.

Os períodos e arquiteturas já foram usados; resultados não são independentes nem
garantem alcançar o líder. Preservar S10–S12, seus metadados e códigos congelados.

## Execução

```powershell
.\.venv\Scripts\python.exe -m src.round20 evaluate
.\.venv\Scripts\python.exe -m src.round20 select
.\.venv\Scripts\python.exe -m src.round20 confirm
.\.venv\Scripts\python.exe -m src.round20 summarize
```

A confirmação é bloqueada sem aprovação. Dados/modelos em `data/processed/round20`,
relatórios em `reports/competition/round20`. Checkpoints por modelo e por bloco.
