"""Rodada 26: investigação OOF do resíduo S12 no norte da grade oficial."""
from __future__ import annotations

import os
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"

import argparse
import gc
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import roc_auc_score, average_precision_score

from . import round20, round25
from .competition import CACHE, ROOT, REPORT, VARIABLES, save_json
from .round2 import Features, target_origins

OUT = REPORT / "round26"
ART = ROOT / "data/processed/round26"
PROTOCOL = ROOT / "experiments/ROUND26.md"
SOURCE = ROOT / "src/round26.py"
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "tmp" / "matplotlib"))
YEARS = (2009, 2011, 2013, 2015, 2017, 2019)
EVAL = YEARS[1:]
NORTH = np.flatnonzero(round25.LAT >= 0).astype(np.intp)
NORTH_LAT = round25.LAT[NORTH]
NORTH_LON = round25.LON[NORTH]
NORTH_SIZE = len(NORTH)
SAMPLE = 512
RIDGE_PENALTY = .3
EPS = .1
WIDTH = 105

CORE = np.arange(0, 7)
LOCAL = np.arange(7, 57)
CONT = np.arange(57, 73)
TROP = np.arange(73, 89)
MEMBERS = np.arange(89, 94)
CONSENSUS = np.arange(94, 105)
GROUPS = {
    "base": CORE,
    "local": np.r_[CORE, LOCAL],
    "continental": np.r_[CORE, CONT],
    "tropical": np.r_[CORE, TROP],
    "components": np.r_[CORE, MEMBERS],
    "dispersion": np.r_[CORE, 95, 96],
    "consensus": np.r_[CORE, CONSENSUS],
    "local_continental": np.r_[CORE, LOCAL, CONT],
    "local_tropical": np.r_[CORE, LOCAL, TROP],
    "full": np.arange(WIDTH),
}
FEATURE_NAMES = (
    ["latitude", "longitude", "sin_target_month", "cos_target_month",
     "climatology", "s12", "s12_anomaly"]
    + [f"local_context_{j}" for j in range(5, 55)]
    + [f"continental_pc_{j+1}" for j in range(8)]
    + [f"continental_mean3_pc_{j+1}" for j in range(8)]
    + [f"tropical_pc_{j+1}" for j in range(8)]
    + [f"tropical_mean3_pc_{j+1}" for j in range(8)]
    + [f"component_minus_s12_{j}" for j in range(5)]
    + ["member_mean", "member_std", "member_range", "member_min",
       "member_max", "above_climatology", "below_climatology",
       "majority_anomaly_sign", "mean_absolute_member_anomaly",
       "absolute_mean_member_anomaly", "consensus_ratio"]
)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def locked() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    record = {
        "protocol_sha256": digest(PROTOCOL), "source_sha256": digest(SOURCE),
        "s12_reference_hashes": {
            str(y): digest(round20.ART / f"{y}_s12.npy") for y in YEARS
        },
        "north_cells": NORTH_SIZE, "training_sample_per_month": SAMPLE,
        "evaluated_blocks": EVAL, "descriptive_blocks": YEARS,
        "ridge_penalty_average_covariance": RIDGE_PENALTY,
        "groups": {name: cols.tolist() for name, cols in GROUPS.items()},
        "feature_names": FEATURE_NAMES,
        "official_only": True, "no_test_targets": True,
        "no_submission": True,
    }
    path = OUT / "protocol.json"
    if path.exists():
        prior = json.loads(path.read_text(encoding="utf-8"))
        if prior != json.loads(json.dumps(record)):
            raise ValueError("Protocolo, código ou S12 histórica mudou")
    else:
        save_json(path, record)


def _source(year: int) -> tuple[np.ndarray, np.ndarray]:
    return round20.reference(year).reshape(24, -1), round25.component_maps(year)


def _month_lookup(years: tuple[int, ...]) -> dict[int, tuple[int, int]]:
    return {
        int(origin): (year, slot)
        for year in years
        for slot, origin in enumerate(target_origins(year))
    }


def _sample_cells(origin: int) -> np.ndarray:
    rng = np.random.default_rng(20260926 + int(origin))
    return NORTH[rng.choice(NORTH_SIZE, SAMPLE, replace=False)]


def _features(f: Features, origin: int, cells: np.ndarray, global_values: np.ndarray,
              s12: np.ndarray, components: np.ndarray) -> np.ndarray:
    local = f.matrix(origin, cells, context=True)
    member = np.stack([components[j, cells] for j in range(5)], axis=1).astype(np.float32)
    base = np.asarray(s12[cells], np.float32)
    climo = local[:, 4]
    anomaly = member-climo[:, None]
    mean = member.mean(axis=1)
    std = member.std(axis=1)
    amplitude = np.ptp(member, axis=1)
    mean_anomaly = mean-climo
    x = np.empty((len(cells), WIDTH), np.float32)
    x[:, :5] = local[:, :5]
    x[:, 5] = base
    x[:, 6] = base-climo
    x[:, LOCAL] = local[:, 5:55]
    x[:, CONT] = np.r_[global_values[:8], global_values[16:24]]
    x[:, TROP] = np.r_[global_values[32:40], global_values[48:56]]
    x[:, MEMBERS] = member-base[:, None]
    x[:, 94] = mean
    x[:, 95] = std
    x[:, 96] = amplitude
    x[:, 97] = member.min(axis=1)
    x[:, 98] = member.max(axis=1)
    x[:, 99] = np.sum(anomaly > 0, axis=1)
    x[:, 100] = np.sum(anomaly < 0, axis=1)
    x[:, 101] = np.sign(x[:, 99]-x[:, 100])
    x[:, 102] = np.mean(np.abs(anomaly), axis=1)
    x[:, 103] = np.abs(mean_anomaly)
    x[:, 104] = np.abs(mean_anomaly)/(std+EPS)
    if not np.isfinite(x).all():
        raise ValueError("Features não finitas")
    return x


def _fit_ridge_family(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, tuple[np.ndarray, np.ndarray]]:
    mu = x.mean(axis=0, dtype=np.float64)
    sd = x.std(axis=0, dtype=np.float64)
    sd = np.where(sd > 1e-6, sd, 1.)
    z = ((x-mu)/sd).astype(np.float32)
    gram = (z.T @ z).astype(np.float64)/len(y)
    centered = y-y.mean()
    xy = (z.T @ centered).astype(np.float64)/len(y)
    return mu, sd, (gram, xy)


def _ridge_coefficients(gram: np.ndarray, xy: np.ndarray, cols: np.ndarray) -> np.ndarray:
    reg = gram[np.ix_(cols, cols)] + RIDGE_PENALTY*np.eye(len(cols))
    return np.linalg.solve(reg, xy[cols])


def _score(y: np.ndarray, pred: np.ndarray) -> dict:
    y = np.asarray(y, np.float64).ravel()
    pred = np.asarray(pred, np.float64).ravel()
    sse = float(np.sum((y-pred)**2))
    zero = float(np.sum(y*y))
    centered = float(np.sum((y-y.mean())**2))
    corr = float(np.corrcoef(y, pred)[0, 1]) if np.std(pred) > 0 else None
    return {
        "count": len(y), "residual_rmse": float(np.sqrt(sse/len(y))),
        "zero_residual_rmse": float(np.sqrt(zero/len(y))),
        "r2_against_zero": 1-sse/zero,
        "r2_centered": 1-sse/centered,
        "correlation": corr,
        "mean_true_residual": float(y.mean()),
        "mean_predicted_residual": float(pred.mean()),
    }


def _binary_score(y: np.ndarray, probability: np.ndarray, prior: float,
                  critical: bool = False) -> dict:
    actual = np.asarray(y, bool).ravel()
    p = np.clip(np.asarray(probability, np.float64).ravel(), .01, .99)
    baseline = float(np.mean((actual-prior)**2))
    brier = float(np.mean((actual-p)**2))
    result = {
        "count": len(actual), "prevalence": float(actual.mean()),
        "prior_from_training": float(prior),
        "auc": float(roc_auc_score(actual, p)) if np.unique(actual).size == 2 else None,
        "brier": brier, "baseline_brier": baseline,
        "brier_gain": baseline-brier,
    }
    if critical:
        limit = float(np.quantile(p, .9))
        top = p >= limit
        result.update(
            average_precision=float(average_precision_score(actual, p)),
            top_decile_rate=float(actual[top].mean()),
            top_decile_lift=float(actual[top].mean()/actual.mean())
            if actual.mean() > 0 else None,
        )
    return result


