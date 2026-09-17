"""Verifica previsões integrais e seleções das hipóteses 3 e 4."""
import json
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src import round22_23 as r
from src.round9 import digest,metrics,passes_gate
from src.round2 import target_origins


def verify_round(out, names, candidates):
    tp=np.load(r.old.CACHE/'tp.npy',mmap_mode='r')
    collected={name:[] for name in ('s12',)+tuple(f'{base}_a{a:g}' for base in names for a in r.FRACTIONS)}
    for year in r.old.DEV:
        rows=r.old.read(out/f'{year}.json')
        truth=tp[target_origins(year)+1]
        ref=r.prior.reference(year)
        byname={row['model']:row for row in rows}
        for name in names:
            kind='decomposed9' if name=='decomposed9' else 'direct'
            start='start1981' if name=='decomposed9' else name
            path=r.ART/f'{year}_{start}_{kind}.npy'
            assert digest(path)==r.old.read(path.with_suffix('.json'))['sha256']
            pred=np.load(path)
            for a in r.FRACTIONS:
                label=f'{name}_a{a:g}'
                actual=metrics(ref+a*(pred-ref),truth,ref)
                np.testing.assert_allclose(actual['monthly_rmse'],byname[label]['monthly_rmse'],rtol=0,atol=1e-9)
                for field in ('rmse','year1_rmse','year2_rmse','correction_rms'):
                    np.testing.assert_allclose(actual[field],byname[label][field],rtol=0,atol=1e-9)
                collected[label].extend(actual['monthly_rmse'])
        actual=metrics(ref,truth,ref)
        np.testing.assert_allclose(actual['monthly_rmse'],byname['s12']['monthly_rmse'],rtol=0,atol=1e-9)
        collected['s12'].extend(actual['monthly_rmse'])
    selected=r.old.read(out/'selection.json')
    refs=np.asarray(collected['s12']).reshape(6,24)
    ref=float(np.sqrt(np.mean(refs**2)))
    np.testing.assert_allclose(ref,selected['reference_rmse'],rtol=0,atol=1e-12)
    refyears=np.sqrt(np.mean(refs.reshape(-1,12)**2,axis=1))
    second=float(np.sqrt(np.mean(refs[:,12:]**2)))
    eligible=[]
    for name in candidates:
        vals=np.asarray(collected[name]).reshape(6,24)
        rmse=float(np.sqrt(np.mean(vals**2)))
        yrs=np.sqrt(np.mean(vals.reshape(-1,12)**2,axis=1))
        sec=float(np.sqrt(np.mean(vals[:,12:]**2)))
        blocks=int(np.sum(np.mean(vals**2,axis=1)<np.mean(refs**2,axis=1)))
        years=int(np.sum(yrs<refyears)); months=int(np.sum(vals<refs))
        worst=float(np.max(yrs/refyears-1))
        passed=passes_gate(rmse,ref,sec,second,blocks,years,months,144,worst)
        row=next(v for v in selected['ranking'] if v['model']==name)
        np.testing.assert_allclose(rmse,row['rmse'],rtol=0,atol=1e-12)
        assert (blocks,years,months,passed)==(row['blocks_improved'],row['years_improved'],row['months_improved'],row['passed'])
        if passed: eligible.append((rmse,name))
    eligible.sort()
    assert selected['selected']==(eligible[0][1] if eligible else None)


def main():
    r.locked()
    verify_round(r.OUT22,('start1981','start1960','start1940'),
        tuple(f'{name}_a{a:g}' for name in ('start1960','start1940') for a in r.FRACTIONS))
    verify_round(r.OUT23,('start1981','decomposed9'),
        tuple(f'decomposed9_a{a:g}' for a in r.FRACTIONS))
    result=dict(passed=True,full_grid=True,official_only=True,blocks=list(r.old.DEV),
        controls_recomputed=True,selections_recomputed=True,csv_exported=False,uploaded=False)
    for out in (r.OUT22,r.OUT23): r.old.save_json(out/'verification.json',result)
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=='__main__': main()
