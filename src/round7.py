"""Joint local and continental atmospheric memory, bounded S07 experiment."""
import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import xarray as xr
from sklearn.decomposition import PCA

from .competition import ROOT, REPORT, RAW, CACHE, save_json, score
from .round2 import Features, target_origins
from .round3 import ART as R3, YEARS, seasonal_mask, seasonal_design
from .round4 import ART as R4, memory, groups
from .round6 import ART as R6, history_features
from .submission import export_csv

ART=ROOT / "data/processed/round7"
OUT=REPORT / "round7"


def ocean_history(values,origins):
    origins=np.asarray(origins)
    if origins.min()<3:
        raise ValueError("Need ocean observations from target minus two months or earlier")
    current=values[origins-1]
    average=sum(values[origins-k] for k in (1,2,3))/3
    result=np.column_stack([current,average])
    if not np.isfinite(result).all():
        raise ValueError("Missing ocean observations")
    return result


def ocean_model(f,final=False):
    idx,origins=f.idx,target_origins(f.year)
    raw=np.load(R3 / "coarse_weather.npy",mmap_mode="r")[:origins[-1]+1]
    means=np.stack([raw[idx[idx%12==m]].mean(axis=0) for m in range(12)])
    train=raw[idx]-means[idx%12]; scale=np.maximum(train.std(axis=0),1e-8)
    pca=PCA(n_components=16,svd_solver="randomized",random_state=20260914).fit(train/scale)
    pc_scale=np.maximum(pca.transform(train/scale).std(axis=0),1e-8)
    z=pca.transform((raw-means[np.arange(len(raw))%12])/scale)/pc_scale
    source=ROOT / "data/external/ersst5.nino.mth.91-20.ascii"
    table=np.loadtxt(source,skiprows=1)
    if table.ndim!=2 or table.shape[1]!=10:
        raise ValueError("Unexpected NOAA table shape")
    dates=(table[:,0].astype(int)-1940)*12+table[:,1].astype(int)-1
    if len(np.unique(dates))!=len(dates) or not np.all((table[:,1]>=1)&(table[:,1]<=12)):
        raise ValueError("Invalid or duplicate NOAA dates")
    used=table[(dates>=((1980-1940)*12))&(dates<(2024-1940)*12+10)][:,[2,4,6,8]]
    if not np.isfinite(used).all() or (used<=0).any() or (used>=40).any():
        raise ValueError("Invalid raw tropical SST values")
    ocean=np.full((len(raw),4),np.nan,dtype=float)
    for row in table:
        j=(int(row[0])-1940)*12+int(row[1])-1
        if 0<=j<min(len(raw),(2024-1940)*12+10):
            ocean[j]=row[[2,4,6,8]]
    ocean_means=np.stack([ocean[(idx-1)[(idx-1)%12==m]].mean(axis=0) for m in range(12)])
    ocean-=ocean_means[np.arange(len(ocean))%12]
    ox,ov=ocean_history(ocean,idx),ocean_history(ocean,origins)
    oscale=np.maximum(ox.std(axis=0),1e-8)
    x=seasonal_design(np.column_stack([memory(z,idx,"mean3"),ox/oscale]),idx)
    xv=seasonal_design(np.column_stack([memory(z,origins,"mean3"),ov/oscale]),origins)
    base=f.climo[(origins+1)%12]; pred={a:base.copy() for a in (.3,3.)}
    xx=x.T@x/len(x)
    coefficients={a:np.empty((x.shape[1],base.shape[1])) for a in pred} if final else None
    for start in range(0,base.shape[1],5000):
        sl=slice(start,start+5000)
        y=f.tp[idx+1,sl]-f.climo[(idx+1)%12,sl]
        xy=x.T@y/len(x)
        for a in pred:
            penalty=a*np.eye(x.shape[1]); penalty[0,0]=0
            coef=np.linalg.solve(xx+penalty,xy)
            pred[a][:,sl]=np.maximum(base[:,sl]+xv@coef,0)
            if final:
                coefficients[a][:,sl]=coef
    if final:
        joblib.dump(dict(pca=pca,means=means,scale=scale,pc_scale=pc_scale,ocean_means=ocean_means,
                         ocean_scale=oscale,coefficients=coefficients,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest()),
                    ART / "final_ocean.joblib")
    return {a:p.reshape(24,301,261) for a,p in pred.items()}


