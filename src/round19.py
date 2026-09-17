"""Histórico ampliado para o corretor; seleção estrita contra S12."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'): os.environ[k]='1'
import argparse
import json
from pathlib import Path
import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from . import round17 as old
from .round19_history import EARLY,ART
from .round9 import passes_gate,preceding

OUT=old.REPORT/'round19'
HISTORY=EARLY+old.HISTORY
CONFIGS=('expanded_uniform','expanded_recent8')


def locked():
    old.locked(); ART.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
    obj=dict(protocol_sha256=old.digest(old.ROOT/'experiments/ROUND19.md'),
        sources={p:old.digest(old.ROOT/'src'/p) for p in ('round19.py','round19_history.py','s11_delivery.py','round6.py','round4.py')},
        parent_protocol=old.read(old.OUT/'protocol.json'),configurations=CONFIGS,
        additional_blocks=EARLY,reference='S12 meta15_a0.25',minimum_gain=.003,
        s12_sha256='bba1f8b279447868170b6b2f9b18ee2cc723b891c25627c91438c7725d3aead8',official_only=True)
    obj=json.loads(json.dumps(obj)); path=OUT/'protocol.json'
    if path.exists() and old.read(path)!=obj: raise ValueError('Protocolo/código congelado mudou')
    if not path.exists(): old.save_json(path,obj)
    if old.digest(old.ROOT/'submissions/submission_12.csv')!=obj['s12_sha256']: raise ValueError('S12 alterada')
    return obj


def weights(years,cutoff,recent):
    if any(y+2>cutoff for y in years): raise ValueError('Bloco futuro')
    if not recent: return None
    targets=np.concatenate([12*y+np.arange(24) for y in years])
    w=2.**(-((cutoff*12-1)-targets)/96.)
    return np.repeat(w/w.mean(),2048)


def samples(year):
    if year not in HISTORY: raise ValueError('Alvos indisponíveis')
    if year not in EARLY: return old.samples(year)
    path=ART/f'{year}_samples.npz'
    record=old.read(path.with_suffix('.json'))
    if record['base_training_targets_end']!=f'{year-1}-12' or old.digest(path)!=record['sha256']: raise ValueError('Amostra inválida')
    with np.load(path) as z: return z['x'],z['y']


def fitted(cutoff,name):
    if name not in CONFIGS or cutoff not in old.DEV+(2021,2023): raise ValueError('Configuração inválida')
    years=preceding(HISTORY,cutoff); path=ART/f'{cutoff}_{name}.joblib'
    if path.exists():
        meta=old.read(path.with_suffix('.json'))
        if old.digest(path)!=meta['sha256'] or meta['training_blocks']!=years: raise ValueError('Modelo alterado')
        return joblib.load(path)
    items=[samples(y) for y in years]; x=np.concatenate([a for a,b in items]); y=np.concatenate([b for a,b in items])
    model=HistGradientBoostingRegressor(max_leaf_nodes=15,**old.TREE).fit(x,y,sample_weight=weights(years,cutoff,name.endswith('recent8')))
    joblib.dump(model,path); saved=joblib.load(path)
    np.testing.assert_array_equal(model.predict(x[:2048]),saved.predict(x[:2048]))
    old.save_json(path.with_suffix('.json'),dict(sha256=old.digest(path),training_blocks=years,
        last_training_target=f'{years[-1]+1}-12',samples=len(x),official_only=True,configuration=name))
    return saved


def prediction(cutoff,model):
    delta=np.stack([model.predict(old.matrix(cutoff,m,np.arange(78561))).reshape(301,261) for m in range(24)])
    return np.maximum(old.reference(cutoff)+.25*delta,0)


def reference(cutoff):
    return prediction(cutoff,old.fitted(cutoff,15))


def evaluate():
    locked(); old.audit()
    tp=np.load(old.CACHE/'tp.npy',mmap_mode='r')
    for year in old.DEV:
        path=OUT/f'{year}.json'
        if path.exists(): print('BLOCO EXISTENTE',year,flush=True); continue
        ref=reference(year); truth=tp[old.target_origins(year)+1]
        baseline=old.metrics(ref,truth,ref)
        original=next(r for r in old.read(old.OUT/f'{year}.json') if r['model']=='meta15_a0.25')
        if abs(original['rmse']-baseline['rmse'])>1e-12: raise ValueError('Referência S12 mudou')
        rows=[dict(model='s12',**baseline)]
        for name in CONFIGS:
            pred=prediction(year,fitted(year,name)); rows.append(dict(model=name,**old.metrics(pred,truth,ref)))
        old.save_json(path,rows); print('RESULTADO',year,[(r['model'],r['rmse']) for r in rows],flush=True)


def select():
    locked(); records={y:old.read(OUT/f'{y}.json') for y in old.DEV}
    refs=np.array([records[y][0]['monthly_rmse'] for y in old.DEV]); ref=float(np.sqrt(np.mean(refs**2)))
    second=float(np.sqrt(np.mean(refs[:,12:]**2))); yrs=np.sqrt(np.mean(refs.reshape(-1,12)**2,axis=1)); ranking=[]
    for name in CONFIGS:
        rs=[next(r for r in records[y] if r['model']==name) for y in old.DEV]
        ms=np.asarray([r['monthly_rmse'] for r in rs]); ys=np.sqrt(np.mean(ms.reshape(-1,12)**2,axis=1))
        rmse=float(np.sqrt(np.mean(ms**2))); sec=float(np.sqrt(np.mean(ms[:,12:]**2)))
        b=int(np.sum(np.mean(ms**2,axis=1)<np.mean(refs**2,axis=1))); yy=int(np.sum(ys<yrs)); mm=int(np.sum(ms<refs)); worst=float(np.max(ys/yrs-1))
        ranking.append(dict(model=name,rmse=rmse,relative_gain=1-rmse/ref,second_year_rmse=sec,
            blocks_improved=b,years_improved=yy,months_improved=mm,worst_annual_relative_change=worst,
            historical_correction_rms=float(np.sqrt(np.mean([r['correction_rms']**2 for r in rs]))),
            passed=passes_gate(rmse,ref,sec,second,b,yy,mm,144,worst)))
    ranking.sort(key=lambda r:r['rmse']); eligible=[r for r in ranking if r['passed']]
    result=dict(reference='S12',reference_rmse=ref,minimum_relative_gain=.003,ranking=ranking,
        selected=eligible[0]['model'] if eligible else None,periods_reused=True)
    path=OUT/'selection.json'
    if path.exists() and old.read(path)!=result: raise ValueError('Seleção mudou')
    old.save_json(path,result); print(json.dumps(result,indent=2),flush=True)


def selected():
    name=old.read(OUT/'selection.json')['selected']
    if name is None: raise ValueError('Nenhuma candidata aprovada: S13 bloqueada')
    return name


def confirm():
    from .round17_experimental import confirmation_passes
    locked(); name=selected(); path=OUT/'confirmation.json'
    if path.exists(): print(json.dumps(old.read(path),indent=2)); return
    ref=reference(2021); pred=prediction(2021,fitted(2021,name))
    truth=np.load(old.CACHE/'tp.npy',mmap_mode='r')[old.target_origins(2021)+1]
    before,after=old.metrics(ref,truth,ref),old.metrics(pred,truth,ref)
    result=dict(candidate=name,reference=before,result=after,passed=confirmation_passes(before,after),
        previously_consumed_period=True,no_post_confirmation_tuning=True)
    old.save_json(path,result); print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('stage',choices=('evaluate','select','confirm'))
    globals()[p.parse_args().stage]()
