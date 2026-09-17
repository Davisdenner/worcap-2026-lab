"""Especialistas não lineares regionais com âncora global S12 e gates fixos."""
import os
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import gc
import json
import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from . import round17 as old
from . import round20 as prior
from .round9 import preceding, passes_gate

ART = old.ROOT/'data/processed/round21'
OUT = old.REPORT/'round21'
PROTOCOL = old.ROOT/'experiments/ROUND21.md'
BETAS = (.25, .5)
LEAVES = (7, 15)
CONFIGS = {f'region{leaf}_b{beta:g}': (leaf, beta) for leaf in LEAVES for beta in BETAS}
TREE = dict(loss='squared_error', learning_rate=.03, max_iter=200,
            max_bins=128, min_samples_leaf=300, l2_regularization=100.,
            early_stopping=False, random_state=old.SEED)
REGIONS = ('sul', 'centro', 'norte')


def weights(latitude):
    lat = np.asarray(latitude, dtype=float)
    south_transition = np.clip((lat+17.5)/5, 0, 1)
    north_transition = np.clip((lat+2.5)/5, 0, 1)
    result = np.stack((1-south_transition,
                       south_transition*(1-north_transition), north_transition), axis=-1)
    if not np.all(result >= 0) or not np.allclose(result.sum(axis=-1), 1):
        raise ValueError('Transição regional inválida')
    return result


def training_mask(latitude, region):
    lat = np.asarray(latitude)
    if region == 'sul': return lat < -12.5
    if region == 'centro': return (lat >= -17.5) & (lat < 2.5)
    if region == 'norte': return lat >= -2.5
    raise ValueError('Região inválida')


def locked():
    prior.locked(); ART.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
    obj = dict(protocol_sha256=old.digest(PROTOCOL), source_sha256=old.digest(old.ROOT/'src/round21.py'),
               parent_protocol=old.read(prior.OUT/'protocol.json'), configs=CONFIGS,
               tree=TREE, training_blocks='only complete preceding blocks',
               reference='S12', official_only=True, minimum_relative_gain=.003)
    obj = json.loads(json.dumps(obj)); path = OUT/'protocol.json'
    if path.exists() and old.read(path) != obj: raise ValueError('Código ou protocolo da rodada 21 mudou')
    if not path.exists(): old.save_json(path, obj)
    return obj


def samples(cutoff):
    years = preceding(old.HISTORY, cutoff)
    if not years or any(year+2 > cutoff for year in years): raise ValueError('Bloco futuro no treino')
    pieces = []
    for year in years:
        path = old.ART/f'{year}_samples.npz'
        record = old.read(path.with_suffix('.json'))
        if record['residual_targets_end'] != f'{year+1}-12' or old.digest(path) != record['sha256']:
            raise ValueError('Amostra histórica inválida')
        pieces.append(old.samples(year))
    return years, np.concatenate([v[0] for v in pieces]), np.concatenate([v[1] for v in pieces])


def fitted(cutoff, region, leaves, years, x, y):
    path = ART/f'{cutoff}_{region}{leaves}.joblib'
    if path.exists():
        record = old.read(path.with_suffix('.json'))
        if old.digest(path) != record['sha256'] or record['training_blocks'] != years:
            raise ValueError('Especialista alterado')
        return joblib.load(path)
    mask = training_mask(x[:,0], region)
    if mask.sum() < 1000: raise ValueError('Amostras regionais insuficientes')
    model = HistGradientBoostingRegressor(max_leaf_nodes=leaves, **TREE).fit(x[mask], y[mask])
    joblib.dump(model, path); saved = joblib.load(path)
    np.testing.assert_array_equal(model.predict(x[mask][:2048]), saved.predict(x[mask][:2048]))
    old.save_json(path.with_suffix('.json'), dict(sha256=old.digest(path), region=region,
        leaves=leaves, training_blocks=years, last_training_target=f'{years[-1]+1}-12',
        samples=int(mask.sum()), official_only=True))
    print('TREINADO', cutoff, region, leaves, int(mask.sum()), flush=True)
    return saved