def ocean():
    cal=json.loads((REPORT / "round4/calibration.json").read_text())
    for i,year in enumerate(YEARS):
        f=Features(year)
        truth=f.tp[target_origins(year)+1].reshape(24,301,261)
        ref=np.load(R6 / f"{year}_memory_0.3_1.npy")
        old=np.load(R4 / f"{year}_mean3_0.3.npy")
        weights=np.asarray(cal["leave_block_out_weights"][i])[groups(),1]
        rows=json.loads((OUT / f"{year}.json").read_text())
        rows=[r for r in rows if not r["model"].startswith("ocean_")]
        for a,new in ocean_model(f).items():
            np.save(ART / f"{year}_ocean_{a:g}.npy",new)
            for fraction in (.5,1.):
                pred=np.maximum(ref+fraction*weights*(new-old),0)
                name=f"ocean_{a:g}_{fraction:g}"
                row=dict(model=name,**score(pred,truth)); rows.append(row)
                np.save(ART / f"{year}_{name}.npy",pred)
                print(year,name,row["rmse"],flush=True)
        save_json(OUT / f"{year}.json",rows)


def continental(f, final=False):
    idx,origins=f.idx,target_origins(f.year)
    raw=np.load(R3 / "coarse_weather.npy",mmap_mode="r")[:origins[-1]+1]
    means=np.stack([raw[idx[idx%12==m]].mean(axis=0) for m in range(12)])
    train=raw[idx]-means[idx%12]
    scale=np.maximum(train.std(axis=0),1e-8)
    pca=PCA(n_components=16,svd_solver="randomized",random_state=20260914).fit(train/scale)
    pc_scale=np.maximum(pca.transform(train/scale).std(axis=0),1e-8)
    z=(pca.transform((raw-means[np.arange(len(raw))%12])/scale)/pc_scale)[:,:4]
    if final:
        joblib.dump(dict(pca=pca,monthly_means=means,scale=scale,pc_scale=pc_scale,used_components=4),ART / "final_continental.joblib")
    return memory(z,idx,"mean3"),memory(z,origins,"mean3")


def joint(f, final=False):
    idx,origins=f.idx,target_origins(f.year)
    gx,gv=continental(f,final)
    base=f.climo[(origins+1)%12].reshape(24,301,261)
    predictions={a:base.copy() for a in (.3,3.)}
    for begin in range(0,301,7):
        end=min(begin+7,301); sl=slice(begin*261,end*261)
        xall=np.empty((len(idx),(end-begin)*261,26),dtype=np.float32)
        vall=np.empty((24,(end-begin)*261,26),dtype=np.float32)
        for j,w in enumerate(f.weather):
            means=f.means[:,sl,j]
            frames=[w[idx-k,sl]-means[(idx-k)%12] for k in range(3)]
            now,avg=history_features(lambda o:f.row(j,o)[sl],means,origins)
            xall[:,:,j],xall[:,:,j+9]=frames[0],sum(frames)/3
            vall[:,:,j],vall[:,:,j+9]=now,avg
        xall[:,:,18:]=gx[:,None,:]; vall[:,:,18:]=gv[:,None,:]
        yall=f.tp[idx+1,sl]-f.climo[(idx+1)%12,sl]
        for month in range(12):
            use=seasonal_mask(idx,month)
            take=np.flatnonzero((origins+1)%12==month)
            x,xv,y=xall[use].copy(),vall[take].copy(),yall[use].copy()
            scale=np.maximum(x.std(axis=0),1e-8)
            x/=scale; xv/=scale
            xm,ym=x.mean(axis=0),y.mean(axis=0)
            x-=xm; xv-=xm; y-=ym
            xx=np.einsum("tpi,tpj->pij",x,x,optimize=True)/len(x)
            xy=np.einsum("tpi,tp->pi",x,y,optimize=True)/len(x)
            for a in predictions:
                coef=np.linalg.solve(xx+a*np.eye(26)[None],xy[...,None])[...,0]
                delta=np.einsum("tpi,pi->tp",xv,coef)+ym
                predictions[a][take,begin:end]=np.maximum(base[take,begin:end]+delta.reshape(len(take),end-begin,261),0)
        if end%70==0 or end==301:
            print(f.year,"joint latitude rows",end,"/301",flush=True)
    return predictions


