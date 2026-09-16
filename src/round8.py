"""Atlantic SST indices as a bounded complement to S07's Pacific model."""
import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import xarray as xr
from sklearn.decomposition import PCA

from .competition import ROOT, REPORT, RAW, save_json, score
from .round2 import Features, target_origins
from .round3 import ART as R3, YEARS, seasonal_design
from .round4 import memory, groups
from .round7 import ART as R7, ocean_history
from .submission import export_csv

ART=ROOT / "data/processed/round8"
OUT=REPORT / "round8"
EXTERNAL=ROOT / "data/external"


def parse_psl(text,length):
    lines=text.splitlines()
    first,last=map(int,lines[0].split())
    result=np.full(length,np.nan)
    seen=set()
    for line in lines[1:]:
        fields=line.split()
        if len(fields)!=13:
            continue
        try:
            year=int(fields[0])
        except ValueError:
            continue
        if not first<=year<=last or year in seen:
            raise ValueError("Invalid or duplicate PSL year")
        seen.add(year)
        values=np.array(fields[1:],dtype=float)
        for month,value in enumerate(values):
            position=(year-1940)*12+month
            if 0<=position<min(length,(2024-1940)*12+10):
                result[position]=value if np.isfinite(value) and abs(value)<10 else np.nan
    if seen!=set(range(first,last+1)):
        raise ValueError("Missing PSL year")
    return result


def monthly_center(values,fit_origins):
    """fit_origins are observation dates, never target or future dates."""
    values=np.asarray(values)
    if not np.isfinite(values[fit_origins]).all():
        raise ValueError("Missing training observations")
    means=np.stack([values[fit_origins[fit_origins%12==m]].mean(axis=0) for m in range(12)])
    return values-means[np.arange(len(values))%12],means


def design(f,atlantic=True):
    idx,origins=f.idx,target_origins(f.year)
    raw=np.load(R3 / "coarse_weather.npy",mmap_mode="r")[:origins[-1]+1]
    centered,means=monthly_center(raw,idx)
    scale=np.maximum(centered[idx].std(axis=0),1e-8)
    pca=PCA(n_components=16,svd_solver="randomized",random_state=20260914).fit(centered[idx]/scale)
    pc_scale=np.maximum(pca.transform(centered[idx]/scale).std(axis=0),1e-8)
    z=pca.transform(centered/scale)/pc_scale
    table=np.loadtxt(EXTERNAL / "ersst5.nino.mth.91-20.ascii",skiprows=1)
    pacific=np.full((len(raw),4),np.nan)
    for row in table:
        j=(int(row[0])-1940)*12+int(row[1])-1
        if 0<=j<min(len(raw),(2024-1940)*12+10):
            pacific[j]=row[[2,4,6,8]]
    pacific,pacific_means=monthly_center(pacific,idx-1)
    ox,ov=ocean_history(pacific,idx),ocean_history(pacific,origins)
    ocean_scale=np.maximum(ox.std(axis=0),1e-8)
    parts=[memory(z,idx,"mean3"),ox/ocean_scale]
    vparts=[memory(z,origins,"mean3"),ov/ocean_scale]
    state=dict(pca=pca,means=means,scale=scale,pc_scale=pc_scale,
               pacific_means=pacific_means,ocean_scale=ocean_scale)
    if atlantic:
        values=np.column_stack([parse_psl((EXTERNAL / f"{index}.data").read_text(),len(raw)) for index in ("tna","tsa")])
        values,atlantic_means=monthly_center(values,idx-1)
        ax,av=ocean_history(values,idx),ocean_history(values,origins)
        atlantic_scale=np.maximum(ax.std(axis=0),1e-8)
        parts.append(ax/atlantic_scale); vparts.append(av/atlantic_scale)
        state.update(atlantic_means=atlantic_means,atlantic_scale=atlantic_scale)
    return seasonal_design(np.column_stack(parts),idx),seasonal_design(np.column_stack(vparts),origins),state


