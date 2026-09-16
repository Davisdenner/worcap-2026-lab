"""Fixed official-only tropical multiscale experiment, relative to immutable S09."""
from __future__ import annotations

import argparse
import warnings
import importlib.metadata
import joblib
import numpy as np
import xarray as xr
from scipy.ndimage import uniform_filter
from sklearn.decomposition import PCA
from sklearn.cross_decomposition import PLSRegression
from sklearn.exceptions import ConvergenceWarning

from .competition import ROOT, RAW, CACHE, REPORT, VARIABLES, dates, training_pairs, fit_climatology, save_json
from .round2 import target_origins
from .round3 import seasonal_design
from .round4 import memory
from . import round9 as r9
from . import round10 as r10

ART=ROOT/'data/processed/round11'
OUT=REPORT/'round11'
PROTOCOL=ROOT/'experiments/ROUND11.md'
DEV=r10.DEV
SEED=20260917
CONFIGS={f'fine{n}_{a:g}':('fine',n,a) for n in (16,32) for a in (.25,.5)}
CONTROL='coarse16_0.25'
ALL_CONFIGS={**CONFIGS,CONTROL:('coarse',16,.25)}


def locked():
    ART.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
    value=dict(protocol_sha256=r9.digest(PROTOCOL),script_sha256=r9.digest(ROOT/'src/round11.py'),
               dependency_hashes={p:r9.digest(ROOT/'src'/p) for p in
                                  ('round9.py','round10.py','round2.py','round3.py','round4.py','competition.py','submission.py')},
               configs=ALL_CONFIGS,seed=SEED,official_only=True)
    # JSON roundtrip normalizes tuples to lists.
    import json
    value=json.loads(json.dumps(value))
    path=OUT/'protocol.json'
    if path.exists() and r9.read(path)!=value:
        raise RuntimeError('Frozen implementation or protocol changed')
    if not path.exists(): save_json(path,value)
    return value


def fine_fields(values):
    """Spatial filtering only; crop after filtering so crop edges are not padded."""
    return uniform_filter(values,size=(1,5,5),mode='nearest')[:,160::4,::4].reshape(len(values),-1)


def prepare():
    locked()
    # Recheck official sources, cache equality and immutable S09 artifacts.
    r10.audit()
    path=ART/'fine_weather.npy'
    if not path.exists():
        width=36*66
        result=np.empty((1019,9*width),np.float32)
        with xr.open_dataset(RAW/'teste_features.nc') as test:
            expected=np.arange('2022-12','2024-12',dtype='datetime64[M]')
            np.testing.assert_array_equal(test.time_origem.values.astype('datetime64[M]'),expected)
            for j,name in enumerate(VARIABLES):
                train=np.load(CACHE/f'{name}.npy',mmap_mode='r')
                np.testing.assert_array_equal(test[name].values[0],train[-1])
                for start in range(0,len(train),48):
                    block=fine_fields(train[start:start+48])
                    result[start:start+len(block),j*width:(j+1)*width]=block
                result[996:,j*width:(j+1)*width]=fine_fields(test[name].values[1:])
                print('FINE CACHE',name,flush=True)
        if not np.isfinite(result).all(): raise ValueError('Invalid fine cache')
        np.save(path,result)
    # Independently compare every feature to its official field, in temporal chunks.
    cache=np.load(path,mmap_mode='r')
    with xr.open_dataset(RAW/'teste_features.nc') as test:
        for j,name in enumerate(VARIABLES):
            train=np.load(CACHE/f'{name}.npy',mmap_mode='r'); sl=slice(j*2376,(j+1)*2376)
            for start in range(0,996,48):
                expected=fine_fields(train[start:start+48])
                np.testing.assert_array_equal(cache[start:start+len(expected),sl],expected)
            np.testing.assert_array_equal(cache[996:,sl],fine_fields(test[name].values[1:]))
    save_json(OUT/'audit.json',dict(passed=True,official_only=True,fine_sha256=r9.digest(path),
              previous_audit_sha256=r9.digest(r10.OUT/'audit.json'),full_feature_comparison=True))


def regional_raw(kind):
    if kind=='fine': return np.load(ART/'fine_weather.npy',mmap_mode='r')
    if kind!='coarse': raise ValueError(kind)
    raw=np.load(ROOT/'data/processed/round3/coarse_weather.npy',mmap_mode='r')
    return raw.reshape(len(raw),9,38,33)[:,:,20:,:].reshape(len(raw),-1)


