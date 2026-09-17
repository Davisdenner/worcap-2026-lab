"""Blocos adicionais causais: componentes oficiais e amostras, sem seleção."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'): os.environ[k]='1'
import argparse
import gc
import joblib
import numpy as np
from . import round17 as old
from . import s11_delivery as base
from .round2 import Features, trees, ridge, target_origins
from .round4 import predict as regional_prediction
from .round6 import local_memory
from .round10 import weather_design
from .round11 import fit_weather, fit_pls, anomaly_prediction, blend
from .competition import ROOT, CACHE, save_json

ART=ROOT/'data/processed/round19'
EARLY=(1997,1999,2001,2003)


def early_prior():
    return np.array([.28125,.140625,.140625,.1875,.25])


def feature_rows(pred,pieces,climo,fields,month,cells,origin):
    x=np.empty((len(cells),23),np.float32)
    x[:,0]=-60+(cells//261)*.25; x[:,1]=-90+(cells%261)*.25
    angle=2*np.pi*(month%12)/12; x[:,2]=np.sin(angle); x[:,3]=np.cos(angle)
    x[:,4]=climo[month%12,cells]; x[:,5]=pred[month,cells]
    part=pieces[:,month,cells].T
    x[:,6:11]=part-x[:,5,None]; x[:,11]=part.std(axis=1)
    x[:,12]=np.ptp(part,axis=1); x[:,13]=x[:,5]-x[:,4]
    for j in range(9): x[:,14+j]=fields[j][origin,cells]
    if not np.isfinite(x).all(): raise ValueError('Atributos inválidos')
    return x


def generate(year):
    if year not in EARLY: raise ValueError('Bloco adicional não registrado')
    from .round19 import locked
    locked(); ART.mkdir(parents=True,exist_ok=True)
    output=ART/f'{year}_samples.npz'
    if output.exists():
        if old.digest(output)!=old.read(output.with_suffix('.json'))['sha256']: raise ValueError('Amostra alterada')
        print('AMOSTRA EXISTENTE',year,flush=True); return
    f=Features(year)
    if f.idx.max()+1 >= (year-1940)*12: raise ValueError('Alvo futuro no treino')
    origins=target_origins(year)
    def cached(name,fn):
        path=ART/f'{year}_{name}.npy'
        if path.exists():
            if old.digest(path)!=old.read(path.with_suffix('.json'))['sha256']: raise ValueError('Cache alterado')
            return np.load(path)
        print('COMPONENTE',year,name,flush=True)
        p=fn(); np.save(path,p)
        save_json(path.with_suffix('.json'),dict(sha256=old.digest(path),last_training_target=f'{year-1}-12',official_only=True))
        return p
    local=cached('localtree',lambda: trees(f,False)['local_150'])
    context=cached('context',lambda: trees(f,True,(150,300))['context_300'])
    linear=cached('ridge',lambda: ridge(f))
    climo=f.climo[(origins+1)%12].reshape(24,301,261)
    s02=.5*context+.25*local+.125*linear+.125*climo
    modes=cached('modes',lambda: next(regional_prediction(f,('mean3',),(.3,)))[1])
    local18=cached('local18',lambda: local_memory(f)[.3])
    coarse=np.load(ROOT/'data/processed/round3/coarse_weather.npy',mmap_mode='r')
    def fitted(name,fn):
        path=ART/f'{year}_{name}.joblib'
        if not path.exists():
            joblib.dump(fn(),path)
            save_json(path.with_suffix('.json'),dict(sha256=old.digest(path),last_training_target=f'{year-1}-12'))
        if old.digest(path)!=old.read(path.with_suffix('.json'))['sha256']: raise ValueError('Modelo alterado')
        return joblib.load(path)
    cont=fitted('continental',lambda: base.fit_continental(f,coarse[:origins[-1]+1]))
    design=weather_design(coarse,cont,origins)
    cp=np.maximum(f.climo[(origins+1)%12]+anomaly_prediction(cont,design),0).astype(np.float32).reshape(24,301,261)
    fine=np.load(ROOT/'data/processed/round11/fine_weather.npy',mmap_mode='r')
    prep=fitted('tropical_weather',lambda: fit_weather(fine,f.idx))
    x=np.column_stack([weather_design(coarse,cont,f.idx),weather_design(fine,prep,f.idx)])
    y=f.tp[f.idx+1,180*261:]-f.climo[(f.idx+1)%12,180*261:]
    trop=fitted('tropical',lambda: fit_pls(x,y,32))
    xv=np.column_stack([design,weather_design(fine,prep,origins)])
    tp=np.maximum(f.climo[(origins+1)%12,180*261:]+anomaly_prediction(trop,xv),0).reshape(24,121,261)
    s09=.75*(.5*s02+.25*modes+.25*local18)+.25*cp
    pieces=np.stack([s02,modes,local18,cp,blend(s09,tp,1.)]).astype(float).reshape(5,24,-1)
    ref=np.sum(pieces*early_prior()[:,None,None],axis=0)
    rng=np.random.default_rng(old.SEED+year); xs=[]; ys=[]
    for m,o in enumerate(origins):
        cells=rng.choice(78561,2048,replace=False)
        xs.append(feature_rows(ref,pieces,f.climo,f.weather,m,cells,o))
        ys.append((f.tp[o+1,cells]-ref[m,cells]).astype(np.float32))
    np.savez_compressed(output,x=np.concatenate(xs),y=np.concatenate(ys))
    save_json(output.with_suffix('.json'),dict(sha256=old.digest(output),block=year,
        base_training_targets_end=f'{year-1}-12',residual_targets_end=f'{year+1}-12',
        official_only=True,prior=early_prior().tolist(),calibration_blocks=[],
        seed=old.SEED+year,samples_per_month=2048,features=old.FEATURES,
        warmup='Prior S10 fixo, sem calibração retrospectiva'))
    print('AMOSTRAS PRONTAS',year,len(np.concatenate(ys)),flush=True)
    del f,pieces,x,y; gc.collect()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('years',nargs='*',type=int,default=EARLY)
    for year in p.parse_args().years: generate(year)
