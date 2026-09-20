"""Rodada 33: taxa de amostragem de células no corretor da S12.

Testa a única classe de mudança que escapa da parede de estimação
documentada nas Rodadas 27-32: mais dado de treino, sem nenhum parâmetro
calibrado nos blocos de avaliação. Ver experiments/ROUND33.md.

Reproduz a configuração `global31` da Rodada 20 sem nenhuma alteração —
mesmos 119 atributos (55 locais de `round2` + 64 globais de
`round20.context`), mesma árvore, mesmo alvo, mesmas frações de mistura —
e varia uma única coisa: as **768 células por mês** viram **8.192**.

O braço de 768 deve reproduzir a linha `global31` já registrada em
`reports/competition/round20/{ano}.json`. Essa é a verificação externa da
implementação: se não bater, não olhe o resto.

Roda em CPU, cabe em máquina local: pico em torno de 2,5 GB, cerca de 1,5 h
para os seis blocos. `evaluate()` retoma bloco a bloco.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor

from .competition import CACHE, ROOT, REPORT, save_json
from .round2 import Features, target_origins
from . import round20, round27

OUT = REPORT / "round33"
ART = ROOT / "data/processed/round33"
PROTOCOL = ROOT / "experiments/ROUND33.md"

YEARS = round27.YEARS
EVAL = round27.EVAL
SHAPE = (301, 261)
GRID = SHAPE[0] * SHAPE[1]
LOCAL = 55                          # round2.Features.matrix(..., context=True)
GLOBAL = 64                         # round20.context
FEATURES = LOCAL + GLOBAL           # 119, idêntico a global31

BASE_MODEL = "global31"             # round20.MODELS['global31'] = (True, 31, 768, 100, 10.)
CELL_COUNTS = (768, 8192)           # 768 é o valor vigente; 0,98% da grade
FRACTIONS = round20.FRACTIONS       # (.10, .25), as mesmas da Rodada 20
SEED = 20261101


def _tree():
    """Exatamente os hiperparâmetros de `round20.fitted` para global31."""
    _, leaves, _, minimum, l2 = round20.MODELS[BASE_MODEL]
    return dict(max_leaf_nodes=leaves, min_samples_leaf=minimum,
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
    _, _, base_cells, _, _ = round20.MODELS[BASE_MODEL]
    record = {
        "protocol_sha256": sha(PROTOCOL), "reference": "S12",
        "base_model": BASE_MODEL, "round20_cells": base_cells,
        "features": FEATURES, "cell_counts": list(CELL_COUNTS),
        "fractions": [float(a) for a in FRACTIONS], "tree": _tree(),
        "seed": SEED, "years": list(YEARS), "eval_years": list(EVAL),
        "training_start": "1981-01-01 (Features.idx, inalterado)",
        "minimum_gain": 0.003, "official_only": True,
        "no_test_targets": True, "no_submission": True,
    }
    path = OUT / "protocol.json"
    if not path.exists():
        save_json(path, record)
        return
    stored = json.loads(path.read_text(encoding="utf-8"))
    current = json.loads(json.dumps(record))
    if stored == current:
        return
    diff = [f"  {key}: {stored.get(key, '<ausente>')!r} -> {current.get(key, '<ausente>')!r}"
            for key in sorted(set(stored) | set(current))
            if stored.get(key) != current.get(key)]
    raise ValueError(
        "Protocolo ou configuração da rodada 33 mudou depois de congelado:\n"
        + "\n".join(diff)
        + f"\n\nSe a mudança foi deliberada, apague {path} e os artefatos de "
          f"{ART} antes de reexecutar; os resultados antigos medem outro desenho.")


def tag(cells: int) -> str:
    return f"c{cells}"


def build_block(f: Features, global_train: np.ndarray, max_cells: int):
    """(n, max_cells, 119) e (n, max_cells), montados UMA vez no tamanho máximo.

    O braço de 768 células sai daqui pelas primeiras 768 colunas: a amostra
    pequena é ANINHADA na grande, o que isola a taxa de amostragem sem ruído
    de reamostragem e evita remontar a matriz por configuração.

    Convenção idêntica à de `round20.training`: alvo é o observado menos a
    climatologia do mês-alvo (coluna 4), e os 64 atributos globais do mês
    são repetidos em todas as células daquele mês.
    """
    rng = np.random.default_rng(SEED)
    n = f.idx.size
    x = np.empty((n, max_cells, FEATURES), np.float32)
    y = np.empty((n, max_cells), np.float32)
    started = time.monotonic()
    for k, origin in enumerate(f.idx):
        cells = rng.choice(GRID, max_cells, replace=False)
        local = f.matrix(int(origin), cells, context=True)
        x[k, :, :LOCAL] = local
        x[k, :, LOCAL:] = global_train[k]
        y[k] = f.tp[int(origin) + 1, cells] - local[:, 4]
        if (k + 1) % 100 == 0 or k + 1 == n:
            print(f"  montadas {k + 1}/{n} origens "
                  f"({time.monotonic() - started:.0f}s)", flush=True)
    return x, y


def predict_block(model, f: Features, global_valid: np.ndarray) -> np.ndarray:
    """Previsão completa de grade cheia, como `round20.predict`."""
    cells = np.arange(GRID)
    out = np.empty((24, GRID), np.float32)
    for k, origin in enumerate(target_origins(f.year)):
        local = f.matrix(int(origin), cells, context=True)
        rows = np.column_stack([local, np.broadcast_to(global_valid[k], (GRID, GLOBAL))])
        out[k] = np.maximum(local[:, 4] + model.predict(rows), 0.0)
    return out.reshape(24, *SHAPE)


def evaluate() -> None:
    locked()
    widest = max(CELL_COUNTS)
    tree = _tree()
    for year in YEARS:
        pending = [c for c in CELL_COUNTS if not (ART / f"{year}_{tag(c)}.npy").exists()]
        if not pending:
            print(f"BLOCO EXISTENTE {year}", flush=True)
            continue
        print(f"INICIANDO BLOCO {year}: {pending}", flush=True)
        f = Features(year)
        gtrain, gvalid = round20.context(f)          # 64 atributos globais, código original
        x, y = build_block(f, gtrain, widest)
        for cells_per_month in pending:
            name = tag(cells_per_month)
            xs = x[:, :cells_per_month].reshape(-1, FEATURES)
            ys = y[:, :cells_per_month].reshape(-1)
            started = time.monotonic()
            print(f"  {name}: {xs.shape[0]} linhas x {FEATURES} atributos", flush=True)
            model = HistGradientBoostingRegressor(**tree).fit(xs, ys)
            seconds = time.monotonic() - started
            print(f"  {name}: ajuste em {seconds:.0f}s", flush=True)
            del xs, ys
            prediction = predict_block(model, f, gvalid)
            np.save(ART / f"{year}_{name}.npy", prediction)
            save_json(ART / f"{year}_{name}.json", {
                "cells_per_month": cells_per_month, "base_model": BASE_MODEL,
                "features": FEATURES, "train_origins": int(f.idx.size),
                "train_rows": int(f.idx.size * cells_per_month),
                "nested_sample": True, "fit_seconds": seconds})
            print(f"  {name}: CONCLUIDO", flush=True)
            del model, prediction
        del f, x, y, gtrain, gvalid


def control_check() -> dict:
    """Compara o braço de 768 com a linha `global31` já registrada na Rodada 20."""
    rows = {}
    for year in YEARS:
        recorded = REPORT / "round20" / f"{year}_direct.json"
        path = ART / f"{year}_{tag(768)}.npy"
        if not (recorded.exists() and path.exists()):
            continue
        reference = next((r for r in json.loads(recorded.read_text(encoding="utf-8"))
                          if r["model"] == BASE_MODEL), None)
        if reference is None:
            continue
        tp = np.load(CACHE / "tp.npy", mmap_mode="r")
        truth = np.asarray(tp[target_origins(year) + 1], np.float64).reshape(24, -1)
        mine = np.asarray(np.load(path), np.float64).reshape(24, -1)
        rows[year] = {"round20_rmse": reference["rmse"],
                      "round33_rmse": float(np.sqrt(np.mean((mine - truth) ** 2))),
                      }
        rows[year]["difference"] = rows[year]["round33_rmse"] - rows[year]["round20_rmse"]
    print("\n=== Controle: braco de 768 contra a global31 da Rodada 20 ===")
    print(f'{"bloco":<8}{"round20":>12}{"round33":>12}{"diferenca":>12}')
    for year, r in rows.items():
        print(f'{year:<8}{r["round20_rmse"]:>12.6f}{r["round33_rmse"]:>12.6f}'
              f'{r["difference"]:>12.6f}')
    print("Diferencas pequenas confirmam a implementacao. Grandes invalidam o resto.")
    return rows


def decision() -> dict:
    tp = np.load(CACHE / "tp.npy", mmap_mode="r")
    monthly: dict[str, list[float]] = {}
    for year in EVAL:
        truth = np.asarray(tp[target_origins(year) + 1], np.float64).reshape(24, -1)
        s12 = np.maximum(np.asarray(round20.reference(year), np.float64).reshape(24, -1), 0.0)
        monthly.setdefault("s12", []).extend(np.mean((s12 - truth) ** 2, axis=1).tolist())
        for cells_per_month in CELL_COUNTS:
            path = ART / f"{year}_{tag(cells_per_month)}.npy"
            if not path.exists():
                continue
            candidate = np.asarray(np.load(path), np.float64).reshape(24, -1)
            name = tag(cells_per_month)
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
              if k != "s12" and not k.endswith("_direto")
              and r["gain_vs_s12_percent"] >= 0.3 and r["positive_blocks"] >= 4
              and r["positive_years"] >= 7 and r["positive_months"] >= 67]
    if stable:
        cls, why = "A", "Alguma combinacao atinge amplitude e estabilidade exigidas."
    elif all(r["gain_vs_s12_percent"] <= 0 for k, r in rows.items()
             if k != "s12" and not k.endswith("_direto")):
        cls, why = "B", "Toda combinacao piora a S12."
    else:
        cls, why = "D", "Ha ganho, mas sem amplitude (0,3%) e estabilidade simultaneas."

    result = {"classification": cls, "reason": why,
              "baseline_rmse": float(np.sqrt(base.mean())),
              "variants": dict(sorted(rows.items(), key=lambda kv: kv[1]["rmse"])),
              "stable_variants": stable, "control": control_check(),
              "evaluation_blocks": list(EVAL), "no_candidate": not stable,
              "no_test_targets": True, "no_submission": True}
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
    parser.add_argument("stage", choices=("evaluate", "decision", "control_check"))
    globals()[parser.parse_args().stage]()
