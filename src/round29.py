"""Round 29: fixed, forward-fitted model-family comparisons against S12."""
from __future__ import annotations

import os
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "4"

import argparse
import gc
import hashlib
import json
import time
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.utils.extmath import randomized_svd

from . import round20, round26
from .competition import CACHE, ROOT, REPORT, save_json
from .round2 import Features, target_origins

YEARS = (2009, 2011, 2013, 2015, 2017, 2019)
OUT = REPORT / "round29"
ART = ROOT / "data/processed/round29"
PROTOCOL = ROOT / "experiments/ROUND29.md"
GRID = 78_561
CELLS = np.arange(GRID)
NORTH = round26.NORTH
SEED = 20260929
RANKS = (4, 8, 16, 32)
ET = {
    "extratrees_64": dict(n_estimators=64, max_features=.5,
                          min_samples_leaf=8, max_depth=24),
    "extratrees_96": dict(n_estimators=96, max_features=.75,
                          min_samples_leaf=16, max_depth=24),
}
LGB = {
    "lightgbm_15": dict(n_estimators=300, num_leaves=15, max_depth=8,
                        learning_rate=.05, min_child_samples=100,
                        subsample=.8, subsample_freq=1, colsample_bytree=.8,
                        reg_alpha=0., reg_lambda=10.),
    "lightgbm_31": dict(n_estimators=400, num_leaves=31, max_depth=8,
                        learning_rate=.03, min_child_samples=200,
                        subsample=.8, subsample_freq=1, colsample_bytree=.8,
                        reg_alpha=.1, reg_lambda=20.),
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def locked() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    inputs = {str(year): {
        "s12": sha(round20.ART / f"{year}_s12.npy"),
        "pls16": sha(ROOT / f"data/processed/round9/{year}_pls16.npy"),
        "continental_transform": sha(round20.transform_paths(year)[0]),
        "tropical_transform": sha(round20.transform_paths(year)[1]),
    } for year in YEARS}
    obj = {"protocol_sha256": sha(PROTOCOL), "years": YEARS,
           "reference": "S12", "inputs_sha256": inputs,
           "historical_target_cache_sha256": sha(CACHE / "tp.npy"),
           "official_only": True, "no_2023_2024_targets": True,
           "no_submission": True}
    path = OUT / "protocol.json"
    normalized = json.loads(json.dumps(obj))
    if path.exists() and json.loads(path.read_text(encoding="utf-8")) != normalized:
        raise ValueError("Protocolo ou entradas congeladas mudaram")
    if not path.exists():
        save_json(path, obj)
    return obj


def _moments(actual: np.ndarray, s12: np.ndarray, alternative: np.ndarray) -> dict:
    y = np.asarray(actual, np.float64).ravel()
    a = np.asarray(s12, np.float64).ravel()
    b = np.asarray(alternative, np.float64).ravel()
    e, f = y-a, y-b
    blend = e-.1*(b-a)
    return {"n": int(y.size), "sse_s12": float(np.dot(e, e)),
            "sse_model": float(np.dot(f, f)),
            "sse_oracle": float(np.minimum(e*e, f*f).sum()),
            "sse_blend10": float(np.dot(blend, blend)),
            "sum_e12": float(e.sum()), "sum_emodel": float(f.sum()),
            "sum_cross": float(np.dot(e, f)),
            "sum_e12_sq": float(np.dot(e, e)),
            "sum_emodel_sq": float(np.dot(f, f))}


def _derived(m: dict) -> dict:
    n = m["n"]
    s = m["sse_s12"]
    a = m["sse_model"]
    v1 = m["sum_e12_sq"]/n-(m["sum_e12"]/n)**2
    v2 = m["sum_emodel_sq"]/n-(m["sum_emodel"]/n)**2
    cov = m["sum_cross"]/n-m["sum_e12"]*m["sum_emodel"]/n**2
    return {
        "n": n, "rmse_s12": float(np.sqrt(s/n)),
        "rmse_model": float(np.sqrt(a/n)),
        "rmse_oracle": float(np.sqrt(m["sse_oracle"]/n)),
        "rmse_blend10": float(np.sqrt(m["sse_blend10"]/n)),
        "gain_model_percent": float(100*(1-np.sqrt(a/s))),
        "gain_oracle_percent": float(100*(1-np.sqrt(m["sse_oracle"]/s))),
        "gain_blend10_percent": float(100*(1-np.sqrt(m["sse_blend10"]/s))),
        "residual_covariance": float(cov),
        "residual_correlation": float(cov/np.sqrt(v1*v2)),
    }


def _add(a: dict, b: dict) -> dict:
    return {key: a[key]+b[key] for key in a}


def evaluate_one(year: int, name: str, prediction: np.ndarray,
                 train_seconds: float, predict_seconds: float,
                 extra: dict | None = None) -> dict:
    # Preserve the immutable S12 reference byte-for-byte in its audit copy.
    dtype = np.float64 if name == "s12" else np.float32
    pred = np.asarray(prediction, dtype).reshape(24, GRID)
    if not np.isfinite(pred).all() or np.min(pred) < 0:
        raise ValueError(f"Previsão inválida: {name} {year}")
    path = ART / f"{year}_{name}.npy"
    if path.exists():
        np.testing.assert_array_equal(np.load(path), pred.reshape(24, 301, 261))
    else:
        np.save(path, pred.reshape(24, 301, 261))
    tp = np.load(CACHE / "tp.npy", mmap_mode="r").reshape(-1, GRID)
    truth = np.asarray(tp[target_origins(year)+1], np.float64)
    s12 = np.asarray(round20.reference(year).reshape(24, GRID), np.float64)
    regions = {"global": CELLS, "north": NORTH}
    lat = np.repeat(np.arange(-60, 15.01, .25), 261)
    for low, high in ((-60, -45), (-45, -30), (-30, -15), (-15, 0), (0, 15.01)):
        regions[f"lat_{low}_{high}"] = np.flatnonzero((lat >= low) & (lat < high))
    row = {
        "year_start": year, "model": name,
        "prediction_sha256": sha(path),
        "global_moments": _moments(truth, s12, pred),
        "global": _derived(_moments(truth, s12, pred)),
        "region_moments": {key: _moments(truth[:, cells], s12[:, cells], pred[:, cells])
                           for key, cells in regions.items() if key != "global"},
        "by_region": {key: _derived(_moments(truth[:, cells], s12[:, cells], pred[:, cells]))
                      for key, cells in regions.items() if key != "global"},
        "by_year": {str(year+k): _derived(_moments(truth[12*k:12*(k+1)],
                                                 s12[12*k:12*(k+1)],
                                                 pred[12*k:12*(k+1)]))
                    for k in (0, 1)},
        "train_seconds": float(train_seconds),
        "predict_seconds": float(predict_seconds),
        "extra": extra or {},
    }
    save_json(OUT / f"{year}_{name}.json", row)
    print("SCORE", year, name, "RMSE", round(row["global"]["rmse_model"], 6),
          "blend", round(row["global"]["gain_blend10_percent"], 4),
          "corr", round(row["global"]["residual_correlation"], 4), flush=True)
    return row


def _tabular_training(f: Features, global_train: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    samples = round20.nested_cells(f.idx)
    n = 768
    x = np.empty((len(f.idx)*n, 119), np.float32)
    y = np.empty(len(x), np.float32)
    for k, (origin, chosen) in enumerate(zip(f.idx, samples)):
        cells = chosen[:n]
        sl = slice(k*n, (k+1)*n)
        local = f.matrix(int(origin), cells, context=True)
        x[sl, :55] = local
        x[sl, 55:] = global_train[k]
        y[sl] = f.tp[origin+1, cells]-local[:, 4]
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Amostra tabular não finita")
    return x, y


def tabular() -> None:
    locked()
    from lightgbm import LGBMRegressor
    for year in YEARS:
        expected = [OUT / f"{year}_{name}.json" for name in (*ET, *LGB)]
        if all(path.exists() for path in expected):
            print("TABULAR EXISTENTE", year, flush=True)
            continue
        f = Features(year)
        global_train, global_valid = round20.context(f)
        started = time.perf_counter()
        xtrain, ytrain = _tabular_training(f, global_train)
        preparation_seconds = time.perf_counter()-started
        print("TABULAR FEATURES", year, xtrain.shape, round(preparation_seconds, 1), "s", flush=True)
        models = {}
        fit_time = {}
        for name, params in ET.items():
            started = time.perf_counter()
            model = ExtraTreesRegressor(**params, bootstrap=False,
                                        random_state=SEED, n_jobs=4)
            model.fit(xtrain, ytrain)
            models[name] = model
            fit_time[name] = time.perf_counter()-started
            print("FIT", year, name, round(fit_time[name], 1), "s", flush=True)
        for name, params in LGB.items():
            started = time.perf_counter()
            model = LGBMRegressor(**params, random_state=SEED, n_jobs=4,
                                  deterministic=True, force_col_wise=True,
                                  verbosity=-1)
            model.fit(xtrain, ytrain)
            models[name] = model
            fit_time[name] = time.perf_counter()-started
            print("FIT", year, name, round(fit_time[name], 1), "s", flush=True)
        del xtrain, ytrain
        gc.collect()
        predictions = {name: np.empty((24, GRID), np.float32) for name in models}
        times = {name: 0. for name in models}
        for slot, origin in enumerate(target_origins(year)):
            local = f.matrix(int(origin), CELLS, context=True)
            xv = np.empty((GRID, 119), np.float32)
            xv[:, :55] = local
            xv[:, 55:] = global_valid[slot]
            for name, model in models.items():
                started = time.perf_counter()
                predictions[name][slot] = np.maximum(
                    local[:, 4]+model.predict(xv), 0).astype(np.float32)
                times[name] += time.perf_counter()-started
            if slot % 6 == 5:
                print("PREDICT", year, slot+1, "/24", flush=True)
        for name in models:
            evaluate_one(year, name, predictions[name], fit_time[name], times[name],
                         {"preparation_seconds_shared": preparation_seconds,
                          "train_rows": int(len(f.idx)*768),
                          "input_features": 119})
        del f, global_train, global_valid, models, predictions
        gc.collect()


def _whitening(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = x.mean(axis=0)
    centered = x-mean
    eig, vec = np.linalg.eigh(centered.T@centered/len(x))
    matrix = (vec/np.sqrt(np.maximum(eig, 1e-8)))@vec.T
    return mean, matrix, centered@matrix


def _invsqrt(m: np.ndarray) -> np.ndarray:
    eig, vec = np.linalg.eigh(m)
    return (vec/np.sqrt(np.maximum(eig, 1e-10)))@vec.T


def _mode_overlap(new_modes: np.ndarray, pls_modes: np.ndarray) -> float:
    qn, _ = np.linalg.qr(new_modes.T)
    qp, _ = np.linalg.qr(pls_modes.T)
    return float(np.sum((qn.T@qp)**2)/min(qn.shape[1], qp.shape[1]))


def multivariate() -> None:
    locked()
    for year in YEARS:
        names = [f"rrr_{r}" for r in RANKS]+[f"cca_{r}" for r in RANKS]
        if all((OUT / f"{year}_{name}.json").exists() for name in names):
            print("MULTIVARIADO EXISTENTE", year, flush=True)
            continue
        f = Features(year)
        x, xv = round20.context(f)
        x = np.asarray(x, np.float64)
        xv = np.asarray(xv, np.float64)
        y = np.asarray(f.tp[f.idx+1], np.float32)-f.climo[(f.idx+1)%12]
        ymean = y.mean(axis=0, dtype=np.float64)
        yc = np.asarray(y, np.float64)-ymean
        clim_valid = f.climo[(target_origins(year)+1)%12].astype(np.float64)
        pls_model = joblib.load(round20.transform_paths(year)[0])
        pls_modes = np.asarray(pls_model["coefficients"][1:], np.float64)
        started = time.perf_counter()
        xmean, whitening, z = _whitening(x)
        zv = (xv-xmean)@whitening
        gram = z.T@z/len(z)
        b = np.linalg.solve(gram+.3*np.eye(z.shape[1]), z.T@yc/len(z))
        eig, u = np.linalg.eigh(b@b.T)
        u = u[:, ::-1]
        rrr_fit_seconds = time.perf_counter()-started
        for rank in RANKS:
            started = time.perf_counter()
            modes = u[:, :rank].T@b
            prediction = np.maximum(clim_valid+ymean+zv@u[:, :rank]@modes, 0).astype(np.float32)
            predict_seconds = time.perf_counter()-started
            evaluate_one(year, f"rrr_{rank}", prediction, rrr_fit_seconds,
                         predict_seconds, {"rank": rank, "ridge": .3,
                                           "mode_overlap_pls16": _mode_overlap(modes, pls_modes),
                                           "train_months": len(f.idx)})
        started = time.perf_counter()
        uu, ss, vt = randomized_svd(np.asarray(yc, np.float32), n_components=32,
                                    n_oversamples=8, n_iter=2, random_state=SEED)
        target_score = uu.astype(np.float64)*ss.astype(np.float64)
        target_scale = np.maximum(target_score.std(axis=0), 1e-8)
        xscale = np.maximum(x.std(axis=0), 1e-8)
        xs = (x-xmean)/xscale
        xvs = (xv-xmean)/xscale
        ys = target_score/target_scale
        cx = xs.T@xs/len(x)+.3*np.eye(xs.shape[1])
        cy = ys.T@ys/len(x)+.3*np.eye(ys.shape[1])
        cross = xs.T@ys/len(x)
        wx = _invsqrt(cx)
        wy = _invsqrt(cy)
        left, singular, _ = np.linalg.svd(wx@cross@wy, full_matrices=False)
        canonical = wx@left
        cca_fit_seconds = time.perf_counter()-started
        for rank in RANKS:
            started = time.perf_counter()
            t = xs@canonical[:, :rank]
            tv = xvs@canonical[:, :rank]
            decoder = np.linalg.solve(t.T@t/len(t)+.3*np.eye(rank),
                                      t.T@target_score/len(t))
            modes = decoder@vt.astype(np.float64)
            prediction = np.maximum(clim_valid+ymean+tv@decoder@vt, 0).astype(np.float32)
            predict_seconds = time.perf_counter()-started
            evaluate_one(year, f"cca_{rank}", prediction, cca_fit_seconds,
                         predict_seconds, {"rank": rank, "cca_ridge": .3,
                                           "decoder_ridge": .3,
                                           "canonical_correlation_sum": float(singular[:rank].sum()),
                                           "mode_overlap_pls16": _mode_overlap(modes, pls_modes),
                                           "train_months": len(f.idx)})
        del f, x, xv, y, yc, b, uu, ss, vt
        gc.collect()


def baseline() -> None:
    locked()
    for year in YEARS:
        row = OUT / f"{year}_s12.json"
        if row.exists():
            continue
        s12 = round20.reference(year)
        evaluate_one(year, "s12", s12, 0., 0., {"immutable_reference": True})
        pls = np.load(ROOT / f"data/processed/round9/{year}_pls16.npy")
        evaluate_one(year, "pls16_existing", pls, 0., 0., {"existing_control": True})


def summarize() -> None:
    locked()
    names = ["s12", "pls16_existing", *ET, *LGB,
             *[f"rrr_{r}" for r in RANKS], *[f"cca_{r}" for r in RANKS]]
    records = {}
    for name in names:
        paths = [OUT / f"{year}_{name}.json" for year in YEARS]
        if not all(p.exists() for p in paths):
            continue
        rows = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
        total = rows[0]["global_moments"]
        for row in rows[1:]:
            total = _add(total, row["global_moments"])
        overall = _derived(total)
        positive_blocks = sum(row["global"]["gain_model_percent"] > 0 for row in rows)
        positive_blend_blocks = sum(row["global"]["gain_blend10_percent"] > 0 for row in rows)
        positive_years = sum(val["gain_model_percent"] > 0 for row in rows
                             for val in row["by_year"].values())
        records[name] = {"overall": overall, "positive_blocks": positive_blocks,
                         "positive_blend_blocks": positive_blend_blocks,
                         "positive_years": positive_years,
                         "train_seconds": sum(row["train_seconds"] for row in rows),
                         "predict_seconds": sum(row["predict_seconds"] for row in rows),
                         "by_block": {str(row["year_start"]): row["global"] for row in rows},
                         "by_year": {key: val for row in rows for key, val in row["by_year"].items()},
                         "by_region": {key: _derived(_combine_region(rows, key))
                                       for key in rows[0]["by_region"]},
                         "mode_overlap_pls16_mean": float(np.mean([
                             row["extra"]["mode_overlap_pls16"] for row in rows]))
                         if "mode_overlap_pls16" in rows[0]["extra"] else None}
    save_json(OUT / "summary.json", records)


def _combine_region(rows: list[dict], region: str) -> dict:
    totals = rows[0]["region_moments"][region]
    for row in rows[1:]:
        totals = _add(totals, row["region_moments"][region])
    return totals


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("baseline", "tabular", "multivariate", "summarize"))
    stage = parser.parse_args().stage
    {"baseline": baseline, "tabular": tabular,
     "multivariate": multivariate, "summarize": summarize}[stage]()
