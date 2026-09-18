"""Independent audit of the final S14 experimental CSV and its components."""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path

for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"

import joblib
import numpy as np
import xarray as xr
from sklearn.linear_model import LogisticRegression

from src import round20, round25, round26, round27
from src.competition import CACHE, RAW, ROOT, save_json
from src.round2 import Features, target_origins

NAME = "S14_experimental_round27_gate"
ART = ROOT / "data/processed" / NAME
REPORT = ROOT / "reports/competition/s14_experimental_round27_gate"
CSV = ROOT / "submissions" / f"{NAME}.csv"
S12_HASH = "bba1f8b279447868170b6b2f9b18ee2cc723b891c25627c91438c7725d3aead8"
YEARS = (2009, 2011, 2013, 2015, 2017, 2019, 2021)
GRID = round25.GRID
NORTH = round26.NORTH


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fail_if(condition: bool, message: str) -> None:
    if condition:
        raise ValueError(message)


def make_x(origin: int, cells: np.ndarray, climo: np.ndarray,
           s12: np.ndarray, analog: np.ndarray) -> np.ndarray:
    month = (origin+1) % 12
    x = np.empty((len(cells), 7), np.float32)
    x[:, 0] = round25.LAT[cells]
    x[:, 1] = round25.LON[cells]
    x[:, 2] = np.sin(2*np.pi*month/12)
    x[:, 3] = np.cos(2*np.pi*month/12)
    x[:, 4] = climo[month, cells]
    x[:, 5] = s12[cells]
    x[:, 6] = analog[cells]-x[:, 5]
    return x


