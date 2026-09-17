"""Memória longa causal no PLS tropical S11; quatro candidatas congeladas."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
import argparse
import json
import sys
import joblib
import numpy as np
from .competition import ROOT,CACHE,REPORT,dates,training_pairs,fit_climatology,save_json
from .round2 import target_origins
from .round3 import seasonal_design
from .round4 import groups
from .round9 import read,digest,metrics,passes_gate
from .round11 import fit_pls,anomaly_prediction
from .round16 import DEV,reference

ART=ROOT/'data/processed/round18'
OUT=REPORT/'round18'
CONFIGS={f'long{window}_a{a:g}':(window,a) for window in (6,12) for a in (.5,1.)}


def locked():
    ART.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
    obj=dict(protocol_sha256=digest(ROOT/'experiments/ROUND18.md'),source_sha256=digest(ROOT/'src/round18.py'),
        dependencies={p:digest(ROOT/'src'/p) for p in
            ('round16.py','diagnose_s11.py','competition.py','round2.py','round3.py','round4.py','round9.py','round11.py','round15.py')},
        configurations=CONFIGS,reference='S11',official_only=True,minimum_relative_gain=.003)
    obj=json.loads(json.dumps(obj)); path=OUT/'protocol.json'
    if path.exists() and read(path)!=obj: raise ValueError('Código ou protocolo congelado mudou')
    if not path.exists(): save_json(path,obj)
    return obj


def audit():
    coarse=ROOT/'data/processed/round3/coarse_weather.npy'
    fine=ROOT/'data/processed/round11/fine_weather.npy'
    expected1=read(REPORT/'round9/audit.json')['coarse_sha256']
    expected2=read(REPORT/'round11/audit.json')['fine_sha256']
    if digest(coarse)!=expected1 or digest(fine)!=expected2:
        raise ValueError('Cache espacial oficial alterado')
    save_json(OUT/'audit.json',dict(passed=True,coarse_sha256=expected1,fine_sha256=expected2,official_only=True))


def long_memory(z,origins,window):
    origins=np.asarray(origins)
    if window not in (6,12) or origins.min()<window-1 or origins.max()>=len(z):
        raise ValueError('Histórico causal indisponível')
    return np.column_stack([z[origins],sum(z[origins-k] for k in range(3))/3,
                            sum(z[origins-k] for k in range(window))/window])


def design(raw,prep,origins,window):
    take=np.arange(np.max(origins)+1)
    z=prep['pca'].transform((raw[take]-prep['means'][take%12])/prep['scale'])/prep['pc_scale']
    return seasonal_design(long_memory(z,origins,window),origins)[:,1:]


def tropical(cutoff,windows):
    idx=training_pairs(dates(),f'{cutoff}-01-01'); origins=target_origins(cutoff)
    if idx.max()+1>=(cutoff-1940)*12: raise ValueError('Alvo fora do treino')
    coarse=np.load(ROOT/'data/processed/round3/coarse_weather.npy',mmap_mode='r')
    fine=np.load(ROOT/'data/processed/round11/fine_weather.npy',mmap_mode='r')
    cpath=ROOT/f'data/processed/round9/{cutoff}_pls16.joblib'
    rpath=ROOT/f'data/processed/round11/{cutoff}_fine_weather.joblib'
    continental=joblib.load(cpath); regional=joblib.load(rpath)
    if continental['training_cutoff']!=f'{cutoff}-01' or not continental['official_only']:
        raise ValueError('Transformação com corte incorreto')
    tp=np.load(CACHE/'tp.npy',mmap_mode='r')[:,180:].reshape(996,-1)
    climo=fit_climatology(tp,dates(),f'{cutoff}-01-01',60)
    y=tp[idx+1]-climo[(idx+1)%12]; predictions={}
    for window in windows:
        x=np.column_stack([design(coarse,continental,idx,window),design(fine,regional,idx,window)])
        xv=np.column_stack([design(coarse,continental,origins,window),design(fine,regional,origins,window)])
        path=ART/f'{cutoff}_long{window}.joblib'
        provenance=dict(cutoff=cutoff,window=window,training_pairs=len(idx),
            last_training_target=f'{cutoff-1}-12',official_only=True,
            continental_sha256=digest(cpath),tropical_weather_sha256=digest(rpath))
        if path.exists():
            meta=read(path.with_suffix('.json'))
            if meta['provenance']!=provenance or meta['sha256']!=digest(path):
                raise ValueError('Modelo alterado')
        else:
            model=fit_pls(x,y,32)
            model.update(climatology=climo,**provenance)
            joblib.dump(model,path)
            np.testing.assert_array_equal(anomaly_prediction(model,xv),anomaly_prediction(joblib.load(path),xv))
            save_json(path.with_suffix('.json'),dict(provenance=provenance,sha256=digest(path)))
        model=joblib.load(path)
        predictions[window]=np.maximum(model['climatology'][(origins+1)%12]+anomaly_prediction(model,xv),0).reshape(24,121,261)
    return predictions


def replace_tropical(ref,original,new,weights,fraction):
    if ref.shape!=(24,301,261) or original.shape!=(24,121,261) or new.shape!=original.shape:
        raise ValueError('Forma inválida')
    if weights.shape!=(12,5) or not 0<=fraction<=1: raise ValueError('Pesos inválidos')
    taper=np.clip((np.arange(-15,15.01,.25)+15)/5,0,1)[None,:,None]
    factor=weights[groups(),4][:,180:]*taper*fraction
    result=ref.copy(); result[:,180:]=np.maximum(ref[:,180:]+factor*(new-original),0)
    if not np.isfinite(result).all(): raise ValueError('Previsão não finita')
    return result


def candidate(cutoff,window,fraction,new=None):
    ref=reference(cutoff)
    original=np.load(ROOT/f'data/processed/round11/{cutoff}_fine32.npy')
    weights=np.asarray(read(ROOT/f'data/processed/round15/{cutoff}_joint1_weights.json')['weights'])
    if new is None: new=tropical(cutoff,(window,))[window]
    return replace_tropical(ref,original,new,weights,fraction)


def evaluate():
    locked(); audit(); tp=np.load(CACHE/'tp.npy',mmap_mode='r')
    for year in DEV:
        path=OUT/f'{year}.json'
        if path.exists(): print('BLOCO JÁ REGISTRADO',year,flush=True); continue
        ref=reference(year); truth=tp[target_origins(year)+1]
        rows=[dict(model='s11',**metrics(ref,truth,ref))]
        predictions=tropical(year,(6,12))
        for name,(window,fraction) in CONFIGS.items():
            pred=candidate(year,window,fraction,predictions[window])
            rows.append(dict(model=name,**metrics(pred,truth,ref)))
        save_json(path,rows)
        print('RESULTADOS',year,[(r['model'],round(r['rmse'],6)) for r in rows],flush=True)


def select():
    locked(); records={y:read(OUT/f'{y}.json') for y in DEV}
    refs=np.asarray([records[y][0]['monthly_rmse'] for y in DEV])
    ref=float(np.sqrt(np.mean(refs**2))); second=float(np.sqrt(np.mean(refs[:,12:]**2)))
    refyears=np.sqrt(np.mean(refs.reshape(-1,12)**2,axis=1)); ranking=[]
    for name in CONFIGS:
        rows=[next(r for r in records[y] if r['model']==name) for y in DEV]
        months=np.asarray([r['monthly_rmse'] for r in rows]); years=np.sqrt(np.mean(months.reshape(-1,12)**2,axis=1))
        pooled=float(np.sqrt(np.mean(months**2))); second_new=float(np.sqrt(np.mean(months[:,12:]**2)))
        b=int(np.sum(np.mean(months**2,axis=1)<np.mean(refs**2,axis=1)))
        yy=int(np.sum(years<refyears)); mm=int(np.sum(months<refs)); worst=float(np.max(years/refyears-1))
        ranking.append(dict(model=name,rmse=pooled,relative_gain=1-pooled/ref,second_year_rmse=second_new,
            blocks_improved=b,years_improved=yy,months_improved=mm,worst_annual_relative_change=worst,
            historical_correction_rms=float(np.sqrt(np.mean([r['correction_rms']**2 for r in rows]))),
            passed=passes_gate(pooled,ref,second_new,second,b,yy,mm,144,worst)))
    ranking.sort(key=lambda r:r['rmse']); eligible=[r for r in ranking if r['passed']]
    result=dict(reference='S11',reference_rmse=ref,minimum_relative_gain=.003,
        ranking=ranking,selected=eligible[0]['model'] if eligible else None,periods_reused=True)
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
    window,fraction=CONFIGS[name]; ref=reference(2021); pred=candidate(2021,window,fraction)
    truth=np.load(CACHE/'tp.npy',mmap_mode='r')[target_origins(2021)+1]
    before,after=metrics(ref,truth,ref),metrics(pred,truth,ref)
    passed=after['rmse']<=before['rmse']*.999 and all(after[k]<before[k] for k in ('year1_rmse','year2_rmse'))
    obj=dict(candidate=name,reference=before,result=after,passed=passed,previously_consumed_period=True)
    save_json(path,obj); print(json.dumps(obj,ensure_ascii=False,indent=2),flush=True)


def prepare_final():
    locked(); name=selected(); check=read(OUT/'confirmation.json')
    if not check['passed'] or check['candidate']!=name: raise ValueError('Confirmação reprovada')
    ref=reference(2023); window,fraction=CONFIGS[name]; pred=candidate(2023,window,fraction)
    hist=next(r['historical_correction_rms'] for r in read(OUT/'selection.json')['ranking'] if r['model']==name)
    rms=[float(np.sqrt(np.mean((pred[s]-ref[s])**2))) for s in (slice(0,12),slice(12,24))]
    passed=all(v<=2*hist for v in rms)
    save_json(OUT/'test_shift.json',dict(candidate=name,historical_rms=hist,public2023_rms=rms[0],private2024_rms=rms[1],passed=passed))
    if not passed: raise ValueError('Mudança no teste excede limite')
    path=ART/'candidate_predictions.npy'
    if path.exists(): np.testing.assert_array_equal(pred,np.load(path))
    else: np.save(path,pred)
    save_json(OUT/'ready.json',dict(candidate=name,sha256=digest(path),official_only=True,
        csv_exported=False,uploaded=False,explicit_export_request_required=True))
    print('PREVISÃO INTERNA PRONTA, SEM EXPORTAÇÃO CSV',flush=True)


def summarize():
    locked(); s=read(OUT/'selection.json')
    lines=['# Rodada 18 — memória longa no PLS tropical S11','',
        f"Referência histórica S11: {s['reference_rmse']:.6f}. Somente dados oficiais.",
        'Ganho mínimo 0,3% e todos os critérios de estabilidade.','',
        '| Candidata | RMSE | Ganho | Blocos | Anos | Meses | Aprovada |',
        '| --- | ---: | ---: | ---: | ---: | ---: | --- |']
    for r in s['ranking']:
        lines.append(f"| {r['model']} | {r['rmse']:.6f} | {100*r['relative_gain']:.3f}% | {r['blocks_improved']}/6 | {r['years_improved']}/12 | {r['months_improved']}/144 | {r['passed']} |")
    lines += ['',f"Selecionada: {s['selected'] or 'nenhuma'}.",
        'Memória causal de 6/12 meses adicionada ao estado atual e à média de 3 meses.',
        'Arquitetura, diagnóstico e períodos reutilizados; não é teste independente.',
        'Nenhum CSV novo ou upload.',
        '', '[Protocolo](../../../experiments/ROUND18.md) · [Seleção](selection.json) · [Diagnóstico](../s11_diagnostic/RESULTS.md)']
    if (OUT/'confirmation.json').exists():
        c=read(OUT/'confirmation.json'); lines += ['',f"Confirmação reutilizada: {c['reference']['rmse']:.6f} → {c['result']['rmse']:.6f}; aprovada: {c['passed']}."]
    elif s['selected'] is None:
        lines += ['','Nenhuma candidata passou; confirmação e preparação final não executadas.']
    (OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines),flush=True)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('evaluate','select','confirm','prepare_final','summarize'))
    globals()[parser.parse_args().stage]()
