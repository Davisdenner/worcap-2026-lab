# Rodada 21 — hipótese 2: especialistas regionais não lineares

Protocolo fixado antes de medir qualquer candidata. Somente dados oficiais,
sem exportação de CSV ou envio. Referência S12, reproduzida historicamente.
O diagnóstico da S12 em `reports/competition/s12_diagnostic` informa onde
ocorre erro, mas não escolhe pesos ou limites por resultado de candidata.

## Arquitetura e separação temporal

Reusar os 23 atributos e amostras residuais S11 fora do treino da rodada 17:
2.048 células aleatórias por mês por bloco histórico completo. Reusar como
âncora o corretor global HGB15 causal da S12. Para cada corte, treinar três
HGB independentes com amostras dos blocos anteriores completos, sem chuva do
bloco avaliado. O alvo é precipitação observada menos S11 histórica OOF.
Cada especialista mantém latitude, longitude, climatologia calculada apenas
com o treino e as nove variáveis atmosféricas como atributos. Não usar
classes baseadas na chuva observada do mês alvo em inferência.

Núcleos: sul <−15°, centro [−15°,0°), norte >=0°. Treinar com halo de 2,5°
em cada borda: sul lat<−12,5°; centro −17,5°<=lat<2,5°; norte lat>=−2,5°.
Inferência: duas rampas lineares de 5° centradas em −15° e 0°. Fora delas,
o especialista correspondente tem peso 1. As três parcelas são não negativas
e somam 1 em cada ponto; verificar bordas e continuidade em testes.
Combinar `delta=(1−beta)*delta_global+beta*sum(peso_regiao*delta_regiao)`;
saída `max(S11+0,25*delta,0)`. Beta 0 recupera S12. Compartilhar o modelo
global em todas as regiões evita cortes duros e mantém a âncora existente.

## Candidatas predefinidas

HGB squared_error, learning_rate 0,03, 200 iterações, 128 bins,
min_samples_leaf 300, L2 100, early_stopping=False,
semente 20260918, uma thread. Dois números de folhas para os três
especialistas: 7 e 15. Para cada um, beta=0,25 ou 0,50: quatro candidatas.
Nenhum limite geográfico, folha ou peso será escolhido por bloco. Latitudes
e climatologia provêm somente dos arquivos oficiais.

## Seleção

Seis blocos de 24 meses: 2009, 2011, 2013, 2015, 2017, 2019. RMSE de todos
os pontos e meses contra S12, incluindo oceano. Exigir ganho >=0,3%, segundo
ano melhor, >=5/6 blocos, >=9/12 anos, >=80/144 meses e pior perda anual
<=0,5%. Escolher a menor RMSE que passe todos. Se nenhuma passar, parar:
nenhuma confirmação, previsão final, CSV ou envio. Se passar, confirmar em
2021–22, período já reutilizado: ganho >=0,1% e ambos os anos melhores.
Reportar reutilização de períodos e ausência de teste independente.
