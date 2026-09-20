r"""O ENSO carrega informação que a S12 não tem?

Primeiro teste com dado externo do projeto. A Seção 2.6 das regras da
competição permite Dados Externos "de domínio público e igualmente
acessíveis a todos os Participantes [...] sem custo"; o ONI do NOAA Climate
Prediction Center qualifica (obra do governo dos EUA, domínio público,
publicação gratuita).

Pré-requisito -- baixe manualmente e salve como data/external/oni.ascii.txt:

    https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt

Quatro colunas: SEAS YR TOTAL ANOM. O ONI de uma estação de três meses é
atribuído ao seu mês central (DJF -> janeiro, NDJ -> dezembro).

CAUSALIDADE. O ONI centrado no mês `m` usa TSM dos meses m-1, m e m+1, logo
só está disponível ao fim do mês `m+1`. Para uma origem `o` o valor mais
recente legítimo é o centrado em `o-1`. Usar ONI[o] seria vazamento. As
variantes abaixo respeitam esse limite.

MÉTODO. O resíduo da S12 é, por definição, o que o pipeline não explicou.
Como o ONI é um escalar por mês, seu efeito é um PADRÃO de resposta por
célula multiplicado por uma série temporal -- então ajustamos uma regressão
por célula, `residuo ~ beta * oni`, com beta estimado SÓ em blocos
anteriores, e medimos o RMSE resultante. A versão oracle (beta ajustado no
próprio bloco) é o teto.

CRITÉRIO DECLARADO ANTES DE RODAR. O ganho máximo de RMSE de um preditor
com correlação r é 1 - sqrt(1 - r^2). Para 0,3% é preciso |r| >= 0,077.
Correlação típica abaixo de 0,08, ou ganho causal abaixo de 0,3% com menos
de 4/5 blocos, encerra a linha -- por mais consistente que seja o sinal.

Não treina modelo, não lê alvo de teste, não gera CSV, não cria submissão.

Uso (na raiz do repositório, com o venv ativado):

    .\.venv\Scripts\python.exe scripts\diag_oni.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src import round4, round27
from src.competition import CACHE, ROOT, dates
from src.round2 import target_origins
from src import round20

YEARS = round27.YEARS
EVAL = round27.EVAL
SHAPE = (301, 261)
ONI_PATH = ROOT / 'data' / 'external' / 'oni.ascii.txt'
OUT_DIR = ROOT / 'reports' / 'competition' / 'oni_diagnostic'

SEASON_CENTER = {'DJF': 1, 'JFM': 2, 'FMA': 3, 'MAM': 4, 'AMJ': 5, 'MJJ': 6,
                 'JJA': 7, 'JAS': 8, 'ASO': 9, 'SON': 10, 'OND': 11, 'NDJ': 12}
SEASONS = ('DJF', 'MAM', 'JJA', 'SON')
BANDS = ('lat<-30', '-30a-10', 'lat>=-10')
SEASON_OF_MONTH = ((np.arange(24) % 12 + 1) % 12) // 3
GROUPS = [(s, b) for s in range(4) for b in range(3)]
GROUP_NAME = {(s, b): f'{SEASONS[s]}/{BANDS[b]}' for s, b in GROUPS}

# Cada variante é (rótulo, função que devolve o valor para a origem o).
# Nenhuma usa índice > o-1.
VARIANTS = {
    'oni_lag1': lambda oni, o: oni[o - 1],
    'oni_lag3': lambda oni, o: oni[o - 3],
    'oni_tendencia': lambda oni, o: oni[o - 1] - oni[o - 4],
}
MIN_ABS_R = 0.077


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def load_oni() -> np.ndarray:
    """Série mensal de ONI alinhada ao índice de `dates()`; NaN onde faltar."""
    if not ONI_PATH.exists():
        raise SystemExit(
            f'Arquivo não encontrado: {ONI_PATH}\n'
            'Baixe https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt '
            'e salve nesse caminho.')
    times = dates()
    series = np.full(len(times), np.nan)
    first_year = times[0].year
    kept = 0
    for line in ONI_PATH.read_text(encoding='utf-8', errors='ignore').splitlines():
        parts = line.split()
        if len(parts) != 4 or parts[0] not in SEASON_CENTER:
            continue
        month = SEASON_CENTER[parts[0]]
        year = int(parts[1])
        index = (year - first_year) * 12 + (month - 1)
        if 0 <= index < len(series):
            series[index] = float(parts[3])
            kept += 1
    print(f'ONI: {kept} valores mapeados, '
          f'cobertura {np.isfinite(series).sum()}/{len(series)} meses')
    print(f'sha256 do arquivo: {sha256_of(ONI_PATH)}')
    return series


def band_masks():
    bands = (round4.groups()[0] % 3).reshape(-1)
    return [bands == i for i in range(3)]


def block_residual(year: int, tp) -> np.ndarray:
    """Resíduo da S12 no bloco: (24, GRID)."""
    targets = target_origins(year) + 1
    truth = np.asarray(tp[targets], np.float64).reshape(24, -1)
    s12 = np.asarray(round20.reference(year), np.float64).reshape(24, -1)
    return truth - s12


def main() -> None:
    oni = load_oni()
    masks = band_masks()
    tp = np.load(CACHE / 'tp.npy', mmap_mode='r')

    residual = {y: block_residual(y, tp) for y in YEARS}
    values = {name: {y: np.array([fn(oni, int(o)) for o in target_origins(y)])
                     for y in YEARS}
              for name, fn in VARIANTS.items()}
    for name in VARIANTS:
        bad = sum(int(np.isnan(v).sum()) for v in values[name].values())
        if bad:
            raise SystemExit(f'{name}: {bad} valores de ONI ausentes nos blocos')

    # --- 1. Correlação temporal por célula, agregada por grupo ---
    print('\n=== Correlacao temporal por celula entre ONI e residuo da S12 ===')
    print('(media, sobre as celulas do grupo, da correlacao no tempo; 6 blocos juntos)')
    print(f'{"grupo":<18}' + ''.join(f'{n:>15}' for n in VARIANTS))
    table = {}
    all_res = np.concatenate([residual[y] for y in YEARS])            # (144, GRID)
    for s, b in GROUPS:
        months = np.concatenate([np.flatnonzero(SEASON_OF_MONTH == s) + 24 * k
                                 for k in range(len(YEARS))])
        cells = np.flatnonzero(masks[b])
        row = {}
        for name in VARIANTS:
            x = np.concatenate([values[name][y] for y in YEARS])[months]
            y_ = all_res[np.ix_(months, cells)]
            xc = x - x.mean()
            yc = y_ - y_.mean(axis=0, keepdims=True)
            denom = np.sqrt(float(xc @ xc) * np.sum(yc * yc, axis=0))
            with np.errstate(invalid='ignore', divide='ignore'):
                r = np.where(denom > 0, (xc @ yc) / denom, np.nan)
            row[name] = float(np.nanmean(r))
        table[GROUP_NAME[(s, b)]] = row
        print(f'{GROUP_NAME[(s, b)]:<18}' + ''.join(f'{row[n]:>15.3f}' for n in VARIANTS))

    best_abs = max(abs(v) for row in table.values() for v in row.values())
    print(f'\nmaior |r| observado em qualquer grupo/variante: {best_abs:.3f}'
          f'   (limiar declarado: {MIN_ABS_R:.3f})')

    # --- 2. Correcao por celula, causal e oracle ---
    print('\n=== RMSE ao adicionar beta_celula * ONI a S12 (blocos 2011-2020) ===')
    print(f'{"variante":<28}{"RMSE":>12}{"ganho":>10}{"blocos":>9}{"anos":>8}{"meses":>10}')
    monthly = {'s12': []}
    for year in EVAL:
        monthly['s12'].extend(np.mean(residual[year] ** 2, axis=1).tolist())
    base = np.asarray(monthly['s12'])
    print(f'{"s12":<28}{np.sqrt(base.mean()):>12.6f}{"+0.000%":>10}{"-":>9}{"-":>8}{"-":>10}')

    results = {}
    for name in VARIANTS:
        for mode in ('causal', 'oracle'):
            key = f'{name}_{mode}'
            monthly[key] = []
            for year in EVAL:
                fit_years = [year] if mode == 'oracle' else [y for y in YEARS if y < year]
                xf = np.concatenate([values[name][y] for y in fit_years])
                rf = np.concatenate([residual[y] for y in fit_years])
                xc = xf - xf.mean()
                den = float(xc @ xc)
                beta = (xc @ (rf - rf.mean(axis=0, keepdims=True))) / den if den > 0 else 0.0
                xe = values[name][year] - xf.mean()
                corrected = residual[year] - np.outer(xe, beta)
                monthly[key].extend(np.mean(corrected ** 2, axis=1).tolist())
            v = np.asarray(monthly[key])
            results[key] = {
                'rmse': float(np.sqrt(v.mean())),
                'ganho_percent': 100.0 * (1.0 - np.sqrt(v.mean() / base.mean())),
                'blocos': int(np.sum(v.reshape(-1, 24).mean(axis=1)
                                     < base.reshape(-1, 24).mean(axis=1))),
                'anos': int(np.sum(v.reshape(-1, 12).mean(axis=1)
                                   < base.reshape(-1, 12).mean(axis=1))),
                'meses': int(np.sum(v < base))}
            r = results[key]
            print(f'{key:<28}{r["rmse"]:>12.6f}{r["ganho_percent"]:>9.3f}%'
                  f'{str(r["blocos"]) + "/5":>9}{str(r["anos"]) + "/10":>8}'
                  f'{str(r["meses"]) + "/120":>10}')

    passes = [k for k, r in results.items()
              if k.endswith('_causal') and r['ganho_percent'] >= 0.3 and r['blocos'] >= 4]
    print('\nVEREDITO:', 'candidata para uma Rodada 33 formal -> ' + ', '.join(passes)
          if passes else
          'nenhuma variante causal atinge 0,3% com >=4/5 blocos; linha encerrada.')

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / 'oni.json').write_text(json.dumps({
        'pergunta': 'O ENSO carrega informacao ausente do residuo da S12?',
        'fonte': 'NOAA CPC oni.ascii.txt',
        'sha256': sha256_of(ONI_PATH),
        'causalidade': 'ONI centrado em o-1 ou anterior; nunca o proprio mes de origem',
        'limiar_declarado_abs_r': MIN_ABS_R,
        'correlacao_por_grupo': table, 'maior_abs_r': best_abs,
        'rmse_s12': float(np.sqrt(base.mean())), 'resultados': results,
        'aprovadas': passes,
        'treino_novo': False, 'alvo_de_teste_lido': False, 'csv_gerado': False,
    }, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'\nGravado em {OUT_DIR / "oni.json"}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
