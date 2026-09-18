"""Recompute Round-29 metrics from frozen prediction maps and write its report."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path

import numpy as np

from src.competition import CACHE, ROOT, save_json
from src.round2 import target_origins

YEARS = (2009, 2011, 2013, 2015, 2017, 2019)
OUT = ROOT / "reports/competition/round29"
ART = ROOT / "data/processed/round29"
NAMES = ("s12", "pls16_existing", "extratrees_64", "extratrees_96",
         "lightgbm_15", "lightgbm_31", *[f"rrr_{r}" for r in (4, 8, 16, 32)],
         *[f"cca_{r}" for r in (4, 8, 16, 32)])


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def calc(y: np.ndarray, a: np.ndarray, b: np.ndarray) -> dict:
    e = np.asarray(y, np.float64).ravel()-np.asarray(a, np.float64).ravel()
    f = np.asarray(y, np.float64).ravel()-np.asarray(b, np.float64).ravel()
    delta = np.asarray(b, np.float64).ravel()-np.asarray(a, np.float64).ravel()
    s12 = np.mean(e*e)
    model = np.mean(f*f)
    oracle = np.mean(np.minimum(e*e, f*f))
    blend = np.mean((e-.1*delta)**2)
    centered_e = e-e.mean()
    centered_f = f-f.mean()
    cov = np.mean(centered_e*centered_f)
    corr = cov/np.sqrt(np.mean(centered_e**2)*np.mean(centered_f**2))
    return {
        "rmse_s12": float(np.sqrt(s12)), "rmse_model": float(np.sqrt(model)),
        "rmse_oracle": float(np.sqrt(oracle)), "rmse_blend10": float(np.sqrt(blend)),
        "residual_correlation": float(corr), "residual_covariance": float(cov),
        "gain_model_percent": float(100*(1-np.sqrt(model/s12))),
        "gain_oracle_percent": float(100*(1-np.sqrt(oracle/s12))),
        "gain_blend10_percent": float(100*(1-np.sqrt(blend/s12))),
    }


def raw(y: np.ndarray, a: np.ndarray, b: np.ndarray) -> dict:
    e = np.asarray(y, np.float64).ravel()-np.asarray(a, np.float64).ravel()
    f = np.asarray(y, np.float64).ravel()-np.asarray(b, np.float64).ravel()
    d = np.asarray(b, np.float64).ravel()-np.asarray(a, np.float64).ravel()
    return {"n": int(e.size), "s12": float(np.sum(e*e)),
            "model": float(np.sum(f*f)),
            "oracle": float(np.sum(np.minimum(e*e, f*f))),
            "blend": float(np.sum((e-.1*d)**2)),
            "e": float(e.sum()), "f": float(f.sum()),
            "ee": float(np.sum(e*e)), "ff": float(np.sum(f*f)),
            "ef": float(np.sum(e*f))}


def pooled(m: dict) -> dict:
    n = m["n"]
    ve = m["ee"]/n-(m["e"]/n)**2
    vf = m["ff"]/n-(m["f"]/n)**2
    cov = m["ef"]/n-m["e"]*m["f"]/n**2
    return {"rmse_s12": float(np.sqrt(m["s12"]/n)),
            "rmse_model": float(np.sqrt(m["model"]/n)),
            "rmse_oracle": float(np.sqrt(m["oracle"]/n)),
            "rmse_blend10": float(np.sqrt(m["blend"]/n)),
            "gain_model_percent": float(100*(1-np.sqrt(m["model"]/m["s12"]))),
            "gain_oracle_percent": float(100*(1-np.sqrt(m["oracle"]/m["s12"]))),
            "gain_blend10_percent": float(100*(1-np.sqrt(m["blend"]/m["s12"]))),
            "residual_covariance": float(cov),
            "residual_correlation": float(cov/np.sqrt(ve*vf))}


def compare(expected: dict, actual: dict, label: str) -> None:
    for key, value in actual.items():
        if not np.isclose(expected[key], value, rtol=0, atol=5e-10):
            raise ValueError(f"Métrica divergente: {label} {key}: {expected[key]} {value}")


def audit() -> dict:
    protocol = json.loads((OUT / "protocol.json").read_text(encoding="utf-8"))
    if sha(ROOT / "experiments/ROUND29.md") != protocol["protocol_sha256"]:
        raise ValueError("Protocolo alterado")
    if sha(CACHE / "tp.npy") != protocol["historical_target_cache_sha256"]:
        raise ValueError("Observações históricas alteradas")
    tp = np.load(CACHE / "tp.npy", mmap_mode="r").reshape(-1, 78561)
    if tp.shape != (996, 78561):
        raise ValueError("Alvos ultrapassam dezembro de 2022")
    summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
    if set(summary) != set(NAMES):
        raise ValueError("Faltam modelos ou cortes completos na síntese")
    checks = {}
    totals = {name: None for name in NAMES}
    lat = np.repeat(np.arange(-60, 15.01, .25), 261)
    for year in YEARS:
        refpath = ROOT / f"data/processed/round20/{year}_s12.npy"
        if sha(refpath) != protocol["inputs_sha256"][str(year)]["s12"]:
            raise ValueError("S12 alterada")
        s12 = np.load(refpath, mmap_mode="r").reshape(24, 78561)
        truth = np.asarray(tp[target_origins(year)+1]).reshape(24, 78561)
        if np.max(target_origins(year)+1) >= 996:
            raise ValueError("Corte histórico inválido")
        for name in NAMES:
            path = ART / f"{year}_{name}.npy"
            row = json.loads((OUT / f"{year}_{name}.json").read_text(encoding="utf-8"))
            if sha(path) != row["prediction_sha256"]:
                raise ValueError(f"Previsão alterada: {year} {name}")
            pred = np.load(path, mmap_mode="r").reshape(24, 78561)
            if not np.isfinite(pred).all() or np.min(pred) < 0:
                raise ValueError(f"Previsão inválida: {year} {name}")
            if name == "s12":
                np.testing.assert_array_equal(pred, s12)
            if name == "pls16_existing":
                original = ROOT / f"data/processed/round9/{year}_pls16.npy"
                if sha(original) != protocol["inputs_sha256"][str(year)]["pls16"]:
                    raise ValueError("PLS16 alterado")
                np.testing.assert_array_equal(pred, np.load(original, mmap_mode="r").reshape(24, 78561))
            compare(row["global"], calc(truth, s12, pred), f"{year} {name} global")
            block_raw = raw(truth, s12, pred)
            totals[name] = block_raw if totals[name] is None else {
                key: totals[name][key]+block_raw[key] for key in block_raw}
            north = np.arange(240*261, 301*261)
            compare(row["by_region"]["north"],
                    calc(truth[:, north], s12[:, north], pred[:, north]),
                    f"{year} {name} norte")
            for low, high in ((-60, -45), (-45, -30), (-30, -15), (-15, 0), (0, 15.01)):
                cells = np.flatnonzero((lat >= low) & (lat < high))
                compare(row["by_region"][f"lat_{low}_{high}"],
                        calc(truth[:, cells], s12[:, cells], pred[:, cells]),
                        f"{year} {name} latitude {low}:{high}")
            for k in (0, 1):
                sl = slice(12*k, 12*(k+1))
                compare(row["by_year"][str(year+k)],
                        calc(truth[sl], s12[sl], pred[sl]),
                        f"{year+k} {name}")
            checks[f"{year}_{name}"] = row["prediction_sha256"]
    for name, moments in totals.items():
        compare(summary[name]["overall"], pooled(moments), f"{name} agregado")
    return {"passed": True, "prediction_hashes": checks,
            "protocol_sha256": protocol["protocol_sha256"],
            "summary_sha256": sha(OUT / "summary.json"),
            "generator_code_sha256": sha(ROOT / "src/round29.py"),
            "audit_code_sha256": sha(Path(__file__)),
            "runtime": {"python": platform.python_version(),
                        "numpy": np.__version__,
                        "scikit_learn": importlib.metadata.version("scikit-learn"),
                        "lightgbm": importlib.metadata.version("lightgbm")},
            "full_grid_block_year_region_and_pooled_recomputed": True,
            "no_2023_2024_targets": True,
            "baseline_s12_unchanged": True,
            "no_submission": True}


def classify(record: dict) -> str:
    m = record["overall"]
    if (m["gain_model_percent"] >= .3 and record["positive_blocks"] >= 4 and
            record["positive_years"] >= 7):
        return "A"
    if (m["gain_blend10_percent"] >= .1 and
            record["positive_blend_blocks"] >= 4 and
            m["gain_oracle_percent"] >= 1):
        return "B"
    return "C"


def report(audit_result: dict) -> None:
    summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
    families = {
        "ExtraTrees": ("extratrees_64", "extratrees_96"),
        "LightGBM": ("lightgbm_15", "lightgbm_31"),
        "RRR": tuple(f"rrr_{r}" for r in (4, 8, 16, 32)),
        "CCA regularizada": tuple(f"cca_{r}" for r in (4, 8, 16, 32)),
    }
    order = {"A": 0, "B": 1, "C": 2, "D": 3}
    family_class = {name: min((classify(summary[key]) for key in names), key=order.get)
                    for name, names in families.items()}
    family_class["CNN/U-Net"] = "D"
    # Only A/B families are eligible for immediate follow-up. The already
    # reused folds do not justify promoting a merely diverse C family.
    followup = [name for name, cls in family_class.items() if cls in ("A", "B")][:2]
    lines = [
        "# Rodada 29 — famílias fora do HistBoost",
        "",
        "Comparação OOF causal nos seis blocos 2009–2020, sempre contra a S12",
        "inalterada. Dados e transformações de cada corte foram ajustados antes",
        "do bloco avaliado. Nenhum alvo 2023/24, submission ou score público foi usado.",
        "",
        "## Tabela principal",
        "",
        "O oracle escolhe o menor erro por pixel **com acesso ao observado**:",
        "é limite diagnóstico, não previsão operacional. Ensemble é o blend",
        "fixo 90% S12 + 10% novo modelo, sem ajuste após os folds.",
        "",
        "| Modelo | RMSE | Corr(e,S12) | Cov(e,S12) | Oracle RMSE | Blend 10% (ganho) | Blocos/anos melhores | Custo treino+pred (s) | Classe |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |",
    ]
    for name in ("s12", "pls16_existing", *[n for group in families.values() for n in group]):
        row = summary[name]
        m = row["overall"]
        cost = row["train_seconds"]+row["predict_seconds"]
        cls = "ref." if name == "s12" else ("controle" if name == "pls16_existing" else classify(row))
        lines.append(f"| {name} | {m['rmse_model']:.6f} | {m['residual_correlation']:.4f} | "
                     f"{m['residual_covariance']:.4f} | {m['rmse_oracle']:.6f} | "
                     f"{m['gain_blend10_percent']:+.3f}% | "
                     f"{row['positive_blocks']}/6, {row['positive_years']}/12 | {cost:.1f} | {cls} |")
    lines += [
        "",
        "## Estabilidade, regiões e modos",
        "",
        "As métricas completas por bloco, ano, norte e faixa de latitude",
        "estão em `summary.json`; os mapas e hashes individuais ficam em",
        "`data/processed/round29`. Os números abaixo são por configuração",
        "fixada, não escolha de um fold para ajustar o próximo.",
        "",
    ]
    for family, names in families.items():
        lines += [f"### {family}", ""]
        for name in names:
            row = summary[name]
            m = row["overall"]
            north = row["by_region"]["north"]
            per_block = ", ".join(f"{year}: {value['gain_model_percent']:+.2f}%/"
                                  f"{value['gain_blend10_percent']:+.2f}%"
                                  for year, value in row["by_block"].items())
            line = (f"- `{name}`: RMSE global {m['rmse_model']:.6f} "
                    f"({m['gain_model_percent']:+.3f}% vs S12); norte "
                    f"{north['rmse_model']:.6f}; oracle {m['gain_oracle_percent']:+.2f}%; "
                    f"blend 10% {m['gain_blend10_percent']:+.3f}% "
                    f"em {row['positive_blend_blocks']}/6 blocos. "
                    f"Blocos (individual/blend): {per_block}.")
            if row["mode_overlap_pls16_mean"] is not None:
                line += f" Sobreposição média de subespaço com PLS16: {row['mode_overlap_pls16_mean']:.3f}."
            lines.append(line)
        lines.append("")
    lines += [
        "## Decisão",
        "",
        *[f"- **{name}: {cls}.**" for name, cls in family_class.items()],
        "",
        "A classe C significa que as configurações testadas não entregaram",
        "ganho individual nem complementar estável. Os oracles de 5–7%",
        "mostram diferenças pontuais, mas dependem do observado e não se",
        "converteram no blend fixo causal. Não provam ausência de qualquer",
        "estrutura nova em arquiteturas ou decisões ainda não testadas.",
        f"O melhor LightGBM isolado ficou em RMSE {summary['lightgbm_31']['overall']['rmse_model']:.6f} "
        f"contra {summary['s12']['overall']['rmse_model']:.6f} da S12; "
        f"seu blend mudou o RMSE em {summary['lightgbm_31']['overall']['gain_blend10_percent']:+.3f}%. "
        "Não há justificativa empírica para",
        "outra rodada de tuning de boosting com estes atributos. ExtraTrees",
        "também perdeu e teve custo substancialmente maior. RRR/CCA",
        "diversificaram um pouco os resíduos, mas sem ganho operacional",
        "estável; os modos dominantes têm grande sobreposição com PLS16.",
        "",
        f"Famílias para aprofundar na próxima rodada: {', '.join(followup) if followup else 'nenhuma por enquanto'}.",
        "A classe D de CNN/U-Net reflete apenas viabilidade: MX350 com 2 GB",
        "e ausência de PyTorch/CUDA no ambiente do projeto. Não é resultado",
        "de validação preditiva. LightGBM foi instalado apenas no ambiente",
        "virtual local; nenhuma outra família de boosting foi adicionada.",
        "",
        "## Limitações e rastreabilidade",
        "",
        "Os blocos 2009–2020 já foram reutilizados em várias decisões; a",
        "melhor linha de uma pequena grade ainda sofre viés de seleção.",
        "Correlação e oracle por pixel descrevem diversidade, mas pixels",
        "de um mesmo mês não são observações temporais independentes.",
        "O custo tabelado inclui ajuste e previsão do modelo; preparação",
        "comum dos atributos e PCs não está atribuída a cada configuração.",
        "Nenhum modelo foi promovido e nenhuma submission foi criada.",
        "",
        f"- Protocolo SHA-256: `{audit_result['protocol_sha256']}`",
        f"- Código de geração SHA-256: `{audit_result['generator_code_sha256']}`",
        f"- Síntese SHA-256: `{audit_result['summary_sha256']}`",
        f"- Ambiente: Python {audit_result['runtime']['python']}, NumPy "
        f"{audit_result['runtime']['numpy']}, scikit-learn "
        f"{audit_result['runtime']['scikit_learn']}, LightGBM "
        f"{audit_result['runtime']['lightgbm']}.",
        f"- Auditoria: {len(audit_result['prediction_hashes'])} mapas OOF com hashes e métricas refeitas.",
        "",
    ]
    (OUT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    save_json(OUT / "decision.json", {"family_class": family_class,
                                      "followup_families": followup,
                                      "no_submission": True,
                                      "no_automatic_promotion": True})


if __name__ == "__main__":
    result = audit()
    save_json(OUT / "audit.json", result)
    report(result)
    print(json.dumps({"passed": True, "maps": len(result["prediction_hashes"]),
                      "decision": json.loads((OUT / "decision.json").read_text(encoding="utf-8"))},
                     ensure_ascii=False), flush=True)
