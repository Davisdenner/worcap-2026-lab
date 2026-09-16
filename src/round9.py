"""Official-only experiments with forward-fitted base weights and residuals."""
from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.metadata
import json
import time
from pathlib import Path

import joblib
import numpy as np
import xarray as xr
from scipy.ndimage import uniform_filter
from sklearn.cross_decomposition import PLSRegression
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingRegressor

from .competition import ROOT, RAW, CACHE, REPORT, VARIABLES, save_json, score
from .round2 import Features, target_origins, trees, ridge
from .round3 import seasonal_design, seasonal_local
from .round4 import groups, fit_weights, memory, predict as atmospheric_modes
from .round6 import local_memory

ART = ROOT / 'data/processed/round9'
OUT = REPORT / 'round9'
SEEDS = (2005, 2007)
DEVELOPMENT = (2009, 2011, 2013, 2015, 2017, 2019)
ALL_HISTORY = SEEDS + DEVELOPMENT + (2021,)
CALIBRATION = (2013, 2015, 2017, 2019)
PRIOR = np.array([.5, .25, .25])
FRACTIONS = (.25, .5)
TREE_LEAVES = (7, 15)
PLS_COMPONENTS = (8, 16)
SAMPLE_SIZE = 2048
SEED = 20260916
PROTOCOL = ROOT / 'experiments/ROUND9.md'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def lock_protocol():
    ART.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / 'protocol.json'
    value = dict(protocol_sha256=digest(PROTOCOL), only_official_data=True,
                 seed_years=list(SEEDS), development_years=list(DEVELOPMENT),
                 confirmation_year=2021, confirmation_previously_consumed=True,
                 model_candidates=[f'{family}{n}_{a:g}'
                                   for family, ns in [('tree', TREE_LEAVES), ('pls', PLS_COMPONENTS)]
                                   for n in ns for a in FRACTIONS])
    if path.exists() and read(path) != value:
        raise RuntimeError('Frozen protocol changed')
    if not path.exists():
        save_json(path, value)
    return value


def audit():
    lock_protocol()
    result = dict(official_sources={}, cache_equal={}, coarse_max_abs_error={})
    coarse = np.load(ROOT / 'data/processed/round3/coarse_weather.npy', mmap_mode='r')
    with xr.open_dataset(RAW / 'teste_features.nc') as test:
        for name in ['tp'] + VARIABLES:
            source = RAW / f'treino_{name}.nc'
            cache = np.load(CACHE / f'{name}.npy', mmap_mode='r')
            with xr.open_dataset(source) as ds:
                if tuple(ds[name].shape) != cache.shape:
                    raise ValueError('Official cache shape mismatch')
                for start in range(0, len(cache), 48):
                    np.testing.assert_array_equal(ds[name].isel(time=slice(start, start+48)).values,
                                                  cache[start:start+48])
            result['official_sources'][source.name] = digest(source)
            result['cache_equal'][name] = True
            if name != 'tp':
                j = VARIABLES.index(name)
                stop = (j+1)*38*33
                error = 0.
                for start in range(0, len(cache), 48):
                    actual = uniform_filter(cache[start:start+48], size=(1,9,9), mode='nearest')[:,::8,::8]
                    expected = coarse[start:start+len(actual), j*38*33:stop]
                    error = max(error, float(np.max(np.abs(actual.reshape(len(actual), -1)-expected))))
                actual = uniform_filter(test[name].values[1:], size=(1,9,9), mode='nearest')[:,::8,::8]
                error = max(error, float(np.max(np.abs(actual.reshape(23,-1)-coarse[996:, j*38*33:stop]))))
                if error != 0:
                    raise ValueError(f'Coarse cache mismatch: {name}: {error}')
                result['coarse_max_abs_error'][name] = error
            print('AUDIT', name, 'official cache equal', flush=True)
    result['official_sources']['teste_features.nc'] = digest(RAW / 'teste_features.nc')
    result['coarse_sha256'] = digest(ROOT / 'data/processed/round3/coarse_weather.npy')
    result['allowed_component_sources'] = ['round2', 'round3', 'round4', 'round6']
    result['excluded'] = ['data/external', 'data/interim', 'round7', 'round8']
    result['passed'] = True
    save_json(OUT / 'audit.json', result)