def evaluate():
    ART.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
    for year in YEARS:
        f=Features(year)
        truth=f.tp[target_origins(year)+1].reshape(24,301,261)
        ref=np.load(R6 / f"{year}_memory_0.3_1.npy")
        rows=[dict(model="submission06",**score(ref,truth))]
        for a,new in joint(f).items():
            np.save(ART / f"{year}_joint_{a:g}.npy",new)
            for weight in (.25,.5):
                pred=(1-weight)*ref+weight*new
                name=f"joint_{a:g}_{weight:g}"
                row=dict(model=name,**score(pred,truth)); rows.append(row)
                np.save(ART / f"{year}_{name}.npy",pred)
                print(year,name,row["rmse"],flush=True)
        save_json(OUT / f"{year}.json",rows)


def select():
    rows={y:json.loads((OUT / f"{y}.json").read_text()) for y in YEARS}
    ranking=[]
    for name in [r["model"] for r in rows[YEARS[0]]]:
        candidates=[next(r for r in rows[y] if r["model"]==name) for y in YEARS]
        ranking.append(dict(model=name,rmse=float(np.sqrt(np.mean([r["rmse"]**2 for r in candidates]))),
                            second_year_rmse=float(np.sqrt(np.mean([r["year2_rmse"]**2 for r in candidates]))),
                            folds_improved=sum(r["rmse"]<rows[y][0]["rmse"] for y,r in zip(YEARS,candidates)),
                            years_improved=sum(r[k]<rows[y][0][k] for y,r in zip(YEARS,candidates) for k in ("year1_rmse","year2_rmse"))))
    ranking.sort(key=lambda r:r["rmse"])
    ref=next(r for r in ranking if r["model"]=="submission06")
    eligible=[r for r in ranking if r["rmse"]<ref["rmse"] and r["second_year_rmse"]<ref["second_year_rmse"]
              and r["folds_improved"]>=3 and r["years_improved"]>=6]
    report=dict(selected=eligible[0]["model"] if eligible else "submission06",ranking=ranking,holdout_evaluated=False,
                caveat="Reused retrospective development blocks; S06 inherited cross-fitted weights. Not an independent test.")
    save_json(OUT / "selection.json",report)
    print(json.dumps(report,indent=2),flush=True)


def final():
    choice=json.loads((OUT / "selection.json").read_text()); name=choice["selected"]
    if name=="submission06":
        raise RuntimeError("No qualifying candidate")
    path=ROOT / "submissions/submission_07.csv"
    if path.exists():
        raise FileExistsError(path)
    family,a,weight=name.split("_"); a,weight=float(a),float(weight)
    f=Features(2023,final=True)
    new=ocean_model(f,final=True)[a] if family=="ocean" else joint(f,final=True)[a]
    np.save(ART / f"final_{family}_{a:g}.npy",new)
    with xr.open_dataset(R6 / "submission_06_predictions.nc") as ds:
        pred=(1-weight)*ds.tp_mm_day.values+weight*new
        reference=ds.tp_mm_day.values.copy()
    if family=="ocean":
        model=joblib.load(R4 / "final_mean3.joblib")
        origins=target_origins(2023); take=np.arange(origins[-1]+1)
        raw=np.load(R3 / "coarse_weather.npy",mmap_mode="r")[take]
        z=model["pca"].transform((raw-model["monthly_means"][take%12])/model["scale"])/model["pc_scale"]
        old=np.maximum(f.climo[(origins+1)%12]+seasonal_design(memory(z,origins,"mean3"),origins)@model["coefficients"][.3],0).reshape(24,301,261)
        cal=json.loads((REPORT / "round4/calibration.json").read_text())
        weights=np.asarray(cal["final_weights"])[groups(),1]
        pred=np.maximum(reference+weight*weights*(new-old),0)
    with xr.open_dataset(RAW / "teste_features.nc") as grid:
        da=xr.DataArray(pred,dims=("time","lat","lon"),coords={d:grid[d] for d in ("time","lat","lon")},name="tp_mm_day")
        da.attrs.update(units="mm/day",model=name)
        da.to_netcdf(ART / "submission_07_predictions.nc")
        report=export_csv(da,grid,path,RAW / "sample_submission.csv")
    report.update(model=name,development_selection=choice,uploaded=False,public_score=None,training_targets_end="2022-12",
                  csv_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    if family=="ocean":
        report["external_source"]=json.loads((ROOT / "data/external/ersst5.nino.mth.91-20.json").read_text())
    save_json(path.with_suffix(".json"),report)
    print(json.dumps(report,indent=2),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=("evaluate","ocean","select","final"))
    args=parser.parse_args(); globals()[args.stage]()