def predict(f,atlantic=True,final=False):
    x,xv,state=design(f,atlantic)
    idx,origins=f.idx,target_origins(f.year)
    base=f.climo[(origins+1)%12]
    penalties=(.3,3.) if atlantic else (.3,)
    predictions={a:base.copy() for a in penalties}
    coefficients={a:np.empty((x.shape[1],base.shape[1])) for a in penalties} if final else None
    xx=x.T@x/len(x)
    for start in range(0,base.shape[1],5000):
        sl=slice(start,start+5000)
        y=f.tp[idx+1,sl]-f.climo[(idx+1)%12,sl]
        xy=x.T@y/len(x)
        for a in penalties:
            penalty=a*np.eye(x.shape[1]); penalty[0,0]=0
            coef=np.linalg.solve(xx+penalty,xy)
            predictions[a][:,sl]=np.maximum(base[:,sl]+xv@coef,0)
            if final:
                coefficients[a][:,sl]=coef
    if final:
        state["coefficients"]=coefficients
        joblib.dump(state,ART / "final_atlantic.joblib")
    return {a:p.reshape(24,301,261) for a,p in predictions.items()}


def evaluate():
    ART.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
    cal=json.loads((REPORT / "round4/calibration.json").read_text())
    for i,year in enumerate(YEARS):
        f=Features(year)
        truth=f.tp[target_origins(year)+1].reshape(24,301,261)
        ref=np.load(R7 / f"{year}_ocean_0.3_1.npy")
        old=np.load(R7 / f"{year}_ocean_0.3.npy")
        if i==0:
            reproduced=predict(f,atlantic=False)[.3]
            np.testing.assert_allclose(reproduced,old,rtol=0,atol=2e-5)
            save_json(OUT / "reproduction.json",dict(year=year,max_absolute_error=float(np.max(abs(reproduced-old)))))
        weights=np.asarray(cal["leave_block_out_weights"][i])[groups(),1]
        rows=[dict(model="submission07",**score(ref,truth))]
        for a,new in predict(f).items():
            np.save(ART / f"{year}_atlantic_{a:g}.npy",new)
            for fraction in (.5,1.):
                pred=np.maximum(ref+fraction*weights*(new-old),0)
                name=f"atlantic_{a:g}_{fraction:g}"
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
    ref=next(r for r in ranking if r["model"]=="submission07")
    eligible=[r for r in ranking if r["rmse"]<ref["rmse"] and r["second_year_rmse"]<ref["second_year_rmse"]
              and r["folds_improved"]>=3 and r["years_improved"]>=6]
    report=dict(selected=eligible[0]["model"] if eligible else "submission07",ranking=ranking,holdout_evaluated=False,
                caveat="Reused retrospective development blocks and cross-fitted blend weights; not independent test.")
    save_json(OUT / "selection.json",report)
    print(json.dumps(report,indent=2),flush=True)


