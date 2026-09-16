"""Spatial/temporal development experiments and reproducible submission 02.

All weather inputs are from M or earlier; targets are M+1. The 2021-2022
reserved period is never scored. Final fitting may use its training labels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

try:
    from .competition import (CACHE, PRED, RAW, REPORT, ROOT, VARIABLES, dates,
                             fit_climatology, save_json, score, training_pairs, write_results)
    from .submission import export_csv
except ImportError:
    from competition import (CACHE, PRED, RAW, REPORT, ROOT, VARIABLES, dates,
                            fit_climatology, save_json, score, training_pairs, write_results)
    from submission import export_csv

import joblib
import numpy as np
import pandas as pd
import xarray as xr
from scipy.ndimage import uniform_filter
from sklearn.ensemble import HistGradientBoostingRegressor

OUT = REPORT / "round2"
ART = ROOT / "data/processed/round2"
SPATIAL = [1, 2, 3, 4, 5, 8]
SIZES = [9, 25]
TREE_CONFIG = dict(learning_rate=.05, max_leaf_nodes=15, min_samples_leaf=100,
                   l2_regularization=10., early_stopping=False, random_state=20260914,
                   loss="squared_error", warm_start=True)


def target_origins(year):
    return (year - 1940) * 12 - 1 + np.arange(24)


def weather_row(train, test, origin):
    """Test position zero duplicates the last training weather month."""
    if origin < 0:
        raise ValueError("Unavailable weather history")
    if origin < len(train):
        return train[origin]
    position = origin - len(train) + 1
    if test is None or position >= len(test):
        raise ValueError("Requested unavailable weather month")
    return test[position]


class Features:
    def __init__(self, year, final=False):
        self.year = year
        self.times = dates()
        self.idx = training_pairs(self.times, f"{year}-01-01")
        self.tp = np.load(CACHE / "tp.npy", mmap_mode="r").reshape(len(self.times), -1)
        self.weather = [np.load(CACHE / f"{v}.npy", mmap_mode="r").reshape(len(self.times), -1)
                        for v in VARIABLES]
        self.test = [None] * len(VARIABLES)
        if final:
            with xr.open_dataset(RAW / "teste_features.nc") as ds:
                assert np.array_equal(ds.time_origem.values,
                                      pd.date_range("2022-12-01", periods=24, freq="MS").values)
                for j, v in enumerate(VARIABLES):
                    self.test[j] = ds[v].values.reshape(24, -1)
                    np.testing.assert_array_equal(self.test[j][0], self.weather[j][-1])
        self.climo = fit_climatology(self.tp, self.times, f"{year}-01-01", 60)
        self.means = np.empty((12, self.tp.shape[1], len(VARIABLES)), dtype=np.float32)
        for j, w in enumerate(self.weather):
            for m in range(12):
                self.means[m, :, j] = np.nanmean(w[self.idx[self.idx % 12 == m]], axis=0)
        np.nan_to_num(self.means, copy=False)
        lat, lon = np.meshgrid(np.arange(-60, 15.01, .25), np.arange(-90, -24.99, .25), indexing="ij")
        self.lat, self.lon = lat.ravel(), lon.ravel()

    def row(self, j, origin):
        return weather_row(self.weather[j], self.test[j], origin)

    def matrix(self, origin, cells, context=False):
        if context and origin < 2:
            raise ValueError("Context needs three observed months")
        x = np.empty((len(cells), 55 if context else 23), dtype=np.float32)
        m, target = origin % 12, (origin + 1) % 12
        x[:, 0], x[:, 1] = self.lat[cells], self.lon[cells]
        x[:, 2], x[:, 3] = np.sin(2*np.pi*target/12), np.cos(2*np.pi*target/12)
        x[:, 4] = self.climo[target, cells]
        full_anomalies = {}
        for j in range(9):
            raw = self.row(j, origin)
            anomaly = raw - self.means[m, :, j]
            x[:, 5+j], x[:, 14+j] = raw[cells], anomaly[cells]
            if context:
                previous = self.row(j, origin-1)[cells] - self.means[(origin-1) % 12, cells, j]
                older = self.row(j, origin-2)[cells] - self.means[(origin-2) % 12, cells, j]
                x[:, 23+j] = (anomaly[cells] + previous + older)/3
                x[:, 32+j] = anomaly[cells] - previous
                if j in SPATIAL:
                    full_anomalies[j] = anomaly.reshape(301, 261)
        if context:
            k = 41
            for j in SPATIAL:
                for size in SIZES:
                    # Spatial-only filter: no averaging along the time axis.
                    x[:, k] = uniform_filter(full_anomalies[j], size=size, mode="nearest").ravel()[cells]
                    k += 1
            x[:, 53] = x[:, 7] * x[:, 9]   # specific humidity * u wind
            x[:, 54] = x[:, 7] * x[:, 10]  # specific humidity * v wind
        if not np.isfinite(x).all():
            raise ValueError("Nonfinite atmospheric features")
        return x


def trees(features, context, iterations=(150,), final=False):
    rng = np.random.default_rng(20260914)
    n = 768
    x = np.empty((len(features.idx)*n, 55 if context else 23), dtype=np.float32)
    y = np.empty(len(x), dtype=np.float32)
    for k, origin in enumerate(features.idx):
        cells = rng.choice(features.tp.shape[1], n, replace=False)
        sl = slice(k*n, (k+1)*n)
        x[sl] = features.matrix(origin, cells, context)
        y[sl] = features.tp[origin+1, cells] - x[sl, 4]
    model = HistGradientBoostingRegressor(max_iter=iterations[0], **TREE_CONFIG)
    cells = np.arange(features.tp.shape[1])
    results = {}
    for iterations_count in iterations:
        started = time.monotonic()
        model.set_params(max_iter=iterations_count).fit(x, y)
        pred = np.empty((24, 301, 261), dtype=np.float32)
        for k, origin in enumerate(target_origins(features.year)):
            v = features.matrix(origin, cells, context)
            pred[k] = np.maximum(v[:, 4] + model.predict(v), 0).reshape(301, 261)
        name = f"context_{iterations_count}" if context else "local_150"
        results[name] = pred
        print(features.year, name, f"fit+prediction {time.monotonic()-started:.0f}s", flush=True)
        if final:
            joblib.dump(model, ART / f"final_{name}.joblib")
    return results


def ridge(features):
    idx = features.idx
    origins = target_origins(features.year)
    base = features.climo[(origins+1) % 12].reshape(24, 301, 261)
    pred = base.copy()
    for begin in range(0, 301, 19):
        end = min(begin+19, 301)
        sl = slice(begin*261, end*261)
        n = (end-begin)*261
        x = np.empty((len(idx), n, 9), dtype=np.float32)
        xv = np.empty((24, n, 9), dtype=np.float32)
        for j, w in enumerate(features.weather):
            means = features.means[:, sl, j]
            train = w[idx, sl] - means[idx % 12]
            valid = np.stack([features.row(j, o)[sl] for o in origins]) - means[origins % 12]
            scale = np.nanstd(train, axis=0)
            scale = np.where(np.isfinite(scale) & (scale > 1e-8), scale, 1)
            x[:, :, j], xv[:, :, j] = np.nan_to_num(train/scale), np.nan_to_num(valid/scale)
        y = features.tp[idx+1, sl] - features.climo[(idx+1) % 12, sl]
        xm, ym = x.mean(axis=0), y.mean(axis=0)
        x -= xm
        xv -= xm
        y -= ym
        xx = np.einsum("tpi,tpj->pij", x, x, optimize=True)/len(idx)
        xy = np.einsum("tpi,tp->pi", x, y, optimize=True)/len(idx)
        coef = np.linalg.solve(xx + .1*np.eye(9, dtype=np.float32)[None], xy[..., None])[..., 0]
        correction = np.einsum("tpi,pi->tp", xv, coef) + ym
        pred[:, begin:end] = np.maximum(base[:, begin:end] + correction.reshape(24, end-begin, 261), 0)
    return pred


def previous_ensemble(features):
    year = features.year
    path = PRED / f"dev_{year}_{year+1}_half_trees_half_prior.npy"
    if path.exists():
        return np.load(path)
    local = trees(features, False)["local_150"]
    linear = ridge(features)
    base = features.climo[(target_origins(year)+1) % 12].reshape(24, 301, 261)
    return .5*local + .25*linear + .25*base


def evaluate(years):
    OUT.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    for year in years:
        if year not in (2013, 2015, 2017, 2019):
            raise ValueError("Only registered development folds are permitted")
        print("Preparing", year, flush=True)
        f = Features(year)
        origins = target_origins(year)
        truth = f.tp[origins+1].reshape(24, 301, 261)
        base = f.climo[(origins+1) % 12].reshape(24, 301, 261)
        legacy = previous_ensemble(f)
        predictions = {"clim_60y": base, "previous_ensemble": legacy}
        predictions.update(trees(f, True, (150, 300)))
        for n in (150, 300):
            predictions[f"blend_context_{n}"] = .5*predictions[f"context_{n}"] + .5*legacy
        rows = []
        for name, pred in predictions.items():
            rows.append({"fold": str(year), "model": name, **score(pred, truth)})
            np.save(ART / f"{year}_{name}.npy", pred)
            print(year, name, rows[-1]["rmse"], "second year", rows[-1]["year2_rmse"], flush=True)
        write_results(OUT / f"{year}.json", rows)


def select():
    years = [2013, 2015, 2017, 2019]
    rows = [row for year in years for row in json.loads((OUT / f"{year}.json").read_text())]
    models = sorted(set(r["model"] for r in rows))
    ranking = []
    for model in models:
        records = [r for r in rows if r["model"] == model]
        ranking.append({"model": model, "rmse": float(np.sqrt(np.mean([r["rmse"]**2 for r in records]))),
                        "second_year_rmse": float(np.sqrt(np.mean([r["year2_rmse"]**2 for r in records])))})
    ranking.sort(key=lambda r: r["rmse"])
    selected = ranking[0]["model"]
    save_json(OUT / "selection.json", {"selected": selected, "ranking": ranking,
              "folds": years, "criterion": "pooled full-grid RMSE of four development folds",
              "holdout_2021_2022_evaluated": False})
    write_results(OUT / "all_results.json", rows)
    lines = ["# Segunda submissão: seleção local", "",
             "RMSE em mm/dia, grade completa. Período reservado 2021–2022 não avaliado.", "",
             "| Modelo | 2013–14 | 2015–16 | 2017–18 | 2019–20 | Agrupado | Segundos anos |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for rank in ranking:
        metrics = [next(r["rmse"] for r in rows if r["model"] == rank["model"] and r["fold"] == str(y)) for y in years]
        numbers = " | ".join(f"{m:.6f}" for m in metrics + [rank["rmse"], rank["second_year_rmse"]])
        lines.append(f"| {rank['model']} | {numbers} |")
    lines += ["", f"Selecionado: **{selected}**.", "",
              "São resultados de desenvolvimento, utilizados para a seleção; não são scores do Kaggle.",
              "Os atributos de contexto usam média e variação de anomalias de três meses, médias espaciais",
              "em janelas de 9×9 e 25×25 células e produtos de umidade específica por vento.",
              "As transformações e os modelos são ajustados antes de cada bloco; nenhum alvo do bloco entra como atributo.",
              "As árvores mantêm a mesma configuração da rodada anterior, comparando 150 e 300 iterações.",
              "`blend_context` combina 50% do novo modelo e 50% do ensemble anterior.", ""]
    (OUT / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines), flush=True)


def verify():
    """Check the shared final-fitting implementation against saved round-1 outputs."""
    f = Features(2017)
    actual = {"trees_150": trees(f, False)["local_150"], "ridge_0.1_clim_60y": ridge(f)}
    results = {}
    for name, pred in actual.items():
        expected = np.load(PRED / f"dev_2017_2018_{name}.npy")
        results[name] = {"max_absolute_difference": float(np.max(np.abs(pred-expected)))}
        np.testing.assert_allclose(pred, expected, rtol=1e-6, atol=1e-5)
    save_json(OUT / "reproduction_check.json", results)
    print("ROUND-1 REPRODUCTION PASS", results, flush=True)


def final():
    selection = json.loads((OUT / "selection.json").read_text())
    name = selection["selected"]
    ART.mkdir(parents=True, exist_ok=True)
    csv_path = ROOT / "submissions/submission_02.csv"
    if csv_path.exists():
        raise FileExistsError("submission_02.csv already exists; refusing overwrite")
    f = Features(2023, final=True)
    base = f.climo[(target_origins(2023)+1) % 12].reshape(24, 301, 261)
    np.savez_compressed(ART / "final_preprocessing.npz", means=f.means, climatology=f.climo)
    if name == "clim_60y":
        pred = base
    else:
        if name == "previous_ensemble" or name.startswith("blend_"):
            legacy = .5*trees(f, False, final=True)["local_150"] + .25*ridge(f) + .25*base
        if name == "previous_ensemble":
            pred = legacy
        else:
            n = int(name.rsplit("_", 1)[1])
            # Repeat the same warm-start schedule used during development.
            schedule = (150, 300) if n == 300 else (150,)
            context = trees(f, True, schedule, final=True)[f"context_{n}"]
            pred = .5*context + .5*legacy if name.startswith("blend_") else context
    with xr.open_dataset(RAW / "teste_features.nc") as grid:
        da = xr.DataArray(pred, dims=("time", "lat", "lon"),
                          coords={d: grid[d] for d in ("time", "lat", "lon")}, name="tp_mm_day")
        da.attrs.update(units="mm/day", model=name)
        nc_path = ART / "submission_02_predictions.nc"
        da.to_netcdf(nc_path)
        with xr.open_dataset(nc_path) as check:
            np.testing.assert_array_equal(check.tp_mm_day.values, pred)
        # The first baseline's IDs have already been accepted by Kaggle.
        template = RAW / "sample_submission.csv"
        if not template.exists():
            template = ROOT / "submissions/climatologia_60anos.csv"
        report = export_csv(da, grid, csv_path, template)
    report.update(model=name, trained_target_last_month="2022-12", training_input_last_month="2022-11",
                  test_weather_origin_first="2022-12", test_weather_origin_last="2024-11",
                  id_reference="first submission accepted by Kaggle" if template.name == "climatologia_60anos.csv" else "official sample",
                  official_template_verified=template.name == "sample_submission.csv",
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  tree_parameters=TREE_CONFIG, samples_per_month=768,
                  runtime_threads={key: os.environ.get(key) for key in
                                   ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")},
                  train_input_start="1981-01", baseline_years=60,
                  development_selection=selection, public_score=None, uploaded=False)
    report["id_order"] = report["id_reference"]
    report["csv_sha256"] = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    save_json(csv_path.with_suffix(".json"), report)
    print(report, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["evaluate", "select", "verify", "final"])
    parser.add_argument("--years", nargs="+", type=int, default=[2017, 2019])
    args = parser.parse_args()
    if args.stage == "evaluate":
        evaluate(args.years)
    elif args.stage == "select":
        select()
    elif args.stage == "verify":
        verify()
    else:
        final()
