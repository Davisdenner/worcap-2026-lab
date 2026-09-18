"""Rodada 27: oracle e seleção temporal S12 versus análogos."""
from __future__ import annotations

import os
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, log_loss

from .competition import CACHE, ROOT, REPORT, save_json
from .round2 import target_origins
from . import round20, round25, round26

OUT = REPORT / "round27"
ART = ROOT / "data/processed/round27"
PROTOCOL = ROOT / "experiments/ROUND27.md"
YEARS = (2009, 2011, 2013, 2015, 2017, 2019)
EVAL = YEARS[1:]
GRID = round25.GRID
NORTH = round26.NORTH
NORTH_SIZE = round26.NORTH_SIZE
LAT = round25.LAT
LON = round25.LON


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def locked() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    paths = {
        str(y): {
            "s12": round20.ART / f"{y}_s12.npy",
            "analog": round25.ART / f"{y}_h4_prediction.npy",
            **({"risk_q90": round26.ART / f"{y}_oof.npz"} if y in EVAL else {}),
        }
        for y in YEARS
    }
    record = {
        "protocol_sha256": sha(PROTOCOL),
        "input_hashes": {year: {name: sha(path) for name, path in row.items()}
                         for year, row in paths.items()},
        "reference": "S12", "alternative": "Round25 H4 pure analog",
        "north_cells": NORTH_SIZE, "descriptive_blocks": YEARS,
        "risk_and_predictive_blocks": EVAL,
        "official_only": True, "no_test_targets": True,
        "no_submission": True,
    }
    path = OUT / "protocol.json"
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != json.loads(json.dumps(record)):
            raise ValueError("Protocolo ou previsões OOF congeladas mudaram")
    else:
        save_json(path, record)


