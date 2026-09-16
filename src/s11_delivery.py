"""Isolated S11 delivery: raw preparation, fixed-configuration training and inference.

No Kaggle access, candidate search, promotion or upload. Frozen experimental
sources are imported only for numerical routines, never their stage runners.
All I/O roots come from the supplied SETTINGS.json.
"""
from __future__ import annotations
import os
for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_key] = '1'
import argparse
import hashlib
import json
import platform
import time
from pathlib import Path
import importlib.metadata
import joblib
import numpy as np
import pandas as pd
import psutil
import xarray as xr
from scipy.ndimage import uniform_filter
from sklearn.decomposition import PCA
from sklearn.cross_decomposition import PLSRegression
from sklearn.ensemble import HistGradientBoostingRegressor
from .competition import VARIABLES, dates, training_pairs, fit_climatology
from .round2 import Features, TREE_CONFIG, target_origins
from .round3 import seasonal_mask, seasonal_design
from .round4 import memory, groups
from .round10 import weather_design
from .round11 import fit_weather, fit_pls, anomaly_prediction, blend
from .round15 import solve_weights
from .submission import export_csv


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')


def settings(path):
    path = Path(path).resolve()
    config = read(path)
    for key in ('raw', 'cache', 'models', 'output', 'evidence'):
        config[key] = (path.parent / config[key]).resolve()
    if any(config[k] == config['raw'] for k in ('cache', 'models', 'output', 'evidence')):
        raise ValueError('Outputs must be separate from raw inputs')
    return config


def prepare(c):
    """Extract official arrays only; no learned statistics or old caches."""
    c['cache'].mkdir(parents=True, exist_ok=True)
    hashes = {}
    with xr.open_dataset(c['raw']/'teste_features.nc') as test:
        np.testing.assert_array_equal(test.time.values.astype('datetime64[M]'), np.arange('2023-01','2025-01',dtype='datetime64[M]'))
        np.testing.assert_array_equal(test.time_origem.values.astype('datetime64[M]'), np.arange('2022-12','2024-12',dtype='datetime64[M]'))
        coarse, fine = [], []
        for name in ['tp']+VARIABLES:
            path = c['raw']/f'treino_{name}.nc'
            hashes[path.name] = digest(path)
            with xr.open_dataset(path) as ds:
                np.testing.assert_array_equal(ds.time.values, dates().values)
                values = ds[name].transpose('time','lat','lon').values
                if values.shape != (996,301,261) or not np.isfinite(values).all():
                    raise ValueError('Invalid official training array')
                np.testing.assert_array_equal(ds.lat.values, np.arange(-60,15.01,.25))
                np.testing.assert_array_equal(ds.lon.values, np.arange(-90,-24.99,.25))
                out = c['cache']/f'{name}.npy'
                if out.exists():
                    np.testing.assert_array_equal(np.load(out,mmap_mode='r'),values)
                else:
                    np.save(out,values)
                if name != 'tp':
                    np.testing.assert_array_equal(test[name].values[0],values[-1])
                    # Training-only spatial caches. Inference transforms new fields separately.
                    small, detail = [], []
                    for start in range(0,len(values),48):
                        block = values[start:start+48]
                        small.append(uniform_filter(block,size=(1,9,9),mode='nearest')[:,::8,::8].reshape(len(block),-1))
                        detail.append(uniform_filter(block,size=(1,5,5),mode='nearest')[:,160::4,::4].reshape(len(block),-1))
                    coarse.append(np.concatenate(small)); fine.append(np.concatenate(detail))
            print('PREPARED',name,flush=True)
        for name, pieces in [('coarse',coarse),('fine',fine)]:
            out=c['cache']/f'{name}.npy'; values=np.concatenate(pieces,axis=1)
            if out.exists(): np.testing.assert_array_equal(values,np.load(out))
            else: np.save(out,values)
    hashes['teste_features.nc']=digest(c['raw']/'teste_features.nc')
    expected=read(c['evidence']/'official_sources.json')
    if hashes != expected: raise ValueError('Input package differs from original S11 official sources')
    write(c['cache']/'prepared.json',dict(official_only=True,source_hashes=hashes))


