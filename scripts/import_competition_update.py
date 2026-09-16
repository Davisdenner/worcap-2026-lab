"""Inspect an official ZIP, import its sample only, and compare existing outputs."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"


def digest(stream):
    h = hashlib.sha256()
    for block in iter(lambda: stream.read(1024*1024), b""):
        h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = {"archive_at_import": str(args.archive.resolve()), "netcdf": [], "submissions": []}
    with zipfile.ZipFile(args.archive) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate archive entries")
        expected = {p.name for p in RAW.glob("*.nc")}
        present = {n for n in names if n.endswith(".nc")}
        if expected != present:
            raise ValueError(f"NetCDF inventory changed: added={present-expected}, missing={expected-present}")
        for name in sorted(expected):
            with archive.open(name) as incoming, (RAW / name).open("rb") as current:
                new_hash, old_hash = digest(incoming), digest(current)
            report["netcdf"].append({"file": name, "sha256_incoming": new_hash,
                                     "sha256_existing": old_hash, "identical": new_hash == old_hash})
            print(name, "IDENTICAL" if new_hash == old_hash else "CHANGED", flush=True)
        sample_name = "sample_submission.csv"
        with archive.open(sample_name) as stream:
            sample_hash = digest(stream)
        destination = RAW / sample_name
        if destination.exists():
            with destination.open("rb") as stream:
                if digest(stream) != sample_hash:
                    raise ValueError("An existing different sample must be preserved before replacement")
        else:
            # Literal known entry: no arbitrary archive paths are extracted.
            archive.extract(sample_name, RAW)
        report["sample_sha256"] = sample_hash
    sample = pd.read_csv(destination, dtype={"id": str})
    if list(sample.columns) != ["id", "tp_mm_day"] or len(sample) != 1885464 or not sample.id.is_unique:
        raise ValueError("Unexpected sample schema, row count or duplicate IDs")
    report["sample"] = {"rows": len(sample), "columns": list(sample.columns),
                         "first_id": sample.id.iloc[0], "last_id": sample.id.iloc[-1],
                         "unique_ids": True, "placeholder_values": sample.tp_mm_day.unique().tolist()}
    ledger = json.loads((ROOT / "submissions/manifest.json").read_text(encoding="utf-8"))
    official_ids = pd.Index(sample.id)
    for item in ledger["submissions"]:
        submitted = pd.read_csv(ROOT / item["file"], usecols=["id"], dtype={"id": str})
        equal_order = np.array_equal(submitted.id.to_numpy(), sample.id.to_numpy())
        equal_set = len(submitted) == len(sample) and submitted.id.is_unique and submitted.id.isin(official_ids).all()
        report["submissions"].append({"file": item["file"], "same_ids": bool(equal_set), "same_order": bool(equal_order)})
        print(item["file"], "same_ids", equal_set, "same_order", equal_order, flush=True)
    report["all_netcdf_unchanged"] = all(r["identical"] for r in report["netcdf"])
    report["all_submission_ids_and_order_match"] = all(r["same_ids"] and r["same_order"] for r in report["submissions"])
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print("REPORT", args.report, flush=True)


if __name__ == "__main__":
    main()
