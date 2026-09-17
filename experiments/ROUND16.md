# Rodada 16 — calibração espacial e sazonal dos resíduos S11

Definida após o diagnóstico S11 de 2009–2020 e antes de pontuar as candidatas
desta rodada. Hipótese: parte do erro é um viés espacial persistente que pode
ser corrigido usando previsões históricas fora do treino. O diagnóstico mostrou
47,38% do erro quadrático entre 0 e 15°N e RMS de viés médio por ponto 0,23037
mm/dia. Isso motiva o teste, mas não estima seu ganho fora da amostra.

Referência única de seleção: S11 histórica, configuração joint1. S10 permanece
controle aprovado anterior; não substituir a referência durante a rodada.
Somente dados oficiais, sem NOAA, S07/S08, chuva oculta ou data/interim.

## Configurações congeladas

Aprender resíduos `observado − S11` em blocos completos anteriores ao corte.
Para os blocos iniciais: 2005 usa o prior S10, pois não há calibração anterior;
2007 usa os pesos conjuntos ajustados apenas na covariância de 2005, com λ=1.
De 2009 em diante, usar as previsões S11 joint1 previamente salvas e verificadas.
As escolhas retrospectivas de arquitetura continuam limitando a independência.

Dois estimadores de intercepto por ponto: média anual dos resíduos; média
sazonal em janela circular de cinco meses (mês-alvo ±2). No segundo caso,
a correção de janeiro combina somente resíduos de meses novembro a março
de anos inteiramente anteriores ao corte; não lê esses meses no bloco avaliado.

Suavizar espacialmente o campo de correção com filtro gaussiano de sigma 4 ou
12 células (1° ou 3°), `mode=nearest`, sem mistura temporal. Aplicar fração
0,5 ou 1,0. Total: 2 estimadores × 2 suavizações × 2 frações = **8 candidatas**.
As médias são estimadores de intercepto por mínimos quadrados; suavização
espacial e frações menores regularizam a correção. Não usar a intensidade da
chuva observada para escolher correções na inferência.

Previsão = máximo(S11 + fração × correção estimada, 0). Todos os componentes
S11, pesos e grades permanecem os originais. Não modificar configurações
após observar os resultados. Calibração final, se elegível, só até 2022.

## Seleção e confirmação

Desenvolvimento nos seis blocos 2009–2010 até 2019–2020. Treinar correções somente
com blocos completos anteriores (2005 em diante). Métrica uniforme em toda a grade.
Exigir conjuntamente: ganho RMSE >=0,3% contra S11; segundos anos melhores;
>=5/6 blocos, >=9/12 anos, >=80/144 meses melhores; pior perda anual <=0,5%.

Selecionar menor RMSE entre elegíveis. Se nenhuma passar, encerrar sem confirmar,
treinar a correção final ou exportar CSV. Confirmar somente a selecionada em
2021–2022, período já reutilizado: ganho >=0,1% e ambos os anos melhores.
Falha bloqueia a promoção; não escolher uma segunda candidata após a confirmação.

Se aprovada, conferir RMS da mudança em 2023 e 2024 separadamente, <=2× RMS
histórico. Salvar modelo e previsões internas para revisão. A exportação de uma
nova submissão e o upload dependem de pedido explícito do usuário. Esta rodada
foi autorizada para diagnosticar e testar melhorias; não consome envios.

## Reprodução

```powershell
.\.venv\Scripts\python.exe -m src.diagnose_s11
.\.venv\Scripts\python.exe -m src.round16 evaluate
.\.venv\Scripts\python.exe -m src.round16 select
.\.venv\Scripts\python.exe -m src.round16 confirm
.\.venv\Scripts\python.exe -m src.round16 prepare_final
.\.venv\Scripts\python.exe -m src.round16 summarize
```

Executar confirmação e preparação final somente após aprovação da etapa anterior.
O programa bloqueia essas etapas quando não há candidata elegível. Usa caches
oficiais já existentes e verifica as previsões de referência por reconstrução.
Modelos da rodada em `data/processed/round16`; relatórios em `reports/competition/round16`.
