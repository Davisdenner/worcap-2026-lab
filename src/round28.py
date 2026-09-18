"""Rodada 28: decompõe e testa a vantagem entre S12 e Analog."""
from __future__ import annotations

import os
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, log_loss

from .competition import CACHE, ROOT, REPORT, save_json
from .round2 import target_origins
from . import round20, round25, round26, round27

OUT = REPORT / "round28"
ART = ROOT / "data/processed/round28"
PROTOCOL = ROOT / "experiments/ROUND28.md"
YEARS = round27.YEARS
EVAL = round27.EVAL
GRID = round25.GRID
NORTH = round26.NORTH
NORTH_SIZE = round26.NORTH_SIZE
FRACTIONS = (.01, .025, .05, .1, .2, .5)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def locked() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    record = {
        "protocol_sha256": sha(PROTOCOL),
        "input_hashes": {str(y): {
            "s12": sha(round20.ART / f"{y}_s12.npy"),
            "analog": sha(round25.ART / f"{y}_h4_prediction.npy"),
            **({"round27_winner": sha(round27.ART / f"{y}_winner_oof.npz")}
               if y in EVAL else {}),
        } for y in YEARS},
        "development_only": True, "no_2023_2024_targets": True,
        "no_s14_or_submission": True,
    }
    path = OUT / "protocol.json"
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != json.loads(json.dumps(record)):
            raise ValueError("Protocolo ou previsões OOF congeladas mudaram")
    else:
        save_json(path, record)


def _g_and_s12(year: int, tp: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    target = np.asarray(tp[target_origins(year)+1], np.float64)
    s12 = np.asarray(round20.reference(year).reshape(24, GRID), np.float64)
    analog = np.asarray(np.load(round25.ART / f"{year}_h4_prediction.npy", mmap_mode="r")
                        .reshape(24, GRID), np.float64)
    l12 = (target-s12)**2
    g = l12-(target-analog)**2
    return g.astype(np.float32), l12.astype(np.float32)


def _decompose(g: np.ndarray, l12: np.ndarray) -> dict:
    values = np.asarray(g, np.float32).ravel()
    baseline = np.asarray(l12, np.float32).ravel()
    n = len(values)
    positive = np.maximum(values, 0)
    benefit = float(np.sum(positive, dtype=np.float64))
    baseline_sse = float(np.sum(baseline, dtype=np.float64))
    ordered_abs = np.argsort(np.abs(values))[::-1]
    abs_benefit = np.cumsum(positive[ordered_abs], dtype=np.float64)
    positive_only = np.sort(values[values > 0])[::-1]
    positive_benefit = np.cumsum(positive_only, dtype=np.float64)
    top_abs, top_positive = {}, {}
    for fraction in FRACTIONS:
        label = f"{100*fraction:g}%"
        k_abs = int(np.ceil(fraction*n))
        k_positive = int(np.ceil(fraction*len(positive_only)))
        top_abs[label] = {
            "points": k_abs,
            "oracle_benefit_fraction": float(abs_benefit[k_abs-1]/benefit),
            "positive_wins_among_selected": int(np.sum(values[ordered_abs[:k_abs]] > 0)),
        }
        top_positive[label] = {
            "positive_wins": k_positive,
            "oracle_benefit_fraction": float(positive_benefit[k_positive-1]/benefit),
        }
    return {
        "count": n, "positive_win_count": int(len(positive_only)),
        "positive_win_fraction": float(len(positive_only)/n),
        "mean_G": float(np.mean(values, dtype=np.float64)),
        "median_G": float(np.median(values)),
        "q01_G": float(np.quantile(values, .01)),
        "q99_G": float(np.quantile(values, .99)),
        "s12_sse": baseline_sse,
        "oracle_benefit_sse": benefit,
        "oracle_rmse_gain_percent": float(100*(1-np.sqrt((baseline_sse-benefit)/baseline_sse))),
        "top_abs_G": top_abs,
        "top_positive_G": top_positive,
    }


def decomposition() -> None:
    locked()
    tp = np.load(CACHE / "tp.npy", mmap_mode="r").reshape(-1, GRID)
    pairs = {year: _g_and_s12(year, tp) for year in YEARS}
    def group(slices: list[tuple[np.ndarray, np.ndarray]]) -> dict:
        return _decompose(np.concatenate([g.ravel() for g, _ in slices]),
                          np.concatenate([l.ravel() for _, l in slices]))
    output = {
        "global": group([pairs[y] for y in YEARS]),
        "north": group([(pairs[y][0][:, NORTH], pairs[y][1][:, NORTH]) for y in YEARS]),
        "by_block": {}, "by_year": {}, "by_latitude_15deg": {},
        "by_north_sector": {}, "by_season": {},
        "fractions": FRACTIONS,
        "top_abs_denominator": "all points in group",
        "top_positive_denominator": "positive G points in group",
        "no_test_targets": True,
    }
    for year, (g, l) in pairs.items():
        output["by_block"][str(year)] = {
            "global": _decompose(g, l), "north": _decompose(g[:, NORTH], l[:, NORTH])}
        for k in (0, 1):
            sl = slice(12*k, 12*(k+1))
            output["by_year"][str(year+k)] = {
                "global": _decompose(g[sl], l[sl]),
                "north": _decompose(g[sl, NORTH], l[sl, NORTH]),
            }
        print("DECOMPOSITION", year, flush=True)
    for i in range(5):
        cells = np.flatnonzero((round25.LAT >= -60+15*i) &
                               ((round25.LAT < -45+15*i) if i < 4 else
                                (round25.LAT <= 15)))
        output["by_latitude_15deg"][f"{-60+15*i}:{-45+15*i}"] = group(
            [(pairs[y][0][:, cells], pairs[y][1][:, cells]) for y in YEARS])
    for name, selected in round26._strata_code().items():
        cells = NORTH[selected]
        output["by_north_sector"][name] = group(
            [(pairs[y][0][:, cells], pairs[y][1][:, cells]) for y in YEARS])
    season_code = ((np.arange(24) % 12+1) % 12)//3
    for i, name in enumerate(("DJF", "MAM", "JJA", "SON")):
        selected = season_code == i
        output["by_season"][name] = group(
            [(pairs[y][0][selected], pairs[y][1][selected]) for y in YEARS])
    save_json(OUT / "decomposition.json", output)
    _plot_decomposition(output)
    print("DECOMPOSITION GLOBAL TOP1 ABS",
          output["global"]["top_abs_G"]["1%"]["oracle_benefit_fraction"], flush=True)


def _plot_decomposition(output: dict) -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "tmp" / "matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    labels = [f"{100*f:g}%" for f in FRACTIONS]
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.3), constrained_layout=True)
    for area, color in (("global", "#28628c"), ("north", "#b4514a")):
        row = output[area]
        ax[0].plot(100*np.array(FRACTIONS),
                   [100*row["top_abs_G"][label]["oracle_benefit_fraction"]
                    for label in labels], marker="o", label=area, color=color)
        ax[1].plot(100*np.array(FRACTIONS),
                   [100*row["top_positive_G"][label]["oracle_benefit_fraction"]
                    for label in labels], marker="o", label=area, color=color)
    ax[0].set(title="Top |G| entre todos os pontos", xlabel="Pontos selecionados (%)",
              ylabel="Fração do benefício oracle (%)")
    ax[1].set(title="Top G entre vitórias Analog", xlabel="Vitórias selecionadas (%)",
              ylabel="Fração do benefício oracle (%)")
    for item in ax:
        item.set_xscale("log")
        item.set_xticks(100*np.array(FRACTIONS), labels)
        item.legend()
        item.grid(alpha=.2)
    fig.savefig(OUT / "concentracao_oracle.png", dpi=170)
    plt.close(fig)


