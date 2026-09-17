"""Recalcular métricas de toda a grade e gates a partir dos arrays preservados."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'): os.environ[key]='1'
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from src import round20 as r


def load(path):
    if r.old.digest(path)!=r.old.read(path.with_suffix('.json'))['sha256']: raise ValueError('Array alterado')
    value=np.load(path)
    if value.shape!=(24,301,261) or not np.isfinite(value).all() or (value<0).any(): raise ValueError('Previsão inválida')
    return value


def monthly(pred,truth):
    return np.sqrt(np.mean((pred.astype(np.float64)-truth.astype(np.float64))**2,axis=(1,2)))


def main():
    r.locked(); selection=r.old.read(r.OUT/'selection.json')
    tp=np.load(r.old.CACHE/'tp.npy',mmap_mode='r')
    reference=[]; candidates={name:[] for name in r.CONFIGS}
    for year in r.old.DEV:
        ref=load(r.ART/f'{year}_s12.npy'); truth=tp[r.target_origins(year)+1]
        rows=r.old.read(r.OUT/f'{year}.json'); direct_rows=r.old.read(r.OUT/f'{year}_direct.json')
        rm=monthly(ref,truth); reference.append(rm)
        np.testing.assert_allclose(rm,rows[0]['monthly_rmse'],rtol=0,atol=1e-12)
        for name in r.MODELS:
            pred=load(r.ART/f'{year}_{name}_prediction.npy')
            np.testing.assert_allclose(monthly(pred,truth),next(row['monthly_rmse'] for row in direct_rows if row['model']==name),rtol=0,atol=1e-12)
            for fraction in r.FRACTIONS:
                candidate=f'{name}_a{fraction:g}'; values=monthly(ref+fraction*(pred-ref),truth)
                candidates[candidate].append(values)
                np.testing.assert_allclose(values,next(row['monthly_rmse'] for row in rows if row['model']==candidate),rtol=0,atol=1e-12)
    refs=np.asarray(reference); base=float(np.sqrt(np.mean(refs**2))); second=float(np.sqrt(np.mean(refs[:,12:]**2)))
    ref_years=np.sqrt(np.mean(refs.reshape(12,12)**2,axis=1)); eligible=[]
    for name,values in candidates.items():
        values=np.asarray(values); pooled=float(np.sqrt(np.mean(values**2)))
        sec=float(np.sqrt(np.mean(values[:,12:]**2))); years=np.sqrt(np.mean(values.reshape(12,12)**2,axis=1))
        blocks=int(np.sum(np.mean(values**2,axis=1)<np.mean(refs**2,axis=1)))
        ny=int(np.sum(years<ref_years)); nm=int(np.sum(values<refs)); worst=float(np.max(years/ref_years-1))
        passed=r.passes_gate(pooled,base,sec,second,blocks,ny,nm,144,worst)
        saved=next(row for row in selection['ranking'] if row['model']==name)
        np.testing.assert_allclose([pooled,sec,1-pooled/base,worst],
            [saved['rmse'],saved['second_year_rmse'],saved['relative_gain'],saved['worst_annual_relative_change']],rtol=0,atol=1e-12)
        if (blocks,ny,nm,passed)!=(saved['blocks_improved'],saved['years_improved'],saved['months_improved'],saved['passed']): raise ValueError('Critérios divergentes')
        if passed: eligible.append((pooled,name))
    expected=min(eligible)[1] if eligible else None
    if expected!=selection['selected']: raise ValueError('Selecionada incorreta')
    r.old.save_json(r.OUT/'verification.json',dict(passed=True,full_grid_metrics_recomputed=True,
        development_months=144,grid_points=78561,candidates=8,all_candidate_gates_recomputed=True,
        selected=expected,protected_submissions_unchanged=True,verifier_sha256=r.old.digest(Path(__file__)),
        csv_exported=False,uploaded=False))
    print('PASS: métricas completas, oito candidatas, critérios e originais preservados',flush=True)


if __name__=='__main__': main()
