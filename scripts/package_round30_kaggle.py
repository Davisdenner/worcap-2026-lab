"""Empacota os artefatos necessários para a rodada 30 (gate CNN S12 x
Analog) em uma pasta única, pronta para subir como Kaggle Dataset privado.

Uso (na raiz do repositório, com o venv ativado):

    .\.venv\Scripts\python.exe scripts\package_round30_kaggle.py

Gera `kaggle_bundle/round30/` com:
  - code/        todos os módulos de src/*.py (o pipeline tem dependências
                  encadeadas entre rounds; copiar tudo evita erros de
                  import por um módulo faltando) + experiments/ROUND30.md.
  - artifacts/round27/, round28/    OOF do gate tabular já existente.
  - artifacts/round9/, round10/, round20/, round25/   mapas OOF em grade
                  cheia (S02, modos, local18, PLS16, S09, S12, análogo H4)
                  para os seis blocos de `round27.YEARS`.
  - artifacts/s12_evidence/  exemplos OOF congelados do corretor S12.
  - configs/     modelos.json (versões e hashes).
  - MANIFEST.json  lista de arquivos + sha256, no mesmo espírito dos
                    manifestos que o projeto já mantém em delivery/*/evidence.

Não copia dados brutos oficiais (NetCDF) nem `data/processed/official/tp.npy`
-- esse é reconstruído dentro do notebook Kaggle a partir do dataset oficial
anexado (ver experiments/ROUND30_KAGGLE_SETUP.md), para não redistribuir
dado bruto por fora do Kaggle (docs/CONFORMIDADE.md).
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLE_ROOT = REPO_ROOT / "kaggle_bundle" / "round30"

YEARS = (2009, 2011, 2013, 2015, 2017, 2019)

# (pasta de origem relativa a REPO_ROOT, lista de nomes de arquivo por ano)
FULL_GRID_ARTIFACTS = {
    "data/processed/round9": [
        "{year}_s02.npy", "{year}_modes.npy", "{year}_local18.npy", "{year}_pls16.npy",
    ],
    "data/processed/round10": ["{year}_s09.npy"],
    "data/processed/round20": ["{year}_s12.npy", "{year}_s12.json"],
    "data/processed/round25": ["{year}_h4_prediction.npy", "{year}_h4_prediction.json"],
}

# Diretórios copiados por inteiro (já são só o essencial nessas pastas).
FULL_DIR_ARTIFACTS = [
    "data/processed/round27",
    "data/processed/round28",
]

EVIDENCE_DIRS = {
    "artifacts/s12_evidence": "delivery/s12/evidence",
}

CONFIG_FILES = ["configs/modelos.json"]
EXTRA_DOCS = ["experiments/ROUND30.md", "experiments/ROUND32.md",
              "experiments/ROUND33.md"]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_and_hash(src: Path, dest: Path, manifest: dict) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    manifest[str(dest.relative_to(BUNDLE_ROOT)).replace("\\", "/")] = {
        "source": str(src.relative_to(REPO_ROOT)).replace("\\", "/"),
        "sha256": sha256_of(dest),
        "bytes": dest.stat().st_size,
    }


def main() -> None:
    if BUNDLE_ROOT.exists():
        shutil.rmtree(BUNDLE_ROOT)
    BUNDLE_ROOT.mkdir(parents=True)

    manifest: dict = {}

    code_count = 0
    for src in sorted((REPO_ROOT / "src").glob("*.py")):
        copy_and_hash(src, BUNDLE_ROOT / "code" / src.name, manifest)
        code_count += 1
    print(f"[ok] code: {code_count} módulos de src/*.py")

    for rel in EXTRA_DOCS:
        src = REPO_ROOT / rel
        if src.exists():
            copy_and_hash(src, BUNDLE_ROOT / "code" / Path(rel).name, manifest)
        else:
            print(f"[aviso] não encontrado, pulando: {rel}")

    for folder, patterns in FULL_GRID_ARTIFACTS.items():
        dest_prefix = f"artifacts/{Path(folder).name}"
        count = 0
        for year in YEARS:
            for pattern in patterns:
                name = pattern.format(year=year)
                src = REPO_ROOT / folder / name
                if src.exists():
                    copy_and_hash(src, BUNDLE_ROOT / dest_prefix / name, manifest)
                    count += 1
                else:
                    print(f"[aviso] não encontrado, pulando: {folder}/{name}")
        print(f"[ok] {dest_prefix}: {count} arquivos")

    for folder in FULL_DIR_ARTIFACTS:
        src_dir = REPO_ROOT / folder
        dest_prefix = f"artifacts/{Path(folder).name}"
        count = 0
        if src_dir.exists():
            for src in src_dir.glob("*"):
                if src.is_file():
                    copy_and_hash(src, BUNDLE_ROOT / dest_prefix / src.name, manifest)
                    count += 1
        print(f"[ok] {dest_prefix}: {count} arquivos")

    for dest_prefix, folder in EVIDENCE_DIRS.items():
        src_dir = REPO_ROOT / folder
        count = 0
        if src_dir.exists():
            for src in src_dir.glob("*"):
                if src.is_file():
                    copy_and_hash(src, BUNDLE_ROOT / dest_prefix / src.name, manifest)
                    count += 1
        print(f"[ok] {dest_prefix}: {count} arquivos")

    for rel in CONFIG_FILES:
        src = REPO_ROOT / rel
        if src.exists():
            copy_and_hash(src, BUNDLE_ROOT / rel, manifest)

    manifest_path = BUNDLE_ROOT / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(
            {
                "gerado_por": "scripts/package_round30_kaggle.py",
                "proposito": "Artefatos congelados para gate CNN S12 x Analog (rodada 30) no Kaggle",
                "aviso": "Não inclui dados brutos oficiais nem tp.npy. Reconstruir no notebook via competition.audit().",
                "arquivos": manifest,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    total_bytes = sum(v["bytes"] for v in manifest.values())
    print(f"\nPronto: {len(manifest)} arquivos, {total_bytes / 1e6:.1f} MB em {BUNDLE_ROOT}")
    print("Próximo passo: scripts/upload_round30_kaggle.py SEU_USUARIO_KAGGLE")


if __name__ == "__main__":
    main()