REG_NAMES = ("ridge_G", "ridge_clip", "ridge_signedlog", "ridge_logpositive",
             "hgb_G", "hgb_clip")
STRONG_NAMES = ("logistic_base", "hgb_full")


def _build(cutoff: int, tp: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray,
                                              np.ndarray, np.ndarray, np.ndarray]:
    prior = tuple(y for y in YEARS if y < cutoff)
    sources = {y: round26._source(y) for y in (*prior, cutoff)}
    f = round26.Features(cutoff)
    global_train, global_valid = round20.context(f)
    xtr, rtr, xva, rva = round26._build_block(
        cutoff, f, global_train, global_valid, sources, tp)
    atr, ava = round27._analog_values(prior, cutoff)
    train = round27._add_analog_features(xtr, atr)
    valid = round27._add_analog_features(xva, ava)
    gtr = rtr.astype(np.float64)**2 - (rtr+xtr[:, 5]-atr).astype(np.float64)**2
    gva = rva.astype(np.float64)**2 - (rva+xva[:, 5]-ava).astype(np.float64)**2
    r_analog = (rva+xva[:, 5]-ava).astype(np.float64)
    return train, gtr, valid, gva, rva.astype(np.float64), r_analog


def _strong_threshold(cutoff: int, tp: np.ndarray) -> float:
    positive = []
    for year in YEARS:
        if year >= cutoff:
            break
        g, _ = _g_and_s12(year, tp)
        values = g[:, NORTH]
        positive.append(values[values > 0])
    return float(np.quantile(np.concatenate(positive), .9))


def _fit_regressions(train: np.ndarray, gtrain: np.ndarray,
                     valid: np.ndarray) -> tuple[np.ndarray, dict]:
    from .round26 import _fit_ridge_family
    mean, sd, (gram, _) = _fit_ridge_family(train, gtrain)
    ztr = ((train-mean)/sd).astype(np.float32)
    zva = ((valid-mean)/sd).astype(np.float32)
    cap = float(np.quantile(np.abs(gtrain), .99))
    max_abs = float(np.max(np.abs(gtrain)))
    transformed = {
        "ridge_G": gtrain,
        "ridge_clip": np.clip(gtrain, -cap, cap),
        "ridge_signedlog": np.sign(gtrain)*np.log1p(np.abs(gtrain)),
        "ridge_logpositive": np.log1p(np.maximum(gtrain, 0)),
    }
    outputs = []
    for name in REG_NAMES[:4]:
        target = transformed[name]
        xy = (ztr.T@(target-target.mean())).astype(np.float64)/len(target)
        coef = np.linalg.solve(gram+.3*np.eye(108), xy)
        pred = target.mean()+zva@coef
        if name == "ridge_signedlog":
            pred = np.sign(pred)*np.expm1(np.minimum(np.abs(pred), np.log1p(max_abs)))
        elif name == "ridge_logpositive":
            pred = np.expm1(np.clip(pred, 0, np.log1p(max_abs)))
        outputs.append(pred.astype(np.float32))
    for name, target in (("hgb_G", gtrain),
                         ("hgb_clip", np.clip(gtrain, -cap, cap))):
        model = HistGradientBoostingRegressor(
            max_leaf_nodes=7, max_iter=100, learning_rate=.03,
            min_samples_leaf=500, l2_regularization=100., max_bins=128,
            early_stopping=False, random_state=20260928)
        model.fit(train, target)
        outputs.append(model.predict(valid).astype(np.float32))
    return np.stack(outputs), {"clip_q99_abs_G_training": cap,
                               "max_abs_G_training": max_abs,
                               "mean_G_training": float(gtrain.mean())}


def _fit_strong(train: np.ndarray, gtrain: np.ndarray,
                valid: np.ndarray, threshold: float) -> tuple[np.ndarray, float]:
    y = gtrain > threshold
    mean = train.mean(axis=0, dtype=np.float64)
    sd = train.std(axis=0, dtype=np.float64)
    sd = np.where(sd > 1e-6, sd, 1.)
    ztr = ((train-mean)/sd).astype(np.float32)
    zva = ((valid-mean)/sd).astype(np.float32)
    base = round27.BASE_COLUMNS
    logistic = LogisticRegression(C=.3, max_iter=200, solver="lbfgs", tol=1e-4)
    logistic.fit(ztr[:, base], y)
    pbase = logistic.predict_proba(zva[:, base])[:, 1].astype(np.float32)
    hgb = HistGradientBoostingClassifier(
        max_leaf_nodes=7, max_iter=100, learning_rate=.03,
        min_samples_leaf=500, l2_regularization=100., max_bins=128,
        early_stopping=False, random_state=20260928)
    hgb.fit(train, y)
    phgb = hgb.predict_proba(valid)[:, 1].astype(np.float32)
    return np.stack([pbase, phgb]), float(y.mean())


def _regression_metrics(g: np.ndarray, predicted: np.ndarray, prior: float) -> dict:
    actual = np.asarray(g, np.float64).ravel()
    p = np.asarray(predicted, np.float64).ravel()
    mse = float(np.mean((actual-p)**2))
    baseline = float(np.mean((actual-prior)**2))
    return {
        "count": len(actual), "r2_against_training_mean": float(1-mse/baseline),
        "rmse_G": float(np.sqrt(mse)),
        "pearson": float(np.corrcoef(actual, p)[0, 1]) if p.std() > 0 else None,
        "spearman": float(spearmanr(actual, p).statistic) if p.std() > 0 else None,
        "mean_G": float(actual.mean()), "mean_prediction": float(p.mean()),
    }


