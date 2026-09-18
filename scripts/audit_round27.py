"""Recontagem independente do oracle, vencedor e soft gating da rodada 27."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score, log_loss

from src.competition import CACHE, ROOT, save_json
from src.round2 import target_origins

YEARS = (2009, 2011, 2013, 2015, 2017, 2019)
EVAL = YEARS[1:]
GRID = 301*261
NORTH = np.arange(240*261, GRID)
OUT = ROOT / "reports/competition/round27"
ART = ROOT / "data/processed/round27"
REF = ROOT / "data/processed/round20"
ANALOG = ROOT / "data/processed/round25"
RISK = ROOT / "data/processed/round26"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def close(x: float, y: float, tol: float = 1e-8) -> None:
    if not np.isclose(x, y, rtol=tol, atol=tol):
        raise AssertionError(f"metric mismatch: {x} != {y}")


def main() -> None:
    protocol = json.loads((OUT / "protocol.json").read_text(encoding="utf-8"))
    assert protocol["protocol_sha256"] == sha(ROOT / "experiments/ROUND27.md")
    for year, row in protocol["input_hashes"].items():
        y = int(year)
        paths = {"s12": REF / f"{y}_s12.npy",
                 "analog": ANALOG / f"{y}_h4_prediction.npy"}
        if y in EVAL:
            paths["risk_q90"] = RISK / f"{y}_oof.npz"
        for name, path in paths.items():
            assert row[name] == sha(path)
    tp = np.load(CACHE / "tp.npy", mmap_mode="r").reshape(-1, GRID)
    oracle = json.loads((OUT / "oracle.json").read_text(encoding="utf-8"))
    decision = json.loads((OUT / "decision.json").read_text(encoding="utf-8"))
    global_sums = np.zeros(4, np.float64)
    north_sums = np.zeros(4, np.float64)
    gate_sums = {key: np.zeros(5, np.float64) for key in decision["gates"]}
    baseline_sse_5 = 0.
    fixed_global_sse_5 = 0.
    model_rows = []
    for year in YEARS:
        indices = target_origins(year)+1
        assert indices.max() < 972  # Last permitted target is 2020-12.
        truth = np.asarray(tp[indices], np.float64)
        s12 = np.asarray(np.load(REF / f"{year}_s12.npy", mmap_mode="r")
                         .reshape(24, GRID), np.float64)
        analog = np.asarray(np.load(ANALOG / f"{year}_h4_prediction.npy", mmap_mode="r")
                            .reshape(24, GRID), np.float64)
        l12 = (truth-s12)**2
        la = (truth-analog)**2
        lo = np.minimum(l12, la)
        wins = la < l12
        totals = np.array([l12.sum(), la.sum(), lo.sum(), wins.sum()])
        global_sums += totals
        north_totals = np.array([l12[:, NORTH].sum(), la[:, NORTH].sum(),
                                 lo[:, NORTH].sum(), wins[:, NORTH].sum()])
        north_sums += north_totals
        for j, key in enumerate(("sse_s12", "sse_analog", "sse_oracle", "analog_wins")):
            close(totals[j], oracle["by_block"][str(year)][key], 1e-9)
        if year not in EVAL:
            continue
        baseline_sse_5 += totals[0]
        fixed_global_sse_5 += np.sum((truth-(s12+.1*(analog-s12)))**2)
        path = ART / f"{year}_winner_oof.npz"
        meta = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        assert sha(path) == meta["sha256"]
        assert meta["last_training_target"] == f"{year-1}-12"
        report = json.loads((OUT / f"{year}_winner.json").read_text(encoding="utf-8"))
        with np.load(path) as saved:
            probabilities = np.asarray(saved["probability"], np.float64)
            y = np.asarray(saved["winner"], bool)
            d = np.asarray(saved["advantage"], np.float64)
        assert y.shape == (24, len(NORTH))
        np.testing.assert_array_equal(y, wins[:, NORTH])
        # The stored D uses float32 source residuals; allow its final rounding.
        np.testing.assert_allclose(d, l12[:, NORTH]-la[:, NORTH], rtol=2e-6, atol=1e-3)
        prior = report["prior_analog_win"]
        for j, name in enumerate(meta["model_names"]):
            p = np.clip(probabilities[j].ravel(), .01, .99)
            target = y.ravel()
            m = report["winner_metrics"][name]["block"]
            close(roc_auc_score(target, p), m["auc"])
            close(np.mean((target-p)**2), m["brier"])
            close(log_loss(target, p, labels=[False, True]), m["log_loss"])
            close(np.mean((target-prior)**2), m["baseline_brier"])
        model_rows.append({"block": year, "target_last": f"{year+1}-12",
                           "archive_sha256": sha(path),
                           "winner_fraction": float(y.mean())})
        for key, row in decision["gates"].items():
            j = meta["model_names"].index(row["model"])
            g = row["gmax"]*probabilities[j]
            delta = analog[:, NORTH]-s12[:, NORTH]
            altered = s12[:, NORTH]+g*delta
            north_sse = float(np.sum((truth[:, NORTH]-altered)**2))
            total_sse = float(totals[0]-north_totals[0]+north_sse)
            gate_sums[key] += [total_sse, north_sse, np.sum((g*delta)**2),
                               int(total_sse < totals[0]), 0.]
            close(np.sqrt(total_sse/(24*GRID)), row["by_block"][str(year)]["global_rmse"])
    for j, key in enumerate(("sse_s12", "sse_analog", "sse_oracle", "analog_wins")):
        close(global_sums[j], oracle["global"][key], 1e-9)
        close(north_sums[j], oracle["north"][key], 1e-9)
    n_global = 5*24*GRID
    n_north = 5*24*len(NORTH)
    close(np.sqrt(baseline_sse_5/n_global), decision["baselines"]["s12"]["global_rmse"])
    close(np.sqrt(fixed_global_sse_5/n_global),
          decision["baselines"]["fixed10_global"]["global_rmse"])
    for key, row in decision["gates"].items():
        sums = gate_sums[key]
        close(np.sqrt(sums[0]/n_global), row["global_rmse"])
        close(np.sqrt(sums[1]/n_north), row["north_rmse"])
        close(np.sqrt(sums[2]/n_north), row["rms_change_north"])
        close(sums[3], row["positive_blocks"])
    assert decision["classification"] == "D"
    save_json(OUT / "audit.json", {
        "protocol_and_all_input_hashes_verified": True,
        "oracle_recomputed_from_frozen_predictions": True,
        "all_winner_labels_and_advantages_recomputed": True,
        "all_auc_brier_log_loss_recomputed": True,
        "all_gated_rmse_and_block_counts_recomputed": True,
        "all_targets_at_or_before_2020_12": True,
        "classification": "D", "model_rows": model_rows,
        "source_sha256": sha(ROOT / "src/round27.py"),
        "audit_script_sha256": sha(ROOT / "scripts/audit_round27.py"),
    })
    print("ROUND27 AUDIT OK", flush=True)


if __name__ == "__main__":
    main()
