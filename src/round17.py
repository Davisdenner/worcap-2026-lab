"""Corretor não linear causal dos componentes S11; quatro candidatas fixas."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
import argparse
import json
import sys
from functools import lru_cache
import joblib
import numpy as np
import xarray as xr
from sklearn.ensemble import HistGradientBoostingRegressor
from .competition import ROOT,RAW,CACHE,REPORT,VARIABLES,dates,fit_climatology,save_json
from .round2 import target_origins
from .round9 import read,digest,preceding,metrics,passes_gate
from .round11 import blend
from .round16 import reference,DEV,HISTORY

ART=ROOT/'data/processed/round17'
OUT=REPORT/'round17'
CONFIGS={f'meta{leaves}_a{weight:g}':(leaves,weight) for leaves in (7,15) for weight in (.25,.5)}
SEED=20260918
TREE=dict(loss='squared_error',learning_rate=.03,max_iter=200,min_samples_leaf=300,
          l2_regularization=100.,max_bins=128,early_stopping=False,random_state=SEED)
FEATURES=['latitude','longitude','sin_mes_alvo','cos_mes_alvo','climatologia','s11',
          'desvio_s02','desvio_modos','desvio_local18','desvio_pls16','desvio_tropical',
          'dispersao_componentes','amplitude_componentes','anomalia_s11']+VARIABLES


def locked():
    ART.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
    record=dict(protocol_sha256=digest(ROOT/'experiments/ROUND17.md'),source_sha256=digest(ROOT/'src/round17.py'),
        dependencies={p:digest(ROOT/'src'/p) for p in
            ('round16.py','diagnose_s11.py','competition.py','round2.py','round9.py','round11.py','round15.py')},
        configurations=CONFIGS,tree_parameters=TREE,features=FEATURES,samples_per_month=2048,
        reference='S11',official_only=True,minimum_relative_gain=.003)
    record=json.loads(json.dumps(record)); path=OUT/'protocol.json'
    if path.exists() and read(path)!=record: raise ValueError('Código ou protocolo congelado mudou')
    if not path.exists(): save_json(path,record)
    return record


def audit():
    expected=read(ROOT/'delivery/s11/evidence/official_sources.json')
    hashes={}
    for name in ['tp']+VARIABLES:
        path=RAW/f'treino_{name}.nc'
        if digest(path)!=expected[path.name]: raise ValueError('Fonte oficial alterada')
        cached=np.load(CACHE/f'{name}.npy',mmap_mode='r')
        with xr.open_dataset(path) as ds:
            for start in range(0,996,48):
                np.testing.assert_array_equal(cached[start:start+48],ds[name].isel(time=slice(start,start+48)).values)
        hashes[name]=digest(CACHE/f'{name}.npy')
    save_json(OUT/'audit.json',dict(passed=True,official_only=True,full_cache_equality=True,cache_hashes=hashes))


@lru_cache(maxsize=2)
def data(cutoff):
    pred=reference(cutoff)
    root=ROOT/'data/processed/round9'
    arrays=[np.load(root/f'{cutoff}_{name}.npy') for name in ('s02','modes','local18','pls16')]
    s09=np.load(ROOT/f'data/processed/round10/{cutoff}_s09.npy')
    trop=np.load(ROOT/f'data/processed/round11/{cutoff}_fine32.npy')
    pieces=np.stack(arrays+[blend(s09,trop,1.)]).reshape(5,24,-1)
    tp=np.load(CACHE/'tp.npy',mmap_mode='r')
    climo=fit_climatology(tp,dates(),f'{cutoff}-01-01',60).reshape(12,-1)
    fields=[np.load(CACHE/f'{v}.npy',mmap_mode='r').reshape(996,-1) for v in VARIABLES]
    extra=None
    if cutoff==2023:
        with xr.open_dataset(RAW/'teste_features.nc') as ds:
            np.testing.assert_array_equal(ds.time_origem.values.astype('datetime64[M]'),np.arange('2022-12','2024-12',dtype='datetime64[M]'))
            extra=[ds[v].values.reshape(24,-1) for v in VARIABLES]
            for j in range(9): np.testing.assert_array_equal(extra[j][0],fields[j][-1])
    return pred.reshape(24,-1),pieces,climo,fields,extra


def matrix(cutoff, month_index, cells):
    if cutoff not in HISTORY+(2023,) or not 0<=month_index<24:
        raise ValueError('Corte ou mês não disponível')
    pred,pieces,climo,fields,extra=data(cutoff)
    origin=int(target_origins(cutoff)[month_index]); month=month_index%12
    x=np.empty((len(cells),len(FEATURES)),np.float32)
    x[:,0]=-60+(cells//261)*.25; x[:,1]=-90+(cells%261)*.25
    angle=2*np.pi*month/12; x[:,2]=np.sin(angle); x[:,3]=np.cos(angle)
    x[:,4]=climo[month,cells]; x[:,5]=pred[month_index,cells]
    component=pieces[:,month_index,cells].T
    x[:,6:11]=component-x[:,5,None]
    x[:,11]=component.std(axis=1); x[:,12]=np.ptp(component,axis=1)
    x[:,13]=x[:,5]-x[:,4]
    for j in range(9): x[:,14+j]=(fields[j][origin,cells] if origin<996 else extra[j][origin-995,cells])
    if not np.isfinite(x).all(): raise ValueError('Atributos inválidos')
    return x


def samples(year):
    if year not in HISTORY: raise ValueError('Não há alvos de treino nesse corte')
    path=ART/f'{year}_samples.npz'
    if path.exists():
        meta=read(path.with_suffix('.json'))
        if digest(path)!=meta['sha256']: raise ValueError('Amostra alterada')
        with np.load(path) as z: return z['x'],z['y']
    tp=np.load(CACHE/'tp.npy',mmap_mode='r').reshape(996,-1)
    pred=reference(year).reshape(24,-1); rng=np.random.default_rng(SEED+year)
    x=[]; y=[]
    for m,origin in enumerate(target_origins(year)):
        cells=rng.choice(78561,2048,replace=False)
        x.append(matrix(year,m,cells)); y.append((tp[origin+1,cells]-pred[m,cells]).astype(np.float32))
    x,y=np.concatenate(x),np.concatenate(y)
    np.savez_compressed(path,x=x,y=y)
    save_json(path.with_suffix('.json'),dict(sha256=digest(path),block=year,
        base_training_targets_end=f'{year-1}-12',residual_targets_end=f'{year+1}-12',
        seed=SEED+year,samples_per_month=2048,features=FEATURES,official_only=True))
    return x,y


def fitted(cutoff, leaves):
    years=preceding(HISTORY,cutoff)
    if not years: raise ValueError('Sem blocos anteriores completos')
    path=ART/f'{cutoff}_meta{leaves}.joblib'
    if path.exists():
        meta=read(path.with_suffix('.json'))
        if meta['training_blocks']!=years or digest(path)!=meta['sha256']: raise ValueError('Modelo alterado')
        return joblib.load(path)
    items=[samples(y) for y in years]
    x=np.concatenate([a for a,b in items]); target=np.concatenate([b for a,b in items])
    model=HistGradientBoostingRegressor(max_leaf_nodes=leaves,**TREE).fit(x,target)
    joblib.dump(model,path)
    saved=joblib.load(path)
    np.testing.assert_array_equal(saved.predict(x[:2048]),model.predict(x[:2048]))
    save_json(path.with_suffix('.json'),dict(sha256=digest(path),cutoff=cutoff,leaves=leaves,
        training_blocks=years,last_training_target=f'{years[-1]+1}-12',samples=len(x),
        official_only=True,base='S11',features=FEATURES))
    return saved


def correction(cutoff, leaves):
    model=fitted(cutoff,leaves); pred=np.empty((24,301,261)); cells=np.arange(78561)
    for m in range(24): pred[m]=model.predict(matrix(cutoff,m,cells)).reshape(301,261)
    return pred


def evaluate():
    locked(); audit()
    tp=np.load(CACHE/'tp.npy',mmap_mode='r')
    for year in DEV:
        path=OUT/f'{year}.json'
        if path.exists(): print('BLOCO JÁ REGISTRADO',year,flush=True); continue
        ref=reference(year); truth=tp[target_origins(year)+1]
        rows=[dict(model='s11',**metrics(ref,truth,ref))]
        for leaves in (7,15):
            delta=correction(year,leaves)
            for fraction in (.25,.5):
                pred=np.maximum(ref+fraction*delta,0)
                rows.append(dict(model=f'meta{leaves}_a{fraction:g}',**metrics(pred,truth,ref)))
        save_json(path,rows)
        print('RESULTADOS',year,[(r['model'],round(r['rmse'],6)) for r in rows],flush=True)


def select():
    locked()
    records={y:read(OUT/f'{y}.json') for y in DEV}
    refs=np.asarray([records[y][0]['monthly_rmse'] for y in DEV])
    ref=float(np.sqrt(np.mean(refs**2))); second=float(np.sqrt(np.mean(refs[:,12:]**2)))
    refyears=np.sqrt(np.mean(refs.reshape(-1,12)**2,axis=1)); rows=[]
    for name in CONFIGS:
        rs=[next(r for r in records[y] if r['model']==name) for y in DEV]
        months=np.asarray([r['monthly_rmse'] for r in rs]); years=np.sqrt(np.mean(months.reshape(-1,12)**2,axis=1))
        pooled=float(np.sqrt(np.mean(months**2))); second_new=float(np.sqrt(np.mean(months[:,12:]**2)))
        b=int(np.sum(np.mean(months**2,axis=1)<np.mean(refs**2,axis=1)))
        yy=int(np.sum(years<refyears)); mm=int(np.sum(months<refs)); worst=float(np.max(years/refyears-1))
        rows.append(dict(model=name,rmse=pooled,relative_gain=1-pooled/ref,second_year_rmse=second_new,
            blocks_improved=b,years_improved=yy,months_improved=mm,worst_annual_relative_change=worst,
            historical_correction_rms=float(np.sqrt(np.mean([r['correction_rms']**2 for r in rs]))),
            passed=passes_gate(pooled,ref,second_new,second,b,yy,mm,144,worst)))
    rows.sort(key=lambda r:r['rmse']); eligible=[r for r in rows if r['passed']]
    result=dict(reference='S11',reference_rmse=ref,minimum_relative_gain=.003,ranking=rows,
                selected=eligible[0]['model'] if eligible else None,periods_reused=True)
    path=OUT/'selection.json'
    if path.exists() and read(path)!=result: raise ValueError('Seleção mudou')
    save_json(path,result); print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)


def selected():
    name=read(OUT/'selection.json')['selected']
    if name is None: raise ValueError('Nenhuma candidata aprovada: etapa bloqueada')
    return name


def confirm():
    locked(); name=selected(); path=OUT/'confirmation.json'
    if path.exists(): print(json.dumps(read(path),ensure_ascii=False)); return
    leaves,fraction=CONFIGS[name]; ref=reference(2021)
    pred=np.maximum(ref+fraction*correction(2021,leaves),0)
    truth=np.load(CACHE/'tp.npy',mmap_mode='r')[target_origins(2021)+1]
    before,after=metrics(ref,truth,ref),metrics(pred,truth,ref)
    passed=after['rmse']<=before['rmse']*.999 and all(after[k]<before[k] for k in ('year1_rmse','year2_rmse'))
    result=dict(candidate=name,reference=before,result=after,passed=passed,previously_consumed_period=True)
    save_json(path,result); print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)


def prepare_final():
    locked(); name=selected(); check=read(OUT/'confirmation.json')
    if not check['passed'] or check['candidate']!=name: raise ValueError('Confirmação reprovada')
    leaves,fraction=CONFIGS[name]; ref=reference(2023)
    pred=np.maximum(ref+fraction*correction(2023,leaves),0)
    record=next(r for r in read(OUT/'selection.json')['ranking'] if r['model']==name)
    hist=record['historical_correction_rms']
    rms=[float(np.sqrt(np.mean((pred[s]-ref[s])**2))) for s in (slice(0,12),slice(12,24))]
    passed=all(v<=2*hist for v in rms)
    save_json(OUT/'test_shift.json',dict(candidate=name,historical_rms=hist,
        public2023_rms=rms[0],private2024_rms=rms[1],passed=passed))
    if not passed: raise ValueError('Mudança no teste excede limite')
    path=ART/'candidate_predictions.npy'
    if path.exists(): np.testing.assert_array_equal(pred,np.load(path))
    else: np.save(path,pred)
    save_json(OUT/'ready.json',dict(candidate=name,sha256=digest(path),official_only=True,
        csv_exported=False,uploaded=False,explicit_export_request_required=True))
    print('PREVISÃO INTERNA PRONTA, SEM EXPORTAÇÃO CSV',flush=True)


def summarize():
    locked(); selection=read(OUT/'selection.json')
    lines=['# Rodada 17 — correção não linear condicionada à S11','',
        f"Referência histórica S11: {selection['reference_rmse']:.6f}. Somente dados oficiais.",
        'Ganho mínimo 0,3%, junto com todos os critérios de estabilidade.','',
        '| Candidata | RMSE | Ganho | Blocos | Anos | Meses | Aprovada |',
        '| --- | ---: | ---: | ---: | ---: | ---: | --- |']
    for r in selection['ranking']:
        lines.append(f"| {r['model']} | {r['rmse']:.6f} | {100*r['relative_gain']:.3f}% | {r['blocks_improved']}/6 | {r['years_improved']}/12 | {r['months_improved']}/144 | {r['passed']} |")
    lines += ['',f"Selecionada: {selection['selected'] or 'nenhuma'}.",
        'Corretores aprendidos apenas de resíduos fora do treino de blocos anteriores completos.',
        'Diagnóstico, arquitetura e períodos reutilizados; não é teste independente.',
        'Nenhum CSV novo ou upload foi realizado.',
        '', '[Protocolo](../../../experiments/ROUND17.md) · [Seleção](selection.json) · [Diagnóstico](../s11_diagnostic/RESULTS.md)']
    if (OUT/'confirmation.json').exists():
        c=read(OUT/'confirmation.json')
        lines += ['',f"Confirmação reutilizada: {c['reference']['rmse']:.6f} → {c['result']['rmse']:.6f}; aprovada: {c['passed']}."]
    elif selection['selected'] is None:
        lines += ['','Nenhuma candidata passou; confirmação e preparação final não foram executadas.']
    (OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines),flush=True)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('evaluate','select','confirm','prepare_final','summarize'))
    globals()[parser.parse_args().stage]()