def source(year: int, tp: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    s12 = round20.reference(year).reshape(24, GRID)
    analog = np.load(round25.ART / f"{year}_h4_prediction.npy", mmap_mode="r").reshape(24, GRID)
    truth = tp[target_origins(year)+1]
    return np.asarray(truth), np.asarray(s12), np.asarray(analog)


def moments(truth: np.ndarray, s12: np.ndarray, analog: np.ndarray,
            axis: int | None = None) -> dict:
    e12 = np.asarray(truth, np.float64)-np.asarray(s12, np.float64)
    ea = np.asarray(truth, np.float64)-np.asarray(analog, np.float64)
    l12, la = e12*e12, ea*ea
    wins = la < l12
    lo = np.minimum(l12, la)
    if axis is not None:
        l12, la, lo, wins = (np.sum(l12, axis=axis), np.sum(la, axis=axis),
                              np.sum(lo, axis=axis), np.sum(wins, axis=axis))
        count = truth.shape[axis]
    else:
        l12, la, lo, wins = (float(l12.sum()), float(la.sum()), float(lo.sum()),
                              int(wins.sum()))
        count = truth.size
    return {"count": count, "sse_s12": l12, "sse_analog": la,
            "sse_oracle": lo, "analog_wins": wins}


def combine(rows: list[dict]) -> dict:
    counts = {key: sum(row[key] for row in rows)
              for key in ("count", "sse_s12", "sse_analog", "sse_oracle", "analog_wins")}
    n = counts["count"]
    a, b, o = (float(counts[key]) for key in ("sse_s12", "sse_analog", "sse_oracle"))
    return {
        **counts, "rmse_s12": float(np.sqrt(a/n)),
        "rmse_analog": float(np.sqrt(b/n)), "rmse_oracle": float(np.sqrt(o/n)),
        "analog_win_fraction": float(counts["analog_wins"]/n),
        "analog_gain_percent": float(100*(1-np.sqrt(b/a))),
        "oracle_gain_percent": float(100*(1-np.sqrt(o/a))),
        "oracle_sse_reduction_percent": float(100*(1-o/a)),
    }


def _risk_deciles(year: int, truth: np.ndarray, s12: np.ndarray,
                  analog: np.ndarray) -> list[dict]:
    with np.load(round26.ART / f"{year}_oof.npz") as saved:
        risk = np.asarray(saved["critical_probability"], np.float64).ravel()
        reference_residual = np.asarray(saved["residual"], np.float64).ravel()
    np.testing.assert_allclose(reference_residual,
                               (truth[:, NORTH]-s12[:, NORTH]).ravel(),
                               atol=2e-6, rtol=0)
    order = np.argsort(risk, kind="stable")
    t = truth[:, NORTH].ravel()
    p = s12[:, NORTH].ravel()
    a = analog[:, NORTH].ravel()
    rows = []
    total_sse = np.sum((t.astype(np.float64)-p.astype(np.float64))**2)
    for decile, selected in enumerate(np.array_split(order, 10), start=1):
        stats = combine([moments(t[selected], p[selected], a[selected])])
        rows.append({"block": year, "risk_decile": decile,
                     "risk_min": float(risk[selected].min()),
                     "risk_max": float(risk[selected].max()),
                     "s12_sse_fraction": float(stats["sse_s12"]/total_sse),
                     "mean_D": float((stats["sse_s12"]-stats["sse_analog"])
                                     /stats["count"]), **stats})
    return rows


def oracle() -> None:
    locked()
    tp = np.load(CACHE / "tp.npy", mmap_mode="r").reshape(-1, GRID)
    all_rows, north_rows, block_rows, annual_rows = [], [], {}, {}
    latitude_rows = {i: [] for i in range(5)}
    sector_rows = {name: [] for name in ("west", "central", "east")}
    season_rows = {name: [] for name in ("DJF", "MAM", "JJA", "SON")}
    risk_rows = []
    for year in YEARS:
        truth, s12, analog = source(year, tp)
        block_rows[str(year)] = combine([moments(truth, s12, analog)])
        all_rows.append(moments(truth, s12, analog))
        north_rows.append(moments(truth[:, NORTH], s12[:, NORTH], analog[:, NORTH]))
        for k in (0, 1):
            sl = slice(12*k, 12*(k+1))
            annual_rows[str(year+k)] = {
                "global": combine([moments(truth[sl], s12[sl], analog[sl])]),
                "north": combine([moments(truth[sl, NORTH], s12[sl, NORTH],
                                          analog[sl, NORTH])]),
            }
        for i in range(5):
            cells = np.flatnonzero((LAT >= -60+15*i) &
                                   ((LAT < -45+15*i) if i < 4 else (LAT <= 15)))
            latitude_rows[i].append(moments(truth[:, cells], s12[:, cells], analog[:, cells]))
        for name, selected in round26._strata_code().items():
            cells = NORTH[selected]
            sector_rows[name].append(moments(truth[:, cells], s12[:, cells], analog[:, cells]))
        seasons = ((np.arange(24) % 12+1) % 12)//3
        for i, name in enumerate(("DJF", "MAM", "JJA", "SON")):
            selected = seasons == i
            season_rows[name].append(moments(truth[selected], s12[selected], analog[selected]))
        if year in EVAL:
            risk_rows.extend(_risk_deciles(year, truth, s12, analog))
        print("ORACLE", year, block_rows[str(year)]["oracle_gain_percent"], flush=True)
    global_stats = combine(all_rows)
    north_stats = combine(north_rows)
    relevant = global_stats["oracle_gain_percent"] >= .3 and \
               north_stats["oracle_gain_percent"] >= 1.
    output = {
        "global": global_stats, "north": north_stats,
        "by_block": block_rows, "by_year": annual_rows,
        "by_latitude_15deg": {f"{-60+15*i}:{-45+15*i}": combine(rows)
                               for i, rows in latitude_rows.items()},
        "by_north_sector": {name: combine(rows) for name, rows in sector_rows.items()},
        "by_season": {name: combine(rows) for name, rows in season_rows.items()},
        "risk_deciles_by_block": risk_rows,
        "oracle_relevant_predefined": bool(relevant),
        "early_stop_if_not_relevant": True,
        "no_test_targets": True,
    }
    save_json(OUT / "oracle.json", output)
    _plot_oracle(output)
    print("ORACLE GLOBAL", global_stats["oracle_gain_percent"],
          "NORTH", north_stats["oracle_gain_percent"],
          "RELEVANT", relevant, flush=True)


def _plot_oracle(output: dict) -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "tmp" / "matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    blocks = output["by_block"]
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.3), constrained_layout=True)
    ax[0].plot(YEARS, [blocks[str(y)]["rmse_s12"] for y in YEARS], marker="o", label="S12")
    ax[0].plot(YEARS, [blocks[str(y)]["rmse_analog"] for y in YEARS], marker="o", label="Analog")
    ax[0].plot(YEARS, [blocks[str(y)]["rmse_oracle"] for y in YEARS], marker="o", label="Oracle")
    ax[0].set(xlabel="Início do bloco", ylabel="RMSE global (mm/dia)",
              title="Limite empírico da escolha perfeita")
    ax[0].legend()
    ax[1].bar([f"{y}–{y+1}" for y in YEARS],
              [blocks[str(y)]["oracle_gain_percent"] for y in YEARS], color="#28628c")
    ax[1].set(xlabel="Bloco", ylabel="Ganho oracle sobre S12 (%)",
              title="Ganho por bloco")
    ax[1].tick_params(axis="x", labelrotation=30)
    fig.savefig(OUT / "oracle_blocos.png", dpi=170)
    plt.close(fig)
    risk = output["risk_deciles_by_block"]
    if risk:
        fig, ax = plt.subplots(1, 2, figsize=(12, 4.3), constrained_layout=True)
        for year in EVAL:
            rows = [r for r in risk if r["block"] == year]
            ax[0].plot(range(1, 11), [r["analog_win_fraction"] for r in rows],
                       marker=".", label=str(year))
            ax[1].plot(range(1, 11), [r["analog_gain_percent"] for r in rows],
                       marker=".", label=str(year))
        ax[0].set(xlabel="Decil de risco Q90 previsto", ylabel="Fração de vitórias Analog",
                  title="Risco extremo versus vencedor")
        ax[1].set(xlabel="Decil de risco Q90 previsto", ylabel="Ganho Analog sobre S12 (%)",
                  title="Vantagem relativa por risco")
        for item in ax:
            item.set_xticks(range(1, 11))
            item.axhline(0, color="gray", lw=.7)
            item.legend(title="Bloco")
        fig.savefig(OUT / "risco_q90_vs_vencedor.png", dpi=170)
        plt.close(fig)


FEATURES = {
    "climatology": 4, "s12": 5, "s12_anomaly": 6,
    "member_std": 95, "consensus_ratio": 104,
    "latitude": 0, "longitude": 1,
    **{f"continental_pc_{j+1}": 57+j for j in range(4)},
    **{f"tropical_pc_{j+1}": 73+j for j in range(4)},
    **{name: 7+j for j, name in enumerate(round26.VARIABLES)},
    "analog_minus_s12": 106, "abs_analog_minus_s12": 107,
}
MODEL_NAMES = ("logistic_base", "logistic_full", "ridge_full", "hgb_full")
BASE_COLUMNS = np.array([0, 1, 2, 3, 4, 5, 106], dtype=np.intp)


