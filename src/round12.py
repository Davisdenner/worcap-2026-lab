"""Forward residual correction of immutable S10, official-only and gated."""
from __future__ import annotations

import argparse
import json
import importlib.metadata
import joblib
import numpy as np
import xarray as xr

from .competition import ROOT, CACHE, RAW, REPORT, save_json
from .round2 import target_origins
from . import round9 as r9
from . import round10 as r10
from . import round11 as r11

ART=ROOT/'data/processed/round12'
OUT=REPORT/'round12'
PROTOCOL=ROOT/'experiments/ROUND12.md'
DEV=r10.DEV
CONFIGS={f'residual{n}_{a:g}':(n,a) for n in (2,4,8) for a in (.25,.5)}


def locked():
    ART.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
    value=dict(protocol_sha256=r9.digest(PROTOCOL),script_sha256=r9.digest(ROOT/'src/round12.py'),
               dependencies={p:r9.digest(ROOT/'src'/p) for p in
               ('round9.py','round10.py','round11.py','round2.py','round3.py','round4.py','competition.py','submission.py')},
               configs=CONFIGS,official_only=True,reference='submission_10.csv')
    value=json.loads(json.dumps(value)); path=OUT/'protocol.json'
    if path.exists() and r9.read(path)!=value: raise RuntimeError('Frozen protocol or code changed')
    if not path.exists(): save_json(path,value)
    return value


def baseline(cutoff):
    path=ART/f'{cutoff}_s10.npy'
    if path.exists():
        provenance=r9.read(path.with_suffix('.json'))
        if r9.digest(path)!=provenance['sha256']: raise ValueError('Baseline changed')
        return np.load(path)
    if cutoff not in r10.HISTORY+(2023,): raise ValueError('Unregistered cutoff')
    if cutoff in r10.SEEDS:
        # Only these missing seed models are added to the old cache.
        new=r11.tropical(cutoff,'fine',(32,))[32]
    else:
        new=np.load(r11.ART/f'{cutoff}_fine32.npy')
    pred=r11.blend(r10.baseline(cutoff),new,.25)
    if cutoff in DEV:
        np.testing.assert_array_equal(pred,np.load(r11.ART/f'{cutoff}_fine32_0.25.npy'))
    elif cutoff==2023:
        with xr.open_dataset(r11.ART/'submission_10_predictions.nc') as ds:
            np.testing.assert_array_equal(pred,ds.tp_mm_day.values)
    if not np.isfinite(pred).all() or (pred<0).any(): raise ValueError('Invalid baseline')
    np.save(path,pred)
    save_json(path.with_suffix('.json'),dict(model='S10',cutoff=cutoff,sha256=r9.digest(path),
              training_target_end=f'{cutoff-1}-12',official_only=True,formula_reconstructed=True))
    return pred


def prepare():
    locked(); r11.locked(); r10.audit()
    metadata=r9.read(ROOT/'submissions/submission_10.json')
    if r9.digest(ROOT/'submissions/submission_10.csv')!=metadata['csv_sha256']:
        raise ValueError('S10 CSV changed')
    for filename,expected in metadata['artifact_hashes'].items():
        if r9.digest(r11.ART/filename)!=expected: raise ValueError(f'S10 artifact changed: {filename}')
    audit=r9.read(r11.OUT/'audit.json')
    if r9.digest(r11.ART/'fine_weather.npy')!=audit['fine_sha256']:
        raise ValueError('Fine atmospheric cache changed')
    for cutoff in r10.SEEDS+DEV:
        baseline(cutoff)
        print('S10 BASELINE',cutoff,flush=True)
    save_json(OUT/'audit.json',dict(passed=True,official_only=True,s10_sha256=metadata['csv_sha256'],
              inherited_audit_sha256=r9.digest(r10.OUT/'audit.json'),fine_sha256=audit['fine_sha256'],
              development_baseline_hashes={str(y):r9.digest(ART/f'{y}_s10.npy') for y in r10.SEEDS+DEV},
              immutable_s10_artifacts_verified=True))


def features(cutoff,origins):
    regional=joblib.load(r11.ART/f'{cutoff}_fine_weather.joblib')
    continental=joblib.load(r9.ART/f'{cutoff}_pls16.joblib')
    if continental['training_cutoff']!=f'{cutoff}-01' or not continental['official_only']:
        raise ValueError('Wrong atmospheric cutoff')
    return r11.weather_design(r11.regional_raw('fine'),regional,continental,origins)


def correction(cutoff,counts=(2,4,8)):
    locked(); years,idx=r10.training_origins(cutoff)
    x=features(cutoff,idx); xv=features(cutoff,target_origins(cutoff))
    tp=np.load(CACHE/'tp.npy',mmap_mode='r')
    y=np.concatenate([(tp[target_origins(year)+1]-baseline(year)).reshape(24,-1) for year in years])
    results={}
    for n in counts:
        path=ART/f'{cutoff}_residual{n}.joblib'
        if not path.exists():
            model=r10.fit_residual(x,y,n)
            model.update(training_blocks=years,training_target_last=f'{max(years)+1}-12',cutoff=cutoff,
                         official_only=True,base='S10',
                         regional_transform_sha256=r9.digest(r11.ART/f'{cutoff}_fine_weather.joblib'),
                         continental_transform_sha256=r9.digest(r9.ART/f'{cutoff}_pls16.joblib'))
            joblib.dump(model,path)
        model=joblib.load(path)
        if model['training_blocks']!=years or model['base']!='S10': raise ValueError('Stale model')
        pred=r10.predict_residual(model,xv).reshape(24,301,261)
        np.testing.assert_array_equal(pred,r10.predict_residual(joblib.load(path),xv).reshape(pred.shape))
        output=ART/f'{cutoff}_residual{n}.npy'
        if output.exists(): np.testing.assert_array_equal(pred,np.load(output))
        else: np.save(output,pred)
        results[n]=pred
        print('S10 RESIDUAL',cutoff,n,'training months',len(idx),flush=True)
    save_json(ART/f'{cutoff}_training.json',dict(training_blocks=years,training_months=len(idx),
              target_last=f'{max(years)+1}-12',forecast_start=f'{cutoff}-01',official_only=True,
              caveat='S10 architecture and development periods selected retrospectively; not independent test'))
    return results


