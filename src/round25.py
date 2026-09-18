"""Rodada 25: diagnóstico S12, dinâmica latente e previsão por análogos."""
from __future__ import annotations

import os
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"

import argparse
import gc
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.cluster import KMeans
from sklearn.ensemble import HistGradientBoostingRegressor

from . import round20
from .competition import CACHE, ROOT, REPORT, save_json
from .round2 import Features, target_origins
from .round9 import passes_gate

YEARS = (2009, 2011, 2013, 2015, 2017, 2019)
OUT = REPORT / "round25"
ART = ROOT / "data/processed/round25"
PROTOCOL = ROOT / "experiments/ROUND25.md"
SOURCE = ROOT / "src/round25.py"
WEIGHTS = (.10, .25)
GRID = 78_561
LAT = np.repeat(np.arange(-60, 15.01, .25, dtype=np.float32), 261)
LON = np.tile(np.arange(-90, -24.99, .25, dtype=np.float32), 301)
NAMES = ("s02", "modes", "local18", "pls16", "tropical_extension")


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
        "protocol_sha256": digest(PROTOCOL),
        "source_sha256": digest(SOURCE),
        "reference": "S12",
        "years": YEARS,
        "h2_model": "global31_dense_plus_lag1",
        "h2_blend_weights": WEIGHTS,
        "h4": {"pcs_per_region": 4, "memory": "state_mean3",
               "season_radius": 1, "neighbors": 10, "weight": "uniform"},
        "h4_blend_weights": WEIGHTS,
        "official_only": True,
        "no_test_targets": True,
    }
    path = OUT / "protocol.json"
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != json.loads(json.dumps(record)):
            raise ValueError("Protocolo ou código da rodada 25 mudou")
    else:
        save_json(path, record)


def component_maps(year: int) -> np.ndarray:
    """Cinco componentes exatamente na representação usada pelo corretor S12."""
    folder = ROOT / "data/processed/round9"
    pieces = [np.load(folder / f"{year}_{name}.npy", mmap_mode="r")
              for name in NAMES[:4]]
    s09 = np.load(ROOT / f"data/processed/round10/{year}_s09.npy", mmap_mode="r")
    tropical = np.load(ROOT / f"data/processed/round11/{year}_fine32.npy",
                       mmap_mode="r")
    from .round11 import blend
    extension = blend(s09, tropical, 1.)
    return np.stack([*pieces, extension]).reshape(5, 24, GRID)


class Buckets:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, np.ndarray]] = {}

    def add(self, name: str, codes: np.ndarray | int, size: int,
            err: np.ndarray, observed: np.ndarray, predicted: np.ndarray) -> None:
        row = self.rows.setdefault(name, {
            key: np.zeros(size, np.float64)
            for key in ("count", "sse", "error_sum", "observed_sum", "predicted_sum")
        })
        if np.isscalar(codes):
            code = int(codes)
            row["count"][code] += err.size
            row["sse"][code] += np.dot(err, err)
            row["error_sum"][code] += err.sum()
            row["observed_sum"][code] += observed.sum()
            row["predicted_sum"][code] += predicted.sum()
        else:
            code = np.asarray(codes, dtype=np.intp)
            row["count"] += np.bincount(code, minlength=size)
            row["sse"] += np.bincount(code, weights=err * err, minlength=size)
            row["error_sum"] += np.bincount(code, weights=err, minlength=size)
            row["observed_sum"] += np.bincount(code, weights=observed, minlength=size)
            row["predicted_sum"] += np.bincount(code, weights=predicted, minlength=size)

    def describe(self, labels: dict[str, list[str]]) -> dict:
        total_sse = self.rows["global"]["sse"].sum()
        result = {}
        for family, values in self.rows.items():
            count = values["count"]
            result[family] = [
                {
                    "group": label,
                    "count": int(count[i]),
                    "rmse": float(np.sqrt(values["sse"][i] / count[i])) if count[i] else None,
                    "bias_prediction_minus_observed": float(values["error_sum"][i] / count[i]) if count[i] else None,
                    "sse_fraction": float(values["sse"][i] / total_sse),
                    "count_fraction": float(count[i] / self.rows["global"]["count"].sum()),
                }
                for i, label in enumerate(labels[family])
            ]
        return result


