r"""Persistência de precipitação carrega informação que a S12 não tem?

CONTEXTO. O organizador esclareceu o critério: para prever o mês T vale
qualquer dado que em tese estaria disponível até o fim de T-1, incluindo
dados externos e informação de fora do domínio; o que não vale é usar o
próprio mês T para estimar T.

Isso libera a precipitação observada em T-1 como preditor. E o pipeline
NUNCA a usou: `round2.Features.matrix` tem 55 colunas sem nenhuma de chuva,
e `round6.local_memory` usa as nove variáveis ATMOSFÉRICAS em três
defasagens, não precipitação. A chuva só aparece como rótulo.

Este diagnóstico mede o tamanho da oportunidade ANTES de construir, e usa
SOMENTE dado oficial: `tp.npy` cobre 1940-2022, então todas as origens dos
seis blocos já têm chuva observada. Nenhum download é necessário aqui.

MÉTODO. O resíduo da S12 é o que o pipeline não explicou. Correlacionamos
com cinco atributos de persistência, todos na origem `o` e em anomalia
contra climatologia causal, e medimos também o R² conjunto dos cinco.

CRITÉRIO DECLARADO ANTES DE RODAR. O teto de ganho de RMSE de um preditor
com R² conjunto vale `1 - sqrt(1 - R2)`. Para os 0,3% do limiar de promoção
é preciso R2 >= 0,006, o que corresponde a |r| ~ 0,077 para um preditor
isolado. R² conjunto abaixo de 0,006 na faixa tropical encerra a linha.

Não treina modelo, não lê alvo de teste, não gera CSV, não cria submissão.

Uso (na raiz do repositório, com o venv ativado):

    .\.venv\Scripts\python.exe scripts\diag_persist.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import uniform_filter

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src import round4, round20, round27
from src.competition import CACHE, ROOT, dates, fit_climatology, month_number
from src.round2 import target_origins

YEARS = round27.YEARS
SHAPE = (301, 261)
OUT_DIR = ROOT / 'reports' / 'competition' / 'persist_diagnostic'
CLIMATOLOGY_YEARS = 60
MIN_R2 = 0.006

SEASONS = ('DJF', 'MAM', 'JJA', 'SON')
BANDS = ('lat<-30', '-30a-10', 'lat>=-10')
SEASON_OF_MONTH = ((np.arange(24) % 12 + 1) % 12) // 3
GROUPS = [(s, b) for s in range(4) for b in range(3)]
GROUP_NAME = {(s, b): f'{SEASONS[s]}/{BANDS[b]}' for s, b in GROUPS}
FEATURES = ('anom_o', 'anom_media3', 'anom_suave3x3', 'anom_suave9x9', 'tendencia')


def band_masks():
    bands = (round4.groups()[0] % 3).reshape(-1)
    return [bands == i for i in range(3)]


def persistence(tp, climo, origins) -> dict[str, np.ndarray]:
    """Cinco atributos de persistência na origem, em anomalia. (24, GRID) cada."""
    _times = dates()
    def anomaly(idx):
        idx = np.asarray(idx, int)
        return (np.asarray(tp[idx], np.float64)
                - climo[month_number(_times[idx])]).reshape(len(idx), *SHAPE)

    a0 = anomaly(origins)
    a1 = anomaly(origins - 1)
    a2 = anomaly(origins - 2)
    return {
        'anom_o': a0.reshape(24, -1),
        'anom_media3': ((a0 + a1 + a2) / 3).reshape(24, -1),
        'anom_suave3x3': uniform_filter(a0, size=(1, 3, 3), mode='nearest').reshape(24, -1),
        'anom_suave9x9': uniform_filter(a0, size=(1, 9, 9), mode='nearest').reshape(24, -1),
        'tendencia': (a0 - a1).reshape(24, -1),
    }


def joint_r2(design: np.ndarray, target: np.ndarray) -> float:
    """R² de `target` sobre as colunas de `design`, com intercepto."""
    x = design - design.mean(axis=0, keepdims=True)
    y = target - target.mean()
    xtx = x.T @ x
    xty = x.T @ y
    try:
        beta = np.linalg.solve(xtx + 1e-9 * np.eye(x.shape[1]) * np.trace(xtx), xty)
    except np.linalg.LinAlgError:
        return float('nan')
    explained = float(beta @ xty)
    total = float(y @ y)
    return explained / total if total > 0 else float('nan')


def main() -> None:
    masks = band_masks()
    tp = np.load(CACHE / 'tp.npy', mmap_mode='r')
    times = dates()

    per_group = {name: {f: [] for f in FEATURES} for name in GROUP_NAME.values()}
    r2_group: dict[str, list[float]] = {name: [] for name in GROUP_NAME.values()}

    for year in YEARS:
        origins = target_origins(year)
        targets = origins + 1
        cut = int(targets.min())
        climo = fit_climatology(np.asarray(tp[:cut], np.float32), times[:cut],
                                times[cut], CLIMATOLOGY_YEARS)
        truth = np.asarray(tp[targets], np.float64).reshape(24, -1)
        s12 = np.asarray(round20.reference(year), np.float64).reshape(24, -1)
        residual = truth - s12
        feats = persistence(tp, climo, origins)

        for s, b in GROUPS:
            months = np.flatnonzero(SEASON_OF_MONTH == s)
            cells = np.flatnonzero(masks[b])
            r = residual[np.ix_(months, cells)].ravel()
            columns = []
            for name in FEATURES:
                v = feats[name][np.ix_(months, cells)].ravel()
                columns.append(v)
                rc = np.corrcoef(v, r)[0, 1] if v.std() > 0 and r.std() > 0 else np.nan
                per_group[GROUP_NAME[(s, b)]][name].append(float(rc))
            r2_group[GROUP_NAME[(s, b)]].append(joint_r2(np.column_stack(columns), r))
        print(f'[bloco] {year} concluido', flush=True)
        del truth, s12, residual, feats

    print('\n=== Correlacao com o residuo da S12 (media dos seis blocos) ===')
    print(f'{"grupo":<18}' + ''.join(f'{f:>15}' for f in FEATURES) + f'{"R2 conj":>10}')
    table = {}
    for s, b in GROUPS:
        name = GROUP_NAME[(s, b)]
        row = {f: float(np.nanmean(per_group[name][f])) for f in FEATURES}
        row['r2_conjunto'] = float(np.nanmean(r2_group[name]))
        row['r2_por_bloco'] = [float(v) for v in r2_group[name]]
        table[name] = row
        print(f'{name:<18}' + ''.join(f'{row[f]:>15.3f}' for f in FEATURES)
              + f'{row["r2_conjunto"]:>10.4f}')

    tropic = [GROUP_NAME[g] for g in GROUPS if g[1] == 2]
    r2_tropic = float(np.mean([table[n]['r2_conjunto'] for n in tropic]))
    ceiling = 100.0 * (1.0 - np.sqrt(max(1.0 - r2_tropic, 0.0)))
    r2_all = float(np.mean([r['r2_conjunto'] for r in table.values()]))
    ceiling_all = 100.0 * (1.0 - np.sqrt(max(1.0 - r2_all, 0.0)))

    print(f'\nR2 conjunto medio -- faixa tropical: {r2_tropic:.4f}  '
          f'(teto de RMSE {ceiling:.3f}%)')
    print(f'R2 conjunto medio -- todos os grupos: {r2_all:.4f}  '
          f'(teto de RMSE {ceiling_all:.3f}%)')
    print(f'Limiar declarado: R2 >= {MIN_R2:.3f}, equivalente a 0,3% de RMSE.')
    print('\nVEREDITO:', 'vale construir a Rodada 35.'
          if r2_tropic >= MIN_R2 else
          'persistencia nao carrega sinal suficiente; linha encerrada.')

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / 'persist.json').write_text(json.dumps({
        'pergunta': 'Persistencia de precipitacao carrega informacao ausente do residuo da S12?',
        'contexto': 'Organizador permite qualquer dado disponivel ate o fim de T-1',
        'somente_dado_oficial': True,
        'limiar_declarado_r2': MIN_R2,
        'features': list(FEATURES), 'blocos': list(YEARS),
        'por_grupo': table, 'r2_tropical': r2_tropic, 'teto_tropical_percent': ceiling,
        'r2_global': r2_all, 'teto_global_percent': ceiling_all,
        'treino_novo': False, 'alvo_de_teste_lido': False, 'csv_gerado': False,
    }, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'\nGravado em {OUT_DIR / "persist.json"}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