class TrainingFeatures(Features):
    def __init__(self,c):
        self.year=2023; self.times=dates(); self.idx=training_pairs(self.times,'2023-01-01')
        self.tp=np.load(c['cache']/'tp.npy',mmap_mode='r').reshape(996,-1)
        self.weather=[np.load(c['cache']/f'{v}.npy',mmap_mode='r').reshape(996,-1) for v in VARIABLES]
        self.test=[None]*9
        self.climo=fit_climatology(self.tp,self.times,'2023-01-01',60)
        self.means=np.empty((12,78561,9),dtype=np.float32)
        for j,w in enumerate(self.weather):
            for m in range(12): self.means[m,:,j]=np.nanmean(w[self.idx[self.idx%12==m]],axis=0)
        np.nan_to_num(self.means,copy=False)
        lat,lon=np.meshgrid(np.arange(-60,15.01,.25),np.arange(-90,-24.99,.25),indexing='ij')
        self.lat,self.lon=lat.ravel(),lon.ravel()


class PredictionFeatures(Features):
    def __init__(self,model,test):
        self.year=2023; self.means=model['means']; self.climo=model['climatology']
        self.history=model['weather_history']
        self.test=[test[v].transpose('time','lat','lon').values.reshape(24,-1) for v in VARIABLES]
        for j in range(9): np.testing.assert_array_equal(self.test[j][0],self.history[j][-1])
        lat,lon=np.meshgrid(test.lat.values,test.lon.values,indexing='ij')
        self.lat,self.lon=lat.ravel(),lon.ravel()

    def row(self,j,origin):
        if 993 <= origin <= 995: return self.history[j][origin-993]
        if 996 <= origin <= 1018: return self.test[j][origin-995]
        raise ValueError('Prediction needs contiguous atmospheric history October 2022 to November 2024')


def fit_tree(f,context):
    rng=np.random.default_rng(20260914); n=768
    x=np.empty((len(f.idx)*n,55 if context else 23),dtype=np.float32)
    y=np.empty(len(x),dtype=np.float32)
    for k,origin in enumerate(f.idx):
        cells=rng.choice(78561,n,replace=False); sl=slice(k*n,(k+1)*n)
        x[sl]=f.matrix(origin,cells,context); y[sl]=f.tp[origin+1,cells]-x[sl,4]
    model=HistGradientBoostingRegressor(max_iter=150,**TREE_CONFIG).fit(x,y)
    if context: model.set_params(max_iter=300).fit(x,y)
    return model


def fit_local(f,seasonal):
    """Persist every fitted scale, centering offset and ridge coefficient."""
    n=18 if seasonal else 9; months=12 if seasonal else 1
    model={k:np.empty((months,78561,n),dtype=d) for k,d in [('scale',np.float32),('xm',np.float32),('coef',np.float64 if seasonal else np.float32)]}
    model['ym']=np.empty((months,78561),dtype=np.float32)
    step=7 if seasonal else 19; idx=f.idx
    for begin in range(0,301,step):
        end=min(begin+step,301); sl=slice(begin*261,end*261)
        xall=np.empty((len(idx),(end-begin)*261,n),dtype=np.float32)
        scales=[]
        for j,w in enumerate(f.weather):
            means=f.means[:,sl,j]; current=w[idx,sl]-means[idx%12]
            if seasonal:
                frames=[w[idx-k,sl]-means[(idx-k)%12] for k in range(3)]
                xall[:,:,j]=frames[0]; xall[:,:,j+9]=sum(frames)/3
            else:
                scale=np.nanstd(current,axis=0); scale=np.where(np.isfinite(scale)&(scale>1e-8),scale,1)
                xall[:,:,j]=np.nan_to_num(current/scale); scales.append(scale)
        yall=f.tp[idx+1,sl]-f.climo[(idx+1)%12,sl]
        for m in range(months):
            use=seasonal_mask(idx,m) if seasonal else np.ones(len(idx),dtype=bool)
            x=xall[use].copy(); y=yall[use].copy()
            if seasonal:
                scale=np.maximum(x.std(axis=0),1e-8); x/=scale
            else: scale=np.stack(scales,axis=1)
            xm,ym=x.mean(axis=0),y.mean(axis=0); x-=xm; y-=ym
            xx=np.einsum('tpi,tpj->pij',x,x,optimize=True)/len(x)
            xy=np.einsum('tpi,tp->pi',x,y,optimize=True)/len(x)
            penalty=.3*np.eye(n) if seasonal else .1*np.eye(n,dtype=np.float32)
            coef=np.linalg.solve(xx+penalty[None],xy[...,None])[...,0]
            for key,val in [('scale',scale),('xm',xm),('ym',ym),('coef',coef)]: model[key][m,sl]=val
        print('LOCAL FIT',n,end,'/301',flush=True)
    return model


