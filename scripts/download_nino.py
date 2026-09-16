"""Download immutable NOAA CPC raw SST index snapshot; no rainfall targets."""
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
URL="https://www.cpc.ncep.noaa.gov/data/indices/ersst5.nino.mth.91-20.ascii"
path=ROOT / "data/external/ersst5.nino.mth.91-20.ascii"
path.parent.mkdir(parents=True,exist_ok=True)
if path.exists():
    raise FileExistsError("Existing snapshot is immutable")
with urllib.request.urlopen(URL,timeout=45) as response:
    payload=response.read()
header=payload.decode("ascii").splitlines()[0]
if "YR" not in header or "NINO" not in header:
    raise ValueError("Unexpected NOAA response")
path.write_bytes(payload)
metadata=dict(url=URL,retrieved_utc=datetime.now(timezone.utc).isoformat(),sha256=hashlib.sha256(payload).hexdigest(),
              fields="Raw monthly SST for Nino1+2, Nino3, Nino4, Nino3.4. Published anomaly columns ignored.",
              temporal_policy="Latest predictor month is target minus two months; only dates through 2024-10 consumed.",
              vintage_limitation="Current revised historical SST, not archived real-time releases. Extra lag is not a vintage guarantee.")
path.with_suffix(".json").write_text(json.dumps(metadata,indent=2),encoding="utf-8")
print(header)
print(json.dumps(metadata,indent=2))
