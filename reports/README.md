# Índice dos resultados

A busca por uma sucessora da S12 foi até a rodada 36. O [resumo final](../docs/ENCERRAMENTO.md) cobre a trajetória até a rodada 29 e a [síntese das rodadas](../docs/SINTESE_RODADAS_25_34.md) explica, com os números, por que o platô se manteve até o fim. O [índice cronológico de experimentos](../experiments/README.md) lista cada rodada em ordem.

Melhor pública informada: **S12, 1,71456**. A S13 marcou **1,71461**,
0,00005 acima em RMSE. S12 permanece a referência reproduzível; S13 foi
um teste exploratório cuja confirmação reutilizada falhou. A classificação
final não foi informada.
S10, 1,71895, permanece como controle aprovado. Veja a
[metodologia central](../docs/METODOLOGIA.md) e o
[guia de reprodução](../docs/REPRODUCAO.md).

| Registro | Período de avaliação | Finalidade |
| --- | --- | --- |
| [Retomada S11: rodadas 16 a 18](competition/s11_followup_2026-09-16.md) | 2009 a 2020 | Diagnóstico e 16 candidatas; nenhuma aprovada |
| [S12 experimental](competition/round17_experimental/RESULTS.md) | Desenvolvimento e confirmação reutilizada 2021 a 2022 | Exceção autorizada; público informado 1,71456, sem aprovação automática |
| [Histórico ampliado, rodada 19](competition/round19/RESULTS.md) | 2009 a 2020 | Duas candidatas reprovadas contra S12; sem S13 |
| [Aprendizado direto, rodada 20](competition/round20/RESULTS.md) | 2009 a 2020 | Contexto local/global, oito misturas reprovadas |
| [Diagnóstico S12](competition/s12_diagnostic/RESULTS.md) | 2009 a 2020 | Distribuição espacial do erro da S12 reproduzida |
| [Especialistas regionais, rodada 21](competition/round21/RESULTS.md) | 2009 a 2020 | Quatro candidatas; melhor ganho 0,018%, nenhuma promovida |
| [Início do treino-base, rodada 22](competition/round22/RESULTS.md) | 2009 a 2020 | 1940/1960/1981 em árvore local; início antigo não aprovado |
| [Saída ampla + detalhe, rodada 23](competition/round23/RESULTS.md) | 2009 a 2020 | Reconstrução 9×9; mistura reprovada |
| [Transporte de umidade, rodada 24](competition/round24/RESULTS.md) | 2009 a 2020 | Convergência e lags de 850 hPa; ganho 0,0078%, sem promoção |
| [S13 experimental](competition/round24_experimental/RESULTS.md) | 2021 a 2022 reutilizado e público 2023 | Exceções autorizadas; 1,71461 informado, pior que S12 por 0,00005 |
| [Diagnóstico, PCs e análogos, rodada 25](competition/round25/DECISION.md) | 2009 a 2020 | H2 piorou; análogo +10% ganhou 0,0482%, abaixo do gate; nenhum promovido |
| [Previsibilidade do erro S12, rodada 26](competition/round26/REPORT.md) | Descritivo 2009 a 2020; OOF 2011 a 2020 | Valor do resíduo sem ganho; Q90 discriminável, sobretudo pelo regime chuvoso; classe C |
| [Seleção S12 × análogos, rodada 27](competition/round27/REPORT.md) | Oracle 2009 a 2020; gating OOF 2011 a 2020 | Oracle forte, risco Q90 não indica vencedor; melhor gate +0,075%, instável; classe D |
| [Magnitude da vantagem, rodada 28](competition/round28/REPORT.md) | Decomposição 2009 a 2020; ranking OOF 2011 a 2020 | Top 10% de G em módulo responde por 65% do benefício oracle; strong wins previsíveis, top-k +0,040%; classe D diagnóstica |
| [Novas famílias, rodada 29](competition/round29/REPORT.md) | OOF histórico auditado | ExtraTrees, LightGBM, RRR e CCA sem benefício estável; CNN/U-Net sem avaliação preditiva por limite de infraestrutura |
| [CSV S14 exploratório](competition/s14_experimental_round27_gate/REPORT.md) | Geração após a rodada 27 | Artefato local auditado, sem score público registrado |
| [Gate convolucional, rodada 30](competition/round30/REPORT.md) | OOF 2011 a 2019, GPU no Kaggle | Contexto 2D no gate; +0,078%, classe D |
| [U-Net ponta a ponta, rodada 32](competition/round32/REPORT.md) | OOF 2011 a 2019 | Arquitetura convolucional completa; -3,78% |
| [Volume de células, rodada 33](competition/round33/REPORT.md) | OOF 2011 a 2019 | 10,7 vezes mais células; corretor melhora 0,303%, mistura piora |
| [Corretor máximo, rodada 36](competition/round36/REPORT.md) | OOF 2011 a 2019 | Melhor resultado pós-S12, +0,110% com 5/5 blocos; não entregável, a persistência não existe no teste |
| [Combinação S10 com S12](competition/combinacao_diagnostic/RESULTS.md) | OOF 2009 a 2019 | Oracle de 0,000%; o erro da S10 é o da S12 mais ruído ortogonal |
| [Reprodução em clone vazio](competition/reproducao_clone_limpo.json) | S12, ambiente novo | CSV idêntico byte a byte, 6,1 minutos, nada faltando no clone |
| [Reprodução S10/S11](reproducao/README.md) | Treino final e inferência 2023 a 2024 | CSVs e previsões idênticos aos originais; 72 testes |
| [Reprodução S12](reproducao/S12.md) | Retreino do corretor e inferência completa | CSV e valores NetCDF idênticos; exemplos OOF oficiais empacotados |
| [Auditoria](competition/audit.json) | Arquivos oficiais | Integridade, coordenadas e alinhamento |
| [Atualização 15/09](competition/update_2026-09-15.json) | ZIP atualizado | NetCDF idênticos e sample compatível com S01 a S03 |
| [Rodada inicial](competition/RESULTS.md) | 2017 a 2020, 48 meses | Climatologias, ridge anual e árvores locais |
| [Rodada 2](competition/round2/RESULTS.md) | 2013 a 2020, 96 meses | Contexto espacial/temporal e seleção da S02 |
| [Rodada 3](competition/round3/RESULTS.md) | 2013 a 2020, 96 meses | Padrões regionais, sazonalidade e seleção da S03 |
| [Scores públicos](competition/leaderboard_observations.json) | 2023 | Scores informados após envio ao Kaggle |
| [Geração S10](competition/round11/RESULTS.md) | 2009 a 2020; confirmação 2021 a 2022 reutilizada | Modelo tropical fino aprovado |
| [Correção residual](competition/round12/RESULTS.md) | 2009 a 2020 | Não promovida |
| [Kernel tropical](competition/round13/RESULTS.md) | 2009 a 2020 | Não promovido |
| [Atributos físicos](competition/round14/RESULTS.md) | 2009 a 2020 | Não promovidos |
| [Recalibração conjunta](competition/round15/RESULTS.md) | 2009 a 2020 | Pesos causais, não promovida |

Cada rodada mantém JSON/CSV com métricas agregadas e por ano; os JSON incluem
RMSE mensal. Arquivos `selection.json` registram a decisão daquela rodada.
As seleções antigas são históricas. S10 é o controle aprovado; S12 tem o
melhor score público informado, sem aprovação retroativa. S12 é a referência
reproduzível. A exceção anterior da S11 está documentada nos
[resultados da S11](competition/round15_experimental/RESULTS.md).

O relatório inicial permanece como registro daquela etapa. Sua referência à
ausência de submissões descreve o momento da geração. Para o estado atual,
consultar o registro público e [submissions/README.md](../submissions/README.md).

2021 a 2022 já foi avaliado e reutilizado nas confirmações. Os resultados locais
e arquiteturas foram usados para seleção; não são uma estimativa independente
do privado. Relatos antigos de holdout intocado descrevem apenas aquele momento.
