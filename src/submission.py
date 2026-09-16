"""Export labeled predictions; optionally preserve official template ID order."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

try:
    from .competition import RAW, ROOT, fit_climatology, month_number, save_json
except ImportError:
    from competition import RAW, ROOT, fit_climatology, month_number, save_json


def expected_ids(grid):
    spatial = [f"{float(lat):.2f}_{float(lon):.2f}"
               for lat in grid.lat.values for lon in grid.lon.values]
    return pd.Index([f"{t:%Y_%m}_{point}" for t in pd.DatetimeIndex(grid.time.values)
                     for point in spatial], name="id")


def export_csv(predictions, grid, destination, template=None):
    """Match values to coordinate labels, never infer array orientation."""
    if set(predictions.dims) != {"time", "lat", "lon"}:
        raise ValueError("Expected labeled time/lat/lon predictions")
    for dim in ("time", "lat", "lon"):
        if not predictions.get_index(dim).is_unique:
            raise ValueError(f"Duplicate {dim} coordinates")
        if set(predictions[dim].values) != set(grid[dim].values):
            raise ValueError(f"Prediction coordinates do not match test {dim}")
    ordered = predictions.sel(time=grid.time, lat=grid.lat, lon=grid.lon).transpose("time", "lat", "lon")
    values = ordered.values.reshape(-1)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Predictions must be finite and nonnegative")
    ids = expected_ids(grid)
    if not ids.is_unique:
        raise ValueError("Duplicate formatted IDs")
    frame = pd.DataFrame({"tp_mm_day": values}, index=ids)
    if template is not None:
        official = pd.read_csv(template, usecols=["id"], dtype={"id": str})["id"]
        if len(official) != len(ids) or not official.is_unique or not official.isin(ids).all():
            raise ValueError("Official template IDs do not match test grid")
        frame = frame.loc[official.to_numpy()]
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Never silently replace a previous candidate.
    frame.to_csv(destination, float_format="%.8f", mode="x")
    check = pd.read_csv(destination, dtype={"id": str})
    if list(check.columns) != ["id", "tp_mm_day"]:
        raise ValueError("Invalid CSV columns")
    if not np.array_equal(check.id.to_numpy(), frame.index.to_numpy()):
        raise ValueError("CSV ID roundtrip failed")
    if not np.allclose(check.tp_mm_day, frame.tp_mm_day, rtol=0, atol=5.1e-9):
        raise ValueError("CSV prediction roundtrip failed")
    return {"file": str(destination.resolve()), "rows": len(check),
            "columns": list(check.columns), "unique_ids": bool(check.id.is_unique),
            "first_id": check.id.iloc[0], "last_id": check.id.iloc[-1],
            "min_prediction": float(check.tp_mm_day.min()),
            "max_prediction": float(check.tp_mm_day.max()),
            "id_order": "official template" if template else "test NetCDF time, lat, lon; longitude varies fastest",
            "official_template_verified": template is not None, "uploaded": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, help="NetCDF with labeled tp_mm_day predictions")
    parser.add_argument("--baseline", action="store_true", help="Generate a 60-year climatology reference, not the ensemble")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--template", type=Path)
    args = parser.parse_args()
    if bool(args.predictions) == args.baseline:
        parser.error("Choose exactly one of --predictions or --baseline")
    template = args.template
    if template is None and (RAW / "sample_submission.csv").exists():
        template = RAW / "sample_submission.csv"
    with xr.open_dataset(RAW / "teste_features.nc") as grid:
        if args.baseline:
            with xr.open_dataset(RAW / "treino_tp.nc") as train:
                climatology = fit_climatology(train.tp.values, train.time.values, "2023-01-01", years=60)
            pred = xr.DataArray(climatology[month_number(grid.time.values)], dims=("time", "lat", "lon"),
                                coords={d: grid[d] for d in ("time", "lat", "lon")}, name="tp_mm_day")
            model = "clim_60y; reference baseline, NOT the best development ensemble"
        else:
            with xr.open_dataset(args.predictions) as dataset:
                pred = dataset.tp_mm_day.load()
            model = str(args.predictions)
        report = export_csv(pred, grid, args.output, template)
    report["model"] = model
    save_json(args.output.with_suffix(".json"), report)
    print(report)


if __name__ == "__main__":
    main()
