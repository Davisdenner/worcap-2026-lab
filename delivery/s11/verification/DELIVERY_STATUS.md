# Registro histórico da verificação da entrega S11

Este registro descreve a verificação da entrega técnica anterior à organização
do repositório. Não substitui o relatório atual de S10/S11 em
`reports/reproducao/2026-09-16.json`. O ZIP original permanece preservado.

## Verificações concluídas naquela entrega

- Arquivos oficiais de treino relidos para um cache novo e isolado, sem usar
  previsões antigas para ajustar os componentes finais.
- Todos os componentes finais retreinados e parâmetros de inferência salvos.
- CSV reproduzido idêntico à S11 enviada, com SHA-256
  `8b871e4fa982045ee1c59abb19ff9e4954444aaf96de22052daa3de22e64b26f`.
- Ambiente Python 3.11.1 novo, sem pacotes do sistema, instalado com wheels
  offline Windows x64. A verificação `pip check` passou.
- Código copiado para uma pasta autônoma e utilizado para retreinar nesse ambiente
  separado, seguido de inferência independente. O segundo CSV também coincidiu
  exatamente. O cache recém-regenerado foi reutilizado no segundo treino;
  não foram usados caches antigos da pesquisa.
- Os pacotes offline preservaram licenças e seus arquivos corresponderam aos
  hashes RECORD das distribuições instaladas. São cópias reempacotadas localmente,
  não wheels originais dos editores. A tentativa pelo índice disponível não
  resolveu as versões nesse ambiente.
- Passaram 67 testes do repositório **naquela etapa**, incluindo a manutenção
  da reprovação histórica da S11. O total da verificação atual está no relatório
  de reprodução S10/S11, separado deste registro.
- Submissões originais e código científico congelado preservados.
- PDF de quatro páginas em inglês renderizado e inspecionado visualmente.

## Limitações do escopo

A calibração final foi reproduzida a partir das estatísticas de covariância
fora do treino arquivadas e do prior S10 congelado. Não se refez a pesquisa
histórica nem todas as previsões dos blocos de calibração a partir dos dados brutos.

As execuções usaram o mesmo host Windows. Não foi validado outro sistema
operacional, família de processadores ou instalação com pacotes baixados de
forma independente. A inferência atende à grade e ao calendário oficial de
24 meses, não a domínios arbitrários.

## Pendências do participante

- Confirmar a licença OSI do código; MIT foi proposta, não aprovada automaticamente.
- Informar equipe, integrantes, contatos, experiência e divisão de trabalho.
- Registrar resultado privado e classificação quando divulgados e confirmar
  exigências específicas do patrocinador.

O pacote é um rascunho técnico, não certificação jurídica ou entrega automática.
Não foi gerada uma nova candidata nem realizado upload ao Kaggle. Os critérios
internos de validação continuam vigentes.
