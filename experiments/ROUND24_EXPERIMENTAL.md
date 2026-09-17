# S13 experimental — transporte de umidade com lags no norte

Pedido explícito do usuário após ver o ganho de desenvolvimento de 0,0078%:
gerar um arquivo para **testar** o score público no Kaggle. A candidata exata
é `transporte_lag_norte_b0.5` da rodada 24. Este pedido autoriza dispensar
**somente** o mínimo histórico de 0,3% nesta exportação; não altera o gate
vigente, o registro de reprovação, os pesos ou a máscara. Não autoriza upload
automático nem alega melhora no score público/privado.

Manter obrigatoriamente: segundo ano agregado melhor, >=5/6 blocos,
>=9/12 anos, >=80/144 meses, perda anual máxima <=0,5%; confirmação
reutilizada 2021–2022 com ganho >=0,1% e ambos os anos melhores; RMS da
mudança em 2023 e em 2024 <=2× RMS histórico; proveniência oficial,
integridade da S12, alinhamento do eixo temporal, modelo final treinado
somente com alvos até dezembro/2022 e CSV ordenado pelo sample oficial.
Se alguma condição não dispensada falhar, não exportar sem nova decisão.

Para a confirmação, ajustar o corretor HGB15 sobre blocos OOF completos
anteriores a 2021, sem dados de 2021–2022 no treino. Para o teste, ajustar
o mesmo corretor sobre todos os blocos OOF completos até 2021. O corretor
global S12 final mantém seus parâmetros e treino originais. Usar os campos
`shum_850`, `u_850`, `v_850` do `teste_features.nc` somente na posição
`time_origem` correspondente ao mês observado; para dezembro/2022 usar o
treino e verificar igualdade com a primeira posição do teste. Não ler
`tp_alvo`, nem interpolar chuva observada de 2023/2024.

Compor `max(S11+0,25*(delta_S12+0,5*máscara_norte*(delta_lag−delta_S12)),0)`.
Preservar os IDs e a ordem de `sample_submission.csv`, sem reconstruí-los.
Registrar hashes, modelo, evidências, confirmação e limite de mudança.

## Decisão posterior: S13 somente para teste exploratório

Após a confirmação reutilizada de 2021–2022 reprovar (ganho de 0,00247%,
2022 ligeiramente pior), o usuário respondeu "prossiga" ao pedido explícito
de decisão sobre dispensar também essa confirmação. Esta é uma **segunda
exceção pontual** para gerar o CSV e testar o score público, não uma revisão
retroativa da confirmação ou do critério histórico de 0,3%. Registrar a
dispensa em `confirmation_waiver.json` e manter `passed: false` no resultado
original. O limite de RMS da mudança em 2023 e 2024, a integridade da S12,
os dados oficiais e todas as demais verificações permanecem obrigatórios.
O envio ao Kaggle continua manual, a cargo do usuário.
