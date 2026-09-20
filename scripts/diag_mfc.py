r"""A convergencia de fluxo de umidade carrega informacao que a S12 nao tem?

Motivacao: seis metodos independentes de RECOMBINAR os mapas congelados
(gates logistico/ridge/HGB da Rodada 27, top-k da 28, gate convolucional da
30, recalibracao de amplitude da 31-diag) aterrissaram todos entre +0,04% e
+0,08%. Isso indica que os mapas existentes estao esgotados. A radiografia
por grupo mostrou onde ainda mora o erro: 62% do erro quadratico total esta
na faixa lat >= -10, que e so um terco das linhas da grade.

Hipotese: a convergencia de fluxo de umidade, -div(q * V) a 850 hPa, e o
diagnostico fisico padrao de precipitacao tropical. Ela e uma combinacao
NAO-LINEAR de tres variaveis que o pipeline ja usa separadamente
(`shum_850`, `u_850`, `v_850`), e que nem PLS nem arvore sobre campos brutos
constroem sozinhas.

Teste: o residuo da S12 (observado - S12) e, por definicao, o que o pipeline
NAO explicou. Se a MFC do mes de origem correlaciona com esse residuo no mes
seguinte, ela e informacao nova -- nao ha risco de estar medindo redundancia.

Controle: as mesmas correlacoes para q, u e v isoladas. Se a MFC nao superar
as tres variaveis cruas, o operador nao-linear nao esta agregando nada e a
linha se encerra.

Convencao causal identica a do pipeline: features no mes de origem `o`,
precipitacao alvo em `o + 1` (`competition.develop_ridge` usa
`origin_idx = target_idx - 1`). Climatologia de cada campo calculada so com
meses estritamente anteriores ao primeiro mes de origem do bloco.

Nao treina modelo, nao le alvo de teste, nao gera CSV, nao cria submissao.

Uso (na raiz do repositorio, com o venv ativado):

    .\.venv\Scripts\python.exe scripts\diag_mfc.py

A primeira execucao gera um cache de MFC (~313 MB, float32) em
data/processed/mfc_diagnostic/. As seguintes reaproveitam.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src import round4, round27
from src.competition import CACHE
from src.round2 import target_origins

YEARS = round27.YEARS
OUT_DIR = REPO_ROOT / 'reports' / 'competition' / 'mfc_diagnostic'
MFC_DIR = REPO_ROOT / 'data' / 'processed' / 'mfc_diagnostic'

LAT = np.arange(-60, 15.01, .25)
LON = np.arange(-90, -24.99, .25)
NLAT, NLON = LAT.size, LON.size
EARTH = 6.371e6
DPHI = DLAM = np.deg2rad(.25)
COSPHI = np.cos(np.deg2rad(LAT))[None, :, None]

SEASONS = ('DJF', 'MAM', 'JJA', 'SON')
BANDS = ('lat<-30', '-30a-10', 'lat>=-10')
SEASON_OF_MONTH = ((np.arange(24) % 12 + 1) % 12) // 3
GROUPS = [(s, b) for s in range(4) for b in range(3)]
GROUP_NAME = {(s, b): f'{SEASONS[s]}/{BANDS[b]}' for s, b in GROUPS}
FEATURES = ('shum_850', 'u_850', 'v_850', 'mfc')


def moisture_flux_convergence(u, v, q):
    """-div(q V) em coordenadas esfericas. Entradas (n, NLAT, NLON)."""
    dqu = np.gradient(q * u, DLAM, axis=2)
    dqv = np.gradient(q * v * COSPHI, DPHI, axis=1)
    return -(dqu + dqv) / (EARTH * COSPHI)


def build_mfc_cache(chunk=48):
    """Calcula a MFC de toda a serie uma vez, em blocos, e guarda em float32."""
    path = MFC_DIR / 'mfc.npy'
    if path.exists():
        return path
    MFC_DIR.mkdir(parents=True, exist_ok=True)
    u = np.load(CACHE / 'u_850.npy', mmap_mode='r')
    v = np.load(CACHE / 'v_850.npy', mmap_mode='r')
    q = np.load(CACHE / 'shum_850.npy', mmap_mode='r')
    n = u.shape[0]
    out = np.lib.format.open_memmap(path, mode='w+', dtype=np.float32,
                                    shape=(n, NLAT, NLON))
    for start in range(0, n, chunk):
        stop = min(start + chunk, n)
        out[start:stop] = moisture_flux_convergence(
            np.asarray(u[start:stop], np.float64),
            np.asarray(v[start:stop], np.float64),
            np.asarray(q[start:stop], np.float64)).astype(np.float32)
        print(f'[mfc] {stop}/{n} meses', flush=True)
    out.flush()
    del out
    return path


def band_masks():
    bands = (round4.groups()[0] % 3).reshape(-1)
    return [bands == i for i in range(3)]


def causal_anomaly(series, idx, cut):
    """Campo nos meses `idx` menos a media por mes-calendario de antes de `cut`."""
    cache: dict[int, np.ndarray] = {}
    rows = []
    for t in idx:
        c = int(t) % 12
        if c not in cache:
            sel = np.arange(c, cut, 12)
            if sel.size == 0:
                raise ValueError(f'Sem historico anterior para o mes-calendario {c}')
            cache[c] = np.asarray(series[sel], np.float64).reshape(sel.size, -1).mean(axis=0)
        rows.append(np.asarray(series[int(t)], np.float64).reshape(-1) - cache[c])
    return np.stack(rows)


def corr(x, y):
    """Pearson sobre os pontos finitos; nan se nao houver variancia."""
    good = np.isfinite(x) & np.isfinite(y)
    if good.sum() < 100:
        return float('nan')
    a, b = x[good], y[good]
    a = a - a.mean()
    b = b - b.mean()
    da, db = float(a @ a), float(b @ b)
    if da <= 0 or db <= 0:
        return float('nan')
    return float((a @ b) / np.sqrt(da * db))


def main() -> None:
    mfc_path = build_mfc_cache()
    masks = band_masks()
    tp = np.load(CACHE / 'tp.npy', mmap_mode='r')
    series = {name: np.load(CACHE / f'{name}.npy', mmap_mode='r')
              for name in FEATURES if name != 'mfc'}
    series['mfc'] = np.load(mfc_path, mmap_mode='r')

    # correl[feature][grupo] = lista de correlacoes, uma por bloco
    correl = {f: {g: [] for g in GROUPS} for f in FEATURES}

    for year in YEARS:
        origins = target_origins(year)
        truth, s12, _ = round27.source(year, tp)
        residual = (np.asarray(truth, np.float64).reshape(24, -1)
                    - np.asarray(s12, np.float64).reshape(24, -1))
        cut = int(np.min(origins))
        anomalies = {f: causal_anomaly(series[f], origins, cut) for f in FEATURES}
        for s, b in GROUPS:
            months = np.flatnonzero(SEASON_OF_MONTH == s)
            m = masks[b]
            r = residual[np.ix_(months, np.flatnonzero(m))].ravel()
            for f in FEATURES:
                a = anomalies[f][np.ix_(months, np.flatnonzero(m))].ravel()
                correl[f][(s, b)].append(corr(a, r))
        print(f'[bloco] {year} concluido', flush=True)
        del truth, s12, residual, anomalies

    print('\n=== Correlacao com o residuo da S12 (media dos seis blocos) ===')
    print(f'{"grupo":<18}' + ''.join(f'{f:>11}' for f in FEATURES) + f'{"mfc sinal":>11}')
    table = {}
    for s, b in GROUPS:
        row = {f: float(np.nanmean(correl[f][(s, b)])) for f in FEATURES}
        vals = np.array(correl['mfc'][(s, b)])
        agree = int(max((vals > 0).sum(), (vals < 0).sum()))
        row['mfc_blocos_mesmo_sinal'] = f'{agree}/{len(vals)}'
        row['mfc_por_bloco'] = [float(v) for v in vals]
        table[GROUP_NAME[(s, b)]] = row
        print(f'{GROUP_NAME[(s, b)]:<18}'
              + ''.join(f'{row[f]:>11.3f}' for f in FEATURES)
              + f'{row["mfc_blocos_mesmo_sinal"]:>11}')

    tropic = [g for g in GROUPS if g[1] == 2]
    best_raw = max(abs(np.nanmean([table[GROUP_NAME[g]][f] for g in tropic]))
                   for f in FEATURES if f != 'mfc')
    mfc_trop = abs(np.nanmean([table[GROUP_NAME[g]]['mfc'] for g in tropic]))
    print(f'\nFaixa tropical (lat >= -10), media dos quatro grupos:'
          f'\n  melhor variavel crua : |r| = {best_raw:.3f}'
          f'\n  MFC                  : |r| = {mfc_trop:.3f}')

    print('\nLeitura: a MFC so justifica uma Rodada 31 se |r| superar as variaveis'
          '\ncruas E mantiver o mesmo sinal em pelo menos 5 dos 6 blocos nos grupos'
          '\ntropicais. |r| em torno de 0,05 com sinal instavel significa que o'
          '\npipeline ja extraiu o que havia nesses campos, e a linha se encerra.')

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / 'mfc.json').write_text(json.dumps(dict(
        pergunta='A MFC carrega informacao ausente do residuo da S12?',
        convencao='features no mes de origem, alvo no mes seguinte',
        blocos=list(YEARS), features=list(FEATURES),
        correlacao_por_grupo=table,
        tropico_melhor_variavel_crua=best_raw, tropico_mfc=mfc_trop,
        treino_novo=False, alvo_de_teste_lido=False, csv_gerado=False,
    ), indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'\nGravado em {OUT_DIR / "mfc.json"}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