def audit() -> dict:
    manifest = json.loads((ART / "manifest.json").read_text(encoding="utf-8"))
    fail_if(manifest["method"] != "Round27 logistic_base_0.3" or
            manifest["gmax"] != .3 or
            manifest["training"]["last_training_target"] != "2022-12",
            "Método, peso ou corte divergente")
    fail_if(round27.BASE_COLUMNS.tolist() != [0, 1, 2, 3, 4, 5, 106],
            "Colunas da Rodada 27 divergentes")
    hash_checks = {}
    for name, relative in manifest["files"].items():
        expected = manifest["files_sha256"][name]
        actual = sha(ROOT / relative)
        fail_if(actual != expected, f"Hash divergente de {name}")
        hash_checks[name] = actual
    for name, expected in manifest["round27_oof_inputs_sha256"].items():
        if name == "s12_csv":
            path = ROOT / "submissions/submission_12.csv"
        elif name == "s12_reproduction_nc":
            path = ROOT / "data/processed/reproducao/saidas_verificadas/s12/s12_reproduction.nc"
        elif name == "official_test_features":
            path = RAW / "teste_features.nc"
        elif name == "official_sample":
            path = RAW / "sample_submission.csv"
        elif name == "official_tp_cache":
            path = CACHE / "tp.npy"
        else:
            year, kind = name.split("_", 1)
            path = round20.ART / f"{year}_s12.npy" if kind == "s12" else \
                   round25.ART / f"{year}_h4_prediction.npy"
        fail_if(sha(path) != expected, f"Insumo mudou: {name}")
    fail_if(sha(ROOT / "submissions/submission_12.csv") != S12_HASH,
            "S12 oficial foi alterada")
    with xr.open_dataset(ROOT / "data/processed/reproducao/saidas_verificadas/s12/s12_reproduction.nc") as ds:
        s12 = np.load(round20.ART / "2023_s12.npy").reshape(24, GRID)
        np.testing.assert_array_equal(s12.reshape(24, 301, 261), ds.tp_mm_day.values)
    with xr.open_dataset(RAW / "teste_features.nc") as ds:
        fail_if(not np.isnan(ds.tp_alvo.values).all(), "Alvos 2023/24 não ausentes")
    f = Features(2023, final=True)
    tp = np.load(CACHE / "tp.npy", mmap_mode="r").reshape(-1, GRID)
    fail_if(tp.shape != (996, GRID), "Histórico ultrapassa dezembro de 2022")
    with np.load(ART / "gate_training.npz") as saved:
        xtrain = np.asarray(saved["x"])
        ytrain = np.asarray(saved["y"])
    fail_if(xtrain.shape != (len(YEARS)*24*512, 7) or ytrain.shape != (len(xtrain),),
            "Dimensão do treino inesperada")
    for block, year in enumerate(YEARS):
        historical_s12 = np.load(round20.ART / f"{year}_s12.npy", mmap_mode="r").reshape(24, GRID)
        analog_path = (ART / "2021_analog_h4.npy" if year == 2021 else
                       round25.ART / f"{year}_h4_prediction.npy")
        historical_analog = np.load(analog_path, mmap_mode="r").reshape(24, GRID)
        for slot, origin in enumerate(target_origins(year)):
            cells = round26._sample_cells(int(origin))
            sl = slice((block*24+slot)*512, (block*24+slot+1)*512)
            reconstructed = make_x(int(origin), cells, f.climo,
                                   historical_s12[slot], historical_analog[slot])
            np.testing.assert_array_equal(xtrain[sl], reconstructed)
            r12 = (tp[origin+1, cells]-reconstructed[:, 5]).astype(np.float32)
            ra = (r12+reconstructed[:, 5]-historical_analog[slot, cells]).astype(np.float64)
            np.testing.assert_array_equal(ytrain[sl], ra**2 < r12.astype(np.float64)**2)
    gate = joblib.load(ART / "gate.joblib")
    model = gate["model"]
    params = model.get_params()
    fail_if(params["C"] != .3 or params["solver"] != "lbfgs" or
            params["max_iter"] != 200 or params["tol"] != 1e-4 or
            gate["base_columns_round27"] != [0, 1, 2, 3, 4, 5, 106],
            "Hiperparâmetros do gate mudaram")
    mean = xtrain.mean(axis=0, dtype=np.float64)
    std = np.where(xtrain.std(axis=0, dtype=np.float64) > 1e-6,
                   xtrain.std(axis=0, dtype=np.float64), 1.)
    np.testing.assert_array_equal(mean, gate["mean"])
    np.testing.assert_array_equal(std, gate["sd"])
    ztrain = ((xtrain-mean)/std).astype(np.float32)
    independent_model = LogisticRegression(C=.3, max_iter=200, solver="lbfgs", tol=1e-4)
    independent_model.fit(ztrain, ytrain)
    np.testing.assert_array_equal(independent_model.coef_, model.coef_)
    np.testing.assert_array_equal(independent_model.intercept_, model.intercept_)
    analog = np.load(ART / "2023_analog_h4.npy").reshape(24, GRID)
    saved_probability = np.load(ART / "probability_north.npy")
    fail_if(saved_probability.shape != (24, len(NORTH)), "Shape das probabilidades")
    calculated = s12.astype(np.float64).copy()
    pmin, pmax = 1., 0.
    for slot, origin in enumerate(target_origins(2023)):
        x = make_x(int(origin), NORTH, f.climo, s12[slot], analog[slot])
        z = ((x-mean)/std).astype(np.float32)
        p = independent_model.predict_proba(z)[:, 1].astype(np.float32)
        np.testing.assert_array_equal(saved_probability[slot], p)
        g = .3*p.astype(np.float64)
        pmin = min(pmin, float(g.min()))
        pmax = max(pmax, float(g.max()))
        fail_if(np.min(g) < 0 or np.max(g) > .3, "Peso fora de [0,0.3]")
        calculated[slot, NORTH] = s12[slot, NORTH].astype(np.float64)+g*(
            analog[slot, NORTH].astype(np.float64)-s12[slot, NORTH].astype(np.float64))
    saved_prediction = np.load(ART / "prediction.npy").reshape(24, GRID)
    np.testing.assert_array_equal(saved_prediction, calculated)
    rest = np.setdiff1d(np.arange(GRID), NORTH)
    np.testing.assert_array_equal(saved_prediction[:, rest], s12[:, rest].astype(np.float64))
    fail_if(not np.isfinite(saved_prediction).all() or np.min(saved_prediction) < 0,
            "Saída não finita ou negativa")
    expected_flat = calculated.ravel()
    ids = set()
    count = 0
    with (RAW / "sample_submission.csv").open("r", newline="", encoding="utf-8") as official, \
         CSV.open("r", newline="", encoding="utf-8") as candidate:
        template = csv.reader(official)
        output = csv.reader(candidate)
        fail_if(next(template) != ["id", "tp_mm_day"] or
                next(output) != ["id", "tp_mm_day"], "Cabeçalho divergente")
        for template_row, output_row in zip(template, output, strict=True):
            fail_if(len(template_row) != 2 or len(output_row) != 2,
                    f"CSV malformado na linha {count+2}")
            fail_if(template_row[0] != output_row[0], f"ID ou ordem incorreta na linha {count+2}")
            fail_if(output_row[0] in ids, f"ID duplicado na linha {count+2}")
            ids.add(output_row[0])
            fail_if(count >= expected_flat.size, "CSV tem linhas extras")
            fail_if(output_row[1] != f"{expected_flat[count]:.8f}",
                    f"Valor não reproduz a fórmula e formato na linha {count+2}")
            count += 1
    fail_if(count != expected_flat.size, "Contagem de linhas divergente")
    validation = json.loads((ART / "validation.json").read_text(encoding="utf-8"))
    delta = calculated-s12.astype(np.float64)
    rms = float(np.sqrt(np.mean(delta*delta)))
    fail_if(not np.isclose(rms, validation["change_vs_s12"]["all_global"]["rms_change"]),
            "RMS reportado incorreto")
    result = {
        "passed": True, "method": "Round27 logistic_base_0.3",
        "manifest_sha256": sha(ART / "manifest.json"),
        "audit_code_sha256": sha(Path(__file__)),
        "checked_file_sha256": hash_checks,
        "s12_original_sha256": S12_HASH,
        "s12_reproduction_equal": True,
        "historical_train_rows_verified": int(len(xtrain)),
        "historical_last_target": "2022-12",
        "test_targets_all_nan": True,
        "logistic_parameters_and_refit_equal": True,
        "probabilities_recomputed_equal": True,
        "formula_array_equal": True,
        "outside_north_exactly_s12": True,
        "g_min": pmin, "g_max": pmax, "g_bound": .3,
        "csv_matches_formula_eight_decimals": True,
        "csv_ids_unique_and_official_order": True,
        "csv_rows": count, "csv_sha256": sha(CSV),
        "rms_change_global": rms,
        "uploaded": False, "official_reference": "S12",
    }
    REPORT.mkdir(parents=True, exist_ok=True)
    save_json(REPORT / "AUDIT.json", result)
    return result


