r"""Diagnostico de calibracao de amplitude da S12 em espaco de anomalia.

Pergunta unica: a amplitude da anomalia prevista pela S12 corresponde a skill
que ela de fato tem? Se o slope OLS de (observado - climatologia) contra
(previsto - climatologia) for sistematicamente menor que 1, amortecer a
anomalia em direcao a climatologia reduz o RMSE. O pooling atual nao pode
capturar esse ganho: `round4.fit_weights` impoe soma de pesos igual a 1,
piso de 0,1 por componente e nenhum intercepto, o que proibe por construcao
qualquer encolhimento liquido em direcao a climatologia.

Este script NAO treina modelo novo, NAO le alvo de teste, NAO gera CSV e NAO
cria submissao. Usa apenas artefatos OOF ja congelados (via `round27.source`)
e o cache oficial `tp.npy`.

Uso (na raiz do repositorio, com o venv ativado):

    .\.venv\Scripts\python.exe scripts\diag_slope.py

Saida no terminal e em reports/competition/slope_diagnostic/slope.json:

  1. Slope e correlacao por grupo (3 bandas de latitude x 4 estacoes,
     exatamente os 12 grupos de `round4.groups()`), por bloco.
  2. Ganho de RMSE com recalibracao CAUSAL (coeficientes ajustados somente
     em blocos anteriores ao bloco avaliado) nos cinco blocos 2011-2020,
     na mesma moeda das rodadas 27-30.
  3. Ganho com recalibracao ORACLE (coeficientes do proprio bloco), que e
     o teto superior: se este numero ja for pequeno, a avenida esta fechada.
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
NGROUPS = 12
OUT_DIR = REPO_ROOT / 'reports' / 'competition' / 'slope_diagnostic'

SEASONS = ('DJF', 'MAM', 'JJA', 'SON')
BANDS = ('lat<-30', '-30a-10', 'lat>=-10')
GROUP_NAMES = [f'{SEASONS[g // 3]}/{BANDS[g % 3]}' for g in range(NGROUPS)]


def group_masks():
    """Os mesmos 12 grupos do pooling base, achatados para (24, GRID)."""
    g = round4.groups().reshape(24, -1)
    return [g == k for k in range(NGROUPS)]


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
    """Observado, S12 e climatologia causal do bloco, todos (24, GRID)."""
    truth, s12, _ = round27.source(year, tp)
    t = np.asarray(truth, np.float64).reshape(24, -1)
    p = np.asarray(s12, np.float64).reshape(24, -1)
    clim = causal_climatology(tp, target_origins(year) + 1)
    return t, p, clim


def stats_of(f, y):
    """Estatisticas suficientes para OLS com intercepto: n, Sf, Sy, Sff, Sfy, Syy."""
    return np.array([f.size, f.sum(), y.sum(), float(f @ f), float(f @ y), float(y @ y)])


def solve(s):
    """Devolve (a, b) de y ~ a*f + b a partir das estatisticas suficientes."""
    n, sf, sy, sff, sfy, _ = s
    den = n * sff - sf * sf
    if n < 2 or den <= 0:
        return 1.0, 0.0
    a = (n * sfy - sf * sy) / den
    return float(a), float((sy - a * sf) / n)


def correlation(s):
    n, sf, sy, sff, sfy, syy = s
    vf = sff - sf * sf / n
    vy = syy - sy * sy / n
    if vf <= 0 or vy <= 0:
        return float('nan')
    return float((sfy - sf * sy / n) / np.sqrt(vf * vy))


def recalibrated(p, clim, coef, masks):
    """clim + a*(p - clim) + b por grupo, truncado em zero."""
    fa = p - clim
    out = np.empty_like(p)
    for k, m in enumerate(masks):
        a, b = coef[k]
        out[m] = clim[m] + a * fa[m] + b
    return np.maximum(out, 0.0, out=out)


def summarize(sse_old, sse_new, n_total, month_old, month_new):
    """Mesma moeda das rodadas 27-30: ganho relativo, blocos/anos/meses."""
    old = np.asarray(month_old)
    new = np.asarray(month_new)
    blocks = int(np.sum(new.reshape(-1, 24).mean(axis=1) < old.reshape(-1, 24).mean(axis=1)))
    years = int(np.sum(new.reshape(-1, 12).mean(axis=1) < old.reshape(-1, 12).mean(axis=1)))
    rmse_old = float(np.sqrt(sse_old / n_total))
    rmse_new = float(np.sqrt(sse_new / n_total))
    return dict(rmse_s12=rmse_old, rmse_recalibrado=rmse_new,
                ganho_percent=100.0 * (1.0 - rmse_new / rmse_old),
                blocos=f'{blocks}/{len(old) // 24}', anos=f'{years}/{len(old) // 12}',
                meses=f'{int(np.sum(new < old))}/{len(old)}')


def main() -> None:
    masks = group_masks()
    tp = np.load(CACHE / 'tp.npy', mmap_mode='r')

    # Passagem 1: estatisticas suficientes por bloco e grupo (um bloco por vez).
    stats: dict[int, np.ndarray] = {}
    for year in YEARS:
        t, p, clim = block_arrays(year, tp)
        fa, ya = (p - clim).ravel(), (t - clim).ravel()
        flat = [m.ravel() for m in masks]
        stats[year] = np.stack([stats_of(fa[m], ya[m]) for m in flat])
        print(f'[stats] bloco {year} concluido', flush=True)
        del t, p, clim, fa, ya, flat

    print('\n=== Slope da anomalia por grupo (ajuste no proprio bloco) ===')
    print(f'{"grupo":<18}' + ''.join(f'{y:>9}' for y in YEARS))
    slopes_table = {}
    for k in range(NGROUPS):
        row = [solve(stats[y][k])[0] for y in YEARS]
        slopes_table[GROUP_NAMES[k]] = row
        print(f'{GROUP_NAMES[k]:<18}' + ''.join(f'{v:>9.3f}' for v in row))

    print('\n=== Correlacao da anomalia por grupo ===')
    corr_table = {}
    for k in range(NGROUPS):
        row = [correlation(stats[y][k]) for y in YEARS]
        corr_table[GROUP_NAMES[k]] = row
        print(f'{GROUP_NAMES[k]:<18}' + ''.join(f'{v:>9.3f}' for v in row))

    # Passagem 2: aplica coeficientes causais e oracle nos cinco blocos de avaliacao.
    acc = dict(causal=[0.0, 0.0], oracle=[0.0, 0.0])
    month_old: list[float] = []
    month_causal: list[float] = []
    month_oracle: list[float] = []
    n_total = 0
    coef_causal_log = {}

    for year in EVAL:
        prior = [y for y in YEARS if y < year]
        coef_causal = [solve(sum(stats[y][k] for y in prior)) for k in range(NGROUPS)]
        coef_oracle = [solve(stats[year][k]) for k in range(NGROUPS)]
        coef_causal_log[year] = {GROUP_NAMES[k]: coef_causal[k] for k in range(NGROUPS)}

        t, p, clim = block_arrays(year, tp)
        new_c = recalibrated(p, clim, coef_causal, masks)
        new_o = recalibrated(p, clim, coef_oracle, masks)

        e_old = (p - t) ** 2
        e_c = (new_c - t) ** 2
        e_o = (new_o - t) ** 2
        acc['causal'][0] += float(e_old.sum()); acc['causal'][1] += float(e_c.sum())
        acc['oracle'][0] += float(e_old.sum()); acc['oracle'][1] += float(e_o.sum())
        n_total += e_old.size
        month_old.extend(e_old.mean(axis=1).tolist())
        month_causal.extend(e_c.mean(axis=1).tolist())
        month_oracle.extend(e_o.mean(axis=1).tolist())
        print(f'[aplica] bloco {year} concluido', flush=True)
        del t, p, clim, new_c, new_o, e_old, e_c, e_o

    causal = summarize(acc['causal'][0], acc['causal'][1], n_total, month_old, month_causal)
    oracle = summarize(acc['oracle'][0], acc['oracle'][1], n_total, month_old, month_oracle)

    print('\n=== Resultado nos cinco blocos 2011-2020 ===')
    print(f'{"variante":<28}{"RMSE":>12}{"ganho":>10}{"blocos":>9}{"anos":>8}{"meses":>10}')
    print(f'{"s12":<28}{causal["rmse_s12"]:>12.6f}{"+0.000%":>10}{"-":>9}{"-":>8}{"-":>10}')
    for name, r in (('recalibrado (causal)', causal), ('recalibrado (oracle)', oracle)):
        print(f'{name:<28}{r["rmse_recalibrado"]:>12.6f}{r["ganho_percent"]:>9.3f}%'
              f'{r["blocos"]:>9}{r["anos"]:>8}{r["meses"]:>10}')

    print('\nLeitura: o ganho ORACLE e o teto absoluto desta ideia (coeficientes'
          '\najustados no proprio bloco avaliado). Se ele ja for menor que 0,3%,'
          '\na recalibracao de amplitude nao sustenta uma rodada de promocao.')

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / 'slope.json').write_text(json.dumps(dict(
        pergunta='A amplitude da anomalia da S12 esta calibrada?',
        grupos=GROUP_NAMES, blocos=list(YEARS), blocos_avaliados=list(EVAL),
        slope_por_bloco=slopes_table, correlacao_por_bloco=corr_table,
        coeficientes_causais=coef_causal_log,
        resultado_causal=causal, resultado_oracle=oracle,
        treino_novo=False, alvo_de_teste_lido=False, csv_gerado=False,
    ), indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'\nGravado em {OUT_DIR / "slope.json"}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
