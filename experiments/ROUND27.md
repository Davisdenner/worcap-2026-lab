# Rodada 27 — seleção de especialista S12 versus análogos

Protocolo registrado antes dos cálculos novos. Referência S12 e previsor puro
`h4` de análogos da rodada 25, ambos OOF e congelados. Resíduo positivo
significa observado maior que previsão. Nenhuma S14, CSV, treino final,
confirmação 2021–2022 ou submissão nesta rodada. Não usar alvos 2023/2024.

## Escopo e paradas

Oracle e diagnóstico de vantagem em seis blocos 2009–2020 na grade inteira,
com tabelas para latitude, setor/longitude, estação, bloco e ano. O norte
0–15°N (61 × 261 células) é a área da hipótese de risco Q90 da rodada 26.
As previsões OOF de risco Q90 existem apenas para 2011–2020. Portanto os
decis de risco e qualquer meta-modelo usam cinco blocos, com treino
expansivo em blocos anteriores; 2009–2010 entra como treino do primeiro
corte e apenas em diagnósticos sem risco previsto.

O oracle escolhe a previsão com menor erro absoluto por ponto/mês, com
empate para S12. É diagnóstico com acesso ao alvo e um upper bound empírico
de *escolha dura entre os dois mapas*, não uma regra operacional nem limite
de todas as combinações possíveis. Definir ganho relevante antes de medir:
RMSE oracle pelo menos 1,0% menor no norte **e** pelo menos 0,3% menor na
grade inteira, ambos sobre S12 nos seis blocos. Se qualquer condição falhar,
encerrar após oracle, vantagem e auditoria, sem classificador nem gating.

## Métricas diagnósticas

Perda L = (observado − previsão)² e vantagem D = L_S12 − L_Analog.
D positivo significa análogo melhor. Calcular SSE, RMSE, ganho relativo,
fração de vitórias do análogo, média/mediana e caudas de D por bloco,
ano, estação, faixas latitudinais de 15°, três setores no norte,
climatologia, intensidade S12, anomalia S12, dispersão/consenso dos
componentes, PCs continentais/tropicais e variáveis meteorológicas locais.
Para atributos contínuos, usar quintis definidos no histórico anterior
ao corte quando houver análise OOF, ou faixas físicas predefinidas quando
estritamente descritivo. Não usar chuva observada como atributo de decisão.

Para cada bloco 2011–2020, formar decis de risco usando somente a previsão
OOF Q90 da rodada 26; o ranking é calculado dentro do próprio bloco sem
consultar rótulos. Registrar RMSE S12, RMSE análogo, vitória do análogo,
RMSE oracle, ganho oracle, D médio e fração do SSE S12 em cada decil.
Testar tendência baixo→alto risco por bloco, sem selecionar um corte depois.
Comparar P(Q90) com D, mas nunca confundir a discriminação de erro extremo
com discriminação do modelo vencedor.

## Meta-modelos somente se o oracle passar a parada

Alvo binário: `Analog` vence por menor perda quadrática; empate pertence a
S12. Features disponíveis em inferência: 105 atributos fixos da rodada 26
(local, PCs, componentes, clima, posição, mês) mais previsão do análogo,
diferença análogo−S12 e |diferença|. O risco Q90 OOF não entra no
meta-modelo, pois não há versão anterior causal para o bloco 2009–2010;
ele permanece estratificador diagnóstico. Transformações locais e PCs são
reajustados com dados anteriores ao corte, e os mesmos parâmetros do corte
transformam treino e validação. Amostrar as mesmas 512 células norte por
mês histórico da rodada 26; validar todas as 15.921 células e 24 meses.

Modelos fixos, sem busca: regressão logística L2 C=0,3 com padronização de
treino; ridge probabilístico (alvo 0/1, penalidade 0,3 da covariância média,
intercepto livre, saída limitada [0,01;0,99]); HGB pequeno com 7 folhas,
100 iterações, taxa 0,03, mínimo 500 amostras/folha, L2=100,
128 bins, seed 20260927. Checagem simples adicional: logística apenas
com latitude, longitude, mês, climatologia, S12 e diferença Analog−S12.
Treinar em blocos anteriores; avaliar AUC, Brier, log loss, calibração em
dez faixas de probabilidade, prevalência, lift do decil superior e inferior,
por bloco e ano. Baselines: prior de vitória aprendido no treino e
intensidade/climatologia como ordenadores sem ajuste (AUC apenas).

## Soft gating somente se houver sinal temporal

Prosseguir para gating se ao menos um modelo tiver AUC >0,53, Brier menor
que o prior de treino em pelo menos 4/5 blocos e separação de taxa de
vitória entre decis extremos em 4/5 blocos. Não escolher arquitetura nem
parâmetro com base no bloco avaliado. Se nenhuma passar, classe B ou D
conforme o oracle e encerrar.

Para modelos elegíveis, usar `g = gmax × P(Analog melhor | X)` com
`gmax ∈ {0,10; 0,20; 0,30}`. Essa modulação preserva a ordem das
probabilidades e limita o peso; não há limiar duro. Aplicar gating somente
no norte; fora do norte manter S12. Avaliar os cinco blocos 2011–2020.
Comparar na mesma janela com S12, mistura fixa global 10% da rodada 25,
mistura fixa 10% somente no norte, e oracle. Reportar RMSE global e norte,
ganho relativo, blocos/anos/meses positivos, setor, e RMS da alteração
em mm/dia. Reportar cada combinação predefinida, sem seleção posterior
para gerar candidata.

## Interpretação

**A — espaço e vencedor previsível:** oracle relevante, um gating melhora
S12 em >=0,3% global nos cinco blocos, supera mistura fixa 10% global,
e melhora >=4/5 blocos, >=7/10 anos e >=67/120 meses. É apenas evidência
exploratória; não há promoção.

**B — espaço, vencedor não previsível:** oracle relevante, mas sem modelo
que passe o gate preditivo acima ou sem ganho OOF de qualquer soft gating.

**C — pouco espaço:** oracle falha o limiar de relevância predefinido.

**D — sinal aparente instável:** oracle relevante e há ganho em algumas
combinações/blocos, mas nenhum satisfaz A; declarar exatamente onde falha.

Os blocos e escolhas S12/análogo já foram reutilizados em decisões
anteriores; não calcular p-valores ingênuos por pixel nem interpretar o
melhor de várias linhas como validação independente. Auditoria separada
refará métricas de arquivos congelados e verificará hashes, cortes, rótulos
e ausência de alvos futuros.
