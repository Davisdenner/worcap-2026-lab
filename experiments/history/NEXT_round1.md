# Próxima rodada

## O que foi executado

- Auditoria integral dos arquivos oficiais e cache local.
- Seis climatologias, três penalidades ridge, três combinações ridge/climatologia.
- Uma configuração de árvores e uma combinação com o candidato linear.
- Dois blocos de desenvolvimento, sempre com pontuação na grade completa.
- Cinco testes do protocolo temporal e da métrica.

Consultar `reports/competition/RESULTS.md` e os arquivos JSON/CSV correspondentes.
As previsões por modelo/bloco estão em `data/processed/validation`.

## Decisão inicial

O melhor RMSE agrupado desta rodada veio de 50% árvores + 25% ridge com
penalidade 0,1 + 25% climatologia de 60 anos. É um candidato de desenvolvimento.
A piora em 2018 impede concluir que o ganho será estável no privado.

## Hipóteses em ordem

1. Diagnosticar os meses de maior piora em `reports/competition/diagnostics.json`.
   Separar contribuição ao erro por regiões da grade sem mudar a métrica global.
2. Avaliar os candidatos já fixados em blocos de desenvolvimento anteriores,
   por exemplo 2013–2014 e 2015–2016, preservando 2021–2022.
3. Acrescentar contexto regional e padrões espaciais das variáveis atmosféricas,
   ajustando todas as transformações somente antes de cada bloco.
4. Testar sazonalidade nas correções e histórico atmosférico de 2–3 meses;
   esses históricos são disponíveis no teste por concatenação com o treino.
5. Investigar disponibilidade de previsões externas históricas com prazo de
   pesquisa limitado e comprovação de disponibilidade no instante da previsão.

Não aumentar indiscriminadamente a busca de hiperparâmetros nos mesmos 48 meses.
O exportador já constrói IDs conforme o formato confirmado pelo usuário e as
coordenadas do teste. Comparar a ordem com o `sample_submission.csv` se ele for
disponibilizado. Nenhum arquivo foi enviado ao Kaggle e nenhuma previsão foi
avaliada em 2021–2022.