def evaluate_block(cutoff):
    locked(); prior.audit()
    result_path = OUT/f'{cutoff}.json'
    if result_path.exists(): print('BLOCO EXISTENTE', cutoff, flush=True); return
    years, x_train, y_train = samples(cutoff)
    models = {(region, leaf): fitted(cutoff, region, leaf, years, x_train, y_train)
              for leaf in LEAVES for region in REGIONS}
    del x_train, y_train
    global_model = old.fitted(cutoff, 15)
    s11 = old.reference(cutoff).reshape(24, -1)
    ref = prior.reference(cutoff).reshape(24, -1)
    truth = np.load(old.CACHE/'tp.npy', mmap_mode='r')[old.target_origins(cutoff)+1]
    candidate = {name: np.empty((24, 301, 261), np.float32) for name in CONFIGS}
    cells = np.arange(78561); latitude = -60+(cells//261)*.25; w = weights(latitude)
    for month in range(24):
        matrix = old.matrix(cutoff, month, cells)
        global_delta = global_model.predict(matrix)
        baseline = np.maximum(s11[month]+.25*global_delta, 0)
        np.testing.assert_allclose(baseline, ref[month], rtol=0, atol=1e-7)
        for leaf in LEAVES:
            regional_delta = np.zeros(78561)
            for index, region in enumerate(REGIONS):
                active = w[:,index] > 0
                regional_delta[active] += w[active,index]*models[(region,leaf)].predict(matrix[active])
            for beta in BETAS:
                name = f'region{leaf}_b{beta:g}'
                candidate[name][month] = np.maximum(s11[month]+.25*((1-beta)*global_delta+beta*regional_delta),0).reshape(301,261)
        print('MÊS', cutoff, month+1, flush=True)
    rows = [dict(model='s12', **old.metrics(ref.reshape(24,301,261), truth, ref.reshape(24,301,261)))]
    for name, pred in candidate.items():
        path = ART/f'{cutoff}_{name}.npy'; np.save(path, pred)
        old.save_json(path.with_suffix('.json'), dict(sha256=old.digest(path), model=name,
            cutoff=cutoff, official_only=True))
        rows.append(dict(model=name, **old.metrics(pred, truth, ref.reshape(24,301,261))))
    old.save_json(result_path, rows)
    print('RESULTADOS', cutoff, [(r['model'], round(r['rmse'],6)) for r in rows], flush=True)
    del candidate, models, s11, ref, truth
    old.data.cache_clear(); old.reference.cache_clear(); gc.collect()


def evaluate():
    for year in old.DEV: evaluate_block(year)


def select():
    locked()
    records = {year: old.read(OUT/f'{year}.json') for year in old.DEV}
    refs = np.array([records[year][0]['monthly_rmse'] for year in old.DEV])
    ref = float(np.sqrt(np.mean(refs**2)))
    ref_second = float(np.sqrt(np.mean(refs[:,12:]**2)))
    ref_years = np.sqrt(np.mean(refs.reshape(-1,12)**2,axis=1))
    ranking = []
    for name in CONFIGS:
        rows = [next(r for r in records[year] if r['model']==name) for year in old.DEV]
        months = np.array([r['monthly_rmse'] for r in rows])
        years = np.sqrt(np.mean(months.reshape(-1,12)**2,axis=1))
        rmse = float(np.sqrt(np.mean(months**2)))
        second = float(np.sqrt(np.mean(months[:,12:]**2)))
        blocks = int(np.sum(np.mean(months**2,axis=1) < np.mean(refs**2,axis=1)))
        nyears = int(np.sum(years < ref_years)); nmonths = int(np.sum(months < refs))
        worst = float(np.max(years/ref_years-1))
        ranking.append(dict(model=name, rmse=rmse, relative_gain=1-rmse/ref,
            second_year_rmse=second, blocks_improved=blocks, years_improved=nyears,
            months_improved=nmonths, worst_annual_relative_change=worst,
            historical_correction_rms=float(np.sqrt(np.mean([r['correction_rms']**2 for r in rows]))),
            passed=passes_gate(rmse,ref,second,ref_second,blocks,nyears,nmonths,144,worst)))
    ranking.sort(key=lambda v:v['rmse']); eligible = [r for r in ranking if r['passed']]
    result = dict(reference='S12', reference_rmse=ref, minimum_relative_gain=.003,
                  ranking=ranking, selected=eligible[0]['model'] if eligible else None,
                  periods_reused=True, csv_exported=False, uploaded=False)
    path = OUT/'selection.json'
    if path.exists() and old.read(path)!=result: raise ValueError('Seleção alterada')
    old.save_json(path,result); print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)


def summarize():
    locked(); selected = old.read(OUT/'selection.json')
    lines = ['# Rodada 21 — especialistas regionais', '',
             f"S12 histórica: {selected['reference_rmse']:.6f} mm/dia.",
             'Períodos reutilizados; sem teste independente. Somente dados oficiais.', '',
             '| Candidata | RMSE | Ganho | Blocos | Anos | Meses | Aprovada |',
             '| --- | ---: | ---: | ---: | ---: | ---: | --- |']
    for r in selected['ranking']:
        lines.append(f"| {r['model']} | {r['rmse']:.6f} | {100*r['relative_gain']:.3f}% | "
                     f"{r['blocks_improved']}/6 | {r['years_improved']}/12 | "
                     f"{r['months_improved']}/144 | {r['passed']} |")
    lines += ['', f"Selecionada: {selected['selected'] or 'nenhuma'}.",
              'Nenhuma submissão foi exportada ou enviada nesta rodada.']
    (OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines),flush=True)


if __name__=='__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('evaluate','select','summarize'))
    parser.add_argument('--year',type=int)
    args=parser.parse_args()
    if args.year is not None:
        if args.stage!='evaluate' or args.year not in old.DEV: raise ValueError('Corte inválido')
        evaluate_block(args.year)
    else: globals()[args.stage]()
