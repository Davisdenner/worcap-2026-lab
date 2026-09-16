"""One budgeted nonlinear atmospheric experiment; no reserved-period scoring."""
from __future__ import annotations

import json
import time

# Import first: competition sets the native thread budget before numpy/sklearn.
from competition import (CACHE, FOLDS, PRED, REPORT, VARIABLES, dates,
                         fit_climatology, month_number, save_json, score,
                         training_pairs, write_results)
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor


def run():
    started = time.monotonic()
    times = dates()
    tp = np.load(CACHE / "tp.npy", mmap_mode="r").reshape(len(times), -1)
    atmosphere = [np.load(CACHE / f"{v}.npy", mmap_mode="r").reshape(len(times), -1)
                  for v in VARIABLES]
    lat, lon = np.meshgrid(np.arange(-60, 15.01, .25), np.arange(-90, -24.99, .25), indexing="ij")
    lat, lon = lat.ravel(), lon.ravel()
    selected = json.loads((REPORT / "baseline_selection.json").read_text())["selected"]
    years = None if selected == "clim_all" else int(selected[5:-1])
    config = {"learning_rate": 0.05, "max_iter": 150, "max_leaf_nodes": 15,
              "min_samples_leaf": 100, "l2_regularization": 10.0,
              "early_stopping": False, "random_state": 20260914,
              "loss": "squared_error"}
    results = []
    for fold, year in FOLDS.items():
        idx = training_pairs(times, f"{year}-01-01")
        valid_idx = np.flatnonzero((times >= f"{year}-01-01") & (times < f"{year+2}-01-01"))
        climo = fit_climatology(tp, times, f"{year}-01-01", years)
        feature_means = np.empty((12, tp.shape[1], len(VARIABLES)), dtype=np.float32)
        for j, data in enumerate(atmosphere):
            for m in range(12):
                feature_means[m, :, j] = np.nanmean(data[idx[month_number(times[idx]) == m]], axis=0)
        np.nan_to_num(feature_means, copy=False)

        def make_features(origin, cells):
            target_month = times[origin + 1].month - 1
            origin_month = times[origin].month - 1
            x = np.empty((len(cells), 5 + 2 * len(VARIABLES)), dtype=np.float32)
            x[:, 0], x[:, 1] = lat[cells], lon[cells]
            x[:, 2] = np.sin(2 * np.pi * target_month / 12)
            x[:, 3] = np.cos(2 * np.pi * target_month / 12)
            x[:, 4] = climo[target_month, cells]
            for j, data in enumerate(atmosphere):
                raw = data[origin, cells]
                mean = feature_means[origin_month, cells, j]
                raw = np.where(np.isfinite(raw), raw, mean)
                x[:, 5 + j] = raw
                x[:, 5 + len(VARIABLES) + j] = raw - mean
            return x

        # Uniform spatial sampling at EVERY training month: sample count is not
        # interpreted as independent climate realizations. Score the full grid.
        samples_per_month = 768
        rng = np.random.default_rng(20260914)
        x = np.empty((len(idx) * samples_per_month, 23), dtype=np.float32)
        y = np.empty(len(x), dtype=np.float32)
        for k, origin in enumerate(idx):
            cells = rng.choice(tp.shape[1], samples_per_month, replace=False)
            sl = slice(k * samples_per_month, (k + 1) * samples_per_month)
            x[sl] = make_features(origin, cells)
            y[sl] = tp[origin + 1, cells] - x[sl, 4]
        print(f"{fold} fitting trees on {len(x):,} rows / {len(idx)} months", flush=True)
        model = HistGradientBoostingRegressor(**config).fit(x, y)
        del x, y
        pred = np.empty((24, 301, 261), dtype=np.float32)
        cells = np.arange(tp.shape[1])
        for k, target in enumerate(valid_idx):
            x = make_features(target - 1, cells)
            pred[k] = np.maximum(x[:, 4] + model.predict(x), 0).reshape(301, 261)
            if (k + 1) % 6 == 0:
                print(f"{fold} predicted {k+1}/24 months; elapsed {time.monotonic()-started:.0f}s", flush=True)
        name = "trees_150"
        results.append({"fold": fold, "model": name, **score(pred, tp[valid_idx].reshape(24, 301, 261))})
        np.save(PRED / f"{fold}_{name}.npy", pred)
        prior = np.load(PRED / f"{fold}_half_ridge_0.1_{selected}.npy")
        combo = (prior + pred) / 2
        results.append({"fold": fold, "model": "half_trees_half_prior",
                        **score(combo, tp[valid_idx].reshape(24, 301, 261))})
        np.save(PRED / f"{fold}_half_trees_half_prior.npy", combo)
        print(results[-2:], flush=True)
    write_results(REPORT / "trees.json", results)
    save_json(REPORT / "trees_config.json", {"parameters": config, "baseline": selected,
              "samples_per_month": samples_per_month, "train_start": "1981-01-01",
              "features": ["lat", "lon", "target_month_sin", "target_month_cos", "climatology"] +
                          VARIABLES + [f"{v}_monthly_anomaly" for v in VARIABLES],
              "elapsed_seconds": time.monotonic() - started, "holdout_evaluated": False})


if __name__ == "__main__":
    run()
