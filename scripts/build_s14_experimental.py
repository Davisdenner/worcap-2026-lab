"""Build the frozen Round-27 logistic_base_0.3 leaderboard probe."""
from __future__ import annotations

import gc
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"

import joblib
import numpy as np
import xarray as xr
from sklearn.linear_model import LogisticRegression

from src import round20, round25, round26, round27
from src.competition import CACHE, RAW, ROOT, save_json
from src.round2 import Features, target_origins
from src.submission import export_csv

NAME = "S14_experimental_round27_gate"
ART = ROOT / "data/processed" / NAME
OUT = ROOT / "submissions" / f"{NAME}.csv"
PROTOCOL = ROOT / "experiments/S14_EXPERIMENTAL_ROUND27_GATE.md"
S12_CSV = ROOT / "submissions/submission_12.csv"
S12_NC = ROOT / "data/processed/reproducao/saidas_verificadas/s12/s12_reproduction.nc"
S12_HASH = "bba1f8b279447868170b6b2f9b18ee2cc723b891c25627c91438c7725d3aead8"
YEARS = (2009, 2011, 2013, 2015, 2017, 2019, 2021)
GRID = round25.GRID
NORTH = round26.NORTH
GMAX = .3


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def require_hash(path: Path, expected: str) -> None:
    actual = sha(path)
    if actual != expected:
        raise ValueError(f"SHA-256 inesperado: {path}: {actual}")


def preflight() -> dict:
    if OUT.exists() or (ART / "manifest.json").exists():
        raise FileExistsError("Submission experimental já existe; não sobrescrever")
    if round27.BASE_COLUMNS.tolist() != [0, 1, 2, 3, 4, 5, 106]:
        raise ValueError("Colunas logistic_base da Rodada 27 mudaram")
    require_hash(S12_CSV, S12_HASH)
    require_hash(ROOT / "data/processed/reproducao/saidas_verificadas/s12/s12_reproduction.csv", S12_HASH)
    ref = round20.reference(2023)
    with xr.open_dataset(S12_NC) as ds:
        np.testing.assert_array_equal(ref, ds.tp_mm_day.values)
    with xr.open_dataset(RAW / "teste_features.nc") as ds:
        if not np.isnan(ds.tp_alvo.values).all():
            raise ValueError("Alvos do teste não estão inteiramente ausentes")
        np.testing.assert_array_equal(ds.time.values.astype("datetime64[M]"),
                                      np.arange("2023-01", "2025-01", dtype="datetime64[M]"))
    tp = np.load(CACHE / "tp.npy", mmap_mode="r")
    if tp.shape != (996, 301, 261):
        raise ValueError("Treino histórico não termina em dezembro de 2022")
    hashes = {}
    for year in YEARS[:-1]:
        for name, path in (("s12", round20.ART / f"{year}_s12.npy"),
                           ("analog", round25.ART / f"{year}_h4_prediction.npy")):
            meta = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
            require_hash(path, meta["sha256"])
            hashes[f"{year}_{name}"] = meta["sha256"]
    s12_2021 = round20.ART / "2021_s12.npy"
    require_hash(s12_2021, json.loads(s12_2021.with_suffix(".json").read_text(encoding="utf-8"))["sha256"])
    hashes["2021_s12"] = sha(s12_2021)
    hashes["2023_s12"] = sha(round20.ART / "2023_s12.npy")
    hashes["s12_csv"] = S12_HASH
    hashes["s12_reproduction_nc"] = sha(S12_NC)
    hashes["official_test_features"] = sha(RAW / "teste_features.nc")
    hashes["official_sample"] = sha(RAW / "sample_submission.csv")
    hashes["official_tp_cache"] = sha(CACHE / "tp.npy")
    return hashes


def analog_h4(cutoff: int, final: bool = False) -> np.ndarray:
    """The H4 loop from Round 25, with the same transform and tie ordering."""
    f = Features(cutoff, final=final)
    global_train, global_valid = round20.context(f)
    train = round25._analog_coordinates(global_train).astype(np.float64)
    valid = round25._analog_coordinates(global_valid).astype(np.float64)
    archive_month = (f.idx + 1) % 12
    pred = np.empty((24, GRID), np.float32)
    for k, origin in enumerate(target_origins(cutoff)):
        target_month = (origin + 1) % 12
        seasonal_distance = np.minimum((archive_month-target_month) % 12,
                                       (target_month-archive_month) % 12)
        eligible = np.flatnonzero(seasonal_distance <= 1)
        if len(eligible) < 10:
            raise ValueError("Menos de dez análogos sazonais")
        distance = np.linalg.norm(train[eligible]-valid[k], axis=1)
        order = np.argsort(distance, kind="stable")[:10]
        idx = f.idx[eligible[order]]+1
        if np.max(idx) >= (cutoff-1940)*12:
            raise ValueError("Análogo incluiu alvo do bloco previsto")
        observed = np.asarray(f.tp[idx], dtype=np.float64)
        anomaly = observed-np.asarray(f.climo[idx % 12], dtype=np.float64)
        result = np.maximum(f.climo[target_month]+anomaly.mean(axis=0), 0)
        pred[k] = result.astype(np.float32)
    del f, global_train, global_valid, train, valid
    gc.collect()
    return pred.reshape(24, 301, 261)


