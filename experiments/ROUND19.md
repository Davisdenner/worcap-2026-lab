# Rodada 19 — mais histórico para o corretor da S12

Referência fixa: S12 `meta15_a0.25`; S11 apenas como comparação auxiliar.
Protocolo registrado antes de gerar e avaliar novas candidatas. Somente dados
oficiais; nenhuma alteração em S10–S12, seus modelos, protocolos ou metadados.

## Hipótese e duas candidatas

Adicionar blocos 1997–1998, 1999–2000, 2001–2002 e 2003–2004 às amostras
históricas iniciadas em 2005. Cada modelo-base é treinado somente até dezembro
do ano anterior ao bloco. O treinamento supervisionado dos componentes começa
em 1981, como nos componentes originais; climatologia causal dos últimos 60 anos.

Antes de 2005 não existem blocos de calibração S11: usar o prior S10 fixo
(.28125, .140625, .140625, .1875, .25) para os cinco componentes, sem aprender
pesos com resultados posteriores. Esse aquecimento não é uma S11 calibrada;
é uma aproximação causal explícita, como o bloco inicial da pesquisa anterior.
Não recalibrar referências de 2005 em diante para favorecer a hipótese.

Amostragem: 2.048 pontos uniformes sem reposição por mês; semente 20260918 +
ano do bloco. Mesmos 23 atributos e resíduos observados menos referência causal.
Corretor: mesmos parâmetros da rodada 17, 15 folhas, 200 iterações e fração 0,25.
Nenhuma busca de fração, número de folhas ou novos atributos.

1. `expanded_uniform`: pesos iguais em todos os exemplos disponíveis anteriores.
2. `expanded_recent8`: peso exponencial por mês-alvo, meia-vida de oito anos,
   relativo ao último alvo anterior ao corte; normalizar pesos para média um,
   preservando a escala da regularização. Não calcular pesos usando erro futuro.

Previsão candidata = máximo(S11 causal + 0,25 × novo corretor, 0).
A referência S12 = máximo(S11 causal + 0,25 × corretor original, 0).
Não adicionar o novo corretor em cima da correção antiga.

## Critérios e ordem

Desenvolvimento: seis blocos de 24 meses, 2009–2020, toda a grade uniforme.
Exigir contra S12: ganho >=0,3%, segundos anos melhores, >=5/6 blocos,
>=9/12 anos, >=80/144 meses melhores e pior perda anual <=0,5%.
Selecionar o menor RMSE entre elegíveis. Se nenhuma passar, encerrar sem S13.

Só confirmar a selecionada em 2021–2022, janela já reutilizada: ganho >=0,1%
e ambos os anos melhores. Não substituir candidata após falha. Se passar,
treinar até dezembro de 2022 e exigir RMS da mudança contra S12 em cada ano
2023/2024 <=2× RMS histórico. Não acessar precipitação oculta desses anos.

O usuário autorizou gerar **S13** apenas se os resultados forem promissores;
interpretamos isso como passar em todos esses critérios, sem exceção. Nenhum
upload foi autorizado. Conferir modelo recarregado, CSV, ordem oficial e hashes.
O número 13 identifica a próxima versão, preservando a antiga S03.

A reprodução S12 pode usar os exemplos OOF oficiais congelados como evidência
de treino, assim como S11 usa covariâncias históricas congeladas. Documentar
essa dependência; não alegar reconstrução de toda a pesquisa a partir só dos NC.
