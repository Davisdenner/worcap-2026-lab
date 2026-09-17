"""Ablação causal de produtos, convergência e lags de umidade de 850 hPa."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
import argparse
import gc
import json
from functools import lru_cache
import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from . import round17 as old
from . import round20 as prior
from .round9 import preceding,passes_gate

ART=old.ROOT/'data/processed/round24'
OUT=old.REPORT/'round24'
PROTOCOL=old.ROOT/'experiments/ROUND24.md'
KINDS={'produtos':2,'convergencia':3,'transporte_lag':6}
BETAS=(.25,.5)
SCOPES=('global','norte')
CONFIGS={f'{kind}_{scope}_b{beta:g}':(kind,scope,beta)
         for kind in ('convergencia','transporte_lag') for scope in SCOPES for beta in BETAS}
RADIUS=6371000.
STEP=np.pi/180*.25*RADIUS
ALL_CELLS=np.arange(78561)


def locked():
    prior.locked(); ART.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
    obj=dict(protocol_sha256=old.digest(PROTOCOL),source_sha256=old.digest(old.ROOT/'src/round24.py'),
        parent_protocol=old.read(prior.OUT/'protocol.json'),kinds=KINDS,configs=CONFIGS,
        tree=old.TREE,seed=old.SEED,reference='S12',official_only=True,
        minimum_relative_gain=.003,flux_units='convergence 1e-6 per second')
    obj=json.loads(json.dumps(obj)); path=OUT/'protocol.json'
    if path.exists() and old.read(path)!=obj: raise ValueError('Protocolo ou código da rodada 24 mudou')
    if not path.exists(): old.save_json(path,obj)
    return obj


@lru_cache(maxsize=1)
def fields():
    return tuple(np.load(old.CACHE/f'{name}.npy',mmap_mode='r')
                 for name in ('shum_850','u_850','v_850'))


@lru_cache(maxsize=4)
def flux(origin):
    if origin<0 or origin>=996: raise ValueError('Estado atmosférico indisponível')
    qraw,uraw,vraw=fields()
    q=np.asarray(qraw[origin],np.float32); u=np.asarray(uraw[origin],np.float32)
    v=np.asarray(vraw[origin],np.float32)
    qu=q*u; qv=q*v
    lat=np.deg2rad(np.arange(-60,15.01,.25))
    dx=STEP*np.cos(lat)[:,None]
    convergence=-(np.gradient(qu,axis=1)/dx+np.gradient(qv,axis=0)/STEP)*1e6
    yi,xi=np.indices(q.shape)
    y_up=np.clip(yi-8*np.sign(v).astype(int),0,300)
    x_up=np.clip(xi-8*np.sign(u).astype(int),0,260)
    upstream=q[y_up,x_up]-q
    values=(qu.ravel(),qv.ravel(),convergence.astype(np.float32).ravel(),upstream.ravel())
    if any(not np.isfinite(x).all() for x in values): raise ValueError('Fluxo não finito')
    return values


def extra(origin,cells):
    current=flux(int(origin)); prev1=flux(int(origin)-1)[2]
    prev2=flux(int(origin)-2)[2]
    cells=np.asarray(cells)
    x=np.column_stack([current[0][cells],current[1][cells],current[2][cells],
                       prev1[cells],(current[2][cells]+prev1[cells]+prev2[cells])/3,
                       current[3][cells]]).astype(np.float32)
    if x.shape!=(len(cells),6) or not np.isfinite(x).all(): raise ValueError('Atributos inválidos')
    return x


def north_mask():
    lat=-60+(ALL_CELLS//261)*.25
    result=np.clip((lat+5)/5,0,1).reshape(301,261)
    if result.min()!=0 or result.max()!=1: raise ValueError('Máscara norte inválida')
    return result


def samples(cutoff):
    years=preceding(old.HISTORY,cutoff)
    if not years or any(year+2>cutoff for year in years): raise ValueError('Bloco futuro no treino')
    base=[]; target=[]; added=[]
    for year in years:
        x,y=old.samples(year)
        meta=old.read(old.ART/f'{year}_samples.json')
        if meta['residual_targets_end']!=f'{year+1}-12': raise ValueError('Alvo residual futuro')
        rng=np.random.default_rng(old.SEED+year)
        extras=np.empty((len(x),6),np.float32)
        for month,origin in enumerate(old.target_origins(year)):
            cells=rng.choice(78561,2048,replace=False)
            sl=slice(month*2048,(month+1)*2048)
            np.testing.assert_array_equal(x[sl,0],(-60+(cells//261)*.25).astype(np.float32))
            np.testing.assert_array_equal(x[sl,1],(-90+(cells%261)*.25).astype(np.float32))
            extras[sl]=extra(origin,cells)
        base.append(x); target.append(y); added.append(extras)
    return years,np.concatenate(base),np.concatenate(added),np.concatenate(target)


def fitted(cutoff,kind,years,base,added,target):
    path=ART/f'{cutoff}_{kind}.joblib'
    if path.exists():
        meta=old.read(path.with_suffix('.json'))
        if old.digest(path)!=meta['sha256'] or meta['training_blocks']!=years:
            raise ValueError('Modelo de transporte alterado')
        return joblib.load(path)
    x=np.column_stack([base,added[:,:KINDS[kind]]])
    model=HistGradientBoostingRegressor(max_leaf_nodes=15,**old.TREE).fit(x,target)
    joblib.dump(model,path); saved=joblib.load(path)
    np.testing.assert_array_equal(model.predict(x[:2048]),saved.predict(x[:2048]))
    old.save_json(path.with_suffix('.json'),dict(sha256=old.digest(path),cutoff=cutoff,
        kind=kind,features=x.shape[1],training_blocks=years,
        last_training_target=f'{years[-1]+1}-12',samples=len(x),official_only=True))
    print('TREINADO',cutoff,kind,len(x),flush=True)
    return saved


def delta(cutoff,models):
    names=('original',)+tuple(KINDS)
    paths={name:ART/f'{cutoff}_{name}_delta.npy' for name in names}
    if all(path.exists() for path in paths.values()):
        for path in paths.values():
            if old.digest(path)!=old.read(path.with_suffix('.json'))['sha256']:
                raise ValueError('Previsão de correção alterada')
        return {name:np.load(path) for name,path in paths.items()}
    output={name:np.empty((24,301,261)) for name in names}
    original=old.fitted(cutoff,15)
    for month,origin in enumerate(old.target_origins(cutoff)):
        base=old.matrix(cutoff,month,ALL_CELLS)
        added=extra(origin,ALL_CELLS)
        output['original'][month]=original.predict(base).reshape(301,261)
        for name,model in models.items():
            x=np.column_stack([base,added[:,:KINDS[name]]])
            output[name][month]=model.predict(x).reshape(301,261)
        print('PREVISTO',cutoff,month+1,flush=True)
    for name,path in paths.items():
        np.save(path,output[name])
        old.save_json(path.with_suffix('.json'),dict(sha256=old.digest(path),cutoff=cutoff,
            model=name,official_only=True))
    return output


def forecast(s11,deltas,kind,scope,beta):
    if kind not in ('convergencia','transporte_lag') or scope not in SCOPES or beta not in BETAS:
        raise ValueError('Candidata não registrada')
    mask=1 if scope=='global' else north_mask()
    return np.maximum(s11+.25*(deltas['original']+beta*mask*(deltas[kind]-deltas['original'])),0)


def regional_metrics(pred,truth):
    north=np.arange(-60,15.01,.25)>=0
    err=(np.asarray(pred)-truth)**2
    n=float(np.sqrt(np.mean(err[:,north,:])))
    rest=float(np.sqrt(np.mean(err[:,~north,:])))
    frac=float(np.sum(err[:,north,:])/np.sum(err))
    return dict(north_rmse=n,outside_rmse=rest,north_sse_fraction=frac)


def evaluate_block(cutoff):
    locked(); prior.audit()
    path=OUT/f'{cutoff}.json'
    if path.exists(): print('BLOCO EXISTENTE',cutoff,flush=True); return
    years,base,added,target=samples(cutoff)
    models={kind:fitted(cutoff,kind,years,base,added,target) for kind in KINDS}
    del base,added,target
    correction=delta(cutoff,models)
    s11=old.reference(cutoff); ref=prior.reference(cutoff)
    np.testing.assert_allclose(np.maximum(s11+.25*correction['original'],0),ref,rtol=0,atol=1e-8)
    truth=np.load(old.CACHE/'tp.npy',mmap_mode='r')[old.target_origins(cutoff)+1]
    rows=[dict(model='s12',**old.metrics(ref,truth,ref),**regional_metrics(ref,truth))]
    for name,(kind,scope,beta) in CONFIGS.items():
        pred=forecast(s11,correction,kind,scope,beta)
        rows.append(dict(model=name,**old.metrics(pred,truth,ref),**regional_metrics(pred,truth)))
    pure=[]
    for kind in KINDS:
        pred=np.maximum(s11+.25*correction[kind],0)
        pure.append(dict(model=kind,**old.metrics(pred,truth,ref),**regional_metrics(pred,truth)))
    old.save_json(OUT/f'{cutoff}_pure.json',pure); old.save_json(path,rows)
    print('RESULTADOS',cutoff,[(r['model'],round(r['rmse'],6)) for r in rows],flush=True)
    del correction,models,s11,ref,truth
    old.data.cache_clear(); old.reference.cache_clear(); flux.cache_clear(); fields.cache_clear(); gc.collect()


def evaluate():
    for year in old.DEV: evaluate_block(year)


def select():
    locked(); records={year:old.read(OUT/f'{year}.json') for year in old.DEV}
    refs=np.array([records[year][0]['monthly_rmse'] for year in old.DEV])
    ref=float(np.sqrt(np.mean(refs**2))); second=float(np.sqrt(np.mean(refs[:,12:]**2)))
    refyears=np.sqrt(np.mean(refs.reshape(-1,12)**2,axis=1)); ranking=[]
    for name in CONFIGS:
        rs=[next(r for r in records[y] if r['model']==name) for y in old.DEV]
        months=np.array([r['monthly_rmse'] for r in rs]); years=np.sqrt(np.mean(months.reshape(-1,12)**2,axis=1))
        rmse=float(np.sqrt(np.mean(months**2))); sec=float(np.sqrt(np.mean(months[:,12:]**2)))
        blocks=int(np.sum(np.mean(months**2,axis=1)<np.mean(refs**2,axis=1)))
        nyears=int(np.sum(years<refyears)); nmonths=int(np.sum(months<refs))
        worst=float(np.max(years/refyears-1))
        ranking.append(dict(model=name,rmse=rmse,relative_gain=1-rmse/ref,
            second_year_rmse=sec,blocks_improved=blocks,years_improved=nyears,
            months_improved=nmonths,worst_annual_relative_change=worst,
            historical_correction_rms=float(np.sqrt(np.mean([r['correction_rms']**2 for r in rs]))),
            north_rmse=float(np.sqrt(np.mean([r['north_rmse']**2 for r in rs]))),
            outside_rmse=float(np.sqrt(np.mean([r['outside_rmse']**2 for r in rs]))),
            passed=passes_gate(rmse,ref,sec,second,blocks,nyears,nmonths,144,worst)))
    ranking.sort(key=lambda r:r['rmse']); eligible=[r for r in ranking if r['passed']]
    result=dict(reference='S12',reference_rmse=ref,minimum_relative_gain=.003,
        ranking=ranking,selected=eligible[0]['model'] if eligible else None,
        periods_reused=True,csv_exported=False,uploaded=False)
    path=OUT/'selection.json'
    if path.exists() and old.read(path)!=result: raise ValueError('Seleção mudou')
    old.save_json(path,result); print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)


def summarize():
    locked(); selected=old.read(OUT/'selection.json')
    lines=['# Rodada 24 — transporte de umidade de 850 hPa','',
        f"S12 histórica: {selected['reference_rmse']:.6f} mm/dia.",
        'Somente dados oficiais. Períodos reutilizados; sem teste independente.','',
        '| Candidata | RMSE | Ganho | Blocos | Anos | Meses | Norte | Aprovada |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |']
    for row in selected['ranking']:
        lines.append(f"| {row['model']} | {row['rmse']:.6f} | {100*row['relative_gain']:.3f}% | "
            f"{row['blocks_improved']}/6 | {row['years_improved']}/12 | {row['months_improved']}/144 | "
            f"{row['north_rmse']:.4f} | {row['passed']} |")
    lines += ['',f"Selecionada: {selected['selected'] or 'nenhuma'}.",
              'Nenhuma confirmação, previsão final, CSV ou upload foi realizada.']
    (OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines),flush=True)


if __name__=='__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=('evaluate','select','summarize'))
    p.add_argument('--year',type=int)
    args=p.parse_args()
    if args.year is not None:
        if args.stage!='evaluate' or args.year not in old.DEV: raise ValueError('Corte inválido')
        evaluate_block(args.year)
    elif args.stage=='evaluate': evaluate()
    else: globals()[args.stage]()
