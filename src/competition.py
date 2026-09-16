"""Reproducible WORCAP audit, temporal baselines and local atmospheric ridge.

Run from the repository root with the project Python environment.
Only official data/raw inputs are used. Validation targets stop at 2020.
"""
from __future__ import annotations

import argparse
import csv
import json
import importlib.metadata
import os
import time
from pathlib import Path

# Keep small matrix operations from oversubscribing this laptop.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")

import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
CACHE = ROOT / "data/processed/official"
REPORT = ROOT / "reports/competition"
PRED = ROOT / "data/processed/validation"
VARIABLES = ["t2", "cloud_cover", "shum_850", "surface_pressure", "u_850",
             "v_850", "temperature_850", "rel_hum_850", "geopotential_850"]
FOLDS = {"dev_2017_2018": 2017, "dev_2019_2020": 2019}


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def dates():
    return pd.date_range("1940-01-01", "2022-12-01", freq="MS")


def month_number(values):
    return pd.DatetimeIndex(values).month.to_numpy() - 1


def fit_climatology(values, times, cutoff, years=None):
    """All fitting observations strictly precede the first forecast target."""
    times = pd.DatetimeIndex(times)
    use = times < pd.Timestamp(cutoff)
    if years is not None:
        use &= times >= pd.Timestamp(cutoff) - pd.DateOffset(years=years)
    months = month_number(times)
    return np.stack([np.mean(values[use & (months == m)], axis=0, dtype=np.float64)
                     for m in range(12)]).astype(np.float32)


def training_pairs(times, cutoff, start="1981-01-01"):
    """The target, not just the predictor, must precede the cutoff."""
    times = pd.DatetimeIndex(times)
    return np.flatnonzero((times[:-1] >= pd.Timestamp(start)) &
                          (times[1:] < pd.Timestamp(cutoff)))


def score(predicted, observed):
    if predicted.shape != observed.shape or not np.isfinite(predicted).all():
        raise ValueError("Prediction shape mismatch or non-finite prediction")
    if not np.isfinite(observed).all():
        raise ValueError("Non-finite evaluation target")
    errors = np.asarray(predicted, np.float64) - observed
    mse_month = np.mean(errors * errors, axis=tuple(range(1, errors.ndim)))
    return {"rmse": float(np.sqrt(mse_month.mean())),
            "year1_rmse": float(np.sqrt(mse_month[:12].mean())),
            "year2_rmse": float(np.sqrt(mse_month[12:].mean())),
            "monthly_rmse": np.sqrt(mse_month).tolist()}