def holdout():
    """One-shot 2021-2022 assessment with the candidate frozen beforehand."""
    choice=json.loads((OUT / "selection.json").read_text())
    name=choice["selected"]
    if name=="submission07":
        raise RuntimeError("No qualified development candidate")
    result_path=OUT / "holdout_2021_2022.json"
    protocol_path=OUT / "holdout_protocol.json"
    if result_path.exists():
        raise FileExistsError("Holdout has already been scored; do not tune on it")
    protocol=dict(candidate=name,reference="submission07",years=[2021,2022],
                  cutoff="2021-01-01",criterion="Lower pooled RMSE and lower RMSE in both individual years than frozen S07",
                  no_post_holdout_parameter_tuning=True,blend_weights="round4 final_weights fitted on development 2013-2020 only")
    if protocol_path.exists():
        if json.loads(protocol_path.read_text())!=protocol:
            raise RuntimeError("Cannot change the locked holdout protocol")
    else:
        save_json(protocol_path,protocol)
    from .round2 import trees,ridge
    from .round6 import local_memory
    from .round7 import ocean_model
    f=Features(2021)
    pieces={}
    jobs={"trees_local":lambda:trees(f,False)["local_150"],
          "trees_context":lambda:trees(f,True,(300,))["context_300"],
          "ridge":lambda:ridge(f),"local_memory":lambda:local_memory(f)[.3],
          "pacific":lambda:ocean_model(f)[.3],
          "atlantic":lambda:predict(f)[float(name.split("_")[1])]}
    for key,job in jobs.items():
        path=ART / f"holdout2021_{key}.npy"
        if path.exists():
            pieces[key]=np.load(path)
        else:
            print("Holdout fitting",key,flush=True)
            pieces[key]=job()
            np.save(path,pieces[key])
    base=f.climo[(target_origins(2021)+1)%12].reshape(24,301,261)
    s02=.5*pieces["trees_context"]+.25*pieces["trees_local"]+.125*pieces["ridge"]+.125*base
    cal=json.loads((REPORT / "round4/calibration.json").read_text())
    weights=np.asarray(cal["final_weights"])[groups()].transpose(3,0,1,2)
    reference=weights[0]*s02+weights[1]*pieces["pacific"]+weights[2]*pieces["local_memory"]
    fraction=float(name.split("_")[2])
    candidate=np.maximum(reference+fraction*weights[1]*(pieces["atlantic"]-pieces["pacific"]),0)
    np.save(ART / "holdout2021_submission07.npy",reference)
    np.save(ART / "holdout2021_submission08.npy",candidate)
    # Read and score reserved labels only after predictions and protocol are fixed.
    truth=f.tp[target_origins(2021)+1].reshape(24,301,261)
    ref_score,new_score=score(reference,truth),score(candidate,truth)
    passed=all(new_score[k]<ref_score[k] for k in ("rmse","year1_rmse","year2_rmse"))
    report=dict(protocol=protocol,reference=ref_score,candidate=new_score,passed=bool(passed),
                warning="2021-2022 is now consumed as final validation, no longer an untouched holdout")
    save_json(result_path,report)
    print(json.dumps(report,indent=2),flush=True)


def final():
    choice=json.loads((OUT / "selection.json").read_text()); name=choice["selected"]
    if name=="submission07":
        raise RuntimeError("No candidate passed stability gate")
    holdout_report=json.loads((OUT / "holdout_2021_2022.json").read_text())
    if not holdout_report["passed"] or holdout_report["protocol"]["candidate"]!=name:
        raise RuntimeError("Candidate failed or changed after the locked holdout")
    destination=ROOT / "submissions/submission_08.csv"
    if destination.exists():
        raise FileExistsError(destination)
    _,a,fraction=name.split("_"); a,fraction=float(a),float(fraction)
    f=Features(2023,final=True)
    new=predict(f,final=True)[a]
    np.save(ART / f"final_atlantic_{a:g}.npy",new)
    old=np.load(R7 / "final_ocean_0.3.npy")
    cal=json.loads((REPORT / "round4/calibration.json").read_text())
    weights=np.asarray(cal["final_weights"])[groups(),1]
    with xr.open_dataset(R7 / "submission_07_predictions.nc") as ds:
        pred=np.maximum(ds.tp_mm_day.values+fraction*weights*(new-old),0)
    with xr.open_dataset(RAW / "teste_features.nc") as grid:
        da=xr.DataArray(pred,dims=("time","lat","lon"),coords={d:grid[d] for d in ("time","lat","lon")},name="tp_mm_day")
        da.attrs.update(units="mm/day",model=name)
        da.to_netcdf(ART / "submission_08_predictions.nc")
        report=export_csv(da,grid,destination,RAW / "sample_submission.csv")
    report.update(model=name,development_selection=choice,final_holdout=holdout_report,uploaded=False,public_score=None,training_targets_end="2022-12",
                  csv_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  external_sources=[json.loads((EXTERNAL / file).read_text()) for file in ("ersst5.nino.mth.91-20.json","tna.json","tsa.json")])
    save_json(destination.with_suffix(".json"),report)
    print(json.dumps(report,indent=2),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=("evaluate","select","holdout","final"))
    args=parser.parse_args(); globals()[args.stage]()
