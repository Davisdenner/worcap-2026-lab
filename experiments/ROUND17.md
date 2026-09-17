# Rodada 17 — correção não linear condicionada aos componentes S11

Protocolo definido antes de avaliar as candidatas. A rodada 16 foi encerrada
sem aprovação; seus corretores não entram nesta rodada. Referência fixa: S11.
Somente dados oficiais, com os mesmos critérios mínimos de 0,3% e estabilidade.

Hipótese: a confiabilidade relativa dos componentes varia com latitude,
longitude, estação, intensidade prevista, discordância entre componentes e
atmosfera observada. Um corretor não linear pode modelar parte dessas diferenças.
Não se presume ganho nem se usa o score do líder para ajustar parâmetros.

## Dados de treinamento e atributos

Treinar sobre resíduos `chuva observada − previsão S11 fora do treino`, apenas
em blocos completos que terminaram antes do bloco previsto. Blocos de dois anos
desde 2005; aquecimento 2005 com prior S10 e 2007 com calibração conjunta apenas
em 2005, conforme a rodada 16. De 2009 em diante, verificar as referências S11
reconstruídas contra as previsões joint1 salvas. Não usar resíduos da própria
amostra de treinamento dos modelos-base.

23 atributos: latitude, longitude, seno/cosseno do mês-alvo, climatologia causal
de 60 anos, previsão S11, desvios dos cinco componentes em relação à S11,
desvio-padrão e amplitude entre componentes, anomalia S11 menos climatologia,
e nove variáveis atmosféricas brutas oficiais do mês de origem. O quinto
componente é o tropical estendido da S11, sem extrapolar sua área disponível.
Nenhuma intensidade observada, alvo oculto, informação NOAA ou S07/S08 entra nos atributos.

Amostragem uniforme de 2.048 pontos sem reposição por mês, semente 20260918
somada ao ano do bloco para repetir exatamente cada conjunto. A avaliação usa
todos os pontos. A distribuição temporal dos exemplos históricos é uniforme.

## Quatro candidatas congeladas

HistGradientBoostingRegressor com perda quadrática, taxa 0,03, 200 iterações,
mínimo 300 amostras por folha, regularização L2 100, 128 bins, semente 20260918,
parada antecipada desativada. Duas complexidades: 7 ou 15 folhas. Duas frações
da correção: 0,25 ou 0,5. Total de quatro candidatas.

Previsão = máximo(S11 + fração × resíduo previsto, 0). Não usar correção da
rodada 16 nem alterar árvores-base ou pesos S11. Salvar modelos do corretor e
conferir previsões após recarregamento. Sem ampliar a busca após os resultados.

## Seleção

Seis blocos de desenvolvimento 2009–2010 até 2019–2020. RMSE uniforme sobre
toda a grade. Exigir ganho >=0,3%, agregado dos segundos anos melhor, >=5/6
blocos, >=9/12 anos, >=80/144 meses melhores e pior perda anual <=0,5%.
Selecionar o menor RMSE elegível. Se nenhuma passar, encerrar a rodada.

Confirmar apenas a selecionada em 2021–2022, já reutilizado: ganho >=0,1% e
ambos os anos melhores. Sem substituir candidata após falha na confirmação.
Se aprovada, treinar corretor final apenas com resíduos históricos até 2022 e
exigir RMS da mudança em 2023 e 2024, separadamente, <=2× RMS histórico.
Salvar previsão interna; CSV novo e upload exigem pedido explícito do usuário.

```powershell
.\.venv\Scripts\python.exe -m src.round17 evaluate
.\.venv\Scripts\python.exe -m src.round17 select
.\.venv\Scripts\python.exe -m src.round17 confirm
.\.venv\Scripts\python.exe -m src.round17 prepare_final
.\.venv\Scripts\python.exe -m src.round17 summarize
```

Etapas posteriores são bloqueadas se a anterior reprovar. Caches/modelos locais
em `data/processed/round17`; relatórios em `reports/competition/round17`.
Arquitetura, diagnóstico e períodos históricos foram reutilizados; não alegar
independência estatística ou garantia de liderança a partir deste desenvolvimento.
