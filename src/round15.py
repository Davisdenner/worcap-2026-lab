"""Joint forward-only convex recalibration of five existing S10 components."""
from __future__ import annotations

import argparse
import json
import importlib.metadata
import numpy as np
import xarray as xr
from scipy.optimize import minimize

from .competition import ROOT,RAW,CACHE,REPORT,save_json
from .round2 import target_origins
from .round4 import groups
from . import round9 as r9
from . import round10 as r10
from . import round11 as r11
from . import round12 as r12

ART=ROOT/'data/processed/round15'
OUT=REPORT/'round15'
PROTOCOL=ROOT/'experiments/ROUND15.md'
DEV=r11.DEV
HISTORY=r10.HISTORY
CONFIGS={f'joint{a:g}':a for a in (.1,.3,1.,3.)}
COMPONENTS=('s02','modes','local18','continental_pls16','tropical_extended')


def locked():
    ART.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
    value=dict(protocol_sha256=r9.digest(PROTOCOL),script_sha256=r9.digest(ROOT/'src/round15.py'),
               dependencies={p:r9.digest(ROOT/'src'/p) for p in
                  ('round9.py','round10.py','round11.py','round12.py','round2.py','round3.py','round4.py','competition.py','submission.py')},
               configurations=CONFIGS,official_only=True,reference='S10',components=COMPONENTS)
    value=json.loads(json.dumps(value)); path=OUT/'protocol.json'
    if path.exists() and r9.read(path)!=value: raise RuntimeError('Frozen code or protocol changed')
    if not path.exists(): save_json(path,value)
    return value


def prior_weights(cutoff):
    base,years=r9.forward_weights(cutoff)
    return np.column_stack([.5625*base,np.full(12,.1875),np.full(12,.25)]),years


def combine(pieces,weights):
    if pieces.shape!=(5,24,301,261) or weights.shape!=(12,5): raise ValueError('Wrong blend dimensions')
    if not np.isfinite(weights).all() or (weights<-1e-10).any() or not np.allclose(weights.sum(axis=1),1,atol=1e-9):
        raise ValueError('Weights must be convex')
    return np.sum(pieces*weights[groups()].transpose(3,0,1,2),axis=0)


def source_paths(cutoff):
    return [r9.ART/f'{cutoff}_{name}.npy' for name in ('s02','modes','local18','pls16')]+[
        r11.ART/f'{cutoff}_fine32.npy']


def components(cutoff):
    if cutoff not in HISTORY+(2023,): raise ValueError('Unknown cutoff')
    paths=source_paths(cutoff)
    first=[np.load(p) for p in paths[:4]]
    extended=r11.blend(r10.baseline(cutoff),np.load(paths[4]),1.)
    pieces=np.stack(first+[extended]).astype(float)
    if not np.isfinite(pieces).all() or (pieces<0).any(): raise ValueError('Invalid components')
    prior,years=prior_weights(cutoff)
    reference=r12.baseline(cutoff)
    error=float(np.max(abs(combine(pieces,prior)-reference)))
    if error>1e-10: raise ValueError(f'S10 reconstruction mismatch: {error}')
    report=dict(component_sources={p.relative_to(ROOT).as_posix():r9.digest(p) for p in paths},
                max_s10_reconstruction_error=error,prior=prior.tolist(),prior_calibration_blocks=years,
                training_targets_end=f'{cutoff-1}-12',official_only=True)
    path=ART/f'{cutoff}_components.json'
    if path.exists() and r9.read(path)!=report: raise ValueError('Components or prior changed')
    if not path.exists(): save_json(path,report)
    return pieces,reference,prior


