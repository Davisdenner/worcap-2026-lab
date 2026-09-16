"""Causal atmospheric memory; fixed small search and cross-fitted blend checks."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import xarray as xr
from sklearn.decomposition import PCA
from scipy.optimize import minimize

from .competition import CACHE, RAW, ROOT, REPORT, save_json, score
from .round2 import Features, target_origins
from .round3 import ART as OLD, YEARS, seasonal_design
from .submission import export_csv

ART = ROOT / "data/processed/round4"
OUT = REPORT / "round4"
CONFIGS = ("mean3", "lags3", "mean6trend")
PENALTIES = (.3, 3.)


def memory(z, origins, config):
    origins = np.asarray(origins)
    needed = 5 if config == "mean6trend" else 2
    if origins.min() < needed or origins.max() >= len(z):
        raise ValueError("Unavailable causal history")
    now = z[origins]
    if config == "mean3":
        extra = sum(z[origins-k] for k in range(3))/3
        return np.column_stack([now, extra])
    if config == "lags3":
        return np.column_stack([now, z[origins-1], z[origins-2]])
    if config == "mean6trend":
        extra = sum(z[origins-k] for k in range(6))/6
        return np.column_stack([now, extra, now-z[origins-2]])
    raise ValueError(config)


def predict(f, configs=CONFIGS, penalties=PENALTIES, final=False):
    coarse = np.load(OLD / "coarse_weather.npy", mmap_mode="r")
    idx, origins = f.idx, target_origins(f.year)
    means = np.stack([coarse[idx[idx % 12 == m]].mean(axis=0) for m in range(12)])
    train = coarse[idx] - means[idx % 12]
    scale = np.maximum(train.std(axis=0), 1e-8)
    pca = PCA(n_components=16, svd_solver="randomized", random_state=20260914)
    pca.fit(train/scale)
    pc_scale = np.maximum(pca.transform(train/scale).std(axis=0), 1e-8)
    # Transformation is pointwise; fitting never sees validation origins.
    take = np.arange(origins[-1]+1)
    z = pca.transform((coarse[take]-means[take % 12])/scale)/pc_scale
    base = f.climo[(origins+1) % 12]
    for config in configs:
        x = seasonal_design(memory(z, idx, config), idx)
        xv = seasonal_design(memory(z, origins, config), origins)
        xx = x.T @ x / len(x)
        predictions = {a: base.copy() for a in penalties}
        coefficients = {a: np.empty((x.shape[1], base.shape[1])) for a in penalties} if final else {}
        for start in range(0, base.shape[1], 5000):
            sl = slice(start, start+5000)
            y = f.tp[idx+1, sl] - f.climo[(idx+1) % 12, sl]
            xy = x.T @ y / len(x)
            for a in penalties:
                penalty = a*np.eye(x.shape[1])
                penalty[0, 0] = 0
                coef = np.linalg.solve(xx+penalty, xy)
                predictions[a][:, sl] = np.maximum(base[:, sl]+xv@coef, 0)
                if final:
                    coefficients[a][:, sl] = coef
        if final:
            joblib.dump(dict(pca=pca, monthly_means=means, scale=scale,
                             pc_scale=pc_scale, config=config, coefficients=coefficients),
                        ART / f"final_{config}.joblib")
        for a, pred in predictions.items():
            yield f"{config}_{a:g}", pred.reshape(24, 301, 261)


def evaluate():
    ART.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for year in YEARS:
        f = Features(year)
        truth = f.tp[target_origins(year)+1].reshape(24, 301, 261)
        reference = np.load(OLD / f"{year}_joint25_modes_seasonal.npy")
        old_modes = np.load(OLD / f"{year}_modes_0.3.npy")
        rows = [{"model": "submission03", **score(reference, truth)}]
        for name, pred in predict(f):
            np.save(ART / f"{year}_{name}.npy", pred)
            # Replace half or all of S03's 25% old-mode component.
            for weight in (.125, .25):
                blend = np.maximum(reference + weight*(pred-old_modes), 0)
                key = f"replace{weight:g}_{name}"
                row = {"model": key, **score(blend, truth)}
                rows.append(row)
                print(year, key, row["rmse"], flush=True)
        save_json(OUT / f"{year}.json", rows)


def candidate(year, name):
    reference = np.load(OLD / f"{year}_joint25_modes_seasonal.npy")
    if name == "submission03":
        return reference
    replacement, config, a = name.split("_")
    weight = float(replacement.removeprefix("replace"))
    pred = np.load(ART / f"{year}_{config}_{a}.npy")
    old_modes = np.load(OLD / f"{year}_modes_0.3.npy")
    return np.maximum(reference + weight*(pred-old_modes), 0)


def select():
    records = {year: json.loads((OUT / f"{year}.json").read_text()) for year in YEARS}
    refs = {year: rows[0] for year, rows in records.items()}
    ranking = []
    for name in [r["model"] for r in records[YEARS[0]]]:
        rows = [next(r for r in records[y] if r["model"] == name) for y in YEARS]
        ranking.append(dict(model=name, rmse=float(np.sqrt(np.mean([r["rmse"]**2 for r in rows]))),
                            second_year_rmse=float(np.sqrt(np.mean([r["year2_rmse"]**2 for r in rows]))),
                            folds_improved=sum(r["rmse"] < refs[y]["rmse"] for y, r in zip(YEARS, rows)),
                            years_improved=sum(r[k] < refs[y][k] for y, r in zip(YEARS, rows)
                                               for k in ("year1_rmse", "year2_rmse"))))
    ranking.sort(key=lambda r: r["rmse"])
    ref = next(r for r in ranking if r["model"] == "submission03")
    eligible = [r for r in ranking if r["rmse"] < ref["rmse"] and r["second_year_rmse"] < ref["second_year_rmse"]
                and r["folds_improved"] >= 3 and r["years_improved"] >= 6]
    selected = eligible[0]["model"] if eligible else "submission03"
    save_json(OUT / "selection.json", dict(selected=selected, ranking=ranking, holdout_evaluated=False,
              criterion="lower pooled and second-year RMSE; >=3/4 blocks and >=6/8 years improved",
              caveat="Development blocks reused for selection; not independent test"))
    print(json.dumps(dict(selected=selected, ranking=ranking), indent=2), flush=True)


def groups():
    """Three fixed latitude bands x four meteorological seasons, no learned cuts."""
    lat = np.arange(-60, 15.01, .25)
    bands = np.digitize(lat, [-30, -10])
    seasons = ((np.arange(24) % 12 + 1) % 12)//3
    return seasons[:, None, None]*3 + bands[None, :, None] + np.zeros((1, 1, 261), dtype=int)


def fit_weights(covariance):
    prior = np.array([.5, .25, .25])
    result = minimize(lambda w: w@covariance@w + .5*np.sum((w-prior)**2), prior,
                      jac=lambda w: 2*covariance@w + (w-prior), method="SLSQP",
                      bounds=[(.1, .7)]*3,
                      constraints=[dict(type="eq", fun=lambda w: w.sum()-1,
                                        jac=lambda w: np.ones(3))],
                      options=dict(ftol=1e-12, maxiter=100))
    if not result.success:
        raise RuntimeError(result.message)
    return result.x


def calibrate():
    choice = json.loads((OUT / "selection.json").read_text())
    name = choice["selected"]
    if not name.startswith("replace0.25_"):
        raise RuntimeError("Calibration requires the full 25% memory candidate")
    _, config, penalty = name.split("_")
    masks = groups()
    truth = np.load(CACHE / "tp.npy", mmap_mode="r")
    covariances, components = [], []
    for year in YEARS:
        p = np.stack([np.load(OLD / f"{year}_submission02.npy"),
                      np.load(ART / f"{year}_{config}_{penalty}.npy"),
                      np.load(OLD / f"{year}_seasonal_0.3.npy")]).astype(np.float64)
        error = p-truth[target_origins(year)+1]
        covariances.append(np.stack([error[:, masks == g]@error[:, masks == g].T/(masks == g).sum()
                                     for g in range(12)]))
        components.append(p)
    covariances = np.array(covariances)
    rows, weights = [], []
    for i, year in enumerate(YEARS):
        # Meta-calibration excludes this entire two-year block.
        w = np.stack([fit_weights(c) for c in np.delete(covariances, i, axis=0).mean(axis=0)])
        pred = np.sum(components[i]*w[masks].transpose(3, 0, 1, 2), axis=0)
        np.save(ART / f"{year}_calibrated.npy", pred)
        row = dict(year=year, **score(pred, truth[target_origins(year)+1]))
        rows.append(row)
        weights.append(w.tolist())
    selected_rows = [next(r for r in json.loads((OUT / f"{y}.json").read_text()) if r["model"] == name) for y in YEARS]
    improved = sum(r["rmse"] < old["rmse"] for r, old in zip(rows, selected_rows))
    years_improved = sum(r[k] < old[k] for r, old in zip(rows, selected_rows) for k in ("year1_rmse", "year2_rmse"))
    pooled = float(np.sqrt(np.mean([r["rmse"]**2 for r in rows])))
    second = float(np.sqrt(np.mean([r["year2_rmse"]**2 for r in rows])))
    baseline = next(r for r in choice["ranking"] if r["model"] == name)
    promote = pooled < baseline["rmse"] and second < baseline["second_year_rmse"] and improved >= 3 and years_improved >= 6
    report = dict(promoted=bool(promote), rmse=pooled, second_year_rmse=second, folds_improved=improved,
                  years_improved=years_improved, rows=rows, leave_block_out_weights=weights,
                  final_weights=np.stack([fit_weights(c) for c in covariances.mean(axis=0)]).tolist(),
                  component_order=["submission02", f"{config}_{penalty}", "seasonal_0.3"],
                  prior=[.5,.25,.25], penalty=.5, bounds=[.1,.7],
                  caveat="Retrospective leave-block-out meta-calibration, not forward validation. Base candidate selected on these same development blocks; 2021-2022 untouched.")
    save_json(OUT / "calibration.json", report)
    print(json.dumps(report, indent=2), flush=True)


def final():
    choice = json.loads((OUT / "selection.json").read_text())
    name = choice["selected"]
    if name == "submission03":
        raise RuntimeError("No qualified improvement; preserve S03")
    path = ROOT / "submissions/submission_04.csv"
    if path.exists():
        raise FileExistsError(path)
    replacement, config, penalty = name.split("_")
    weight = float(replacement.removeprefix("replace"))
    f = Features(2023, final=True)
    _, new = next(predict(f, (config,), (float(penalty),), final=True))
    # Reconstruct the old mode field from its saved model without overwriting it.
    model = joblib.load(OLD / "final_modes.joblib")
    origins = target_origins(2023)
    coarse = np.load(OLD / "coarse_weather.npy", mmap_mode="r")
    z = model["pca"].transform((coarse[origins]-model["monthly_means"][origins % 12])/model["feature_scale"])/model["pc_scale"]
    old = np.maximum(f.climo[(origins+1) % 12]+seasonal_design(z, origins)@model["coefficients"][.3], 0).reshape(24, 301, 261)
    with xr.open_dataset(OLD / "submission_03_predictions.nc") as ds:
        pred = np.maximum(ds.tp_mm_day.values+weight*(new-old), 0)
    calibration = json.loads((OUT / "calibration.json").read_text()) if (OUT / "calibration.json").exists() else None
    if calibration and calibration["promoted"]:
        from .round3 import seasonal_local
        with xr.open_dataset(ROOT / "data/processed/round2/submission_02_predictions.nc") as ds:
            previous = ds.tp_mm_day.values
        local = seasonal_local(f)["seasonal_0.3"]
        weights = np.asarray(calibration["final_weights"])[groups()].transpose(3, 0, 1, 2)
        pred = np.sum(np.stack([previous, new, local])*weights, axis=0)
    with xr.open_dataset(RAW / "teste_features.nc") as grid:
        da = xr.DataArray(pred, dims=("time", "lat", "lon"), coords={d: grid[d] for d in ("time", "lat", "lon")}, name="tp_mm_day")
        da.attrs.update(units="mm/day", model=name)
        da.to_netcdf(ART / "submission_04_predictions.nc")
        report = export_csv(da, grid, path, RAW / "sample_submission.csv")
    report.update(model=name, development_selection=choice, calibration=calibration, uploaded=False, public_score=None,
                  training_targets_end="2022-12", official_template_verified=True,
                  csv_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    save_json(path.with_suffix(".json"), report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("evaluate", "select", "calibrate", "final"))
    args = parser.parse_args()
    {"evaluate": evaluate, "select": select, "calibrate": calibrate, "final": final}[args.stage]()