def base_features(origin: int, cells: np.ndarray, climo: np.ndarray,
                  s12: np.ndarray, analog: np.ndarray) -> np.ndarray:
    target = (origin+1) % 12
    x = np.empty((len(cells), 7), np.float32)
    x[:, 0] = round25.LAT[cells]
    x[:, 1] = round25.LON[cells]
    x[:, 2] = np.sin(2*np.pi*target/12)
    x[:, 3] = np.cos(2*np.pi*target/12)
    x[:, 4] = climo[target, cells]
    x[:, 5] = s12[cells]
    x[:, 6] = analog[cells]-x[:, 5]
    if not np.isfinite(x).all():
        raise ValueError("Atributo não finito")
    return x


def train_gate(climo: np.ndarray, analog_2021: np.ndarray) -> tuple[dict, dict]:
    tp = np.load(CACHE / "tp.npy", mmap_mode="r").reshape(-1, GRID)
    n = len(YEARS)*24*round26.SAMPLE
    x = np.empty((n, 7), np.float32)
    y = np.empty(n, bool)
    provenance = {}
    for year in YEARS:
        s12 = np.load(round20.ART / f"{year}_s12.npy", mmap_mode="r").reshape(24, GRID)
        analog = (analog_2021 if year == 2021 else
                  np.load(round25.ART / f"{year}_h4_prediction.npy", mmap_mode="r")).reshape(24, GRID)
        for slot, origin in enumerate(target_origins(year)):
            cells = round26._sample_cells(int(origin))
            sl = slice(((year-2009)//2*24+slot)*round26.SAMPLE,
                       ((year-2009)//2*24+slot+1)*round26.SAMPLE)
            x[sl] = base_features(int(origin), cells, climo, s12[slot], analog[slot])
            r12 = (tp[origin+1, cells]-x[sl, 5]).astype(np.float32)
            ra = (r12+x[sl, 5]-analog[slot, cells]).astype(np.float64)
            y[sl] = ra**2 < r12.astype(np.float64)**2
        provenance[str(year)] = {"samples": 24*round26.SAMPLE,
                                 "last_target": f"{year+1}-12"}
    if not np.isfinite(x).all() or np.unique(y).size != 2:
        raise ValueError("Treino inválido")
    mean = x.mean(axis=0, dtype=np.float64)
    sd = np.where(x.std(axis=0, dtype=np.float64) > 1e-6,
                  x.std(axis=0, dtype=np.float64), 1.)
    z = ((x-mean)/sd).astype(np.float32)
    model = LogisticRegression(C=.3, max_iter=200, solver="lbfgs", tol=1e-4)
    model.fit(z, y)
    artifact = {"model": model, "mean": mean, "sd": sd,
                "base_columns_round27": round27.BASE_COLUMNS.tolist()}
    joblib.dump(artifact, ART / "gate.joblib")
    np.savez_compressed(ART / "gate_training.npz", x=x, y=y)
    return artifact, {"rows": n, "positive_fraction": float(y.mean()),
                      "training_blocks": provenance,
                      "last_training_target": "2022-12",
                      "coef": model.coef_.tolist(),
                      "intercept": model.intercept_.tolist(),
                      "mean": mean.tolist(), "sd": sd.tolist()}


def metrics(pred: np.ndarray, s12: np.ndarray, probability: np.ndarray) -> dict:
    d = pred-s12.astype(np.float64)
    north = np.zeros(GRID, bool)
    north[NORTH] = True
    labels = {"global": np.ones(GRID, bool), "north": north, "rest": ~north}
    summary = {}
    for time_name, months in (("all", slice(None)), ("2023", slice(0, 12)),
                              ("2024", slice(12, 24))):
        for region_name, cells in labels.items():
            values = d[months].reshape(-1, GRID)[:, cells]
            summary[f"{time_name}_{region_name}"] = {
                "rms_change": float(np.sqrt(np.mean(values*values))),
                "max_absolute_change": float(np.max(np.abs(values))),
                "mean_change": float(np.mean(values)),
                "changed_fraction": float(np.mean(values != 0)),
            }
    flat = pred.ravel()
    stats = {"min": float(flat.min()), "max": float(flat.max()),
             "mean": float(flat.mean()), "std": float(flat.std()),
             "quantiles": {str(q): float(np.quantile(flat, q))
                           for q in (0, .01, .05, .25, .5, .75, .95, .99, 1)}}
    bands = {}
    for low, high in ((-60, -45), (-45, -30), (-30, -15), (-15, 0),
                      (0, 5), (5, 10), (10, 15.01)):
        selected = (round25.LAT >= low) & (round25.LAT < high)
        values = d[:, selected]
        bands[f"{low}:{high}"] = {
            "cells": int(selected.sum()),
            "rms_change": float(np.sqrt(np.mean(values*values))),
            "mean_absolute_change": float(np.mean(np.abs(values))),
        }
    return {"prediction": stats, "change_vs_s12": summary,
            "latitude_bands": bands,
            "probability": {"min": float(probability.min()),
                            "max": float(probability.max()),
                            "mean": float(probability.mean())}}


def main() -> None:
    inputs = preflight()
    ART.mkdir(parents=True, exist_ok=True)
    print("Preflight S12 e insumos OOF: OK", flush=True)
    check = analog_h4(2019)
    np.testing.assert_array_equal(check, np.load(round25.ART / "2019_h4_prediction.npy"))
    print("Analog H4 reproduzido exatamente em 2019–2020", flush=True)
    del check
    gc.collect()
    analog_2021 = analog_h4(2021)
    np.save(ART / "2021_analog_h4.npy", analog_2021)
    print("Analog H4 OOF 2021–2022: OK", flush=True)
    analog_2023 = analog_h4(2023, final=True)
    np.save(ART / "2023_analog_h4.npy", analog_2023)
    print("Analog H4 final 2023–2024: OK", flush=True)
    f = Features(2023, final=True)
    gate, training = train_gate(f.climo, analog_2021)
    s12 = np.load(round20.ART / "2023_s12.npy", mmap_mode="r").reshape(24, GRID)
    analog = analog_2023.reshape(24, GRID)
    pred = np.asarray(s12, np.float64).copy()
    probabilities = np.empty((24, len(NORTH)), np.float32)
    for slot, origin in enumerate(target_origins(2023)):
        x = base_features(int(origin), NORTH, f.climo, s12[slot], analog[slot])
        z = ((x-gate["mean"])/gate["sd"]).astype(np.float32)
        p = gate["model"].predict_proba(z)[:, 1].astype(np.float32)
        probabilities[slot] = p
        g = GMAX*p.astype(np.float64)
        pred[slot, NORTH] = s12[slot, NORTH].astype(np.float64)+g*(
            analog[slot, NORTH].astype(np.float64)-s12[slot, NORTH].astype(np.float64))
    if np.min(probabilities) < 0 or np.max(probabilities) > 1:
        raise ValueError("Probabilidade fora de [0,1]")
    if not np.isfinite(pred).all() or np.min(pred) < 0:
        raise ValueError("Previsão inválida")
    np.testing.assert_array_equal(pred[:, np.setdiff1d(np.arange(GRID), NORTH)],
                                  np.asarray(s12[:, np.setdiff1d(np.arange(GRID), NORTH)], np.float64))
    pred = pred.reshape(24, 301, 261)
    np.save(ART / "probability_north.npy", probabilities)
    np.save(ART / "prediction.npy", pred)
    with xr.open_dataset(RAW / "teste_features.nc") as grid:
        da = xr.DataArray(pred, dims=("time", "lat", "lon"),
                          coords={d: grid[d] for d in ("time", "lat", "lon")},
                          name="tp_mm_day")
        csv_validation = export_csv(da, grid, OUT, RAW / "sample_submission.csv")
    validation = metrics(pred.reshape(24, GRID), np.asarray(s12), probabilities)
    save_json(ART / "validation.json", {**csv_validation, **validation})
    files = {
        "protocol": PROTOCOL, "builder": Path(__file__),
        "round27_code": ROOT / "src/round27.py", "round25_code": ROOT / "src/round25.py",
        "round20_code": ROOT / "src/round20.py", "round26_code": ROOT / "src/round26.py",
        "gate": ART / "gate.joblib", "gate_training": ART / "gate_training.npz",
        "analog_2021": ART / "2021_analog_h4.npy",
        "analog_2023": ART / "2023_analog_h4.npy",
        "probability": ART / "probability_north.npy", "prediction": ART / "prediction.npy",
        "validation": ART / "validation.json", "csv": OUT,
        "pca_continental_2021": round20.transform_paths(2021)[0],
        "pca_tropical_2021": round20.transform_paths(2021)[1],
        "pca_continental_2023": round20.transform_paths(2023)[0],
        "pca_tropical_2023": round20.transform_paths(2023)[1],
    }
    manifest = {
        "name": NAME, "status": "experimental / leaderboard probe / não promovida",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "method": "Round27 logistic_base_0.3", "gmax": GMAX,
        "north_cells": len(NORTH), "training": training,
        "round27_oof_inputs_sha256": inputs,
        "files_sha256": {key: sha(path) for key, path in files.items()},
        "files": {key: str(path.relative_to(ROOT)).replace("\\", "/") for key, path in files.items()},
        "official_reference": "S12", "official_reference_unchanged": sha(S12_CSV) == S12_HASH,
        "uses_2023_2024_targets": False, "uploaded": False,
    }
    save_json(ART / "manifest.json", manifest)
    print(json.dumps({"csv": str(OUT), "sha256": manifest["files_sha256"]["csv"],
                      "rows": csv_validation["rows"], "rms_change": validation["change_vs_s12"]["all_global"]["rms_change"]},
                     ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
