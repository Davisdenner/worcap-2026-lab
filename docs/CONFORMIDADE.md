# Conformidade técnica e preparação da entrega

Esta é uma verificação técnica do que o repositório oferece, não uma certificação
de elegibilidade pelo organizador. A base é o trecho de regras fornecido pelo
participante, especialmente a obrigação de entregar código de treino, inferência,
documentação e ambiente capazes de gerar a submissão final.

## O que está disponível

| Obrigação técnica | Material no repositório |
| --- | --- |
| Código de treinamento e inferência | `src/s11_delivery.py` e dependências científicas preservadas |
| Execução por um novo usuário | [Guia de reprodução](REPRODUCAO.md) e `src/reproducao.py` |
| Explicação do método | [Metodologia](METODOLOGIA.md) |
| Ambiente e recursos | Dependências fixadas, configurações e registros de execução |
| Rastreabilidade da submissão | Metadados originais, catálogo, manifesto e hashes independentes |
| Artefatos aprendidos | Evidências de calibração versionadas; componentes finais retreináveis e serializados |
| Separação de dados | Dados oficiais fora do Git; S10/S11 sem componentes externos S07/S08 |

Os critérios históricos de 0,3% são uma política interna de seleção, não uma
regra da competição. A exceção S11 não é, por si, infração às regras; deve
continuar documentada como exceção, sem afrouxar a política futura.

## Escopo que não deve ser exagerado

A reprodução retreina os componentes finais e verifica o CSV. Ela reutiliza
pesos-base e estatísticas históricas de calibração congelados. Não foi reexecutada
toda a pesquisa histórica nem a geração de cada previsão fora do treino.
O ambiente offline foi testado com distribuições locais reempacotadas; não
é correto apresentá-las como wheels originais baixados dos editores.

Modelos, wheels e ZIP de entrega são arquivos locais ignorados pelo Git. Um
clone não inclui automaticamente esses arquivos; o guia ensina o retreino e
explica a alternativa offline. Antes de entregar, reúna os artefatos necessários
da versão final e teste o pacote isoladamente, não apenas a pasta de trabalho.

## Pendências antes da entrega definitiva

1. Confirmar a licença OSI do código com o titular; não foi atribuída uma
   licença automaticamente. Respeitar licenças das dependências separadamente.
2. Preencher equipe, integrantes, contatos e atribuições em
   [TEAM_INFO.json](../delivery/s11/TEAM_INFO.json), sem inventar dados pessoais.
3. Selecionar a versão final conforme as regras e conservar seus modelos,
   evidências, código, configurações e hashes em um pacote fechado.
4. Repetir instalação e reprodução do pacote final em ambiente separado,
   conferir resultados e atualizar o inventário/relatório dessa entrega.
5. Confirmar exigências específicas do patrocinador e registrar o resultado
   privado/classificação somente quando conhecidos.

As [diretrizes oficiais de documentação de modelos vencedores](https://www.kaggle.com/WinningModelDocumentationGuidelines)
pedem resumo em Word/PDF, normalmente em inglês salvo aprovação diversa, além
do código, modelos, instruções de ambiente, treino e inferência. Os guias atuais
do repositório são em português por decisão do participante. O PDF em inglês
da entrega técnica anterior foi preservado como complemento histórico; sua
existência não dispensa revisar o resumo da versão realmente entregue nem
confirmar com o organizador eventual entrega somente em português.

Não redistribuir os dados oficiais como se fossem cobertos pela licença do código.
Observar os termos da competição e a atribuição Copernicus. Nenhuma credencial
deve integrar o pacote. Nenhum commit, publicação ou envio ao patrocinador é
realizado automaticamente por este fluxo.
