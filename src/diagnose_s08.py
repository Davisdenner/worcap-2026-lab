"""Post-submission diagnostic only: no fitting, model edits, or CSV creation."""
import hashlib
import json

import joblib
import numpy as np
import xarray as xr

from .competition import ROOT, REPORT, CACHE, dates, training_pairs, fit_climatology, save_json
from .round3 import YEARS, seasonal_design
from .round4 import memory, groups
from .round7 import ocean_history
from .round8 import parse_psl

OUT=REPORT / "s08_diagnostic"
ART=ROOT / "data/processed"
EXT=ROOT / "data/external"


def array_summary(x):
    x=np.asarray(x,dtype=float)
    return dict(mean=float(x.mean()),rms=float(np.sqrt(np.mean(x*x))),
                abs_p95=float(np.quantile(abs(x),.95)),abs_max=float(abs(x).max()))


def changes(reference,candidate,truth=None):
    delta=np.asarray(candidate,dtype=float)-reference
    result=array_summary(delta)
    if truth is not None:
        error=np.asarray(reference,dtype=float)-truth
        q=float(np.mean(delta*delta)); b=float(np.mean(error*delta))
        result.update(reference_rmse=float(np.sqrt(np.mean(error*error))),
                      candidate_rmse=float(np.sqrt(np.mean((error+delta)**2))),
                      delta_mse=2*b+q,correction_energy=q,error_correction_cross_mean=b)
    return result


def sources_and_matrices():
    times=dates(); idx=training_pairs(times,"2023-01-01")
    raw=np.load(ART / "round3/coarse_weather.npy",mmap_mode="r")
    allidx=np.arange(len(raw)); origins=np.arange(995,1019)
    s7=joblib.load(ART / "round7/final_ocean.joblib")
    s8=joblib.load(ART / "round8/final_atlantic.joblib")
    hashes={}
    for name in ("ersst5.nino.mth.91-20.ascii","tna.data","tsa.data"):
        path=EXT / name
        metadata=json.loads(path.with_suffix(".json").read_text())
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest!=metadata["sha256"]:
            raise ValueError(f"External snapshot changed: {name}")
        hashes[name]=digest
    pacific=np.full((len(raw),4),np.nan)
    table=np.loadtxt(EXT / "ersst5.nino.mth.91-20.ascii",skiprows=1)
    for row in table:
        j=(int(row[0])-1940)*12+int(row[1])-1
        if 0<=j<1018:
            pacific[j]=row[[2,4,6,8]]
    atlantic=np.column_stack([parse_psl((EXT / f"{n}.data").read_text(),len(raw)) for n in ("tna","tsa")])
    designs={}
    external={}
    for number,state in ((7,s7),(8,s8)):
        z=state["pca"].transform((raw-state["means"][allidx%12])/state["scale"])/state["pc_scale"]
        pmean=state["ocean_means"] if number==7 else state["pacific_means"]
        p=pacific-pmean[allidx%12]
        trainparts=[memory(z,idx,"mean3"),ocean_history(p,idx)/state["ocean_scale"]]
        validparts=[memory(z,origins,"mean3"),ocean_history(p,origins)/state["ocean_scale"]]
        if number==8:
            a=atlantic-state["atlantic_means"][allidx%12]
            at=ocean_history(a,idx)/state["atlantic_scale"]
            av=ocean_history(a,origins)/state["atlantic_scale"]
            external=dict(atlantic_train=at,atlantic_valid=av,
                          combined_train=np.column_stack([trainparts[1],at]),
                          combined_valid=np.column_stack([validparts[1],av]))
            trainparts.append(at); validparts.append(av)
        designs[number]=(seasonal_design(np.column_stack(trainparts),idx),
                         seasonal_design(np.column_stack(validparts),origins),state)
    return idx,origins,designs,external,hashes


