"""Testes controlados do início de treino e da decomposição espacial da saída."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
import argparse
import gc
import json
import joblib
import numpy as np
from scipy.ndimage import uniform_filter
from sklearn.ensemble import HistGradientBoostingRegressor
from . import round17 as old
from . import round20 as prior
from .competition import training_pairs
from .round2 import Features, target_origins
from .round9 import passes_gate

ART=old.ROOT/'data/processed/round22_23'
OUT22=old.REPORT/'round22'
OUT23=old.REPORT/'round23'
PROTOCOLS=(old.ROOT/'experiments/ROUND22.md',old.ROOT/'experiments/ROUND23.md')
STARTS={'start1940':'1940-03-01','start1960':'1960-01-01','start1981':'1981-01-01'}
FRACTIONS=(.10,.25)
TREE=dict(loss='squared_error',learning_rate=.05,max_iter=150,max_leaf_nodes=15,
          min_samples_leaf=100,l2_regularization=10.,max_bins=128,
          early_stopping=False,random_state=20260914)
SEED=20260914
N=512


def locked():
    prior.locked()
    ART.mkdir(parents=True,exist_ok=True); OUT22.mkdir(parents=True,exist_ok=True); OUT23.mkdir(parents=True,exist_ok=True)
    obj=dict(protocol_hashes=[old.digest(p) for p in PROTOCOLS],source_sha256=old.digest(old.ROOT/'src/round22_23.py'),
             parent_protocol=old.read(prior.OUT/'protocol.json'),starts=STARTS,
             tree=TREE,points_per_month=N,fractions=FRACTIONS,smooth_size=9,
             reference='S12',official_only=True,minimum_relative_gain=.003)
    obj=json.loads(json.dumps(obj))
    for out in (OUT22,OUT23):
        path=out/'protocol.json'
        if path.exists() and old.read(path)!=obj: raise ValueError('Código ou protocolos 22/23 mudaram')
        if not path.exists(): old.save_json(path,obj)
    return obj


def features(cutoff,name):
    if name not in STARTS: raise ValueError('Início inválido')
    f=Features(cutoff)
    f.idx=training_pairs(f.times,f'{cutoff}-01-01',start=STARTS[name])
    if f.idx.min()<2 or f.idx.max()+1 >= (cutoff-1940)*12:
        raise ValueError('Contexto indisponível ou alvo alcança a validação')
    for j,w in enumerate(f.weather):
        for month in range(12):
            f.means[month,:,j]=np.nanmean(w[f.idx[f.idx%12==month]],axis=0)
    np.nan_to_num(f.means,copy=False)
    return f


def cells_for(origin):
    return np.random.default_rng(SEED+int(origin)).choice(78561,N,replace=False)


def training(f,decompose=False):
    count=len(f.idx)
    x=np.empty((count*N,55),np.float32)
    direct=np.empty(count*N,np.float32)
    broad=np.empty(count*N,np.float32) if decompose else None
    detail=np.empty(count*N,np.float32) if decompose else None
    for k,origin in enumerate(f.idx):
        cells=cells_for(origin); sl=slice(k*N,(k+1)*N)
        x[sl]=f.matrix(origin,cells,context=True)
        truth=f.tp[origin+1,cells]
        direct[sl]=truth-x[sl,4]
        if decompose:
            target=(origin+1)%12
            wide=uniform_filter(f.tp[origin+1].reshape(301,261),size=9,mode='nearest').ravel()
            climowide=uniform_filter(f.climo[target].reshape(301,261),size=9,mode='nearest').ravel()
            broad[sl]=wide[cells]-climowide[cells]
            detail[sl]=truth-wide[cells]
    if not np.isfinite(x).all() or not np.isfinite(direct).all(): raise ValueError('Amostras inválidas')
    if decompose and (not np.isfinite(broad).all() or not np.isfinite(detail).all()): raise ValueError('Alvos inválidos')
    return x,direct,broad,detail


def fitted(cutoff,name,kind,x,y):
    path=ART/f'{cutoff}_{name}_{kind}.joblib'
    if path.exists():
        meta=old.read(path.with_suffix('.json'))
        if old.digest(path)!=meta['sha256'] or meta['last_training_target']!=f'{cutoff-1}-12':
            raise ValueError('Modelo alterado')
        return joblib.load(path)
    model=HistGradientBoostingRegressor(**TREE).fit(x,y)
    joblib.dump(model,path); saved=joblib.load(path)
    np.testing.assert_array_equal(saved.predict(x[:1024]),model.predict(x[:1024]))
    old.save_json(path.with_suffix('.json'),dict(sha256=old.digest(path),cutoff=cutoff,
        start=STARTS[name],kind=kind,training_months=len(x)//N,samples=len(x),
        last_training_target=f'{cutoff-1}-12',official_only=True))
    print('TREINADO',cutoff,name,kind,len(x),flush=True)
    return saved


def prediction(cutoff,name,kind,f,models):
    path=ART/f'{cutoff}_{name}_{kind}.npy'
    if path.exists():
        if old.digest(path)!=old.read(path.with_suffix('.json'))['sha256']:
            raise ValueError('Previsão alterada')
        return np.load(path)
    cells=np.arange(78561); result=np.empty((24,301,261),np.float32)
    for month,origin in enumerate(target_origins(cutoff)):
        x=f.matrix(origin,cells,context=True)
        if kind=='direct':
            values=x[:,4]+models[0].predict(x)
        else:
            target=(origin+1)%12
            smooth=uniform_filter(f.climo[target].reshape(301,261),size=9,mode='nearest').ravel()
            values=smooth+models[0].predict(x)+models[1].predict(x)
        result[month]=np.maximum(values,0).reshape(301,261)
    np.save(path,result)
    old.save_json(path.with_suffix('.json'),dict(sha256=old.digest(path),cutoff=cutoff,
        start=STARTS[name],kind=kind,official_only=True))
    return result


def rows_for(reference,truth,predictions,which):
    rows=[dict(model='s12',**old.metrics(reference,truth,reference))]
    for name in which:
        pred=predictions[name]
        for fraction in FRACTIONS:
            value=reference+fraction*(pred-reference)
            rows.append(dict(model=f'{name}_a{fraction:g}',**old.metrics(value,truth,reference)))
    return rows


def evaluate_block(cutoff):
    locked(); prior.audit()
    p22,p23=OUT22/f'{cutoff}.json',OUT23/f'{cutoff}.json'
    if p22.exists() and p23.exists(): print('BLOCO EXISTENTE',cutoff,flush=True); return
    reference=prior.reference(cutoff)
    truth=np.load(old.CACHE/'tp.npy',mmap_mode='r')[target_origins(cutoff)+1]
    predictions={}
    pure=[]
    for name in ('start1981','start1960','start1940'):
        f=features(cutoff,name)
        x,y,broad,detail=training(f,decompose=(name=='start1981'))
        direct_model=fitted(cutoff,name,'direct',x,y)
        pred=prediction(cutoff,name,'direct',f,(direct_model,))
        predictions[name]=pred
        pure.append(dict(model=name,**old.metrics(pred,truth,reference)))
        if name=='start1981':
            broad_model=fitted(cutoff,name,'broad9',x,broad)
            detail_model=fitted(cutoff,name,'detail9',x,detail)
            decomposed=prediction(cutoff,name,'decomposed9',f,(broad_model,detail_model))
            predictions['decomposed9']=decomposed
            pure.append(dict(model='decomposed9',**old.metrics(decomposed,truth,reference)))
        print('PREVISTO',cutoff,name,flush=True)
        del f,x,y,broad,detail,direct_model
        if name=='start1981': del broad_model,detail_model
        gc.collect()
    if not p22.exists():
        old.save_json(p22,rows_for(reference,truth,predictions,('start1981','start1960','start1940')))
        old.save_json(OUT22/f'{cutoff}_pure.json',[r for r in pure if r['model']!='decomposed9'])
    if not p23.exists():
        old.save_json(p23,rows_for(reference,truth,predictions,('start1981','decomposed9')))
        old.save_json(OUT23/f'{cutoff}_pure.json',[r for r in pure if r['model'] in ('start1981','decomposed9')])
    print('RESULTADOS',cutoff,[(r['model'],round(r['rmse'],6)) for r in pure],flush=True)


def select(out,candidates):
    locked(); records={year:old.read(out/f'{year}.json') for year in old.DEV}
    refs=np.array([records[y][0]['monthly_rmse'] for y in old.DEV]); ref=float(np.sqrt(np.mean(refs**2)))
    second=float(np.sqrt(np.mean(refs[:,12:]**2))); refyears=np.sqrt(np.mean(refs.reshape(-1,12)**2,axis=1))
    ranking=[]
    for name in candidates:
        rs=[next(r for r in records[y] if r['model']==name) for y in old.DEV]
        months=np.array([r['monthly_rmse'] for r in rs]); years=np.sqrt(np.mean(months.reshape(-1,12)**2,axis=1))
        rmse=float(np.sqrt(np.mean(months**2))); sec=float(np.sqrt(np.mean(months[:,12:]**2)))
        blocks=int(np.sum(np.mean(months**2,axis=1)<np.mean(refs**2,axis=1)))
        yy=int(np.sum(years<refyears)); mm=int(np.sum(months<refs)); worst=float(np.max(years/refyears-1))
        ranking.append(dict(model=name,rmse=rmse,relative_gain=1-rmse/ref,second_year_rmse=sec,
            blocks_improved=blocks,years_improved=yy,months_improved=mm,worst_annual_relative_change=worst,
            historical_correction_rms=float(np.sqrt(np.mean([r['correction_rms']**2 for r in rs]))),
            passed=passes_gate(rmse,ref,sec,second,blocks,yy,mm,144,worst)))
    ranking.sort(key=lambda r:r['rmse']); eligible=[r for r in ranking if r['passed']]
    result=dict(reference='S12',reference_rmse=ref,minimum_relative_gain=.003,
        ranking=ranking,selected=eligible[0]['model'] if eligible else None,
        periods_reused=True,csv_exported=False,uploaded=False)
    path=out/'selection.json'
    if path.exists() and old.read(path)!=result: raise ValueError('Seleção mudou')
    old.save_json(path,result); print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)


def select22():
    select(OUT22,tuple(f'{name}_a{a:g}' for name in ('start1960','start1940') for a in FRACTIONS))


def select23():
    select(OUT23,tuple(f'decomposed9_a{a:g}' for a in FRACTIONS))


def summarize(out,title):
    locked(); s=old.read(out/'selection.json')
    lines=[f'# {title}','',f"S12 histórica: {s['reference_rmse']:.6f} mm/dia.",
        'Somente dados oficiais. Períodos reutilizados; sem teste independente.','',
        '| Candidata | RMSE | Ganho | Blocos | Anos | Meses | Aprovada |',
        '| --- | ---: | ---: | ---: | ---: | ---: | --- |']
    for r in s['ranking']:
        lines.append(f"| {r['model']} | {r['rmse']:.6f} | {100*r['relative_gain']:.3f}% | "
                     f"{r['blocks_improved']}/6 | {r['years_improved']}/12 | "
                     f"{r['months_improved']}/144 | {r['passed']} |")
    lines += ['',f"Selecionada: {s['selected'] or 'nenhuma'}.",
              'Nenhuma confirmação, previsão final, CSV ou upload foi realizado.']
    (out/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines),flush=True)


def summarize22(): summarize(OUT22,'Rodada 22 — início do treino-base')
def summarize23(): summarize(OUT23,'Rodada 23 — saída ampla + detalhe local')


if __name__=='__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=('evaluate','select22','select23','summarize22','summarize23'))
    p.add_argument('--year',type=int)
    args=p.parse_args()
    if args.year is not None:
        if args.stage!='evaluate' or args.year not in old.DEV: raise ValueError('Corte inválido')
        evaluate_block(args.year)
    elif args.stage=='evaluate':
        for year in old.DEV: evaluate_block(year)
    else: globals()[args.stage]()