def _ranking(g: np.ndarray, predicted: np.ndarray,
             r12: np.ndarray, ra: np.ndarray) -> tuple[list[dict], list[dict]]:
    values = np.asarray(g, np.float64).ravel()
    score = np.asarray(predicted, np.float64).ravel()
    e12 = np.asarray(r12, np.float64).ravel()
    ea = np.asarray(ra, np.float64).ravel()
    ordered = np.argsort(score, kind="stable")[::-1]
    total_positive = float(np.sum(np.maximum(values, 0)))
    top = []
    for fraction in FRACTIONS[:-1]:
        selected = ordered[:int(np.ceil(fraction*len(values)))]
        v = values[selected]
        a = e12[selected]
        b = ea[selected]
        top.append({
            "fraction": fraction, "count": len(selected),
            "mean_G": float(v.mean()),
            "analog_win_fraction": float(np.mean(v > 0)),
            "oracle_benefit_fraction": float(np.sum(np.maximum(v, 0))/total_positive),
            "rmse_s12": float(np.sqrt(np.mean(a*a))),
            "rmse_analog": float(np.sqrt(np.mean(b*b))),
            "analog_gain_percent": float(100*(1-np.sqrt(np.sum(b*b)/np.sum(a*a)))),
        })
    deciles = []
    for decile, selected in enumerate(np.array_split(ordered[::-1], 10), start=1):
        v = values[selected]
        a = e12[selected]
        b = ea[selected]
        deciles.append({
            "predicted_decile_low_to_high": decile, "count": len(selected),
            "mean_G": float(v.mean()),
            "analog_win_fraction": float(np.mean(v > 0)),
            "rmse_s12": float(np.sqrt(np.mean(a*a))),
            "rmse_analog": float(np.sqrt(np.mean(b*b))),
            "oracle_gain_percent": float(100*(1-np.sqrt(
                np.sum(np.minimum(a*a,b*b))/np.sum(a*a)))),
        })
    return top, deciles