def covariance(cutoff):
    if cutoff not in HISTORY: raise ValueError('No hidden targets allowed')
    path=ART/f'{cutoff}_covariance.npy'
    if path.exists():
        metadata=r9.read(path.with_suffix('.json'))
        if r9.digest(path)!=metadata['sha256']: raise ValueError('Covariance changed')
        return np.load(path)
    pieces,_,_=components(cutoff)
    truth=np.load(CACHE/'tp.npy',mmap_mode='r')[target_origins(cutoff)+1]
    errors=pieces-truth; mask=groups()
    c=np.stack([errors[:,mask==g]@errors[:,mask==g].T/(mask==g).sum() for g in range(12)])
    np.save(path,c)
    save_json(path.with_suffix('.json'),dict(block=cutoff,target_start=f'{cutoff}-01',target_end=f'{cutoff+1}-12',
              sha256=r9.digest(path),component_record_sha256=r9.digest(ART/f'{cutoff}_components.json'),
              uniform_grid_months=True,official_only=True))
    return c


def calibration_blocks(cutoff):
    years=r9.preceding(HISTORY,cutoff)
    if not years: raise ValueError('No earlier calibration blocks')
    return years


def solve_weights(cov,prior,penalty):
    cov=np.asarray(cov,dtype=float); prior=np.asarray(prior,dtype=float)
    if cov.shape!=(len(prior),len(prior)) or penalty<=0 or not np.isfinite(cov).all():
        raise ValueError('Invalid covariance or penalty')
    if (prior<0).any() or not np.isclose(prior.sum(),1): raise ValueError('Invalid prior')
    cov=(cov+cov.T)/2
    bounds=list(zip(np.maximum(prior-.1,0),np.minimum(prior+.1,1)))
    fit=minimize(lambda w: w@cov@w+penalty*np.sum((w-prior)**2),prior,
                 jac=lambda w: 2*cov@w+2*penalty*(w-prior),method='SLSQP',bounds=bounds,
                 constraints=[dict(type='eq',fun=lambda w:w.sum()-1,jac=lambda w:np.ones(len(w)))],
                 options=dict(ftol=1e-12,maxiter=1000))
    w=fit.x
    if not fit.success or not np.isfinite(w).all() or abs(w.sum()-1)>1e-9 or (w< -1e-10).any() or np.max(abs(w-prior))>.100000001:
        raise RuntimeError(f'Convex weight fit failed: {fit.message}')
    return w


def fitted_weights(cutoff,penalty):
    years=calibration_blocks(cutoff)
    c=np.mean([covariance(y) for y in years],axis=0)
    prior,prior_years=prior_weights(cutoff)
    weights=np.stack([solve_weights(c[g],prior[g],penalty) for g in range(12)])
    path=ART/f'{cutoff}_joint{penalty:g}_weights.json'
    result=dict(cutoff=cutoff,penalty=penalty,calibration_blocks=years,calibration_months=len(years)*24,
                last_calibration_target=f'{years[-1]+1}-12',prior_calibration_blocks=prior_years,
                prior=prior.tolist(),weights=weights.tolist(),max_weight_change=float(np.max(abs(weights-prior))),
                sum_to_one=True,nonnegative=True,official_only=True)
    if path.exists() and r9.read(path)!=result: raise ValueError('Frozen fitted weights changed')
    if not path.exists(): save_json(path,result)
    return weights


def prepare():
    locked(); r12.prepare()
    for cutoff in r10.SEEDS+DEV:
        components(cutoff)
        print('FIVE COMPONENTS VERIFIED',cutoff,flush=True)
    save_json(OUT/'audit.json',dict(passed=True,official_only=True,
              inherited_audit_sha256=r9.digest(r12.OUT/'audit.json'),
              s10_sha256=r9.digest(ROOT/'submissions/submission_10.csv'),
              development_components_reconstruct_s10=True,base_models_not_retrained=True))


def candidates(cutoff,names=None):
    locked()
    if not r9.read(OUT/'audit.json')['passed']: raise RuntimeError('Audit required')
    pieces,ref,prior=components(cutoff); result={}
    for name in (CONFIGS if names is None else names):
        weights=fitted_weights(cutoff,CONFIGS[name])
        pred=combine(pieces,weights)
        saved=np.asarray(r9.read(ART/f'{cutoff}_{name}_weights.json')['weights'])
        np.testing.assert_array_equal(pred,combine(pieces,saved))
        if not np.isfinite(pred).all() or (pred<0).any(): raise ValueError('Invalid prediction')
        path=ART/f'{cutoff}_{name}.npy'
        if path.exists(): np.testing.assert_array_equal(pred,np.load(path))
        else: np.save(path,pred)
        result[name]=pred
        print('JOINT WEIGHTS',cutoff,name,'past blocks',calibration_blocks(cutoff),flush=True)
    return result