def audit():
    CACHE.mkdir(parents=True, exist_ok=True)
    report = {"source": str(RAW), "files": {}, "checks": {},
              "versions": {p: importlib.metadata.version(p) for p in
                           ["numpy", "pandas", "xarray", "netCDF4", "scikit-learn"]},
              "excluded": ["data/interim/precip_jan_2023_america_sul.nc",
                           "data/interim/precip_fev_2023_america_sul.nc"]}
    expected_dates = dates().values
    lat = np.arange(-60, 15.01, .25)
    lon = np.arange(-90, -24.99, .25)
    for name in ["tp", "tp_alvo"] + VARIABLES:
        path = RAW / f"treino_{name}.nc"
        with xr.open_dataset(path) as ds:
            assert np.array_equal(ds.time.values, expected_dates), path
            assert np.array_equal(ds.lat.values, lat), path
            assert np.array_equal(ds.lon.values, lon), path
            assert ds[name].dims == ("time", "lat", "lon"), path
            values = ds[name].values
            finite = np.isfinite(values)
            stats = {"bytes": path.stat().st_size, "shape": list(values.shape),
                     "nonfinite": int(values.size - finite.sum()),
                     "negative": int((values < 0).sum()),
                     "min": float(np.min(values[finite])),
                     "max": float(np.max(values[finite])), "attributes": ds[name].attrs}
            if name == "tp_alvo":
                tp = np.load(CACHE / "tp.npy", mmap_mode="r")
                assert np.array_equal(values[:-1], tp[1:]), "Target shift mismatch"
                assert np.isnan(values[-1]).all(), "Last target must be NaN"
                report["checks"]["target_shift_exact"] = True
                del tp
            else:
                # Missing atmospheric fields are handled in the ridge pipeline.
                if name == "tp":
                    assert finite.all(), "Observed precipitation must be finite"
                np.save(CACHE / f"{name}.npy", values)
            report["files"][path.name] = stats
            print(name, stats, flush=True)
            del finite, values
    with xr.open_dataset(RAW / "teste_features.nc") as ds:
        assert np.array_equal(ds.time.values, pd.date_range("2023-01-01", periods=24, freq="MS").values)
        assert np.array_equal(ds.time_origem.values, pd.date_range("2022-12-01", periods=24, freq="MS").values)
        assert np.array_equal(ds.lag_meses.values, np.arange(1, 25))
        assert np.array_equal(ds.lat.values, lat) and np.array_equal(ds.lon.values, lon)
        assert np.isnan(ds.tp_alvo.values).all()
        tp = np.load(CACHE / "tp.npy", mmap_mode="r")
        assert np.all(ds.tp_ultima_obs.values == tp[-1])
        for name in VARIABLES:
            v = ds[name].values
            train = np.load(CACHE / f"{name}.npy", mmap_mode="r")
            assert np.allclose(v[0], train[-1], rtol=0, atol=0, equal_nan=True), name
            report["checks"][f"test_{name}_nonfinite"] = int((~np.isfinite(v)).sum())
            del train
        report["checks"].update(test_dates=True, origin_dates=True, frozen_precipitation=True,
                                  empty_test_target=True, grid=True, december_features_exact=True)
    report["sample_submission_present"] = (RAW / "sample_submission.csv").exists()
    save_json(REPORT / "audit.json", report)
    print("AUDIT PASS", flush=True)