def apply_correction(ref,delta,weight):
    if ref.shape!=delta.shape or not 0<=weight<=1: raise ValueError('Invalid correction')
    pred=np.maximum(ref+weight*delta,0)
    if not np.isfinite(pred).all(): raise ValueError('Nonfinite correction')
    return pred


def evaluate():
    locked()
    if not r9.read(OUT/'audit.json')['passed']: raise RuntimeError('Audit required')
    tp=np.load(CACHE/'tp.npy',mmap_mode='r')
    for cutoff in DEV:
        path=OUT/f'{cutoff}.json'
        if path.exists(): continue
        ref=baseline(cutoff); deltas=correction(cutoff)
        truth=tp[target_origins(cutoff)+1]
        rows=[dict(model='s10',**r9.metrics(ref,truth,ref))]
        for name,(n,a) in CONFIGS.items():
            pred=apply_correction(ref,deltas[n],a)
            rows.append(dict(model=name,**r9.metrics(pred,truth,ref)))
            np.save(ART/f'{cutoff}_{name}.npy',pred)
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


def chosen(cutoff,name):
    n,a=CONFIGS[name]
    return apply_correction(baseline(cutoff),correction(cutoff,(n,))[n],a)


def confirm():
    locked(); name=r9.read(OUT/'selection.json')['selected']
    if name is None: raise RuntimeError('No approved candidate; no confirmation')
    path=OUT/'confirmation.json'
    if path.exists(): return
    pred=chosen(2021,name); ref=baseline(2021)
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
    ref=baseline(2023); pred=chosen(2023,name)
    historical=next(r['historical_correction_rms'] for r in selection['ranking'] if r['model']==name)
    rms=[float(np.sqrt(np.mean((pred[s]-ref[s])**2))) for s in (slice(0,12),slice(12,24))]
    passed=all(v<=2*historical for v in rms)
    save_json(OUT/'test_shift.json',dict(historical_rms=historical,public2023_rms=rms[0],private2024_rms=rms[1],passed=passed))
    if not passed: raise RuntimeError('Correction exceeds frozen bound; no export')
    from .submission import export_csv
    with xr.open_dataset(RAW/'teste_features.nc') as grid:
        da=xr.DataArray(pred,dims=('time','lat','lon'),coords={d:grid[d] for d in ('time','lat','lon')},name='tp_mm_day')
        da.attrs.update(units='mm/day',model=name,official_only='true')
        da.to_netcdf(ART/'submission_11_predictions.nc')
        metadata=export_csv(da,grid,destination,RAW/'sample_submission.csv')
    metadata.update(experiment='round12',model=name,base_model='S10',official_data_only=True,external_sources=[],
                    csv_sha256=r9.digest(destination),public_score=None,uploaded=False,training_targets_end='2022-12',
                    protocol=locked(),audit_sha256=r9.digest(OUT/'audit.json'),selection=selection,confirmation=confirmation,
                    artifact_hashes={p.name:r9.digest(p) for p in ART.glob('2023_*')},
                    versions={p:importlib.metadata.version(p) for p in ('numpy','scipy','scikit-learn','xarray','pandas')})
    save_json(destination.with_suffix('.json'),metadata); print('EXPORTED',destination,flush=True)


def summarize():
    locked(); selection=r9.read(OUT/'selection.json')
    lines=['# Rodada 12 — correção residual da S10','',
           'Somente dados oficiais; RMSE da grade completa em 2009–2020, não score Kaggle.',
           f"Referência histórica S10: {selection['reference_rmse']:.6f}. Público S10 informado: 1,71895.",'',
           '| Candidata | RMSE | Ganho | Blocos | Anos | Meses | Aprovada |',
           '| --- | ---: | ---: | ---: | ---: | ---: | --- |']
    for r in selection['ranking']:
        lines.append(f"| {r['model']} | {r['rmse']:.6f} | {100*r['relative_gain']:.3f}% | {r['blocks_improved']}/6 | "
                     f"{r['years_improved']}/12 | {r['months_improved']}/144 | {r['passed']} |")
    lines+=['',f"Selecionada: {selection['selected'] or 'nenhuma'}.",
            'Critérios definidos antes dos resultados; mínimo de ganho agregado de 0,3%.',
            'Treino dos resíduos usa somente blocos encerrados. Arquitetura S10 e períodos reutilizados.',
            '2021–2022 não é holdout inédito. Nenhuma chuva oculta 2023/2024 foi acessada.',
            'Nenhum upload ou garantia de 1,70. Usuário informou um envio restante hoje.',
            '', '[Protocolo](../../../experiments/ROUND12.md) · [Seleção](selection.json) · [Auditoria](audit.json)']
    if (OUT/'confirmation.json').exists():
        c=r9.read(OUT/'confirmation.json')
        lines+=['',f"Confirmação reutilizada: {c['reference']['rmse']:.6f} → {c['result']['rmse']:.6f}; aprovada: {c['passed']}."]
    elif not selection['selected']:
        lines+=['','Sem nova confirmação, treino final ou CSV. S10 permanece a referência; preservar o envio restante.']
    (OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8'); print('\n'.join(lines),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('prepare','evaluate','select','confirm','final','summarize'))
    globals()[parser.parse_args().stage]()