def evaluate():
    locked(); tp=np.load(CACHE/'tp.npy',mmap_mode='r')
    for cutoff in DEV:
        path=OUT/f'{cutoff}.json'
        if path.exists(): continue
        predictions=candidates(cutoff); ref=r12.baseline(cutoff)
        truth=tp[target_origins(cutoff)+1]
        rows=[dict(model='s10',**r9.metrics(ref,truth,ref))]
        rows += [dict(model=name,**r9.metrics(pred,truth,ref)) for name,pred in predictions.items()]
        save_json(path,rows)
        print('RESULT',cutoff,[(r['model'],round(r['rmse'],6)) for r in rows],flush=True)


def rank(records):
    refs=np.array([records[y][0]['monthly_rmse'] for y in DEV])
    ref=float(np.sqrt(np.mean(refs**2))); second=float(np.sqrt(np.mean(refs[:,12:]**2)))
    refyears=np.sqrt(np.mean(refs.reshape(-1,12)**2,axis=1)); ranking=[]
    for name in CONFIGS:
        rows=[next(r for r in records[y] if r['model']==name) for y in DEV]
        months=np.array([r['monthly_rmse'] for r in rows]); years=np.sqrt(np.mean(months.reshape(-1,12)**2,axis=1))
        pooled=float(np.sqrt(np.mean(months**2))); s=float(np.sqrt(np.mean(months[:,12:]**2)))
        b=int(np.sum(np.mean(months**2,axis=1)<np.mean(refs**2,axis=1)))
        yy=int(np.sum(years<refyears)); mm=int(np.sum(months<refs)); worst=float(np.max(years/refyears-1))
        ranking.append(dict(model=name,rmse=pooled,relative_gain=1-pooled/ref,second_year_rmse=s,
                       blocks_improved=b,years_improved=yy,months_improved=mm,worst_annual_relative_change=worst,
                       passed=r9.passes_gate(pooled,ref,s,second,b,yy,mm,144,worst),
                       historical_correction_rms=float(np.sqrt(np.mean([r['correction_rms']**2 for r in rows])))))
    ranking.sort(key=lambda r:r['rmse']); eligible=[r for r in ranking if r['passed']]
    return dict(selected=eligible[0]['model'] if eligible else None,reference_rmse=ref,ranking=ranking,
                reused_periods=True,confirmation_previously_consumed=True)


def select():
    locked(); result=rank({y:r9.read(OUT/f'{y}.json') for y in DEV}); path=OUT/'selection.json'
    if path.exists() and r9.read(path)!=result: raise RuntimeError('Frozen selection changed')
    save_json(path,result); print(json.dumps(result,indent=2),flush=True)


def confirm():
    locked(); name=r9.read(OUT/'selection.json')['selected']
    if name is None: raise RuntimeError('No approved candidate')
    path=OUT/'confirmation.json'
    if path.exists(): return
    pred=candidates(2021,(name,))[name]; ref=r12.baseline(2021)
    truth=np.load(CACHE/'tp.npy',mmap_mode='r')[target_origins(2021)+1]
    before,after=r9.metrics(ref,truth,ref),r9.metrics(pred,truth,ref)
    passed=after['rmse']<=before['rmse']*.999 and all(after[k]<before[k] for k in ('year1_rmse','year2_rmse'))
    save_json(path,dict(candidate=name,reference=before,result=after,passed=passed,
              previously_consumed_period=True,no_post_confirmation_tuning=True))
    print('CONFIRMATION',before['rmse'],after['rmse'],passed,flush=True)


