"""Small forward-only PLS correction of S09; official data and frozen gates."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
from pathlib import Path
import warnings

import joblib
import numpy as np
import xarray as xr
from sklearn.cross_decomposition import PLSRegression
from sklearn.decomposition import PCA
from sklearn.exceptions import ConvergenceWarning

from .competition import ROOT, RAW, CACHE, REPORT, VARIABLES, save_json, score
from .round2 import Features, target_origins
from .round3 import seasonal_design
from .round4 import memory, groups
from . import round9 as r9

ART = ROOT / 'data/processed/round10'
OUT = REPORT / 'round10'
PROTOCOL = ROOT / 'experiments/ROUND10.md'
SEEDS = (2005,2007)
DEV = (2009,2011,2013,2015,2017,2019)
HISTORY = SEEDS+DEV+(2021,)
COUNTS = (2,4,8)
FRACTIONS = (.25,.5)
SEED = 20260916


def locked():
    ART.mkdir(parents=True,exist_ok=True)
    OUT.mkdir(parents=True,exist_ok=True)
    metadata = r9.read(ROOT / 'submissions/submission_09.json')
    value = dict(protocol_sha256=r9.digest(PROTOCOL),official_only=True,
                 s09_sha256=metadata['csv_sha256'],counts=list(COUNTS),fractions=list(FRACTIONS),
                 ridge=1.,seed=SEED,development=list(DEV),seed_blocks=list(SEEDS),
                 confirmation=2021,confirmation_previously_consumed=True)
    path = OUT / 'protocol.json'
    if path.exists() and r9.read(path)!=value:
        raise RuntimeError('Frozen protocol changed')
    if not path.exists():
        save_json(path,value)
    return value


def audit():
    locked()
    previous = r9.read(REPORT / 'round9/audit.json')
    metadata = r9.read(ROOT / 'submissions/submission_09.json')
    if r9.digest(ROOT / 'submissions/submission_09.csv')!=metadata['csv_sha256']:
        raise ValueError('S09 changed')
    if r9.digest(ROOT / 'src/round9.py')!=metadata['script_sha256']:
        raise ValueError('Frozen S09 implementation changed')
    for filename,expected in metadata['dependency_script_hashes'].items():
        if r9.digest(ROOT / 'src' / filename)!=expected:
            raise ValueError(f'S09 dependency changed: {filename}')
    for filename,expected in previous['official_sources'].items():
        if r9.digest(RAW / filename)!=expected:
            raise ValueError(f'Official source changed: {filename}')
    for name in ['tp']+VARIABLES:
        values = np.load(CACHE / f'{name}.npy',mmap_mode='r')
        with xr.open_dataset(RAW / f'treino_{name}.nc') as ds:
            if values.shape!=ds[name].shape:
                raise ValueError('Official cache shape mismatch')
            for start in range(0,len(values),48):
                np.testing.assert_array_equal(values[start:start+48],ds[name].isel(time=slice(start,start+48)).values)
        print('AUDIT official cache',name,flush=True)
    coarse = ROOT / 'data/processed/round3/coarse_weather.npy'
    if r9.digest(coarse)!=previous['coarse_sha256']:
        raise ValueError('Audited atmospheric spatial cache changed')
    for filename,expected in metadata['final_artifact_hashes'].items():
        if r9.digest(r9.ART / filename)!=expected:
            raise ValueError(f'S09 final model artifact changed: {filename}')
    save_json(OUT / 'audit.json',dict(passed=True,official_only=True,
              inherited_audit_sha256=r9.digest(REPORT / 'round9/audit.json'),
              s09_csv_sha256=metadata['csv_sha256'],coarse_sha256=previous['coarse_sha256'],
              all_official_cache_values_equal=True,prior_model_artifacts_unchanged=True))


def baseline(year):
    path = ART / f'{year}_s09.npy'
    if path.exists():
        return np.load(path)
    if year==2023:
        with xr.open_dataset(r9.ART / 'submission_09_predictions.nc') as ds:
            pred = ds.tp_mm_day.values.copy()
        ref = np.load(r9.ART / '2023_reference.npy')
        pls = np.load(r9.ART / '2023_pls16.npy')
    elif year in SEEDS:
        f = Features(year)
        pls = r9.pls_models(f,(16,))[16]
        ref = np.load(r9.ART / f'{year}_reference.npy')
        pred = .75*ref+.25*pls
    elif year in DEV+(2021,):
        pred = np.load(r9.ART / f'{year}_pls16_0.25.npy')
        ref = np.load(r9.ART / f'{year}_reference.npy')
        pls = np.load(r9.ART / f'{year}_pls16.npy')
    else:
        raise ValueError('Unregistered baseline year')
    error = float(np.max(abs(pred-(.75*ref+.25*pls))))
    if error>1e-10 or not np.isfinite(pred).all() or (pred<0).any():
        raise ValueError('S09 baseline reconstruction failed')
    np.save(path,pred)
    save_json(ART / f'{year}_baseline_provenance.json',dict(year=year,model='S09',
              training_targets_end=f'{year-1}-12',max_reconstruction_error=error,
              file_sha256=r9.digest(path),official_only=True))
    return pred


def prepare():
    locked()
    if not r9.read(OUT / 'audit.json')['passed']:
        raise RuntimeError('Audit required')
    for year in SEEDS+DEV:
        baseline(year)
        print('S09 historical baseline ready',year,flush=True)


def training_origins(cutoff):
    years = r9.preceding(HISTORY,cutoff)
    if not years:
        raise ValueError('No earlier residual block')
    origins = np.concatenate([target_origins(y) for y in years])
    if np.any(origins+1 >= (cutoff-1940)*12):
        raise ValueError('Residual training target reaches validation')
    return years,origins


def weather_design(raw,model,origins):
    """Fixed transform, pointwise in time; history never exceeds each origin."""
    origins = np.asarray(origins)
    if origins.min()<2 or origins.max()>=len(raw):
        raise ValueError('Unavailable atmospheric history')
    take = np.arange(origins.max()+1)
    z = model['pca'].transform((raw[take]-model['means'][take%12])/model['scale'])/model['pc_scale']
    return seasonal_design(memory(z,origins,'mean3'),origins)[:,1:]


def fit_residual(x,y,count):
    """Reusable numerical core: all scalers, EOFs and PLS fit only these rows."""
    if len(x)!=len(y) or len(x)<=count or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('Invalid residual training matrices')
    scale = np.maximum(x.std(axis=0),1e-8)
    x = x/scale
    eof = PCA(n_components=min(16,len(y)-1,y.shape[1]),svd_solver='randomized',random_state=SEED)
    target = eof.fit_transform(y)
    pls = PLSRegression(n_components=count,scale=False,max_iter=1000,tol=1e-7)
    with warnings.catch_warnings():
        warnings.simplefilter('error',ConvergenceWarning)
        pls.fit(x,target)
    z = pls.transform(x)
    zscale = np.maximum(z.std(axis=0),1e-8)
    design = np.column_stack([np.ones(len(x)),z/zscale])
    penalty = np.eye(count+1); penalty[0,0]=0
    coef = np.linalg.solve(design.T@design/len(x)+penalty,design.T@y/len(x))
    return dict(pls=pls,x_scale=scale,score_scale=zscale,coefficients=coef,
                residual_eof_variance=float(eof.explained_variance_ratio_.sum()))


def predict_residual(model,x):
    z = model['pls'].transform(x/model['x_scale'])/model['score_scale']
    return np.column_stack([np.ones(len(x)),z])@model['coefficients']


def corrections(cutoff,counts=COUNTS):
    locked()
    years,idx = training_origins(cutoff)
    origins = target_origins(cutoff)
    raw = np.load(ROOT / 'data/processed/round3/coarse_weather.npy',mmap_mode='r')
    atmospheric = joblib.load(r9.ART / f'{cutoff}_pls16.joblib')
    if atmospheric['training_cutoff']!=f'{cutoff}-01' or not atmospheric['official_only']:
        raise ValueError('Wrong atmospheric preprocessing cutoff/provenance')
    x = weather_design(raw,atmospheric,idx)
    xv = weather_design(raw,atmospheric,origins)
    tp = np.load(CACHE / 'tp.npy',mmap_mode='r')
    y = np.concatenate([(tp[target_origins(year)+1]-baseline(year)).reshape(24,-1)
                        for year in years])
    outputs = {}
    for n in counts:
        path = ART / f'{cutoff}_residual{n}.npy'
        model_path = ART / f'{cutoff}_residual{n}.joblib'
        if model_path.exists():
            model = joblib.load(model_path)
            if model['training_blocks']!=years:
                raise ValueError('Stale residual model')
        else:
            model = fit_residual(x,y,n)
            model.update(training_blocks=years,training_target_last=f'{max(years)+1}-12',
                         cutoff=cutoff,official_only=True,
                         atmosphere_model_sha256=r9.digest(r9.ART / f'{cutoff}_pls16.joblib'))
            joblib.dump(model,model_path)
        pred = predict_residual(model,xv).reshape(24,301,261)
        if path.exists():
            np.testing.assert_allclose(pred,np.load(path),rtol=0,atol=1e-10)
        else:
            np.save(path,pred)
        check = predict_residual(joblib.load(model_path),xv).reshape(pred.shape)
        np.testing.assert_array_equal(pred,check)
        outputs[n]=pred
        print('RESIDUAL PLS',cutoff,n,'training months',len(idx),flush=True)
    save_json(ART / f'{cutoff}_training.json',dict(training_blocks=years,training_months=len(idx),
              last_target=f'{max(years)+1}-12',validation_start=f'{cutoff}-01',
              independent_forecast_residuals=True,model_reconstruction_passed=True,
              caveat='S09 architecture selected retrospectively; temporal fitting does not erase selection history'))
    return outputs


def diagnose():
    locked()
    tp = np.load(CACHE / 'tp.npy',mmap_mode='r')
    annual=[]; months=[]; regional=[]
    total_energy=0.
    for year in DEV:
        pred=baseline(year)
        truth=tp[target_origins(year)+1]
        error=pred-truth
        total_energy+=float(np.sum(error**2))
        for k in range(2):
            e=error[k*12:(k+1)*12]
            annual.append(dict(year=year+k,rmse=float(np.sqrt(np.mean(e**2))),bias=float(e.mean())))
        for k in range(24):
            months.append(dict(year=year+k//12,month=k%12+1,mse=float(np.mean(error[k]**2)),
                               bias=float(error[k].mean())))
        for band,sl in enumerate((slice(0,120),slice(120,200),slice(200,301))):
            for season in range(4):
                mask=((np.arange(24)%12+1)%12)//3==season
                e=error[mask,sl]
                regional.append(dict(year=year,band=band,season=season,n=e.size,
                                     squared_error_sum=float(np.sum(e**2)),error_sum=float(np.sum(e))))
    band_summary=[]
    for b,label in enumerate(('[-60,-30)','[-30,-10)','[-10,15]')):
        rows=[r for r in regional if r['band']==b]
        energy=sum(r['squared_error_sum'] for r in rows); n=sum(r['n'] for r in rows)
        band_summary.append(dict(latitude_band=label,rmse=float(np.sqrt(energy/n)),
                            squared_error_share=energy/total_energy,bias=sum(r['error_sum'] for r in rows)/n))
    monthly_summary=[dict(month=m,rmse=float(np.sqrt(np.mean([r['mse'] for r in months if r['month']==m]))),
                     bias=float(np.mean([r['bias'] for r in months if r['month']==m]))) for m in range(1,13)]
    report=dict(years=annual,calendar_months=monthly_summary,bands=band_summary,region_season_blocks=regional,
                scope='Only 2009-2020 historical S09 errors; not errors of hidden 2023-2024 targets')
    save_json(OUT/'diagnostic.json',report)
    print(json.dumps(dict(bands=band_summary,calendar_months=monthly_summary),indent=2),flush=True)


def evaluate():
    locked()
    if not r9.read(OUT/'audit.json')['passed'] or not (OUT/'diagnostic.json').exists():
        raise RuntimeError('Audit and diagnostic required first')
    tp=np.load(CACHE/'tp.npy',mmap_mode='r')
    for year in DEV:
        path=OUT/f'{year}.json'
        if path.exists():
            print('CACHED',year,flush=True); continue
        ref=baseline(year)
        predicted=corrections(year)
        truth=tp[target_origins(year)+1]
        rows=[dict(model='s09',**r9.metrics(ref,truth,ref))]
        for n,delta in predicted.items():
            for a in FRACTIONS:
                name=f'residual{n}_{a:g}'
                pred=np.maximum(ref+a*delta,0)
                np.save(ART/f'{year}_{name}.npy',pred)
                rows.append(dict(model=name,**r9.metrics(pred,truth,ref)))
        save_json(path,rows)
        print('RESULT',year,[(r['model'],round(r['rmse'],6)) for r in rows],flush=True)


def select():
    locked()
    records={y:r9.read(OUT/f'{y}.json') for y in DEV}
    refs=np.array([records[y][0]['monthly_rmse'] for y in DEV])
    ref=float(np.sqrt(np.mean(refs**2))); ref_second=float(np.sqrt(np.mean(refs[:,12:]**2)))
    ref_annual=np.sqrt(np.mean(refs.reshape(-1,12)**2,axis=1))
    ranking=[]
    for n in COUNTS:
        for a in FRACTIONS:
            name=f'residual{n}_{a:g}'
            rows=[next(r for r in records[y] if r['model']==name) for y in DEV]
            months=np.array([r['monthly_rmse'] for r in rows])
            annual=np.sqrt(np.mean(months.reshape(-1,12)**2,axis=1))
            pooled=float(np.sqrt(np.mean(months**2))); second=float(np.sqrt(np.mean(months[:,12:]**2)))
            blocks=int(np.sum(np.mean(months**2,axis=1)<np.mean(refs**2,axis=1)))
            years=int(np.sum(annual<ref_annual)); monthly=int(np.sum(months<refs))
            worst=float(np.max(annual/ref_annual-1))
            passed=r9.passes_gate(pooled,ref,second,ref_second,blocks,years,monthly,months.size,worst)
            ranking.append(dict(model=name,rmse=pooled,relative_gain=1-pooled/ref,second_year_rmse=second,
                      blocks_improved=blocks,years_improved=years,months_improved=monthly,
                      worst_annual_relative_change=worst,passed=passed,
                      historical_correction_rms=float(np.sqrt(np.mean([r['correction_rms']**2 for r in rows])))))
    ranking.sort(key=lambda r:r['rmse'])
    eligible=[r for r in ranking if r['passed']]
    result=dict(selected=eligible[0]['model'] if eligible else None,reference_rmse=ref,
                reference_second_year_rmse=ref_second,ranking=ranking,
                caveat='Reused development; fixed S09 architecture chosen retrospectively, not independent test')
    path=OUT/'selection.json'
    if path.exists() and r9.read(path)!=result:
        raise RuntimeError('Frozen selection changed')
    save_json(path,result)
    print(json.dumps(result,indent=2),flush=True)


def chosen(cutoff,name):
    family,a=name.split('_'); n=int(family.removeprefix('residual'))
    return np.maximum(baseline(cutoff)+float(a)*corrections(cutoff,(n,))[n],0)


def confirm():
    locked()
    name=r9.read(OUT/'selection.json')['selected']
    if name is None:
        raise RuntimeError('No approved candidate; preserve remaining submissions')
    path=OUT/'confirmation.json'
    if path.exists():
        print(json.dumps(r9.read(path),indent=2)); return
    pred=chosen(2021,name)
    ref=baseline(2021)
    tp=np.load(CACHE/'tp.npy',mmap_mode='r')
    truth=tp[target_origins(2021)+1]
    before,after=r9.metrics(ref,truth,ref),r9.metrics(pred,truth,ref)
    passed=after['rmse']<=before['rmse']*.999 and all(after[k]<before[k] for k in ('year1_rmse','year2_rmse'))
    np.save(ART/f'2021_{name}.npy',pred)
    result=dict(candidate=name,reference=before,result=after,passed=bool(passed),
                previously_consumed_period=True,no_post_confirmation_tuning=True)
    save_json(path,result)
    print(json.dumps(result,indent=2),flush=True)


def final():
    locked()
    selection=r9.read(OUT/'selection.json'); name=selection['selected']
    confirmation=r9.read(OUT/'confirmation.json')
    if not name or not confirmation['passed'] or confirmation['candidate']!=name:
        raise RuntimeError('Candidate not approved')
    destination=ROOT/'submissions/submission_10.csv'
    if destination.exists():
        raise FileExistsError(destination)
    ref=baseline(2023); pred=chosen(2023,name)
    historical=next(r['historical_correction_rms'] for r in selection['ranking'] if r['model']==name)
    changes=[float(np.sqrt(np.mean((pred[sl]-ref[sl])**2))) for sl in (slice(0,12),slice(12,24))]
    passed=all(r<=2*historical for r in changes)
    save_json(OUT/'test_shift.json',dict(historical_rms=historical,public2023_rms=changes[0],
              private2024_rms=changes[1],passed=passed,unknown_test_errors=True))
    if not passed:
        raise RuntimeError('Test correction exceeds frozen bound; no export')
    from .submission import export_csv
    with xr.open_dataset(RAW/'teste_features.nc') as grid:
        da=xr.DataArray(pred,dims=('time','lat','lon'),coords={d:grid[d] for d in ('time','lat','lon')},name='tp_mm_day')
        da.attrs.update(units='mm/day',model=name,official_only='true')
        da.to_netcdf(ART/'submission_10_predictions.nc')
        report=export_csv(da,grid,destination,RAW/'sample_submission.csv')
    report.update(model=name,base_model='S09',official_data_only=True,external_sources=[],
                  public_score=None,uploaded=False,development_selection=selection,confirmation=confirmation,
                  training_targets_end='2022-12',csv_sha256=r9.digest(destination),
                  script_sha256=r9.digest(Path(__file__)),protocol_sha256=r9.digest(PROTOCOL),
                  audit_sha256=r9.digest(OUT/'audit.json'),
                  versions={p:importlib.metadata.version(p) for p in ('numpy','scipy','scikit-learn','xarray','pandas')})
    save_json(destination.with_suffix('.json'),report)
    print(json.dumps(report,indent=2),flush=True)


def summarize():
    selection=r9.read(OUT/'selection.json')
    lines=['# Rodada 10 — correção residual da S09','',
           'Somente dados oficiais. RMSE local em 144 meses de 2009–2020; não é score do Kaggle.',
           f"Referência S09 histórica: **{selection['reference_rmse']:.6f}**.",'',
           '| Candidata | RMSE | Ganho relativo | Blocos melhores | Anos melhores | Meses melhores | Aprovada |',
           '| --- | ---: | ---: | ---: | ---: | ---: | --- |']
    for r in selection['ranking']:
        lines.append(f"| {r['model']} | {r['rmse']:.6f} | {100*r['relative_gain']:.3f}% | "
                     f"{r['blocks_improved']}/6 | {r['years_improved']}/12 | {r['months_improved']}/144 | "
                     f"{'Sim' if r['passed'] else 'Não'} |")
    lines+=['',f"Selecionada: **{selection['selected'] or 'nenhuma'}**.",
            'Se nenhuma passou, não gerar S10 e preservar os envios restantes. Não afrouxar critérios após os resultados.',
            '', '## Limitações','',
            'Os resíduos de treino vêm de previsões com cortes temporais anteriores, e o corretor só usa blocos passados.',
            'A arquitetura da S09 foi escolhida retrospectivamente. Os períodos de desenvolvimento são reutilizados.',
            '2021–2022 já foi consumido nas rodadas 8/9; não é holdout inédito.',
            'Nenhuma chuva oculta de 2023/2024 foi acessada. Nenhum score local garante 1,70 ou liderança.',
            'Nenhum upload foi realizado.', '',
            '[Protocolo](../../../experiments/ROUND10.md) · [Diagnóstico](diagnostic.json) · [Seleção](selection.json) · [Auditoria](audit.json)']
    if selection['selected'] is None:
        best=selection['ranking'][0]
        lines+=['','## Decisão desta execução','',
                f"Melhor candidata: {best['model']}, ganho relativo {100*best['relative_gain']:.3f}%; mínimo exigido: 0,300%.",
                'Não houve nova pontuação de 2021–2022, treino final, exportação S10 ou upload. S09 permanece a referência.',
                'Diagnóstico histórico: 63,1% do erro quadrático na faixa de 10°S a 15°N, incluindo oceano e terra.',
                'Esse diagnóstico não revela a distribuição dos erros ocultos do teste.']
    if (OUT/'confirmation.json').exists():
        c=r9.read(OUT/'confirmation.json')
        lines+=['','## Confirmação em período previamente utilizado','',
                f"2021–2022: {c['reference']['rmse']:.6f} para {c['result']['rmse']:.6f}. Aprovada: {c['passed']}."]
    (OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('audit','prepare','diagnose','evaluate','select','confirm','final','summarize'))
    globals()[parser.parse_args().stage]()
