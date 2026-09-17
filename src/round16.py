"""Calibração causal espacial/sazonal da S11; oito candidatas e critérios fixos."""
import os
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import json
import sys
from functools import lru_cache
import numpy as np
from scipy.ndimage import gaussian_filter
from .competition import ROOT, CACHE, REPORT, save_json
from .round2 import target_origins
from .round9 import digest, read, metrics, passes_gate, preceding
from .round11 import blend
from .round15 import combine, solve_weights
from .diagnose_s11 import verified_prediction, audit_rain

ART = ROOT / 'data/processed/round16'
OUT = REPORT / 'round16'
DEV = (2009,2011,2013,2015,2017,2019)
HISTORY = (2005,2007) + DEV + (2021,)
CONFIGS = {f'{kind}_s{sigma}_a{weight:g}':(kind,sigma,weight)
           for kind in ('anual','sazonal') for sigma in (4,12) for weight in (.5,1.)}


def locked():
    ART.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
    result = dict(protocol_sha256=digest(ROOT/'experiments/ROUND16.md'),
        source_sha256=digest(ROOT/'src/round16.py'),
        dependencies={p:digest(ROOT/'src'/p) for p in
            ('diagnose_s11.py','competition.py','round2.py','round9.py','round11.py','round15.py')},
        configurations=CONFIGS, reference='S11 joint1', official_only=True,
        minimum_relative_gain=.003, frozen_before_candidate_scores=True)
    result=json.loads(json.dumps(result))
    path=OUT/'protocol.json'
    if path.exists() and read(path)!=result:
        raise ValueError('Código ou protocolo congelado mudou')
    if not path.exists(): save_json(path,result)
    return result


@lru_cache(maxsize=10)
def reference(cutoff):
    if cutoff not in (2005,2007):
        return verified_prediction(cutoff)
    # Aquecimento causal, sem ajustar pesos aos alvos do próprio bloco.
    parent=ROOT/'data/processed/round15'
    record=read(parent/f'{cutoff}_components.json')
    for filename,h in record['component_sources'].items():
        if digest(ROOT/filename)!=h: raise ValueError('Componente histórico alterado')
    prior=np.asarray(record['prior'])
    years=preceding(HISTORY,cutoff)
    weights=prior.copy()
    if years:
        cov=[]
        for year in years:
            path=parent/f'{year}_covariance.npy'
            if digest(path)!=read(path.with_suffix('.json'))['sha256']:
                raise ValueError('Covariância histórica alterada')
            cov.append(np.load(path))
        mean=np.mean(cov,axis=0)
        weights=np.stack([solve_weights(mean[g],prior[g],1.) for g in range(12)])
    root=ROOT/'data/processed/round9'
    pieces=[np.load(root/f'{cutoff}_{name}.npy') for name in ('s02','modes','local18','pls16')]
    s09=np.load(ROOT/f'data/processed/round10/{cutoff}_s09.npy')
    trop=np.load(ROOT/f'data/processed/round11/{cutoff}_fine32.npy')
    return combine(np.stack(pieces+[blend(s09,trop,1.)]).astype(float),weights)


def seasonal_mean(residuals, kind):
    """Médias usam apenas resíduos históricos fornecidos, em meses Jan..Dez."""
    if residuals.ndim!=3 or len(residuals)%12:
        raise ValueError('São necessários anos históricos completos')
    if kind=='anual':
        return np.repeat(residuals.mean(axis=0)[None],12,axis=0)
    if kind!='sazonal': raise ValueError('Estimador desconhecido')
    months=np.arange(len(residuals))%12
    return np.stack([residuals[np.minimum((months-m)%12,(m-months)%12)<=2].mean(axis=0)
                     for m in range(12)])