def preceding(years, cutoff):
    """Only complete two-year blocks strictly before cutoff's target months."""
    return [y for y in years if y+2 <= cutoff]


def forward_weights(cutoff):
    years = preceding(CALIBRATION, cutoff)
    if not years:
        return np.tile(PRIOR, (12,1)), years
    mask = groups()
    tp = np.load(CACHE / 'tp.npy', mmap_mode='r')
    covariance = []
    for year in years:
        p = np.stack([np.load(ROOT / f'data/processed/round3/{year}_submission02.npy'),
                      np.load(ROOT / f'data/processed/round4/{year}_mean3_0.3.npy'),
                      np.load(ROOT / f'data/processed/round3/{year}_seasonal_0.3.npy')]).astype(float)
        error = p-tp[target_origins(year)+1]
        covariance.append(np.stack([error[:,mask==g]@error[:,mask==g].T/(mask==g).sum()
                                    for g in range(12)]))
    return np.stack([fit_weights(c) for c in np.mean(covariance,axis=0)]), years


def combine(pieces, weights):
    return np.sum(pieces * weights[groups()].transpose(3,0,1,2), axis=0)


def base_components(f):
    """Build only official-data components; never load S07/S08 artifacts."""
    year = f.year
    paths = [ART / f'{year}_{key}.npy' for key in ('s02','modes','local18')]
    if all(p.exists() for p in paths):
        return np.stack([np.load(p) for p in paths])
    if year in CALIBRATION:
        sources = [ROOT / f'data/processed/round3/{year}_submission02.npy',
                   ROOT / f'data/processed/round4/{year}_mean3_0.3.npy',
                   ROOT / f'data/processed/round6/{year}_memory_0.3.npy']
        pieces = [np.load(p) for p in sources]
        provenance = [dict(path=p.relative_to(ROOT).as_posix(), sha256=digest(p)) for p in sources]
    elif year == 2023:
        with xr.open_dataset(ROOT / 'data/processed/round2/submission_02_predictions.nc') as ds:
            s02 = ds.tp_mm_day.values.copy()
        regional = next(atmospheric_modes(f, ('mean3',), (.3,)))[1]
        local = np.load(ROOT / 'data/processed/round6/final_memory_0.3.npy')
        pieces = [s02, regional, local]
        provenance = ['official S02 final', 'recomputed official mean3', 'official local18 final']
    else:
        def cached(key, fn):
            p = ART / f'{year}_{key}.npy'
            if not p.exists():
                print('BASE', year, key, flush=True)
                np.save(p, fn())
            return np.load(p)
        localtree = cached('localtree', lambda: trees(f,False)['local_150'])
        context = cached('context', lambda: trees(f,True,(150,300))['context_300'])
        linear = cached('linear', lambda: ridge(f))
        climatology = f.climo[(target_origins(year)+1)%12].reshape(24,301,261)
        s02 = .5*context+.25*localtree+.125*linear+.125*climatology
        regional = cached('modes', lambda: next(atmospheric_modes(f, ('mean3',), (.3,)))[1])
        local = cached('local18', lambda: local_memory(f)[.3])
        pieces = [s02, regional, local]
        provenance = ['recomputed from official inputs with temporal cutoff']
    for path, values in zip(paths,pieces):
        if not path.exists():
            np.save(path,values)
    save_json(ART / f'{year}_base_provenance.json', dict(sources=provenance,
              training_target_end=f'{year-1}-12', official_only=True,
              outputs={p.name:digest(p) for p in paths}))
    return np.stack(pieces)


def reference(f, pieces):
    weights, years = forward_weights(f.year)
    pred = combine(pieces,weights)
    path = ART / f'{f.year}_reference.npy'
    if path.exists():
        np.testing.assert_allclose(np.load(path),pred,rtol=0,atol=1e-10)
    else:
        np.save(path,pred)
    save_json(ART / f'{f.year}_weights.json', dict(calibration_years=years,weights=weights.tolist(),
              all_calibration_targets_before_cutoff=True,cutoff=f'{f.year}-01'))
    if f.year == 2023:
        original = np.asarray(read(REPORT / 'round4/calibration.json')['final_weights'])
        np.testing.assert_allclose(weights, original, rtol=0, atol=1e-10)
        with xr.open_dataset(ROOT / 'data/processed/round6/submission_06_predictions.nc') as ds:
            error = float(np.max(abs(pred-ds.tp_mm_day.values)))
            if error > 2e-5:
                raise ValueError(f'Final S06 reconstruction failed: {error}')
        save_json(OUT / 's06_reconstruction.json', dict(max_abs_error=error,passed=True))
    return pred


