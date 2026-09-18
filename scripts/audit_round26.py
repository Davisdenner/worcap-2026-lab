"""Auditoria independente dos arquivos OOF e limiares da rodada 26."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

from src.competition import CACHE, ROOT, save_json
from src.round2 import Features, target_origins
from src.round20 import reference
from src.round25 import GRID


OUT = ROOT / "reports/competition/round26"
ART = ROOT / "data/processed/round26"
YEARS = (2009, 2011, 2013, 2015, 2017, 2019)
EVAL = YEARS[1:]
NORTH = np.arange(240*261, 301*261, dtype=np.intp)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    protocol = json.loads((OUT / "protocol.json").read_text(encoding="utf-8"))
    assert protocol["source_sha256"] == sha(ROOT / "src/round26.py")
    assert protocol["protocol_sha256"] == sha(ROOT / "experiments/ROUND26.md")
    assert len(NORTH) == protocol["north_cells"] == 15921
    tp = np.load(CACHE / "tp.npy", mmap_mode="r").reshape(-1, GRID)
    for y in YEARS:
        assert protocol["s12_reference_hashes"][str(y)] == sha(
            ROOT / f"data/processed/round20/{y}_s12.npy")
    rows = []
    for cutoff in EVAL:
        report = json.loads((OUT / f"{cutoff}_predictability.json").read_text(encoding="utf-8"))
        path = ART / f"{cutoff}_oof.npz"
        meta = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        assert sha(path) == meta["sha256"]
        assert meta["last_training_target"] == f"{cutoff-1}-12"
        prior_residual = np.concatenate([
            (tp[target_origins(y)+1][:, NORTH] -
             reference(y).reshape(24, GRID)[:, NORTH]).ravel()
            for y in YEARS if y < cutoff
        ])
        q90, q95 = np.quantile(np.abs(prior_residual), [.9, .95])
        assert np.isclose(q90, report["q90_training_abs_residual"], atol=1e-6)
        assert np.isclose(q95, report["q95_training_abs_residual"], atol=1e-6)
        with np.load(path) as saved:
            residual = saved["residual"]
            predictions = saved["predictions"]
            critical_p = saved["critical_probability"].ravel()
            direction_p = saved["direction_probability"].ravel()
        actual = (tp[target_origins(cutoff)+1][:, NORTH] -
                  reference(cutoff).reshape(24, GRID)[:, NORTH])
        np.testing.assert_allclose(residual, actual, rtol=0, atol=2e-6)
        assert predictions.shape == (len(meta["model_names"]), 24, len(NORTH))
        assert target_origins(cutoff)[-1]+1 < tp.shape[0]-24
        for j, name in enumerate(meta["model_names"]):
            y = residual.astype(np.float64)
            p = predictions[j].astype(np.float64)
            r2 = 1-np.sum((y-p)**2)/np.sum(y*y)
            assert np.isclose(r2, report["group_metrics"][name]["block"]
                              ["r2_against_zero"], atol=1e-9)
        event = np.abs(residual.ravel()) > q90
        assert np.isclose(roc_auc_score(event, critical_p),
                          report["binary_metrics"]["critical_q90"]["block"]["auc"],
                          atol=1e-9)
        assert np.isclose(roc_auc_score(residual.ravel() > 0, direction_p),
                          report["binary_metrics"]["direction"]["block"]["auc"],
                          atol=1e-9)
        f = Features(cutoff)
        climo = np.concatenate([f.climo[(origin+1) % 12, NORTH]
                                for origin in target_origins(cutoff)])
        s12 = reference(cutoff).reshape(24, GRID)[:, NORTH].ravel()
        rows.append({
            "cutoff": cutoff, "sha256_oof": sha(path), "q90_previous": float(q90),
            "q95_previous": float(q95), "last_training_target": meta["last_training_target"],
            "auc_q90_climatology_only_unfitted": float(roc_auc_score(event, climo)),
            "auc_q90_s12_only_unfitted": float(roc_auc_score(event, s12)),
            "auc_q90_full_trained": float(roc_auc_score(event, critical_p)),
        })
        print("AUDIT", cutoff, rows[-1]["auc_q90_full_trained"], flush=True)
    summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
    assert summary["classification"] == "C"
    assert all(summary["pooled_groups"][name]["r2_against_zero"] < 0
               for name in summary["pooled_groups"])
    save_json(OUT / "audit.json", {
        "all_five_oof_residuals_match_frozen_s12": True,
        "all_five_previous_block_thresholds_recomputed": True,
        "all_saved_group_r2_and_binary_auc_recomputed": True,
        "source_protocol_and_s12_hashes_match": True,
        "all_targets_end_by_2020": True,
        "q90_unfitted_rank_baselines_posthoc": rows,
    })
    print("AUDIT OK", flush=True)


if __name__ == "__main__":
    main()