def fit_weather(raw,idx):
    means=np.stack([raw[idx[idx%12==m]].mean(axis=0) for m in range(12)])
    train=raw[idx]-means[idx%12]
    scale=np.maximum(train.std(axis=0),1e-8)
    pca=PCA(n_components=64,svd_solver='randomized',random_state=SEED)
    z=pca.fit_transform(train/scale)
    return dict(means=means,scale=scale,pca=pca,pc_scale=np.maximum(z.std(axis=0),1e-8))


def weather_design(raw,regional,continental,origins):
    # Shared causal transform truncates data at the largest requested origin.
    coarse=np.load(ROOT/'data/processed/round3/coarse_weather.npy',mmap_mode='r')
    return np.column_stack([r10.weather_design(coarse,continental,origins),
                            r10.weather_design(raw,regional,origins)])


def fit_pls(x,y,n):
    scale=np.maximum(x.std(axis=0),1e-8); x=x/scale
    eof=PCA(n_components=32,svd_solver='randomized',random_state=SEED)
    targets=eof.fit_transform(y)
    pls=PLSRegression(n_components=n,scale=False,max_iter=1000,tol=1e-7)
    with warnings.catch_warnings():
        warnings.simplefilter('error',ConvergenceWarning)
        pls.fit(x,targets)
    z=pls.transform(x); zscale=np.maximum(z.std(axis=0),1e-8)
    design=np.column_stack([np.ones(len(x)),z/zscale])
    penalty=.3*np.eye(n+1); penalty[0,0]=0
    coefficients=np.linalg.solve(design.T@design/len(x)+penalty,design.T@y/len(x))
    return dict(x_scale=scale,pls=pls,score_scale=zscale,coefficients=coefficients,
                target_eof_variance=float(eof.explained_variance_ratio_.sum()))


def anomaly_prediction(model,x):
    z=model['pls'].transform(x/model['x_scale'])/model['score_scale']
    return np.column_stack([np.ones(len(x)),z])@model['coefficients']


def tropical(cutoff,kind,counts):
    locked()
    idx=training_pairs(dates(),f'{cutoff}-01-01'); origins=target_origins(cutoff)
    if idx.max()+1>=(cutoff-1940)*12: raise ValueError('Target leakage')
    raw=regional_raw(kind)
    continental=joblib.load(r9.ART/f'{cutoff}_pls16.joblib')
    if continental['training_cutoff']!=f'{cutoff}-01' or not continental['official_only']:
        raise ValueError('Wrong continental transform')
    prep=ART/f'{cutoff}_{kind}_weather.joblib'
    if not prep.exists(): joblib.dump(fit_weather(raw,idx),prep)
    regional=joblib.load(prep)
    x=weather_design(raw,regional,continental,idx)
    xv=weather_design(raw,regional,continental,origins)
    tp=np.load(CACHE/'tp.npy',mmap_mode='r')[:,180:].reshape(996,-1)
    climo=fit_climatology(tp,dates(),f'{cutoff}-01-01',60)
    y=tp[idx+1]-climo[(idx+1)%12]
    result={}
    for n in counts:
        path=ART/f'{cutoff}_{kind}{n}.joblib'
        if not path.exists():
            model=fit_pls(x,y,n)
            model.update(climatology=climo,training_target_end=f'{cutoff-1}-12',official_only=True)
            joblib.dump(model,path)
        model=joblib.load(path)
        pred=np.maximum(model['climatology'][(origins+1)%12]+anomaly_prediction(model,xv),0).reshape(24,121,261)
        np.testing.assert_array_equal(pred,np.maximum(model['climatology'][(origins+1)%12]+
                                      anomaly_prediction(joblib.load(path),xv),0).reshape(pred.shape))
        if not np.isfinite(pred).all(): raise ValueError('Invalid tropical prediction')
        np.save(ART/f'{cutoff}_{kind}{n}.npy',pred)
        result[n]=pred
        print('TROPICAL',cutoff,kind,n,'training pairs',len(idx),flush=True)
    return result


