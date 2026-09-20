"""Rodada 32: U-Net causal prevendo precipitação a partir dos campos oficiais.

Primeiro previsor base novo desde a S12. Não recebe nenhum mapa OOF de
rodada anterior: a entrada são os nove campos atmosféricos oficiais em
anomalia padronizada nos meses `o`, `o-1` e `o-2`, mais climatologia,
latitude e o mês-alvo; a saída é o resíduo de precipitação do mês `o+1`
contra a climatologia. Ver experiments/ROUND32.md antes de usar.

Distinção em relação à Rodada 30: lá a rede era um classificador escolhendo
entre dois mapas prontos e só podia rearranjar previsões existentes. Aqui a
rede lê campos atmosféricos brutos e emite precipitação.

`evaluate()` exige PyTorch e, na prática, GPU (Kaggle). `decision()` só usa
numpy e roda localmente sobre os `.npy` já gerados.

Este arquivo não foi executado antes de ser escrito. A primeira execução
deve ser tratada como depuração: confira as formas dos arrays, a perda de
validação interna e o RMSE da climatologia antes de levar `decision()` a
sério.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from .competition import (CACHE, ROOT, REPORT, VARIABLES, dates,
                          fit_climatology, month_number, save_json,
                          training_pairs)
from .round2 import target_origins
from . import round20, round27

OUT = REPORT / "round32"
ART = ROOT / "data/processed/round32"
PROTOCOL = ROOT / "experiments/ROUND32.md"

YEARS = round27.YEARS
EVAL = round27.EVAL
SHAPE = (301, 261)
PADDED = (304, 264)          # múltiplo de 4 para os dois níveis de pooling

LAGS = (0, 1, 2)
N_DYNAMIC = len(VARIABLES) * len(LAGS)      # 27
N_STATIC = 4                                # climatologia, latitude, sin, cos
N_CHANNELS = N_DYNAMIC + N_STATIC           # 31

CROP = 64
BATCH = 32
STEPS_PER_EPOCH = 400
MAX_EPOCHS = 25
PATIENCE = 5
LR = 1e-3
WEIGHT_DECAY = 1e-4
SEED = 20261001
INNER_VALID_MONTHS = 24
CLIMATOLOGY_YEARS = 60
BLEND_FIXED = 0.5

_TIMES = None
_MONTH_OF = None


def _times():
    global _TIMES, _MONTH_OF
    if _TIMES is None:
        _TIMES = dates()
        _MONTH_OF = month_number(_TIMES)
    return _TIMES


def _month_of(index: int) -> int:
    _times()
    return int(_MONTH_OF[index])


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
        "reference": "S12", "target": "tp residual vs causal climatology",
        "variables": list(VARIABLES), "lags": list(LAGS),
        "channels": N_CHANNELS, "crop": CROP, "batch": BATCH,
        "steps_per_epoch": STEPS_PER_EPOCH, "max_epochs": MAX_EPOCHS,
        "patience": PATIENCE, "lr": LR, "weight_decay": WEIGHT_DECAY,
        "seed": SEED, "inner_valid_months": INNER_VALID_MONTHS,
        "climatology_years": CLIMATOLOGY_YEARS,
        "training_start": "1981-01-01 (competition.training_pairs)",
        "years": list(YEARS), "eval_years": list(EVAL),
        "frozen_maps_as_input": False,
        "official_only": True, "no_test_targets": True, "no_submission": True,
    }
    path = OUT / "protocol.json"
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != json.loads(json.dumps(record)):
            raise ValueError("Protocolo ou configuração da rodada 32 mudou depois de congelado")
    else:
        save_json(path, record)


# --------------------------------------------------------------------------
# Preparação causal dos dados
# --------------------------------------------------------------------------

def _targets(year: int) -> np.ndarray:
    return target_origins(year) + 1


def _cutoff(year: int) -> int:
    """Índice do primeiro mês-alvo do bloco: nada daqui em diante entra no treino."""
    return int(_targets(year).min())


def standardized_fields(cutoff: int, n_months: int) -> np.ndarray:
    """(n_months, 9, 301, 261) float16: anomalia padronizada por mês-calendário.

    Médias e desvios vêm SÓ de meses estritamente anteriores a `cutoff`.
    float16 só é seguro porque o array já está padronizado: pressão bruta em
    Pa (~1e5) estouraria o alcance do formato.
    """
    out = np.empty((n_months, len(VARIABLES), *SHAPE), np.float16)
    for j, name in enumerate(VARIABLES):
        series = np.asarray(np.load(CACHE / f"{name}.npy", mmap_mode="r")[:n_months], np.float32)
        for c in range(12):
            history = np.arange(c, cutoff, 12)
            if history.size == 0:
                raise ValueError(f"Sem histórico anterior para o mês-calendário {c}")
            block = series[history].astype(np.float64)
            mean = np.nanmean(block, axis=0)
            std = np.nanstd(block, axis=0)
            std = np.where(np.isfinite(std) & (std > 1e-8), std, 1.0)
            use = np.arange(c, n_months, 12)
            values = (series[use].astype(np.float64) - mean) / std
            out[use, j] = np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float16)
            del block, values
        del series
        print(f"[campos] {name} padronizado", flush=True)
    return out


def static_stack(climo: np.ndarray) -> np.ndarray:
    """(12, 4, 301, 261): climatologia do mês-alvo, latitude, seno e cosseno."""
    lat = np.broadcast_to(np.arange(-60, 15.01, .25, dtype=np.float32)[:, None], SHAPE) / 60.0
    rows = []
    for m in range(12):
        angle = 2 * np.pi * m / 12
        rows.append(np.stack([
            climo[m].astype(np.float32) / 5.0,
            np.asarray(lat, np.float32),
            np.full(SHAPE, np.sin(angle), np.float32),
            np.full(SHAPE, np.cos(angle), np.float32)]))
    return np.stack(rows)


def assemble(fields, statics, origins, rows=None, cols=None, size=None):
    """Empilha os 31 canais. Com `rows`/`cols`/`size`, recorta direto (barato)."""
    origins = np.asarray(origins, int)
    n = origins.size
    h, w = (size, size) if size else SHAPE
    out = np.empty((n, N_CHANNELS, h, w), np.float32)
    nv = len(VARIABLES)
    for k in range(n):
        o = int(origins[k])
        r = int(rows[k]) if rows is not None else 0
        c = int(cols[k]) if cols is not None else 0
        for i, lag in enumerate(LAGS):
            out[k, i * nv:(i + 1) * nv] = fields[o - lag][:, r:r + h, c:c + w]
        out[k, N_DYNAMIC:] = statics[_month_of(o + 1)][:, r:r + h, c:c + w]
    return out


def pad_spec():
    """Padding reflexivo até um múltiplo de 4, exigido pelos dois poolings."""
    return ((0, 0), (0, 0), (0, PADDED[0] - SHAPE[0]), (0, PADDED[1] - SHAPE[1]))


def residual_of(tp, climo, origins) -> np.ndarray:
    """Resíduo observado dos alvos `origins + 1`. (n, 301, 261) float32."""
    targets = np.asarray(origins, int) + 1
    truth = np.asarray(tp[targets], np.float32)
    _times()
    return truth - climo[_MONTH_OF[targets]]


# --------------------------------------------------------------------------
# Modelo
# --------------------------------------------------------------------------

def build_unet(torch, nn):
    def block(cin, cout):
        return nn.Sequential(
            nn.Conv2d(cin, cout, 3, padding=1), nn.GroupNorm(8, cout), nn.ReLU(inplace=True),
            nn.Conv2d(cout, cout, 3, padding=1), nn.GroupNorm(8, cout), nn.ReLU(inplace=True))

    class UNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.enc1 = block(N_CHANNELS, 32)
            self.enc2 = block(32, 64)
            self.mid = block(64, 128)
            self.dec2 = block(128 + 64, 64)
            self.dec1 = block(64 + 32, 32)
            self.head = nn.Conv2d(32, 1, 1)
            self.pool = nn.MaxPool2d(2)
            self.up = nn.Upsample(scale_factor=2, mode="nearest")

        def forward(self, x):
            e1 = self.enc1(x)
            e2 = self.enc2(self.pool(e1))
            m = self.mid(self.pool(e2))
            d2 = self.dec2(torch.cat([self.up(m), e2], dim=1))
            d1 = self.dec1(torch.cat([self.up(d2), e1], dim=1))
            return self.head(d1)[:, 0]

    return UNet()


# --------------------------------------------------------------------------
# Treino e previsão
# --------------------------------------------------------------------------

def train_cutoff(year: int):
    """Treina a U-Net com dados estritamente anteriores ao bloco `year`."""
    import torch
    from torch import nn

    times = _times()
    cutoff = _cutoff(year)
    origins = target_origins(year)
    n_months = int(origins.max()) + 1

    tp = np.load(CACHE / "tp.npy", mmap_mode="r")
    climo = fit_climatology(np.asarray(tp[:cutoff], np.float32), times[:cutoff],
                            times[cutoff], CLIMATOLOGY_YEARS)
    statics = static_stack(climo)
    fields = standardized_fields(cutoff, n_months + 1)

    usable = training_pairs(times, times[cutoff])
    usable = usable[usable >= max(LAGS)]
    if usable.size <= INNER_VALID_MONTHS + 12:
        raise ValueError(f"Treino insuficiente para o corte {year}")
    train_months, valid_months = usable[:-INNER_VALID_MONTHS], usable[-INNER_VALID_MONTHS:]

    train_residual = residual_of(tp, climo, train_months)
    scale = float(np.std(train_residual))
    train_residual /= scale
    # Grade cheia precisa de padding: 301 e 261 não são múltiplos de 4 e as
    # conexões de salto não casariam depois de dois poolings. Os recortes de
    # treino são 64x64 e não passam por aqui.
    valid_x = np.pad(assemble(fields, statics, valid_months), pad_spec(), mode="reflect")
    valid_y = residual_of(tp, climo, valid_months) / scale

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(SEED)
    rng = np.random.default_rng(SEED)
    model = build_unet(torch, nn).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    loss_fn = nn.MSELoss()

    best, best_state, waited, history = float("inf"), None, 0, []
    for epoch in range(MAX_EPOCHS):
        model.train()
        running = 0.0
        for _ in range(STEPS_PER_EPOCH):
            pick = rng.integers(0, train_months.size, BATCH)
            rows = rng.integers(0, SHAPE[0] - CROP + 1, BATCH)
            cols = rng.integers(0, SHAPE[1] - CROP + 1, BATCH)
            xb = assemble(fields, statics, train_months[pick], rows, cols, CROP)
            yb = np.empty((BATCH, CROP, CROP), np.float32)
            for k in range(BATCH):
                r, c = int(rows[k]), int(cols[k])
                yb[k] = train_residual[pick[k], r:r + CROP, c:c + CROP]
            xt = torch.from_numpy(xb).to(device)
            yt = torch.from_numpy(yb).to(device)
            optimizer.zero_grad()
            loss = loss_fn(model(xt), yt)
            loss.backward()
            optimizer.step()
            running += float(loss.detach())
        model.eval()
        chunks = []
        with torch.no_grad():
            for i in range(0, valid_months.size, 2):
                xv = torch.from_numpy(valid_x[i:i + 2]).to(device)
                yv = torch.from_numpy(valid_y[i:i + 2]).to(device)
                out = model(xv)[:, :SHAPE[0], :SHAPE[1]]
                chunks.append(float(loss_fn(out, yv)))
        vloss = float(np.mean(chunks))
        history.append({"epoch": epoch, "train": running / STEPS_PER_EPOCH, "valid": vloss})
        print(f"corte={year} epoca={epoch} treino={running / STEPS_PER_EPOCH:.4f} "
              f"validacao_interna={vloss:.4f}", flush=True)
        if vloss < best - 1e-5:
            best, waited = vloss, 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            waited += 1
            if waited >= PATIENCE:
                print(f"corte={year} parada antecipada na epoca {epoch}", flush=True)
                break
    if best_state is not None:
        model.load_state_dict(best_state)

    info = {"cutoff": year, "train_months": int(train_months.size),
            "inner_valid_months": int(valid_months.size), "residual_scale": scale,
            "best_inner_valid": best, "epochs_run": len(history), "history": history,
            "last_training_target": str(times[int(train_months.max()) + 1].date())}
    return model, fields, statics, climo, scale, info


def predict_block(model, fields, statics, climo, scale, year: int) -> np.ndarray:
    """Previsão de grade cheia para os 24 meses-alvo do bloco."""
    import torch

    device = next(model.parameters()).device
    origins = target_origins(year)
    x = np.pad(assemble(fields, statics, origins), pad_spec(), mode="reflect")
    model.eval()
    pieces = []
    with torch.no_grad():
        for i in range(0, origins.size, 2):
            pieces.append(model(torch.from_numpy(x[i:i + 2]).to(device)).cpu().numpy())
    residual = np.concatenate(pieces)[:, :SHAPE[0], :SHAPE[1]] * scale
    _times()
    base = climo[_MONTH_OF[origins + 1]]
    return np.maximum(base + residual, 0.0).astype(np.float32)


def evaluate() -> None:
    locked()
    for year in YEARS:
        path = ART / f"{year}_unet.npy"
        if path.exists():
            print(f"BLOCO EXISTENTE {year}", flush=True)
            continue
        print(f"INICIANDO BLOCO {year}", flush=True)
        model, fields, statics, climo, scale, info = train_cutoff(year)
        prediction = predict_block(model, fields, statics, climo, scale, year)
        np.save(path, prediction)
        save_json(ART / f"{year}_unet.json", info)
        print(f"BLOCO CONCLUIDO {year} rmse_interno={info['best_inner_valid']:.4f}", flush=True)
        del model, fields, statics, climo


# --------------------------------------------------------------------------
# Decisão (só numpy; roda local)
# --------------------------------------------------------------------------

def _blend_weight(years) -> float:
    """Peso causal: minimiza ||verdade - ((1-w)*s12 + w*unet)||."""
    num = den = 0.0
    tp = np.load(CACHE / "tp.npy", mmap_mode="r")
    for year in years:
        truth = np.asarray(tp[_targets(year)], np.float64)
        s12 = np.asarray(round20.reference(year), np.float64).reshape(24, *SHAPE)
        unet = np.asarray(np.load(ART / f"{year}_unet.npy"), np.float64)
        delta = unet - s12
        num += float(np.sum(delta * (truth - s12)))
        den += float(np.sum(delta * delta))
    return float(np.clip(num / den, 0.0, 1.0)) if den > 0 else 0.0


def decision() -> dict:
    tp = np.load(CACHE / "tp.npy", mmap_mode="r")
    monthly: dict[str, list[float]] = {}
    weights = {}
    for year in EVAL:
        truth = np.asarray(tp[_targets(year)], np.float64)
        s12 = np.asarray(round20.reference(year), np.float64).reshape(24, *SHAPE)
        unet = np.asarray(np.load(ART / f"{year}_unet.npy"), np.float64)
        w = _blend_weight([y for y in YEARS if y < year])
        weights[year] = w
        variants = {"s12": s12, "unet": unet,
                    f"blend_{BLEND_FIXED:g}": (1 - BLEND_FIXED) * s12 + BLEND_FIXED * unet,
                    "blend_causal": (1 - w) * s12 + w * unet}
        for name, pred in variants.items():
            monthly.setdefault(name, []).extend(
                np.mean((np.maximum(pred, 0.0) - truth) ** 2, axis=(1, 2)).tolist())

    base = np.asarray(monthly["s12"])
    rmse_s12 = float(np.sqrt(base.mean()))
    rows = {}
    for name, values in monthly.items():
        v = np.asarray(values)
        rows[name] = {
            "rmse": float(np.sqrt(v.mean())),
            "gain_vs_s12_percent": 100.0 * (1.0 - np.sqrt(v.mean()) / rmse_s12),
            "positive_blocks": int(np.sum(v.reshape(-1, 24).mean(axis=1)
                                          < base.reshape(-1, 24).mean(axis=1))),
            "positive_years": int(np.sum(v.reshape(-1, 12).mean(axis=1)
                                         < base.reshape(-1, 12).mean(axis=1))),
            "positive_months": int(np.sum(v < base)),
        }
    stable = [n for n, r in rows.items()
              if n != "s12" and r["gain_vs_s12_percent"] >= 0.3
              and r["positive_blocks"] >= 4 and r["positive_years"] >= 7
              and r["positive_months"] >= 67]
    if stable:
        cls, why = "A", "Alguma variante atinge amplitude e estabilidade exigidas."
    elif all(r["gain_vs_s12_percent"] <= 0 for n, r in rows.items() if n != "s12"):
        cls, why = "B", "Toda variante piora a S12."
    else:
        cls, why = "D", "Ha ganho, mas sem amplitude (0,3%) e estabilidade simultaneas."

    result = {"classification": cls, "reason": why, "baseline_rmse": rmse_s12,
              "variants": rows, "stable_variants": stable,
              "causal_blend_weights": weights, "evaluation_blocks": list(EVAL),
              "no_candidate": not stable, "no_test_targets": True, "no_submission": True}
    OUT.mkdir(parents=True, exist_ok=True)
    save_json(OUT / "decision.json", result)
    print("DECISAO", cls, why, flush=True)
    print(json.dumps(rows, indent=2), flush=True)
    return result


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("evaluate", "decision"))
    globals()[parser.parse_args().stage]()
