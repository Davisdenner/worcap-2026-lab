"""Aprendizado direto local/global, comparação controlada e gates contra S12."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'): os.environ[key]='1'
import argparse
import gc
import json
import time
import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from . import round17 as old
from . import round19 as previous
from .round2 import Features,target_origins
from .round9 import passes_gate
from .round17_experimental import confirmation_passes

ART=old.ROOT/'data/processed/round20'
OUT=old.REPORT/'round20'
PROTOCOL=old.ROOT/'experiments/ROUND20.md'
MODELS={'local15':(False,15,768,100,10.),'global15':(True,15,768,100,10.),
        'global31':(True,31,768,100,10.),'global31_dense':(True,31,1536,200,20.)}
FRACTIONS=(.10,.25)
CONFIGS={f'{name}_a{a:g}':(name,a) for name in MODELS for a in FRACTIONS}
SEED=20260914
TREE=dict(loss='squared_error',learning_rate=.05,max_iter=300,max_bins=128,
          early_stopping=False,warm_start=False,random_state=SEED)
S12_HASH='bba1f8b279447868170b6b2f9b18ee2cc723b891c25627c91438c7725d3aead8'


def transform_paths(year):
    return [old.ROOT/f'data/processed/round9/{year}_pls16.joblib',
            old.ROOT/f'data/processed/round11/{year}_fine_weather.joblib']


def locked():
    old.locked(); ART.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
    dependencies=('round20.py','round2.py','round9.py','round19.py','round17_experimental.py')
    protected=[old.ROOT/f'submissions/submission_{n}.{ext}' for n in ('10','11','12') for ext in ('csv','json')]
    obj=dict(protocol_sha256=old.digest(PROTOCOL),sources={p:old.digest(old.ROOT/'src'/p) for p in dependencies},
        inherited_protocol=old.read(old.OUT/'protocol.json'),models=MODELS,tree=TREE,configurations=CONFIGS,
        reference='S12',minimum_gain=.003,official_only=True,
        transforms={str(y):{p.relative_to(old.ROOT).as_posix():old.digest(p) for p in transform_paths(y)} for y in old.DEV+(2021,)},
        protected={p.relative_to(old.ROOT).as_posix():old.digest(p) for p in protected})
    obj=json.loads(json.dumps(obj)); path=OUT/'protocol.json'
    if obj['protected']['submissions/submission_12.csv']!=S12_HASH: raise ValueError('S12 alterada')
    if path.exists() and old.read(path)!=obj: raise ValueError('Protocolo, modelo-base ou código congelado mudou')
    if not path.exists(): old.save_json(path,obj)
    return obj


def audit():
    old.audit()
    coarse=old.ROOT/'data/processed/round3/coarse_weather.npy'
    fine=old.ROOT/'data/processed/round11/fine_weather.npy'
    expected_coarse=old.read(old.REPORT/'round9/audit.json')['coarse_sha256']
    expected_fine=old.read(old.REPORT/'round11/audit.json')['fine_sha256']
    if old.digest(coarse)!=expected_coarse or old.digest(fine)!=expected_fine: raise ValueError('Cache espacial auditado alterado')
    old.save_json(OUT/'audit.json',dict(passed=True,official_only=True,
        official_array_audit=old.read(old.OUT/'audit.json'),coarse_sha256=expected_coarse,fine_sha256=expected_fine))


def global_features(raw,model,origins):
    origins=np.asarray(origins)
    if origins.min()<2 or origins.max()>=len(raw): raise ValueError('Histórico atmosférico indisponível')
    take=np.arange(origins.max()+1)
    # Transformação ponto a ponto no tempo; nenhum campo posterior à origem requerida.
    z=model['pca'].transform((raw[take]-model['means'][take%12])/model['scale'])[:,:16]
    z/=model['pc_scale'][:16]
    return np.column_stack([z[origins],sum(z[origins-k] for k in range(3))/3]).astype(np.float32)


def context(f):
    files=transform_paths(f.year)
    arrays=[np.load(old.ROOT/'data/processed/round3/coarse_weather.npy',mmap_mode='r'),
            np.load(old.ROOT/'data/processed/round11/fine_weather.npy',mmap_mode='r')]
    transforms=[joblib.load(p) for p in files]
    if transforms[0]['training_cutoff']!=f'{f.year}-01' or not transforms[0]['official_only']: raise ValueError('PCA continental de outro corte')
    train=[]; valid=[]
    for raw,model in zip(arrays,transforms):
        means=np.stack([raw[f.idx[f.idx%12==m]].mean(axis=0) for m in range(12)])
        np.testing.assert_array_equal(means,model['means'])
        scale=np.maximum((raw[f.idx]-means[f.idx%12]).std(axis=0),1e-8)
        np.testing.assert_array_equal(scale,model['scale'])
        train.append(global_features(raw,model,f.idx)); valid.append(global_features(raw,model,target_origins(f.year)))
    old.save_json(ART/f'{f.year}_context.json',dict(last_training_target=f'{f.year-1}-12',
        supervised_pls_unused=True,training_means_and_scales_verified=True,pcs_each_region=16,
        features=64,source_hashes={p.relative_to(old.ROOT).as_posix():old.digest(p) for p in files}))
    return np.column_stack(train),np.column_stack(valid)


def nested_cells(origins):
    rng=np.random.default_rng(SEED)
    return [rng.choice(78561,1536,replace=False) for _ in origins]


def training(f,global_train):
    if f.idx.max()+1 >= (f.year-1940)*12: raise ValueError('Alvo alcança o bloco de validação')
    x=np.empty((len(f.idx),1536,119),np.float32); y=np.empty((len(f.idx),1536),np.float32)
    for k,(o,cells) in enumerate(zip(f.idx,nested_cells(f.idx))):
        local=f.matrix(o,cells,context=True)
        x[k,:,:55]=local; x[k,:,55:]=global_train[k]
        y[k]=f.tp[o+1,cells]-local[:,4]
    if not np.isfinite(x).all() or not np.isfinite(y).all(): raise ValueError('Treino não finito')
    return x,y


def fitted(f,name,x,y):
    with_global,leaves,n,minimum,l2=MODELS[name]
    width=119 if with_global else 55
    path=ART/f'{f.year}_{name}.joblib'
    if path.exists():
        meta=old.read(path.with_suffix('.json'))
        if old.digest(path)!=meta['sha256'] or meta['last_training_target']!=f'{f.year-1}-12': raise ValueError('Modelo alterado')
        return joblib.load(path)
    xt=np.ascontiguousarray(x[:,:n,:width].reshape(-1,width)); yt=np.ascontiguousarray(y[:,:n].reshape(-1))
    started=time.perf_counter()
    model=HistGradientBoostingRegressor(max_leaf_nodes=leaves,min_samples_leaf=minimum,l2_regularization=l2,**TREE).fit(xt,yt)
    joblib.dump(model,path); saved=joblib.load(path)
    np.testing.assert_array_equal(saved.predict(xt[:2048]),model.predict(xt[:2048]))
    old.save_json(path.with_suffix('.json'),dict(sha256=old.digest(path),model=name,
        cutoff=f.year,last_training_target=f'{f.year-1}-12',training_months=len(f.idx),samples=len(xt),
        features=width,official_only=True,train_seconds=time.perf_counter()-started))
    print('MODELO TREINADO',f.year,name,len(xt),round(time.perf_counter()-started,1),'s',flush=True)
    return saved


def predict(f,name,model,global_valid):
    path=ART/f'{f.year}_{name}_prediction.npy'
    if path.exists():
        if old.digest(path)!=old.read(path.with_suffix('.json'))['sha256']: raise ValueError('Previsão alterada')
        return np.load(path)
    result=np.empty((24,301,261),np.float32); cells=np.arange(78561)
    for k,o in enumerate(target_origins(f.year)):
        x=f.matrix(o,cells,context=True)
        if MODELS[name][0]: x=np.column_stack([x,np.broadcast_to(global_valid[k],(len(cells),64))])
        result[k]=np.maximum(x[:,4]+model.predict(x),0).reshape(301,261)
    np.save(path,result)
    old.save_json(path.with_suffix('.json'),dict(sha256=old.digest(path),model=name,official_only=True))
    return result


def reference(year):
    path=ART/f'{year}_s12.npy'
    if path.exists():
        if old.digest(path)!=old.read(path.with_suffix('.json'))['sha256']: raise ValueError('Referência alterada')
        return np.load(path)
    ref=previous.reference(year)
    if year in old.DEV:
        truth=np.load(old.CACHE/'tp.npy',mmap_mode='r')[target_origins(year)+1]
        expected=next(row for row in old.read(old.OUT/f'{year}.json') if row['model']=='meta15_a0.25')['rmse']
        if abs(old.metrics(ref,truth,ref)['rmse']-expected)>1e-12: raise ValueError('Controle S12 não reproduzido')
    np.save(path,ref); old.save_json(path.with_suffix('.json'),dict(sha256=old.digest(path),reference='S12'))
    return ref


def evaluate():
    locked(); audit()
    for year in old.DEV:
        path=OUT/f'{year}.json'
        if path.exists(): print('BLOCO EXISTENTE',year,flush=True); continue
        print('INICIANDO BLOCO',year,flush=True)
        f=Features(year); gtrain,gvalid=context(f); x,y=training(f,gtrain)
        ref=reference(year); truth=f.tp[target_origins(year)+1].reshape(24,301,261)
        rows=[dict(model='s12',**old.metrics(ref,truth,ref))]
        direct=[]
        for name in MODELS:
            model=fitted(f,name,x,y); pred=predict(f,name,model,gvalid)
            direct.append(dict(model=name,**old.metrics(pred,truth,ref)))
            for a in FRACTIONS:
                value=ref+a*(pred-ref)
                rows.append(dict(model=f'{name}_a{a:g}',**old.metrics(value,truth,ref)))
            print('AVALIADO',year,name,'RMSE direto',direct[-1]['rmse'],flush=True)
        old.save_json(OUT/f'{year}_direct.json',direct); old.save_json(path,rows)
        print('BLOCO CONCLUÍDO',year,[(r['model'],round(r['rmse'],6)) for r in rows],flush=True)
        del f,x,y,ref,truth,pred,model; old.data.cache_clear(); old.reference.cache_clear(); gc.collect()


def select():
    locked(); records={y:old.read(OUT/f'{y}.json') for y in old.DEV}
    refs=np.array([records[y][0]['monthly_rmse'] for y in old.DEV]); ref=float(np.sqrt(np.mean(refs**2)))
    second=float(np.sqrt(np.mean(refs[:,12:]**2))); yrs=np.sqrt(np.mean(refs.reshape(-1,12)**2,axis=1)); ranking=[]
    for name in CONFIGS:
        rows=[next(r for r in records[y] if r['model']==name) for y in old.DEV]
        months=np.array([r['monthly_rmse'] for r in rows]); years=np.sqrt(np.mean(months.reshape(-1,12)**2,axis=1))
        rmse=float(np.sqrt(np.mean(months**2))); sec=float(np.sqrt(np.mean(months[:,12:]**2)))
        b=int(np.sum(np.mean(months**2,axis=1)<np.mean(refs**2,axis=1))); yy=int(np.sum(years<yrs)); mm=int(np.sum(months<refs)); worst=float(np.max(years/yrs-1))
        ranking.append(dict(model=name,rmse=rmse,relative_gain=1-rmse/ref,second_year_rmse=sec,
            blocks_improved=b,years_improved=yy,months_improved=mm,worst_annual_relative_change=worst,
            historical_correction_rms=float(np.sqrt(np.mean([r['correction_rms']**2 for r in rows]))),
            passed=passes_gate(rmse,ref,sec,second,b,yy,mm,144,worst)))
    ranking.sort(key=lambda r:r['rmse']); eligible=[r for r in ranking if r['passed']]
    ablations=[]
    for newer,control in [('global15','local15'),('global31','global15'),('global31_dense','global31')]:
        a=np.array([next(r for r in old.read(OUT/f'{y}_direct.json') if r['model']==newer)['monthly_rmse'] for y in old.DEV])
        b=np.array([next(r for r in old.read(OUT/f'{y}_direct.json') if r['model']==control)['monthly_rmse'] for y in old.DEV])
        ablations.append(dict(model=newer,control=control,rmse=float(np.sqrt(np.mean(a*a))),
            control_rmse=float(np.sqrt(np.mean(b*b))),relative_gain=float(1-np.sqrt(np.mean(a*a)/np.mean(b*b))),
            blocks_improved=int(np.sum(np.mean(a*a,axis=1)<np.mean(b*b,axis=1)))))
    result=dict(reference='S12',reference_rmse=ref,minimum_relative_gain=.003,ranking=ranking,
        selected=eligible[0]['model'] if eligible else None,ablations=ablations,periods_reused=True,csv_exported=False,uploaded=False)
    path=OUT/'selection.json'
    if path.exists() and old.read(path)!=result: raise ValueError('Seleção mudou')
    old.save_json(path,result); print(json.dumps(result,indent=2),flush=True)


def selected():
    name=old.read(OUT/'selection.json')['selected']
    if name is None: raise ValueError('Nenhuma candidata aprovada: confirmação bloqueada')
    return name


def confirm():
    locked(); choice=selected(); path=OUT/'confirmation.json'
    if path.exists(): print(json.dumps(old.read(path),indent=2)); return
    name,a=CONFIGS[choice]; f=Features(2021); gt,gv=context(f); x,y=training(f,gt)
    pred=predict(f,name,fitted(f,name,x,y),gv); ref=reference(2021); value=ref+a*(pred-ref)
    truth=f.tp[target_origins(2021)+1].reshape(24,301,261)
    before,after=old.metrics(ref,truth,ref),old.metrics(value,truth,ref)
    result=dict(candidate=choice,reference=before,result=after,passed=confirmation_passes(before,after),
        previously_consumed_period=True,no_post_confirmation_tuning=True,csv_exported=False,uploaded=False)
    old.save_json(path,result); print(json.dumps(result,indent=2),flush=True)


def summarize():
    locked(); s=old.read(OUT/'selection.json')
    lines=['# Rodada 20 — árvores locais/globais, hipótese 1','',
        f"Referência S12: RMSE {s['reference_rmse']:.9f}. Somente dados oficiais.",'',
        '| Candidata | RMSE | Ganho | Blocos | Anos | Meses | Passou |',
        '| --- | ---: | ---: | ---: | ---: | ---: | --- |']
    for r in s['ranking']:
        lines.append(f"| {r['model']} | {r['rmse']:.9f} | {100*r['relative_gain']:.4f}% | {r['blocks_improved']}/6 | {r['years_improved']}/12 | {r['months_improved']}/144 | {r['passed']} |")
    lines += ['',f"Selecionada: {s['selected'] or 'nenhuma'}.",'','## Comparações controladas dos modelos individuais','',
        '| Mudança | Controle | RMSE novo | RMSE controle | Ganho | Blocos |',
        '| --- | --- | ---: | ---: | ---: | ---: |']
    for r in s['ablations']:
        lines.append(f"| {r['model']} | {r['control']} | {r['rmse']:.6f} | {r['control_rmse']:.6f} | {100*r['relative_gain']:.3f}% | {r['blocks_improved']}/6 |")
    lines += ['','Os resultados individuais explicam a hipótese; a promoção exige melhora da mistura contra S12.',
        'Critérios de 0,3% e estabilidade preservados. Períodos reutilizados, não teste independente.',
        'Nenhum CSV novo, previsão final ou upload foi autorizado por esta rodada.',
        '[Protocolo](../../../experiments/ROUND20.md) · [Seleção](selection.json) · [Auditoria](audit.json)']
    if (OUT/'confirmation.json').exists():
        c=old.read(OUT/'confirmation.json'); lines += ['',f"Confirmação reutilizada: {c['reference']['rmse']:.9f} → {c['result']['rmse']:.9f}; passou: {c['passed']}."]
    elif s['selected'] is None: lines+=['','Nenhuma candidata aprovada: confirmação e treino final não executados.']
    (OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


if __name__=='__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('stage',choices=('evaluate','select','confirm','summarize'))
    globals()[p.parse_args().stage]()