def novelty(train,valid):
    center=train.mean(axis=0)
    covariance=np.cov(train,rowvar=False,bias=True)+.05*np.eye(train.shape[1])
    inv=np.linalg.inv(covariance)
    def distance(values):
        z=values-center
        return np.sqrt(np.einsum("ti,ij,tj->t",z,inv,z))
    td,vd=distance(train),distance(valid)
    outside=(valid<train.min(axis=0))|(valid>train.max(axis=0))
    return dict(training_max_distance=float(td.max()),training_p95_distance=float(np.quantile(td,.95)),
                monthly_distance=vd.tolist(),outside_training_range_count=outside.sum(axis=1).tolist(),
                months_above_training_max=int((vd>td.max()).sum()))


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    idx,origins,designs,external,hashes=sources_and_matrices()
    with xr.open_dataset(ART / "round7/submission_07_predictions.nc") as ds:
        reference=ds.tp_mm_day.values.copy()
    with xr.open_dataset(ART / "round8/submission_08_predictions.nc") as ds:
        candidate=ds.tp_mm_day.values.copy()
    tp=np.load(CACHE / "tp.npy",mmap_mode="r")
    climo=fit_climatology(tp,dates(),"2023-01-01",60).reshape(12,-1)
    base=climo[(origins+1)%12]
    component_checks={}
    for number in (7,8):
        _,xv,state=designs[number]
        reconstructed=np.maximum(base+xv@state["coefficients"][.3],0).astype(np.float32).reshape(24,301,261)
        file=ART / ("round7/final_ocean_0.3.npy" if number==7 else "round8/final_atlantic_0.3.npy")
        saved=np.load(file)
        difference=float(np.max(abs(reconstructed-saved)))
        if difference>2e-5:
            raise ValueError(f"S{number} component reconstruction failed: {difference}")
        component_checks[str(number)]=difference
    old=np.load(ART / "round7/final_ocean_0.3.npy")
    new=np.load(ART / "round8/final_atlantic_0.3.npy")
    cal=json.loads((REPORT / "round4/calibration.json").read_text())
    weights=np.asarray(cal["final_weights"])[groups(),1]
    reconstructed=np.maximum(reference+weights*(new-old),0)
    blend_error=float(np.max(abs(reconstructed-candidate)))
    if blend_error>1e-10:
        raise ValueError("S08 blend reconstruction failed")
    report=dict(audit=dict(component_max_abs_error=component_checks,blend_max_abs_error=blend_error,
                          external_hashes=hashes,latest_atmospheric_origin="2024-11",latest_ocean_origin="2024-10"),
                prediction_changes=dict(public2023=changes(reference[:12],candidate[:12]),
                                        private2024_unknown_error=changes(reference[12:],candidate[12:])),
                monthly_test_changes=[],historical_years=[],historical_months=[],regional_test_changes=[])
    delta=candidate-reference
    for i in range(24):
        report["monthly_test_changes"].append(dict(target=f"{2023+i//12}-{i%12+1:02d}",**changes(reference[i],candidate[i])))
    for year in (*YEARS,2021):
        if year==2021:
            r=np.load(ART / "round8/holdout2021_submission07.npy")
            p=np.load(ART / "round8/holdout2021_submission08.npy")
        else:
            r=np.load(ART / f"round7/{year}_ocean_0.3_1.npy")
            p=np.load(ART / f"round8/{year}_atlantic_0.3_1.npy")
        first=(year-1940)*12
        for k in range(2):
            sl=slice(k*12,(k+1)*12)
            report["historical_years"].append(dict(year=year+k,**changes(r[sl],p[sl],tp[first+k*12:first+(k+1)*12])))
        for k in range(24):
            report["historical_months"].append(dict(target=f"{year+k//12}-{k%12+1:02d}",**changes(r[k],p[k],tp[first+k])))
    g=groups()
    for year_index in range(2):
        d=delta[year_index*12:(year_index+1)*12]
        for band in range(3):
            take=(g[year_index*12:(year_index+1)*12]%3)==band
            report["regional_test_changes"].append(dict(year=2023+year_index,latitude_band=("[-60,-30)","[-30,-10)","[-10,15]")[band],
                                                      correction_energy_share=float(np.sum(d[take]**2)/np.sum(d**2)),**array_summary(d[take])))
    report["atlantic_novelty"]=novelty(external["atlantic_train"],external["atlantic_valid"])
    report["pacific_atlantic_novelty"]=novelty(external["combined_train"],external["combined_valid"])
    labels=["TNA latest","TSA latest","TNA trailing3","TSA trailing3"]
    train,valid=external["atlantic_train"],external["atlantic_valid"]
    report["atlantic_standardized_features"]=[dict(feature=label,train_min=float(train[:,j].min()),train_max=float(train[:,j].max()),
                                                  test_values=valid[:,j].tolist()) for j,label in enumerate(labels)]
    # Aggregate diagnostic, not a new submission or a fitted leaderboard weight.
    observations=json.loads((REPORT / "leaderboard_observations.json").read_text())["observations"]
    observed={o["submission_file"]:o["public_rmse"] for o in observations}
    s7,s8=observed["submissions/submission_07.csv"],observed["submissions/submission_08.csv"]
    q=float(np.mean(np.asarray(delta[:12],float)**2))
    difference=s8*s8-s7*s7
    lower=(s8-5e-6)**2-(s7+5e-6)**2-q
    upper=(s8+5e-6)**2-(s7-5e-6)**2-q
    report["public_correction_diagnostic"]=dict(s07_rmse=s7,s08_rmse=s8,mse_difference=difference,
            correction_energy=q,error_cross_term_twice=difference-q,rounding_interval=[lower,upper],
            positive_convex_blends_worse_than_s07=bool(lower>0),
            assumptions="Public score is unweighted RMSE on every 2023 grid cell, same targets for S07/S08, rounded to five decimals as supplied. No clipping or other changes to blends.",
            formula="MSE(S07 + a*(S08-S07)) = MSE(S07) + a*(MSE(S08)-MSE(S07)-mean(delta^2)) + a^2*mean(delta^2)",
            limitation="Cannot locate actual 2023 errors by region/month or infer private 2024 score from aggregate public feedback")
    # Diagnostic attribution: direct Atlantic columns at zero=train monthly mean.
    _,xv,state=designs[8]
    atlantic_columns=np.concatenate([np.arange(43,47),np.arange(87,91),np.arange(131,135)])
    direct=xv[:,atlantic_columns]@state["coefficients"][.3][atlantic_columns]
    direct=direct.reshape(24,301,261)*weights
    report["direct_atlantic_term_before_clipping"]=dict(public2023=array_summary(direct[:12]),private2024=array_summary(direct[12:]),
            caveat="Diagnostic contribution only; adding correlated indices also refits all original coefficients. Not causal attribution or a proposed model.")
    save_json(OUT / "diagnostic.json",report)
    concise={k:report[k] for k in ("audit","prediction_changes","public_correction_diagnostic","regional_test_changes","atlantic_novelty","pacific_atlantic_novelty")}
    concise["historical_years"]=report["historical_years"]
    print(json.dumps(concise,indent=2),flush=True)


if __name__=="__main__":
    main()