def fit_regional(f,raw):
    idx=f.idx
    means=np.stack([raw[idx[idx%12==m]].mean(axis=0) for m in range(12)])
    train=raw[idx]-means[idx%12]; scale=np.maximum(train.std(axis=0),1e-8)
    pca=PCA(n_components=16,svd_solver='randomized',random_state=20260914).fit(train/scale)
    pc_scale=np.maximum(pca.transform(train/scale).std(axis=0),1e-8)
    model=dict(pca=pca,means=means,scale=scale,pc_scale=pc_scale)
    x=np.column_stack([np.ones(len(idx)),weather_design(raw,model,idx)])
    xx=x.T@x/len(x); coef=np.empty((x.shape[1],78561))
    for start in range(0,78561,5000):
        sl=slice(start,start+5000); y=f.tp[idx+1,sl]-f.climo[(idx+1)%12,sl]
        penalty=.3*np.eye(x.shape[1]); penalty[0,0]=0
        coef[:,sl]=np.linalg.solve(xx+penalty,x.T@y/len(x))
    model['coefficients']=coef
    return model


def fit_continental(f,raw):
    idx=f.idx; seed=20260916
    means=np.stack([raw[idx[idx%12==m]].mean(axis=0) for m in range(12)])
    train=raw[idx]-means[idx%12]; scale=np.maximum(train.std(axis=0),1e-8)
    pca=PCA(n_components=64,svd_solver='randomized',random_state=seed).fit(train/scale)
    z=pca.transform((raw-means[np.arange(len(raw))%12])/scale)
    pc_scale=np.maximum(z[idx].std(axis=0),1e-8); z/=pc_scale
    x=seasonal_design(memory(z,idx,'mean3'),idx)[:,1:]
    x_scale=np.maximum(x.std(axis=0),1e-8); x/=x_scale
    y=f.tp[idx+1]-f.climo[(idx+1)%12]
    target=PCA(n_components=32,svd_solver='randomized',random_state=seed).fit_transform(y)
    pls=PLSRegression(n_components=16,scale=False,max_iter=1000,tol=1e-7).fit(x,target)
    scores=pls.transform(x); score_scale=np.maximum(scores.std(axis=0),1e-8)
    design=np.column_stack([np.ones(len(idx)),scores/score_scale])
    penalty=.3*np.eye(17); penalty[0,0]=0
    coef=np.linalg.solve(design.T@design/len(idx)+penalty,design.T@y/len(idx))
    return dict(pca=pca,means=means,scale=scale,pc_scale=pc_scale,x_scale=x_scale,
                pls=pls,score_scale=score_scale,coefficients=coef)


