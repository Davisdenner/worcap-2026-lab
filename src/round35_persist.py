"""Rodada 35: persistência de precipitação como atributo do corretor da S12.

Em trinta e quatro rodadas a precipitação apareceu apenas como rótulo:
`round2.Features.matrix` não tem coluna de chuva e `round6.local_memory` usa
as nove variáveis ATMOSFÉRICAS. O organizador esclareceu que dados
disponíveis até o fim de T-1 são válidos para prever T, o que libera a
persistência. Ver experiments/ROUND35.md.

Reproduz `c8192` da Rodada 33 sem alteração — mesmas células, mesma semente,
mesmo sorteio, mesma árvore de 31 folhas — e acrescenta cinco colunas,
passando de 119 para 124 atributos. O braço da Rodada 33 é o controle
pareado.

ESCOPO: validação OOF com dado exclusivamente oficial (`tp.npy` cobre
1940-2022). Não usa dado externo e não produz submissão. Aplicar ao teste
exigiria a chuva observada nas 24 origens e uma verificação de consistência
de produto, que é decisão separada.

Roda em CPU, local, cerca de 25 minutos. `evaluate()` retoma bloco a bloco.
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

from .competition import CACHE, ROOT, REPORT, save_json
from .round2 import Features, target_origins
from . import round20, round27, round33_scale

OUT = REPORT / "round35"
ART = ROOT / "data/processed/round35"
PROTOCOL = ROOT / "experiments/ROUND35.md"

YEARS = round27.YEARS
EVAL = round27.EVAL
SHAPE = round33_scale.SHAPE
GRID = SHAPE[0] * SHAPE[1]
BASE_FEATURES = round33_scale.FEATURES          # 119
PERSIST = ("anom_o", "anom_media3", "anom_suave3x3", "anom_suave9x9", "tendencia")
FEATURES = BASE_FEATURES + len(PERSIST)         # 124

CELLS = 8192
LEAVES = 31
SEED = round33_scale.SEED                       # mesmo sorteio da Rodada 33
FRACTIONS = round33_scale.FRACTIONS             # (.10, .25)
CONTROL_NAME = "c8192_119"


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
        "inherits": "round33_scale c8192 (mesmo sorteio, arvore e alvo)",
        "base_features": BASE_FEATURES, "persistence": list(PERSIST),
        "features": FEATURES, "cells": CELLS, "leaves": LEAVES, "seed": SEED,
        "fractions": [float(a) for a in FRACTIONS], "tree": _tree(),
        "years": list(YEARS), "eval_years": list(EVAL),
        "external_data_used": False, "oof_only": True,
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
        "Protocolo ou configuração da rodada 35 mudou depois de congelado:\n"
        + "\n".join(diff)
        + f"\n\nSe a mudança foi deliberada, apague {path} e os artefatos de {ART}.")


def persistence_rows(f: Features, origin: int, cells: np.ndarray) -> np.ndarray:
    """As cinco colunas de persistência na origem. (len(cells), 5) float32.

    `f.climo` é a climatologia de 60 anos ajustada só com meses anteriores ao
    bloco, portanto causal por construção. Os índices `o`, `o-1` e `o-2` são
    todos anteriores ao alvo `o+1`.
    """
    fields = [np.asarray(f.tp[origin - k], np.float64).reshape(SHAPE)
              - np.asarray(f.climo[(origin - k) % 12], np.float64).reshape(SHAPE)
              for k in range(3)]
    mean3 = (fields[0] + fields[1] + fields[2]) / 3.0
    out = np.empty((len(cells), len(PERSIST)), np.float32)
    out[:, 0] = fields[0].reshape(-1)[cells]
    out[:, 1] = mean3.reshape(-1)[cells]
    out[:, 2] = uniform_filter(fields[0], size=3, mode="nearest").reshape(-1)[cells]
    out[:, 3] = uniform_filter(fields[0], size=9, mode="nearest").reshape(-1)[cells]
    out[:, 4] = (fields[0] - fields[1]).reshape(-1)[cells]
    return out


def build_block(f: Features, global_train: np.ndarray):
    """(n, CELLS, 124) e (n, CELLS). Sorteio idêntico ao da Rodada 33."""
    rng = np.random.default_rng(SEED)
    n = f.idx.size
    x = np.empty((n, CELLS, FEATURES), np.float32)
    y = np.empty((n, CELLS), np.float32)
    started = time.monotonic()
    for k, origin in enumerate(f.idx):
        cells = rng.choice(GRID, CELLS, replace=False)
        local = f.matrix(int(origin), cells, context=True)
        x[k, :, :round33_scale.LOCAL] = local
        x[k, :, round33_scale.LOCAL:BASE_FEATURES] = global_train[k]
        x[k, :, BASE_FEATURES:] = persistence_rows(f, int(origin), cells)
        y[k] = f.tp[int(origin) + 1, cells] - local[:, 4]
        if (k + 1) % 100 == 0 or k + 1 == n:
            print(f"  montadas {k + 1}/{n} origens "
                  f"({time.monotonic() - started:.0f}s)", flush=True)
    return x, y


def predict_block(model, f: Features, global_valid: np.ndarray) -> np.ndarray:
    cells = np.arange(GRID)
    out = np.empty((24, GRID), np.float32)
    for k, origin in enumerate(target_origins(f.year)):
        local = f.matrix(int(origin), cells, context=True)
        rows = np.column_stack([
            local,
            np.broadcast_to(global_valid[k], (GRID, round33_scale.GLOBAL)),
            persistence_rows(f, int(origin), cells)])
        out[k] = np.maximum(local[:, 4] + model.predict(rows), 0.0)
    return out.reshape(24, *SHAPE)


def evaluate() -> None:
    locked()
    tree = _tree()
    for year in YEARS:
        path = ART / f"{year}_persist.npy"
        if path.exists():
            print(f"BLOCO EXISTENTE {year}", flush=True)
            continue
        control = round33_scale.ART / f"{year}_c{CELLS}.npy"
        if not control.exists():
            raise SystemExit(
                f"Falta {control}. Rode a Rodada 33 antes: o braço de 119 "
                "atributos é o controle pareado desta rodada.")
        print(f"INICIANDO BLOCO {year}", flush=True)
        f = Features(year)
        gtrain, gvalid = round20.context(f)
        x, y = build_block(f, gtrain)
        xs = x.reshape(-1, FEATURES)
        ys = y.reshape(-1)
        started = time.monotonic()
        print(f"  {xs.shape[0]} linhas x {FEATURES} atributos", flush=True)
        model = HistGradientBoostingRegressor(**tree).fit(xs, ys)
        seconds = time.monotonic() - started
        print(f"  ajuste em {seconds:.0f}s", flush=True)
        prediction = predict_block(model, f, gvalid)
        np.save(path, prediction)
        save_json(ART / f"{year}_persist.json", {
            "features": FEATURES, "persistence": list(PERSIST), "cells": CELLS,
            "leaves": LEAVES, "train_rows": int(xs.shape[0]),
            "fit_seconds": seconds, "external_data_used": False})
        print(f"BLOCO CONCLUIDO {year}", flush=True)
        del f, x, y, xs, ys, model, prediction, gtrain, gvalid


def decision() -> dict:
    tp = np.load(CACHE / "tp.npy", mmap_mode="r")
    sources = {CONTROL_NAME: lambda yr: round33_scale.ART / f"{yr}_c{CELLS}.npy",
               "persist_124": lambda yr: ART / f"{yr}_persist.npy"}
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

    stable = [k for k, r in rows.items()
              if k.startswith("persist_") and not k.endswith("_direto")
              and r["gain_vs_s12_percent"] >= 0.3 and r["positive_blocks"] >= 4
              and r["positive_years"] >= 7 and r["positive_months"] >= 67]
    candidates = [k for k in rows if k.startswith("persist_") and not k.endswith("_direto")]
    if stable:
        cls, why = "A", "Alguma fracao atinge amplitude e estabilidade exigidas."
    elif all(rows[k]["gain_vs_s12_percent"] <= 0 for k in candidates):
        cls, why = "B", "Toda fracao piora a S12."
    else:
        cls, why = "D", "Ha ganho, mas sem amplitude (0,3%) e estabilidade simultaneas."

    direct_gain = None
    if f"{CONTROL_NAME}_direto" in rows and "persist_124_direto" in rows:
        a = rows[f"{CONTROL_NAME}_direto"]["rmse"]
        b = rows["persist_124_direto"]["rmse"]
        direct_gain = 100.0 * (1.0 - b / a)
        print("\n=== Efeito pareado das cinco colunas de persistencia ===")
        print(f"  119 atributos (Rodada 33): {a:.6f}")
        print(f"  124 atributos (esta rodada): {b:.6f}")
        print(f"  ganho direto do corretor: {direct_gain:+.3f}%")

    result = {"classification": cls, "reason": why,
              "baseline_rmse": float(np.sqrt(base.mean())),
              "direct_gain_from_persistence_percent": direct_gain,
              "variants": dict(sorted(rows.items(), key=lambda kv: kv[1]["rmse"])),
              "stable_variants": stable, "evaluation_blocks": list(EVAL),
              "external_data_used": False, "no_candidate": not stable,
              "no_test_targets": True, "no_submission": True}
    OUT.mkdir(parents=True, exist_ok=True)
    save_json(OUT / "decision.json", result)
    print("\nDECISAO", cls, why, flush=True)
    print(f'{"variante":<22}{"RMSE":>12}{"ganho":>10}{"blocos":>9}{"anos":>8}{"meses":>10}')
    for key, r in result["variants"].items():
        print(f'{key:<22}{r["rmse"]:>12.6f}{r["gain_vs_s12_percent"]:>9.3f}%'
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
