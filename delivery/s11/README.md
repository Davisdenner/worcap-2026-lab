# Entrega técnica S11 — documentação em português

S11: RMSE público informado **1,71718**. Este diretório reúne evidências,
dependências, instruções e registros da entrega técnica. Não certifica vitória,
score privado ou elegibilidade. O arquivo ZIP já construído é um snapshot
anterior, não é atualizado automaticamente quando este repositório muda.

Para um primeiro acesso ao repositório, siga o
[guia atual de reprodução S10/S11](../../docs/REPRODUCAO.md) e a
[metodologia central](../../docs/METODOLOGIA.md). Para o pacote autônomo
anterior, use [entry_points.md](entry_points.md).

## Conteúdo e ambiente

- `SETTINGS.json`: diretórios da interface anterior S11; a interface atual do
  repositório usa `configs/reproducao.json`.
- `requirements.txt`: versões fixadas, Python 3.11.1, Windows x64, CPU sem GPU,
  uma thread numérica. Referência: i5-1135G7, 16 GB RAM e aproximadamente 8 GB
  de espaço livre para dados/cache/modelos/saídas.
- `evidence`: pesos-base e estatísticas históricas de calibração, com hashes.
- `verification`: resultados da reprodução anterior em ambiente separado.
- `wheels/provenance.json`: inventário de distribuições reempacotadas localmente.
  Os wheels, modelos treinados e ZIP são locais e **não estão no Git**.
- `MODEL_SUMMARY.pdf`: resumo em inglês preservado da entrega anterior,
  complementar aos guias atuais em português.
- `TEAM_INFO.json`: identificação pendente de preenchimento pelo participante.

Os dados oficiais devem ser obtidos pelo participante após aceitar as regras;
não são incluídos no pacote. Nenhuma credencial é necessária no pipeline local.
As [licenças de terceiros](THIRD_PARTY_NOTICES.md) continuam aplicáveis.

## Escopo da reprodução

O treino final refaz todos os componentes a partir de arrays dos dados oficiais.
Os pesos-base são artefatos históricos preservados; a calibração conjunta é
recalculada das estatísticas fora do treino incluídas, sem alvos ocultos.
Não se refaz a pesquisa completa nem todos os blocos de calibração do zero.
A inferência carrega modelos e atmosfera do teste, sem ler chuva de treinamento.

O CSV da reprodução anterior S11 coincidiu byte a byte com o original:

```text
8b871e4fa982045ee1c59abb19ff9e4954444aaf96de22052daa3de22e64b26f
```

S11 foi uma exceção autorizada após falhar nos critérios. O mínimo de 0,3% e
os demais critérios continuam ativos. Reprodução não seleciona candidatas nem
envia arquivos. O pacote técnico ainda exige confirmação de licença do código,
identificação da equipe e revisão das exigências do patrocinador; veja
[conformidade](../../docs/CONFORMIDADE.md).
