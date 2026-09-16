"""Round 3: broad atmospheric modes and seasonally varying local regression."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

try:
    from .round2 import Features, target_origins
    from .competition import CACHE, RAW, ROOT, REPORT, VARIABLES, save_json, score, write_results
    from .submission import export_csv
except ImportError:
    from round2 import Features, target_origins
    from competition import CACHE, RAW, ROOT, REPORT, VARIABLES, save_json, score, write_results
    from submission import export_csv

import joblib
import numpy as np
import xarray as xr
from scipy.ndimage import uniform_filter
from sklearn.decomposition import PCA

OUT = REPORT / "round3"
ART = ROOT / "data/processed/round3"
YEARS = (2013, 2015, 2017, 2019)
PENALTIES = (.3, 3.)


def seasonal_mask(origins, target_month, radius=2):
    months = (np.asarray(origins)+1) % 12
    distance = np.abs(months-target_month)
    return np.minimum(distance, 12-distance) <= radius


def seasonal_design(scores, origins):
    angle = 2*np.pi*((np.asarray(origins)+1) % 12)/12
    s, c = np.sin(angle)[:, None], np.cos(angle)[:, None]
    return np.column_stack([np.ones(len(scores)), s, c, scores, scores*s, scores*c])


def prepare():
    """Pure per-month spatial filtering; no statistics fit on future dates."""
    ART.mkdir(parents=True, exist_ok=True)
    arrays = []
    with xr.open_dataset(RAW / "teste_features.nc") as test:
        for name in VARIABLES:
            train = np.load(CACHE / f"{name}.npy", mmap_mode="r")
            pieces = []
            for start in range(0, len(train), 63):
                block = np.asarray(train[start:start+63])
                pieces.append(uniform_filter(block, size=(1, 9, 9), mode="nearest")[:, ::8, ::8].reshape(len(block), -1))
            values = test[name].values
            np.testing.assert_array_equal(values[0], train[-1])
            pieces.append(uniform_filter(values[1:], size=(1, 9, 9), mode="nearest")[:, ::8, ::8].reshape(23, -1))
            arrays.append(np.concatenate(pieces))
            print("Coarse fields", name, flush=True)
    np.save(ART / "coarse_weather.npy", np.concatenate(arrays, axis=1))
    save_json(ART / "coarse_metadata.json", {"first_origin": "1940-01", "last_origin": "2024-11",
              "spatial_kernel": [9, 9], "stride": 8, "variables": VARIABLES,
              "uses_precipitation": False, "future_fitted_statistics": False})


def modes(features, final=False):
    coarse = np.load(ART / "coarse_weather.npy", mmap_mode="r")
    idx, origins = features.idx, target_origins(features.year)
    means = np.stack([coarse[idx[idx % 12 == m]].mean(axis=0) for m in range(12)])
    train = coarse[idx] - means[idx % 12]
    valid = coarse[origins] - means[origins % 12]
    scale = train.std(axis=0)
    scale = np.where(scale > 1e-8, scale, 1)
    train, valid = train/scale, valid/scale
    pca = PCA(n_components=16, svd_solver="randomized", random_state=20260914)
    pca.fit(train)
    z = pca.transform(train)
    zvalid = pca.transform(valid)
    pc_scale = z.std(axis=0)
    z, zvalid = z/pc_scale, zvalid/pc_scale
    x, xv = seasonal_design(z, idx), seasonal_design(zvalid, origins)
    xx = x.T @ x / len(x)
    base = features.climo[(origins+1) % 12]
    predictions = {a: base.copy() for a in PENALTIES}
    coefficients = {a: np.empty((x.shape[1], base.shape[1])) for a in PENALTIES} if final else None
    for begin in range(0, base.shape[1], 5000):
        sl = slice(begin, min(begin+5000, base.shape[1]))
        y = features.tp[idx+1, sl] - features.climo[(idx+1) % 12, sl]
        xy = x.T @ y / len(x)
        for a in PENALTIES:
            penalty = np.eye(x.shape[1])*a
            penalty[0, 0] = 0
            coef = np.linalg.solve(xx + penalty, xy)
            predictions[a][:, sl] = np.maximum(base[:, sl] + xv @ coef, 0)
            if final:
                coefficients[a][:, sl] = coef
    if final:
        joblib.dump({"pca": pca, "monthly_means": means, "feature_scale": scale,
                     "pc_scale": pc_scale, "coefficients": coefficients}, ART / "final_modes.joblib")
    print(features.year, "PCA variance fraction", float(pca.explained_variance_ratio_.sum()), flush=True)
    return {f"modes_{a:g}": p.reshape(24, 301, 261) for a, p in predictions.items()}


def seasonal_local(features):
    idx, origins = features.idx, target_origins(features.year)
    base = features.climo[(origins+1) % 12].reshape(24, 301, 261)
    predictions = {a: base.copy() for a in PENALTIES}
    for begin in range(0, 301, 19):
        end = min(begin+19, 301)
        sl = slice(begin*261, end*261)
        cells = (end-begin)*261
        xall = np.empty((len(idx), cells, 9), dtype=np.float32)
        vall = np.empty((24, cells, 9), dtype=np.float32)
        for j, w in enumerate(features.weather):
            mean = features.means[:, sl, j]
            xall[:, :, j] = w[idx, sl] - mean[idx % 12]
            vall[:, :, j] = np.stack([features.row(j, o)[sl] for o in origins]) - mean[origins % 12]
        yall = features.tp[idx+1, sl] - features.climo[(idx+1) % 12, sl]
        for month in range(12):
            use = seasonal_mask(idx, month)
            take = np.flatnonzero((origins+1) % 12 == month)
            x, xv, y = xall[use].copy(), vall[take].copy(), yall[use].copy()
            scale = x.std(axis=0)
            scale = np.where(scale > 1e-8, scale, 1)
            x, xv = x/scale, xv/scale
            xm, ym = x.mean(axis=0), y.mean(axis=0)
            x -= xm
            xv -= xm
            y -= ym
            xx = np.einsum("tpi,tpj->pij", x, x, optimize=True)/len(x)
            xy = np.einsum("tpi,tp->pi", x, y, optimize=True)/len(x)
            for a in PENALTIES:
                coef = np.linalg.solve(xx + a*np.eye(9, dtype=np.float32)[None], xy[..., None])[..., 0]
                correction = np.einsum("tpi,pi->tp", xv, coef) + ym
                predictions[a][take, begin:end] = np.maximum(base[take, begin:end] + correction.reshape(len(take), end-begin, 261), 0)
        if end % 57 == 0 or end == 301:
            print(features.year, "seasonal latitude rows", end, "/301", flush=True)
    return {f"seasonal_{a:g}": p for a, p in predictions.items()}


def evaluate(years):
    OUT.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    for year in years:
        if year not in YEARS:
            raise ValueError("Reserved/test years must not be evaluated")
        start = time.monotonic()
        f = Features(year)
        truth = f.tp[target_origins(year)+1].reshape(24, 301, 261)
        previous = np.load(ROOT / f"data/processed/round2/{year}_blend_context_300.npy")
        predictions = {"submission02": previous}
        new = modes(f)
        new.update(seasonal_local(f))
        predictions.update(new)
        for name, p in new.items():
            for weight in (.25, .5):
                predictions[f"blend{int(weight*100)}_{name}"] = (1-weight)*previous + weight*p
        rows = []
        for name, p in predictions.items():
            row = {"fold": str(year), "model": name, **score(p, truth)}
            rows.append(row)
            np.save(ART / f"{year}_{name}.npy", p)
            print(year, name, row["rmse"], "second year", row["year2_rmse"], flush=True)
        write_results(OUT / f"{year}.json", rows)
        print(year, "elapsed", round(time.monotonic()-start), "s", flush=True)


def select():
    # One exploratory combination motivated by complementary family errors.
    tp = np.load(CACHE / "tp.npy", mmap_mode="r")
    for year in YEARS:
        records = json.loads((OUT / f"{year}.json").read_text())
        name = "joint25_modes_seasonal"
        records = [r for r in records if r["model"] != name]
        previous = np.load(ART / f"{year}_submission02.npy")
        large = np.load(ART / f"{year}_modes_0.3.npy")
        local = np.load(ART / f"{year}_seasonal_0.3.npy")
        pred = .5*previous + .25*large + .25*local
        records.append({"fold": str(year), "model": name,
                        **score(pred, tp[target_origins(year)+1])})
        np.save(ART / f"{year}_{name}.npy", pred)
        write_results(OUT / f"{year}.json", records)
    rows = [r for year in YEARS for r in json.loads((OUT / f"{year}.json").read_text())]
    ref = {r["fold"]: r for r in rows if r["model"] == "submission02"}
    ranking = []
    for name in sorted(set(r["model"] for r in rows)):
        records = [r for r in rows if r["model"] == name]
        ranking.append({"model": name, "rmse": float(np.sqrt(np.mean([r["rmse"]**2 for r in records]))),
                        "second_year_rmse": float(np.sqrt(np.mean([r["year2_rmse"]**2 for r in records]))),
                        "folds_improved": sum(r["rmse"] < ref[r["fold"]]["rmse"] for r in records)})
    ranking.sort(key=lambda r: r["rmse"])
    old = next(r for r in ranking if r["model"] == "submission02")
    eligible = [r for r in ranking if r["rmse"] < old["rmse"] and r["folds_improved"] >= 3
                and r["second_year_rmse"] < old["second_year_rmse"]]
    selected = eligible[0]["model"] if eligible else "submission02"
    save_json(OUT / "selection.json", {"selected": selected, "ranking": ranking,
              "criterion": "lower pooled RMSE, improvement in at least 3/4 folds and pooled second years",
              "holdout_evaluated": False, "folds": list(YEARS)})
    write_results(OUT / "all_results.json", rows)
    lines = ["# Terceira rodada: validação histórica", "",
             "RMSE em mm/dia, 96 meses na grade completa. 2021–2022 não foi avaliado.", "",
             "| Modelo | Agrupado | Segundos anos | Blocos melhores que S02 |",
             "| --- | ---: | ---: | ---: |"]
    lines += [f"| {r['model']} | {r['rmse']:.6f} | {r['second_year_rmse']:.6f} | {r['folds_improved']}/4 |" for r in ranking]
    lines += ["", f"Selecionado: **{selected}**.", "",
              "Resultados usados para seleção, não um teste independente nem previsão do score público.",
              "`modes`: 16 componentes principais de campos atmosféricos regionais e interações sazonais.",
              "`seasonal`: regressão local ajustada em janelas circulares de cinco meses do calendário.",
              "`blend25` e `blend50`: pesos de 25% e 50% do modelo novo, com o restante da submissão 02.",
              "`joint25`: combinação exploratória de 50% S02 + 25% modos (0,3) + 25% sazonal (0,3)."]
    (OUT / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines), flush=True)


def final():
    choice = json.loads((OUT / "selection.json").read_text())
    name = choice["selected"]
    if name == "submission02":
        raise RuntimeError("No qualifying improvement: do not create a duplicate submission")
    destination = ROOT / "submissions/submission_03.csv"
    if destination.exists():
        raise FileExistsError(destination)
    f = Features(2023, final=True)
    with xr.open_dataset(ROOT / "data/processed/round2/submission_02_predictions.nc") as ds:
        previous = ds.tp_mm_day.values
    if name == "joint25_modes_seasonal":
        pred = .5*previous + .25*modes(f, final=True)["modes_0.3"] + .25*seasonal_local(f)["seasonal_0.3"]
    else:
        family = name.split("_", 1)[1] if name.startswith("blend") else name
        new = modes(f, final=True) if family.startswith("modes") else seasonal_local(f)
        pred = new[family]
        if name.startswith("blend"):
            weight = int(name.split("_", 1)[0][5:])/100
            pred = (1-weight)*previous + weight*pred
    with xr.open_dataset(RAW / "teste_features.nc") as grid:
        da = xr.DataArray(pred, dims=("time", "lat", "lon"),
                          coords={d: grid[d] for d in ("time", "lat", "lon")}, name="tp_mm_day")
        da.attrs.update(units="mm/day", model=name)
        da.to_netcdf(ART / "submission_03_predictions.nc")
        template = RAW / "sample_submission.csv"
        if not template.exists():
            template = ROOT / "submissions/submission_02.csv"
        report = export_csv(da, grid, destination, template)
    report.update(model=name, development_selection=choice,
                  id_order="official sample_submission.csv" if template.name == "sample_submission.csv" else "same as accepted submission_02.csv",
                  official_template_verified=template.name == "sample_submission.csv",
                  training_targets_end="2022-12", public_score=None,
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  csv_sha256=hashlib.sha256(destination.read_bytes()).hexdigest())
    save_json(destination.with_suffix(".json"), report)
    print(report, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["prepare", "evaluate", "select", "final"])
    parser.add_argument("--years", nargs="+", type=int, default=list(YEARS))
    args = parser.parse_args()
    if args.stage == "evaluate":
        evaluate(args.years)
    else:
        {"prepare": prepare, "select": select, "final": final}[args.stage]()