def residual_features(f, origin, cells, pieces, pred, position):
    """Causal official context and numerical model predictions, no rain history."""
    x = f.matrix(origin,cells,context=True)
    mean6 = np.empty((len(cells),9),np.float32)
    regional = []
    band = np.digitize(f.lat,[-30,-10])
    for j in range(9):
        mean6[:,j] = sum(f.row(j,origin-k)[cells]-f.means[(origin-k)%12,cells,j] for k in range(6))/6
        anomaly = f.row(j,origin)-f.means[origin%12,:,j]
        regional.extend(float(anomaly[band==b].mean()) for b in range(3))
    components = pieces[:,position].reshape(3,-1)[:,cells].T
    base = pred[position].ravel()[cells,None]
    features = np.column_stack([x,mean6,np.broadcast_to(regional,(len(cells),27)),
                                components,base,components-base]).astype(np.float32)
    if features.shape[1] != 98 or not np.isfinite(features).all():
        raise ValueError('Invalid residual features')
    return features


def samples(f,pieces,pred):
    path = ART / f'{f.year}_samples.npz'
    if path.exists():
        return
    rng = np.random.default_rng(SEED+f.year)
    x = np.empty((24*SAMPLE_SIZE,98),np.float32)
    y = np.empty(len(x),np.float32)
    for k,o in enumerate(target_origins(f.year)):
        cells = rng.choice(301*261,SAMPLE_SIZE,replace=False)
        sl = slice(k*SAMPLE_SIZE,(k+1)*SAMPLE_SIZE)
        x[sl] = residual_features(f,int(o),cells,pieces,pred,k)
        y[sl] = f.tp[o+1,cells]-pred[k].ravel()[cells]
    np.savez(path,x=x,y=y)


def fit_correctors(cutoff, leaves=TREE_LEAVES):
    train_years = preceding(ALL_HISTORY,cutoff)
    xx,yy = [],[]
    for year in train_years:
        with np.load(ART / f'{year}_samples.npz') as data:
            xx.append(data['x']); yy.append(data['y'])
    if not xx:
        raise ValueError('No earlier out-of-training predictions')
    x,y = np.concatenate(xx),np.concatenate(yy)
    del xx,yy
    models = {}
    for n in leaves:
        path = ART / f'{cutoff}_tree{n}.joblib'
        if path.exists():
            models[n] = joblib.load(path)
            continue
        print('CORRECTOR',cutoff,'leaves',n,'training blocks',train_years,flush=True)
        model = HistGradientBoostingRegressor(max_iter=150,max_leaf_nodes=n,
                    learning_rate=.05,min_samples_leaf=200,l2_regularization=20,
                    early_stopping=False,loss='squared_error',random_state=SEED)
        model.fit(x,y)
        models[n] = model
        joblib.dump(model,path)
    save_json(ART / f'{cutoff}_corrector_provenance.json',dict(training_blocks=train_years,
              last_training_target=f'{max(train_years)+1}-12',sample_count=len(y),official_only=True))
    return models


def corrections(f,pieces,pred,leaves=TREE_LEAVES):
    paths = {n:ART / f'{f.year}_tree{n}_correction.npy' for n in leaves}
    if all(p.exists() for p in paths.values()):
        return {n:np.load(p) for n,p in paths.items()}
    models = fit_correctors(f.year,leaves)
    output = {n:np.empty_like(pred,dtype=np.float32) for n in leaves}
    cells = np.arange(301*261)
    for k,o in enumerate(target_origins(f.year)):
        x = residual_features(f,int(o),cells,pieces,pred,k)
        for n,model in models.items():
            output[n][k] = model.predict(x).reshape(301,261)
        if (k+1)%6 == 0:
            print('CORRECTION PREDICTION',f.year,k+1,'/24',flush=True)
    for n,p in paths.items():
        np.save(p,output[n])
    return output


