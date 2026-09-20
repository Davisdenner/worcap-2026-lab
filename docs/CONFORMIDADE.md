# Conformidade técnica e preparação da entrega

Esta é uma verificação técnica do que o repositório oferece, não uma certificação
de elegibilidade pelo organizador. A base é o trecho de regras fornecido pelo
participante, especialmente a obrigação de entregar código de treino, inferência,
documentação e ambiente capazes de gerar a submissão final.

## O que está disponível

| Obrigação técnica | Material no repositório |
| --- | --- |
| Código de treinamento e inferência | `src/s11_delivery.py`, `src/s12_delivery.py` e dependências científicas preservadas |
| Execução por um novo usuário | [Guia de reprodução](REPRODUCAO.md) e `src/reproducao.py` |
| Documentação da versão entregue | [Entrega da S12](ENTREGA_S12.md), na estrutura das diretrizes da Kaggle |
| Explicação do método | [Metodologia](METODOLOGIA.md) |
| Ambiente e recursos | Dependências fixadas, configurações e registros de execução |
| Rastreabilidade da submissão | Metadados originais, catálogo, manifesto e hashes independentes |
| Artefatos aprendidos | Evidências de calibração versionadas; componentes finais retreináveis e serializados |
| Separação de dados | Dados brutos oficiais fora do Git; S10/S11/S12/S13 sem componentes externos S07/S08 |

Os critérios históricos de 0,3% são uma política interna de seleção, não uma
regra da competição. A exceção S11 não é, por si, infração às regras; deve
continuar documentada como exceção, sem afrouxar a política futura.

## Escopo que não deve ser exagerado

A reprodução retreina os componentes finais e verifica o CSV. Ela reutiliza
pesos-base, estatísticas históricas de calibração e exemplos OOF do corretor S12
congelados. Estes últimos são dados derivados oficiais, incluídos no pacote e
sujeitos aos termos dos dados, não automaticamente à licença do código. Não foi reexecutada
toda a pesquisa histórica nem a geração de cada previsão fora do treino.
O ambiente offline foi testado com distribuições locais reempacotadas; não
é correto apresentá-las como wheels originais baixados dos editores.

Modelos, wheels e ZIP de entrega são arquivos locais ignorados pelo Git. Um
clone não inclui automaticamente esses arquivos; o guia ensina o retreino e
explica a alternativa offline. Antes de entregar, reúna os artefatos necessários
da versão final e teste o pacote isoladamente, não apenas a pasta de trabalho.

## Resolvidas

**Licença.** O código está sob **MIT**, aprovada pela OSI. Isso cobre apenas o
código; as licenças das dependências continuam valendo separadamente, e os
dados oficiais não são cobertos por ela.

**Reprodução em ambiente separado.** A S12 foi reproduzida byte a byte a partir
de um clone vazio, com `.venv` novo e as dependências fixadas, sem nenhum
arquivo copiado de fora do repositório. O teste está automatizado em
[verificar_clone_limpo.ps1](../scripts/verificar_clone_limpo.ps1) e deve ser
repetido sobre o pacote final.

## Pendências antes da entrega definitiva

1. Preencher equipe, integrantes, contatos e atribuições em
   [TEAM_INFO.json](../delivery/s11/TEAM_INFO.json), sem inventar dados pessoais.
2. Selecionar a versão final conforme as regras e conservar seus modelos,
   evidências, código, configurações e hashes em um pacote fechado.
3. Atualizar o inventário e o relatório da entrega para a versão escolhida.
4. Confirmar exigências específicas do patrocinador e registrar o resultado
   privado/classificação somente quando conhecidos.

As [diretrizes oficiais de documentação de modelos vencedores](https://www.kaggle.com/WinningModelDocumentationGuidelines)
pedem resumo em Word/PDF, normalmente em inglês salvo aprovação diversa, além
do código, modelos, instruções de ambiente, treino e inferência. Os guias atuais
do repositório são em português por decisão do participante, e a
[documentação de entrega da S12](ENTREGA_S12.md) segue a estrutura dessas
diretrizes. O [PDF em inglês](../output/pdf/S11_Model_Summary.pdf) da entrega
técnica anterior foi preservado como complemento histórico e descreve a **S11**,
não a S12; sua existência não dispensa revisar o resumo da versão realmente
entregue nem confirmar com o organizador eventual entrega somente em português.

Não redistribuir os dados oficiais como se fossem cobertos pela licença do código.
Observar os termos da competição e a atribuição Copernicus. Nenhuma credencial
deve integrar o pacote. Nenhum commit, publicação ou envio ao patrocinador é
realizado automaticamente por este fluxo.
