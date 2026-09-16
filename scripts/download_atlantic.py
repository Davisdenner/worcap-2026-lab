"""Immutable public NOAA PSL TNA/TSA snapshots, no precipitation targets."""
import hashlib
import json
import urllib.request
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
folder=ROOT / "data/external"
folder.mkdir(parents=True,exist_ok=True)
for index in ("tna","tsa"):
    url=f"https://psl.noaa.gov/data/correlation/{index}.data"
    path=folder / f"{index}.data"
    if path.exists():
        print("Preserving existing snapshot",path.name)
        continue
    with urllib.request.urlopen(url,timeout=45) as response:
        payload=response.read()
    first=payload.decode("utf-8").splitlines()[0].split()
    if len(first)!=2 or not all(x.isdigit() for x in first):
        raise ValueError("Unexpected PSL response")
    path.write_bytes(payload)
    metadata=dict(url=url,retrieved_utc=datetime.now(timezone.utc).isoformat(),sha256=hashlib.sha256(payload).hexdigest(),
                  source="NOAA Physical Sciences Laboratory",index=index.upper(),
                  temporal_policy="Only target-minus-two months or older; maximum consumed month 2024-10.",
                  vintage_limitation="Revised historical series, not archived real-time releases.")
    path.with_suffix(".json").write_text(json.dumps(metadata,indent=2),encoding="utf-8")
    print(json.dumps(metadata,indent=2))
