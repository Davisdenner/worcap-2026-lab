r"""Quanto do teto de 0,760% e recuperavel com um estimador regularizado?

O `diag_slope.py` mostrou que recalibrar a amplitude da anomalia por grupo
vale +0,760% no limite oracle, mas -0,194% com 12 pares (a, b) livres
estimados em um a cinco blocos anteriores. O sinal existe; o estimador e
que tem variancia demais. Este script mede quanto sobra depois de
regularizar, e onde exatamente o ganho mora.

Duas saidas:

  1. Radiografia por grupo (3 bandas x 4 estacoes): fatia do erro quadratico
     total, RMSE da S12 contra RMSE da climatologia pura, em quantos blocos
     a climatologia ja vence a S12, o slope agrupado e o fator de
     encolhimento. Tudo calculado a partir de estatisticas suficientes.

  2. Comparacao de variantes na mesma moeda das rodadas 27-30, todas
     causais (coeficientes de cada bloco vem SO de blocos anteriores),
     exceto o oracle, que e o teto.

Estimador regularizado: sem intercepto, um unico slope por grupo. O slope
agrupado dos blocos anteriores e encolhido em direcao a 1 por
`lambda = d^2 / (d^2 + se^2)`, onde `d = a_agrupado - 1` e `se` e o erro
padrao das estimativas MENSAIS do proprio grupo (o mes e a unidade de
amostragem, nao o pixel, porque pixels do mesmo mes nao sao independentes).
Grupos cujos blocos anteriores discordam ficam com a ~ 1, isto e, S12
intacta. O resultado e truncado em [0, 1.5]: 0 e climatologia pura, e o teto
de 1.5 e uma guarda contra as estimativas extremas (1.85) vistas no
diagnostico anterior -- limite escolhido DEPOIS de ver aquela tabela, o que
torna este script um diagnostico, nao uma rodada de promocao.

Nao treina modelo, nao le alvo de teste, nao gera CSV, nao cria submissao.

Uso (na raiz do repositorio, com o venv ativado):

    .\.venv\Scripts\python.exe scripts\diag_shrink.py
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
EVAL = round27.EVAL
OUT_DIR = REPO_ROOT / 'reports' / 'competition' / 'slope_diagnostic'

SEASONS = ('DJF', 'MAM', 'JJA', 'SON')
BANDS = ('lat<-30', '-30a-10', 'lat>=-10')
SEASON_OF_MONTH = ((np.arange(24) % 12 + 1) % 12) // 3
GROUPS = [(s, b) for s in range(4) for b in range(3)]
GROUP_NAME = {(s, b): f'{SEASONS[s]}/{BANDS[b]}' for s, b in GROUPS}
CLIP = (0.0, 1.5)


def band_masks():
    """As 3 bandas de latitude de `round4.groups()`, constantes no tempo."""
    bands = (round4.groups()[0] % 3).reshape(-1)
    return [bands == i for i in range(3)]


def causal_climatology(tp, target_idx):
    """Media por mes-calendario usando SO meses estritamente anteriores ao bloco."""
    cut = int(np.min(target_idx))
    cache: dict[int, np.ndarray] = {}
    rows = []
    for t in target_idx:
        c = int(t) % 12
        if c not in cache:
            sel = np.arange(c, cut, 12)
            if sel.size == 0:
                raise ValueError(f'Sem historico anterior para o mes-calendario {c}')
            cache[c] = np.asarray(tp[sel], np.float64).reshape(sel.size, -1).mean(axis=0)
        rows.append(cache[c])
    return np.stack(rows)


def block_arrays(year, tp):
    truth, s12, _ = round27.source(year, tp)
    t = np.asarray(truth, np.float64).reshape(24, -1)
    p = np.asarray(s12, np.float64).reshape(24, -1)
    return t, p, causal_climatology(tp, target_origins(year) + 1)


def stats_of(f, y):
    """n, Sff, Sfy, Syy -- suficientes para slope sem intercepto e para SSE."""
    return np.array([f.size, float(f @ f), float(f @ y), float(y @ y)])


def slope(s):
    return float(s[2] / s[1]) if s[1] > 0 else 1.0


def sse_s12(s):
    """Sum (f - y)^2 = Sff - 2 Sfy + Syy."""
    return float(s[1] - 2 * s[2] + s[3])


def sse_clim(s):
    """Sum (0 - y)^2 = Syy."""
    return float(s[3])


def group_stats(mstats, years, s, b):
    out = np.zeros(4)
    for y in years:
        for j in range(24):
            if SEASON_OF_MONTH[j] == s:
                out += mstats[y][j, b]
    return out


def monthly_slopes(mstats, years, s, b):
    return np.array([slope(mstats[y][j, b]) for y in years
                     for j in range(24) if SEASON_OF_MONTH[j] == s])


def shrink(pooled, monthly):
    """Devolve (a_final, lambda). lambda=0 significa deixar a S12 intacta."""
    a = slope(pooled)
    if monthly.size < 2:
        return 1.0, 0.0
    se2 = float(np.var(monthly, ddof=1)) / monthly.size
    d = a - 1.0
    lam = float(d * d / (d * d + se2)) if (d * d + se2) > 0 else 0.0
    return float(np.clip(1.0 + lam * d, *CLIP)), lam


def coefficients(mstats, prior, mode):
    """Um slope por grupo, a partir SOMENTE dos blocos em `prior`."""
    coef, lam = {}, {}
    if mode == 'global':
        pooled = sum(group_stats(mstats, prior, s, b) for s, b in GROUPS)
        monthly = np.concatenate([monthly_slopes(mstats, prior, s, b) for s, b in GROUPS])
        a, l = shrink(pooled, monthly)
        return {g: a for g in GROUPS}, {g: l for g in GROUPS}
    for s, b in GROUPS:
        pooled = group_stats(mstats, prior, s, b)
        if mode == 'bruto':
            coef[(s, b)] = float(np.clip(slope(pooled), *CLIP))
            lam[(s, b)] = 1.0
            continue
        a, l = shrink(pooled, monthly_slopes(mstats, prior, s, b))
        if mode == 'consistente':
            per_block = [slope(group_stats(mstats, [y], s, b)) for y in prior]
            agree = len(per_block) >= 2 and (all(x > 1 for x in per_block)
                                             or all(x < 1 for x in per_block))
            if not agree:
                a, l = 1.0, 0.0
        coef[(s, b)] = a
        lam[(s, b)] = l
    return coef, lam


def apply_coef(p, clim, coef, masks):
    amap = np.ones_like(p)
    for j in range(24):
        s = int(SEASON_OF_MONTH[j])
        for b in range(3):
            amap[j, masks[b]] = coef[(s, b)]
    return np.maximum(clim + amap * (p - clim), 0.0)


def verdict(month_old, month_new, n_per_month):
    old, new = np.asarray(month_old), np.asarray(month_new)
    rmse_old = float(np.sqrt(old.mean()))
    rmse_new = float(np.sqrt(new.mean()))
    return dict(
        rmse=rmse_new, ganho_percent=100.0 * (1.0 - rmse_new / rmse_old),
        blocos=int(np.sum(new.reshape(-1, 24).mean(axis=1) < old.reshape(-1, 24).mean(axis=1))),
        anos=int(np.sum(new.reshape(-1, 12).mean(axis=1) < old.reshape(-1, 12).mean(axis=1))),
        meses=int(np.sum(new < old)))


def main() -> None:
    masks = band_masks()
    tp = np.load(CACHE / 'tp.npy', mmap_mode='r')

    mstats: dict[int, np.ndarray] = {}
    for year in YEARS:
        t, p, clim = block_arrays(year, tp)
        fa, ya = p - clim, t - clim
        m = np.zeros((24, 3, 4))
        for j in range(24):
            for b in range(3):
                m[j, b] = stats_of(fa[j][masks[b]], ya[j][masks[b]])
        mstats[year] = m
        print(f'[stats] bloco {year} concluido', flush=True)
        del t, p, clim, fa, ya

    # --- Radiografia por grupo, nos cinco blocos de avaliacao ---
    total_sse = sum(sse_s12(group_stats(mstats, EVAL, s, b)) for s, b in GROUPS)
    print('\n=== Onde mora o erro, e onde a climatologia ja vence (blocos 2011-2020) ===')
    print(f'{"grupo":<18}{"%SSE":>7}{"RMSE s12":>10}{"RMSE clim":>11}'
          f'{"clim vence":>12}{"slope":>8}{"lambda":>8}')
    radiografia = {}
    for s, b in GROUPS:
        g = group_stats(mstats, EVAL, s, b)
        wins = sum(sse_clim(group_stats(mstats, [y], s, b))
                   < sse_s12(group_stats(mstats, [y], s, b)) for y in EVAL)
        a_all, lam_all = shrink(group_stats(mstats, YEARS, s, b),
                                monthly_slopes(mstats, YEARS, s, b))
        row = dict(share_sse=100.0 * sse_s12(g) / total_sse,
                   rmse_s12=float(np.sqrt(sse_s12(g) / g[0])),
                   rmse_clim=float(np.sqrt(sse_clim(g) / g[0])),
                   clim_vence_blocos=f'{wins}/{len(EVAL)}',
                   slope_encolhido=a_all, lam=lam_all)
        radiografia[GROUP_NAME[(s, b)]] = row
        print(f'{GROUP_NAME[(s, b)]:<18}{row["share_sse"]:>6.1f}%{row["rmse_s12"]:>10.3f}'
              f'{row["rmse_clim"]:>11.3f}{row["clim_vence_blocos"]:>12}'
              f'{a_all:>8.3f}{lam_all:>8.2f}')

    # --- Variantes causais, aplicadas bloco a bloco ---
    modes = ('global', 'bruto', 'encolhido', 'consistente')
    months = {k: [] for k in ('s12', 'oracle', *modes)}
    coef_log: dict[int, dict] = {}

    for year in EVAL:
        prior = [y for y in YEARS if y < year]
        t, p, clim = block_arrays(year, tp)
        n = p[0].size
        months['s12'].extend((((p - t) ** 2).mean(axis=1)).tolist())

        oracle = {g: float(np.clip(slope(group_stats(mstats, [year], *g)), *CLIP))
                  for g in GROUPS}
        months['oracle'].extend((((apply_coef(p, clim, oracle, masks) - t) ** 2)
                                 .mean(axis=1)).tolist())

        coef_log[year] = {}
        for mode in modes:
            coef, lam = coefficients(mstats, prior, mode)
            months[mode].extend((((apply_coef(p, clim, coef, masks) - t) ** 2)
                                 .mean(axis=1)).tolist())
            coef_log[year][mode] = {GROUP_NAME[g]: round(coef[g], 4) for g in GROUPS}
        print(f'[aplica] bloco {year} concluido', flush=True)
        del t, p, clim

    print('\n=== Variantes nos cinco blocos 2011-2020 ===')
    print(f'{"variante":<34}{"RMSE":>12}{"ganho":>10}{"blocos":>9}{"anos":>8}{"meses":>10}')
    base = float(np.sqrt(np.mean(months['s12'])))
    print(f'{"s12":<34}{base:>12.6f}{"+0.000%":>10}{"-":>9}{"-":>8}{"-":>10}')
    labels = {'global': 'slope unico global (causal)', 'bruto': '12 grupos, sem encolher',
              'encolhido': '12 grupos, encolhido', 'consistente': 'so grupos consistentes',
              'oracle': 'oracle por grupo (teto)'}
    resultados = {}
    for key in (*modes, 'oracle'):
        r = verdict(months['s12'], months[key], None)
        resultados[key] = r
        print(f'{labels[key]:<34}{r["rmse"]:>12.6f}{r["ganho_percent"]:>9.3f}%'
              f'{str(r["blocos"]) + "/5":>9}{str(r["anos"]) + "/10":>8}'
              f'{str(r["meses"]) + "/120":>10}')

    print('\nLeitura: se "encolhido" ou "so grupos consistentes" ficar acima de'
          '\n+0,3% com >=4/5 blocos, existe candidata para uma Rodada 31 formal.'
          '\nSe ficarem perto de zero, o sinal e real mas nao e estimavel com'
          '\nseis blocos, e a linha se encerra aqui.')

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / 'shrink.json').write_text(json.dumps(dict(
        pergunta='Quanto do teto de 0,760% sobrevive a um estimador causal regularizado?',
        clip=list(CLIP), blocos=list(YEARS), blocos_avaliados=list(EVAL),
        radiografia_por_grupo=radiografia, rmse_s12=base,
        resultados=resultados, coeficientes=coef_log,
        treino_novo=False, alvo_de_teste_lido=False, csv_gerado=False,
    ), indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'\nGravado em {OUT_DIR / "shrink.json"}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