def final():
    locked(); selection=r9.read(OUT/'selection.json'); name=selection['selected']
    if name is None: raise RuntimeError('No approved candidate')
    confirmation=r9.read(OUT/'confirmation.json')
    if not confirmation['passed'] or confirmation['candidate']!=name: raise RuntimeError('Confirmation failed')
    destination=ROOT/'submissions/submission_11.csv'
    if destination.exists(): raise FileExistsError(destination)
    pred=candidates(2023,(name,))[name]; ref=r12.baseline(2023)
    historical=next(r['historical_correction_rms'] for r in selection['ranking'] if r['model']==name)
    rms=[float(np.sqrt(np.mean((pred[s]-ref[s])**2))) for s in (slice(0,12),slice(12,24))]
    passed=all(v<=2*historical for v in rms)
    save_json(OUT/'test_shift.json',dict(historical_rms=historical,public2023_rms=rms[0],private2024_rms=rms[1],passed=passed))
    if not passed: raise RuntimeError('Correction exceeds frozen bound')
    from .submission import export_csv
    with xr.open_dataset(RAW/'teste_features.nc') as grid:
        da=xr.DataArray(pred,dims=('time','lat','lon'),coords={d:grid[d] for d in ('time','lat','lon')},name='tp_mm_day')
        da.attrs.update(units='mm/day',model=name,official_only='true')
        da.to_netcdf(ART/'submission_11_predictions.nc')
        metadata=export_csv(da,grid,destination,RAW/'sample_submission.csv')
    metadata.update(experiment='round15',model=name,base_model='S10',official_data_only=True,external_sources=[],
                    csv_sha256=r9.digest(destination),public_score=None,uploaded=False,training_targets_end='2022-12',
                    protocol=locked(),audit_sha256=r9.digest(OUT/'audit.json'),selection=selection,confirmation=confirmation,
                    artifact_hashes={p.name:r9.digest(p) for p in ART.glob('2023_*')},
                    versions={p:importlib.metadata.version(p) for p in ('numpy','scipy','scikit-learn','xarray','pandas')})
    save_json(destination.with_suffix('.json'),metadata); print('EXPORTED',destination,flush=True)


def summarize():
    locked(); selection=r9.read(OUT/'selection.json')
    lines=['# Rodada 15 — recalibração conjunta dos componentes S10','',
           'Somente dados oficiais; RMSE em toda a grade de2009–2020, não score Kaggle.',
           f"Referência histórica S10: {selection['reference_rmse']:.6f}; público informado1,71895.",'',
           '| Candidata | RMSE | Ganho | Blocos | Anos | Meses | Aprovada |',
           '| --- | ---: | ---: | ---: | ---: | ---: | --- |']
    for r in selection['ranking']:
        lines.append(f"| {r['model']} | {r['rmse']:.6f} | {100*r['relative_gain']:.3f}% | {r['blocks_improved']}/6 | "
                     f"{r['years_improved']}/12 | {r['months_improved']}/144 | {r['passed']} |")
    lines+=['',f"Selecionada: {selection['selected'] or 'nenhuma'}.",
            'Cinco componentes existentes, 12 grupos fixos, pesos não negativos, soma1, variação máxima0,10 do prior.',
            'Prior reproduz S10. Pesos ajustados somente com blocos encerrados antes de cada corte.',
            'Arquitetura e períodos reutilizados; 2021–2022 não é holdout inédito.',
            'Nenhuma chuva oculta2023/24, fonte externa, upload ou garantia de1,70.',
            '', '[Protocolo](../../../experiments/ROUND15.md) · [Seleção](selection.json) · [Auditoria](audit.json)',
            '[Referência S10 consolidada](../../../docs/S10_BASELINE.md)']
    if (OUT/'confirmation.json').exists():
        c=r9.read(OUT/'confirmation.json')
        lines+=['',f"Confirmação reutilizada: {c['reference']['rmse']:.6f} → {c['result']['rmse']:.6f}; aprovada: {c['passed']}."]
    elif not selection['selected']:
        lines+=['','Sem nova confirmação, calibração final ou CSV. S10 preservada e nenhum envio consumido.']
    (OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8'); print('\n'.join(lines),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('prepare','evaluate','select','confirm','final','summarize'))
    globals()[parser.parse_args().stage]()
