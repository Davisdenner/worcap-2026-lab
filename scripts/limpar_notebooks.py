r"""Remove a saída das células dos notebooks antes de versionar.

Um notebook guarda, dentro do próprio JSON, tudo que as células imprimiram:
tabelas, imagens em base64 e às vezes trechos de dado. Isso deixa o diff
ilegível, infla o repositório e pode carregar para o Git material que não
deveria sair daqui. O que interessa versionar é o código.

Não depende de jupyter nem de nbstripout: mexe no JSON direto, com a
biblioteca padrão. Idempotente -- rodar duas vezes não muda nada na segunda.

Uso (na raiz do repositório):

    .\.venv\Scripts\python.exe scripts\limpar_notebooks.py
    .\.venv\Scripts\python.exe scripts\limpar_notebooks.py --conferir

`--conferir` não escreve nada e sai com código 1 se algum notebook ainda
tiver saída, o que serve para rodar antes de um commit.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NOTEBOOKS = REPO_ROOT / "notebooks"


def limpar(nb: dict) -> bool:
    """Zera saídas e contadores. Devolve True se algo mudou."""
    mudou = False
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        if cell.get("outputs"):
            cell["outputs"] = []
            mudou = True
        if cell.get("execution_count") is not None:
            cell["execution_count"] = None
            mudou = True
    # O Jupyter grava aqui a assinatura do kernel que rodou; some entre
    # máquinas e vira diff sem conteúdo.
    metadata = nb.get("metadata", {})
    if metadata.pop("widgets", None) is not None:
        mudou = True
    return mudou


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--conferir", action="store_true",
                        help="não escreve; falha se algum notebook tiver saída")
    args = parser.parse_args()

    if not NOTEBOOKS.is_dir():
        print(f"Sem pasta de notebooks em {NOTEBOOKS}")
        return 0

    sujos = []
    for caminho in sorted(NOTEBOOKS.rglob("*.ipynb")):
        if ".ipynb_checkpoints" in caminho.parts:
            continue
        nb = json.loads(caminho.read_text(encoding="utf-8"))
        if not limpar(nb):
            print(f"ja limpo   {caminho.relative_to(REPO_ROOT)}")
            continue
        sujos.append(caminho)
        if args.conferir:
            print(f"COM SAIDA  {caminho.relative_to(REPO_ROOT)}")
            continue
        caminho.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n",
                           encoding="utf-8")
        print(f"limpo      {caminho.relative_to(REPO_ROOT)}")

    if args.conferir and sujos:
        print(f"\n{len(sujos)} notebook(s) com saida. Rode sem --conferir antes de commitar.")
        return 1
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
