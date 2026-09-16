"""Check documentation and immutable submission files; no training or uploads."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "submissions/manifest.json"
OBSERVATIONS = ROOT / "reports/competition/leaderboard_observations.json"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            digest.update(block)
    return digest.hexdigest()


def local_path(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Artifact must stay inside the repository")
    return path


def refresh():
    observations = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))["observations"]
    records = []
    for observation in observations:
        path = local_path(observation["submission_file"])
        metadata_path = path.with_suffix(".json")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        digest = sha256(path)
        if metadata.get("csv_sha256") and metadata["csv_sha256"] != digest:
            raise ValueError(f"Generation hash mismatch: {path.name}")
        with path.open("rb") as stream:
            if stream.readline().strip() != b"id,tp_mm_day":
                raise ValueError(f"Invalid header: {path.name}")
            rows = sum(1 for _ in stream)
        if rows != 1885464 or rows != metadata["rows"]:
            raise ValueError(f"Invalid row count: {path.name}")
        records.append({"file": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size,
                        "rows": rows, "sha256": digest, "public_rmse": observation["public_rmse"],
                        "accepted": observation["accepted"], "score_source": observation["source"],
                        "generation_metadata": metadata_path.relative_to(ROOT).as_posix()})
    manifest = {"day_closed": "2026-09-14", "best_submission": min(records, key=lambda r: r["public_rmse"])["file"],
                "submissions": records, "no_automatic_uploads": True}
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")


def check(allow_missing):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    observations = {o["submission_file"]: o for o in json.loads(OBSERVATIONS.read_text(encoding="utf-8"))["observations"]}
    failures, missing = [], []
    for record in manifest["submissions"]:
        path = local_path(record["file"])
        if record["public_rmse"] != observations[record["file"]]["public_rmse"]:
            failures.append(f"Score mismatch: {record['file']}")
        if not local_path(record["generation_metadata"]).is_file():
            failures.append(f"Missing metadata: {record['generation_metadata']}")
        if not path.exists():
            missing.append(record["file"])
            continue
        if path.stat().st_size != record["bytes"] or sha256(path) != record["sha256"]:
            failures.append(f"Artifact changed: {record['file']}")
    docs = [ROOT / "README.md", ROOT / "submissions/README.md", ROOT / "src/README.md", ROOT / "reports/README.md"]
    docs += list((ROOT / "docs").glob("*.md")) + list((ROOT / "experiments").glob("*.md"))
    absent_artifacts = {local_path(p) for p in missing}
    for doc in docs:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", doc.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            resolved = (doc.parent / target.split("#", 1)[0]).resolve()
            if not resolved.exists() and not (allow_missing and resolved in absent_artifacts):
                failures.append(f"Broken link: {doc.relative_to(ROOT)} -> {target}")
    if missing:
        print("Local artifacts absent:", ", ".join(missing))
        if not allow_missing:
            failures += [f"Missing artifact: {p}" for p in missing]
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"PASS: {len(manifest['submissions'])} submission records and {len(docs)} documentation files")
    print("Best recorded submission:", manifest["best_submission"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-manifest", action="store_true")
    parser.add_argument("--allow-missing-artifacts", action="store_true")
    args = parser.parse_args()
    if args.refresh_manifest:
        refresh()
    check(args.allow_missing_artifacts)
