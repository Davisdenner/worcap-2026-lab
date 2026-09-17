"""Recalcula as previsões, métricas e gates da rodada 24 na grade integral."""
import json
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src import round24 as r
from src.round9 import digest,metrics,passes_gate
from src.round2 import target_origins


def main():
    r.locked()
    tp=np.load(r.old.CACHE/'tp.npy',mmap_mode='r')
    monthly={name:[] for name in ('s12',)+tuple(r.CONFIGS)}
    gridlat=np.arange(-60,15.01,.25)
    mask=np.clip((gridlat+5)/5,0,1)[None,:,None]
    for year in r.old.DEV:
        rows=r.old.read(r.OUT/f'{year}.json'); byname={row['model']:row for row in rows}
        s11=r.old.reference(year); ref=r.prior.reference(year)
        truth=tp[target_origins(year)+1]
        delta={}
        for kind in ('original',)+tuple(r.KINDS):
            path=r.ART/f'{year}_{kind}_delta.npy'
            assert digest(path)==r.old.read(path.with_suffix('.json'))['sha256']
            delta[kind]=np.load(path)
        np.testing.assert_allclose(np.maximum(s11+.25*delta['original'],0),ref,rtol=0,atol=1e-8)
        for name in ('s12',)+tuple(r.CONFIGS):
            if name=='s12': pred=ref
            else:
                kind,scope,beta=r.CONFIGS[name]
                factor=1 if scope=='global' else mask
                pred=np.maximum(s11+.25*(delta['original']+
                    beta*factor*(delta[kind]-delta['original'])),0)
            actual=metrics(pred,truth,ref); recorded=byname[name]
            np.testing.assert_allclose(actual['monthly_rmse'],recorded['monthly_rmse'],rtol=0,atol=1e-9)
            for field in ('rmse','year1_rmse','year2_rmse','correction_rms'):
                np.testing.assert_allclose(actual[field],recorded[field],rtol=0,atol=1e-9)
            north=gridlat>=0
            error=(pred-truth)**2
            north_rmse=float(np.sqrt(np.mean(error[:,north,:])))
            outside_rmse=float(np.sqrt(np.mean(error[:,~north,:])))
            np.testing.assert_allclose([north_rmse,outside_rmse],
                [recorded['north_rmse'],recorded['outside_rmse']],rtol=0,atol=1e-9)
            monthly[name].extend(actual['monthly_rmse'])
        pure=r.old.read(r.OUT/f'{year}_pure.json')
        for row in pure:
            pred=np.maximum(s11+.25*delta[row['model']],0)
            np.testing.assert_allclose(metrics(pred,truth,ref)['rmse'],row['rmse'],rtol=0,atol=1e-9)
        print('VERIFICADO',year,flush=True)
    selected=r.old.read(r.OUT/'selection.json')
    refs=np.asarray(monthly['s12']).reshape(6,24); reference=float(np.sqrt(np.mean(refs**2)))
    np.testing.assert_allclose(reference,selected['reference_rmse'],rtol=0,atol=1e-12)
    refyears=np.sqrt(np.mean(refs.reshape(-1,12)**2,axis=1))
    refsecond=float(np.sqrt(np.mean(refs[:,12:]**2)))
    eligible=[]
    for name in r.CONFIGS:
        values=np.asarray(monthly[name]).reshape(6,24)
        rmse=float(np.sqrt(np.mean(values**2)))
        years=np.sqrt(np.mean(values.reshape(-1,12)**2,axis=1))
        second=float(np.sqrt(np.mean(values[:,12:]**2)))
        blocks=int(np.sum(np.mean(values**2,axis=1)<np.mean(refs**2,axis=1)))
        nyears=int(np.sum(years<refyears)); nmonths=int(np.sum(values<refs))
        worst=float(np.max(years/refyears-1))
        passed=passes_gate(rmse,reference,second,refsecond,blocks,nyears,nmonths,144,worst)
        row=next(v for v in selected['ranking'] if v['model']==name)
        np.testing.assert_allclose(rmse,row['rmse'],rtol=0,atol=1e-12)
        assert (blocks,nyears,nmonths,passed)==(row['blocks_improved'],row['years_improved'],
                                               row['months_improved'],row['passed'])
        if passed: eligible.append((rmse,name))
    eligible.sort()
    assert selected['selected']==(eligible[0][1] if eligible else None)
    result=dict(passed=True,full_grid=True,official_only=True,blocks=list(r.old.DEV),
                original_s12_reproduced=True,selection_recomputed=True,
                csv_exported=False,uploaded=False)
    r.old.save_json(r.OUT/'verification.json',result)
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=='__main__': main()
