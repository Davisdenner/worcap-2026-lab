"""Official monthly moisture-transport proxies added to the S10 tropical model."""
from __future__ import annotations

import argparse
import json
import importlib.metadata
import joblib
import numpy as np
import xarray as xr
from scipy.ndimage import uniform_filter,minimum_filter
from sklearn.decomposition import PCA

from .competition import ROOT,RAW,CACHE,REPORT,dates,training_pairs,save_json
from .round2 import target_origins
from . import round9 as r9
from . import round10 as r10
from . import round11 as r11
from . import round12 as r12

ART=ROOT/'data/processed/round14'
OUT=REPORT/'round14'
PROTOCOL=ROOT/'experiments/ROUND14.md'
DEV=r11.DEV
CONFIGS={f'{family}{n}':(family,n) for family in ('flux','fluxconv') for n in (16,32)}
SEED=20260918
RADIUS=6371000.


def locked():
    ART.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
    value=dict(protocol_sha256=r9.digest(PROTOCOL),script_sha256=r9.digest(ROOT/'src/round14.py'),
               dependencies={p:r9.digest(ROOT/'src'/p) for p in
                  ('round9.py','round10.py','round11.py','round12.py','round2.py','round3.py','round4.py','competition.py','submission.py')},
               configurations=CONFIGS,official_only=True,reference='S10',seed=SEED)
    value=json.loads(json.dumps(value)); path=OUT/'protocol.json'
    if path.exists() and r9.read(path)!=value: raise RuntimeError('Frozen code or protocol changed')
    if not path.exists(): save_json(path,value)
    return value


def spherical_convergence(east,north,lat,lon):
    phi=np.deg2rad(np.asarray(lat)); lam=np.deg2rad(np.asarray(lon))
    if not np.all(np.diff(phi)>0) or not np.all(np.diff(lam)>0): raise ValueError('Coordinates must ascend')
    cos=np.cos(phi)[None,:,None]
    return -(np.gradient(east,lam,axis=2,edge_order=1)+
             np.gradient(north*cos,phi,axis=1,edge_order=1))/(RADIUS*cos)


def moisture_fields(q,u,v,ps,lat,lon):
    q,u,v,ps=[np.asarray(a,dtype=float) for a in (q,u,v,ps)]
    if q.ndim!=3 or any(a.shape!=q.shape for a in (u,v,ps)) or q.shape[1:]!=(len(lat),len(lon)):
        raise ValueError('Mismatched physical fields')
    valid=np.isfinite(q)&np.isfinite(u)&np.isfinite(v)&np.isfinite(ps)&(ps>=85000)
    east=uniform_filter(np.where(valid,q*u,0),size=(1,5,5),mode='nearest')
    north=uniform_filter(np.where(valid,q*v,0),size=(1,5,5),mode='nearest')
    convergence=spherical_convergence(east,north,lat,lon)*1e6
    usable=minimum_filter(valid.astype(np.uint8),size=(1,7,7),mode='nearest').astype(bool)
    fields=np.stack([np.where(usable,a,0) for a in (east,north,convergence)],axis=1)
    if not np.isfinite(fields).all(): raise ValueError('Nonfinite physical attributes')
    return fields,usable