def blend(reference,new,weight):
    if reference.shape!=(24,301,261) or new.shape!=(24,121,261) or not 0<=weight<=1:
        raise ValueError('Invalid blend')
    taper=np.clip((np.arange(-15,15.01,.25)+15)/5,0,1)[None,:,None]*weight
    pred=reference.copy()
    pred[:,180:]=reference[:,180:]*(1-taper)+new*taper
    return pred


def evaluate():
    locked()
    audit=r9.read(OUT/'audit.json')
    if not audit['passed'] or r9.digest(ART/'fine_weather.npy')!=audit['fine_sha256']:
        raise RuntimeError('Audited cache required')
    tp=np.load(CACHE/'tp.npy',mmap_mode='r')
    for cutoff in DEV:
        path=OUT/f'{cutoff}.json'
        if path.exists(): continue
        ref=r10.baseline(cutoff)
        predictions={kind:tropical(cutoff,kind,ns) for kind,ns in [('fine',(16,32)),('coarse',(16,))]}
        truth=tp[target_origins(cutoff)+1]
        rows=[dict(model='s09',**r9.metrics(ref,truth,ref))]
        for name,(kind,n,a) in ALL_CONFIGS.items():
            pred=blend(ref,predictions[kind][n],a)
            rows.append(dict(model=name,**r9.metrics(pred,truth,ref)))
            np.save(ART/f'{cutoff}_{name}.npy',pred)
        save_json(path,rows)
        print('RESULT',cutoff,[(r['model'],round(r['rmse'],6)) for r in rows],flush=True)


def select():
    locked()
    records={y:r9.read(OUT/f'{y}.json') for y in DEV}
    refs=np.array([records[y][0]['monthly_rmse'] for y in DEV])
    ref=float(np.sqrt(np.mean(refs**2))); second=float(np.sqrt(np.mean(refs[:,12:]**2)))
    refyears=np.sqrt(np.mean(refs.reshape(-1,12)**2,axis=1)); ranking=[]
    for name in ALL_CONFIGS:
        rows=[next(r for r in records[y] if r['model']==name) for y in DEV]
        months=np.array([r['monthly_rmse'] for r in rows]); years=np.sqrt(np.mean(months.reshape(-1,12)**2,axis=1))
        pooled=float(np.sqrt(np.mean(months**2))); s=float(np.sqrt(np.mean(months[:,12:]**2)))
        b=int(np.sum(np.mean(months**2,axis=1)<np.mean(refs**2,axis=1)))
        yy=int(np.sum(years<refyears)); mm=int(np.sum(months<refs)); worst=float(np.max(years/refyears-1))
        eligible=name in CONFIGS
        ranking.append(dict(model=name,rmse=pooled,relative_gain=1-pooled/ref,second_year_rmse=s,
                            blocks_improved=b,years_improved=yy,months_improved=mm,worst_annual_relative_change=worst,
                            eligible=eligible,passed=eligible and r9.passes_gate(pooled,ref,s,second,b,yy,mm,144,worst),
                            historical_correction_rms=float(np.sqrt(np.mean([r['correction_rms']**2 for r in rows])))))
    ranking.sort(key=lambda r:r['rmse']); eligible=[r for r in ranking if r['passed']]
    result=dict(selected=eligible[0]['model'] if eligible else None,reference_rmse=ref,ranking=ranking,
                reused_periods=True,confirmation_previously_consumed=True)
    path=OUT/'selection.json'
    if path.exists() and r9.read(path)!=result: raise RuntimeError('Frozen selection changed')
    save_json(path,result); print(result,flush=True)


def chosen(cutoff,name):
    kind,n,a=CONFIGS[name]
    return blend(r10.baseline(cutoff),tropical(cutoff,kind,(n,))[n],a)


def confirm():
    locked(); name=r9.read(OUT/'selection.json')['selected']
    if name is None: raise RuntimeError('No candidate approved; no confirmation')
    if (OUT/'confirmation.json').exists(): return
    pred=chosen(2021,name); ref=r10.baseline(2021)
    truth=np.load(CACHE/'tp.npy',mmap_mode='r')[target_origins(2021)+1]
    before,after=r9.metrics(ref,truth,ref),r9.metrics(pred,truth,ref)
    passed=after['rmse']<=before['rmse']*.999 and all(after[k]<before[k] for k in ('year1_rmse','year2_rmse'))
    save_json(OUT/'confirmation.json',dict(candidate=name,reference=before,result=after,passed=passed,
              previously_consumed_period=True,no_post_confirmation_tuning=True))
    print('CONFIRMATION',before['rmse'],after['rmse'],passed,flush=True)