def fitted(cutoff, kind, sigma):
    years=preceding(HISTORY,cutoff)
    if not years: raise ValueError('Não há blocos completos anteriores')
    tp=np.load(CACHE/'tp.npy',mmap_mode='r')
    residuals=np.concatenate([tp[target_origins(y)+1].astype(float)-reference(y) for y in years])
    fields=seasonal_mean(residuals,kind)
    fields=gaussian_filter(fields,sigma=(0,sigma,sigma),mode='nearest')
    metadata=dict(cutoff=cutoff,kind=kind,sigma_cells=sigma,training_blocks=years,
                  last_training_target=f'{years[-1]+1}-12',training_months=len(residuals),
                  reference='S11 with causal seed warmup',official_only=True)
    path=ART/f'{cutoff}_{kind}_s{sigma}.npy'
    if path.exists(): np.testing.assert_array_equal(fields,np.load(path))
    else:
        np.save(path,fields)
        save_json(path.with_suffix('.json'),dict(**metadata,sha256=digest(path)))
    return fields


def apply(ref, correction, fraction):
    if correction.shape!=(12,)+ref.shape[1:] or len(ref)!=24:
        raise ValueError('Grade ou calendário incorretos')
    pred=np.maximum(ref+fraction*correction[np.arange(24)%12],0)
    if not np.isfinite(pred).all(): raise ValueError('Previsão não finita')
    return pred


def evaluate():
    locked(); save_json(OUT/'audit.json',audit_rain())
    tp=np.load(CACHE/'tp.npy',mmap_mode='r')
    for cutoff in DEV:
        path=OUT/f'{cutoff}.json'
        if path.exists():
            print('BLOCO JÁ REGISTRADO',cutoff,flush=True); continue
        ref=reference(cutoff); truth=tp[target_origins(cutoff)+1]
        rows=[dict(model='s11',**metrics(ref,truth,ref))]
        fields={}
        for name,(kind,sigma,weight) in CONFIGS.items():
            if (kind,sigma) not in fields: fields[kind,sigma]=fitted(cutoff,kind,sigma)
            pred=apply(ref,fields[kind,sigma],weight)
            rows.append(dict(model=name,**metrics(pred,truth,ref)))
        save_json(path,rows)
        print('RESULTADOS',cutoff,[(r['model'],round(r['rmse'],6)) for r in rows],flush=True)


def rank(records):
    refs=np.array([records[y][0]['monthly_rmse'] for y in DEV])
    ref=float(np.sqrt(np.mean(refs**2))); second=float(np.sqrt(np.mean(refs[:,12:]**2)))
    refyears=np.sqrt(np.mean(refs.reshape(-1,12)**2,axis=1)); ranking=[]
    for name in CONFIGS:
        rows=[next(r for r in records[y] if r['model']==name) for y in DEV]
        months=np.asarray([r['monthly_rmse'] for r in rows])
        years=np.sqrt(np.mean(months.reshape(-1,12)**2,axis=1))
        pooled=float(np.sqrt(np.mean(months**2))); second_new=float(np.sqrt(np.mean(months[:,12:]**2)))
        blocks=int(np.sum(np.mean(months**2,axis=1)<np.mean(refs**2,axis=1)))
        improved_years=int(np.sum(years<refyears)); improved_months=int(np.sum(months<refs))
        worst=float(np.max(years/refyears-1))
        ranking.append(dict(model=name,rmse=pooled,relative_gain=1-pooled/ref,
            second_year_rmse=second_new,blocks_improved=blocks,years_improved=improved_years,
            months_improved=improved_months,worst_annual_relative_change=worst,
            historical_correction_rms=float(np.sqrt(np.mean([r['correction_rms']**2 for r in rows]))),
            passed=passes_gate(pooled,ref,second_new,second,blocks,improved_years,improved_months,144,worst)))
    ranking.sort(key=lambda r:r['rmse']); eligible=[r for r in ranking if r['passed']]
    return dict(reference='S11',reference_rmse=ref,minimum_relative_gain=.003,
                selected=eligible[0]['model'] if eligible else None,ranking=ranking,
                periods_reused=True,confirmation_previously_consumed=True)


def select():
    locked(); result=rank({y:read(OUT/f'{y}.json') for y in DEV})
    path=OUT/'selection.json'
    if path.exists() and read(path)!=result: raise ValueError('Seleção congelada mudou')
    save_json(path,result); print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)


def selected():
    name=read(OUT/'selection.json')['selected']
    if name is None: raise ValueError('Nenhuma candidata aprovada: etapa bloqueada')
    return name


