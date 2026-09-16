"""Read-only independent checks of a candidate CSV, metadata and labeled NetCDF."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

ROOT=Path(__file__).resolve().parents[1]


def verify(csv_path,nc_path):
    frame=pd.read_csv(csv_path,dtype={"id":str})
    template=pd.read_csv(ROOT / "data/raw/sample_submission.csv",usecols=["id"],dtype={"id":str})
    metadata=json.loads(csv_path.with_suffix(".json").read_text())
    if list(frame)!=["id","tp_mm_day"] or len(frame)!=1885464:
        raise ValueError("Wrong columns or row count")
    if not frame.id.is_unique or not frame.id.equals(template.id):
        raise ValueError("IDs/order mismatch")
    values=frame.tp_mm_day.to_numpy()
    if not np.isfinite(values).all() or (values<0).any():
        raise ValueError("Invalid predictions")
    digest=hashlib.sha256(csv_path.read_bytes()).hexdigest()
    if metadata["csv_sha256"]!=digest:
        raise ValueError("Hash mismatch")
    rng=np.random.default_rng(20260915)
    rows=np.unique(np.concatenate([[0,len(frame)-1],rng.choice(len(frame),128,replace=False)]))
    with xr.open_dataset(nc_path) as ds:
        for i in rows:
            year,month,lat,lon=frame.id.iloc[i].split("_")
            expected=float(ds.tp_mm_day.sel(time=np.datetime64(f"{year}-{month}-01"),lat=float(lat),lon=float(lon)))
            if abs(expected-values[i])>5.1e-9:
                raise ValueError(f"Coordinate/value mismatch: {frame.id.iloc[i]}")
    print(json.dumps(dict(status="PASS",file=str(csv_path),rows=len(frame),bytes=csv_path.stat().st_size,
                          full_official_id_order=True,coordinate_value_spot_checks=len(rows),sha256=digest),indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv",type=Path)
    parser.add_argument("netcdf",type=Path)
    args=parser.parse_args()
    verify(args.csv,args.netcdf)