def _analog_values(prior: tuple[int, ...], cutoff: int) -> tuple[np.ndarray, np.ndarray]:
    lookup = round26._month_lookup(prior)
    origins = np.concatenate([target_origins(y) for y in prior])
    analogs = {y: np.load(round25.ART / f"{y}_h4_prediction.npy", mmap_mode="r")
               .reshape(24, GRID) for y in (*prior, cutoff)}
    train = np.empty(len(origins)*round26.SAMPLE, np.float32)
    for k, origin in enumerate(origins):
        year, slot = lookup[int(origin)]
        cells = round26._sample_cells(int(origin))
        train[k*round26.SAMPLE:(k+1)*round26.SAMPLE] = analogs[year][slot, cells]
    valid = np.asarray(analogs[cutoff][:, NORTH], np.float32).ravel()
    return train, valid


def _add_analog_features(x: np.ndarray, analog: np.ndarray) -> np.ndarray:
    combined = np.empty((len(x), 108), np.float32)
    combined[:, :105] = x
    combined[:, 105] = analog
    combined[:, 106] = analog-x[:, 5]
    combined[:, 107] = np.abs(combined[:, 106])
    return combined


def _build_meta(cutoff: int, tp: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    prior = tuple(y for y in YEARS if y < cutoff)
    sources = {y: round26._source(y) for y in (*prior, cutoff)}
    f = round26.Features(cutoff)
    global_train, global_valid = round20.context(f)
    xtr, rtr, xva, rva = round26._build_block(
        cutoff, f, global_train, global_valid, sources, tp)
    atr, ava = _analog_values(prior, cutoff)
    train = _add_analog_features(xtr, atr)
    valid = _add_analog_features(xva, ava)
    e_analog_train = (rtr+xtr[:, 5]-atr).astype(np.float64)
    e_analog_valid = (rva+xva[:, 5]-ava).astype(np.float64)
    ytrain = (e_analog_train**2 < rtr.astype(np.float64)**2)
    yvalid = (e_analog_valid**2 < rva.astype(np.float64)**2)
    dvalid = rva.astype(np.float64)**2-e_analog_valid**2
    return train, ytrain, valid, yvalid, dvalid


def _bin_advantage(train: np.ndarray, valid: np.ndarray, d: np.ndarray,
                   y: np.ndarray, residual_s12: np.ndarray,
                   residual_analog: np.ndarray) -> list[dict]:
    rows = []
    for name, col in FEATURES.items():
        edges = np.quantile(train[:, col], [.2, .4, .6, .8])
        bins = np.searchsorted(edges, valid[:, col], side="right")
        for group in range(5):
            selected = bins == group
            if not selected.any():
                continue
            s12 = residual_s12[selected].astype(np.float64)
            analog = residual_analog[selected].astype(np.float64)
            rows.append({
                "feature": name, "bin": group,
                "train_edges": [float(edge) for edge in edges],
                "count": int(selected.sum()),
                "mean_D": float(d[selected].mean()),
                "median_D": float(np.median(d[selected])),
                "analog_win_fraction": float(y[selected].mean()),
                "rmse_s12": float(np.sqrt(np.mean(s12*s12))),
                "rmse_analog": float(np.sqrt(np.mean(analog*analog))),
            })
    months = np.repeat((np.arange(24) % 12)+1, NORTH_SIZE)
    seasons = (months % 12)//3
    for name, codes, number in (("month", months-1, 12), ("season", seasons, 4)):
        for group in range(number):
            selected = codes == group
            rows.append({
                "feature": name, "bin": group, "count": int(selected.sum()),
                "mean_D": float(d[selected].mean()),
                "median_D": float(np.median(d[selected])),
                "analog_win_fraction": float(y[selected].mean()),
                "rmse_s12": float(np.sqrt(np.mean(residual_s12[selected].astype(np.float64)**2))),
                "rmse_analog": float(np.sqrt(np.mean(residual_analog[selected].astype(np.float64)**2))),
            })
    return rows


def _binary(y: np.ndarray, probability: np.ndarray, prior: float) -> dict:
    actual = np.asarray(y, bool).ravel()
    p = np.clip(np.asarray(probability, np.float64).ravel(), .01, .99)
    n = len(p)
    ordered = np.argsort(p, kind="stable")
    low, high = ordered[:n//10], ordered[-n//10:]
    baseline_brier = float(np.mean((actual-prior)**2))
    baseline_logloss = float(log_loss(actual, np.full(n, prior), labels=[False, True]))
    brier = float(np.mean((actual-p)**2))
    loss = float(log_loss(actual, p, labels=[False, True]))
    calib = []
    bins = np.minimum((p*10).astype(int), 9)
    for i in range(10):
        selected = bins == i
        if selected.any():
            calib.append({"bin": i, "count": int(selected.sum()),
                          "predicted_probability": float(p[selected].mean()),
                          "observed_fraction": float(actual[selected].mean())})
    ece = sum(row["count"]*abs(row["observed_fraction"]-
                               row["predicted_probability"])
              for row in calib)/n
    return {
        "count": n, "prevalence": float(actual.mean()),
        "prior_from_training": float(prior),
        "auc": float(roc_auc_score(actual, p)) if np.unique(actual).size == 2 else None,
        "brier": brier, "baseline_brier": baseline_brier,
        "brier_gain": baseline_brier-brier,
        "log_loss": loss, "baseline_log_loss": baseline_logloss,
        "log_loss_gain": baseline_logloss-loss,
        "top_decile_win_fraction": float(actual[high].mean()),
        "bottom_decile_win_fraction": float(actual[low].mean()),
        "top_decile_lift": float(actual[high].mean()/actual.mean()),
        "extreme_decile_separation": float(actual[high].mean()-actual[low].mean()),
        "calibration_ece": float(ece), "calibration_bins": calib,
    }


def _fit_models(train: np.ndarray, ytrain: np.ndarray,
                valid: np.ndarray) -> np.ndarray:
    mean = train.mean(axis=0, dtype=np.float64)
    sd = np.where(train.std(axis=0, dtype=np.float64) > 1e-6,
                  train.std(axis=0, dtype=np.float64), 1.)
    ztr = ((train-mean)/sd).astype(np.float32)
    zva = ((valid-mean)/sd).astype(np.float32)
    estimates = []
    for columns in (BASE_COLUMNS, np.arange(108)):
        model = LogisticRegression(C=.3, max_iter=200, solver="lbfgs", tol=1e-4)
        model.fit(ztr[:, columns], ytrain)
        estimates.append(model.predict_proba(zva[:, columns])[:, 1].astype(np.float32))
    centered = ytrain.astype(np.float64)-ytrain.mean()
    gram = (ztr.T@ztr).astype(np.float64)/len(ztr)
    xy = (ztr.T@centered).astype(np.float64)/len(ztr)
    coef = np.linalg.solve(gram+.3*np.eye(108), xy)
    estimates.append(np.clip(ytrain.mean()+zva@coef, .01, .99).astype(np.float32))
    model = HistGradientBoostingClassifier(
        max_leaf_nodes=7, max_iter=100, learning_rate=.03,
        min_samples_leaf=500, l2_regularization=100., max_bins=128,
        early_stopping=False, random_state=20260927)
    model.fit(train, ytrain)
    estimates.append(model.predict_proba(valid)[:, 1].astype(np.float32))
    return np.stack(estimates)


def evaluate() -> None:
    locked()
    oracle_result = json.loads((OUT / "oracle.json").read_text(encoding="utf-8"))
    if not oracle_result["oracle_relevant_predefined"]:
        print("PARADA: oracle insuficiente", flush=True)
        return
    tp = np.load(CACHE / "tp.npy", mmap_mode="r").reshape(-1, GRID)
    for cutoff in EVAL:
        metric_path = OUT / f"{cutoff}_winner.json"
        artifact_path = ART / f"{cutoff}_winner_oof.npz"
        if metric_path.exists() and artifact_path.exists() and \
           artifact_path.with_suffix(".json").exists():
            print("BLOCO EXISTENTE", cutoff, flush=True)
            continue
        train, ytrain, valid, yvalid, dvalid = _build_meta(cutoff, tp)
        prior = float(ytrain.mean())
        estimates = _fit_models(train, ytrain, valid)
        res_s12 = (tp[target_origins(cutoff)+1][:, NORTH].ravel()-valid[:, 5])
        res_analog = (tp[target_origins(cutoff)+1][:, NORTH].ravel()-valid[:, 105])
        metrics = {}
        for j, name in enumerate(MODEL_NAMES):
            p = estimates[j]
            metrics[name] = {
                "block": _binary(yvalid, p, prior),
                "year1": _binary(yvalid[:12*NORTH_SIZE], p[:12*NORTH_SIZE], prior),
                "year2": _binary(yvalid[12*NORTH_SIZE:], p[12*NORTH_SIZE:], prior),
            }
        output = {
            "cutoff": cutoff, "training_blocks": [y for y in YEARS if y < cutoff],
            "last_training_target": f"{cutoff-1}-12", "train_count": len(train),
            "validation_count": len(valid), "prior_analog_win": prior,
            "winner_metrics": metrics,
            "advantage_distribution": {
                "mean_D": float(dvalid.mean()), "median_D": float(np.median(dvalid)),
                "p01_D": float(np.quantile(dvalid, .01)),
                "p10_D": float(np.quantile(dvalid, .1)),
                "p90_D": float(np.quantile(dvalid, .9)),
                "p99_D": float(np.quantile(dvalid, .99)),
            },
            "advantage_by_feature": _bin_advantage(
                train, valid, dvalid, yvalid, res_s12, res_analog),
            "no_test_targets": True,
        }
        save_json(metric_path, output)
        np.savez_compressed(artifact_path, probability=estimates.reshape(4, 24, NORTH_SIZE),
                            winner=yvalid.reshape(24, NORTH_SIZE),
                            advantage=dvalid.astype(np.float32).reshape(24, NORTH_SIZE))
        save_json(artifact_path.with_suffix(".json"), {
            "sha256": sha(artifact_path), "cutoff": cutoff,
            "model_names": MODEL_NAMES,
            "last_training_target": f"{cutoff-1}-12", "no_test_targets": True,
        })
        print("WINNER", cutoff,
              {name: round(metrics[name]["block"]["auc"], 4)
               for name in MODEL_NAMES}, flush=True)


def regime_analysis() -> None:
    """Reusa exatamente KMeans e PCs causais da análise descritiva da rodada 25."""
    locked()
    tp = np.load(CACHE / "tp.npy", mmap_mode="r").reshape(-1, GRID)
    rows = []
    for cutoff in EVAL:
        f = round26.Features(cutoff)
        train, valid = round20.context(f)
        cluster = round25.KMeans(n_clusters=4, random_state=20260917,
                                 n_init=20).fit(train[:, :8])
        order = np.argsort(cluster.cluster_centers_[:, 0])
        rank = np.empty(4, np.intp)
        rank[order] = np.arange(4)
        assignments = rank[cluster.predict(valid[:, :8])]
        truth, s12, analog = source(cutoff, tp)
        for group in range(4):
            selected = assignments == group
            if not selected.any():
                continue
            t, p, a = truth[selected][:, NORTH], s12[selected][:, NORTH], \
                      analog[selected][:, NORTH]
            stats = combine([moments(t, p, a)])
            rows.append({"block": cutoff, "regime_rank_pc1": group,
                         "months": int(selected.sum()),
                         "mean_D": float((stats["sse_s12"]-stats["sse_analog"])
                                         /stats["count"]), **stats})
        print("REGIME", cutoff, flush=True)
    save_json(OUT / "regime.json", {
        "method": "Round25 KMeans-4 on first 8 continental PCs; training before cutoff",
        "labels_comparable_across_blocks": False,
        "rows": rows, "no_test_targets": True,
    })


def decision() -> None:
    locked()
    oracle_result = json.loads((OUT / "oracle.json").read_text(encoding="utf-8"))
    if not oracle_result["oracle_relevant_predefined"]:
        result = {"classification": "C", "reason": "Oracle abaixo do limiar pré-fixado.",
                  "gate_tested": False}
        save_json(OUT / "decision.json", result)
        _write_decision(result, oracle_result)
        return
    reports = {y: json.loads((OUT / f"{y}_winner.json").read_text(encoding="utf-8"))
               for y in EVAL}
    eligible = []
    for name in MODEL_NAMES:
        passed = sum(
            report["winner_metrics"][name]["block"]["auc"] > .53 and
            report["winner_metrics"][name]["block"]["brier_gain"] > 0 and
            report["winner_metrics"][name]["block"]["extreme_decile_separation"] > 0
            for report in reports.values())
        if passed >= 4:
            eligible.append(name)
    if eligible:
        result = _gating(reports, eligible)
    else:
        result = {"classification": "B", "reason": "Oracle relevante; nenhum modelo passou 4/5 cortes para AUC, Brier e separação de decis.",
                  "gate_tested": False, "eligible_models": []}
    save_json(OUT / "decision.json", result)
    _write_decision(result, oracle_result, reports)
    print("DECISAO", result["classification"], result["reason"], flush=True)


def _gating(reports: dict, eligible: list[str]) -> dict:
    tp = np.load(CACHE / "tp.npy", mmap_mode="r").reshape(-1, GRID)
    names = [(name, cap) for name in eligible for cap in (.1, .2, .3)]
    sums = {f"{name}_{cap:.1f}": {"global": [], "north": [], "delta2": [],
                                  "block": {}, "year": {}, "month": [],
                                  "sectors": {k: [] for k in ("west", "central", "east")}}
            for name, cap in names}
    base_global, base_north, fixed_global, fixed_north, fixed_north_only = [], [], [], [], []
    oracle_global, oracle_north = [], []
    block_baselines, annual_baselines = {}, {}
    sector_masks = round26._strata_code()
    for cutoff in EVAL:
        truth, s12, analog = source(cutoff, tp)
        t = np.asarray(truth, np.float64)
        p = np.asarray(s12, np.float64)
        a = np.asarray(analog, np.float64)
        r = t-p
        rn = r[:, NORTH]
        delta = a[:, NORTH]-p[:, NORTH]
        month_base_global = np.sum(r*r, axis=1)
        month_base_north = np.sum(rn*rn, axis=1)
        fixed = r-.1*(a-p)
        month_fixed_global = np.sum(fixed*fixed, axis=1)
        fixed_n = rn-.1*delta
        month_fixed_north = np.sum(fixed_n*fixed_n, axis=1)
        ora = np.minimum(r*r, (t-a)**2)
        base_global.extend(month_base_global.tolist())
        base_north.extend(month_base_north.tolist())
        fixed_global.extend(month_fixed_global.tolist())
        fixed_north.extend(month_fixed_north.tolist())
        fixed_north_only.extend((month_base_global-month_base_north+
                                 month_fixed_north).tolist())
        oracle_global.extend(np.sum(ora, axis=1).tolist())
        oracle_north.extend(np.sum(ora[:, NORTH], axis=1).tolist())
        block_baselines[str(cutoff)] = {
            "s12": float(month_base_global.sum()),
            "fixed10_global": float(month_fixed_global.sum()),
        }
        for k in (0, 1):
            sl = slice(12*k, 12*(k+1))
            annual_baselines[str(cutoff+k)] = float(month_base_global[sl].sum())
        with np.load(ART / f"{cutoff}_winner_oof.npz") as saved:
            probabilities = np.asarray(saved["probability"], np.float64)
        for name, cap in names:
            key = f"{name}_{cap:.1f}"
            j = MODEL_NAMES.index(name)
            g = cap*probabilities[j]
            altered = rn-g*delta
            month_north = np.sum(altered*altered, axis=1)
            month_global = month_base_global-month_base_north+month_north
            row = sums[key]
            row["global"].extend(month_global.tolist())
            row["north"].extend(month_north.tolist())
            row["delta2"].extend(np.sum((g*delta)**2, axis=1).tolist())
            row["block"][str(cutoff)] = float(month_global.sum())
            for k in (0, 1):
                row["year"][str(cutoff+k)] = float(month_global[12*k:12*(k+1)].sum())
            for sector, selected in sector_masks.items():
                gain_sse = float(np.sum((rn[:, selected])**2)-
                                 np.sum((altered[:, selected])**2))
                baseline_sse = float(np.sum((rn[:, selected])**2))
                row["sectors"][sector].append((gain_sse, baseline_sse))
    nmonth = len(base_global)
    n_global, n_north = nmonth*GRID, nmonth*NORTH_SIZE
    sum_base = float(sum(base_global))
    fixed_sum = float(sum(fixed_global))
    baselines = {
        "s12": {"global_rmse": float(np.sqrt(sum_base/n_global)),
                "north_rmse": float(np.sqrt(sum(base_north)/n_north))},
        "fixed10_global": {"global_rmse": float(np.sqrt(fixed_sum/n_global)),
                           "north_rmse": float(np.sqrt(sum(fixed_north)/n_north))},
        "fixed10_north_only": {
            "global_rmse": float(np.sqrt(sum(fixed_north_only)/n_global)),
            "north_rmse": float(np.sqrt(sum(fixed_north)/n_north))},
        "oracle": {"global_rmse": float(np.sqrt(sum(oracle_global)/n_global)),
                   "north_rmse": float(np.sqrt(sum(oracle_north)/n_north))},
    }
    gates = {}
    for key, row in sums.items():
        total = float(sum(row["global"]))
        rmse = float(np.sqrt(total/n_global))
        sectors = {}
        for sector, pairs in row["sectors"].items():
            change, baseline = np.sum(pairs, axis=0)
            sectors[sector] = float(100*(1-np.sqrt((baseline-change)/baseline)))
        gates[key] = {
            "model": key.rsplit("_", 1)[0], "gmax": float(key.rsplit("_", 1)[1]),
            "global_rmse": rmse,
            "north_rmse": float(np.sqrt(sum(row["north"])/n_north)),
            "gain_vs_s12_percent": float(100*(1-rmse/baselines["s12"]["global_rmse"])),
            "gain_vs_fixed10_global_percent":
                float(100*(1-rmse/baselines["fixed10_global"]["global_rmse"])),
            "positive_blocks": sum(row["block"][str(y)] <
                                   block_baselines[str(y)]["s12"] for y in EVAL),
            "positive_years": sum(row["year"][str(y)] < annual_baselines[str(y)]
                                  for y in range(2011, 2021)),
            "positive_months": sum(x < b for x, b in zip(row["global"], base_global)),
            "rms_change_global": float(np.sqrt(sum(row["delta2"])/n_global)),
            "rms_change_north": float(np.sqrt(sum(row["delta2"])/n_north)),
            "gain_by_north_sector_percent": sectors,
            "by_block": {str(y): {
                "global_rmse": float(np.sqrt(row["block"][str(y)]/(24*GRID))),
                "gain_vs_s12_percent": float(100*(1-np.sqrt(
                    row["block"][str(y)]/block_baselines[str(y)]["s12"]))),
            } for y in EVAL},
            "by_year": {str(y): {
                "global_rmse": float(np.sqrt(row["year"][str(y)]/(12*GRID))),
                "gain_vs_s12_percent": float(100*(1-np.sqrt(
                    row["year"][str(y)]/annual_baselines[str(y)]))),
            } for y in range(2011, 2021)},
        }
    stable = [key for key, row in gates.items()
              if row["gain_vs_s12_percent"] >= .3
              and row["global_rmse"] < baselines["fixed10_global"]["global_rmse"]
              and row["positive_blocks"] >= 4 and row["positive_years"] >= 7
              and row["positive_months"] >= 67]
    if stable:
        classification = "A"
        reason = "Oracle relevante; soft gating supera S12 e mistura fixa com estabilidade predefinida."
    elif any(row["gain_vs_s12_percent"] > 0 for row in gates.values()):
        classification = "D"
        reason = "Há ganho em algumas combinações, mas nenhuma satisfaz amplitude e estabilidade de A."
    else:
        classification = "B"
        reason = "Oracle relevante, porém todos os soft gates OOF pioram a S12."
    result = {"classification": classification, "reason": reason,
              "gate_tested": True, "eligible_models": eligible,
              "baselines": baselines, "gates": gates,
              "stable_gates": stable, "evaluation_blocks": EVAL,
              "no_candidate": True, "no_test_targets": True}
    _plot_gating(result)
    return result


def _plot_gating(result: dict) -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "tmp" / "matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = sorted(result["gates"].items(), key=lambda kv: -kv[1]["gain_vs_s12_percent"])
    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    ax.barh([key for key, _ in rows][::-1],
            [row["gain_vs_s12_percent"] for _, row in rows][::-1], color="#28628c")
    ax.axvline(0, color="black", lw=.8)
    ax.axvline(.3, color="#b4514a", ls="--", lw=.8)
    ax.set(xlabel="Ganho global sobre S12 (%)", title="Soft gating OOF: 2011–2020")
    fig.savefig(OUT / "gating_ganhos.png", dpi=170)
    plt.close(fig)


def _write_decision(result: dict, oracle_result: dict,
                    reports: dict | None = None) -> None:
    def num(value: float, digits: int = 3) -> str:
        return f"{value:.{digits}f}"

    o = oracle_result
    lines = ["# Rodada 27 — seleção S12 versus análogos", "",
             f"**Decisão predefinida: {result['classification']}.** {result['reason']}", "",
             "## Escopo e limite empírico", "",
             "S12 e análogo puro H4 são previsões OOF congeladas. O oracle "
             "acessa o observado para escolher o menor erro em cada célula; "
             "esse resultado é somente um limite diagnóstico de escolha "
             "perfeita entre os dois mapas. O ganho relevante foi definido "
             "antes dos cálculos como ≥0,3% global e ≥1,0% norte.", "",
             "| Região | RMSE S12 | RMSE Analog | RMSE oracle | Vitórias Analog | Ganho oracle |",
             "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for name in ("global", "north"):
        row = o[name]
        lines.append(f"| {name} | {num(row['rmse_s12'])} | {num(row['rmse_analog'])} | "
                     f"{num(row['rmse_oracle'])} | {100*row['analog_win_fraction']:.2f}% | "
                     f"{row['oracle_gain_percent']:.2f}% |")
    lines += ["", "| Bloco | RMSE S12 | RMSE Analog | RMSE oracle | Vitórias Analog | Ganho oracle |",
              "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for y in YEARS:
        row = o["by_block"][str(y)]
        lines.append(f"| {y}–{y+1} | {num(row['rmse_s12'])} | {num(row['rmse_analog'])} | "
                     f"{num(row['rmse_oracle'])} | {100*row['analog_win_fraction']:.2f}% | "
                     f"{row['oracle_gain_percent']:.2f}% |")
    lines += ["", "### Ano, latitude, setor e estação", "",
              "| Ano | Ganho oracle global | Ganho oracle norte | Vitórias Analog global |",
              "| ---: | ---: | ---: | ---: |"]
    for year in range(2009, 2021):
        row = o["by_year"][str(year)]
        lines.append(f"| {year} | {row['global']['oracle_gain_percent']:.2f}% | "
                     f"{row['north']['oracle_gain_percent']:.2f}% | "
                     f"{100*row['global']['analog_win_fraction']:.2f}% |")
    lines += ["", "| Área | Ganho oracle | Vitórias Analog | RMSE S12 | RMSE oracle |",
              "| --- | ---: | ---: | ---: | ---: |"]
    for family, rows in (("latitude", o["by_latitude_15deg"]),
                         ("setor norte", o["by_north_sector"]),
                         ("estação", o["by_season"])):
        for name, row in rows.items():
            lines.append(f"| {family}: {name} | {row['oracle_gain_percent']:.2f}% | "
                         f"{100*row['analog_win_fraction']:.2f}% | "
                         f"{row['rmse_s12']:.3f} | {row['rmse_oracle']:.3f} |")
    lines += ["", "![Oracle por bloco](oracle_blocos.png)", "",
              "O detalhamento por ano, faixa de latitude, setor norte e "
              "estação está em [oracle.json](oracle.json).", "",
              "## Vantagem por risco Q90 previsto", "",
              "D = L_S12 − L_Analog; D positivo favorece o análogo. Os decis "
              "são ordenados pelo risco OOF da rodada 26 dentro de cada bloco. "
              "A tabela agrega os cinco blocos 2011–2020 com o mesmo número "
              "de pontos por decil.", "",
              "| Decil | RMSE S12 | RMSE Analog | Vitórias Analog | RMSE oracle | Ganho oracle | D médio |",
              "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for decile in range(1, 11):
        rows = [r for r in o["risk_deciles_by_block"] if r["risk_decile"] == decile]
        stats = combine(rows)
        mean_d = (stats["sse_s12"]-stats["sse_analog"])/stats["count"]
        lines.append(f"| {decile} | {num(stats['rmse_s12'])} | "
                     f"{num(stats['rmse_analog'])} | "
                     f"{100*stats['analog_win_fraction']:.2f}% | "
                     f"{num(stats['rmse_oracle'])} | "
                     f"{stats['oracle_gain_percent']:.2f}% | {mean_d:+.3f} |")
    lines += ["", "![Risco Q90 versus vencedor](risco_q90_vs_vencedor.png)", "",
              "A comparação por bloco é decisiva: baixo→alto risco não traz "
              "aumento consistente na fração de vitórias do análogo. Em "
              "2011, 2013 e 2019 a fração até cai; em 2015 cresce; em 2017 "
              "fica quase estável. Prever |erro S12| alto não equivale a "
              "prever qual modelo terá menor erro.", ""]
    if reports is not None:
        lines += ["## Análise de D por atributos disponíveis", "",
                  "Os quintis de cada atributo foram definidos com o treino "
                  "anterior ao bloco. Todas as linhas por corte incluem "
                  "climatologia, S12, anomalia, dispersão, consenso, "
                  "latitude/longitude, mês/estação, PCs e nove variáveis "
                  "locais nos arquivos `YYYY_winner.json`. A tabela mostra "
                  "extremos de atributos centrais, agregados nos cinco blocos.", "",
                  "| Atributo | Quintil | D médio | Vitórias Analog | RMSE S12 | RMSE Analog |",
                  "| --- | ---: | ---: | ---: | ---: | ---: |"]
        for feature in ("climatology", "s12", "s12_anomaly", "member_std",
                        "consensus_ratio", "analog_minus_s12"):
            for bin_id in (0, 4):
                rows = [row for report in reports.values()
                        for row in report["advantage_by_feature"]
                        if row["feature"] == feature and row["bin"] == bin_id]
                n = sum(row["count"] for row in rows)
                if not n:
                    continue
                d = sum(row["count"]*row["mean_D"] for row in rows)/n
                win = sum(row["count"]*row["analog_win_fraction"] for row in rows)/n
                s12_sse = sum(row["count"]*row["rmse_s12"]**2 for row in rows)
                a_sse = sum(row["count"]*row["rmse_analog"]**2 for row in rows)
                lines.append(f"| {feature} | {bin_id} | {d:+.3f} | "
                             f"{100*win:.2f}% | {np.sqrt(s12_sse/n):.3f} | "
                             f"{np.sqrt(a_sse/n):.3f} |")
        lines += ["", "O regime KMeans da rodada 25 foi registrado apenas "
                  "como agregado descritivo. Recalculamos suas atribuições "
                  "com a mesma regra causal, sem usá-las no meta-modelo. "
                  "As classes ordenadas por PC1 mudam entre cortes e não "
                  "representam regimes físicos idênticos. Os resultados "
                  "por bloco estão em [regime.json](regime.json).", ""]
        regime_path = OUT / "regime.json"
        if regime_path.exists():
            regime = json.loads(regime_path.read_text(encoding="utf-8"))["rows"]
            positive = [row for row in regime if row["analog_gain_percent"] > 0]
            lines += [f"Só {len(positive)}/{len(regime)} pares bloco×regime "
                      "tiveram ganho do análogo puro; os positivos ocorreram "
                      "em poucos meses e em classes diferentes.", "",
                      "| Bloco | Regime (ordem PC1) | Meses | Vitórias Analog | Ganho Analog vs S12 | D médio |",
                      "| --- | ---: | ---: | ---: | ---: | ---: |"]
            for row in regime:
                lines.append(f"| {row['block']}–{row['block']+1} | "
                             f"{row['regime_rank_pc1']} | {row['months']} | "
                             f"{100*row['analog_win_fraction']:.1f}% | "
                             f"{row['analog_gain_percent']:+.2f}% | "
                             f"{row['mean_D']:+.3f} |")
        lines += ["",
                  "## Previsão OOF do vencedor", "",
                  "O alvo é 1 se o análogo tem perda quadrática menor. O "
                  "primeiro bloco alimenta o treino, e cinco blocos "
                  "2011–2020 são validados integralmente. `logistic_base` "
                  "usa localização, mês, climatologia, S12 e diferença "
                  "Analog−S12; os outros modelos usam todos os 108 atributos.", "",
                  "| Modelo | Bloco | AUC | Ganho Brier | Ganho log loss | ECE | Lift decil alto | Vitória decil baixo | Separação decis |",
                  "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for name in MODEL_NAMES:
            for y in EVAL:
                row = reports[y]["winner_metrics"][name]["block"]
                lines.append(f"| {name} | {y}–{y+1} | {row['auc']:.3f} | "
                             f"{row['brier_gain']:+.4f} | "
                             f"{row['log_loss_gain']:+.4f} | "
                             f"{row['calibration_ece']:.3f} | "
                             f"{row['top_decile_lift']:.2f}× | "
                             f"{100*row['bottom_decile_win_fraction']:.1f}% | "
                             f"{100*row['extreme_decile_separation']:+.1f} p.p. |")
        lines += ["", "Calibração em dez faixas de probabilidade, métricas "
                  "por ano e lift superior/inferior estão nos JSONs por "
                  "bloco. Os pixels de um mesmo mês não são réplicas "
                  "independentes.", ""]
    if result.get("gate_tested"):
        b = result["baselines"]
        lines += ["## Soft gating OOF", "",
                  "Somente modelos que passaram AUC, Brier e separação "
                  "de decis em ≥4/5 blocos foram testados. Peso norte "
                  "`g = gmax × P(Analog melhor|X)`; fora do norte, S12 "
                  "permanece. Janela comparável: 2011–2020.", "",
                  "| Método | RMSE global | RMSE norte | Ganho global vs S12 | Blocos | Anos | Meses | RMS mudança norte |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for name in ("s12", "fixed10_global", "fixed10_north_only", "oracle"):
            row = b[name]
            gain = 100*(1-row["global_rmse"]/b["s12"]["global_rmse"])
            lines.append(f"| {name} | {row['global_rmse']:.6f} | "
                         f"{row['north_rmse']:.6f} | {gain:+.3f}% | — | — | — | — |")
        for name, row in sorted(result["gates"].items(),
                                key=lambda kv: -kv[1]["gain_vs_s12_percent"]):
            lines.append(f"| {name} | {row['global_rmse']:.6f} | "
                         f"{row['north_rmse']:.6f} | "
                         f"{row['gain_vs_s12_percent']:+.3f}% | "
                         f"{row['positive_blocks']}/5 | {row['positive_years']}/10 | "
                         f"{row['positive_months']}/120 | "
                         f"{row['rms_change_north']:.3f} |")
        lines += ["", "![Ganho de soft gating](gating_ganhos.png)", "",
                  "### Estabilidade da maior linha observada", "",
                  "A linha abaixo foi identificada após a avaliação entre "
                  "nove combinações predefinidas; é descrição, não regra "
                  "selecionada para uso.", "",
                  "| Bloco | Ganho global |",
                  "| --- | ---: |"]
        best_name, best_row = max(result["gates"].items(),
                                  key=lambda kv: kv[1]["gain_vs_s12_percent"])
        for year in EVAL:
            lines.append(f"| {year}–{year+1} | "
                         f"{best_row['by_block'][str(year)]['gain_vs_s12_percent']:+.3f}% |")
        lines += ["", f"`{best_name}` melhorou "
                  f"{best_row['positive_blocks']}/5 blocos, "
                  f"{best_row['positive_years']}/10 anos e "
                  f"{best_row['positive_months']}/120 meses; "
                  "ganho por setor norte:", "",
                  "| Setor | Ganho RMSE norte |",
                  "| --- | ---: |"]
        for sector, gain in best_row["gain_by_north_sector_percent"].items():
            lines.append(f"| {sector} | {gain:+.3f}% |")
        lines += ["",
                  "Métricas por bloco/ano e ganho por setor norte constam em "
                  "[decision.json](decision.json). O melhor valor de "
                  "uma tabela com múltiplas combinações não é teste "
                  "independente nem autoriza escolher pesos retroativamente.", ""]
    lines += ["## Conclusão", "",
              f"**Classe {result['classification']}.** {result['reason']}", "",
              "O oracle demonstra espaço entre os especialistas, mas usa "
              "o alvo observado. O risco Q90 prevê principalmente a "
              "magnitude do erro S12 e não seleciona, por si, o vencedor. "
              "Os períodos históricos já foram reutilizados em várias "
              "rodadas; há viés de seleção. Nenhuma S14, CSV, treino final "
              "ou submissão foi criada. A "
              "[auditoria independente](audit.json) refez as métricas dos "
              "arquivos congelados. "
              "[Protocolo](../../../experiments/ROUND27.md).", ""]
    (OUT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["oracle", "evaluate", "regime", "decision"])
    stage = parser.parse_args().stage
    if stage == "oracle":
        oracle()
    elif stage == "evaluate":
        evaluate()
    elif stage == "regime":
        regime_analysis()
    elif stage == "decision":
        decision()
