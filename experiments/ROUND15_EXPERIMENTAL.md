# S11 experimental — autorização explícita do usuário

Após conhecer a reprovação da rodada 15, o usuário pediu a geração da S11
com o melhor ganho observado: `joint1`, lambda 1, sem retunar ou escolher
outra candidata. Esta autorização permite exportar, não fazer upload.
Novas submissões só devem ser geradas quando solicitadas pelo usuário.

O protocolo, código e seleção congelados da rodada 15 permanecem intactos.
`selected: null` continua correto: a exportação é experimental e não representa
aprovação nos critérios. S10 continua a melhor referência pública confirmada.

Executar uma checagem diagnóstica de 2021–2022, período já reutilizado, sem
seleção ou ajuste posterior. Recalibrar os mesmos cinco componentes oficiais
para 2023–2024 com blocos históricos completos até dezembro de 2022.
Manter lambda 1, os 12 grupos, convexidade e limite de mudança de 0,10.
Não usar dados externos ou chuva oculta de 2023/2024.

Registrar métricas e magnitude da correção, inclusive eventuais reprovações.
O resultado diagnóstico não muda a candidata explicitamente solicitada.
Validar dimensões, valores, ordem do sample oficial, hashes e reprodução.
Recusar sobrescrita e preservar S10. Não registrar score ou upload inexistentes.

Execução: `python -m src.round15_experimental --user-authorized`.