def pls_models(f, counts=PLS_COMPONENTS):
    paths = {n: ART / f'{f.year}_pls{n}.npy' for n in counts}
    if all(p.exists() for p in paths.values()):
        return {n:np.load(p) for n,p in paths.items()}
    raw = np.load(ROOT / 'data/processed/round3/coarse_weather.npy',mmap_mode='r')
    idx,origins = f.idx,target_origins(f.year)
    means = np.stack([raw[idx[idx%12==m]].mean(axis=0) for m in range(12)])
    train = raw[idx]-means[idx%12]
    scale = np.maximum(train.std(axis=0),1e-8)
    pca = PCA(n_components=64,svd_solver='randomized',random_state=SEED)
    pca.fit(train/scale)
    take = np.arange(origins[-1]+1)
    z = pca.transform((raw[take]-means[take%12])/scale)
    pc_scale = np.maximum(z[idx].std(axis=0),1e-8)
    z /= pc_scale
    x = seasonal_design(memory(z,idx,'mean3'),idx)[:,1:]
    xv = seasonal_design(memory(z,origins,'mean3'),origins)[:,1:]
    x_scale = np.maximum(x.std(axis=0),1e-8)
    x,xv = x/x_scale,xv/x_scale
    y = f.tp[idx+1]-f.climo[(idx+1)%12]
    rain = PCA(n_components=32,svd_solver='randomized',random_state=SEED)
    target_scores = rain.fit_transform(y)
    print('PLS',f.year,'training pairs',len(idx),'rain variance',rain.explained_variance_ratio_.sum(),flush=True)
    result = {}
    for n in counts:
        if paths[n].exists():
            result[n] = np.load(paths[n]); continue
        pls = PLSRegression(n_components=n,scale=False,max_iter=1000,tol=1e-7)
        pls.fit(x,target_scores)
        scores = pls.transform(x)
        score_scale = np.maximum(scores.std(axis=0),1e-8)
        design = np.column_stack([np.ones(len(idx)),scores/score_scale])
        valid = np.column_stack([np.ones(24),pls.transform(xv)/score_scale])
        penalty = .3*np.eye(n+1); penalty[0,0] = 0
        coefficients = np.linalg.solve(design.T@design/len(idx)+penalty,design.T@y/len(idx))
        pred = np.maximum(f.climo[(origins+1)%12]+valid@coefficients,0).astype(np.float32).reshape(24,301,261)
        np.save(paths[n],pred)
        joblib.dump(dict(pca=pca,means=means,scale=scale,pc_scale=pc_scale,x_scale=x_scale,
                    pls=pls,score_scale=score_scale,coefficients=coefficients,
                    climatology=f.climo,training_cutoff=f'{f.year}-01',official_only=True),
                    ART / f'{f.year}_pls{n}.joblib')
        result[n] = pred
    return result


def metrics(pred,truth,ref):
    row = score(pred,truth)
    row['correction_rms'] = float(np.sqrt(np.mean((pred-ref)**2)))
    row['correction_monthly_rms'] = np.sqrt(np.mean((pred-ref)**2,axis=(1,2))).tolist()
    row['regional_rmse'] = [float(np.sqrt(np.mean((pred[:,sl]-truth[:,sl])**2)))
                            for sl in (slice(0,120),slice(120,200),slice(200,301))]
    return row


