"""Recalcula, em grade integral, métricas e seleção da rodada 21."""
import json
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src import round21 as r
from src.round2 import target_origins
from src.round9 import digest, metrics, passes_gate


def main():
    r.locked()
    tp = np.load(r.old.CACHE/'tp.npy',mmap_mode='r')
    monthly = {name:[] for name in ('s12',)+tuple(r.CONFIGS)}
    for year in r.old.DEV:
        rows = r.old.read(r.OUT/f'{year}.json')
        truth = tp[target_origins(year)+1]
        reference = r.prior.reference(year)
        for row in rows:
            name = row['model']
            if name == 's12': pred = reference
            else:
                path = r.ART/f'{year}_{name}.npy'
                assert digest(path) == r.old.read(path.with_suffix('.json'))['sha256']
                pred = np.load(path)
            actual = metrics(pred,truth,reference)
            for field in ('rmse','year1_rmse','year2_rmse','correction_rms'):
                np.testing.assert_allclose(actual[field],row[field],rtol=0,atol=1e-9)
            np.testing.assert_allclose(actual['monthly_rmse'],row['monthly_rmse'],rtol=0,atol=1e-9)
            monthly[name].extend(actual['monthly_rmse'])
    selected = r.old.read(r.OUT/'selection.json')
    refs = np.asarray(monthly['s12']).reshape(6,24)
    reference_rmse = float(np.sqrt(np.mean(refs**2)))
    np.testing.assert_allclose(reference_rmse,selected['reference_rmse'],rtol=0,atol=1e-12)
    expected = []
    for name in r.CONFIGS:
        vals = np.asarray(monthly[name]).reshape(6,24)
        years = np.sqrt(np.mean(vals.reshape(-1,12)**2,axis=1))
        refyears = np.sqrt(np.mean(refs.reshape(-1,12)**2,axis=1))
        rmse = float(np.sqrt(np.mean(vals**2)))
        second = float(np.sqrt(np.mean(vals[:,12:]**2)))
        blocks = int(np.sum(np.mean(vals**2,axis=1)<np.mean(refs**2,axis=1)))
        nyears = int(np.sum(years<refyears)); nmonths = int(np.sum(vals<refs))
        worst = float(np.max(years/refyears-1))
        passed = passes_gate(rmse,reference_rmse,second,float(np.sqrt(np.mean(refs[:,12:]**2))),
                             blocks,nyears,nmonths,144,worst)
        row = next(v for v in selected['ranking'] if v['model']==name)
        for key,value in [('rmse',rmse),('second_year_rmse',second),
                          ('relative_gain',1-rmse/reference_rmse),
                          ('worst_annual_relative_change',worst)]:
            np.testing.assert_allclose(row[key],value,rtol=0,atol=1e-12)
        assert (row['blocks_improved'],row['years_improved'],row['months_improved'],row['passed']) == (
            blocks,nyears,nmonths,passed)
        if passed: expected.append((rmse,name))
    expected.sort()
    assert selected['selected'] == (expected[0][1] if expected else None)
    result = dict(passed=True,full_grid=True,official_only=True,blocks=list(r.old.DEV),
                  selection_recomputed=True,csv_exported=False,uploaded=False)
    r.old.save_json(r.OUT/'verification.json',result)
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=='__main__': main()
