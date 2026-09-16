# Diagnóstico S08 e preservação dos três envios restantes

## Decisão

Manter S07 como referência pública: **1,73550** contra **1,74606** da S08.
A S08 piorou o RMSE em 0,01056, aproximadamente 0,61%. Não foi gerada nova
submissão, não houve novo treinamento nem upload durante esta auditoria.
Os scores e os três envios restantes são informações fornecidas pelo usuário.
Não foi consultada a classificação atual.

## O que foi verificado

- Reconstrução dos componentes oceânicos de S07/S08 e da combinação final
  de S08: diferença máxima igual a zero frente às previsões salvas.
- Snapshots externos mantêm seus hashes registrados. Última origem atmosférica
  usada: novembro/2024; última origem oceânica: outubro/2024.
- Verificação independente dos dois CSVs: 1.885.464 linhas, IDs na ordem
  oficial, hashes consistentes e 130 verificações de coordenadas/valores por
  arquivo. Não foi identificado defeito de exportação nas verificações realizadas.

Reprodução: `python -m src.diagnose_s08`. Números completos no
[diagnóstico JSON](diagnostic.json). O script somente lê modelos existentes;
não estima parâmetros de previsão. Os CSVs foram conferidos separadamente
com `scripts/verify_candidate.py`.

## Instabilidade observada

O RMS da diferença S08−S07 foi 0,04379 mm/dia nos anos históricos 2013–2022
e 0,08923 em 2023: **2,04 vezes maior**. Em 2024, foi 0,07845.
A faixa de latitude −10° a 15° concentrou 85,2% da soma dos quadrados das
mudanças em 2023, incluindo terra e oceano. Isso localiza as mudanças de
previsão, **não os erros reais**, pois os alvos do teste são desconhecidos.

Historicamente, S08 ganhou em 9/10 anos, mas somente em **67/120 meses**.
O ganho anual não era evidência suficiente de estabilidade mensal. Os blocos
2013–2020 já foram reutilizados na seleção de modelos. O bloco 2021–2022 foi
aberto para S08 e também não pode voltar a ser descrito como intocado.

Nas quatro entradas atlânticas, nenhum valor de 2023 saiu dos intervalos
individuais de treinamento. A distância multivariada regularizada ficou acima
do percentil 95 histórico em agosto–dezembro/2023, mas abaixo do máximo
histórico. Portanto, não há suporte para explicar a piora simplesmente como
extrapolação fora dos intervalos observados em 2023.

Em 2024, 9/12 meses superaram o máximo histórico dessa distância atlântica.
É um alerta de mudança de distribuição, não uma estimativa do score privado.
A referência é o treino final 1981–2022; a distância usa covariância com
regularização fixa de 0,05 e não constitui teste probabilístico calibrado.
Adicionar índices correlacionados também reajusta os coeficientes antigos;
não é possível atribuir causalmente a piora apenas ao termo atlântico direto.

## Um envio que podemos evitar: mistura parcial S07/S08

Assumindo exatamente o protocolo informado — RMSE uniforme sobre todos os
pontos de 2023, mesmos alvos para ambas as submissões — seja `d = S08−S07`:

```text
MSE(S07 + a*d) = MSE(S07) + a*(MSE8−MSE7−mean(d²)) + a²*mean(d²)
mean(d²) = 0,00796275
MSE8−MSE7−mean(d²) = 0,02880252
```

O coeficiente linear permanece positivo mesmo considerando arredondamento
de ±0,000005 em cada score: intervalo [0,02876771; 0,02883734]. Assim,
**toda mistura convexa positiva destas duas previsões (0 < a ≤ 1) piora S07
no público**, sob essas premissas, sem outras transformações.
Se o público usar máscaras ou amostragem não descritas, a conclusão deve ser
reavaliada. Isso não prevê o resultado privado. Não usar a identidade para
selecionar extrapolações negativas ajustadas ao leaderboard.

## Critérios propostos antes do próximo envio

1. Preservar S07 e não enviar outra versão apenas por melhora agregada pequena.
2. Pré-definir uma hipótese de robustez, comparações e critérios antes de novos
   testes. Investigar controle da magnitude das correções/regularização, sem
   escolher pesos para atingir o score público conhecido.
3. Exigir avaliação temporal por blocos, meses, regiões e segundos anos;
   explicitar perdas e dependência espacial. Analisar também regimes oceânicos
   incomuns e mudança da magnitude das previsões, sem usar os alvos do teste.
4. Separar novos blocos históricos que ainda não participaram da seleção,
   verificando primeiro os registros. Se não houver reserva adequada, declarar
   a limitação, sem chamar validação reutilizada de independente.
5. Só gerar candidata após evidência consistente contra S07 e auditoria final
   de IDs, datas, valores e hashes. Não há garantia de melhora pública/privada.
6. Não consumir os três envios por obrigação: usar o próximo somente se passar
   pelos critérios; condicionar o seguinte ao aprendizado obtido e conservar
   o último como margem para uma candidata final verificada. Não reenviar S07
   idêntica apenas para ocupar um slot.

Esses passos são um plano, não uma nova rodada já executada. Nenhum upload
ou monitoramento automático foi configurado.