def train(c):
    """Refit final base models from raw-derived arrays, with frozen S11 settings."""
    if not (c['cache']/'prepared.json').exists(): raise ValueError('Run prepare first')
    c['models'].mkdir(parents=True,exist_ok=True)
    f=TrainingFeatures(c)
    def fitted(name,fn):
        p=c['models']/f'{name}.joblib'
        if p.exists(): raise FileExistsError(p)
        started=time.perf_counter(); result=fn(); joblib.dump(result,p)
        print('SAVED MODEL',name,round(time.perf_counter()-started,2),'seconds',flush=True)
        return result
    prep=dict(means=f.means,climatology=f.climo,weather_history=np.stack([w[-3:] for w in f.weather]))
    fitted('preprocessing',lambda:prep)
    fitted('local_tree',lambda:fit_tree(f,False))
    fitted('context_tree',lambda:fit_tree(f,True))
    fitted('ridge9',lambda:fit_local(f,False))
    fitted('local18',lambda:fit_local(f,True))
    raw=np.load(c['cache']/'coarse.npy',mmap_mode='r')
    fitted('regional',lambda:fit_regional(f,raw))
    continental=fitted('continental',lambda:fit_continental(f,raw))
    fine=np.load(c['cache']/'fine.npy',mmap_mode='r')
    regional=fitted('tropical_weather',lambda:fit_weather(fine,f.idx))
    x=np.column_stack([weather_design(raw,continental,f.idx),weather_design(fine,regional,f.idx)])
    y=f.tp[f.idx+1,180*261:]-f.climo[(f.idx+1)%12,180*261:]
    fitted('tropical',lambda:fit_pls(x,y,32))
    weights=read(c['evidence']/'frozen_weights.json')
    # Refit the final combiner from archived OOF sufficient statistics. No test labels.
    cov=np.load(c['evidence']/'calibration_covariances.npy')
    prior=np.asarray(weights['prior']); mean=cov.mean(axis=0)
    actual=np.stack([solve_weights(mean[g],prior[g],1.) for g in range(12)])
    np.testing.assert_array_equal(actual,np.asarray(weights['weights']))
    write(c['models']/'weights.json',weights)
    write(c['models']/'manifest.json',dict(training_targets_end='2022-12',training_pairs=len(f.idx),
          fixed_configuration='S11 joint1',official_only=True,
          calibration='Archived official-only OOF covariance sufficient statistics 2005-2022; no new search',
          hashes={p.name:digest(p) for p in c['models'].iterdir() if p.is_file()}))


def local_prediction(f,model,seasonal):
    origins=target_origins(2023); base=f.climo[(origins+1)%12].reshape(24,301,261); pred=base.copy()
    step=7 if seasonal else 19; n=18 if seasonal else 9
    for begin in range(0,301,step):
        end=min(begin+step,301); sl=slice(begin*261,end*261)
        v=np.empty((24,(end-begin)*261,n),dtype=np.float32)
        for j in range(9):
            means=f.means[:,sl,j]
            frames=[np.stack([f.row(j,int(o-k))[sl] for o in origins])-means[(origins-k)%12] for k in range(3 if seasonal else 1)]
            v[:,:,j]=frames[0]
            if seasonal: v[:,:,j+9]=sum(frames)/3
        for m in range(12 if seasonal else 1):
            take=np.flatnonzero((origins+1)%12==m) if seasonal else np.arange(24)
            xv=v[take].copy(); xv/=model['scale'][m,sl]
            if not seasonal: np.nan_to_num(xv,copy=False)
            xv-=model['xm'][m,sl]
            corr=np.einsum('tpi,pi->tp',xv,model['coef'][m,sl])+model['ym'][m,sl]
            pred[take,begin:end]=np.maximum(base[take,begin:end]+corr.reshape(len(take),end-begin,261),0)
    return pred