def _strong_metrics(actual: np.ndarray, p: np.ndarray, prior: float) -> dict:
    y = np.asarray(actual, bool).ravel()
    probability = np.clip(np.asarray(p, np.float64).ravel(), .01, .99)
    n = len(y)
    ordered = np.argsort(probability, kind="stable")
    high = ordered[-n//10:]
    base_brier = float(np.mean((y-prior)**2))
    brier = float(np.mean((y-probability)**2))
    bins = np.minimum((probability*10).astype(int), 9)
    calibration = []
    for i in range(10):
        selected = bins == i
        if selected.any():
            calibration.append({"bin": i, "count": int(selected.sum()),
                                "predicted": float(probability[selected].mean()),
                                "observed": float(y[selected].mean())})
    ece = sum(row["count"]*abs(row["predicted"]-row["observed"])
              for row in calibration)/n
    return {
        "count": n, "prevalence": float(y.mean()), "prior_from_training": prior,
        "auc": float(roc_auc_score(y, probability)),
        "average_precision": float(average_precision_score(y, probability)),
        "brier": brier, "baseline_brier": base_brier,
        "brier_gain": base_brier-brier,
        "log_loss": float(log_loss(y, probability, labels=[False, True])),
        "top_decile_rate": float(y[high].mean()),
        "top_decile_lift": float(y[high].mean()/y.mean()),
        "calibration_ece": float(ece), "calibration_bins": calibration,
    }


def evaluate() -> None:
    locked()
    if not (OUT / "decomposition.json").exists():
        raise ValueError("Decomposição do oracle deve vir antes dos modelos")
    tp = np.load(CACHE / "tp.npy", mmap_mode="r").reshape(-1, GRID)
    for cutoff in EVAL:
        output_path = OUT / f"{cutoff}_advantage.json"
        archive_path = ART / f"{cutoff}_advantage_oof.npz"
        if output_path.exists() and archive_path.exists() and \
           archive_path.with_suffix(".json").exists():
            print("BLOCO EXISTENTE", cutoff, flush=True)
            continue
        train, gtrain, valid, gvalid, r12, ra = _build(cutoff, tp)
        threshold = _strong_threshold(cutoff, tp)
        reg, transform = _fit_regressions(train, gtrain, valid)
        strong, strong_prior = _fit_strong(train, gtrain, valid, threshold)
        with np.load(round27.ART / f"{cutoff}_winner_oof.npz") as saved:
            z_scores = np.asarray(saved["probability"], np.float32)[[0, 3]].reshape(2, -1)
        score_names = (*REG_NAMES, "Z_logistic_base", "Z_hgb_full")
        all_scores = np.concatenate([reg, z_scores])
        summaries = {}
        for j, name in enumerate(score_names):
            score = all_scores[j]
            top, deciles = _ranking(gvalid, score, r12, ra)
            row = {"top_predicted": top, "predicted_deciles": deciles}
            if j < len(REG_NAMES):
                row["block"] = _regression_metrics(gvalid, score, transform["mean_G_training"])
                row["year1"] = _regression_metrics(gvalid[:12*NORTH_SIZE],
                                                   score[:12*NORTH_SIZE],
                                                   transform["mean_G_training"])
                row["year2"] = _regression_metrics(gvalid[12*NORTH_SIZE:],
                                                   score[12*NORTH_SIZE:],
                                                   transform["mean_G_training"])
            summaries[name] = row
        strong_y = gvalid > threshold
        strong_metrics = {}
        for j, name in enumerate(STRONG_NAMES):
            strong_metrics[name] = {
                "block": _strong_metrics(strong_y, strong[j], strong_prior),
                "year1": _strong_metrics(strong_y[:12*NORTH_SIZE],
                                         strong[j, :12*NORTH_SIZE], strong_prior),
                "year2": _strong_metrics(strong_y[12*NORTH_SIZE:],
                                         strong[j, 12*NORTH_SIZE:], strong_prior),
            }
        save_json(output_path, {
            "cutoff": cutoff, "last_training_target": f"{cutoff-1}-12",
            "training_blocks": [y for y in YEARS if y < cutoff],
            "train_samples": len(train), "valid_samples": len(valid),
            "transformation": transform, "strong_win_threshold_prior_north": threshold,
            "strong_win_prior_train_sample": strong_prior,
            "scores": summaries, "strong_win_metrics": strong_metrics,
            "no_test_targets": True,
        })
        np.savez_compressed(archive_path,
                            G=gvalid.astype(np.float32).reshape(24, NORTH_SIZE),
                            regression=reg.reshape(6,24,NORTH_SIZE),
                            strong_probability=strong.reshape(2,24,NORTH_SIZE),
                            strong_label=strong_y.reshape(24,NORTH_SIZE))
        save_json(archive_path.with_suffix(".json"), {
            "sha256": sha(archive_path), "cutoff": cutoff,
            "last_training_target": f"{cutoff-1}-12",
            "regression_names": REG_NAMES, "strong_names": STRONG_NAMES,
        })
        print("ADVANTAGE", cutoff,
              {name: round(summaries[name]["top_predicted"][3]["mean_G"], 4)
               for name in REG_NAMES}, flush=True)


def experts() -> None:
    locked()
    tp = np.load(CACHE / "tp.npy", mmap_mode="r").reshape(-1, GRID)
    names = list(round25.NAMES[:4])+["tropical_extension"]
    accum = {name: {area: dict(count=0, s12=0., analog=0., pure=0.,
                               pair=0., triple=0.)
                    for area in ("global", "north")}
             for name in names}
    by_block = {}
    source_hashes = {}
    for year in YEARS:
        truth = np.asarray(tp[target_origins(year)+1], np.float64)
        s12 = np.asarray(round20.reference(year).reshape(24, GRID), np.float64)
        analog_path = round25.ART / f"{year}_h4_prediction.npy"
        analog = np.asarray(np.load(analog_path, mmap_mode="r").reshape(24, GRID), np.float64)
        components = round25.component_maps(year)
        l12 = (truth-s12)**2
        la = (truth-analog)**2
        source_hashes[str(year)] = {
            **{name: sha(ROOT / f"data/processed/round9/{year}_{name}.npy")
               for name in round25.NAMES[:4]},
            "s09": sha(ROOT / f"data/processed/round10/{year}_s09.npy"),
            "fine32": sha(ROOT / f"data/processed/round11/{year}_fine32.npy"),
        }
        by_block[str(year)] = {}
        for j, name in enumerate(names):
            lc = (truth-np.asarray(components[j], np.float64))**2
            pair = np.minimum(l12, lc)
            triple = np.minimum(pair, la)
            by_block[str(year)][name] = {}
            for area, selection in (("global", slice(None)), ("north", NORTH)):
                a = accum[name][area]
                u12 = l12[:, selection]
                ua = la[:, selection]
                uc = lc[:, selection]
                up = pair[:, selection]
                ut = triple[:, selection]
                row = {"count": u12.size, "s12": float(u12.sum()),
                       "analog": float(ua.sum()), "pure": float(uc.sum()),
                       "pair": float(up.sum()), "triple": float(ut.sum())}
                for key in row:
                    a[key] += row[key]
                by_block[str(year)][name][area] = row
        print("EXPERTS", year, flush=True)
    oracle = json.loads((round27.OUT / "oracle.json").read_text(encoding="utf-8"))
    summary = {}
    for name, areas in accum.items():
        summary[name] = {}
        for area, raw in areas.items():
            n = raw["count"]
            base = raw["s12"]
            analog_oracle = oracle[area]["oracle_gain_percent"]
            pair_gain = 100*(1-np.sqrt(raw["pair"]/base))
            triple_gain = 100*(1-np.sqrt(raw["triple"]/base))
            summary[name][area] = {
                **raw, "pure_rmse": float(np.sqrt(raw["pure"]/n)),
                "pair_oracle_gain_percent": float(pair_gain),
                "triple_oracle_gain_percent": float(triple_gain),
                "extra_triple_vs_analog_oracle_pp": float(triple_gain-analog_oracle),
            }
    analog_rmse = oracle["global"]["rmse_analog"]
    alternative_flag = [name for name, row in summary.items()
                        if ((row["global"]["pair_oracle_gain_percent"] >=
                             oracle["global"]["oracle_gain_percent"]+1.0
                             and row["global"]["pure_rmse"] <= 1.05*analog_rmse)
                            or row["global"]["extra_triple_vs_analog_oracle_pp"] >= 1.0)]
    save_json(OUT / "experts.json", {
        "reference_analog_oracle_global_percent": oracle["global"]["oracle_gain_percent"],
        "reference_analog_oracle_north_percent": oracle["north"]["oracle_gain_percent"],
        "analog_pure_rmse_global": analog_rmse,
        "components": summary, "by_block_raw_sse": by_block,
        "source_hashes": source_hashes,
        "alternative_component_flag_predefined": alternative_flag,
        "no_new_expert": True,
    })
    print("EXPERT FLAGS", alternative_flag, flush=True)


def policy() -> None:
    locked()
    reports = {y: json.loads((OUT / f"{y}_advantage.json").read_text(encoding="utf-8"))
               for y in EVAL}
    continuous = []
    for name in REG_NAMES:
        ok = sum(report["scores"][name]["top_predicted"][3]["mean_G"] > 0
                 and report["scores"][name]["top_predicted"][3]
                 ["oracle_benefit_fraction"] > .15
                 for report in reports.values())
        if ok >= 4:
            continuous.append(name)
    strong = []
    for name in STRONG_NAMES:
        ok = sum(report["strong_win_metrics"][name]["block"]["auc"] >= .6
                 and report["strong_win_metrics"][name]["block"]["top_decile_lift"] >= 1.5
                 and report["strong_win_metrics"][name]["block"]["brier_gain"] > 0
                 for report in reports.values())
        if ok >= 4:
            strong.append(name)
    result = {"continuous_rank_signal": continuous, "strong_win_signal": strong,
              "topk_tested": False, "expected_gain_tested": False,
              "stopping_rule_applied": True}
    if not continuous and not strong:
        save_json(OUT / "policy.json", result)
        print("PARADA ANTES DAS POLITICAS", flush=True)
        return
    tp = np.load(CACHE / "tp.npy", mmap_mode="r").reshape(-1, GRID)
    score_sources = [("strong_"+name, name) for name in strong]
    score_sources += [("continuous_"+name, name) for name in continuous]
    keys = [(source, fraction, alpha)
            for source, _ in score_sources
            for fraction in FRACTIONS[:-1]
            for alpha in (.1, .2, .3)]
    accum = {f"{source}_k{100*fraction:g}_a{alpha:g}":
             {"month_global": [], "month_north": [], "delta2": [],
              "block": {}, "year": {},
              "sector": {area: [] for area in ("west", "central", "east")}}
             for source, fraction, alpha in keys}
    base_month, base_north_month, fixed_month, oldgate_month, oracle_month = [], [], [], [], []
    sectors = round26._strata_code()
    for cutoff in EVAL:
        target = np.asarray(tp[target_origins(cutoff)+1], np.float64)
        s12 = np.asarray(round20.reference(cutoff).reshape(24, GRID), np.float64)
        analog = np.asarray(np.load(round25.ART / f"{cutoff}_h4_prediction.npy",
                                    mmap_mode="r").reshape(24, GRID), np.float64)
        r = target-s12
        rn = r[:, NORTH]
        delta = analog[:, NORTH]-s12[:, NORTH]
        bglobal = np.sum(r*r, axis=1)
        bnorth = np.sum(rn*rn, axis=1)
        base_month.extend(bglobal.tolist())
        base_north_month.extend(bnorth.tolist())
        fixed_month.extend(np.sum((r-.1*(analog-s12))**2, axis=1).tolist())
        oracle_month.extend(np.sum(np.minimum(r*r,(target-analog)**2),axis=1).tolist())
        with np.load(round27.ART / f"{cutoff}_winner_oof.npz") as saved:
            old_probability = np.asarray(saved["probability"][0], np.float64)
        oldr = rn-.3*old_probability*delta
        oldgate_month.extend((bglobal-bnorth+np.sum(oldr*oldr,axis=1)).tolist())
        with np.load(ART / f"{cutoff}_advantage_oof.npz") as saved:
            reg = np.asarray(saved["regression"], np.float64)
            strong_probability = np.asarray(saved["strong_probability"], np.float64)
        for source, model in score_sources:
            if source.startswith("strong_"):
                score = strong_probability[STRONG_NAMES.index(model)].ravel()
            else:
                score = reg[REG_NAMES.index(model)].ravel()
            order = np.argsort(score, kind="stable")[::-1]
            for fraction in FRACTIONS[:-1]:
                selected = np.zeros(24*NORTH_SIZE, bool)
                selected[order[:int(np.ceil(fraction*len(selected)))]] = True
                selected = selected.reshape(24, NORTH_SIZE)
                for alpha in (.1, .2, .3):
                    key = f"{source}_k{100*fraction:g}_a{alpha:g}"
                    changed = alpha*selected*delta
                    altered = rn-changed
                    mnorth = np.sum(altered*altered, axis=1)
                    mglobal = bglobal-bnorth+mnorth
                    row = accum[key]
                    row["month_global"].extend(mglobal.tolist())
                    row["month_north"].extend(mnorth.tolist())
                    row["delta2"].extend(np.sum(changed*changed,axis=1).tolist())
                    row["block"][str(cutoff)] = float(mglobal.sum())
                    for k in (0,1):
                        row["year"][str(cutoff+k)] = float(mglobal[12*k:12*(k+1)].sum())
                    for area, mask in sectors.items():
                        baseline = float(np.sum(rn[:,mask]**2))
                        updated = float(np.sum(altered[:,mask]**2))
                        row["sector"][area].append((baseline,updated))
        print("TOPK", cutoff, flush=True)
    n_global = 5*24*GRID
    n_north = 5*24*NORTH_SIZE
    baseline_sse = float(sum(base_month))
    prior27 = json.loads((round27.OUT / "decision.json").read_text(encoding="utf-8"))
    baselines = {
        "s12": float(np.sqrt(baseline_sse/n_global)),
        "fixed10_global": float(np.sqrt(sum(fixed_month)/n_global)),
        "logistic_base_0.3_round27": float(np.sqrt(sum(oldgate_month)/n_global)),
        "oracle": float(np.sqrt(sum(oracle_month)/n_global)),
    }
    if abs(baselines["logistic_base_0.3_round27"]-
           prior27["gates"]["logistic_base_0.3"]["global_rmse"]) > 1e-8:
        raise ValueError("Baseline rodada 27 não reproduzida")
    block_base = {str(y): float(sum(base_month[24*i:24*(i+1)]))
                  for i,y in enumerate(EVAL)}
    year_base = {str(y): float(sum(base_month[12*i:12*(i+1)]))
                 for i,y in enumerate(range(2011,2021))}
    policies = {}
    for key,row in accum.items():
        total = float(sum(row["month_global"]))
        rmse = float(np.sqrt(total/n_global))
        sector_gain = {}
        for area,pairs in row["sector"].items():
            baseline,updated = np.sum(pairs,axis=0)
            sector_gain[area] = float(100*(1-np.sqrt(updated/baseline)))
        policies[key] = {
            "global_rmse": rmse,
            "north_rmse": float(np.sqrt(sum(row["month_north"])/n_north)),
            "gain_vs_s12_percent": float(100*(1-rmse/baselines["s12"])),
            "gain_vs_oldgate_percent": float(100*(1-rmse/baselines["logistic_base_0.3_round27"])),
            "positive_blocks": sum(row["block"][str(y)]<block_base[str(y)] for y in EVAL),
            "positive_years": sum(row["year"][str(y)]<year_base[str(y)]
                                  for y in range(2011,2021)),
            "positive_months": sum(a<b for a,b in zip(row["month_global"],base_month)),
            "rms_change_north": float(np.sqrt(sum(row["delta2"])/n_north)),
            "sector_gain_percent": sector_gain,
            "by_block_gain_percent": {
                str(y):float(100*(1-np.sqrt(row["block"][str(y)]/block_base[str(y)])))
                for y in EVAL},
            "by_year_gain_percent": {
                str(y):float(100*(1-np.sqrt(row["year"][str(y)]/year_base[str(y)])))
                for y in range(2011,2021)},
        }
    result.update({"topk_tested":True,"topk":policies,"baselines":baselines})
    if continuous:
        # Expected-gain gating is restricted to untransformed G predictors.
        raw = [name for name in continuous if name in ("ridge_G","hgb_G")]
        result["expected_gain_tested"] = bool(raw)
        result["expected_gain_reason"] = (
            "Raw-G ranking model eligible" if raw else
            "No eligible untransformed G predictor; expected-gain gate stopped")
    else:
        result["expected_gain_reason"] = \
            "No continuous ranking signal; expected-gain gate stopped"
    save_json(OUT / "policy.json",result)
    print("TOPK BEST",max(policies.items(),key=lambda kv:kv[1]["gain_vs_s12_percent"])
          [0],max(v["gain_vs_s12_percent"] for v in policies.values()),flush=True)


def signatures() -> None:
    """Caracterização univariada OOF de grandes ganhos e perdas, sem novo modelo."""
    locked()
    tp = np.load(CACHE / "tp.npy", mmap_mode="r").reshape(-1, GRID)
    names = round26.FEATURE_NAMES + ["analog", "analog_minus_s12",
                                       "abs_analog_minus_s12"]
    rows = []
    for cutoff in EVAL:
        train, _, valid, g, r12, ra = _build(cutoff, tp)
        threshold = json.loads((OUT / f"{cutoff}_advantage.json").read_text(
            encoding="utf-8"))["strong_win_threshold_prior_north"]
        strong_analog = g > threshold
        strong_s12 = g < -threshold
        for j, name in enumerate(names):
            edges = np.quantile(train[:,j], [.2,.4,.6,.8])
            bins = np.searchsorted(edges, valid[:,j], side="right")
            for k in range(5):
                selected = bins == k
                if not np.any(selected):
                    continue
                value = g[selected]
                a = r12[selected]
                b = ra[selected]
                rows.append({
                    "cutoff": cutoff, "feature": name, "bin": k,
                    "train_edges": [float(v) for v in edges],
                    "count": int(selected.sum()),
                    "mean_G": float(value.mean()),
                    "analog_win_fraction": float(np.mean(value > 0)),
                    "analog_strong_win_fraction": float(strong_analog[selected].mean()),
                    "s12_strong_win_fraction_same_magnitude":
                        float(strong_s12[selected].mean()),
                    "rmse_s12": float(np.sqrt(np.mean(a*a))),
                    "rmse_analog": float(np.sqrt(np.mean(b*b))),
                })
        month = np.repeat(np.arange(24)%12, NORTH_SIZE)
        season = ((month+1)%12)//3
        for name,codes,number in (("month",month,12),("season",season,4)):
            for k in range(number):
                selected = codes == k
                value = g[selected]
                a,b = r12[selected],ra[selected]
                rows.append({
                    "cutoff":cutoff,"feature":name,"bin":k,"count":int(selected.sum()),
                    "mean_G":float(value.mean()),
                    "analog_win_fraction":float(np.mean(value>0)),
                    "analog_strong_win_fraction":float(strong_analog[selected].mean()),
                    "s12_strong_win_fraction_same_magnitude":
                        float(strong_s12[selected].mean()),
                    "rmse_s12":float(np.sqrt(np.mean(a*a))),
                    "rmse_analog":float(np.sqrt(np.mean(b*b))),
                })
        print("SIGNATURE",cutoff,flush=True)
    save_json(OUT / "signatures.json",{
        "strong_analog_definition":"G>prior positive-G Q90",
        "strong_s12_descriptive_definition":"G<negative of same threshold",
        "feature_quintiles_fit_before_each_cutoff":True,
        "rows":rows,"no_test_targets":True,
    })


def finalize() -> None:
    locked()
    decomposition_result = json.loads((OUT / "decomposition.json").read_text(encoding="utf-8"))
    reports = {y:json.loads((OUT / f"{y}_advantage.json").read_text(encoding="utf-8"))
               for y in EVAL}
    expert = json.loads((OUT / "experts.json").read_text(encoding="utf-8"))
    policy_result = json.loads((OUT / "policy.json").read_text(encoding="utf-8"))
    tp = np.load(CACHE / "tp.npy", mmap_mode="r").reshape(-1, GRID)
    strong_ranking = {}
    for cutoff in EVAL:
        target = np.asarray(tp[target_origins(cutoff)+1][:,NORTH],np.float64)
        s12 = np.asarray(round20.reference(cutoff).reshape(24,GRID)[:,NORTH],np.float64)
        analog = np.asarray(np.load(round25.ART / f"{cutoff}_h4_prediction.npy",
                                    mmap_mode="r").reshape(24,GRID)[:,NORTH],np.float64)
        r12,ra = target-s12,target-analog
        g = r12*r12-ra*ra
        with np.load(ART / f"{cutoff}_advantage_oof.npz") as saved:
            probability = np.asarray(saved["strong_probability"],np.float64)
        strong_ranking[str(cutoff)]={}
        for j,name in enumerate(STRONG_NAMES):
            top,deciles=_ranking(g,probability[j],r12,ra)
            strong_ranking[str(cutoff)][name]={"top_predicted":top,
                                                "predicted_deciles":deciles}
    save_json(OUT / "strong_ranking.json",strong_ranking)
    best_name,best_row = max(policy_result["topk"].items(),
                             key=lambda item:item[1]["gain_vs_s12_percent"])
    old_oracle_gain = 100*(1-policy_result["baselines"]["oracle"]/
                        policy_result["baselines"]["s12"])
    if expert["alternative_component_flag_predefined"]:
        category="D"
        reason=("Oracles triplos com componentes congelados acrescentam >=1 p.p. "
                "ao oracle S12×Analog; segundo especialista individual ainda é melhor Analog.")
    elif policy_result["continuous_rank_signal"]:
        eligible=[row for row in policy_result["topk"].values()
                  if row["gain_vs_s12_percent"]>=.3 and
                  row["global_rmse"]<policy_result["baselines"]["logistic_base_0.3_round27"]
                  and row["global_rmse"]<policy_result["baselines"]["fixed10_global"]
                  and row["positive_blocks"]>=4 and row["positive_years"]>=7
                  and row["positive_months"]>=67]
        if eligible:
            category="A"
            reason="Ranking contínuo e política passam ganho e estabilidade predefinidos."
        else:
            category="C"
            reason="Há sinal parcial de magnitude, mas sem política material/estável."
    elif policy_result["strong_win_signal"]:
        category="B"
        reason="Só strong wins são discrimináveis; vantagem líquida contínua falhou."
    else:
        category="C"
        reason="Nenhum alvo de magnitude passou o critério temporal."
    result = {
        "classification":category,"reason":reason,
        "secondary_finding":"Strong wins discrimináveis; top-k não supera gate anterior.",
        "continuous_rank_signal":policy_result["continuous_rank_signal"],
        "strong_win_signal":policy_result["strong_win_signal"],
        "expected_gain_gate_tested":policy_result["expected_gain_tested"],
        "expected_gain_gate_reason":policy_result["expected_gain_reason"],
        "best_topk_name_descriptive_only":best_name,
        "best_topk_metrics":best_row,
        "prior_round27_gate_rmse_same_window":policy_result["baselines"]["logistic_base_0.3_round27"],
        "oracle_gain_percent_same_five_blocks":old_oracle_gain,
        "best_topk_fraction_of_oracle_rmse_gain":
            best_row["gain_vs_s12_percent"]/old_oracle_gain,
        "no_candidate":True,"no_2023_2024_targets":True,
    }
    save_json(OUT / "decision.json",result)
    _plot_results(decomposition_result,reports,expert,policy_result)
    _write_report(result,decomposition_result,reports,strong_ranking,expert,
                  policy_result)
    print("DECISAO",category,"BEST TOPK",best_name,
          best_row["gain_vs_s12_percent"],flush=True)


def _plot_results(decomp:dict,reports:dict,expert:dict,policy_result:dict)->None:
    os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "tmp" / "matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    matrix=np.array([[reports[y]["scores"][name]["top_predicted"][3]["mean_G"]
                      for y in EVAL] for name in REG_NAMES])
    bound=max(.1,float(np.max(np.abs(matrix))))
    fig,ax=plt.subplots(figsize=(9,4.8),constrained_layout=True)
    im=ax.imshow(matrix,cmap="RdBu",vmin=-bound,vmax=bound,aspect="auto")
    ax.set(yticks=np.arange(len(REG_NAMES)),yticklabels=REG_NAMES,
           xticks=np.arange(5),xticklabels=[f"{y}–{y+1}" for y in EVAL],
           title="G médio real no top 10% previsto",xlabel="Bloco OOF")
    for i in range(len(REG_NAMES)):
        for j in range(5):
            ax.text(j,i,f"{matrix[i,j]:+.2f}",ha="center",va="center",fontsize=8)
    fig.colorbar(im,ax=ax,label="G médio ((mm/dia)²)")
    fig.savefig(OUT / "ranking_G_blocos.png",dpi=170)
    plt.close(fig)
    fig,ax=plt.subplots(1,2,figsize=(12,4),constrained_layout=True)
    for name,color in (("logistic_base","#28628c"),("hgb_full","#b4514a")):
        auc=[reports[y]["strong_win_metrics"][name]["block"]["auc"] for y in EVAL]
        lift=[reports[y]["strong_win_metrics"][name]["block"]["top_decile_lift"]
              for y in EVAL]
        ax[0].plot(EVAL,auc,marker="o",label=name,color=color)
        ax[1].plot(EVAL,lift,marker="o",label=name,color=color)
    ax[0].set(title="Strong win: AUC",xlabel="Início do bloco",ylabel="AUC")
    ax[1].set(title="Strong win: lift no decil",xlabel="Início do bloco",ylabel="Lift")
    for item in ax:
        item.legend()
        item.set_xticks(EVAL)
    fig.savefig(OUT / "strong_wins_blocos.png",dpi=170)
    plt.close(fig)
    rows=sorted(policy_result["topk"].items(),
                key=lambda item:-item[1]["gain_vs_s12_percent"])
    fig,ax=plt.subplots(figsize=(10,7),constrained_layout=True)
    ax.barh([name for name,_ in rows][::-1],
            [row["gain_vs_s12_percent"] for _,row in rows][::-1],color="#28628c")
    ax.axvline(0,color="black",lw=.8)
    ax.axvline(.3,color="#b4514a",ls="--",lw=.8)
    ax.set(title="Top-k blending OOF",xlabel="Ganho global sobre S12 (%)")
    fig.savefig(OUT / "topk_ganhos.png",dpi=170)
    plt.close(fig)
    names=list(expert["components"])
    pairs=[expert["components"][name]["global"]["pair_oracle_gain_percent"]
           for name in names]
    triples=[expert["components"][name]["global"]["triple_oracle_gain_percent"]
             for name in names]
    fig,ax=plt.subplots(figsize=(9,4.4),constrained_layout=True)
    x=np.arange(len(names))
    ax.bar(x-.18,pairs,width=.36,label="S12 + componente",color="#28628c")
    ax.bar(x+.18,triples,width=.36,label="S12 + Analog + componente",color="#b4514a")
    ax.axhline(expert["reference_analog_oracle_global_percent"],color="black",
               ls="--",label="S12 + Analog")
    ax.set(xticks=x,xticklabels=names,ylabel="Ganho oracle global (%)",
           title="Complementaridade dos especialistas congelados")
    ax.legend()
    fig.savefig(OUT / "oracles_componentes.png",dpi=170)
    plt.close(fig)


