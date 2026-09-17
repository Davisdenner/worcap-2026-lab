# S12 experimental — autorização condicionada da variante conservadora

O usuário autorizou a proposta de verificar `meta15_a0.25` em 2021–2022 e,
somente se passar na confirmação e no limite de mudança, gerar S12 para um
envio exploratório. Não autorizou upload automático. Autorização recebida como
“faça isso” após a recomendação explícita dessa variante e dessas condições.

## Exceção restrita

A candidata é fixa: corretor não linear de 15 folhas, fração 0,25, conforme
o protocolo ROUND17. RMSE histórico 1,770775491 contra 1,774621760 da S11;
ganho 0,216737%, inferior ao mínimo de 0,3%. Melhora 5/6 blocos, 10/12 anos e
88/144 meses; pior perda anual 0,351990%, dentro do limite de 0,5%.

A autorização dispensa **somente o ganho mínimo no desenvolvimento para
esta exportação experimental**. Não altera a reprovação da rodada 17 nem os
critérios futuros. Não mudar fração, parâmetros, referência ou candidata após
ver a confirmação. S10, S11 e a seleção original devem permanecer intactas.

## Condições que continuam obrigatórias

1. Confirmação em 2021–2022, período já reutilizado: ganho RMSE agregado >=0,1%
   contra S11 e melhora em ambos os anos. Treino do corretor apenas em blocos
   completos encerrados até 2020.
2. Somente se passar, treinar o corretor final com resíduos oficiais até 2022.
   Nenhum alvo oculto de 2023/2024, NOAA, S07/S08 ou data/interim.
3. RMS da mudança contra S11 em 2023 e em 2024 separadamente <=2× RMS histórico
   da mudança da candidata conservadora, 0,0763325514 mm/dia.
4. Verificar modelos serializados, reconstrução das previsões, grade, todos os
   IDs na ordem do sample oficial, valores finitos/não negativos e hashes.

Falha em qualquer condição encerra a execução sem S12. A eventual geração
produz `submissions/submission_12.csv`, sem sobrescrever arquivos existentes,
e metadados que declaram a exceção. Score público permanece desconhecido até
relato do usuário. Não transformar ganho histórico em previsão de score Kaggle.

## Execução

```powershell
.\.venv\Scripts\python.exe -m src.round17_experimental confirm --user-authorized
.\.venv\Scripts\python.exe -m src.round17_experimental export --user-authorized
```

O segundo comando é bloqueado se a confirmação falhar. Resultados da exceção
ficam separados em `reports/competition/round17_experimental`; previsão NetCDF
em `data/processed/round17_experimental`. O programa não realiza uploads.