def final():
    locked(); selection=r9.read(OUT/'selection.json'); name=selection['selected']
    if not name: raise RuntimeError('No approved candidate')
    confirmation=r9.read(OUT/'confirmation.json')
    if not confirmation['passed'] or confirmation['candidate']!=name: raise RuntimeError('Confirmation failed')
    destination=ROOT/'submissions/submission_10.csv'
    if destination.exists(): raise FileExistsError(destination)
    ref=r10.baseline(2023); pred=chosen(2023,name)
    historical=next(r['historical_correction_rms'] for r in selection['ranking'] if r['model']==name)
    rms=[float(np.sqrt(np.mean((pred[s]-ref[s])**2))) for s in (slice(0,12),slice(12,24))]
    passed=all(v<=2*historical for v in rms)
    save_json(OUT/'test_shift.json',dict(historical_rms=historical,public2023_rms=rms[0],private2024_rms=rms[1],passed=passed))
    if not passed: raise RuntimeError('Correction exceeds frozen bound; no export')
    from .submission import export_csv
    with xr.open_dataset(RAW/'teste_features.nc') as grid:
        da=xr.DataArray(pred,dims=('time','lat','lon'),coords={d:grid[d] for d in ('time','lat','lon')},name='tp_mm_day')
        da.attrs.update(units='mm/day',model=name,official_only='true')
        da.to_netcdf(ART/'submission_10_predictions.nc')
        metadata=export_csv(da,grid,destination,RAW/'sample_submission.csv')
    metadata.update(experiment='round11',model=name,base_model='S09',official_data_only=True,external_sources=[],
                    csv_sha256=r9.digest(destination),public_score=None,uploaded=False,training_targets_end='2022-12',
                    protocol=locked(),audit_sha256=r9.digest(OUT/'audit.json'),selection=selection,confirmation=confirmation,
                    artifact_hashes={p.name:r9.digest(p) for p in ART.glob('2023_*')},
                    versions={p:importlib.metadata.version(p) for p in ('numpy','scipy','scikit-learn','xarray','pandas')})
    save_json(destination.with_suffix('.json'),metadata)
    print('EXPORTED',destination,flush=True)


def summarize():
    locked(); selection=r9.read(OUT/'selection.json')
    lines=['# Rodada 11 — resolução atmosférica tropical','',
           'Somente dados oficiais; RMSE da grade completa em 2009–2020, não score Kaggle.',
           f"Referência S09: {selection['reference_rmse']:.6f}.",'',
           '| Candidata | RMSE | Ganho | Blocos | Anos | Meses | Aprovada |',
           '| --- | ---: | ---: | ---: | ---: | ---: | --- |']
    for r in selection['ranking']:
        lines.append(f"| {r['model']} | {r['rmse']:.6f} | {100*r['relative_gain']:.3f}% | {r['blocks_improved']}/6 | "
                     f"{r['years_improved']}/12 | {r['months_improved']}/144 | {r['passed']} |")
    lines+=['',f"Selecionada: {selection['selected'] or 'nenhuma'}.",
            'coarse16_0.25 é controle diagnóstico, não elegível para exportação.',
            'Critérios definidos antes dos resultados; mínimo de ganho agregado de 0,3%.',
            'Períodos e arquitetura S09 reutilizados; 2021–2022 não é holdout novo.',
            'Nenhuma chuva oculta de 2023/2024 foi acessada. Nenhum upload ou garantia de 1,70.',
            '', '[Protocolo](../../../experiments/ROUND11.md) · [Seleção](selection.json) · [Auditoria](audit.json)']
    if (OUT/'confirmation.json').exists():
        c=r9.read(OUT/'confirmation.json')
        lines+=['',f"Confirmação reutilizada 2021–2022: {c['reference']['rmse']:.6f} → {c['result']['rmse']:.6f}; aprovada: {c['passed']}."]
    elif not selection['selected']:
        lines+=['','Sem nova confirmação, treino final ou CSV. S09 permanece a referência pública (1,72957).']
    (OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('prepare','evaluate','select','confirm','final','summarize'))
    globals()[parser.parse_args().stage]()