def write_results(path, results):
    save_json(path, results)
    rows = [{k: v for k, v in row.items() if k != "monthly_rmse"} for row in results]
    with path.with_suffix(".csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def baselines():
    if not (REPORT / "audit.json").exists():
        raise RuntimeError("Run audit first")
    PRED.mkdir(parents=True, exist_ok=True)
    tp = np.load(CACHE / "tp.npy", mmap_mode="r")
    times = dates()
    results = []
    for fold, year in FOLDS.items():
        cutoff = f"{year}-01-01"
        mask = (times >= cutoff) & (times < f"{year+2}-01-01")
        truth = tp[mask]
        for years in [None, 60, 40, 30, 20, 10]:
            name = "clim_all" if years is None else f"clim_{years}y"
            climo = fit_climatology(tp, times, cutoff, years)
            pred = climo[month_number(times[mask])]
            metrics = score(pred, truth)
            results.append({"fold": fold, "model": name, **metrics})
            np.save(PRED / f"{fold}_{name}.npy", pred)
            print(fold, name, metrics["rmse"], metrics["year2_rmse"], flush=True)
    write_results(REPORT / "baselines.json", results)
    grouped = {}
    for row in results:
        grouped.setdefault(row["model"], []).append(row["rmse"] ** 2)
    ranked = sorted((float(np.sqrt(np.mean(v))), k) for k, v in grouped.items())
    save_json(REPORT / "baseline_selection.json", {
        "criterion": "pooled RMSE across both 24-month development folds; holdout untouched",
        "ranking": [{"model": name, "rmse": value} for value, name in ranked],
        "selected": ranked[0][1]})
    print("SELECTED", ranked[0], flush=True)


def ridge():
    """Pointwise multi-variable regression of precipitation anomalies.

    Nine coefficients per location, shared across seasons. Monthly feature means
    and feature standard deviations are fit strictly on training predictor rows.
    Penalties are added to X'X / n, so their scale is independent of sample count.
    Missing atmospheric values are replaced by their training monthly means.
    """
    started = time.monotonic()
    selection = json.loads((REPORT / "baseline_selection.json").read_text())
    base_name = selection["selected"]
    years = None if base_name == "clim_all" else int(base_name[5:-1])
    tp = np.load(CACHE / "tp.npy", mmap_mode="r")
    features = [np.load(CACHE / f"{v}.npy", mmap_mode="r") for v in VARIABLES]
    times = dates()
    results = []
    penalties = [0.1, 1.0, 10.0]
    for fold, year in FOLDS.items():
        cutoff = f"{year}-01-01"
        idx = training_pairs(times, cutoff)
        target_idx = np.flatnonzero((times >= cutoff) & (times < f"{year+2}-01-01"))
        origin_idx = target_idx - 1
        climo = fit_climatology(tp, times, cutoff, years)
        base = climo[month_number(times[target_idx])]
        predictions = {a: base.copy() for a in penalties}
        train_months = month_number(times[idx])
        for begin in range(0, tp.shape[1], 19):
            end = min(begin + 19, tp.shape[1])
            cells = (end - begin) * tp.shape[2]
            x = np.empty((len(idx), cells, len(VARIABLES)), dtype=np.float32)
            xv = np.empty((24, cells, len(VARIABLES)), dtype=np.float32)
            for j, data in enumerate(features):
                train = np.asarray(data[idx, begin:end, :]).reshape(len(idx), cells)
                valid = np.asarray(data[origin_idx, begin:end, :]).reshape(24, cells)
                means = np.stack([np.nanmean(train[train_months == m], axis=0) for m in range(12)])
                means = np.nan_to_num(means)
                train = train - means[train_months]
                valid = valid - means[month_number(times[origin_idx])]
                scale = np.nanstd(train, axis=0)
                scale = np.where(np.isfinite(scale) & (scale > 1e-8), scale, 1)
                x[:, :, j] = np.nan_to_num(train / scale)
                xv[:, :, j] = np.nan_to_num(valid / scale)
            y = np.asarray(tp[idx + 1, begin:end, :]).reshape(len(idx), cells)
            y = y - climo[month_number(times[idx + 1]), begin:end, :].reshape(len(idx), cells)
            # Center residuals explicitly; the intercept is not regularized.
            xmean = x.mean(axis=0)
            ymean = y.mean(axis=0)
            x -= xmean
            xv -= xmean
            y -= ymean
            xtx = np.einsum("tpi,tpj->pij", x, x, optimize=True) / len(idx)
            xty = np.einsum("tpi,tp->pi", x, y, optimize=True) / len(idx)
            for alpha in penalties:
                regularized = xtx + np.eye(len(VARIABLES), dtype=np.float32)[None] * alpha
                coef = np.linalg.solve(regularized, xty[..., None])[..., 0]
                correction = np.einsum("tpi,pi->tp", xv, coef) + ymean
                pred = base[:, begin:end] + correction.reshape(24, end - begin, tp.shape[2])
                predictions[alpha][:, begin:end] = np.maximum(pred, 0)
            print(f"{fold} latitude rows {end}/{tp.shape[1]} elapsed {time.monotonic()-started:.0f}s", flush=True)
        for alpha, pred in predictions.items():
            name = f"ridge_{alpha:g}_{base_name}"
            metrics = score(pred, tp[target_idx])
            results.append({"fold": fold, "model": name, **metrics})
            np.save(PRED / f"{fold}_{name}.npy", pred)
            print(fold, name, metrics["rmse"], flush=True)
    write_results(REPORT / "ridge.json", results)
    save_json(REPORT / "ridge_config.json", {"features": VARIABLES, "train_start": "1981-01-01",
              "baseline": base_name, "penalties": penalties, "elapsed_seconds": time.monotonic()-started,
              "holdout_evaluated": False, "precipitation_predictor_used": False})


def summarize():
    """Compare a predeclared half-strength blend and write a readable ledger."""
    baseline_rows = json.loads((REPORT / "baselines.json").read_text())
    ridge_rows = json.loads((REPORT / "ridge.json").read_text())
    selected = json.loads((REPORT / "baseline_selection.json").read_text())["selected"]
    tp = np.load(CACHE / "tp.npy", mmap_mode="r")
    times = dates()
    blend_rows = []
    for row in ridge_rows:
        fold = row["fold"]
        year = FOLDS[fold]
        base = np.load(PRED / f"{fold}_{selected}.npy")
        pred = np.load(PRED / f"{fold}_{row['model']}.npy")
        blend = (base + pred) / 2
        mask = (times >= f"{year}-01-01") & (times < f"{year+2}-01-01")
        name = f"half_{row['model']}"
        blend_rows.append({"fold": fold, "model": name, **score(blend, tp[mask])})
        np.save(PRED / f"{fold}_{name}.npy", blend)
    write_results(REPORT / "blends.json", blend_rows)
    all_rows = baseline_rows + ridge_rows + blend_rows
    if (REPORT / "trees.json").exists():
        all_rows += json.loads((REPORT / "trees.json").read_text())
    by_model = {}
    for row in all_rows:
        by_model.setdefault(row["model"], {})[row["fold"]] = row
    ranks = sorted(by_model, key=lambda name: np.mean([r["rmse"]**2 for r in by_model[name].values()]))
    lines = ["# Primeira rodada de desenvolvimento", "",
             "RMSE em mm/dia, grade completa. Menor é melhor. Nenhuma avaliação de 2021–2022 foi executada.", "",
             "| Modelo | 2017–2018 | 2019–2020 | Agrupado | 2018 | 2020 |",
             "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for name in ranks:
        a, b = [by_model[name][f] for f in FOLDS]
        pooled = float(np.sqrt((a["rmse"]**2 + b["rmse"]**2)/2))
        lines.append(f"| {name} | {a['rmse']:.6f} | {b['rmse']:.6f} | {pooled:.6f} | {a['year2_rmse']:.6f} | {b['year2_rmse']:.6f} |")
    best = ranks[0]
    lines += ["", f"Melhor candidato nesta rodada: `{best}`.", "",
              "As escolhas foram feitas nesses mesmos blocos: os números são de desenvolvimento, não de teste independente.",
              "`half_ridge_` representa média simples entre o modelo ridge e a climatologia selecionada.",
              "`half_trees_half_prior` usa 50% árvores + 25% ridge (penalidade 0,1) + 25% climatologia.",
              "As penalidades ridge são aplicadas a X'X/n; `clim_all` usa todo o histórico anterior ao bloco.", "",
              "## Limitações e próximo experimento", "",
              "- Apenas dois blocos de desenvolvimento; confirmar a estabilidade em outros anos antes da seleção final.",
              "- Verificar a coluna 2018: a combinação pode melhorar os blocos completos e ainda degradar um segundo ano.",
              "- Ridge local usa relações lineares e coeficientes comuns entre estações; investigar contexto espacial e sazonalidade.",
              "- Não foi utilizada chuva observada de nenhum bloco como entrada, nem dados externos.",
              "- Nenhuma submissão foi enviada. O exportador gera IDs pelo NetCDF; a ordem oficial não foi verificada sem sample_submission.csv.",
              "- Relatórios JSON/CSV guardam também os 24 RMSE mensais por execução (mensais no JSON).", ""]
    (REPORT / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    save_json(REPORT / "development_selection.json", {"selected": best, "holdout_evaluated": False})
    save_json(REPORT / "environment.json", {p: importlib.metadata.version(p) for p in
              ["numpy", "pandas", "xarray", "netCDF4", "scikit-learn"]})
    baseline = by_model[selected]
    diagnostics = {"candidate": best, "baseline": selected, "folds": {}}
    for fold, year in FOLDS.items():
        cand_month = np.asarray(by_model[best][fold]["monthly_rmse"])
        base_month = np.asarray(baseline[fold]["monthly_rmse"])
        delta = cand_month**2 - base_month**2
        forecast_dates = pd.date_range(f"{year}-01-01", periods=24, freq="MS")
        diagnostics["folds"][fold] = {
            "months_improved": int((delta < 0).sum()),
            "worst_months_by_mse_increase": [
                {"month": str(forecast_dates[k].date()), "delta_mse": float(delta[k]),
                 "baseline_rmse": float(base_month[k]), "candidate_rmse": float(cand_month[k])}
                for k in np.argsort(delta)[-5:][::-1]],
            "year2_rmse_change": by_model[best][fold]["year2_rmse"] - baseline[fold]["year2_rmse"]}
    save_json(REPORT / "diagnostics.json", diagnostics)
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["audit", "baselines", "ridge", "summarize"])
    args = parser.parse_args()
    {"audit": audit, "baselines": baselines, "ridge": ridge, "summarize": summarize}[args.stage]()
