r"""A janela da climatologia, escolhida na primeira rodada, ainda é a certa?

`clim_60y` foi selecionada em `reports/competition/baseline_selection.json`
usando APENAS dois blocos (2017-2018 e 2019-2020), com margem de 0,10% para
a segunda colocada -- e o proprio RESULTS.md registra "apenas dois blocos de
desenvolvimento" como limitacao. Tudo desde a Rodada 2 repousa nessa escolha:
a S02, o residuo que as arvores aprendem, a S12 inteira.

E o ranking INVERTEU entre os dois blocos:
    2017-2018: clim_60y 1.848138  clim_20y 1.857508  -> 60 anos melhor 0,51%
    2019-2020: clim_60y 1.847074  clim_20y 1.841507  -> 20 anos melhor 0,30%
A inversao foi na direcao da janela curta conforme o alvo ficou mais recente,
o que e compativel com tendencia climatica. O teste da competicao e 2023-2024,
quatro anos mais recente ainda. Hoje ha seis blocos para arbitrar, nao dois.

DUAS PERGUNTAS, duas tabelas:

  1. MECANISMO. RMSE da climatologia pura por janela e por bloco. Se a
     vantagem da janela curta cresce monotonicamente com a recencia do alvo,
     a tendencia e real e deve continuar valendo em 2023-2024.

  2. EFEITO NA S12. Trocar a climatologia exigiria reconstruir o pipeline,
     o que e caro. Como aproximacao de primeira ordem testamos
     `S12 + alpha * (clim_X - clim_60)`, com alpha escalar unico ajustado SO
     em blocos anteriores. Isso mede se o residuo da S12 carrega o vies de
     recencia que a janela curta corrigiria. E aproximacao: as correcoes
     foram treinadas contra clim_60, entao o alpha causal e justamente quem
     decide quanto do deslocamento vale a pena aplicar.

CRITERIO DECLARADO ANTES DE RODAR. Reconstruir o pipeline so se justifica se
alguma janela der ganho causal >= 0,3% com >= 4/5 blocos. Vantagem da
climatologia pura sozinha nao basta: o que importa e o efeito na S12.

Nao treina modelo, nao le alvo de teste, nao gera CSV, nao cria submissao.

Uso (na raiz do repositorio, com o venv ativado):

    .\.venv\Scripts\python.exe scripts\diag_clim.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src import round20, round27
from src.competition import CACHE, ROOT, dates, fit_climatology, month_number
from src.round2 import target_origins

YEARS = round27.YEARS
EVAL = round27.EVAL
SHAPE = (301, 261)
BASE_WINDOW = 60
WINDOWS = (None, 60, 50, 40, 30, 25, 20, 15, 10)
OUT_DIR = ROOT / 'reports' / 'competition' / 'clim_diagnostic'
MIN_GAIN = 0.3
MIN_BLOCKS = 4


def label(window) -> str:
    return 'clim_all' if window is None else f'clim_{window}y'


def main() -> None:
    times = dates()
    tp = np.load(CACHE / 'tp.npy', mmap_mode='r')

    per_block_rmse: dict[str, dict[int, float]] = {label(w): {} for w in WINDOWS}
    shifts: dict[int, dict[str, np.ndarray]] = {}
    residual: dict[int, np.ndarray] = {}

    for year in YEARS:
        targets = target_origins(year) + 1
        cutoff = int(targets.min())
        truth = np.asarray(tp[targets], np.float64).reshape(24, -1)
        history = np.asarray(tp[:cutoff], np.float32)
        months = month_number(times[targets])

        base = None
        shifts[year] = {}
        for window in WINDOWS:
            climo = fit_climatology(history, times[:cutoff], times[cutoff], window)
            predicted = np.asarray(climo[months], np.float64).reshape(24, -1)
            error = predicted - truth
            per_block_rmse[label(window)][year] = float(np.sqrt(np.mean(error * error)))
            if window == BASE_WINDOW:
                base = predicted
            shifts[year][label(window)] = predicted
        for name in list(shifts[year]):
            shifts[year][name] = shifts[year][name] - base

        s12 = np.asarray(round20.reference(year), np.float64).reshape(24, -1)
        residual[year] = truth - s12
        del history, truth
        print(f'[bloco] {year} concluido', flush=True)

    # --- Tabela 1: mecanismo ---
    print('\n=== RMSE da climatologia pura, por janela e por bloco ===')
    print(f'{"janela":<12}' + ''.join(f'{y:>10}' for y in YEARS) + f'{"tendencia":>12}')
    trend = {}
    order = np.arange(len(YEARS), dtype=float)
    for window in WINDOWS:
        name = label(window)
        row = [per_block_rmse[name][y] for y in YEARS]
        # vantagem da janela em relacao a clim_60y, por bloco (positivo = melhor)
        gain = np.array([per_block_rmse['clim_60y'][y] - per_block_rmse[name][y] for y in YEARS])
        r = float(np.corrcoef(order, gain)[0, 1]) if np.std(gain) > 0 else 0.0
        trend[name] = {'rmse_por_bloco': row, 'vantagem_vs_60y': gain.tolist(),
                       'correlacao_com_recencia': r}
        marker = '' if window == BASE_WINDOW else f'{r:>12.3f}'
        print(f'{name:<12}' + ''.join(f'{v:>10.4f}' for v in row) + (marker or f'{"(base)":>12}'))

    print('\nA coluna "tendencia" e a correlacao entre a recencia do bloco e a')
    print('vantagem daquela janela sobre clim_60y. Positiva e crescente = a')
    print('janela curta melhora conforme o alvo avanca no tempo.')

    # --- Tabela 2: efeito na S12 ---
    print('\n=== S12 + alpha * (clim_X - clim_60), blocos 2011-2020 ===')
    print(f'{"variante":<22}{"alpha":>8}{"RMSE":>12}{"ganho":>10}{"blocos":>9}{"meses":>10}')
    base_monthly = []
    for year in EVAL:
        base_monthly.extend(np.mean(residual[year] ** 2, axis=1).tolist())
    base_monthly = np.asarray(base_monthly)
    rmse_s12 = float(np.sqrt(base_monthly.mean()))
    print(f'{"s12":<22}{"-":>8}{rmse_s12:>12.6f}{"+0.000%":>10}{"-":>9}{"-":>10}')

    results = {}
    for window in WINDOWS:
        name = label(window)
        if window == BASE_WINDOW:
            continue
        for mode in ('causal', 'oracle'):
            monthly, alphas = [], []
            for year in EVAL:
                fit_years = [year] if mode == 'oracle' else [y for y in YEARS if y < year]
                num = sum(float(np.sum(shifts[y][name] * residual[y])) for y in fit_years)
                den = sum(float(np.sum(shifts[y][name] ** 2)) for y in fit_years)
                alpha = num / den if den > 0 else 0.0
                alphas.append(alpha)
                error = residual[year] - alpha * shifts[year][name]
                monthly.extend(np.mean(error * error, axis=1).tolist())
            v = np.asarray(monthly)
            key = f'{name}_{mode}'
            results[key] = {
                'alpha_medio': float(np.mean(alphas)), 'alphas': alphas,
                'rmse': float(np.sqrt(v.mean())),
                'ganho_percent': 100.0 * (1.0 - np.sqrt(v.mean() / base_monthly.mean())),
                'blocos': int(np.sum(v.reshape(-1, 24).mean(axis=1)
                                     < base_monthly.reshape(-1, 24).mean(axis=1))),
                'meses': int(np.sum(v < base_monthly))}
            r = results[key]
            print(f'{key:<22}{r["alpha_medio"]:>8.3f}{r["rmse"]:>12.6f}'
                  f'{r["ganho_percent"]:>9.3f}%{str(r["blocos"]) + "/5":>9}'
                  f'{str(r["meses"]) + "/120":>10}')

    passes = [k for k, r in results.items()
              if k.endswith('_causal') and r['ganho_percent'] >= MIN_GAIN
              and r['blocos'] >= MIN_BLOCKS]
    print('\nVEREDITO:', ('reconstruir o pipeline se justifica -> ' + ', '.join(passes))
          if passes else
          f'nenhuma janela atinge {MIN_GAIN}% causal com >={MIN_BLOCKS}/5 blocos; '
          'clim_60y fica como esta.')

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / 'clim.json').write_text(json.dumps({
        'pergunta': 'A janela de climatologia escolhida na rodada 1 ainda e a certa?',
        'escolha_original': 'clim_60y, em 2 blocos, margem de 0,10%',
        'criterio_declarado': {'ganho_minimo_percent': MIN_GAIN, 'blocos_minimos': MIN_BLOCKS},
        'blocos': list(YEARS), 'blocos_avaliados': list(EVAL),
        'climatologia_pura': trend, 'rmse_s12': rmse_s12,
        'efeito_na_s12': results, 'aprovadas': passes,
        'aproximacao': 'S12 + alpha*(clim_X - clim_60); correcoes nao foram retreinadas',
        'treino_novo': False, 'alvo_de_teste_lido': False, 'csv_gerado': False,
    }, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'\nGravado em {OUT_DIR / "clim.json"}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