def write_report(audit_result: dict) -> None:
    m = json.loads((ART / "manifest.json").read_text(encoding="utf-8"))
    v = json.loads((ART / "validation.json").read_text(encoding="utf-8"))
    c = v["change_vs_s12"]
    def row(key: str) -> str:
        item = c[key]
        return f"| {key} | {item['rms_change']:.6f} | {item['max_absolute_change']:.6f} | {item['changed_fraction']:.4%} |"
    lines = [
        "# S14_experimental_round27_gate — leaderboard probe",
        "",
        "Submission **experimental / não promovida**. A referência oficial permanece S12.",
        "O objetivo é obter uma observação externa depois de várias rodadas históricas reutilizadas;",
        "nenhum score de leaderboard foi consultado durante a geração.",
        "",
        "## Evidência e escolha congelada",
        "",
        "Na janela OOF 2011–2020 da Rodada 27, S12 teve RMSE 1,756391 e",
        "`logistic_base_0.3` teve 1,755065: ganho 0,075%, 4/5 blocos,",
        "6/10 anos e 67/120 meses positivos. O gate histórico exigia pelo",
        "menos 0,3% global, além de estabilidade. O ganho observado foi",
        "insuficiente; a classificação permaneceu D. O melhor valor veio de",
        "uma tabela de alternativas, com viés de seleção acumulado.",
        "O score público conhecido de S12 é 1,71456, relatado pelo usuário;",
        "nenhum score público desta probe está disponível no momento.",
        "",
        "## Configuração final",
        "",
        "- Analog: H4 puro da Rodada 25, 10 vizinhos sazonais, média uniforme",
        "  das anomalias, climatologia de 60 anos. A reconstrução de 2019–20",
        "  foi idêntica ao arquivo congelado.",
        "- Gate: regressão logística L2 `C=0.3`, `lbfgs`, 200 iterações no",
        "  máximo, tolerância `1e-4`; latitude, longitude, seno/cosseno do mês,",
        "  climatologia, S12 e Analog−S12; padronização pelo treino.",
        "- Treino final: 86.016 linhas (512 células norte × 24 meses × 7 blocos),",
        "  OOF 2009–2022. O Analog 2021–22 foi gerado com o mesmo H4 e corte 2021.",
        "  Toda climatologia e padronização final usa informação disponível",
        "  até dezembro de 2022. Os alvos de 2023–24 no arquivo oficial são NaN.",
        "- Inferência: `g=0.3×P(Analog vence S12)` apenas nas 15.921 células",
        "  de 0–15°N; no restante, S12 exatamente. A saída é um blend convexo",
        "  de previsões não negativas, sem clipping adicional.",
        "",
        "## Arquivo e validações",
        "",
        f"- CSV: `submissions/{NAME}.csv`",
        f"- SHA-256: `{m['files_sha256']['csv']}`",
        f"- Linhas: {audit_result['csv_rows']:,}; IDs únicos na ordem exata do sample oficial.",
        f"- Previsão: mínimo {v['prediction']['min']:.6f}, máximo {v['prediction']['max']:.6f}, "
        f"média {v['prediction']['mean']:.6f}, desvio {v['prediction']['std']:.6f} mm/dia.",
        f"- Quantis: `{json.dumps(v['prediction']['quantiles'], ensure_ascii=False)}`",
        f"- Pesos no norte: mínimo {audit_result['g_min']:.8f}, máximo {audit_result['g_max']:.8f}; limite 0,3.",
        "- Ausência de NaN, infinito, IDs duplicados e valores negativos confirmada.",
        "- O auditor refez o treino a partir das linhas históricas, ajustou",
        "  novamente a logística, refez probabilidades e fórmula, e comparou",
        "  cada valor do CSV com a saída formatada em oito casas decimais.",
        "",
        "| Período e região | RMS mudança (mm/dia) | Máx. absoluta | Fração alterada |",
        "| --- | ---: | ---: | ---: |",
        *[row(key) for key in ("all_global", "2023_global", "2024_global", "all_north",
                              "all_rest", "2023_north", "2023_rest", "2024_north", "2024_rest")],
        "",
        "| Faixa de latitude | Células | RMS mudança (mm/dia) | Média absoluta (mm/dia) |",
        "| --- | ---: | ---: | ---: |",
        *[f"| {name}° | {item['cells']:,} | {item['rms_change']:.6f} | "
          f"{item['mean_absolute_change']:.6f} |"
          for name, item in v["latitude_bands"].items()],
        "",
        "Os quantis completos e a distribuição espacial em precisão integral",
        "constam em `data/processed/S14_experimental_round27_gate/validation.json`.",
        "",
        "## Rastreabilidade e limites",
        "",
        f"- Protocolo SHA-256: `{m['files_sha256']['protocol']}`",
        f"- Código de geração SHA-256: `{m['files_sha256']['builder']}`",
        f"- Manifesto SHA-256: `{audit_result['manifest_sha256']}`",
        f"- Auditoria SHA-256: `{sha(REPORT / 'AUDIT.json')}`",
        f"- S12 oficial SHA-256: `{S12_HASH}`; reprodução byte a byte confirmada.",
        f"- Geração UTC: {m['created_utc']}.",
        "- O manifesto lista hashes das previsões, treino, modelo, transformações",
        "  PCA, dados oficiais, códigos e CSV. Não houve upload automático.",
        "- A probe pública é informação exploratória sujeita ao conjunto",
        "  visível e ao histórico de escolhas. Melhora pública não promove",
        "  automaticamente a candidata, nem altera o gate histórico.",
        "",
        "Esta submission não altera a referência oficial S12 e não satisfaz o gate histórico de promoção.",
        "",
    ]
    (REPORT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    result = audit()
    write_report(result)
    print(json.dumps({"passed": result["passed"], "csv_sha256": result["csv_sha256"],
                      "rows": result["csv_rows"], "rms_change": result["rms_change_global"]}), flush=True)
