# Rodada 14 — atributos físicos de umidade na S10

Definido antes dos resultados: quatro candidatas; somente dados oficiais e
transformações próprias. Referência S10, público 1,71895. Último líder informado
1,71488; último saldo informado um envio hoje. Sem upload automático, sem prometer
ganho ou score1,70. A conformidade foi examinada com a cópia das regras fornecida
pelo usuário; página Kaggle atual indisponível na última consulta.

## Atributos fixos e limitações físicas

Usar shum_850, u_850, v_850, surface_pressure e coordenadas oficiais. Produtos
das médias mensais F_lam=q*u e F_phi=q*v. Eles não são a média dos produtos
instantâneos, nem fluxo integrado verticalmente. Não representam balanço completo
de água, chuva futura conhecida, nem informação observacional nova.

Unidades ausentes dos atributos NetCDF. Faixas observadas são compatíveis com
ERA5 padrão: q em kg/kg, ventos m/s e pressão Pa (amostra: pressão 58507–102621).
Assunção explícita; os novos campos são proxies, não produtos oficiais derivados.
Não importar dados externos para completar coluna vertical ou topografia.

Definir validade por campos finitos e pressão de superfície >=85000 Pa.
Zerar produtos inválidos antes de média espacial5x5 (nearest, sem filtro temporal).
Usar apenas pontos cuja vizinhança7x7 inteira seja válida, para impedir que
valores subterrâneos ou bordas da máscara contaminem derivadas. Nos demais,
novos atributos são zero; não alterar dados oficiais nem os atributos anteriores.
Limitação: máscara usa pressão mensal, não condições instantâneas.

Convergência C=-[dF_lam/dlambda+d(F_phi*cos(phi))/dphi]/[R*cos(phi)],
R=6371000 m; latitude e longitude em radianos, diferenças finitas, bordas de
primeira ordem. Derivar depois da suavização e antes da redução espacial.
Guardar C*1e6 para condicionamento numérico; sinal positivo indica convergência
no proxy calculado. Checar fórmula com campos sintéticos de solução analítica.

Recorte de entrada -20 a15 graus, passo4 na grade0,25 (1 grau), todas as
longitudes, mesmo recorte dos atributos finos S10. Duas famílias: flux=(F_lam,F_phi)
e fluxconv=(F_lam,F_phi,C*1e6). PCA16 ou PCA32 de cada família: quatro candidatas.
Médias mensais e escalas (piso1e-8), PCA e escalas PC ajustadas somente no treino
desde1981 anterior ao corte; semente20260918. Estado atual+média causal3 e
interações sazonais, como S10. Concatenar às entradas continentais/tropicais S10.

## Modelo e controle

Reajustar PLS32 e saída ridge0,3 usando as entradas aumentadas e as mesmas
anomalias de chuva/climatologia60 da S10. Núcleo round11.fit_pls, EOF32 dos
alvos e semente20260917 daquele núcleo. Não usar modelos residuais/kernel
reprovados. Comparar contra controle S10 reproduzido integralmente.

Saída tropical -15 a15 graus. Manter exatamente peso25% ao norte de10S,
transição linear de15S a10S e restante S09. Ao sul de15S, S10 idêntica. Clipping
não negativo. Nenhuma nova candidata, alteração de máscara, suavização ou peso
depois de observar os resultados.

## Critérios congelados

Desenvolvimento em seis blocos de24 meses iniciados2009,2011,2013,2015,2017,2019.
RMSE uniforme da grade inteira. Todos os alvos de treino anteriores ao bloco.
Ganho agrupado>=0,3%, segundos anos melhores, >=5/6 blocos, >=9/12 anos,
>=55% dos144 meses melhores, maior perda anual<=0,5%. Menor RMSE elegível vence.
Se nenhuma passar, não gerar S11. Arquitetura e períodos reutilizados, sem
alegar teste independente ou certeza estatística desses critérios operacionais.

Confirmação apenas da escolhida em2021–2022, já consumido: ganho>=0,1% agrupado
e melhora nos dois anos. Não trocar candidata ou ajustar após essa checagem.
Final somente após aprovação, alvos atédezembro2022; RMS da mudança em2023 e2024,
separadamente, <=2x RMS histórico. Caso contrário, não exportar. Se aprovada,
gerar submission_11.csv com sample oficial e verificar IDs, ordem, valores,
hashes, causalidade e reconstrução integral. Recusar sobrescrita. Nenhum upload.

## Reprodução

PowerShell: OMP_NUM_THREADS, OPENBLAS_NUM_THREADS, MKL_NUM_THREADS=1;
PYTHONIOENCODING=utf-8. Usar .venv/Scripts/python.exe:

```text
-m src.round14 prepare
-m src.round14 evaluate
-m src.round14 select
-m src.round14 confirm  # apenas se selecionada
-m src.round14 final    # apenas se confirmação aprovada
-m src.round14 summarize
```

Artefatos em data/processed/round14, relatórios em reports/competition/round14.
