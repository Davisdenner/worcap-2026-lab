"""Rodada 34: capacidade do corretor da S12 — número de folhas.

A Rodada 33 encerrou a hipótese de volume e registrou que o limite é
capacidade: com 31 folhas e cerca de cem observações por folha, mais dados
refinam valores em vez de criar estrutura. `round20.MODELS` nunca testou
mais de 31 folhas. Ver experiments/ROUND34.md.

Reaproveita integralmente o aparato da Rodada 33 — mesmo sorteio de células
(mesma semente), mesmos 119 atributos, mesmo alvo, mesmas frações — e varia
apenas `max_leaf_nodes`. O braço de 31 folhas é o `c8192` já calculado na
Rodada 33 e não é retreinado, o que torna a comparação pareada e barata.

Roda em CPU, local. Cerca de 1,5 h para os dois braços novos nos seis
blocos. `evaluate()` retoma bloco a bloco.
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
from . import round20, round27, round33_scale

OUT = REPORT / "round34"
ART = ROOT / "data/processed/round34"
PROTOCOL = ROOT / "experiments/ROUND34.md"

YEARS = round27.YEARS
EVAL = round27.EVAL
SHAPE = round33_scale.SHAPE
FEATURES = round33_scale.FEATURES          # 119
CELLS = 8192                               # o braço vencedor da Rodada 33
FRACTIONS = round33_scale.FRACTIONS        # (.10, .25)
SEED = round33_scale.SEED                  # mesmo sorteio de células

BASE_LEAVES = 31                           # reaproveitado de round33 c8192
NEW_LEAVES = (127, 511)
TARGET_DIRECT_RMSE = 1.765                 # alvo declarado no protocolo


def _tree(leaves: int) -> dict:
    """Hiperparâmetros de global31 com `max_leaf_nodes` substituído."""
    _, _, _, minimum, l2 = round20.MODELS[round33_scale.BASE_MODEL]
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
    record = {
        "protocol_sha256": sha(PROTOCOL), "reference": "S12",
        "inherits": "round33_scale (mesmo sorteio, atributos e alvo)",
        "cells": CELLS, "features": FEATURES, "base_leaves": BASE_LEAVES,
        "new_leaves": list(NEW_LEAVES), "seed": SEED,
        "fractions": [float(a) for a in FRACTIONS],
        "target_direct_rmse": TARGET_DIRECT_RMSE,
        "trees": {str(n): _tree(n) for n in (BASE_LEAVES, *NEW_LEAVES)},
        "years": list(YEARS), "eval_years": list(EVAL),
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
        "Protocolo ou configuração da rodada 34 mudou depois de congelado:\n"
        + "\n".join(diff)
        + f"\n\nSe a mudança foi deliberada, apague {path} e os artefatos de "
          f"{ART} antes de reexecutar.")


def tag(leaves: int) -> str:
    return f"L{leaves}"


def prediction_path(year: int, leaves: int) -> Path:
    """O braço de 31 folhas vive na Rodada 33; os novos, aqui."""
    if leaves == BASE_LEAVES:
        return round33_scale.ART / f"{year}_c{CELLS}.npy"
    return ART / f"{year}_{tag(leaves)}.npy"


def evaluate() -> None:
    locked()
    for year in YEARS:
        pending = [n for n in NEW_LEAVES if not prediction_path(year, n).exists()]
        if not pending:
            print(f"BLOCO EXISTENTE {year}", flush=True)
            continue
        if not prediction_path(year, BASE_LEAVES).exists():
            raise SystemExit(
                f"Falta {prediction_path(year, BASE_LEAVES)}. Rode a Rodada 33 "
                "antes: o braço de 31 folhas é o controle pareado desta rodada.")
        print(f"INICIANDO BLOCO {year}: {pending} folhas", flush=True)
        f = Features(year)
        gtrain, gvalid = round20.context(f)
        x, y = round33_scale.build_block(f, gtrain, CELLS)
        xs = x.reshape(-1, FEATURES)
        ys = y.reshape(-1)
        for leaves in pending:
            started = time.monotonic()
            print(f"  {tag(leaves)}: {xs.shape[0]} linhas, {leaves} folhas", flush=True)
            model = HistGradientBoostingRegressor(**_tree(leaves)).fit(xs, ys)
            seconds = time.monotonic() - started
            print(f"  {tag(leaves)}: ajuste em {seconds:.0f}s", flush=True)
            prediction = round33_scale.predict_block(model, f, gvalid)
            np.save(prediction_path(year, leaves), prediction)
            save_json(ART / f"{year}_{tag(leaves)}.json", {
                "leaves": leaves, "cells": CELLS, "features": FEATURES,
                "train_rows": int(xs.shape[0]), "fit_seconds": seconds})
            print(f"  {tag(leaves)}: CONCLUIDO", flush=True)
            del model, prediction
        del f, x, y, xs, ys, gtrain, gvalid


def decision() -> dict:
    tp = np.load(CACHE / "tp.npy", mmap_mode="r")
    leaf_set = (BASE_LEAVES, *NEW_LEAVES)
    monthly: dict[str, list[float]] = {}
    for year in EVAL:
        truth = np.asarray(tp[target_origins(year) + 1], np.float64).reshape(24, -1)
        s12 = np.maximum(np.asarray(round20.reference(year), np.float64).reshape(24, -1), 0.0)
        monthly.setdefault("s12", []).extend(np.mean((s12 - truth) ** 2, axis=1).tolist())
        for leaves in leaf_set:
            path = prediction_path(year, leaves)
            if not path.exists():
                continue
            candidate = np.asarray(np.load(path), np.float64).reshape(24, -1)
            name = tag(leaves)
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

    print("\n=== Capacidade: RMSE direto do corretor ===")
    print(f'{"folhas":<10}{"RMSE direto":>14}{"vs alvo 1.765":>16}')
    for leaves in leaf_set:
        key = f"{tag(leaves)}_direto"
        if key in rows:
            value = rows[key]["rmse"]
            print(f'{leaves:<10}{value:>14.6f}{value - TARGET_DIRECT_RMSE:>+16.6f}')
    print("O alvo declarado era ~1.765; acima de ~1.79 o ganho na mistura e desprezivel.")

    result = {"classification": cls, "reason": why,
              "baseline_rmse": float(np.sqrt(base.mean())),
              "target_direct_rmse": TARGET_DIRECT_RMSE,
              "variants": dict(sorted(rows.items(), key=lambda kv: kv[1]["rmse"])),
              "stable_variants": stable, "evaluation_blocks": list(EVAL),
              "no_candidate": not stable, "no_test_targets": True,
              "no_submission": True}
    OUT.mkdir(parents=True, exist_ok=True)
    save_json(OUT / "decision.json", result)
    print("\nDECISAO", cls, why, flush=True)
    print(f'{"variante":<16}{"RMSE":>12}{"ganho":>10}{"blocos":>9}{"anos":>8}{"meses":>10}')
    for key, r in result["variants"].items():
        print(f'{key:<16}{r["rmse"]:>12.6f}{r["gain_vs_s12_percent"]:>9.3f}%'
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