def prepare():
    locked(); r12.prepare()
    path=ART/'moisture.npy'; sources=('shum_850','u_850','v_850','surface_pressure')
    arrays=[np.load(CACHE/f'{name}.npy',mmap_mode='r') for name in sources]
    result=np.empty((1019,3,36,66),np.float32); valid_count=0; total_count=0
    with xr.open_dataset(RAW/'teste_features.nc') as ds:
        lat,lon=ds.lat.values,ds.lon.values
        np.testing.assert_array_equal(lat,np.arange(-60,15.01,.25))
        np.testing.assert_array_equal(lon,np.arange(-90,-24.99,.25))
        np.testing.assert_array_equal(ds.time_origem.values.astype('datetime64[M]'),np.arange('2022-12','2024-12',dtype='datetime64[M]'))
        for j,name in enumerate(sources): np.testing.assert_array_equal(ds[name].values[0],arrays[j][-1])
        for start in range(0,996,24):
            fields,mask=moisture_fields(*[a[start:start+24] for a in arrays],lat,lon)
            result[start:start+len(fields)]=fields[:,:,160::4,::4]
            valid_count+=int(mask.sum()); total_count+=mask.size
            if start%240==0: print('PHYSICS CACHE',start,'/996',flush=True)
        fields,mask=moisture_fields(*[ds[name].values[1:] for name in sources],lat,lon)
        result[996:]=fields[:,:,160::4,::4]
        valid_count+=int(mask.sum()); total_count+=mask.size
        # Independently re-read official NetCDF chunks (not cache arrays) at fixed dates.
        for start in (0,480,840,972):
            data=[]
            for name in sources:
                with xr.open_dataset(RAW/f'treino_{name}.nc') as original:
                    data.append(original[name].isel(time=slice(start,start+2)).values)
            expected,_=moisture_fields(*data,lat,lon)
            np.testing.assert_array_equal(result[start:start+2],expected[:,:,160::4,::4].astype(np.float32))
    if path.exists(): np.testing.assert_array_equal(result,np.load(path))
    else: np.save(path,result)
    save_json(OUT/'audit.json',dict(passed=True,official_only=True,
              inherited_audit_sha256=r9.digest(r12.OUT/'audit.json'),moisture_sha256=r9.digest(path),
              field_order=['monthly_q_times_u','monthly_q_times_v','convergence_times_1e6'],
              shape=list(result.shape),usable_full_grid_fraction=valid_count/total_count,
              original_nc_spot_checks=8,all_source_cache_values_previously_rechecked=True,
              units_assumed_era5_standard=True,monthly_single_level_proxy_not_column_flux=True))


def fit_physics(raw,idx,n):
    means=np.stack([raw[idx[idx%12==m]].mean(axis=0) for m in range(12)])
    centered=raw[idx]-means[idx%12]; scale=np.maximum(centered.std(axis=0),1e-8)
    pca=PCA(n_components=n,svd_solver='randomized',random_state=SEED)
    pca.fit(centered/scale)
    pc_scale=np.maximum(pca.transform(centered/scale).std(axis=0),1e-8)
    return dict(means=means,scale=scale,pca=pca,pc_scale=pc_scale)


def candidates(cutoff,names=None):
    locked()
    audit=r9.read(OUT/'audit.json')
    if not audit['passed'] or r9.digest(ART/'moisture.npy')!=audit['moisture_sha256']:
        raise RuntimeError('Audited physics cache required')
    idx=training_pairs(dates(),f'{cutoff}-01-01'); origins=target_origins(cutoff)
    if np.any(idx+1>=(cutoff-1940)*12): raise ValueError('Target leakage')
    old=joblib.load(r11.ART/f'{cutoff}_fine32.joblib')
    if old['training_target_end']!=f'{cutoff-1}-12' or not old['official_only']: raise ValueError('Wrong S10 model')
    x=r12.features(cutoff,idx); xv=r12.features(cutoff,origins)
    base=old['climatology'][(origins+1)%12]
    control=np.maximum(base+r11.anomaly_prediction(old,xv),0).reshape(24,121,261)
    np.testing.assert_array_equal(control,np.load(r11.ART/f'{cutoff}_fine32.npy'))
    ref=r12.baseline(cutoff)
    np.testing.assert_array_equal(ref,r11.blend(r10.baseline(cutoff),control,.25))
    tp=np.load(CACHE/'tp.npy',mmap_mode='r')
    y=tp[idx+1,180:].reshape(len(idx),-1)-old['climatology'][(idx+1)%12]
    physics=np.load(ART/'moisture.npy',mmap_mode='r'); result={}
    for name in (CONFIGS if names is None else names):
        family,n=CONFIGS[name]; channels=2 if family=='flux' else 3
        raw=physics[:,:channels].reshape(len(physics),-1)
        prep_path=ART/f'{cutoff}_{name}_physics.joblib'
        if not prep_path.exists(): joblib.dump(fit_physics(raw,idx,n),prep_path)
        prep=joblib.load(prep_path)
        xx=np.column_stack([x,r10.weather_design(raw,prep,idx)])
        vv=np.column_stack([xv,r10.weather_design(raw,prep,origins)])
        model_path=ART/f'{cutoff}_{name}_pls.joblib'
        if not model_path.exists():
            model=r11.fit_pls(xx,y,32)
            model.update(cutoff=cutoff,official_only=True,climatology=old['climatology'],
                         physics_sha256=audit['moisture_sha256'],physics_model_sha256=r9.digest(prep_path))
            joblib.dump(model,model_path)
        model=joblib.load(model_path)
        if model['cutoff']!=cutoff or model['physics_sha256']!=audit['moisture_sha256']:
            raise ValueError('Stale physical model')
        anomaly=r11.anomaly_prediction(model,vv)
        np.testing.assert_array_equal(anomaly,r11.anomaly_prediction(joblib.load(model_path),vv))
        new=np.maximum(base+anomaly,0).reshape(24,121,261)
        pred=r11.blend(r10.baseline(cutoff),new,.25)
        np.testing.assert_array_equal(pred[:,:181],ref[:,:181])
        if not np.isfinite(pred).all() or (pred<0).any(): raise ValueError('Invalid prediction')
        output=ART/f'{cutoff}_{name}.npy'
        if output.exists(): np.testing.assert_array_equal(pred,np.load(output))
        else: np.save(output,pred)
        result[name]=pred
        print('PHYSICS PLS',cutoff,name,'pairs',len(idx),flush=True)
    save_json(ART/f'{cutoff}_training.json',dict(training_pairs=len(idx),last_target=f'{cutoff-1}-12',
              forecast_start=f'{cutoff}-01',linear_control_reproduced=True,official_only=True,
              source_s10_model_sha256=r9.digest(r11.ART/f'{cutoff}_fine32.joblib')))
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
    metadata.update(experiment='round14',model=name,base_model='S10',official_data_only=True,external_sources=[],
                    csv_sha256=r9.digest(destination),public_score=None,uploaded=False,training_targets_end='2022-12',
                    protocol=locked(),audit_sha256=r9.digest(OUT/'audit.json'),selection=selection,confirmation=confirmation,
                    artifact_hashes={p.name:r9.digest(p) for p in ART.glob('2023_*')},
                    versions={p:importlib.metadata.version(p) for p in ('numpy','scipy','scikit-learn','xarray','pandas')})
    save_json(destination.with_suffix('.json'),metadata); print('EXPORTED',destination,flush=True)


