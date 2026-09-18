# Rodada 28 — magnitude da vantagem S12 × Analog

Protocolo fixado antes das novas métricas. Referência S12 e Analog H4 puro
OOF congelados. Ganho pontual `G=(y−S12)^2−(y−Analog)^2`: positivo favorece
Analog; benefício pontual do oracle duro é `G+=max(G,0)`. O oracle escolhe
com conhecimento do alvo e não é operacional. Não gerar S14, CSV, treino
final, confirmação 2021–2022 ou submissão. Nenhum alvo 2023/2024.

## Escopo e decomposição anterior a novos ajustes

Seis blocos 2009–2020 para decomposição e comparação de especialistas na
grade inteira (301×261) e 0–15°N. Cinco cortes 2011–2020 para aprendizado
OOF, sempre com treino expansivo em blocos anteriores e validação integral
do norte. O bloco 2009–2010 treina o primeiro meta-modelo e não recebe
previsão meta OOF fabricada.

Para cada área/bloco/ano/faixa de latitude 15°/setor norte/estação, ordenar
todos os pontos por `|G|` e medir a fração de `sum(G+)` nos top
{1, 2,5, 5, 10, 20, 50}% **dos pontos da área**. Separadamente, ordenar
somente as vitórias `G>0` por G e medir a fração de `sum(G+)` nos top
{1, 2,5, 5, 10, 20, 50}% **das vitórias positivas**. Registrar contagem,
SSE e caudas de G. O primeiro ranking mistura grandes perdas e ganhos;
essa diferença deve ser explícita. Calcular a contribuição em unidades de
SSE e o ganho de RMSE do oracle, sem tratar células como amostras temporais
independentes.

## Features, alvos e modelos fixos

Usar as 105 features causais da rodada 26 mais Analog, Analog−S12 e
|Analog−S12|, como na rodada 27. Climatologia, campos locais e PCs usam o
corte em avaliação; os mesmos parâmetros pré-corte transformam treino e
validação. Amostra de 512 células norte/mês histórico com as mesmas seeds
da rodada 26; avaliar todas as 15.921 células/mês. Risco Q90 predito não
entra no modelo porque não existe valor OOF anterior para 2009–2010.

Comparar diretamente o Z da rodada 27 (probabilidades logistic_base e
HGB) com previsores de magnitude G. Ridge com penalidade 0,3 da covariância
média, intercepto livre, em quatro alvos fixos: G bruto; G limitado a
`±Q99(|G|)` calculado apenas no treino amostrado; `sign(G)log1p(|G|)`;
`log1p(G+)`. Para relatar R² em G original, inverter log com expm1 e limitar
a magnitude ao maior |G| do treino. HGB regressor conservador para G bruto
e G limitado: 7 folhas, 100 iterações, taxa 0,03, mínimo 500
amostras/folha, L2=100, 128 bins, seed 20260928. As transformações
limitada/log tratam a cauda pesada sem introduzir uma busca de estimador
robusto/quantil depois dos resultados. Nenhum ajuste de hiperparâmetros.

Em cada bloco e ano, medir R² bruto contra média G do treino anterior,
Pearson, Spearman, média G e fração de vitórias nos top previstos
{1, 2,5, 5, 10, 20}%, concentração de G+ e RMSE S12/Analog nesses grupos.
Decis de score previsto também registram G médio, vitórias, RMSEs e
ganho possível do oracle. Comparar as mesmas métricas de ranking com Z
logistic_base e Z HGB da rodada 27. Quintis de clima, previsão,
diferença Analog−S12, componentes, PCs, variáveis locais e contexto são
definidos no treino anterior por corte, para caracterizar G e strong wins.

Strong win: `G > Q90(G | G>0)` em **todos os pontos norte dos blocos
anteriores**; limiar reajustado causalmente em cada corte. Modelos fixos:
logística L2 C=0,3 com features base da rodada 27; HGB classificador com
a configuração conservadora acima. AUC, AP, lift do decil superior, Brier,
calibração em dez faixas e estabilidade por bloco/ano, sempre frente ao
prior de treino. A vitória comum Z continua como comparação explícita.

## Parada antes de políticas

G possui sinal operacional de ranking se ao menos um previsor contínuo
produzir G médio **positivo** no top 10% previsto em >=4/5 blocos e
>=7/10 anos, e concentrar G+ no top 10% acima de 15% em >=4/5 blocos.
Strong win possui sinal se algum classificador alcançar AUC>=0,60,
lift>=1,5 e ganho de Brier>0 em >=4/5 blocos. R² pequeno não provoca
parada por si. Se nenhum dos dois critérios passar, encerrar antes de
top-k blending e expected-gain gating; ainda completar o contraste
somente diagnóstico com componentes congelados e a auditoria.

## Políticas apenas após a parada

Se ranking contínuo passar, testar somente os scores que passarem o
critério em top-k blending no norte, com k em {1%,2,5%,5%,10%,20%}
por bloco (ranking sem rótulos) e alpha em {0,1;0,2;0,3}. Se apenas
strong win passar, usar somente o score strong win. Fora do norte manter
S12. Registrar todas as combinações predefinidas, sem escolher candidato.

Expected-gain gating apenas para previsor **em escala G bruta** que passe
o critério de ranking: `g=0,3×max(Ghat,0)/(max(Ghat,0)+m)`, com m igual
à mediana dos G positivos no treino amostrado; por construção 0<=g<=0,3.
Comparar com S12, fixed10 global e logistic_base_0.3 da rodada 27 na
mesma janela 2011–2020, e oracle descritivo. Métricas: RMSE global/norte,
ganho, blocos/anos/meses positivos, setor e RMS da mudança. AUC/AP
isoladas nunca aprovam uma política.

## Outros especialistas congelados

Sem treinar especialista, comparar oracle(S12, Analog) com
oracle(S12, cada um dos cinco componentes S12) e
oracle(S12, Analog, componente), nos seis blocos, global/norte. Registrar
também RMSE puro do componente: oracle de um previsor ruim pode ser alto
por dispersão e não prova utilidade operacional. Os componentes são
correlacionados e a extensão tropical herda modelos anteriores.

## Decisão predefinida

**A:** ranking contínuo estável e política baseada nele ganha >=0,3%
global, supera logistic_base_0.3 e fixed10 da rodada 27, com >=4/5
blocos, >=7/10 anos e >=67/120 meses positivos.

**B:** sem A; somente strong wins passam seu critério temporal, enquanto
ranking contínuo não passa. Política não é promovida.

**C:** nenhum sinal de magnitude ou strong win passa os critérios e a
complementaridade oracle não é identificável operacionalmente com estas
features.

**D:** se outro componente tiver oracle pareado global pelo menos 1 ponto
percentual acima do Analog **e** RMSE puro no máximo 5% pior que Analog,
ou se seu oracle triplo adicionar pelo menos 1 ponto percentual sobre
oracle(S12,Analog). Relatar D como diagnóstico de especialista, mesmo
se houver sinal de magnitude, e nunca promover com base em oracle.

Se houver ranking contínuo mas política sem ganho material/estável e
nenhum componente acionar D, usar C com nota explícita de sinal
insuficiente para RMSE; não inventar quinta classe. Blocos históricos
foram reutilizados para múltiplas decisões: resultados exploratórios,
sem p-valores por pixel. Auditoria independente recalcula hashes,
limiares, rankings e perdas de arquivos OOF.