def evaluate():
    lock_protocol()
    if not read(OUT / 'audit.json')['passed']:
        raise RuntimeError('Official data audit required')
    for year in SEEDS+DEVELOPMENT:
        if (ART / f'{year}_samples.npz').exists() and (year in SEEDS or (OUT / f'{year}.json').exists()):
            print('CACHED',year,flush=True); continue
        start = time.monotonic()
        f = Features(year)
        pieces = base_components(f)
        ref = reference(f,pieces)
        # A block's labels only enter the corrector of a later block.
        samples(f,pieces,ref)
        if year in DEVELOPMENT:
            truth = f.tp[target_origins(year)+1].reshape(24,301,261)
            rows = [dict(model='s06_forward',**metrics(ref,truth,ref))]
            for n,delta in corrections(f,pieces,ref).items():
                for a in FRACTIONS:
                    name = f'tree{n}_{a:g}'
                    pred = np.maximum(ref+a*delta,0)
                    np.save(ART / f'{year}_{name}.npy',pred)
                    rows.append(dict(model=name,**metrics(pred,truth,ref)))
            for n,new in pls_models(f).items():
                for a in FRACTIONS:
                    name = f'pls{n}_{a:g}'
                    pred = (1-a)*ref+a*new
                    np.save(ART / f'{year}_{name}.npy',pred)
                    rows.append(dict(model=name,**metrics(pred,truth,ref)))
            save_json(OUT / f'{year}.json',rows)
            print('RESULT',year,[(r['model'],round(r['rmse'],6)) for r in rows],flush=True)
        print('FINISHED BLOCK',year,round(time.monotonic()-start,1),'s',flush=True)
        del f,pieces,ref
        gc.collect()


def passes_gate(pooled, reference_rmse, second, reference_second, blocks, years, months, total_months, worst):
    """Fixed pre-registered promotion gate, not a leaderboard-tuned threshold."""
    return bool(pooled <= reference_rmse*.997 and second<reference_second and blocks>=5
                and years>=9 and months>=.55*total_months and worst<=.005)


def select():
    lock_protocol()
    records = {y:read(OUT / f'{y}.json') for y in DEVELOPMENT}
    reference_rows = [records[y][0] for y in DEVELOPMENT]
    refs = np.array([r['monthly_rmse'] for r in reference_rows])
    ref = float(np.sqrt(np.mean(refs**2)))
    ref_second = float(np.sqrt(np.mean(refs[:,12:]**2)))
    ranking = []
    for name in lock_protocol()['model_candidates']:
        rows = [next(r for r in records[y] if r['model']==name) for y in DEVELOPMENT]
        months = np.array([r['monthly_rmse'] for r in rows])
        annual = np.sqrt(np.mean(months.reshape(-1,12)**2,axis=1))
        ref_annual = np.sqrt(np.mean(refs.reshape(-1,12)**2,axis=1))
        pooled = float(np.sqrt(np.mean(months**2)))
        second = float(np.sqrt(np.mean(months[:,12:]**2)))
        blocks = int(np.sum(np.mean(months**2,axis=1)<np.mean(refs**2,axis=1)))
        years = int(np.sum(annual<ref_annual))
        monthly = int(np.sum(months<refs))
        worst = float(np.max(annual/ref_annual-1))
        passed = passes_gate(pooled,ref,second,ref_second,blocks,years,monthly,months.size,worst)
        ranking.append(dict(model=name,rmse=pooled,relative_gain=1-pooled/ref,
                    second_year_rmse=second,blocks_improved=blocks,years_improved=years,
                    months_improved=monthly,worst_annual_relative_change=worst,passed=bool(passed),
                    historical_correction_rms=float(np.sqrt(np.mean([r['correction_rms']**2 for r in rows])))))
    ranking.sort(key=lambda r:r['rmse'])
    eligible = [r for r in ranking if r['passed']]
    result = dict(selected=eligible[0]['model'] if eligible else None,
                  reference_rmse=ref,reference_second_year_rmse=ref_second,ranking=ranking,
                  caveat='Forward-fitted parameters; reused development and retrospective architecture selection, not independent test')
    path = OUT / 'selection.json'
    if path.exists() and read(path)!=result:
        raise RuntimeError('Do not alter a frozen selection')
    save_json(path,result)
    print(json.dumps(result,indent=2),flush=True)


def selected_prediction(f,pieces,ref,name):
    family,a = name.split('_'); a = float(a)
    if family.startswith('tree'):
        n = int(family[4:])
        return np.maximum(ref+a*corrections(f,pieces,ref,(n,))[n],0)
    n = int(family[3:])
    return (1-a)*ref+a*pls_models(f,(n,))[n]


