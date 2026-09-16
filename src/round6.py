"""Local seasonal atmospheric memory, four bounded candidates against S04."""
import argparse
import json
import hashlib
from pathlib import Path

import numpy as np
import xarray as xr

from .competition import ROOT, REPORT, CACHE, RAW, save_json, score
from .round2 import Features, target_origins
from .round3 import YEARS, ART as R3, seasonal_mask
from .round4 import ART as R4, groups
from .submission import export_csv

ART = ROOT / "data/processed/round6"
OUT = REPORT / "round6"


def history_features(read_row, means, origins):
    """Current and trailing-three-month anomalies, in that order."""
    origins = np.asarray(origins)
    if origins.min()<2:
        raise ValueError("Three observed months required")
    frames = [np.stack([read_row(int(o-k)) for o in origins])-means[(origins-k)%12] for k in range(3)]
    return frames[0],sum(frames)/3


def local_memory(f):
    idx, origins = f.idx, target_origins(f.year)
    if min(idx.min(), origins.min()) < 2:
        raise ValueError("Three observed weather months required")
    base = f.climo[(origins+1)%12].reshape(24,301,261)
    predictions = {a:base.copy() for a in (.3,3.)}
    for begin in range(0,301,7):
        end = min(begin+7,301)
        sl = slice(begin*261,end*261)
        xall = np.empty((len(idx),(end-begin)*261,18),dtype=np.float32)
        vall = np.empty((24,(end-begin)*261,18),dtype=np.float32)
        for j,w in enumerate(f.weather):
            means = f.means[:,sl,j]
            train = [w[idx-k,sl]-means[(idx-k)%12] for k in range(3)]
            current,average = history_features(lambda o:f.row(j,o)[sl],means,origins)
            xall[:,:,j] = train[0]
            xall[:,:,j+9] = sum(train)/3
            vall[:,:,j] = current
            vall[:,:,j+9] = average
        yall = f.tp[idx+1,sl]-f.climo[(idx+1)%12,sl]
        for month in range(12):
            use = seasonal_mask(idx,month)
            take = np.flatnonzero((origins+1)%12==month)
            x,xv,y = xall[use].copy(),vall[take].copy(),yall[use].copy()
            scale = np.maximum(x.std(axis=0),1e-8)
            x /= scale; xv /= scale
            xm,ym = x.mean(axis=0),y.mean(axis=0)
            x -= xm; xv -= xm; y -= ym
            xx = np.einsum("tpi,tpj->pij",x,x,optimize=True)/len(x)
            xy = np.einsum("tpi,tp->pi",x,y,optimize=True)/len(x)
            for a in predictions:
                coef = np.linalg.solve(xx+a*np.eye(18)[None],xy[...,None])[...,0]
                correction = np.einsum("tpi,pi->tp",xv,coef)+ym
                predictions[a][take,begin:end] = np.maximum(base[take,begin:end]+correction.reshape(len(take),end-begin,261),0)
        if end%70==0 or end==301:
            print(f.year,"latitude rows",end,"/301",flush=True)
    return predictions


def evaluate():
    ART.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
    cal = json.loads((REPORT / "round4/calibration.json").read_text())
    for i,year in enumerate(YEARS):
        f = Features(year)
        truth = f.tp[target_origins(year)+1].reshape(24,301,261)
        ref = np.load(R4 / f"{year}_calibrated.npy")
        old = np.load(R3 / f"{year}_seasonal_0.3.npy")
        weights = np.asarray(cal["leave_block_out_weights"][i])[groups(),2]
        rows = [dict(model="submission04",**score(ref,truth))]
        for a,new in local_memory(f).items():
            np.save(ART / f"{year}_memory_{a:g}.npy",new)
            for fraction in (.5,1.):
                pred = np.maximum(ref+fraction*weights*(new-old),0)
                name = f"memory_{a:g}_{fraction:g}"
                row = dict(model=name,**score(pred,truth))
                rows.append(row)
                np.save(ART / f"{year}_{name}.npy",pred)
                print(year,name,row["rmse"],flush=True)
        save_json(OUT / f"{year}.json",rows)


