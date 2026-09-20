r"""Sobe kaggle_bundle/round30/ (gerado por package_round30_kaggle.py) como
um Kaggle Dataset PRIVADO, usando kagglehub (já está em requirements.txt).

Pré-requisito: autenticação do Kaggle configurada uma vez, por qualquer um
destes caminhos:
  - arquivo kaggle.json em C:\\Users\\<usuario>\\.kaggle\\kaggle.json
    (baixado em kaggle.com -> Settings -> API -> Create New Token)
  - variáveis de ambiente KAGGLE_USERNAME e KAGGLE_KEY
  - kagglehub.login() interativo (abre prompt na primeira execução)

Uso:

    .\.venv\Scripts\python.exe scripts\upload_round30_kaggle.py SEU_USUARIO_KAGGLE

Isso cria (ou atualiza, como nova versão) o dataset privado
"SEU_USUARIO_KAGGLE/worcap-round30-artefatos". Depois, no notebook Kaggle,
anexe esse dataset por "Add Data" -> "Your Datasets".
"""

from __future__ import annotations

import sys
from pathlib import Path

import kagglehub

BUNDLE_DIR = Path(__file__).resolve().parent.parent / "kaggle_bundle" / "round30"
DATASET_SLUG = "worcap-round30-artefatos"


def main() -> None:
    if len(sys.argv) != 2:
        print("Uso: python upload_round30_kaggle.py SEU_USUARIO_KAGGLE")
        sys.exit(1)

    username = sys.argv[1]
    handle = f"{username}/{DATASET_SLUG}"

    if not BUNDLE_DIR.exists():
        print(f"Pasta não encontrada: {BUNDLE_DIR}")
        print("Rode antes: scripts/package_round30_kaggle.py")
        sys.exit(1)

    print(f"Enviando {BUNDLE_DIR} -> {handle} (privado)")
    kagglehub.dataset_upload(handle, str(BUNDLE_DIR), version_notes="rodada 30: bundle inicial")
    print("Concluído. Confirme em kaggle.com/<seu_usuario>/datasets que a visibilidade está PRIVADA.")


if __name__ == "__main__":
    main()