def confirm():
    lock_protocol()
    name = read(OUT / 'selection.json')['selected']
    if name is None:
        raise RuntimeError('No eligible candidate: preserve submissions')
    path = OUT / 'confirmation.json'
    if path.exists():
        print(json.dumps(read(path),indent=2)); return
    f = Features(2021)
    pieces = base_components(f)
    ref = reference(f,pieces)
    pred = selected_prediction(f,pieces,ref,name)
    np.save(ART / f'2021_{name}.npy',pred)
    truth = f.tp[target_origins(2021)+1].reshape(24,301,261)
    base,candidate = metrics(ref,truth,ref),metrics(pred,truth,ref)
    passed = (candidate['rmse']<=base['rmse']*.999 and
              all(candidate[k]<base[k] for k in ('year1_rmse','year2_rmse')))
    save_json(path,dict(candidate=name,reference=base,result=candidate,passed=bool(passed),
                       previously_consumed_period=True,no_post_confirmation_tuning=True))
    # Only subsequent final fitting may use this block as training examples.
    samples(f,pieces,ref)
    print(json.dumps(read(path),indent=2),flush=True)


def final():
    lock_protocol()
    selection = read(OUT / 'selection.json')
    name = selection['selected']
    check = read(OUT / 'confirmation.json')
    if not name or not check['passed'] or check['candidate']!=name:
        raise RuntimeError('Candidate not approved')
    destination = ROOT / 'submissions/submission_09.csv'
    if destination.exists():
        raise FileExistsError(destination)
    f = Features(2023,final=True)
    pieces = base_components(f)
    ref = reference(f,pieces)
    pred = selected_prediction(f,pieces,ref,name)
    historical = next(r['historical_correction_rms'] for r in selection['ranking'] if r['model']==name)
    public_change = float(np.sqrt(np.mean((pred[:12]-ref[:12])**2)))
    shift_passed = public_change<=2*historical
    save_json(OUT / 'test_shift.json',dict(candidate=name,historical_rms=historical,
              public2023_change_rms=public_change,passed=bool(shift_passed),unknown_test_error=True))
    if not shift_passed:
        raise RuntimeError('Excessive test correction: no export; no retuning')
    from .submission import export_csv
    with xr.open_dataset(RAW / 'teste_features.nc') as grid:
        da = xr.DataArray(pred,dims=('time','lat','lon'),
                         coords={d:grid[d] for d in ('time','lat','lon')},name='tp_mm_day')
        da.attrs.update(units='mm/day',model=name,official_only='true')
        nc = ART / 'submission_09_predictions.nc'
        da.to_netcdf(nc)
        report = export_csv(da,grid,destination,RAW / 'sample_submission.csv')
    report.update(model=name,official_data_only=True,external_sources=[],
                  development_selection=selection,confirmation=check,uploaded=False,public_score=None,
                  training_targets_end='2022-12',csv_sha256=digest(destination),
                  script_sha256=digest(Path(__file__)),protocol_sha256=digest(PROTOCOL),
                  official_data_audit_sha256=digest(OUT / 'audit.json'),
                  dependency_script_hashes={filename:digest(ROOT / 'src' / filename)
                    for filename in ('competition.py','round2.py','round3.py','round4.py','round6.py','submission.py')},
                  final_artifact_hashes={p.name:digest(p) for p in ART.glob('2023_*') if p.is_file()},
                  versions={package:importlib.metadata.version(package)
                    for package in ('numpy','scipy','scikit-learn','xarray','pandas')})
    save_json(destination.with_suffix('.json'),report)
    print(json.dumps(report,indent=2),flush=True)


