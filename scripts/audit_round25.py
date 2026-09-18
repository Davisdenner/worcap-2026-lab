"""Auditoria independente das previsões e da diversidade de erro da rodada 25."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from src.competition import CACHE, ROOT, REPORT, save_json
from src.round2 import target_origins

YEARS = (2009, 2011, 2013, 2015, 2017, 2019)
OUT = REPORT / "round25"
ART = ROOT / "data/processed/round25"
REFERENCE = ROOT / "data/processed/round20"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def new_row():
    return dict(count=0, sum_new=0., sum_s12=0., sq_new=0., sq_s12=0., cross=0.)


def add(row, new, s12):
    a = np.asarray(new, np.float64).ravel()
    b = np.asarray(s12, np.float64).ravel()
    row["count"] += len(a)
    row["sum_new"] += a.sum()
    row["sum_s12"] += b.sum()
    row["sq_new"] += np.dot(a, a)
    row["sq_s12"] += np.dot(b, b)
    row["cross"] += np.dot(a, b)


def describe(row):
    n = row["count"]
    an, bs = row["sum_new"]/n, row["sum_s12"]/n
    vn = row["sq_new"]/n-an*an
    vs = row["sq_s12"]/n-bs*bs
    cov = row["cross"]/n-an*bs
    return dict(count=n, new_rmse=float(np.sqrt(row["sq_new"]/n)),
                s12_rmse=float(np.sqrt(row["sq_s12"]/n)),
                new_bias=float(an), s12_bias=float(bs),
                error_cross_product=float(row["cross"]/n),
                error_covariance=float(cov),
                error_correlation=float(cov/np.sqrt(vn*vs)),
                theoretical_unconstrained_alpha=float(
                    (row["sq_s12"]-row["cross"]) /
                    (row["sq_new"]+row["sq_s12"]-2*row["cross"])) )


def main():
    tp = np.load(CACHE / "tp.npy", mmap_mode="r")
    selection = json.loads((OUT / "selection.json").read_text(encoding="utf-8"))
    if selection["selected"] is not None:
        raise ValueError("Esta auditoria assume nenhuma candidata promovida")
    results = {}
    checks = []
    for family in ("h2", "h4"):
        groups = {(area, season): new_row()
                  for area in ("global", "north", "south")
                  for season in ("all", "DJF", "MAM", "JJA", "SON")}
        for year in YEARS:
            pred_path = ART / f"{year}_{family}_prediction.npy"
            meta = json.loads(pred_path.with_suffix(".json").read_text(encoding="utf-8"))
            if digest(pred_path) != meta["sha256"]:
                raise ValueError(f"Hash incorreto: {pred_path}")
            if meta["last_training_target"] != f"{year-1}-12" or not meta["official_only"]:
                raise ValueError("Proveniência do corte incorreta")
            pred = np.load(pred_path, mmap_mode="r")
            ref = np.load(REFERENCE / f"{year}_s12.npy", mmap_mode="r")
            truth = np.asarray(tp[target_origins(year)+1], np.float64)
            if pred.shape != (24, 301, 261) or not np.isfinite(pred).all():
                raise ValueError("Previsão inválida")
            record = json.loads((OUT / f"{year}_{family}.json").read_text(encoding="utf-8"))
            months = (target_origins(year)+1) % 12 + 1
            seasons = (months % 12)//3
            for k in range(24):
                en = truth[k] - pred[k]
                es = truth[k] - ref[k]
                for area, mask in (("global", slice(None)), ("north", slice(240, None)),
                                   ("south", slice(None, 240))):
                    name = ("DJF", "MAM", "JJA", "SON")[seasons[k]]
                    add(groups[(area, "all")], en[mask], es[mask])
                    add(groups[(area, name)], en[mask], es[mask])
            for a in (.1, .25):
                blended = ref + a*(pred-ref)
                rmse = float(np.sqrt(np.mean((truth-blended)**2)))
                reported = next(r["rmse"] for r in record["blends"]
                                if r["model"] == f"{family}_a{a:g}")
                if abs(rmse-reported) > 1e-8:
                    raise ValueError(f"RMSE de mistura divergente: {family} {year} {a}")
                checks.append(dict(model=f"{family}_a{a:g}", year=year,
                                   independently_recomputed_rmse=rmse,
                                   report_rmse=reported))
            if family == "h4":
                if max(max(years) for years in record["selected_analog_years_by_month"]) >= year:
                    raise ValueError("Análogo posterior ao corte")
                if min(record["candidate_count_by_month"]) < 10:
                    raise ValueError("Biblioteca de análogos insuficiente")
        results[family] = {
            area: {season: describe(groups[(area, season)])
                   for season in ("all", "DJF", "MAM", "JJA", "SON")}
            for area in ("global", "north", "south")
        }
    output = dict(source="official historical targets and saved causal predictions",
                  selection_sha256=digest(OUT / "selection.json"),
                  paired_rmse_checks=checks, error_diversity=results,
                  no_test_targets=True, csv_exported=False)
    save_json(OUT / "diversity_audit.json", output)
    lines = ["# Rodada 25 — auditoria da diversidade de erro", "",
             "RMSE das 24 misturas por bloco refeito a partir das previsões arquivadas: PASS.",
             "Hashes das previsões, cortes e anos dos análogos: PASS.", "",
             "| Previsor | Área | RMSE puro | RMSE S12 | Correlação dos erros | Produto cruzado |",
             "| --- | --- | ---: | ---: | ---: | ---: |"]
    for family in ("h2", "h4"):
        for area in ("global", "north", "south"):
            row = results[family][area]["all"]
            lines.append(f"| {family} | {area} | {row['new_rmse']:.6f} | "
                         f"{row['s12_rmse']:.6f} | {row['error_correlation']:.4f} | "
                         f"{row['error_cross_product']:.6f} |")
    lines.extend(["", "A fração ótima analítica consta no JSON apenas como diagnóstico "
                  "retrospectivo; não foi usada para criar outra candidata."])
    (OUT / "DIVERSITY.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
