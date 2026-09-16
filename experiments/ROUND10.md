# Rodada 10 — PLS dos erros residuais da S09

Protocolo definido antes do diagnóstico e dos novos resultados. Referência:
S09, público 1,72957, somente dados oficiais. Meta aspiracional: 1,70 e primeiro
lugar, sem garantia nem uso do score do líder para estimar parâmetros.

## Hipótese e limites

Aprender padrões atmosféricos relacionados ao erro restante da S09, em vez
de aprender novamente o campo de chuva. Resíduo = chuva observada menos S09.
Toda previsão que gera um resíduo de treinamento foi feita por modelos-base
ajustados antes daquele bloco. O corretor para um bloco só usa resíduos de
blocos anteriores. Nunca usar os resíduos da S09 ajustada aos próprios alvos.

S09 permanece 75% S06 + 25% PLS16. Preservar seus arquivos, parâmetros e
metadados. Não aumentar seu peso PLS com base no retorno público.
Somente dados oficiais; proibir NOAA, S07/S08, modelos externos e data/interim.

## Preparação e diagnóstico

Verificar hashes dos arquivos oficiais e da S09, igualdade dos caches oficiais
com os NetCDF e hash do cache espacial já auditado na rodada 9. Reaproveitar
as previsões históricas S09 de 2009–2022; gerar as duas bases faltantes de
2005–2008 com o código congelado da rodada 9. Não sobrescrever artefatos.
Antes dos candidatos, diagnosticar S09 em 2009–2020 por ano, mês de calendário,
faixa de latitude e estação. Não escolher regiões ou mudar candidatos depois
desse diagnóstico. O alvo oculto de 2023–2024 não está disponível nem será usado.

## Experimentos fixos

- Sementes fora do treino: 2005–2006 e 2007–2008.
- Desenvolvimento: seis blocos de 24 meses, iniciados em 2009, 2011, 2013,
  2015, 2017 e 2019. Grade completa; RMSE uniforme.
- Confirmação: 2021–2022, já utilizado nas rodadas 8 e 9, portanto não inédito.
  Pontuar somente a candidata congelada após o desenvolvimento.
- A arquitetura S09 já foi escolhida com esses períodos. O corte temporal
  impede vazamento na nova estimação, mas não torna a pesquisa independente.

Entradas: PCA atmosférica64 da S09 do corte correspondente (ajustada somente
na atmosfera de treino), estado atual + média causal de três meses e interações
com seno/cosseno do mês-alvo. A nova escala das entradas usa somente os meses
de resíduos anteriores ao corte. Não incluir precipitação observada do bloco
previsto como atributo. Alvos: 16 EOFs dos resíduos anteriores, ajustados só
no treino do corretor, sem padronizar cada ponto de chuva para manter sua escala.

PLS com 2, 4 ou 8 componentes; ridge 1,0 dos escores padronizados para o campo
completo de resíduos, intercepto não penalizado. Duas intensidades: 25% ou 50%.
Total: seis candidatas. Predição = máximo(S09 + intensidade × correção, 0).
Semente fixa 20260916. Não adicionar candidatos depois de observar resultados.

## Critérios para gastar um envio

Mesmos critérios de desenvolvimento da rodada 9, agora contra S09: redução
relativa do RMSE agrupado >=0,3%, melhora dos segundos anos, >=5/6 blocos,
>=9/12 anos, >=55% dos 144 meses e piora anual máxima <=0,5%.
Escolher a menor RMSE entre as elegíveis; se nenhuma passar, não gerar S10.

Na confirmação 2021–2022, exigir melhora nos dois anos e ganho agrupado
>=0,1%. Se falhar, não substituir por outra candidata nessa checagem nem
reajustar parâmetros. No final, treinar o corretor com resíduos até 2022,
permitidos apenas depois da seleção/checagem. Para 2023 e 2024 separadamente,
o RMS da correção não pode exceder duas vezes seu RMS de desenvolvimento.
Exceder esse limite bloqueia exportação, sem ajuste posterior de intensidade.

Se aprovada, gerar S10 distinta com o sample oficial e verificar IDs, datas,
valores, hash e reprodução do modelo. Nenhum upload automático. A quantidade
de envios restantes não será assumida como ilimitada. Não prometer score 1,70.

## Reprodução

```powershell
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:PYTHONIOENCODING='utf-8'
.venv/Scripts/python.exe -m src.round10 audit
.venv/Scripts/python.exe -m src.round10 prepare
.venv/Scripts/python.exe -m src.round10 diagnose
.venv/Scripts/python.exe -m src.round10 evaluate
.venv/Scripts/python.exe -m src.round10 select
.venv/Scripts/python.exe -m src.round10 confirm
.venv/Scripts/python.exe -m src.round10 final
.venv/Scripts/python.exe -m src.round10 summarize
```

confirm/final recusam candidatas não aprovadas. Sem aprovação, encerrar em
select/summarize. Resultados em reports/competition/round10; modelos e previsões
em data/processed/round10. As novas bases PLS de 2005/2007 usam o cache original
round9, exclusivamente em arquivos ainda inexistentes.