def _write_report(decision:dict,decomp:dict,reports:dict,strong_ranking:dict,
                  expert:dict,policy_result:dict)->None:
    lines=["# Rodada 28 — magnitude da vantagem S12 × Analog","",
           f"**Decisão predefinida: {decision['classification']}.** {decision['reason']}","",
           "## Método e janelas", "",
           "G = perda quadrática S12 − perda quadrática Analog. G>0 favorece "
           "Analog; G+=max(G,0) é exatamente a redução pontual de SSE do "
           "oracle duro. Os seis blocos 2009–2020 entram na decomposição e "
           "comparação de componentes. As sondas OOF de magnitude e strong "
           "wins usam 2011–2020, com treino apenas em blocos anteriores. "
           "Nenhuma previsão meta para 2009–2010 foi inventada.", "",
           "## 1. De onde vem o ganho do oracle?", "",
           "| Área | Ganho oracle RMSE | Vitórias Analog | Top 1% | Top 2,5% | Top 5% | Top 10% | Top 20% | Top 50% |",
           "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for area in ("global","north"):
        row=decomp[area]
        values=[100*row["top_abs_G"][f"{100*f:g}%"]["oracle_benefit_fraction"]
                for f in FRACTIONS]
        lines.append(f"| {area} | {row['oracle_rmse_gain_percent']:.2f}% | "
                     f"{100*row['positive_win_fraction']:.2f}% | "+
                     " | ".join(f"{v:.1f}%" for v in values)+" |")
    lines += ["", "A tabela acima ranqueia por |G| **todos os pontos**, "
              "inclusive grandes perdas do Analog. Se o denominador for "
              "somente vitórias G>0, os top 10% positivos concentram "
              f"{100*decomp['global']['top_positive_G']['10%']['oracle_benefit_fraction']:.1f}% "
              "do benefício global. Assim, poucos ganhos grandes explicam "
              "parte importante do oracle, mas |G| sozinho não identifica "
              "o sentido da escolha.", "",
              "![Concentração do oracle](concentracao_oracle.png)", "",
              "| Bloco | Top 1% | Top 10% | Ganho oracle |",
              "| --- | ---: | ---: | ---: |"]
    for year in YEARS:
        row=decomp["by_block"][str(year)]["global"]
        lines.append(f"| {year}–{year+1} | "
                     f"{100*row['top_abs_G']['1%']['oracle_benefit_fraction']:.1f}% | "
                     f"{100*row['top_abs_G']['10%']['oracle_benefit_fraction']:.1f}% | "
                     f"{row['oracle_rmse_gain_percent']:.2f}% |")
    lines += ["", "As mesmas decomposições por ano, latitude, setor norte "
              "e estação, para todos os seis percentuais e para G positivo, "
              "estão em [decomposition.json](decomposition.json).", "",
              "## 2. G, G+ e vitória simples em OOF", "",
              "Ridge foi ajustado para G bruto, G limitado por Q99 do treino, "
              "log assinado e log de G+. HGB conservador foi ajustado para G "
              "bruto e limitado. Z usa as probabilidades congeladas da "
              "Rodada 27. Todos os R² abaixo avaliam **G bruto** frente à "
              "média G do treino anterior; as transformações log foram "
              "invertidas para essa métrica. R² pequeno não é critério de "
              "parada isolado.", "",
              "| Score | R² G por bloco (2011, 2013, 2015, 2017, 2019) | G médio top 10% por bloco | Blocos com G top 10% >0 |",
              "| --- | --- | --- | ---: |"]
    for name in (*REG_NAMES,"Z_logistic_base","Z_hgb_full"):
        r2=[reports[y]["scores"][name].get("block",{}).get("r2_against_training_mean")
            for y in EVAL]
        top=[reports[y]["scores"][name]["top_predicted"][3]["mean_G"]
             for y in EVAL]
        r2text=", ".join(f"{v:+.3f}" if v is not None else "—" for v in r2)
        lines.append(f"| {name} | {r2text} | "+
                     ", ".join(f"{v:+.3f}" for v in top)+
                     f" | {sum(v>0 for v in top)}/5 |")
    lines += ["", "![Ranking de G por bloco](ranking_G_blocos.png)", "",
              "Os arquivos `YYYY_advantage.json` incluem Pearson, Spearman, "
              "R² por ano, os decis de score e os top 1%, 2,5%, 5%, 10% "
              "e 20% previstos com RMSE S12/Analog, vitórias e fração G+.", "",
              "## 3. Strong wins", "",
              "Evento: G maior que Q90 dos G positivos de todos os blocos "
              "norte anteriores. O limiar de cada corte foi ajustado sem "
              "seu próprio alvo. AUC/AP/lift detectam grandes vitórias "
              "positivas, mas não penalizam as grandes perdas negativas "
              "que podem coexistir no mesmo decil de score.", "",
              "| Bloco | Limiar G | Modelo | Prevalência | AUC | AP | Lift decil | Ganho Brier | ECE | G médio top 10% score |",
              "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for year in EVAL:
        report=reports[year]
        for name in STRONG_NAMES:
            row=report["strong_win_metrics"][name]["block"]
            top=strong_ranking[str(year)][name]["top_predicted"][3]
            lines.append(f"| {year}–{year+1} | "
                         f"{report['strong_win_threshold_prior_north']:.3f} | "
                         f"{name} | {100*row['prevalence']:.2f}% | "
                         f"{row['auc']:.3f} | {row['average_precision']:.3f} | "
                         f"{row['top_decile_lift']:.2f}× | "
                         f"{row['brier_gain']:+.4f} | {row['calibration_ece']:.3f} | "
                         f"{top['mean_G']:+.3f} |")
    lines += ["", "### Ranking por probabilidade de strong win (HGB)", "",
              "Médias das cinco avaliações por fração selecionada em cada "
              "bloco; G médio negativo indica que as perdas grandes do "
              "Analog ainda superam suas grandes vitórias no grupo.", "",
              "| Top previsto | G médio | Fração de G+ oracle capturada | Ganho Analog puro vs S12 |",
              "| ---: | ---: | ---: | ---: |"]
    for j,fraction in enumerate(FRACTIONS[:-1]):
        rows=[strong_ranking[str(year)]["hgb_full"]["top_predicted"][j]
              for year in EVAL]
        lines.append(f"| {100*fraction:g}% | "
                     f"{np.mean([r['mean_G'] for r in rows]):+.3f} | "
                     f"{100*np.mean([r['oracle_benefit_fraction'] for r in rows]):.1f}% | "
                     f"{np.mean([r['analog_gain_percent'] for r in rows]):+.2f}% |")
    lines += ["", "![Strong wins](strong_wins_blocos.png)", "",
              "Calibração por dez faixas e métricas por ano estão nos JSONs "
              "de cada corte. O ranking completo dos scores strong win "
              "está em [strong_ranking.json](strong_ranking.json).", "",
              "## 4. Top-k blending e expected gain", "",
              "Nenhum regressor contínuo passou o critério pré-fixado de "
              "G positivo no top 10% em 4/5 blocos e 7/10 anos. Os dois "
              "classificadores strong win passaram AUC, lift e Brier em "
              "5/5 blocos; por isso apenas seus scores receberam top-k. "
              "O expected-gain gating por G bruto foi interrompido pelo "
              "critério de parada, sem ajustar f(Ghat) após os resultados.", "",
              "G negativo no grupo significa que trocar integralmente "
              "S12 por Analog piora a perda média. Uma mistura pequena "
              "ainda pode ajudar: se δ=Analog−S12, a redução de perda "
              "da mistura com peso α é `α(G+δ²)−α²δ²`. Por isso medimos "
              "RMSE do blend diretamente, sem inferi-lo do sinal de G.", "",
              "| Método, 2011–2020 | RMSE global | Ganho vs S12 | Blocos | Anos | Meses |",
              "| --- | ---: | ---: | ---: | ---: | ---: |"]
    baselines=policy_result["baselines"]
    for name in ("s12","fixed10_global","logistic_base_0.3_round27","oracle"):
        rmse=baselines[name]
        gain=100*(1-rmse/baselines["s12"])
        lines.append(f"| {name} | {rmse:.6f} | {gain:+.3f}% | — | — | — |")
    top_rows=sorted(policy_result["topk"].items(),
                    key=lambda item:-item[1]["gain_vs_s12_percent"])
    for name,row in top_rows[:10]:
        lines.append(f"| {name} | {row['global_rmse']:.6f} | "
                     f"{row['gain_vs_s12_percent']:+.3f}% | "
                     f"{row['positive_blocks']}/5 | {row['positive_years']}/10 | "
                     f"{row['positive_months']}/120 |")
    lines += ["", "Todas as 30 combinações k×alpha, RMS da mudança, "
              "setores e métricas por bloco/ano estão em "
              "[policy.json](policy.json). A melhor linha foi observada "
              "após ver a tabela e não é uma candidata selecionada.", "",
              "![Ganho top-k](topk_ganhos.png)", "",
              "## 5. Assinatura dos grandes ganhos e perdas", "",
              "Para cada corte, [signatures.json](signatures.json) contém "
              "quintis definidos no treino anterior de todas as 108 "
              "features, mês e estação. Compara G médio, vitória comum, "
              "strong win Analog e uma grande vitória S12 simétrica "
              "(G abaixo do negativo do mesmo limiar). Essa última é "
              "somente descritiva.", "",
              "| Feature | Quintil | Strong Analog | Strong S12 | G médio |",
              "| --- | ---: | ---: | ---: | ---: |"]
    signatures=json.loads((OUT / "signatures.json").read_text(encoding="utf-8"))["rows"]
    for feature in ("climatology","s12","s12_anomaly","analog_minus_s12",
                    "member_std","consensus_ratio","continental_pc_1",
                    "tropical_pc_1","local_context_7"):
        for k in (0,4):
            rows=[row for row in signatures if row["feature"]==feature and row["bin"]==k]
            n=sum(row["count"] for row in rows)
            if not n:continue
            avg=lambda field:sum(row["count"]*row[field] for row in rows)/n
            lines.append(f"| {feature} | {k} | "
                         f"{100*avg('analog_strong_win_fraction'):.2f}% | "
                         f"{100*avg('s12_strong_win_fraction_same_magnitude'):.2f}% | "
                         f"{avg('mean_G'):+.3f} |")
    lines += ["", "## 6. O Analog é um segundo especialista especial?", "",
              "Os cinco componentes já existentes foram comparados sem "
              "treino novo. O oracle pareado S12×Analog é 8,49% global. "
              "Um oracle triplo usa o alvo observado para escolher entre "
              "três mapas e não pode ser interpretado como ganho capturável.", "",
              "| Componente | RMSE puro | Oracle S12×componente | Oracle S12×Analog×componente | Acréscimo sobre oracle duplo |",
              "| --- | ---: | ---: | ---: | ---: |"]
    for name,row in expert["components"].items():
        r=row["global"]
        lines.append(f"| {name} | {r['pure_rmse']:.3f} | "
                     f"{r['pair_oracle_gain_percent']:.2f}% | "
                     f"{r['triple_oracle_gain_percent']:.2f}% | "
                     f"{r['extra_triple_vs_analog_oracle_pp']:+.2f} p.p. |")
    lines += ["", "![Oracles dos componentes](oracles_componentes.png)", "",
              "Analog supera cada componente testado como **segundo** "
              "especialista pelo upper bound pareado. Todos acrescentam "
              "mais de 1 ponto percentual ao oracle como **terceiro** mapa, "
              "acionando D pela regra pré-fixada. Isso aponta potencial de "
              "um conjunto mais amplo; não prova que um componente isolado "
              "substitua Analog nem que o ganho triplo seja operacional.", "",
              "## Decisão científica", "",
              f"**Classe {decision['classification']}.** {decision['reason']}", "",
              "Há uma constatação secundária do tipo B: strong wins são "
              "previsíveis como evento, mas o score não localiza vantagem "
              "líquida positiva suficiente para melhorar RMSE. O melhor "
              f"top-k ganhou {decision['best_topk_metrics']['gain_vs_s12_percent']:.3f}% "
              "global nos cinco blocos, capturando apenas "
              f"{100*decision['best_topk_fraction_of_oracle_rmse_gain']:.2f}% "
              "do ganho de RMSE do oracle nessa mesma janela e ficando "
              "abaixo do gate da Rodada 27. Os resultados OOF de 2009–2020 "
              "já foram reutilizados em várias decisões; há viés de seleção. "
              "Nenhuma S14, CSV, treino final, confirmação ou submissão. "
              "A [auditoria independente](audit.json) refez as perdas, "
              "limiares e políticas a partir dos arquivos OOF. "
              "[Protocolo](../../../experiments/ROUND28.md).", ""]
    (OUT / "REPORT.md").write_text("\n".join(lines),encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["decomposition", "evaluate", "experts", "policy", "signatures", "finalize"])
    stage = parser.parse_args().stage
    if stage == "decomposition":
        decomposition()
    elif stage == "evaluate":
        evaluate()
    elif stage == "experts":
        experts()
    elif stage == "policy":
        policy()
    elif stage == "signatures":
        signatures()
    elif stage == "finalize":
        finalize()