def predict(c):
    """Inference reads serialized models and official test fields; never rain labels."""
    manifest=read(c['models']/'manifest.json')
    for name,h in manifest['hashes'].items():
        if digest(c['models']/name)!=h: raise ValueError('Model integrity failure')
    c['output'].mkdir(parents=True,exist_ok=True)
    csv=c['output']/'s11_reproduction.csv'
    if csv.exists(): raise FileExistsError(csv)
    load=lambda n:joblib.load(c['models']/f'{n}.joblib')
    prep=load('preprocessing'); origins=target_origins(2023); months=(origins+1)%12
    with xr.open_dataset(c['raw']/'teste_features.nc') as test:
        np.testing.assert_array_equal(test.time.values.astype('datetime64[M]'),np.arange('2023-01','2025-01',dtype='datetime64[M]'))
        np.testing.assert_array_equal(test.lat.values,np.arange(-60,15.01,.25))
        np.testing.assert_array_equal(test.lon.values,np.arange(-90,-24.99,.25))
        f=PredictionFeatures(prep,test); base=f.climo[months].reshape(24,301,261)
        trees=[]; cells=np.arange(78561)
        for context,name in [(False,'local_tree'),(True,'context_tree')]:
            model=load(name); pred=np.empty((24,301,261),np.float32)
            for k,o in enumerate(origins):
                x=f.matrix(o,cells,context); pred[k]=np.maximum(x[:,4]+model.predict(x),0).reshape(301,261)
            trees.append(pred)
        linear=local_prediction(f,load('ridge9'),False)
        # Preserve original float32 arithmetic and grouping in S02 exactly.
        legacy=.5*trees[0]+.25*linear+.25*base
        s02=.5*trees[1]+.5*legacy
        local=local_prediction(f,load('local18'),True)
        coarse=[]; fine=[]
        for j,v in enumerate(VARIABLES):
            raw=np.concatenate([prep['weather_history'][j].reshape(3,301,261),test[v].values[1:]])
            coarse.append(uniform_filter(raw,size=(1,9,9),mode='nearest')[:,::8,::8].reshape(26,-1))
            fine.append(uniform_filter(raw,size=(1,5,5),mode='nearest')[:,160::4,::4].reshape(26,-1))
        coarse,fine=np.concatenate(coarse,axis=1),np.concatenate(fine,axis=1)
        # Padding preserves original absolute month indexing without needing training fields.
        def pad(raw):
            full=np.zeros((1019,raw.shape[1]),raw.dtype); full[993:]=raw; return full
        coarse,fine=pad(coarse),pad(fine)
        regional=load('regional')
        design=np.column_stack([np.ones(24),weather_design(coarse,regional,origins)])
        modes=base.copy().reshape(24,-1)
        for start in range(0,78561,5000):
            sl=slice(start,start+5000)
            modes[:,sl]=np.maximum(modes[:,sl]+design@regional['coefficients'][:,sl],0)
        modes=modes.reshape(24,301,261)
        continental=load('continental'); x=weather_design(coarse,continental,origins)
        cont=np.maximum(f.climo[months]+anomaly_prediction(continental,x),0).astype(np.float32).reshape(24,301,261)
        x=np.column_stack([x,weather_design(fine,load('tropical_weather'),origins)])
        trop=np.maximum(f.climo[months,180*261:]+anomaly_prediction(load('tropical'),x),0).reshape(24,121,261)
        w=read(c['models']/'weights.json'); prior=np.asarray(w['prior'])
        base_weights=np.asarray(w['base_weights'])
        s06=np.sum(np.stack([s02,modes,local]).astype(float)*base_weights[groups()].transpose(3,0,1,2),axis=0)
        s09=.75*s06+.25*cont
        extended=blend(s09,trop,1.)
        pieces=np.stack([s02,modes,local,cont,extended]).astype(float)
        result=np.sum(pieces*np.asarray(w['weights'])[groups()].transpose(3,0,1,2),axis=0)
        for name,p in [('s02',s02),('modes',modes),('local18',local),('pls16',cont),('fine32',trop)]:
            np.save(c['output']/f'{name}.npy',p)
        da=xr.DataArray(result,dims=('time','lat','lon'),coords={d:test[d] for d in ('time','lat','lon')},name='tp_mm_day')
        da.to_netcdf(c['output']/'s11_reproduction.nc')
        meta=export_csv(da,test,csv,c['raw']/'sample_submission.csv')
    meta.update(csv_sha256=digest(csv),reproduction_only=True,new_candidate=False,uploaded=False)
    write(csv.with_suffix('.json'),meta)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('prepare','train','predict'))
    parser.add_argument('--settings',type=Path,required=True)
    args=parser.parse_args(); c=settings(args.settings)
    start=time.perf_counter(); globals()[args.stage](c)
    m=psutil.Process().memory_info()
    write(c['output']/f'{args.stage}_execution.json',dict(seconds=time.perf_counter()-start,
          process_peak_working_set_bytes=getattr(m,'peak_wset',None),python=platform.python_version(),
          platform=platform.platform(),logical_cpu_count=psutil.cpu_count(),physical_cpu_count=psutil.cpu_count(logical=False),
          ram_bytes=psutil.virtual_memory().total,threads=1,
          packages={p:importlib.metadata.version(p) for p in ('numpy','scipy','scikit-learn','xarray','pandas','joblib','netCDF4','psutil')}))


if __name__=='__main__': main()