def confirm():
    locked(); name=selected()
    path=OUT/'confirmation.json'
    if path.exists(): print(json.dumps(read(path),ensure_ascii=False)); return
    kind,sigma,weight=CONFIGS[name]; ref=reference(2021)
    pred=apply(ref,fitted(2021,kind,sigma),weight)
    truth=np.load(CACHE/'tp.npy',mmap_mode='r')[target_origins(2021)+1]
    before,after=metrics(ref,truth,ref),metrics(pred,truth,ref)
    passed=after['rmse']<=before['rmse']*.999 and all(after[k]<before[k] for k in ('year1_rmse','year2_rmse'))
    result=dict(candidate=name,reference=before,result=after,passed=passed,
                previously_consumed_period=True,no_post_confirmation_tuning=True)
    save_json(path,result); print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)


def prepare_final():
    locked(); name=selected(); check=read(OUT/'confirmation.json')
    if not check['passed'] or check['candidate']!=name: raise ValueError('Confirmação reprovada')
    kind,sigma,weight=CONFIGS[name]; ref=reference(2023)
    pred=apply(ref,fitted(2023,kind,sigma),weight)
    chosen=next(r for r in read(OUT/'selection.json')['ranking'] if r['model']==name)
    hist=chosen['historical_correction_rms']
    rms=[float(np.sqrt(np.mean((pred[s]-ref[s])**2))) for s in (slice(0,12),slice(12,24))]
    passed=all(v<=2*hist for v in rms)
    save_json(OUT/'test_shift.json',dict(candidate=name,historical_rms=hist,
        public2023_rms=rms[0],private2024_rms=rms[1],passed=passed))
    if not passed: raise ValueError('Mudança no teste excede o limite')
    path=ART/'candidate_predictions.npy'
    if path.exists(): np.testing.assert_array_equal(pred,np.load(path))
    else: np.save(path,pred)
    save_json(OUT/'ready.json',dict(candidate=name,sha256=digest(path),
        official_only=True,csv_exported=False,uploaded=False,explicit_export_request_required=True))
    print('CANDIDATA INTERNA VERIFICADA; SEM EXPORTAÇÃO CSV',flush=True)


def summarize():
    locked(); selection=read(OUT/'selection.json')
    lines=['# Rodada 16 — correção espacial/sazonal S11','',
        f"Referência histórica S11: {selection['reference_rmse']:.6f}. Somente dados oficiais.",
        'Ganho mínimo relativo: 0,3%, com todos os demais critérios de estabilidade.','',
        '| Candidata | RMSE | Ganho | Blocos | Anos | Meses | Aprovada |',
        '| --- | ---: | ---: | ---: | ---: | ---: | --- |']
    for r in selection['ranking']:
        lines.append(f"| {r['model']} | {r['rmse']:.6f} | {100*r['relative_gain']:.3f}% | {r['blocks_improved']}/6 | {r['years_improved']}/12 | {r['months_improved']}/144 | {r['passed']} |")
    lines += ['',f"Selecionada: {selection['selected'] or 'nenhuma'}.",
        'Correções aprendidas somente em blocos anteriores completos; 2005/2007 têm aquecimento causal descrito no protocolo.',
        'Os períodos e a arquitetura foram reutilizados; não se trata de teste independente.',
        'Nenhuma nova submissão CSV ou upload foi feito por este programa.',
        '', '[Protocolo](../../../experiments/ROUND16.md) · [Seleção](selection.json) · [Diagnóstico](../s11_diagnostic/RESULTS.md)']
    if (OUT/'confirmation.json').exists():
        c=read(OUT/'confirmation.json')
        lines += ['',f"Confirmação reutilizada: {c['reference']['rmse']:.6f} → {c['result']['rmse']:.6f}; aprovada: {c['passed']}."]
    elif selection['selected'] is None:
        lines += ['','Nenhuma candidata passou; confirmação e preparação final não foram executadas.']
    (OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines),flush=True)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=('evaluate','select','confirm','prepare_final','summarize'))
    globals()[p.parse_args().stage]()