def summarize():
    """Generate a human-readable record without training or reading test labels."""
    selection = read(OUT / 'selection.json')
    lines = ['# Rodada 9 — resultados com dados oficiais', '',
             'RMSE em mm/dia, 144 meses de 2009–2020, grade inteira e pesos uniformes.',
             'Referência S06-forward: componentes da S06, pesos calibrados somente no passado.',
             'Não comparar estes números diretamente ao score público de 2023.', '',
             f"Referência agrupada: **{selection['reference_rmse']:.6f}**; segundos anos: "
             f"**{selection['reference_second_year_rmse']:.6f}**.", '',
             '| Candidata | RMSE | Ganho relativo | Segundos anos | Blocos melhores | Anos melhores | Meses melhores | Passou? |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |']
    for r in selection['ranking']:
        lines.append(f"| {r['model']} | {r['rmse']:.6f} | {100*r['relative_gain']:.3f}% | "
                     f"{r['second_year_rmse']:.6f} | {r['blocks_improved']}/6 | "
                     f"{r['years_improved']}/12 | {r['months_improved']}/144 | {'Sim' if r['passed'] else 'Não'} |")
    lines += ['', '## Decisão', '',
              f"Candidata selecionada no desenvolvimento: **{selection['selected'] or 'nenhuma'}**.",
              'Se nenhuma candidata passou, não gerar submissão nem gastar envio.', '',
              '## Resultado por bloco', '',
              '| Bloco | S06-forward | Melhor entre as oito (seleção retrospectiva) | RMSE |',
              '| --- | ---: | --- | ---: |']
    for year in DEVELOPMENT:
        rows = read(OUT / f'{year}.json')
        best = min(rows[1:],key=lambda r:r['rmse'])
        lines.append(f"| {year}–{year+1} | {rows[0]['rmse']:.6f} | {best['model']} | {best['rmse']:.6f} |")
    lines += ['', 'A melhor candidata de cada bloco acima não é um modelo selecionável em tempo real.',
              'A decisão usa uma única configuração entre todos os blocos, não escolhe um vencedor por ano.', '',
              '## Limitações e conformidade', '',
              '- Caches oficiais conferidos contra todos os valores dos NetCDF; cache espacial reproduzido exatamente.',
              '- Sem NOAA, S07/S08, modelos externos ou chuva oculta do teste.',
              '- Corretores treinados somente em blocos anteriores de previsões fora do treino.',
              '- Seleção anterior de arquitetura e desenvolvimento reutilizado impedem alegar teste inteiramente independente.',
              '- 2021–2022 já foi consumido na rodada 8. Se usado aqui, serve apenas como confirmação adicional.',
              '- Nenhum RMSE local garante score 1,70, liderança pública ou resultado privado.',
              '- Nenhum upload automático foi realizado.', '',
              '[Protocolo congelado](../../../experiments/ROUND9.md) · [Seleção detalhada](selection.json) · [Auditoria](audit.json)']
    if (OUT / 'confirmation.json').exists():
        c = read(OUT / 'confirmation.json')
        lines += ['', '## Confirmação 2021–2022 (período previamente utilizado)', '',
                  f"{c['candidate']}: {c['reference']['rmse']:.6f} → {c['result']['rmse']:.6f}.",
                  f"Passou: {'sim' if c['passed'] else 'não'}. Nenhum ajuste posterior autorizado pelo protocolo."]
    (OUT / 'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines),flush=True)


def verify_pls():
    """Reconstruct saved PLS predictions without fitting or accessing rain labels."""
    raw = np.load(ROOT / 'data/processed/round3/coarse_weather.npy',mmap_mode='r')
    result = {}
    for year in DEVELOPMENT:
        origins = target_origins(year)
        take = np.arange(origins[-1]+1)
        for n in PLS_COMPONENTS:
            model = joblib.load(ART / f'{year}_pls{n}.joblib')
            z = model['pca'].transform((raw[take]-model['means'][take%12])/model['scale'])/model['pc_scale']
            xv = seasonal_design(memory(z,origins,'mean3'),origins)[:,1:]/model['x_scale']
            valid = np.column_stack([np.ones(24),model['pls'].transform(xv)/model['score_scale']])
            actual = np.maximum(model['climatology'][(origins+1)%12]+valid@model['coefficients'],0)
            actual = actual.astype(np.float32).reshape(24,301,261)
            expected = np.load(ART / f'{year}_pls{n}.npy')
            error = float(np.max(abs(actual-expected)))
            if error > 2e-5:
                raise ValueError(f'PLS reconstruction mismatch: {year} {n}: {error}')
            result[f'{year}_pls{n}'] = error
    save_json(OUT / 'pls_reconstruction.json',dict(max_absolute_errors=result,passed=True))
    print('PLS reconstruction PASS; maximum error:',max(result.values()),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('audit','evaluate','select','confirm','final','summarize','verify_pls'))
    globals()[parser.parse_args().stage]()
