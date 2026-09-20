r"""Confere as duas regras de estilo da documentação deste repositório.

REGRA 1: sem travessão nem meia-risca. Use vírgula, dois-pontos, parênteses
ou duas frases. Intervalos de ano vão por extenso: "2009 a 2020", não
"2009-2020" com meia-risca.

REGRA 2: primeira pessoa. A documentação é escrita por quem fez o trabalho,
então "autorizei a exceção" e não "o usuário autorizou a exceção", "o score
que obtive" e não "o score informado pelo participante". Isso não elimina a
qualificação de proveniência, que continua importando: "os scores são os que
obtive nos envios e não foram verificados de forma independente" diz a mesma
coisa que a versão em terceira pessoa, sem falar de si como um estranho.

Há uma exceção legítima, e por isso existe a lista de permitidos abaixo:
quando o texto se refere a OUTRA pessoa de verdade, como alguém que clona o
repositório para reproduzir a submissão, "usuário" está correto.

ARQUIVOS QUE NÃO PODEM SER CORRIGIDOS. Os protocolos `experiments/ROUND*.md`
ficam de fora da verificação porque **são congelados por hash**. Cada módulo
de rodada guarda `protocol_sha256` no seu `protocol.json` e compara a cada
execução; mudar uma vírgula num protocolo faz a rodada correspondente falhar
com "Código ou protocolo congelado mudou". Isso é proposital: o protocolo
registra o que foi decidido ANTES de a rodada rodar, e um texto que pode ser
editado depois não serve como registro. Estilo perde para rastreabilidade,
e por isso esses arquivos mantêm o estilo antigo.

Uso (na raiz do repositório):

    .\.venv\Scripts\python.exe scripts\verificar_estilo_docs.py

Sai com código 1 se encontrar alguma violação, então serve para rodar antes
de um commit de documentação.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Documentação escrita à mão. Os JSON de resultado ficam de fora: são registros
# gerados por código, não texto para leitura.
ALVOS = ["README.md", "src/README.md", "experiments/README.md",
         "submissions/README.md", "delivery/s11/README.md",
         "delivery/s12/README.md", "experiments/PROTOCOL.md",
         "experiments/NEXT.md"]
PASTAS = [("docs", "*.md"), ("reports", "**/*.md")]

# Protocolos congelados por hash: ver a explicação no cabeçalho.
CONGELADOS = re.compile(r"^ROUND\d+(_[A-Z_]+)?\.md$")

TRACOS = {"—": "travessão (—)", "–": "meia-risca (–)"}

TERCEIRA_PESSOA = re.compile(
    r"\b(o|do|pelo|ao)\s+(usuário|usuario|participante)\b", re.IGNORECASE)

# Frases em que "usuário" ou "participante" se refere mesmo a outra pessoa.
PERMITIDOS = (
    "Execução por um novo usuário",
    "por um novo usuário",
    "qualquer participante",
    "cada participante",
    "outro participante",
)


def arquivos() -> list[Path]:
    encontrados = [REPO_ROOT / a for a in ALVOS]
    for pasta, padrao in PASTAS:
        base = REPO_ROOT / pasta
        if base.is_dir():
            encontrados += [p for p in sorted(base.glob(padrao))
                            if "history" not in p.parts]
    return [p for p in dict.fromkeys(encontrados)
            if p.is_file() and not CONGELADOS.match(p.name)]


def permitido(linha: str) -> bool:
    return any(frase.lower() in linha.lower() for frase in PERMITIDOS)


def main() -> int:
    problemas = 0
    for caminho in arquivos():
        relativo = caminho.relative_to(REPO_ROOT).as_posix()
        for numero, linha in enumerate(
                caminho.read_text(encoding="utf-8").splitlines(), 1):
            for simbolo, nome in TRACOS.items():
                if simbolo in linha:
                    print(f"{relativo}:{numero}: {nome} em "
                          f"{linha.strip()[:88]}")
                    problemas += 1
            if TERCEIRA_PESSOA.search(linha) and not permitido(linha):
                print(f"{relativo}:{numero}: terceira pessoa em "
                      f"{linha.strip()[:88]}")
                problemas += 1

    total = len(arquivos())
    if problemas:
        print(f"\n{problemas} problema(s) em {total} arquivos de documentação.")
        return 1
    print(f"OK: {total} arquivos de documentação sem travessão e em primeira pessoa.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