def diagnostic() -> None:
    locked()
    labels = {
        "global": ["2009-2020"],
        "latitude": ["-60:-30", "-30:-15", "-15:0", "0:15"],
        "region": [f"lat{a}:{a+15},lon{b}:{min(b+10,-25)}"
                   for a in range(-60, 15, 15) for b in range(-90, -25, 10)],
        "year": [str(y) for y in range(2009, 2021)],
        "month": [str(m) for m in range(1, 13)],
        "season": ["DJF", "MAM", "JJA", "SON"],
        "observed": ["0:.5", ".5:2", "2:5", "5:10", "10:20", "20:inf"],
        "predicted": ["0:.5", ".5:2", "2:5", "5:10", "10:20", "20:inf"],
        "abs_observed_anomaly": ["0:.5", ".5:1", "1:2", "2:4", "4:inf"],
        "climatology": ["0:.5", ".5:2", "2:5", "5:10", "10:20", "20:inf"],
        "member_dispersion": ["0:.25", ".25:.5", ".5:1", "1:2", "2:inf"],
        "continental_pc1": ["lt-1", "-1:0", "0:1", "ge1"],
        "continental_pc2": ["lt-1", "-1:0", "0:1", "ge1"],
        "regime": [f"cluster_{k}" for k in range(4)],
        "regime_change": ["same", "changed"],
        "member_error_sign": ["all_under", "mixed", "all_over"],
    }
    buckets = Buckets()
    tp = np.load(CACHE / "tp.npy", mmap_mode="r").reshape(-1, GRID)
    lat_codes = np.digitize(LAT, [-30, -15, 0]).astype(np.int8)
    region_codes = np.minimum(((LAT + 60) // 15).astype(np.intp), 4) * 7 + \
                   np.minimum(((LON + 90) // 10).astype(np.intp), 6)
    moments = {area: {"count": 0, "s12_sum": 0., "s12_sq": 0.,
                      "member_sum": np.zeros(5), "member_sq": np.zeros(5),
                      "cross": np.zeros(5)}
               for area in ("global", "north")}
    hashes = {}
    for year in YEARS:
        f = Features(year)
        train, valid = round20.context(f)
        cluster = KMeans(n_clusters=4, random_state=20260917, n_init=20).fit(train[:, :8])
        order = np.argsort(cluster.cluster_centers_[:, 0])
        rank = np.empty(4, np.intp)
        rank[order] = np.arange(4)
        assignments = rank[cluster.predict(valid[:, :8])]
        first = int(target_origins(year)[0])
        raw = np.load(ROOT / "data/processed/round3/coarse_weather.npy", mmap_mode="r")
        trans = joblib.load(round20.transform_paths(year)[0])
        previous = round20.global_features(raw, trans, [first - 1])[0, :8]
        prior_cluster = int(rank[cluster.predict(previous.reshape(1, -1))[0]])
        components = component_maps(year)
        ref = round20.reference(year).reshape(24, GRID)
        hashes[str(year)] = digest(round20.ART / f"{year}_s12.npy")
        target_idx = target_origins(year) + 1
        for i in range(24):
            observed = np.asarray(tp[target_idx[i]], dtype=np.float64)
            predicted = np.asarray(ref[i], dtype=np.float64)
            err = predicted - observed
            climo = np.asarray(f.climo[target_idx[i] % 12], dtype=np.float64)
            member = np.asarray(components[:, i], dtype=np.float64)
            errors = member - observed
            dispersion = member.std(axis=0)
            same_sign = np.where(np.all(errors < 0, axis=0), 0,
                                 np.where(np.all(errors > 0, axis=0), 2, 1))
            month = int(target_idx[i] % 12) + 1
            year_target = year + i // 12
            for name, codes, size in (
                ("global", 0, 1),
                ("latitude", lat_codes, 4),
                ("region", region_codes, 35),
                ("year", year_target - 2009, 12),
                ("month", month - 1, 12),
                ("season", ((month % 12) // 3), 4),
                ("observed", np.digitize(observed, [.5, 2, 5, 10, 20]), 6),
                ("predicted", np.digitize(predicted, [.5, 2, 5, 10, 20]), 6),
                ("abs_observed_anomaly", np.digitize(np.abs(observed-climo), [.5, 1, 2, 4]), 5),
                ("climatology", np.digitize(climo, [.5, 2, 5, 10, 20]), 6),
                ("member_dispersion", np.digitize(dispersion, [.25, .5, 1, 2]), 5),
                ("continental_pc1", int(np.digitize(valid[i, 0], [-1, 0, 1])), 4),
                ("continental_pc2", int(np.digitize(valid[i, 1], [-1, 0, 1])), 4),
                ("regime", int(assignments[i]), 4),
                ("regime_change", int(assignments[i] != prior_cluster), 2),
                ("member_error_sign", same_sign, 3),
            ):
                buckets.add(name, codes, size, err, observed, predicted)
            prior_cluster = int(assignments[i])
            for area, mask in (("global", slice(None)), ("north", LAT >= 0)):
                e = err[mask]
                em = errors[:, mask]
                row = moments[area]
                row["count"] += e.size
                row["s12_sum"] += e.sum()
                row["s12_sq"] += np.dot(e, e)
                row["member_sum"] += em.sum(axis=1)
                row["member_sq"] += np.einsum("ij,ij->i", em, em)
                row["cross"] += em @ e
        print("DIAGNOSTICO", year, flush=True)
        del f, train, valid, components, ref
        gc.collect()
    result = buckets.describe(labels)
    member_stats = {}
    for area, row in moments.items():
        n = row["count"]
        mu0, var0 = row["s12_sum"]/n, row["s12_sq"]/n-(row["s12_sum"]/n)**2
        mu = row["member_sum"]/n
        var = row["member_sq"]/n-mu*mu
        centered = row["cross"]/n-mu0*mu
        member_stats[area] = [
            {"member": name, "rmse": float(np.sqrt(row["member_sq"][j]/n)),
             "bias": float(mu[j]), "error_cross_product_with_s12": float(row["cross"][j]/n),
             "error_correlation_with_s12": float(centered[j]/np.sqrt(var0*var[j]))}
            for j, name in enumerate(NAMES)
        ]
    output = {
        "reference": "S12", "development_only": True, "reused_periods": True,
        "no_test_targets": True, "reference_prediction_hashes": hashes,
        "groups": result, "members": member_stats,
    }
    save_json(OUT / "diagnostic.json", output)
    _write_diagnostic_summary(output)


def _write_diagnostic_summary(output: dict) -> None:
    groups = output["groups"]
    lines = [
        "# Rodada 25 — diagnóstico da S12",
        "",
        "Previsões causais 2009–2020; períodos reutilizados. Viés = previsão − observado.",
        "",
    ]
    for family in ("latitude", "year", "season", "observed", "predicted",
                   "abs_observed_anomaly", "climatology", "member_dispersion",
                   "continental_pc1", "continental_pc2", "regime",
                   "regime_change", "member_error_sign"):
        lines.extend([f"## {family}", "", "| Grupo | RMSE | Viés | SSE % | Pontos % |",
                      "| --- | ---: | ---: | ---: | ---: |"])
        for row in groups[family]:
            if row["count"]:
                lines.append(f"| {row['group']} | {row['rmse']:.4f} | "
                             f"{row['bias_prediction_minus_observed']:.4f} | "
                             f"{100*row['sse_fraction']:.2f} | "
                             f"{100*row['count_fraction']:.2f} |")
        lines.append("")
    for area, rows in output["members"].items():
        lines.extend([f"## Componentes — {area}", "",
                      "| Componente | RMSE | Viés | E[e_comp e_S12] | Corr(e_comp,e_S12) |",
                      "| --- | ---: | ---: | ---: | ---: |"])
        for row in rows:
            lines.append(f"| {row['member']} | {row['rmse']:.4f} | "
                         f"{row['bias']:.4f} | {row['error_cross_product_with_s12']:.4f} | "
                         f"{row['error_correlation_with_s12']:.4f} |")
        lines.append("")
    lines.append("Grupos por observado são descritivos, indisponíveis na inferência. "
                 "Clusters foram ajustados somente no passado de cada bloco.")
    (OUT / "DIAGNOSTIC.md").write_text("\n".join(lines)+"\n", encoding="utf-8")


def _global_lag1(f: Features) -> tuple[np.ndarray, np.ndarray]:
    train, valid = [], []
    arrays = [
        np.load(ROOT / "data/processed/round3/coarse_weather.npy", mmap_mode="r"),
        np.load(ROOT / "data/processed/round11/fine_weather.npy", mmap_mode="r"),
    ]
    for raw, path in zip(arrays, round20.transform_paths(f.year)):
        model = joblib.load(path)
        train.append(round20.global_features(raw, model, f.idx-1)[:, :16])
        valid.append(round20.global_features(raw, model, target_origins(f.year)-1)[:, :16])
    return np.column_stack(train), np.column_stack(valid)


def _save_prediction(path: Path, value: np.ndarray, metadata: dict) -> None:
    if path.exists():
        expected = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        if digest(path) != expected["sha256"]:
            raise ValueError(f"Predição alterada: {path}")
        return
    np.save(path, value)
    save_json(path.with_suffix(".json"), {"sha256": digest(path), **metadata})


def _prediction_rows(name: str, prediction: np.ndarray, reference: np.ndarray,
                     truth: np.ndarray) -> tuple[dict, list[dict]]:
    direct = {"model": name, **round20.old.metrics(prediction, truth, reference)}
    blends = []
    for a in WEIGHTS:
        mixed = reference + a * (prediction - reference)
        blends.append({"model": f"{name}_a{a:g}",
                       **round20.old.metrics(mixed, truth, reference)})
    return direct, blends


def _diversity(prediction: np.ndarray, reference: np.ndarray, truth: np.ndarray,
               year: int) -> list[dict]:
    en = (truth - prediction).astype(np.float64)
    es = (truth - reference).astype(np.float64)
    areas = {"global": np.ones(301, bool), "north": np.arange(301) >= 240,
             "south": np.arange(301) < 240}
    months = (target_origins(year)+1) % 12 + 1
    seasons = (months % 12) // 3
    rows = []
    for area, latmask in areas.items():
        for season in (-1, 0, 1, 2, 3):
            tmask = np.ones(24, bool) if season == -1 else seasons == season
            a = en[tmask][:, latmask].ravel()
            b = es[tmask][:, latmask].ravel()
            var_a, var_b = a.var(), b.var()
            cross = np.mean(a*b)
            rows.append({
                "area": area, "season": "all" if season == -1 else ("DJF", "MAM", "JJA", "SON")[season],
                "count": len(a),
                "new_rmse": float(np.sqrt(np.mean(a*a))),
                "s12_rmse": float(np.sqrt(np.mean(b*b))),
                "error_cross_product": float(cross),
                "error_covariance": float(cross-a.mean()*b.mean()),
                "error_correlation": float((cross-a.mean()*b.mean())/np.sqrt(var_a*var_b))
                if var_a > 0 and var_b > 0 else None,
            })
    return rows


def evaluate_h2() -> None:
    locked()
    for year in YEARS:
        out = OUT / f"{year}_h2.json"
        if out.exists():
            print("H2 EXISTENTE", year, flush=True)
            continue
        f = Features(year)
        global_train, global_valid = round20.context(f)
        lag_train, lag_valid = _global_lag1(f)
        sample_count = 1536
        x = np.empty((len(f.idx), sample_count, 151), np.float32)
        y = np.empty((len(f.idx), sample_count), np.float32)
        for k, (origin, cells) in enumerate(zip(f.idx, round20.nested_cells(f.idx))):
            local = f.matrix(origin, cells, context=True)
            x[k, :, :55] = local
            x[k, :, 55:119] = global_train[k]
            x[k, :, 119:] = lag_train[k]
            y[k] = f.tp[origin+1, cells] - local[:, 4]
        model = HistGradientBoostingRegressor(
            max_leaf_nodes=31, min_samples_leaf=200, l2_regularization=20.,
            **round20.TREE
        ).fit(np.ascontiguousarray(x.reshape(-1, 151)), y.reshape(-1))
        joblib.dump(model, ART / f"{year}_h2.joblib")
        model_hash = digest(ART / f"{year}_h2.joblib")
        del x, y
        gc.collect()
        pred = np.empty((24, 301, 261), np.float32)
        cells = np.arange(GRID)
        for k, origin in enumerate(target_origins(year)):
            local = f.matrix(origin, cells, context=True)
            all_x = np.column_stack([
                local,
                np.broadcast_to(global_valid[k], (GRID, 64)),
                np.broadcast_to(lag_valid[k], (GRID, 32)),
            ])
            pred[k] = np.maximum(local[:, 4] + model.predict(all_x), 0).reshape(301, 261)
            print("H2 MES", year, k+1, flush=True)
        _save_prediction(ART / f"{year}_h2_prediction.npy", pred,
                         {"cutoff": year, "model_sha256": model_hash,
                          "last_training_target": f"{year-1}-12", "official_only": True})
        ref = round20.reference(year)
        control = np.load(round20.ART / f"{year}_global31_dense_prediction.npy", mmap_mode="r")
        truth = np.asarray(f.tp[target_origins(year)+1]).reshape(24, 301, 261)
        direct, blends = _prediction_rows("h2", pred, ref, truth)
        control_row = {"model": "global31_dense",
                       **round20.old.metrics(control, truth, ref)}
        save_json(out, {"cutoff": year, "reference": {"model": "s12",
                  **round20.old.metrics(ref, truth, ref)},
                  "control": control_row, "direct": direct, "blends": blends,
                  "diversity": _diversity(pred, ref, truth, year),
                  "model_sha256": model_hash, "official_only": True})
        print("H2 BLOCO", year, direct["rmse"], control_row["rmse"], flush=True)
        del f, model, pred, ref, truth, global_train, global_valid, lag_train, lag_valid
        gc.collect()


def _analog_coordinates(values: np.ndarray) -> np.ndarray:
    return np.column_stack([values[:, :4], values[:, 16:20],
                            values[:, 32:36], values[:, 48:52]])


def evaluate_h4() -> None:
    locked()
    for year in YEARS:
        out = OUT / f"{year}_h4.json"
        if out.exists():
            print("H4 EXISTENTE", year, flush=True)
            continue
        f = Features(year)
        global_train, global_valid = round20.context(f)
        train = _analog_coordinates(global_train).astype(np.float64)
        valid = _analog_coordinates(global_valid).astype(np.float64)
        archive_month = (f.idx+1) % 12
        origins = target_origins(year)
        pred = np.empty((24, GRID), np.float32)
        candidates, distances, analog_years = [], [], []
        for k, origin in enumerate(origins):
            target_month = (origin+1) % 12
            seasonal_distance = np.minimum((archive_month-target_month) % 12,
                                           (target_month-archive_month) % 12)
            eligible = np.flatnonzero(seasonal_distance <= 1)
            if len(eligible) < 10:
                raise ValueError("Menos de dez análogos sazonais")
            distance = np.linalg.norm(train[eligible]-valid[k], axis=1)
            order = np.argsort(distance, kind="stable")[:10]
            selected = eligible[order]
            idx = f.idx[selected]+1
            observed = np.asarray(f.tp[idx], dtype=np.float64)
            anomaly = observed - np.asarray(f.climo[idx % 12], dtype=np.float64)
            result = np.maximum(f.climo[target_month] + anomaly.mean(axis=0), 0)
            pred[k] = result.astype(np.float32)
            candidates.append(int(len(eligible)))
            distances.append([float(v) for v in distance[order]])
            analog_years.append([int(1940+j//12) for j in idx])
        pred = pred.reshape(24, 301, 261)
        _save_prediction(ART / f"{year}_h4_prediction.npy", pred,
                         {"cutoff": year, "last_training_target": f"{year-1}-12",
                          "official_only": True})
        ref = round20.reference(year)
        truth = np.asarray(f.tp[origins+1]).reshape(24, 301, 261)
        climo = np.maximum(f.climo[(origins+1) % 12], 0).reshape(24, 301, 261)
        direct, blends = _prediction_rows("h4", pred, ref, truth)
        save_json(out, {
            "cutoff": year, "reference": {"model": "s12", **round20.old.metrics(ref, truth, ref)},
            "climatology": {"model": "climatology",
                            **round20.old.metrics(climo, truth, ref)},
            "direct": direct, "blends": blends,
            "candidate_count_by_month": candidates,
            "selected_distances_by_month": distances,
            "selected_analog_years_by_month": analog_years,
            "diversity": _diversity(pred, ref, truth, year),
            "official_only": True,
        })
        print("H4 BLOCO", year, direct["rmse"], flush=True)
        del f, pred, ref, truth, global_train, global_valid, train, valid
        gc.collect()


def selection() -> None:
    locked()
    records = {}
    for year in YEARS:
        records[(year, "h2")] = json.loads((OUT / f"{year}_h2.json").read_text(encoding="utf-8"))
        records[(year, "h4")] = json.loads((OUT / f"{year}_h4.json").read_text(encoding="utf-8"))
    reference_months = np.array([records[(y, "h2")]["reference"]["monthly_rmse"]
                                 for y in YEARS])
    reference = float(np.sqrt(np.mean(reference_months**2)))
    if abs(reference-1.7707754911700633) > 1e-9:
        raise ValueError("Referência S12 divergente")
    ref_second = float(np.sqrt(np.mean(reference_months[:, 12:]**2)))
    ref_years = np.sqrt(np.mean(reference_months.reshape(-1, 12)**2, axis=1))
    ranking = []
    for family in ("h2", "h4"):
        for a in WEIGHTS:
            name = f"{family}_a{a:g}"
            rows = [next(r for r in records[(year, family)]["blends"]
                         if r["model"] == name) for year in YEARS]
            months = np.array([r["monthly_rmse"] for r in rows])
            annual = np.sqrt(np.mean(months.reshape(-1, 12)**2, axis=1))
            rmse = float(np.sqrt(np.mean(months**2)))
            second = float(np.sqrt(np.mean(months[:, 12:]**2)))
            blocks = int(np.sum(np.mean(months**2, axis=1) <
                                np.mean(reference_months**2, axis=1)))
            years = int(np.sum(annual < ref_years))
            nmonths = int(np.sum(months < reference_months))
            worst = float(np.max(annual/ref_years-1))
            ranking.append({
                "model": name, "rmse": rmse, "relative_gain": 1-rmse/reference,
                "second_year_rmse": second, "blocks_improved": blocks,
                "years_improved": years, "months_improved": nmonths,
                "worst_annual_relative_change": worst,
                "passed": passes_gate(rmse, reference, second, ref_second,
                                      blocks, years, nmonths, 144, worst),
            })
    ranking.sort(key=lambda x: x["rmse"])
    eligible = [x for x in ranking if x["passed"]]
    summary = {
        "reference": "S12", "reference_rmse": reference,
        "minimum_relative_gain": .003,
        "ranking": ranking,
        "selected": eligible[0]["model"] if eligible else None,
        "h2_direct_by_block": [
            {"year": y, "control_rmse": records[(y, "h2")]["control"]["rmse"],
             "new_rmse": records[(y, "h2")]["direct"]["rmse"]}
            for y in YEARS],
        "h4_direct_by_block": [
            {"year": y, "climatology_rmse": records[(y, "h4")]["climatology"]["rmse"],
             "new_rmse": records[(y, "h4")]["direct"]["rmse"]}
            for y in YEARS],
        "confirmation_run": False, "csv_exported": False, "uploaded": False,
        "development_periods_reused": True,
    }
    path = OUT / "selection.json"
    if path.exists() and json.loads(path.read_text(encoding="utf-8")) != summary:
        raise ValueError("Seleção já registrada diverge")
    save_json(path, summary)
    _write_results(summary, records)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


def _write_results(summary: dict, records: dict) -> None:
    lines = [
        "# Rodada 25 — diagnóstico, PCs com ordem e análogos",
        "",
        f"S12 histórica: {summary['reference_rmse']:.9f}. Seis blocos 2009–2020 reutilizados.",
        "",
        "| Candidata | RMSE | Ganho relativo | Blocos | Anos | Meses | Gate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for r in summary["ranking"]:
        lines.append(f"| {r['model']} | {r['rmse']:.9f} | "
                     f"{100*r['relative_gain']:.4f}% | "
                     f"{r['blocks_improved']}/6 | {r['years_improved']}/12 | "
                     f"{r['months_improved']}/144 | {r['passed']} |")
    lines.extend(["", f"Selecionada: {summary['selected'] or 'nenhuma'}.",
                  "", "## Modelos puros por bloco", "",
                  "| Bloco | H2 controle | H2 lag1 | Climatologia | H4 análogos |",
                  "| --- | ---: | ---: | ---: | ---: |"])
    for year in YEARS:
        h2, h4 = records[(year, "h2")], records[(year, "h4")]
        lines.append(f"| {year}–{year+1} | {h2['control']['rmse']:.6f} | "
                     f"{h2['direct']['rmse']:.6f} | "
                     f"{h4['climatology']['rmse']:.6f} | "
                     f"{h4['direct']['rmse']:.6f} |")
    lines.extend(["", "O diagnóstico completo está em DIAGNOSTIC.md e diagnostic.json.",
                  "Produtos cruzados e correlações de erros por bloco/região/estação "
                  "constam nos JSON de cada bloco.",
                  "Nenhum alvo de 2023–2024 foi lido. Nenhum CSV ou upload foi gerado."])
    (OUT / "RESULTS.md").write_text("\n".join(lines)+"\n", encoding="utf-8")


def selfcheck() -> None:
    if len(LAT) != GRID or len(LON) != GRID:
        raise AssertionError("Grade incorreta")
    if not np.array_equal(np.unique(np.minimum(((LAT+60)//15).astype(int), 4)),
                          np.arange(5)):
        raise AssertionError("Faixas regionais incorretas")
    dummy = np.arange(64, dtype=float).reshape(4, 16)
    if _analog_coordinates(np.tile(dummy, (1, 4))).shape != (4, 16):
        raise AssertionError("Coordenadas de análogos incorretas")
    f = Features(2009)
    if f.idx.max()+1 >= target_origins(2009)[0]+1:
        raise AssertionError("Alvo de treino entra na validação")
    print("SELF CHECK PASS", flush=True)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("selfcheck", "diagnostic",
                                          "evaluate_h2", "evaluate_h4", "selection"))
    globals()[parser.parse_args().stage]()