def select():
    rows = {y:json.loads((OUT / f"{y}.json").read_text()) for y in YEARS}
    tp = np.load(CACHE / "tp.npy",mmap_mode="r")
    refs5 = {y:score(np.load(ROOT / f"data/processed/round5/{y}_complement_0.5.npy"),
                    tp[target_origins(y)+1]) for y in YEARS}
    ranking = []
    for name in [r["model"] for r in rows[YEARS[0]]]:
        candidates = [next(r for r in rows[y] if r["model"]==name) for y in YEARS]
        ranking.append(dict(model=name,rmse=float(np.sqrt(np.mean([r["rmse"]**2 for r in candidates]))),
                            second_year_rmse=float(np.sqrt(np.mean([r["year2_rmse"]**2 for r in candidates]))),
                            folds_improved=sum(r["rmse"]<rows[y][0]["rmse"] for y,r in zip(YEARS,candidates)),
                            folds_improved_vs_s05=sum(r["rmse"]<refs5[y]["rmse"] for y,r in zip(YEARS,candidates)),
                            years_improved_vs_s05=sum(r[k]<refs5[y][k] for y,r in zip(YEARS,candidates)
                                               for k in ("year1_rmse","year2_rmse")),
                            years_improved=sum(r[k]<rows[y][0][k] for y,r in zip(YEARS,candidates)
                                               for k in ("year1_rmse","year2_rmse"))))
    ranking.sort(key=lambda r:r["rmse"])
    ref = next(r for r in ranking if r["model"]=="submission04")
    ref5 = dict(rmse=float(np.sqrt(np.mean([r["rmse"]**2 for r in refs5.values()]))),
                second_year_rmse=float(np.sqrt(np.mean([r["year2_rmse"]**2 for r in refs5.values()]))))
    eligible = [r for r in ranking if r["rmse"]<ref["rmse"] and r["second_year_rmse"]<ref["second_year_rmse"]
                and r["folds_improved"]>=3 and r["years_improved"]>=6
                and r["rmse"]<ref5["rmse"] and r["second_year_rmse"]<ref5["second_year_rmse"]
                and r["folds_improved_vs_s05"]>=3 and r["years_improved_vs_s05"]>=6]
    report = dict(selected=eligible[0]["model"] if eligible else "submission04",ranking=ranking,
                  submission05_reference=ref5,holdout_evaluated=False,caveat="Reused retrospective development blocks and S04 cross-fitted weights; not independent test.")
    save_json(OUT / "selection.json",report)
    print(json.dumps(report,indent=2),flush=True)


def final():
    choice=json.loads((OUT / "selection.json").read_text())
    name=choice["selected"]
    if name=="submission04":
        raise RuntimeError("No candidate passed the stability gate against S04 and S05")
    destination=ROOT / "submissions/submission_06.csv"
    if destination.exists():
        raise FileExistsError(destination)
    _,penalty,fraction=name.split("_")
    f=Features(2023,final=True)
    predictions=local_memory(f)
    for a,p in predictions.items():
        np.save(ART / f"final_memory_{a:g}.npy",p)
    from .round3 import seasonal_local
    old=seasonal_local(f)["seasonal_0.3"]
    cal=json.loads((REPORT / "round4/calibration.json").read_text())
    weights=np.asarray(cal["final_weights"])[groups(),2]
    with xr.open_dataset(R4 / "submission_04_predictions.nc") as ds:
        pred=np.maximum(ds.tp_mm_day.values+float(fraction)*weights*(predictions[float(penalty)]-old),0)
    with xr.open_dataset(RAW / "teste_features.nc") as grid:
        da=xr.DataArray(pred,dims=("time","lat","lon"),coords={d:grid[d] for d in ("time","lat","lon")},name="tp_mm_day")
        da.attrs.update(units="mm/day",model=name)
        da.to_netcdf(ART / "submission_06_predictions.nc")
        report=export_csv(da,grid,destination,RAW / "sample_submission.csv")
    report.update(model=name,development_selection=choice,uploaded=False,public_score=None,
                  training_targets_end="2022-12",csv_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    save_json(destination.with_suffix(".json"),report)
    print(json.dumps(report,indent=2),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=("evaluate","select","final"))
    args=parser.parse_args()
    globals()[args.stage]()