def _thresholds(prior_years: tuple[int, ...], tp: np.ndarray,
                sources: dict[int, tuple[np.ndarray, np.ndarray]]) -> tuple[float, float, float]:
    residuals = []
    for year in prior_years:
        ref = sources[year][0][:, NORTH]
        truth = tp[target_origins(year)+1][:, NORTH]
        residuals.append((truth-ref).ravel())
    values = np.concatenate(residuals)
    return float(np.quantile(np.abs(values), .9)), \
           float(np.quantile(np.abs(values), .95)), float(np.mean(values > 0))


def _build_block(cutoff: int, f: Features, globals_train: np.ndarray,
                 globals_valid: np.ndarray,
                 sources: dict[int, tuple[np.ndarray, np.ndarray]],
                 tp: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    prior = tuple(y for y in YEARS if y < cutoff)
    lookup = _month_lookup(prior)
    origins = np.concatenate([target_origins(y) for y in prior])
    train_x = np.empty((len(origins)*SAMPLE, WIDTH), np.float32)
    train_r = np.empty(len(train_x), np.float32)
    for k, origin in enumerate(origins):
        year, slot = lookup[int(origin)]
        cells = _sample_cells(int(origin))
        index = int(np.searchsorted(f.idx, origin))
        if index == len(f.idx) or f.idx[index] != origin:
            raise ValueError("Origem histórica fora do treino causal")
        global_values = globals_train[index]
        s12, comps = sources[year]
        sl = slice(k*SAMPLE, (k+1)*SAMPLE)
        train_x[sl] = _features(f, int(origin), cells, global_values,
                                s12[slot], comps[:, slot])
        train_r[sl] = tp[origin+1, cells]-s12[slot, cells]
    valid_x = np.empty((24*NORTH_SIZE, WIDTH), np.float32)
    valid_r = np.empty(len(valid_x), np.float32)
    s12, comps = sources[cutoff]
    for slot, origin in enumerate(target_origins(cutoff)):
        sl = slice(slot*NORTH_SIZE, (slot+1)*NORTH_SIZE)
        valid_x[sl] = _features(f, int(origin), NORTH, globals_valid[slot],
                                s12[slot], comps[:, slot])
        valid_r[sl] = tp[origin+1, NORTH]-s12[slot, NORTH]
    return train_x, train_r, valid_x, valid_r


def _conditional_rows(train_x: np.ndarray, valid_x: np.ndarray,
                      residual: np.ndarray, q90: float) -> list[dict]:
    critical = np.abs(residual) > q90
    under = residual > 0
    families = {
        "climatology": 4, "s12_anomaly": 6, "member_std": 95,
        "consensus_ratio": 104,
        **{f"continental_pc{j+1}": 57+j for j in range(4)},
        **{f"tropical_pc{j+1}": 73+j for j in range(4)},
        **{name: 7+j for j, name in enumerate(VARIABLES)},
    }
    rows = []
    for name, column in families.items():
        edges = np.quantile(train_x[:, column], [.2, .4, .6, .8])
        code = np.searchsorted(edges, valid_x[:, column], side="right")
        for group in range(5):
            selected = code == group
            if not selected.any():
                continue
            e = residual[selected]
            rows.append({
                "feature": name, "bin": group,
                "train_edges": [float(v) for v in edges],
                "count": int(selected.sum()), "under_probability": float(under[selected].mean()),
                "critical_probability": float(critical[selected].mean()),
                "mean_residual": float(e.mean()),
                "rmse": float(np.sqrt(np.mean(e*e))),
                "sse_fraction": float(np.sum(e*e)/np.sum(residual*residual)),
            })
    month = np.repeat((np.arange(24) % 12)+1, NORTH_SIZE)
    season = (month % 12)//3
    north_lat = np.tile(NORTH_LAT, 24)
    north_lon = np.tile(NORTH_LON, 24)
    fixed = {
        "month": (month-1, 12),
        "season": (season, 4),
        "latitude_5deg": (np.minimum((north_lat//5).astype(int), 2), 3),
        "longitude_10deg": (np.minimum(((north_lon+90)//10).astype(int), 6), 7),
    }
    for name, (code, number) in fixed.items():
        for group in range(number):
            selected = code == group
            if not selected.any():
                continue
            e = residual[selected]
            rows.append({
                "feature": name, "bin": group, "count": int(selected.sum()),
                "under_probability": float(under[selected].mean()),
                "critical_probability": float(critical[selected].mean()),
                "mean_residual": float(e.mean()),
                "rmse": float(np.sqrt(np.mean(e*e))),
                "sse_fraction": float(np.sum(e*e)/np.sum(residual*residual)),
            })
    return rows


def _consensus_rows(valid_x: np.ndarray, residual: np.ndarray, q90: float) -> list[dict]:
    ratio = valid_x[:, 104]
    climo = valid_x[:, 4]
    predicted_magnitude = np.abs(valid_x[:, 6])
    a_code = np.digitize(ratio, [1, 2, 4, 8])
    c_code = np.digitize(climo, [2, 5, 10])
    p_code = np.digitize(predicted_magnitude, [.5, 1, 2])
    rows = []
    for family, codes, number in (
        ("A", a_code, 5),
        ("A_by_climatology", a_code*4+c_code, 20),
        ("A_by_predicted_anomaly", a_code*4+p_code, 20),
    ):
        for group in range(number):
            selected = codes == group
            if not selected.any():
                continue
            e = residual[selected]
            rows.append({
                "group_family": family, "group": group,
                "count": int(selected.sum()), "under_probability": float(np.mean(e > 0)),
                "critical_probability": float(np.mean(np.abs(e) > q90)),
                "rmse": float(np.sqrt(np.mean(e*e))),
                "sse_fraction": float(np.sum(e*e)/np.sum(residual*residual)),
                "mean_climatology": float(climo[selected].mean()),
                "mean_predicted_anomaly_magnitude": float(predicted_magnitude[selected].mean()),
            })
    return rows


def _extreme_contrasts(valid_x: np.ndarray, residual: np.ndarray,
                       q90: float, q95: float) -> list[dict]:
    indices = [4, 6, 95, 104, *range(57, 61), *range(73, 77),
               *range(7, 16)]
    rows = []
    for quantile, threshold in (("q90", q90), ("q95", q95)):
        extreme = np.abs(residual) > threshold
        normal = ~extreme
        for column in indices:
            x = np.asarray(valid_x[:, column], np.float64)
            mu1, mu0 = x[extreme].mean(), x[normal].mean()
            spread = np.sqrt(.5*(x[extreme].var()+x[normal].var()))
            rows.append({
                "threshold": quantile, "feature": FEATURE_NAMES[column],
                "extreme_count": int(extreme.sum()), "normal_count": int(normal.sum()),
                "mean_extreme": float(mu1), "mean_normal": float(mu0),
                "standardized_mean_difference": float((mu1-mu0)/spread)
                if spread > 0 else 0.,
            })
    return rows


def evaluate() -> None:
    locked()
    tp = np.load(CACHE / "tp.npy", mmap_mode="r").reshape(-1, round25.GRID)
    for cutoff in EVAL:
        report_path = OUT / f"{cutoff}_predictability.json"
        path = ART / f"{cutoff}_oof.npz"
        if report_path.exists() and path.exists() and path.with_suffix(".json").exists():
            print("BLOCO EXISTENTE", cutoff, flush=True)
            continue
        prior = tuple(y for y in YEARS if y < cutoff)
        sources = {y: _source(y) for y in (*prior, cutoff)}
        q90, q95, prior_sign = _thresholds(prior, tp, sources)
        f = Features(cutoff)
        global_train, global_valid = round20.context(f)
        xtrain, rtrain, xvalid, rvalid = _build_block(
            cutoff, f, global_train, global_valid, sources, tp)
        mu, sd, (gram, xy) = _fit_ridge_family(xtrain, rtrain)
        ztrain = ((xtrain-mu)/sd).astype(np.float32)
        zvalid = ((xvalid-mu)/sd).astype(np.float32)
        predictions = []
        metrics = {}
        for name, columns in GROUPS.items():
            coef = _ridge_coefficients(gram, xy, columns)
            value = (rtrain.mean()+zvalid[:, columns]@coef).astype(np.float32)
            predictions.append(value)
            metrics[name] = {
                "block": _score(rvalid, value),
                "year1": _score(rvalid[:12*NORTH_SIZE], value[:12*NORTH_SIZE]),
                "year2": _score(rvalid[12*NORTH_SIZE:], value[12*NORTH_SIZE:]),
            }
        hgb = HistGradientBoostingRegressor(
            loss="squared_error", learning_rate=.03, max_iter=100,
            max_leaf_nodes=7, min_samples_leaf=500, l2_regularization=100.,
            max_bins=128, early_stopping=False, random_state=20260926,
        ).fit(xtrain, rtrain)
        nonlinear = hgb.predict(xvalid).astype(np.float32)
        predictions.append(nonlinear)
        metrics["full_hgb"] = {
            "block": _score(rvalid, nonlinear),
            "year1": _score(rvalid[:12*NORTH_SIZE], nonlinear[:12*NORTH_SIZE]),
            "year2": _score(rvalid[12*NORTH_SIZE:], nonlinear[12*NORTH_SIZE:]),
        }
        full = GROUPS["full"]
        direction_y = (rtrain > 0).astype(np.float32)
        critical_y = (np.abs(rtrain) > q90).astype(np.float32)
        direction_xy = (ztrain.T@(direction_y-direction_y.mean())).astype(np.float64)/len(rtrain)
        critical_xy = (ztrain.T@(critical_y-critical_y.mean())).astype(np.float64)/len(rtrain)
        direction_coef = _ridge_coefficients(gram, direction_xy, full)
        critical_coef = _ridge_coefficients(gram, critical_xy, full)
        direction_p = np.clip(direction_y.mean()+zvalid@direction_coef, .01, .99).astype(np.float32)
        critical_p = np.clip(critical_y.mean()+zvalid@critical_coef, .01, .99).astype(np.float32)
        true_direction = rvalid > 0
        true_critical = np.abs(rvalid) > q90
        binary = {}
        for name, actual, probability, prior_probability, iscritical in (
            ("direction", true_direction, direction_p, prior_sign, False),
            ("critical_q90", true_critical, critical_p, .1, True),
        ):
            binary[name] = {
                "block": _binary_score(actual, probability, prior_probability, iscritical),
                "year1": _binary_score(actual[:12*NORTH_SIZE], probability[:12*NORTH_SIZE],
                                       prior_probability, iscritical),
                "year2": _binary_score(actual[12*NORTH_SIZE:], probability[12*NORTH_SIZE:],
                                       prior_probability, iscritical),
            }
        save_json(report_path, {
            "cutoff": cutoff, "training_blocks": prior,
            "last_training_target": f"{cutoff-1}-12",
            "training_months": len(prior)*24, "training_samples": len(rtrain),
            "evaluation_months": 24, "evaluation_cells_per_month": NORTH_SIZE,
            "q90_training_abs_residual": q90, "q95_training_abs_residual": q95,
            "prior_under_probability": prior_sign, "group_metrics": metrics,
            "binary_metrics": binary,
            "conditional": _conditional_rows(xtrain, xvalid, rvalid, q90),
            "consensus": _consensus_rows(xvalid, rvalid, q90),
            "extreme_contrasts": _extreme_contrasts(xvalid, rvalid, q90, q95),
            "official_only": True, "no_test_targets": True,
        })
        np.savez_compressed(
            path, residual=rvalid.reshape(24, NORTH_SIZE),
            predictions=np.stack(predictions).reshape(len(predictions), 24, NORTH_SIZE),
            direction_probability=direction_p.reshape(24, NORTH_SIZE),
            critical_probability=critical_p.reshape(24, NORTH_SIZE),
        )
        save_json(path.with_suffix(".json"), {
            "sha256": digest(path), "cutoff": cutoff, "training_blocks": prior,
            "model_names": list(GROUPS)+["full_hgb"],
            "north_cells": NORTH_SIZE, "last_training_target": f"{cutoff-1}-12",
            "official_only": True,
        })
        print("OOF", cutoff, "base", metrics["base"]["block"]["r2_against_zero"],
              "full", metrics["full"]["block"]["r2_against_zero"],
              "hgb", metrics["full_hgb"]["block"]["r2_against_zero"],
              flush=True)
        del f, sources, xtrain, xvalid, rtrain, rvalid, ztrain, zvalid
        gc.collect()


def _group_stats(residual: np.ndarray, codes: np.ndarray, number: int,
                 total_sse: float, threshold: float | None = None) -> list[dict]:
    value = np.asarray(residual, np.float64).ravel()
    code = np.asarray(codes, np.intp).ravel()
    counts = np.bincount(code, minlength=number)
    sums = np.bincount(code, weights=value, minlength=number)
    squared = np.bincount(code, weights=value*value, minlength=number)
    under = np.bincount(code, weights=value > 0, minlength=number)
    critical = (np.bincount(code, weights=np.abs(value) > threshold, minlength=number)
                if threshold is not None else None)
    return [
        {
            "group": i, "count": int(counts[i]),
            "count_fraction": float(counts[i]/len(value)),
            "rmse": float(np.sqrt(squared[i]/counts[i])) if counts[i] else None,
            "bias_observed_minus_s12": float(sums[i]/counts[i]) if counts[i] else None,
            "under_probability": float(under[i]/counts[i]) if counts[i] else None,
            "sse_fraction": float(squared[i]/total_sse),
            "critical_probability": float(critical[i]/counts[i])
            if critical is not None and counts[i] else None,
        }
        for i in range(number)
    ]


def diagnostic() -> None:
    locked()
    tp = np.load(CACHE / "tp.npy", mmap_mode="r").reshape(-1, round25.GRID)
    residuals, observations, climates, s12_values, stds, ratios = [], [], [], [], [], []
    mean_anomalies, all_same, year_codes, month_codes = [], [], [], []
    map_sse = np.zeros((61, 261), np.float64)
    map_bias_sum = np.zeros((61, 261), np.float64)
    year_month_rmse = np.zeros((12, 12), np.float64)
    year_month_bias = np.zeros((12, 12), np.float64)
    hashes = {}
    for year in YEARS:
        f = Features(year)
        pred, components = _source(year)
        hashes[str(year)] = digest(round20.ART / f"{year}_s12.npy")
        for slot, origin in enumerate(target_origins(year)):
            truth = np.asarray(tp[origin+1, NORTH], np.float64)
            p = np.asarray(pred[slot, NORTH], np.float64)
            climo = np.asarray(f.climo[(origin+1) % 12, NORTH], np.float64)
            member = np.asarray(components[:, slot, NORTH], np.float64)
            err = truth-p
            dispersion = member.std(axis=0)
            mean_anomaly = member.mean(axis=0)-climo
            ratio = np.abs(mean_anomaly)/(dispersion+EPS)
            member_errors = truth[None, :]-member
            consensus_error = np.all(member_errors > 0, axis=0) | \
                              np.all(member_errors < 0, axis=0)
            residuals.append(err.astype(np.float32))
            observations.append(truth.astype(np.float32))
            climates.append(climo.astype(np.float32))
            s12_values.append(p.astype(np.float32))
            stds.append(dispersion.astype(np.float32))
            ratios.append(ratio.astype(np.float32))
            mean_anomalies.append(mean_anomaly.astype(np.float32))
            all_same.append(consensus_error)
            year_codes.append(np.full(NORTH_SIZE, year-2009+slot//12, np.int8))
            month_codes.append(np.full(NORTH_SIZE, slot % 12, np.int8))
            mapped = err.reshape(61, 261)
            map_sse += mapped*mapped
            map_bias_sum += mapped
            year_month_rmse[year-2009+slot//12, slot % 12] = np.sqrt(np.mean(err*err))
            year_month_bias[year-2009+slot//12, slot % 12] = err.mean()
        print("DESCRITIVO", year, flush=True)
    r = np.concatenate(residuals)
    observed = np.concatenate(observations)
    climo = np.concatenate(climates)
    s12 = np.concatenate(s12_values)
    dispersion = np.concatenate(stds)
    ratio = np.concatenate(ratios)
    member_anomaly = np.concatenate(mean_anomalies)
    same = np.concatenate(all_same)
    years = np.concatenate(year_codes)
    months = np.concatenate(month_codes)
    q90, q95 = np.quantile(np.abs(r), [.9, .95])
    sse = float(np.sum(r.astype(np.float64)**2))
    lat = np.tile(NORTH_LAT, 144)
    lon = np.tile(NORTH_LON, 144)
    lat_code = np.minimum((lat//5).astype(np.intp), 2)
    lon_code = np.minimum(((lon+90)//10).astype(np.intp), 6)
    sector = np.where(lon < -70, 0, np.where(lon < -50, 1, 2))
    groups = {}
    descriptions = {
        "latitude_5deg": (lat_code, 3),
        "longitude_10deg": (lon_code, 7),
        "latitude_x_longitude": (lat_code*7+lon_code, 21),
        "sector": (sector, 3),
        "month": (months, 12),
        "season": (((months+1) % 12)//3, 4),
        "year": (years, 12),
        "observed_intensity": (np.digitize(observed, [.5, 2, 5, 10, 20]), 6),
        "abs_observed_anomaly": (np.digitize(np.abs(observed-climo), [.5, 1, 2, 4]), 5),
        "direction": (np.where(r > 0, 1, 0), 2),
        "all_members_same_error_sign": (same.astype(np.intp), 2),
        "consensus_A": (np.digitize(ratio, [1, 2, 4, 8]), 5),
        "consensus_A_by_climatology":
            (np.digitize(ratio, [1, 2, 4, 8])*4+np.digitize(climo, [2, 5, 10]), 20),
        "consensus_A_by_predicted_anomaly":
            (np.digitize(ratio, [1, 2, 4, 8])*4+
             np.digitize(np.abs(s12-climo), [.5, 1, 2]), 20),
    }
    for name, (code, number) in descriptions.items():
        groups[name] = _group_stats(r, code, number, sse, q90)
    sorted_sse = np.sort(r.astype(np.float64)**2)[::-1]
    concentration = {
        f"top_{int(fraction*100)}pct_sse_fraction":
        float(sorted_sse[:int(np.ceil(len(sorted_sse)*fraction))].sum()/sse)
        for fraction in (.01, .05, .10)
    }
    output = {
        "reference": "S12", "region": "latitude 0 to 15N, all longitudes",
        "years": [2009, 2020], "count": len(r),
        "north_rmse": float(np.sqrt(sse/len(r))),
        "north_bias_observed_minus_s12": float(r.mean()),
        "q90_abs_residual_descriptive_only": float(q90),
        "q95_abs_residual_descriptive_only": float(q95),
        "sse_concentration": concentration,
        "groups": groups, "s12_prediction_hashes": hashes,
        "development_periods_reused": True, "no_test_targets": True,
    }
    save_json(OUT / "diagnostic.json", output)
    np.savez_compressed(ART / "diagnostic_maps.npz", sse=map_sse,
                        bias=map_bias_sum/144, year_month_rmse=year_month_rmse,
                        year_month_bias=year_month_bias)
    _plot_diagnostic(output, map_sse, map_bias_sum/144, year_month_rmse,
                     observed, r, climo, ratio)


def _plot_diagnostic(output: dict, map_sse: np.ndarray, map_bias: np.ndarray,
                     year_month_rmse: np.ndarray, observed: np.ndarray,
                     residual: np.ndarray, climo: np.ndarray,
                     ratio: np.ndarray) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm, PowerNorm
    OUT.mkdir(exist_ok=True, parents=True)
    fig, ax = plt.subplots(1, 2, figsize=(14, 4.6), constrained_layout=True)
    extent = [-90, -25, 0, 15]
    per_cell = map_sse/144
    display_ceiling = np.quantile(per_cell, .99)
    im0 = ax[0].imshow(np.minimum(per_cell, display_ceiling), origin="lower",
                       extent=extent, aspect="auto", cmap="magma",
                       norm=PowerNorm(gamma=.45, vmin=0, vmax=display_ceiling))
    fig.colorbar(im0, ax=ax[0], label="Erro quadrático médio (mm/dia)²; escala até P99")
    ax[0].set(title="SSE da S12 por célula (P99 visual)",
              xlabel="Longitude", ylabel="Latitude")
    bound = np.quantile(np.abs(map_bias), .98)
    im1 = ax[1].imshow(map_bias, origin="lower", extent=extent, aspect="auto",
                       cmap="RdBu_r", norm=TwoSlopeNorm(vcenter=0,
                                                       vmin=-bound, vmax=bound))
    fig.colorbar(im1, ax=ax[1], label="Viés observado − S12 (mm/dia)")
    ax[1].set(title="Direção média do erro", xlabel="Longitude", ylabel="Latitude")
    fig.savefig(OUT / "mapas_erro_norte.png", dpi=170)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    im = ax.imshow(year_month_rmse, aspect="auto", cmap="magma")
    fig.colorbar(im, ax=ax, label="RMSE (mm/dia)")
    ax.set(xticks=np.arange(12), xticklabels=["J","F","M","A","M","J","J","A","S","O","N","D"],
           yticks=np.arange(12), yticklabels=np.arange(2009, 2021),
           title="RMSE mensal S12 no norte", xlabel="Mês", ylabel="Ano")
    fig.savefig(OUT / "ano_mes_rmse.png", dpi=170)
    plt.close(fig)
    intensity = output["groups"]["observed_intensity"]
    anomaly = output["groups"]["abs_observed_anomaly"]
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2), constrained_layout=True)
    ax[0].bar(range(6), [100*v["sse_fraction"] for v in intensity], color="#326a9d")
    ax[0].set(xticks=range(6), xticklabels=["<0.5",".5–2","2–5","5–10","10–20",">=20"],
              title="SSE por chuva observada", ylabel="% do SSE norte")
    ax[1].bar(range(5), [100*v["sse_fraction"] for v in anomaly], color="#bd614e")
    ax[1].set(xticks=range(5), xticklabels=["<.5",".5–1","1–2","2–4",">=4"],
              title="SSE por |anomalia observada|", ylabel="% do SSE norte")
    fig.savefig(OUT / "intensidade_erro.png", dpi=170)
    plt.close(fig)
    a = output["groups"]["consensus_A"]
    fig, ax = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
    ax.plot(range(5), [v["rmse"] for v in a], marker="o", color="#255b81")
    ax.set(xticks=range(5), xticklabels=["<1","1–2","2–4","4–8",">=8"],
           title="Erro e razão de consenso A", xlabel="A", ylabel="RMSE (mm/dia)")
    fig.savefig(OUT / "consenso_A.png", dpi=170)
    plt.close(fig)


def _moments() -> dict:
    return dict(n=0, sy=0., sp=0., sy2=0., sp2=0., syp=0., sse=0.)


def _add_moments(row: dict, actual: np.ndarray, predicted: np.ndarray) -> None:
    y = np.asarray(actual, np.float64).ravel()
    p = np.asarray(predicted, np.float64).ravel()
    row["n"] += len(y)
    row["sy"] += y.sum()
    row["sp"] += p.sum()
    row["sy2"] += np.dot(y, y)
    row["sp2"] += np.dot(p, p)
    row["syp"] += np.dot(y, p)
    row["sse"] += np.sum((y-p)**2)


def _from_moments(row: dict) -> dict:
    n = row["n"]
    cy = row["sy2"]-row["sy"]**2/n
    cp = row["sp2"]-row["sp"]**2/n
    cov = row["syp"]-row["sy"]*row["sp"]/n
    return {
        "count": n,
        "rmse": float(np.sqrt(row["sse"]/n)),
        "zero_rmse": float(np.sqrt(row["sy2"]/n)),
        "r2_against_zero": float(1-row["sse"]/row["sy2"]),
        "r2_centered": float(1-row["sse"]/cy),
        "correlation": float(cov/np.sqrt(cy*cp)) if cp > 0 else None,
    }


def _strata_code() -> dict[str, np.ndarray]:
    sector = np.where(NORTH_LON < -70, 0, np.where(NORTH_LON < -50, 1, 2))
    return {
        "west": sector == 0,
        "central": sector == 1,
        "east": sector == 2,
    }


def _aggregate_conditional(reports: dict[int, dict]) -> list[dict]:
    bins = {}
    for cutoff, report in reports.items():
        for row in report["conditional"]:
            key = (row["feature"], row["bin"])
            dest = bins.setdefault(key, dict(count=0, under=0., critical=0.,
                                             sse=0., sum_residual=0.))
            n = row["count"]
            dest["count"] += n
            dest["under"] += n*row["under_probability"]
            dest["critical"] += n*row["critical_probability"]
            dest["sse"] += n*row["rmse"]**2
            dest["sum_residual"] += n*row["mean_residual"]
    total = sum(row["sse"] for key, row in bins.items() if key[0] == "month")
    return [
        {"feature": feature, "bin": group, "count": row["count"],
         "under_probability": row["under"]/row["count"],
         "critical_probability": row["critical"]/row["count"],
         "mean_residual": row["sum_residual"]/row["count"],
         "rmse": float(np.sqrt(row["sse"]/row["count"])),
         "sse_fraction": row["sse"]/total}
        for (feature, group), row in sorted(bins.items())
    ]


def _aggregate_consensus(reports: dict[int, dict]) -> list[dict]:
    bins = {}
    for report in reports.values():
        for row in report["consensus"]:
            key = (row["group_family"], row["group"])
            dest = bins.setdefault(key, dict(count=0, under=0., critical=0.,
                                             sse=0., climo=0., pred_anomaly=0.))
            n = row["count"]
            dest["count"] += n
            dest["under"] += n*row["under_probability"]
            dest["critical"] += n*row["critical_probability"]
            dest["sse"] += n*row["rmse"]**2
            dest["climo"] += n*row["mean_climatology"]
            dest["pred_anomaly"] += n*row["mean_predicted_anomaly_magnitude"]
    total = sum(row["sse"] for key, row in bins.items() if key[0] == "A")
    return [
        {"family": family, "bin": group, "count": row["count"],
         "under_probability": row["under"]/row["count"],
         "critical_probability": row["critical"]/row["count"],
         "rmse": float(np.sqrt(row["sse"]/row["count"])),
         "sse_fraction": row["sse"]/total,
         "mean_climatology": row["climo"]/row["count"],
         "mean_predicted_anomaly_magnitude": row["pred_anomaly"]/row["count"]}
        for (family, group), row in sorted(bins.items())
    ]


def _classification(groups: dict, details: dict, binary: dict) -> tuple[str, list[str]]:
    evidence = []
    direction_ok = sum(
        1 for block in binary.values()
        if block["direction"]["block"]["auc"] is not None
        and block["direction"]["block"]["auc"] >= .53
        and block["direction"]["block"]["brier_gain"] > 0)
    critical_ok = sum(
        1 for block in binary.values()
        if block["critical_q90"]["block"]["auc"] is not None
        and block["critical_q90"]["block"]["auc"] >= .55
        and block["critical_q90"]["block"]["top_decile_lift"] >= 1.2
        and block["critical_q90"]["block"]["brier_gain"] > 0)
    baseline_r2 = groups["base"]["r2_against_zero"]
    for name, stats in groups.items():
        if name == "full_hgb":
            continue
        fold_positive = sum(details["fold"][name][str(y)]["r2_against_zero"] > 0 for y in EVAL)
        year_positive = sum(
            details["year"][name][str(y)]["r2_against_zero"] > 0
            for y in range(2011, 2021))
        if (stats["r2_against_zero"] >= .005
            and stats["r2_against_zero"]-baseline_r2 >= .002
            and fold_positive >= 4 and year_positive >= 7
            and groups["full_hgb"]["r2_against_zero"] > 0
            and max(direction_ok, critical_ok) >= 4):
            evidence.append(f"{name}: ganho global e preditores binários estáveis")
            return "A", evidence
    for name, areas in details["strata"].items():
        for area, row in areas.items():
            if area == "global":
                continue
            positive_folds = sum(v["r2_against_zero"] > 0 for v in row["fold"].values())
            positive_years = sum(v["r2_against_zero"] > 0 for v in row["year"].values())
            if (row["pooled"]["r2_against_zero"] > 0 and positive_folds >= 3
                and positive_years >= 6 and row["pooled"]["count"] >= .1*5*24*NORTH_SIZE):
                evidence.append(
                    f"{name} em {area}: {positive_folds}/5 blocos e "
                    f"{positive_years}/10 anos positivos")
    if evidence:
        return "B", evidence
    return "C", [
        "Nenhum grupo passou os critérios globais de A nem os critérios "
        "de setor/estação estável de B.",
        f"Direção: {direction_ok}/5 blocos com AUC/Brier úteis; "
        f"Q90: {critical_ok}/5 blocos com AUC/lift/Brier úteis.",
    ]


def summarize() -> None:
    locked()
    diagnostic_report = json.loads((OUT / "diagnostic.json").read_text(encoding="utf-8"))
    reports = {year: json.loads((OUT / f"{year}_predictability.json").read_text(encoding="utf-8"))
               for year in EVAL}
    group_names = list(GROUPS)+["full_hgb"]
    pooled = {name: _moments() for name in group_names}
    fold = {name: {} for name in group_names}
    annual = {name: {} for name in group_names}
    strata = {name: {} for name in group_names}
    space = _strata_code()
    for name in group_names:
        for area in ("west", "central", "east", "DJF", "MAM", "JJA", "SON"):
            strata[name][area] = {
                "pooled_moments": _moments(), "fold": {}, "year": {},
            }
    all_residual, all_direction, all_critical = [], [], []
    all_dir_probability, all_crit_probability = [], []
    for cutoff in EVAL:
        path = ART / f"{cutoff}_oof.npz"
        meta = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        if digest(path) != meta["sha256"] or meta["last_training_target"] != f"{cutoff-1}-12":
            raise ValueError("Arquivo OOF alterado ou corte incorreto")
        with np.load(path) as saved:
            truth = np.asarray(saved["residual"], np.float64)
            predicted = np.asarray(saved["predictions"], np.float64)
            pdir = np.asarray(saved["direction_probability"], np.float64)
            pcrit = np.asarray(saved["critical_probability"], np.float64)
        if predicted.shape != (len(group_names), 24, NORTH_SIZE):
            raise ValueError("Formato da matriz OOF incorreto")
        all_residual.append(truth.ravel())
        all_direction.append((truth > 0).ravel())
        all_critical.append(
            (np.abs(truth) > reports[cutoff]["q90_training_abs_residual"]).ravel())
        all_dir_probability.append(pdir.ravel())
        all_crit_probability.append(pcrit.ravel())
        for j, name in enumerate(group_names):
            value = predicted[j]
            _add_moments(pooled[name], truth, value)
            fold[name][str(cutoff)] = _score(truth, value)
            annual[name][str(cutoff)] = _score(truth[:12], value[:12])
            annual[name][str(cutoff+1)] = _score(truth[12:], value[12:])
            for area, selected in space.items():
                m = strata[name][area]
                y, p = truth[:, selected], value[:, selected]
                _add_moments(m["pooled_moments"], y, p)
                m["fold"][str(cutoff)] = _score(y, p)
                m["year"][str(cutoff)] = _score(y[:12], p[:12])
                m["year"][str(cutoff+1)] = _score(y[12:], p[12:])
            months = (np.arange(24) % 12)+1
            season_code = (months % 12)//3
            for k, season in enumerate(("DJF", "MAM", "JJA", "SON")):
                selected = season_code == k
                m = strata[name][season]
                y, p = truth[selected], value[selected]
                _add_moments(m["pooled_moments"], y, p)
                m["fold"][str(cutoff)] = _score(y, p)
                for yr in (cutoff, cutoff+1):
                    sub = selected & (np.arange(24)//12 == yr-cutoff)
                    m["year"][str(yr)] = _score(truth[sub], value[sub])
    groups = {name: _from_moments(moments) for name, moments in pooled.items()}
    for name in group_names:
        for area in strata[name]:
            m = strata[name][area]
            m["pooled"] = _from_moments(m.pop("pooled_moments"))
    details = {"fold": fold, "year": annual, "strata": strata}
    classification, reasons = _classification(
        groups, details, {year: row["binary_metrics"] for year, row in reports.items()})
    observed_direction = np.concatenate(all_direction)
    observed_critical = np.concatenate(all_critical)
    predicted_direction = np.concatenate(all_dir_probability)
    predicted_critical = np.concatenate(all_crit_probability)
    binary_pooled = {
        "direction": _binary_score(observed_direction, predicted_direction,
                                   float(observed_direction.mean())),
        "critical_q90": _binary_score(observed_critical, predicted_critical,
                                      float(observed_critical.mean()), True),
    }
    for key in binary_pooled:
        baseline = np.mean([reports[y]["binary_metrics"][key]["block"]
                            ["baseline_brier"] for y in EVAL])
        binary_pooled[key]["baseline_brier"] = float(baseline)
        binary_pooled[key]["brier_gain"] = float(baseline-binary_pooled[key]["brier"])
        binary_pooled[key].pop("prior_from_training")
        binary_pooled[key]["prior_varies_by_fold"] = True
    output = {
        "classification": classification, "classification_reasons": reasons,
        "reference": "S12", "region": "latitude 0 to 15N",
        "descriptive_blocks": YEARS, "predictive_blocks": EVAL,
        "first_block_unscored_reason":
            "Nenhum resíduo S12 OOF anterior a 2009–2010 disponível.",
        "pooled_groups": groups, "details": details,
        "binary_pooled": binary_pooled,
        "binary_per_fold": {str(k): v["binary_metrics"] for k, v in reports.items()},
        "conditional_pooled": _aggregate_conditional(reports),
        "consensus_pooled": _aggregate_consensus(reports),
        "extreme_contrasts_by_fold": {str(k): v["extreme_contrasts"]
                                      for k, v in reports.items()},
        "diagnostic_north_rmse": diagnostic_report["north_rmse"],
        "selection_bias": "Blocos históricos repetidamente reutilizados; resultado exploratório.",
        "no_2023_2024_targets": True, "no_candidate": True,
    }
    save_json(OUT / "summary.json", output)
    _plot_predictability(output)
    _write_report(output, diagnostic_report)
    print("CLASSIFICACAO", classification, flush=True)
    for name, row in sorted(groups.items(), key=lambda item: -item[1]["r2_against_zero"]):
        print(name, round(row["r2_against_zero"], 6),
              round(row["rmse"], 6), flush=True)


def _plot_predictability(result: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = list(GROUPS)+["full_hgb"]
    values = [100*result["pooled_groups"][name]["r2_against_zero"] for name in names]
    fig, ax = plt.subplots(figsize=(10, 5.5), constrained_layout=True)
    colors = ["#28628c" if name not in ("base", "full_hgb") else "#b96547"
              for name in names]
    ax.barh(names[::-1], values[::-1], color=colors[::-1])
    ax.axvline(0, color="black", lw=.8)
    ax.set(xlabel="R² contra resíduo zero (%)", title="Previsão OOF do erro S12: 2011–2020")
    fig.savefig(OUT / "r2_grupos.png", dpi=170)
    plt.close(fig)

    matrix = np.array([[100*result["details"]["fold"][name][str(year)]
                        ["r2_against_zero"] for year in EVAL] for name in names])
    bound = max(.5, np.max(np.abs(matrix)))
    fig, ax = plt.subplots(figsize=(9, 5.8), constrained_layout=True)
    im = ax.imshow(matrix, cmap="RdBu", vmin=-bound, vmax=bound, aspect="auto")
    ax.set(xticks=np.arange(5), xticklabels=[f"{y}–{y+1}" for y in EVAL],
           yticks=np.arange(len(names)), yticklabels=names,
           title="R² contra zero por corte OOF (%)", xlabel="Bloco de validação")
    for i in range(len(names)):
        for j in range(5):
            ax.text(j, i, f"{matrix[i,j]:.2f}", ha="center", va="center", fontsize=7,
                    color="white" if abs(matrix[i,j]) > .6*bound else "black")
    fig.colorbar(im, ax=ax, label="R² contra zero (%)")
    fig.savefig(OUT / "r2_blocos.png", dpi=170)
    plt.close(fig)

    binary = result["binary_per_fold"]
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2), constrained_layout=True)
    for name, color, label in (("direction", "#22688b", "Direção"),
                               ("critical_q90", "#b4514a", "Erro > Q90")):
        auc = [binary[str(y)][name]["block"]["auc"] for y in EVAL]
        gain = [binary[str(y)][name]["block"]["brier_gain"] for y in EVAL]
        ax[0].plot(EVAL, auc, marker="o", label=label, color=color)
        ax[1].plot(EVAL, gain, marker="o", label=label, color=color)
    ax[0].axhline(.5, color="gray", ls="--", lw=.8)
    ax[1].axhline(0, color="gray", ls="--", lw=.8)
    ax[0].set(title="Discriminação OOF", xlabel="Início do bloco", ylabel="AUC")
    ax[1].set(title="Ganho de Brier sobre prior anterior", xlabel="Início do bloco",
              ylabel="Brier base − Brier modelo")
    for a in ax:
        a.legend()
        a.set_xticks(EVAL)
    fig.savefig(OUT / "classificadores_blocos.png", dpi=170)
    plt.close(fig)

    rows = [r for r in result["consensus_pooled"] if r["family"] == "A"]
    rows.sort(key=lambda r: r["bin"])
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), constrained_layout=True)
    labels = ["<1", "1–2", "2–4", "4–8", "≥8"]
    ax[0].bar(labels, [100*r["critical_probability"] for r in rows], color="#bd614e")
    ax[0].set(title="Risco de erro > Q90 por A", xlabel="A", ylabel="% de casos")
    ax[1].bar(labels, [100*r["sse_fraction"] for r in rows], color="#326a9d")
    ax[1].set(title="Participação no SSE por A", xlabel="A", ylabel="% do SSE")
    fig.savefig(OUT / "consenso_previsibilidade.png", dpi=170)
    plt.close(fig)


def _write_report(result: dict, diagnostic_report: dict) -> None:
    def pct(x: float) -> str:
        return f"{100*x:.2f}%"

    def num(x: float | None, places: int = 3) -> str:
        return "—" if x is None else f"{x:.{places}f}"

    groups = diagnostic_report["groups"]
    lines = [
        "# Rodada 26 — previsibilidade do erro comum S12 no norte",
        "",
        f"**Conclusão predefinida: {result['classification']}.** " + " ".join(result["classification_reasons"]),
        "",
        "## Delineamento e validade",
        "",
        "Referência fixa S12; resíduo = observado − S12. Região 0–15°N, "
        f"{NORTH_SIZE:,} células por mês. Os seis blocos de 2009–2020 entram "
        "no diagnóstico descritivo. O primeiro bloco (2009–2010) não pode "
        "receber uma previsão de resíduo temporalmente OOF, pois não há "
        "resíduos S12 OOF anteriores. Os cinco blocos seguintes são avaliados "
        "com treino expansivo apenas em blocos anteriores. Foram usados "
        f"{SAMPLE} pontos norte por mês de treino, e todas as células na validação.",
        "",
        "Climatologia, médias meteorológicas, PCs, padronização e limiares "
        "de extremo são ajustados antes de cada corte. O mesmo referencial PCA "
        "do corte transforma os meses históricos e o bloco avaliado. "
        "As medidas por pixel não representam réplicas independentes; os "
        "blocos e anos mostram a estabilidade temporal. Os dados de 2023/2024 "
        "e o leaderboard não foram consultados nesta rodada.",
        "",
        "## 1. Onde está o erro da S12?",
        "",
        f"RMSE norte nos seis blocos: **{num(diagnostic_report['north_rmse'])} mm/dia**; "
        f"viés observado − S12: **{num(diagnostic_report['north_bias_observed_minus_s12'])} mm/dia**. "
        f"Q90 descritivo |r| = {num(diagnostic_report['q90_abs_residual_descriptive_only'])}; "
        f"Q95 = {num(diagnostic_report['q95_abs_residual_descriptive_only'])} mm/dia. "
        "Esses quantis globais só descrevem o período; cada corte preditivo usa "
        "seu próprio limiar anterior.",
        "",
        "| Fração de pontos de maior erro | Fração do SSE norte |",
        "| --- | ---: |",
    ]
    for k in (1, 5, 10):
        lines.append(f"| {k}% | {pct(diagnostic_report['sse_concentration'][f'top_{k}pct_sse_fraction'])} |")
    lines += ["", "### Divisão espacial e temporal", "",
              "Cada coluna de SSE soma 100% dentro de seu agrupamento; "
              "a fração de pontos ajuda a distinguir concentração de área extensa.",
              "", "| Dimensão | Faixa | Pontos | SSE | RMSE | Viés | P(subestimação) |",
              "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    labels = {
        "latitude_5deg": ["0–5°N", "5–10°N", "10–15°N"],
        "longitude_10deg": ["90–80°W", "80–70°W", "70–60°W", "60–50°W",
                              "50–40°W", "40–30°W", "30–25°W"],
        "sector": ["oeste", "centro", "leste"],
        "season": ["DJF", "MAM", "JJA", "SON"],
    }
    for family in ("latitude_5deg", "longitude_10deg", "sector", "season"):
        for row in groups[family]:
            name = labels[family][row["group"]]
            lines.append(f"| {family} | {name} | {pct(row['count_fraction'])} | "
                         f"{pct(row['sse_fraction'])} | {num(row['rmse'])} | "
                         f"{num(row['bias_observed_minus_s12'])} | "
                         f"{pct(row['under_probability'])} |")
    lines += ["", "### Matriz latitude × longitude", "",
              "Cada célula mostra a fração do SSE total norte nos seis blocos.", "",
              "| Latitude / longitude | 90–80°W | 80–70°W | 70–60°W | 60–50°W | 50–40°W | 40–30°W | 30–25°W |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    cross = groups["latitude_x_longitude"]
    for i, lat_label in enumerate(labels["latitude_5deg"]):
        cells = [pct(cross[7*i+j]["sse_fraction"]) for j in range(7)]
        lines.append("| " + lat_label + " | " + " | ".join(cells) + " |")
    lines += ["", "### Ano", "",
              "| Ano | SSE norte | RMSE | Viés |",
              "| ---: | ---: | ---: | ---: |"]
    for row in groups["year"]:
        lines.append(f"| {2009+row['group']} | {pct(row['sse_fraction'])} | "
                     f"{num(row['rmse'])} | {num(row['bias_observed_minus_s12'])} |")
    lines += ["", "### Intensidade observada e anomalia observada", "",
              "Estas duas variáveis são rótulos diagnósticos obtidos com a chuva "
              "real; não são elegíveis como sinal para um modelo operacional.", "",
              "| Critério | Faixa (mm/dia) | Pontos | SSE | RMSE |",
              "| --- | --- | ---: | ---: | ---: |"]
    for family, names in (("observed_intensity", ["<0,5", "0,5–2", "2–5", "5–10", "10–20", "≥20"]),
                          ("abs_observed_anomaly", ["<0,5", "0,5–1", "1–2", "2–4", "≥4"])):
        for row in groups[family]:
            lines.append(f"| {family} | {names[row['group']]} | "
                         f"{pct(row['count_fraction'])} | {pct(row['sse_fraction'])} | "
                         f"{num(row['rmse'])} |")
    same = groups["all_members_same_error_sign"][1]
    lines += ["", f"Os cinco componentes erram no mesmo sentido em "
              f"{pct(same['count_fraction'])} dos pontos norte; esses pontos "
              f"reúnem {pct(same['sse_fraction'])} do SSE. Essa condição "
              "depende do observado e serve apenas para descrever o erro. "
              "A série completa de 12 meses e a decomposição cruzada estão "
              "em [diagnostic.json](diagnostic.json).", "",
              "Os mapas e perfis permitem ver a geometria do erro:", "",
              "![SSE e viés no norte](mapas_erro_norte.png)", "",
              "![RMSE por ano e mês](ano_mes_rmse.png)", "",
              "![SSE por intensidade e anomalia](intensidade_erro.png)", "",
              "## 2. Resíduo previsível em blocos OOF?", "",
              "R² contra zero mede redução do SSE da S12; valor negativo "
              "significa piora. A base inclui localização, mês, climatologia "
              "e S12. Cada linha adiciona a família indicada à mesma base. "
              "O HGB é apenas uma checagem não linear fixa.", "",
              "| Grupo | R² zero | Δ vs base (p.p.) | RMSE r | Correlação | Blocos positivos | Anos positivos |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    base_r2 = result["pooled_groups"]["base"]["r2_against_zero"]
    for name, row in result["pooled_groups"].items():
        bf = sum(result["details"]["fold"][name][str(y)]["r2_against_zero"] > 0 for y in EVAL)
        yr = sum(result["details"]["year"][name][str(y)]["r2_against_zero"] > 0
                 for y in range(2011, 2021))
        lines.append(f"| {name} | {pct(row['r2_against_zero'])} | "
                     f"{100*(row['r2_against_zero']-base_r2):+.3f} | "
                     f"{num(row['rmse'])} | {num(row['correlation'])} | "
                     f"{bf}/5 | {yr}/10 |")
    lines += ["", "![R² por grupos](r2_grupos.png)", "",
              "![R² por bloco](r2_blocos.png)", "",
              "### Onde o sinal aparece ou desaparece", "",
              "A tabela abaixo mostra os melhores subconjuntos espaciais e "
              "sazonais predefinidos. É uma análise exploratória entre vários "
              "grupos, e nenhuma linha isolada estabelece ganho norte inteiro.", "",
              "| Grupo | Setor/estação | R² zero | Blocos positivos | Anos positivos |",
              "| --- | --- | ---: | ---: | ---: |"]
    ranked = []
    for name, areas in result["details"]["strata"].items():
        for area, row in areas.items():
            bf = sum(v["r2_against_zero"] > 0 for v in row["fold"].values())
            yr = sum(v["r2_against_zero"] > 0 for v in row["year"].values())
            ranked.append((row["pooled"]["r2_against_zero"], name, area, bf, yr))
    for r2, name, area, bf, yr in sorted(ranked, reverse=True)[:12]:
        lines.append(f"| {name} | {area} | {pct(r2)} | {bf}/5 | {yr}/10 |")
    lines += ["", "Os resultados de todas as áreas, blocos e anos estão em "
              "[summary.json](summary.json).", "", "## 3. Direção do erro", "",
              "Subestimação significa observado > S12. As tabelas condicionais "
              "por mês, latitude, longitude e quintis de atributos disponíveis "
              "em inferência estão em [summary.json](summary.json), campo "
              "`conditional_pooled`; os limites dos quintis vêm do treino "
              "anterior a cada corte. A classificação binária usa Ridge "
              "com o conjunto completo, com prior constante aprendido "
              "anteriormente.", "",
              "| Bloco | P(subestimação) | AUC direção | Ganho Brier direção | "
              "P(erro > Q90) | AUC Q90 | AP Q90 | Lift decil Q90 | Ganho Brier Q90 |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for y in EVAL:
        d = result["binary_per_fold"][str(y)]["direction"]["block"]
        c = result["binary_per_fold"][str(y)]["critical_q90"]["block"]
        lines.append(f"| {y}–{y+1} | {pct(d['prevalence'])} | {num(d['auc'])} | "
                     f"{num(d['brier_gain'], 5)} | {pct(c['prevalence'])} | "
                     f"{num(c['auc'])} | {num(c['average_precision'])} | "
                     f"{num(c['top_decile_lift'], 2)}× | {num(c['brier_gain'], 5)} |")
    lines += ["", "![Classificadores por bloco](classificadores_blocos.png)", "",
              "### Taxas condicionais de subestimação e de erro crítico", "",
              "As faixas 0 e 4 são os extremos dos quintis definidos no "
              "treino de cada corte. As frequências são agregadas nos cinco "
              "blocos OOF; uma diferença entre bins não garante "
              "discriminação temporal útil.", "",
              "| Atributo | Bin | P(subestimação) | P(erro > Q90) | RMSE |",
              "| --- | ---: | ---: | ---: | ---: |"]
    for feature in ("climatology", "s12_anomaly", "member_std", "consensus_ratio"):
        for row in result["conditional_pooled"]:
            if row["feature"] == feature and row["bin"] in (0, 4):
                lines.append(f"| {feature} | {row['bin']} | "
                             f"{pct(row['under_probability'])} | "
                             f"{pct(row['critical_probability'])} | "
                             f"{num(row['rmse'])} |")
    lines += ["",
              "## 4. Extremos Q90 e Q95", "",
              "Cada Q90/Q95 é calculado com resíduos S12 OOF de todos os "
              "blocos norte anteriores, sem usar o bloco avaliado. AUC, "
              "average precision, Brier e lift se referem ao evento Q90; "
              "Q95 recebe somente comparação descritiva. AP deve ser lido "
              "junto à prevalência do próprio bloco. Diferença padronizada "
              "de média (extremo menos normal, em desvios combinados) por "
              "feature e corte está em [summary.json](summary.json), campo "
              "`extreme_contrasts_by_fold`. A distribuição em quintis aparece "
              "em `conditional_pooled`. Esses contrastes usam os rótulos "
              "reais para caracterizar o erro; só features disponíveis antes "
              "da previsão entraram no classificador.", "",
              "| Bloco | Q90 anterior | Q95 anterior | Eventos Q90 | Eventos Q95 |",
              "| --- | ---: | ---: | ---: | ---: |"]
    for y in EVAL:
        report = json.loads((OUT / f"{y}_predictability.json").read_text(encoding="utf-8"))
        q95_count = next(row["extreme_count"] for row in report["extreme_contrasts"]
                         if row["threshold"] == "q95")
        lines.append(f"| {y}–{y+1} | {num(report['q90_training_abs_residual'])} | "
                     f"{num(report['q95_training_abs_residual'])} | "
                     f"{pct(report['binary_metrics']['critical_q90']['block']['prevalence'])} | "
                     f"{pct(q95_count/(24*NORTH_SIZE))} |")
    contrast = {}
    for rows in result["extreme_contrasts_by_fold"].values():
        for row in rows:
            if row["threshold"] == "q90":
                contrast.setdefault(row["feature"], []).append(
                    row["standardized_mean_difference"])
    ranked_contrast = sorted(contrast.items(),
                             key=lambda kv: -abs(np.mean(kv[1])))[:8]
    lines += ["", "Os maiores contrastes médios Q90 entre cinco blocos "
              "(positivo = maior entre extremos):", "",
              "| Atributo | Diferença padronizada média | Faixa entre blocos |",
              "| --- | ---: | ---: |"]
    for feature, values in ranked_contrast:
        lines.append(f"| {feature} | {np.mean(values):+.3f} | "
                     f"{min(values):+.3f} a {max(values):+.3f} |")
    lines += ["", "A climatologia e a dispersão entre componentes têm "
              "forte associação marginal com a criticidade. O valor previsto "
              "e a climatologia já são capazes de ordenar parte substancial "
              "do risco; a seção final distingue esse efeito de ganho novo "
              "dos atributos adicionais."]
    lines += ["", "## 5. Consenso excessivo", "",
              "A = |média dos componentes − climatologia| / "
              "(desvio padrão dos componentes + 0,1). Erro simultâneo no "
              "mesmo sentido de todos os componentes é diagnóstico baseado "
              "no observado, jamais feature. O risco abaixo usa Q90 anterior "
              "de cada corte, e cobre 2011–2020.", "",
              "| A | Pontos | RMSE | Risco Q90 | P(subestimação) | SSE |",
              "| --- | ---: | ---: | ---: | ---: | ---: |"]
    a = sorted([r for r in result["consensus_pooled"] if r["family"] == "A"],
               key=lambda r: r["bin"])
    for label, row in zip(["<1", "1–2", "2–4", "4–8", "≥8"], a):
        lines.append(f"| {label} | {row['count']:,} | {num(row['rmse'])} | "
                     f"{pct(row['critical_probability'])} | "
                     f"{pct(row['under_probability'])} | {pct(row['sse_fraction'])} |")
    lines += ["", "### A condicionado ao nível climatológico", "",
              "Risco Q90 em três faixas de A, dentro de cada classe de "
              "climatologia. As células com poucos casos devem ser lidas "
              "com cautela.", "",
              "| Climatologia (mm/dia) | A<1 | A 1–2 | A 2–4 |",
              "| --- | ---: | ---: | ---: |"]
    by_climo = {(r["bin"]//4, r["bin"]%4): r for r in result["consensus_pooled"]
                if r["family"] == "A_by_climatology"}
    for climo_bin, label in enumerate(["<2", "2–5", "5–10", "≥10"]):
        values = []
        for a_bin in (0, 1, 2):
            row = by_climo.get((a_bin, climo_bin))
            values.append(f"{pct(row['critical_probability'])} (n={row['count']:,})"
                          if row else "—")
        lines.append("| " + label + " | " + " | ".join(values) + " |")
    lines += ["", "O cruzamento de A com climatologia e magnitude da anomalia "
              "prevista está em [summary.json](summary.json), campo "
              "`consensus_pooled`. Uma associação que desapareça após essa "
              "estratificação não sugere sinal novo de consenso.", "",
              "![Risco e SSE por A](consenso_previsibilidade.png)", "",
              "## Juízo científico", ""]
    audit_path = OUT / "audit.json"
    if audit_path.exists():
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        lines += ["A checagem adicional abaixo, calculada depois do teste "
                  "principal e sem ajustar pesos, mostra quanta discriminação "
                  "de Q90 já existe nas referências de intensidade chuvosa. "
                  "AUC é independente de calibração; climatologia e S12 "
                  "entram apenas como ordenadores fixos.", "",
                  "| Bloco | AUC climatologia | AUC S12 | AUC classificador completo |",
                  "| --- | ---: | ---: | ---: |"]
        for row in audit["q90_unfitted_rank_baselines_posthoc"]:
            lines.append(f"| {row['cutoff']}–{row['cutoff']+1} | "
                         f"{num(row['auc_q90_climatology_only_unfitted'])} | "
                         f"{num(row['auc_q90_s12_only_unfitted'])} | "
                         f"{num(row['auc_q90_full_trained'])} |")
        lines += ["", "A maior parte da ordenação do risco crítico já aparece "
                  "na climatologia e na própria S12; o incremento do "
                  "classificador completo é pequeno e nem sempre positivo "
                  "frente à S12 simples. A verificação de hashes, resíduos, "
                  "limiares e escores está em [audit.json](audit.json).", ""]
    lines += [f"**Classificação {result['classification']} para o valor do "
              f"resíduo.** " + " ".join(result["classification_reasons"]),
              "", "Há previsibilidade do **risco de erro extremo**, "
              "principalmente associada ao regime chuvoso, mas não se obteve "
              "uma previsão estável da direção nem redução OOF do SSE por "
              "correção do valor do resíduo. Para um eventual ensaio futuro, "
              "um indicador de incerteza deve ser comparado a climatologia "
              "e intensidade S12, validado em blocos posteriores e separado "
              "de qualquer correção/gating de previsão. O gradiente bruto "
              "de A não demonstrou ganho incremental estável.", "",
              "Este é um estudo exploratório em blocos históricos "
              "reutilizados na construção do projeto; há viés de seleção. "
              "Nenhuma correção foi somada à S12, nenhum gating foi construído "
              "e nenhuma candidata foi criada. "
              "[Protocolo](../../../experiments/ROUND26.md).",
              ""]
    (OUT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def selfcheck() -> None:
    assert NORTH_SIZE == 15921
    assert len(FEATURE_NAMES) == WIDTH
    assert set(np.concatenate([CORE, LOCAL, CONT, TROP, MEMBERS, CONSENSUS])) == set(range(WIDTH))
    assert len(_sample_cells(0)) == SAMPLE
    assert np.array_equal(_sample_cells(0), _sample_cells(0))
    y = np.array([-2., 1., 3.])
    assert _score(y, y)["r2_against_zero"] == 1.
    assert _score(y, np.zeros_like(y))["r2_against_zero"] == 0.
    assert np.array_equal(_strata_code()["west"] | _strata_code()["central"] |
                          _strata_code()["east"], np.ones(NORTH_SIZE, bool))
    print("SELF CHECK OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["selfcheck", "diagnostic", "evaluate", "summarize", "all"])
    stage = parser.parse_args().stage
    if stage == "selfcheck":
        selfcheck()
    if stage in ("diagnostic", "all"):
        diagnostic()
    if stage in ("evaluate", "all"):
        evaluate()
    if stage in ("summarize", "all"):
        summarize()
