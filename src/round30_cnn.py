"""Rodada 30: gate espacial convolucional entre S12 e o análogo H4.

Só roda com PyTorch e, na prática, só em GPU (Kaggle) -- ver
experiments/ROUND30_KAGGLE_SETUP.md e experiments/ROUND30.md antes de usar
este módulo. Não treina nenhum previsor de precipitação novo: reaproveita
sete mapas OOF já congelados (S12, análogo H4 e cinco componentes) e
decide, por patch espacial 2D, se o análogo deve substituir parcialmente a
S12 no norte (0-15N), como extensão direta da Rodada 27.

Este arquivo não foi executado antes de ser escrito. A primeira execução
real deve ser tratada como depuração de implementação, não como resultado
científico -- só depois de rodar sem erros e conferir os números básicos
(prevalência, formas dos arrays) o resultado de `decision()` deve ser
levado a sério.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from .competition import CACHE, ROOT, REPORT, save_json
from .round2 import target_origins
from . import round20, round25, round26, round27

OUT = REPORT / "round30"
ART = ROOT / "data/processed/round30"
PROTOCOL = ROOT / "experiments/ROUND30.md"

YEARS = round27.YEARS
EVAL = round27.EVAL
GRID = round25.GRID
SHAPE = (301, 261)
NORTH = round26.NORTH
NORTH_SIZE = round26.NORTH_SIZE
NORTH_ROWS = NORTH // SHAPE[1]
NORTH_COLS = NORTH % SHAPE[1]

PATCH = 15
HALF = PATCH // 2
CHANNELS = ("s12", "analog", "s02", "modes", "local18", "pls16", "s09")
TRAIN_SAMPLE_PER_MONTH = 2048
SEED = 20260930
EPOCHS = 15
BATCH = 512
GATE_CAPS = (0.1, 0.2, 0.3)


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
        "protocol_sha256": sha(PROTOCOL),
        "reference": "S12", "alternative": "Round25 H4 pure analog",
        "channels": list(CHANNELS), "patch_size": PATCH,
        "train_sample_per_month": TRAIN_SAMPLE_PER_MONTH, "seed": SEED,
        "epochs": EPOCHS, "batch_size": BATCH,
        "years": list(YEARS), "eval_years": list(EVAL),
        "gate_caps": list(GATE_CAPS),
        "official_only": True, "no_test_targets": True, "no_submission": True,
    }
    path = OUT / "protocol.json"
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != json.loads(json.dumps(record)):
            raise ValueError("Protocolo ou configuração da rodada 30 mudou depois de congelado")
    else:
        save_json(path, record)


def _grid(path: Path) -> np.ndarray:
    arr = np.load(path, mmap_mode="r")
    return np.asarray(arr, dtype=np.float32).reshape(24, *SHAPE)


def _load_channel_grids(year: int) -> dict[str, np.ndarray]:
    """Sete canais congelados do bloco `year`, grade cheia (24, 301, 261).

    Nenhum arquivo aqui é gerado por este módulo -- todos já existem como
    saída de rodadas anteriores (round9/round10/round20/round25).
    """
    return {
        "s12": _grid(round20.ART / f"{year}_s12.npy"),
        "analog": _grid(round25.ART / f"{year}_h4_prediction.npy"),
        "s02": _grid(ROOT / f"data/processed/round9/{year}_s02.npy"),
        "modes": _grid(ROOT / f"data/processed/round9/{year}_modes.npy"),
        "local18": _grid(ROOT / f"data/processed/round9/{year}_local18.npy"),
        "pls16": _grid(ROOT / f"data/processed/round9/{year}_pls16.npy"),
        "s09": _grid(ROOT / f"data/processed/round10/{year}_s09.npy"),
    }


def _truth_grid(year: int, tp: np.ndarray) -> np.ndarray:
    return np.asarray(tp[target_origins(year) + 1], dtype=np.float32).reshape(24, *SHAPE)


def _stack_and_pad(channel_grids: dict[str, np.ndarray]) -> np.ndarray:
    stacked = np.stack([channel_grids[name] for name in CHANNELS], axis=1)  # (24, C, 301, 261)
    return np.pad(stacked, ((0, 0), (0, 0), (HALF, HALF), (HALF, HALF)), mode="reflect")


def _labels(truth: np.ndarray, s12: np.ndarray, analog: np.ndarray) -> np.ndarray:
    """True se o análogo tem erro quadrático menor que a S12; (24, GRID)."""
    e12 = (truth.reshape(24, GRID) - s12.reshape(24, GRID)).astype(np.float64)
    ea = (truth.reshape(24, GRID) - analog.reshape(24, GRID)).astype(np.float64)
    return ea * ea < e12 * e12


def _advantage(truth: np.ndarray, s12: np.ndarray, analog: np.ndarray) -> np.ndarray:
    """D = perda_S12 - perda_análogo no norte; (24, NORTH_SIZE)."""
    e12 = (truth.reshape(24, GRID) - s12.reshape(24, GRID)).astype(np.float64)
    ea = (truth.reshape(24, GRID) - analog.reshape(24, GRID)).astype(np.float64)
    return (e12 * e12 - ea * ea)[:, NORTH]


def _block_arrays(year: int, tp: np.ndarray):
    grids = _load_channel_grids(year)
    truth = _truth_grid(year, tp)
    padded = _stack_and_pad(grids)  # (24, C, 301+2h, 261+2h)
    labels_full = _labels(truth, grids["s12"], grids["analog"])  # (24, GRID)
    labels_north = labels_full[:, NORTH]  # (24, NORTH_SIZE)
    advantage_north = _advantage(truth, grids["s12"], grids["analog"])
    return padded, labels_north, advantage_north


def _extract_patches(padded_months: np.ndarray, months: np.ndarray, rows: np.ndarray,
                     cols: np.ndarray) -> np.ndarray:
    """padded_months: (n_available_months, C, 301+2h, 261+2h).

    `rows`/`cols` são coordenadas na grade ORIGINAL (0..300 / 0..260); o
    deslocamento HALF já está embutido no recorte.
    """
    n_channels = padded_months.shape[1]
    out = np.empty((len(months), n_channels, PATCH, PATCH), dtype=np.float32)
    for i in range(len(months)):
        m, r, c = int(months[i]), int(rows[i]), int(cols[i])
        out[i] = padded_months[m, :, r:r + PATCH, c:c + PATCH]
    return out


def train_cutoff(cutoff: int, tp: np.ndarray, rng: np.random.Generator):
    """Treina causalmente nos blocos anteriores a `cutoff` e avalia OOF nele."""
    import torch
    from torch import nn

    prior = tuple(y for y in YEARS if y < cutoff)
    if not prior:
        raise ValueError(f"Sem bloco anterior para treinar o corte {cutoff}")

    train_padded_blocks = []
    train_rows, train_cols, train_month_idx, train_y = [], [], [], []
    month_cursor = 0
    for year in prior:
        padded, labels, _ = _block_arrays(year, tp)
        for m in range(24):
            train_padded_blocks.append(padded[m])
            chosen = rng.choice(NORTH_SIZE, size=min(TRAIN_SAMPLE_PER_MONTH, NORTH_SIZE),
                                replace=False)
            train_rows.append(NORTH_ROWS[chosen])
            train_cols.append(NORTH_COLS[chosen])
            train_month_idx.append(np.full(len(chosen), month_cursor, dtype=np.intp))
            train_y.append(labels[m, chosen])
            month_cursor += 1
    train_stack = np.stack(train_padded_blocks)  # (n_train_months, C, 301+2h, 261+2h)
    rows = np.concatenate(train_rows)
    cols = np.concatenate(train_cols)
    months = np.concatenate(train_month_idx)
    y = np.concatenate(train_y).astype(np.float32)
    x = _extract_patches(train_stack, months, rows, cols)
    del train_stack, train_padded_blocks

    valid_padded, valid_labels, valid_advantage = _block_arrays(cutoff, tp)
    vm = np.repeat(np.arange(24), NORTH_SIZE)
    vr = np.tile(NORTH_ROWS, 24)
    vc = np.tile(NORTH_COLS, 24)
    xv = _extract_patches(valid_padded, vm, vr, vc)
    yv = valid_labels.reshape(-1).astype(np.float32)

    mean = x.mean(axis=(0, 2, 3), keepdims=True)
    std = x.std(axis=(0, 2, 3), keepdims=True)
    std = np.where(std > 1e-6, std, 1.0)
    xz = ((x - mean) / std).astype(np.float32)
    xvz = ((xv - mean) / std).astype(np.float32)

    torch.manual_seed(SEED)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    class GateCNN(nn.Module):
        def __init__(self, c_in: int):
            super().__init__()
            self.body = nn.Sequential(
                nn.Conv2d(c_in, 32, 3, padding=1), nn.ReLU(inplace=True),
                nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(inplace=True),
                nn.AdaptiveAvgPool2d(1),
            )
            self.head = nn.Sequential(
                nn.Flatten(), nn.Linear(64, 32), nn.ReLU(inplace=True),
                nn.Dropout(0.3), nn.Linear(32, 1),
            )

        def forward(self, patch: "torch.Tensor") -> "torch.Tensor":
            return self.head(self.body(patch)).squeeze(-1)

    model = GateCNN(len(CHANNELS)).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
    loss_fn = nn.BCEWithLogitsLoss()

    xz_t = torch.from_numpy(xz)
    y_t = torch.from_numpy(y)
    n = len(y_t)
    model.train()
    for epoch in range(EPOCHS):
        order = torch.randperm(n)
        total_loss = 0.0
        for start in range(0, n, BATCH):
            idx = order[start:start + BATCH]
            xb, yb = xz_t[idx].to(device), y_t[idx].to(device)
            optimizer.zero_grad()
            out = model(xb)
            loss = loss_fn(out, yb)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(idx)
        print(f"cutoff={cutoff} epoch={epoch} loss={total_loss / n:.4f}", flush=True)

    model.eval()
    probs = np.empty(len(yv), dtype=np.float32)
    xvz_t = torch.from_numpy(xvz)
    with torch.no_grad():
        for start in range(0, len(yv), 4096):
            xb = xvz_t[start:start + 4096].to(device)
            probs[start:start + 4096] = torch.sigmoid(model(xb)).cpu().numpy()

    return probs.reshape(24, NORTH_SIZE), valid_labels, valid_advantage


def evaluate() -> None:
    locked()
    tp_path = CACHE / "tp.npy"
    if not tp_path.exists():
        raise RuntimeError(
            "tp.npy nao encontrado em " + str(tp_path) + ". No Kaggle, "
            "reconstrua o cache oficial chamando competition.audit() contra "
            "o dataset oficial anexado antes de chamar evaluate() -- ver "
            "experiments/ROUND30_KAGGLE_SETUP.md.")
    tp = np.load(tp_path, mmap_mode="r").reshape(-1, GRID)
    rng = np.random.default_rng(SEED)
    for cutoff in EVAL:
        out_path = ART / f"{cutoff}_gate_oof.npz"
        if out_path.exists() and out_path.with_suffix(".json").exists():
            print("BLOCO EXISTENTE", cutoff, flush=True)
            continue
        probs, labels, advantage = train_cutoff(cutoff, tp, rng)
        np.savez_compressed(out_path, probability=probs, winner=labels,
                            advantage=advantage.astype(np.float32))
        save_json(out_path.with_suffix(".json"), {
            "sha256": sha(out_path), "cutoff": cutoff,
            "channels": list(CHANNELS), "patch_size": PATCH,
            "no_test_targets": True,
        })
        print("GATE", cutoff,
              "prevalencia_real", float(labels.mean()),
              "prevalencia_prevista_media", float(probs.mean()), flush=True)


def decision() -> dict:
    """Reaplica a aritmética de soft gating da Rodada 27 (`round27._gating`),
    trocando a fonte da probabilidade pelo gate convolucional."""
    locked()
    tp = np.load(CACHE / "tp.npy", mmap_mode="r").reshape(-1, GRID)
    sums = {cap: {"global": [], "block": {}, "year": {}} for cap in GATE_CAPS}
    base_global = []
    block_baselines: dict[str, float] = {}
    annual_baselines: dict[str, float] = {}
    for cutoff in EVAL:
        truth, s12, analog = round27.source(cutoff, tp)
        t, p, a = (np.asarray(x, np.float64) for x in (truth, s12, analog))
        r = t - p
        rn = r[:, NORTH]
        delta = a[:, NORTH] - p[:, NORTH]
        month_base_global = np.sum(r * r, axis=1)
        month_base_north = np.sum(rn * rn, axis=1)
        base_global.extend(month_base_global.tolist())
        block_baselines[str(cutoff)] = float(month_base_global.sum())
        for k in (0, 1):
            sl = slice(12 * k, 12 * (k + 1))
            annual_baselines[str(cutoff + k)] = float(month_base_global[sl].sum())
        with np.load(ART / f"{cutoff}_gate_oof.npz") as saved:
            probability = np.asarray(saved["probability"], np.float64)
        for cap in GATE_CAPS:
            g = cap * probability
            altered = rn - g * delta
            month_north = np.sum(altered * altered, axis=1)
            month_global = month_base_global - month_base_north + month_north
            row = sums[cap]
            row["global"].extend(month_global.tolist())
            row["block"][str(cutoff)] = float(month_global.sum())
            for k in (0, 1):
                row["year"][str(cutoff + k)] = float(month_global[12 * k:12 * (k + 1)].sum())
    n_global = len(base_global) * GRID
    baseline_rmse = float(np.sqrt(sum(base_global) / n_global))
    gates = {}
    for cap, row in sums.items():
        total = float(sum(row["global"]))
        rmse = float(np.sqrt(total / n_global))
        gates[f"cnn_gate_{cap:.1f}"] = {
            "gmax": cap, "global_rmse": rmse,
            "gain_vs_s12_percent": float(100 * (1 - rmse / baseline_rmse)),
            "positive_blocks": sum(row["block"][str(y)] < block_baselines[str(y)] for y in EVAL),
            "positive_years": sum(row["year"][str(y)] < annual_baselines[str(y)]
                                  for y in range(2011, 2021)),
            "positive_months": sum(x < b for x, b in zip(row["global"], base_global)),
        }
    stable = [key for key, row in gates.items()
              if row["gain_vs_s12_percent"] >= .3 and row["positive_blocks"] >= 4
              and row["positive_years"] >= 7 and row["positive_months"] >= 67]
    if stable:
        classification, reason = "A", ("Gate convolucional supera S12 com amplitude e "
                                       "estabilidade predefinidas.")
    elif any(row["gain_vs_s12_percent"] > 0 for row in gates.values()):
        classification, reason = "D", ("Ha ganho em alguma capacidade, mas nenhuma "
                                       "satisfaz amplitude (0,3%) e estabilidade simultaneamente.")
    else:
        classification, reason = "B", "Todas as capacidades do gate convolucional pioram a S12."
    result = {
        "classification": classification, "reason": reason,
        "reference_gate_round27_percent": 0.075, "baseline_rmse": baseline_rmse,
        "gates": gates, "stable_gates": stable, "evaluation_blocks": list(EVAL),
        "no_candidate": True, "no_test_targets": True, "no_submission": True,
    }
    save_json(OUT / "decision.json", result)
    print("DECISAO", classification, reason, flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["evaluate", "decision"])
    stage = parser.parse_args().stage
    if stage == "evaluate":
        evaluate()
    else:
        decision()