def summarize():
    locked(); selection=r9.read(OUT/'selection.json')
    lines=['# Rodada 14 — transporte e convergência de umidade','',
           'Somente dados oficiais; RMSE em toda a grade de 2009–2020, não score Kaggle.',
           f"Referência histórica S10: {selection['reference_rmse']:.6f}; público informado 1,71895.",'',
           '| Candidata | RMSE | Ganho | Blocos | Anos | Meses | Aprovada |',
           '| --- | ---: | ---: | ---: | ---: | ---: | --- |']
    for r in selection['ranking']:
        lines.append(f"| {r['model']} | {r['rmse']:.6f} | {100*r['relative_gain']:.3f}% | {r['blocks_improved']}/6 | "
                     f"{r['years_improved']}/12 | {r['months_improved']}/144 | {r['passed']} |")
    lines+=['',f"Selecionada: {selection['selected'] or 'nenhuma'}.",
            'Novos atributos físicos concatenados à representação S10; PLS32 reajustado e pesos preservados.',
            'Produtos de médias mensais em um nível são proxies, não fluxos reais integrados na coluna.',
            'Máscara de pressão e vizinhança evita usar indicadores abaixo do terreno; unidades ERA5 assumidas.',
            'Controle S10 reproduzido. Arquitetura e períodos reutilizados; 2021–2022 não é holdout inédito.',
            'Nenhuma chuva oculta 2023/2024, fonte externa, upload ou garantia de 1,70.',
            '', '[Protocolo](../../../experiments/ROUND14.md) · [Seleção](selection.json) · [Auditoria](audit.json)']
    if (OUT/'confirmation.json').exists():
        c=r9.read(OUT/'confirmation.json')
        lines+=['',f"Confirmação reutilizada: {c['reference']['rmse']:.6f} → {c['result']['rmse']:.6f}; aprovada: {c['passed']}."]
    elif not selection['selected']:
        lines+=['','Sem nova confirmação, treino final ou CSV. S10 preservada e nenhum envio consumido.']
    (OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8'); print('\n'.join(lines),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('prepare','evaluate','select','confirm','final','summarize'))
    globals()[parser.parse_args().stage]()
