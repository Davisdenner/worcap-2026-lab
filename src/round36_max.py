"""Rodada 36: tentativa máxima — persistência estendida, capacidade e histórico.

Combina três alavancas de uma vez, abandonando deliberadamente a disciplina
de uma variável por vez das Rodadas 1 a 35. Ver experiments/ROUND36.md.

Oito colunas de persistência (as cinco da Rodada 35 mais 15x15, média de seis
meses e o mesmo mês do ano anterior), 255 folhas em vez de 31, e dois braços
de histórico: 1981 e 1940. Tudo o mais herdado da Rodada 33 sem alteração,
inclusive o sorteio de células.

A S12 não é modificada. Escopo OOF, dado exclusivamente oficial, sem
submissão.

Roda em CPU, local. O braço de 1940 monta cerca de 4 GB de atributos; se a
memória não comportar, o braço de 1981 roda primeiro e fica salvo.
`evaluate()` retoma bloco a bloco.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import uniform_filter
from sklearn.ensemble import HistGradientBoostingRegressor

from .competition import CACHE, ROOT, REPORT, dates, save_json, training_pairs
from .round2 import Features, target_origins
from . import round20, round27, round33_scale

OUT = REPORT / "round36"
ART = ROOT / "data/processed/round36"
PROTOCOL = ROOT / "experiments/ROUND36.md"

YEARS = round27.YEARS
EVAL = round27.EVAL
SHAPE = round33_scale.SHAPE
GRID = SHAPE[0] * SHAPE[1]
LOCAL = round33_scale.LOCAL                     # 55
GLOBAL = round33_scale.GLOBAL                   # 64
BASE_FEATURES = LOCAL + GLOBAL                  # 119
PERSIST = ("anom_o", "anom_media3", "anom_suave3x3", "anom_suave9x9",
           "tendencia", "anom_suave15x15", "anom_media6", "anom_ano_anterior")
FEATURES = BASE_FEATURES + len(PERSIST)         # 127
MIN_ORIGIN = 11                                 # anom_ano_anterior lê o-11

CELLS = 8192
LEAVES = 255
SEED = round33_scale.SEED
FRACTIONS = round33_scale.FRACTIONS             # (.10, .25)
STARTS = ("1981-01-01", "1940-01-01")           # o mais leve primeiro
TARGET_DIRECT_RMSE = 1.765


def _tree() -> dict:
    _, _, _, minimum, l2 = round20.MODELS[round33_scale.BASE_MODEL]
    return dict(max_leaf_nodes=LEAVES, min_samples_leaf=minimum,
                l2_regularization=l2, **round20.TREE)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def locked() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    record = {
        "protocol_sha256": sha(PROTOCOL), "reference": "S12",
        "combines_three_levers": True, "attribution_sacrificed": True,
        "persistence": list(PERSIST), "features": FEATURES,
        "cells": CELLS, "leaves": LEAVES, "starts": list(STARTS),
        "min_origin": MIN_ORIGIN, "seed": SEED, "tree": _tree(),
        "fractions": [float(a) for a in FRACTIONS],
        "target_direct_rmse": TARGET_DIRECT_RMSE,
        "years": list(YEARS), "eval_years": list(EVAL),
        "external_data_used": False, "s12_unmodified": True, "oof_only": True,
        "minimum_gain": 0.003, "no_test_targets": True, "no_submission": True,
    }
    path = OUT / "protocol.json"
    if not path.exists():
        save_json(path, record)
        return
    stored = json.loads(path.read_text(encoding="utf-8"))
    current = json.loads(json.dumps(record))
    if stored == current:
        return
    diff = [f"  {k}: {stored.get(k, '<ausente>')!r} -> {current.get(k, '<ausente>')!r}"
            for k in sorted(set(stored) | set(current)) if stored.get(k) != current.get(k)]
    raise ValueError(
        "Protocolo ou configuração da rodada 36 mudou depois de congelado:\n"
        + "\n".join(diff)
        + f"\n\nSe a mudança foi deliberada, apague {path} e os artefatos de {ART}.")


def tag(start: str) -> str:
    return f"s{start[:4]}"


def train_origins(year: int, start: str) -> np.ndarray:
    idx = training_pairs(dates(), f"{year}-01-01", start)
    return idx[idx >= MIN_ORIGIN]


def persistence_rows(f: Features, origin: int, cells: np.ndarray) -> np.ndarray:
    """As oito colunas de persistência. Lê apenas índices <= origin."""
    def anomaly(k: int) -> np.ndarray:
        return (np.asarray(f.tp[origin - k], np.float64)
                - np.asarray(f.climo[(origin - k) % 12], np.float64)).reshape(SHAPE)

    a = [anomaly(k) for k in range(6)]
    prev_year = anomaly(11)
    out = np.empty((len(cells), len(PERSIST)), np.float32)
    out[:, 0] = a[0].reshape(-1)[cells]
    out[:, 1] = ((a[0] + a[1] + a[2]) / 3.0).reshape(-1)[cells]
    out[:, 2] = uniform_filter(a[0], size=3, mode="nearest").reshape(-1)[cells]
    out[:, 3] = uniform_filter(a[0], size=9, mode="nearest").reshape(-1)[cells]
    out[:, 4] = (a[0] - a[1]).reshape(-1)[cells]
    out[:, 5] = uniform_filter(a[0], size=15, mode="nearest").reshape(-1)[cells]
    out[:, 6] = (sum(a) / 6.0).reshape(-1)[cells]
    out[:, 7] = prev_year.reshape(-1)[cells]
    return out


def global_rows(f: Features, origins: np.ndarray) -> np.ndarray:
    """Os 64 atributos globais para origens fora de `f.idx` (braço de 1940).

    `round20.context` cobre apenas `f.idx` e o bloco de validação, e faz
    asserções estritas contra o modelo salvo. Para o braço de 1981 usamos a
    `context` original, sem tocar em nada. Só o braço de 1940 precisa deste
    caminho, que reaproveita `round20.global_features` — função pura do
    cache, do modelo e das origens — com o mesmo transform congelado.
    """
    import joblib
    files = round20.transform_paths(f.year)
    arrays = [np.load(ROOT / "data/processed/round3/coarse_weather.npy", mmap_mode="r"),
              np.load(ROOT / "data/processed/round11/fine_weather.npy", mmap_mode="r")]
    models = [joblib.load(p) for p in files]
    # `round20.context` valida só o primeiro transform (round9 pls16); o
    # segundo (round11 fine_weather) não carrega essas chaves. Espelhamos a
    # checagem original em vez de inventar uma mais estrita.
    if (models[0]["training_cutoff"] != f"{f.year}-01"
            or not models[0]["official_only"]):
        raise ValueError("PCA continental de outro corte")
    return np.column_stack([round20.global_features(raw, model, origins)
                            for raw, model in zip(arrays, models)])


def build(f: Features, origins: np.ndarray, gfeat: np.ndarray):
    rng = np.random.default_rng(SEED)
    n = origins.size
    x = np.empty((n, CELLS, FEATURES), np.float32)
    y = np.empty((n, CELLS), np.float32)
    started = time.monotonic()
    for k, origin in enumerate(origins):
        cells = rng.choice(GRID, CELLS, replace=False)
        local = f.matrix(int(origin), cells, context=True)
        x[k, :, :LOCAL] = local
        x[k, :, LOCAL:BASE_FEATURES] = gfeat[k]
        x[k, :, BASE_FEATURES:] = persistence_rows(f, int(origin), cells)
        y[k] = f.tp[int(origin) + 1, cells] - local[:, 4]
        if (k + 1) % 100 == 0 or k + 1 == n:
            print(f"  montadas {k + 1}/{n} origens "
                  f"({time.monotonic() - started:.0f}s)", flush=True)
    return x, y


def predict_block(model, f: Features, gvalid: np.ndarray) -> np.ndarray:
    origins = target_origins(f.year)
    gfeat = gvalid
    cells = np.arange(GRID)
    out = np.empty((24, GRID), np.float32)
    for k, origin in enumerate(origins):
        local = f.matrix(int(origin), cells, context=True)
        rows = np.column_stack([local,
                                np.broadcast_to(gfeat[k], (GRID, GLOBAL)),
                                persistence_rows(f, int(origin), cells)])
        out[k] = np.maximum(local[:, 4] + model.predict(rows), 0.0)
    return out.reshape(24, *SHAPE)


def evaluate() -> None:
    locked()
    tree = _tree()
    # Braço leve primeiro, inteiro: se o de 1940 estourar memória, o de 1981
    # já está completo e avaliável.
    for start in STARTS:
        for year in YEARS:
            name = tag(start)
            path = ART / f"{year}_{name}.npy"
            if path.exists():
                print(f"EXISTENTE {year} {name}", flush=True)
                continue
            print(f"INICIANDO {year} {name}", flush=True)
            f = Features(year)
            origins = train_origins(year, start)
            gtrain, gvalid = round20.context(f)
            if origins.size != f.idx.size or not np.array_equal(origins, f.idx):
                # Braço de 1940: mais origens que `f.idx`, transform congelado.
                gtrain = global_rows(f, origins)
            x, y = build(f, origins, gtrain)
            xs = x.reshape(-1, FEATURES)
            ys = y.reshape(-1)
            started = time.monotonic()
            print(f"  {xs.shape[0]} linhas x {FEATURES} atributos, "
                  f"{LEAVES} folhas", flush=True)
            model = HistGradientBoostingRegressor(**tree).fit(xs, ys)
            seconds = time.monotonic() - started
            print(f"  ajuste em {seconds:.0f}s", flush=True)
            del x, y, xs, ys
            prediction = predict_block(model, f, gvalid)
            np.save(path, prediction)
            save_json(ART / f"{year}_{name}.json", {
                "start": start, "features": FEATURES, "leaves": LEAVES,
                "cells": CELLS, "train_origins": int(origins.size),
                "train_rows": int(origins.size * CELLS),
                "fit_seconds": seconds, "external_data_used": False})
            print(f"CONCLUIDO {year} {name}", flush=True)
            del f, model, prediction, gtrain, gvalid


def decision() -> dict:
    tp = np.load(CACHE / "tp.npy", mmap_mode="r")
    sources = {"r33_119": lambda yr: round33_scale.ART / f"{yr}_c{CELLS}.npy",
               "r35_124": lambda yr: ROOT / f"data/processed/round35/{yr}_persist.npy"}
    for start in STARTS:
        sources[f"r36_{tag(start)}"] = (
            lambda yr, s=start: ART / f"{yr}_{tag(s)}.npy")

    monthly: dict[str, list[float]] = {}
    for year in EVAL:
        truth = np.asarray(tp[target_origins(year) + 1], np.float64).reshape(24, -1)
        s12 = np.maximum(np.asarray(round20.reference(year), np.float64).reshape(24, -1), 0.0)
        monthly.setdefault("s12", []).extend(np.mean((s12 - truth) ** 2, axis=1).tolist())
        for name, locate in sources.items():
            path = locate(year)
            if not path.exists():
                continue
            candidate = np.asarray(np.load(path), np.float64).reshape(24, -1)
            monthly.setdefault(f"{name}_direto", []).extend(
                np.mean((candidate - truth) ** 2, axis=1).tolist())
            for fraction in FRACTIONS:
                predicted = np.maximum(s12 + fraction * (candidate - s12), 0.0)
                monthly.setdefault(f"{name}_a{fraction:g}", []).extend(
                    np.mean((predicted - truth) ** 2, axis=1).tolist())

    base = np.asarray(monthly["s12"])
    rows = {}
    for key, values in monthly.items():
        v = np.asarray(values)
        if v.size != base.size:
            continue
        rows[key] = {
            "rmse": float(np.sqrt(v.mean())),
            "gain_vs_s12_percent": 100.0 * (1.0 - np.sqrt(v.mean() / base.mean())),
            "positive_blocks": int(np.sum(v.reshape(-1, 24).mean(axis=1)
                                          < base.reshape(-1, 24).mean(axis=1))),
            "positive_years": int(np.sum(v.reshape(-1, 12).mean(axis=1)
                                         < base.reshape(-1, 12).mean(axis=1))),
            "positive_months": int(np.sum(v < base))}

    candidates = [k for k in rows if k.startswith("r36_") and not k.endswith("_direto")]
    stable = [k for k in candidates
              if rows[k]["gain_vs_s12_percent"] >= 0.3 and rows[k]["positive_blocks"] >= 4
              and rows[k]["positive_years"] >= 7 and rows[k]["positive_months"] >= 67]
    if stable:
        cls, why = "A", "Alguma fracao atinge amplitude e estabilidade exigidas."
    elif candidates and all(rows[k]["gain_vs_s12_percent"] <= 0 for k in candidates):
        cls, why = "B", "Toda fracao piora a S12."
    else:
        cls, why = "D", "Ha ganho, mas sem amplitude (0,3%) e estabilidade simultaneas."

    print("\n=== Trajetoria do corretor direto rumo ao alvo de 1.765 ===")
    print(f'{"configuracao":<16}{"RMSE direto":>14}{"vs alvo":>12}{"vs S12":>10}')
    for name in ("r33_119", "r35_124", *[f"r36_{tag(s)}" for s in STARTS]):
        key = f"{name}_direto"
        if key in rows:
            value = rows[key]["rmse"]
            print(f'{name:<16}{value:>14.6f}{value - TARGET_DIRECT_RMSE:>+12.6f}'
                  f'{rows[key]["gain_vs_s12_percent"]:>9.3f}%')

    result = {"classification": cls, "reason": why,
              "baseline_rmse": float(np.sqrt(base.mean())),
              "target_direct_rmse": TARGET_DIRECT_RMSE,
              "variants": dict(sorted(rows.items(), key=lambda kv: kv[1]["rmse"])),
              "stable_variants": stable, "evaluation_blocks": list(EVAL),
              "external_data_used": False, "s12_unmodified": True,
              "no_candidate": not stable, "no_test_targets": True,
              "no_submission": True}
    OUT.mkdir(parents=True, exist_ok=True)
    save_json(OUT / "decision.json", result)
    print("\nDECISAO", cls, why, flush=True)
    print(f'{"variante":<18}{"RMSE":>12}{"ganho":>10}{"blocos":>9}{"anos":>8}{"meses":>10}')
    for key, r in result["variants"].items():
        print(f'{key:<18}{r["rmse"]:>12.6f}{r["gain_vs_s12_percent"]:>9.3f}%'
              f'{str(r["positive_blocks"]) + "/5":>9}'
              f'{str(r["positive_years"]) + "/10":>8}'
              f'{str(r["positive_months"]) + "/120":>10}')
    return result


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("evaluate", "decision"))
    globals()[parser.parse_args().stage]()
