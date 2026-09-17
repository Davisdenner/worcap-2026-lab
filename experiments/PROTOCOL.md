# Protocolo vigente de desenvolvimento

Este documento substitui as instruções operacionais antigas. Os protocolos
`ROUND*.md` continuam preservados como registros das decisões de cada rodada.
O texto anterior deste protocolo está em
`docs/history/antes_da_organizacao_2026-09-16/PROTOCOL.txt`.

## Referências e restrições

S10 é o controle aprovado (público informado 1,71895). S12 tem o melhor score
público informado (1,71456); S13 marcou 1,71461. S12 é a
referência reproduzível e teve exceção ao mínimo histórico. S13 foi um teste
exploratório com exceções explícitas ao mínimo histórico e à confirmação
reutilizada reprovada. S11 (1,71718) é a referência anterior, também experimental.
O resultado público não revoga os critérios nem reclassifica S11/S12/S13 como aprovadas.
Antes de cada rodada, declarar a referência exata e compará-la nos mesmos períodos;
não trocar a referência depois de observar os resultados.

Usar somente dados fornecidos pela organização e atributos derivados deles.
Não usar NOAA, modelos externos, previsões/resíduos/pseudoalvos de S07/S08 ou
chuva preparatória em `data/interim`. Nenhum alvo oculto de 2023/2024 pode ser
usado em treino, seleção ou calibração. A atmosfera de cada mês é permitida
conforme o alinhamento oficial mês observado → mês seguinte.

## Critérios ativos — todos são necessários

O ganho é relativo: `1 − RMSE_candidata / RMSE_referencia`.
**0,3% = 0,003**, não uma redução absoluta de 0,3 no RMSE.
A função congelada `src.round9.passes_gate` continua aplicada e coberta por testes.

| Desenvolvimento 2009–2020 | Exigência |
| --- | --- |
| RMSE agregado | Ganho relativo de pelo menos **0,3%** |
| Agregado dos segundos anos dos blocos | Menor RMSE que a referência |
| Blocos de 24 meses melhores | Pelo menos 5 de 6 |
| Anos melhores | Pelo menos 9 de 12 |
| Meses melhores | Pelo menos 55% de 144, isto é, 80 meses |
| Pior degradação anual relativa | No máximo 0,5% |

Depois da seleção em desenvolvimento, confirmar somente a candidata escolhida
em 2021–2022: ganho agregado de pelo menos **0,1%** e melhora nos dois anos.
Esse período já foi reutilizado; não chamá-lo de holdout independente.
Não trocar de candidata ou ajustar parâmetros após falhar na confirmação.

Antes de exportar, exigir que o RMS da mudança em relação à referência seja,
em 2023 e 2024 separadamente, no máximo duas vezes o RMS histórico da mudança.
Isso limita alterações muito maiores no teste; não garante score privado melhor.
Também verificar proveniência, integridade, causalidade, IDs e valores do CSV.

## Ordem de trabalho

1. Congelar hipótese, lista finita de candidatas, parâmetros, sementes,
   referência, períodos e critérios antes de medir resultados.
2. Treinar cada bloco apenas com alvos anteriores ao corte. Ajustar médias,
   escalas e decomposições somente no treino. Aprender pesos em blocos anteriores.
3. Registrar resultados completos e selecionar pelo menor RMSE entre elegíveis.
   Se nenhuma passar, encerrar a rodada sem nova candidata exportada.
4. Aplicar confirmação reutilizada e limite de mudança. Falhas bloqueiam a
   promoção normal; não afrouxar limiares após ver os resultados.
5. Gerar uma nova submissão somente com pedido explícito do usuário. Aprovação
   nos critérios, sozinha, não é autorização de exportação ou upload.
6. Se o usuário solicitar uma exceção, informar quais critérios falharam e
   obter autorização explícita para a exceção. Registrar a reprovação e o pedido
   sem alterar os critérios. Foi esse o caso de S11/S12 e, para teste pontual,
   de S13. As exceções da S13 estão no [protocolo específico](ROUND24_EXPERIMENTAL.md).
7. Preservar arquivos enviados, registrar versão, metadados e hash, verificar
   reprodução e só então atualizar os guias conforme o resultado confirmado.

## Reprodução não é experimento

`src.reproducao` aceita apenas versões registradas e gera cópias verificadas
contra hashes originais. Não promove modelos, não pesquisa parâmetros e não
envia arquivos ao Kaggle. Reproduzir S11 não reabre nem dispensa os critérios
para futuras versões. Consulte o [guia](../docs/REPRODUCAO.md).

O ganho mínimo protege o uso das submissões, mas não elimina seleção retrospectiva,
reutilização de validação ou incerteza sobre 2024. Não prometer 1,70, liderança
ou significância estatística a partir de pequenas diferenças públicas.
