"""Bounded spatial-scale and nonlinear experiments against immutable S04."""
import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import xarray as xr
from scipy.ndimage import uniform_filter
from scipy.spatial.distance import cdist, pdist
from sklearn.decomposition import PCA

from .competition import CACHE, RAW, ROOT, REPORT, save_json, score
from .round2 import Features, target_origins
from .round3 import ART as R3, YEARS, seasonal_design
from .round4 import ART as R4, groups, memory
from .submission import export_csv

ART = ROOT / "data/processed/round5"
OUT = REPORT / "round5"
CONFIGS = ("broad16", "detail32", "rbf16")


def spatial(values, config):
    if config != "broad16":
        return values
    # Every time/variable filtered separately; original sampled spacing is 2 degrees.
    fields = values.reshape(len(values), 9, 38, 33)
    return uniform_filter(fields, size=(1, 1, 3, 3), mode="nearest").reshape(len(values), -1)


def predict(f, config, final=False):
    if config == "complement":
        return .5*predict(f,"regional16",final)+.5*predict(f,"rbf16",final)
    if config == "regional16":
        return regional_predict(f, final)
    origins, idx = target_origins(f.year), f.idx
    raw = np.load(R3 / "coarse_weather.npy", mmap_mode="r")[:origins[-1]+1]
    values = spatial(raw, config)
    means = np.stack([values[idx[idx % 12 == m]].mean(axis=0) for m in range(12)])
    train = values[idx]-means[idx % 12]
    scale = np.maximum(train.std(axis=0), 1e-8)
    pca = PCA(n_components=32 if config == "detail32" else 16,
              svd_solver="randomized", random_state=20260914)
    pca.fit(train/scale)
    pc_scale = np.maximum(pca.transform(train/scale).std(axis=0), 1e-8)
    allidx = np.arange(len(values))
    z = pca.transform((values-means[allidx % 12])/scale)/pc_scale
    x = seasonal_design(memory(z, idx, "mean3"), idx)
    xv = seasonal_design(memory(z, origins, "mean3"), origins)
    state = dict(pca=pca, means=means, scale=scale, pc_scale=pc_scale, config=config)
    if config == "rbf16":
        # Fixed data-dependent length scale, estimated only on training inputs.
        bandwidth = max(float(np.median(pdist(x, "sqeuclidean"))), 1e-8)
        kernel = np.exp(-cdist(x, x, "sqeuclidean")/bandwidth)
        kv = np.exp(-cdist(xv, x, "sqeuclidean")/bandwidth)
        # Kernel ridge plus unpenalized intercept, solved as one linear system.
        system = np.block([[kernel + .3*np.eye(len(x)), np.ones((len(x), 1))],
                           [np.ones((1, len(x))), np.zeros((1, 1))]])
        operator = np.linalg.solve(system, np.vstack([np.eye(len(x)), np.zeros((1, len(x)))]))
        mapping = np.column_stack([kv, np.ones(len(kv))]) @ operator
        state.update(train_design=x, bandwidth=bandwidth, penalty=.3)
    else:
        penalty = .3*np.eye(x.shape[1]); penalty[0, 0] = 0
        operator = np.linalg.solve(x.T@x/len(x)+penalty, x.T/len(x))
        mapping = xv@operator
        state.update(penalty=.3)
    pred = f.climo[(origins+1) % 12].copy()
    coefficients = np.empty((operator.shape[0], pred.shape[1])) if final else None
    for start in range(0, pred.shape[1], 5000):
        sl = slice(start, start+5000)
        y = f.tp[idx+1, sl]-f.climo[(idx+1) % 12, sl]
        pred[:, sl] = np.maximum(pred[:, sl]+mapping@y, 0)
        if final:
            coefficients[:, sl] = operator@y
    if final:
        state["coefficients"] = coefficients
        joblib.dump(state, ART / f"final_{config}.joblib")
    return pred.reshape(24, 301, 261)


def regional_predict(f, final=False):
    origins, idx = target_origins(f.year), f.idx
    raw = np.load(R3 / "coarse_weather.npy", mmap_mode="r")[:origins[-1]+1]
    means = np.stack([raw[idx[idx%12==m]].mean(axis=0) for m in range(12)])
    scale = np.maximum((raw[idx]-means[idx%12]).std(axis=0), 1e-8)
    normalized = (raw-means[np.arange(len(raw))%12])/scale
    global_pca = PCA(n_components=8, svd_solver="randomized", random_state=20260914).fit(normalized[idx])
    global_scale = np.maximum(global_pca.transform(normalized[idx]).std(axis=0),1e-8)
    global_z = global_pca.transform(normalized)/global_scale
    pred = f.climo[(origins+1)%12].copy()
    state = dict(means=means, scale=scale, global_pca=global_pca, global_scale=global_scale, regions=[])
    coarse_lat = np.arange(-60,15.01,.25)[::8]
    target_lat = np.repeat(np.arange(-60,15.01,.25),261)
    for band,(lo,hi) in enumerate(((-60,-30),(-30,-10),(-10,15.01))):
        # Fixed 10-degree halo, no target-dependent region selection.
        columns = np.broadcast_to(((coarse_lat>=lo-10)&(coarse_lat<hi+10))[None,:,None],(9,38,33)).ravel()
        cells = np.flatnonzero((target_lat>=lo)&(target_lat<hi))
        regional = normalized[:,columns]
        pca = PCA(n_components=8,svd_solver="randomized",random_state=20260914).fit(regional[idx])
        pc_scale = np.maximum(pca.transform(regional[idx]).std(axis=0),1e-8)
        z = np.column_stack([global_z,pca.transform(regional)/pc_scale])
        x = seasonal_design(memory(z,idx,"mean3"),idx)
        xv = seasonal_design(memory(z,origins,"mean3"),origins)
        penalty = .3*np.eye(x.shape[1]); penalty[0,0]=0
        operator = np.linalg.solve(x.T@x/len(x)+penalty,x.T/len(x))
        coefficients = np.empty((x.shape[1],len(cells))) if final else None
        for start in range(0,len(cells),5000):
            take = cells[start:start+5000]
            y = f.tp[np.ix_(idx+1,take)]-f.climo[np.ix_((idx+1)%12,take)]
            coef = operator@y
            pred[:,take] = np.maximum(pred[:,take]+xv@coef,0)
            if final:
                coefficients[:,start:start+5000]=coef
        if final:
            state["regions"].append(dict(columns=columns,cells=cells,pca=pca,pc_scale=pc_scale,coefficients=coefficients))
    if final:
        joblib.dump(state,ART / "final_regional16.joblib")
    return pred.reshape(24,301,261)


def diagnostic():
    OUT.mkdir(parents=True, exist_ok=True)
    truth = np.load(CACHE / "tp.npy", mmap_mode="r")
    g = groups()
    sums = np.zeros(12); count = np.zeros(12)
    rows = []
    for year in YEARS:
        pred = np.load(R4 / f"{year}_calibrated.npy")
        errors = (pred-truth[target_origins(year)+1]).astype(float)**2
        for k in range(12):
            sums[k] += errors[g == k].sum(); count[k] += (g == k).sum()
        for m in range(24):
            rows.append(dict(month=f"{year+m//12}-{m%12+1:02d}", rmse=float(np.sqrt(errors[m].mean()))))
    report = dict(regions=[dict(group=k, season=("DJF", "MAM", "JJA", "SON")[k//3],
                                latitude_band=("[-60,-30)", "[-30,-10)", "[-10,15]")[k%3],
                                rmse=float(np.sqrt(sums[k]/count[k])), error_share=float(sums[k]/sums.sum())) for k in range(12)],
                  worst_months=sorted(rows, key=lambda r:r["rmse"], reverse=True)[:10])
    save_json(OUT / "diagnostics.json", report)
    print(json.dumps(report, indent=2), flush=True)


def evaluate(configs=CONFIGS, append=False):
    ART.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
    cal = json.loads((REPORT / "round4/calibration.json").read_text())
    g = groups()
    for i, year in enumerate(YEARS):
        f = Features(year)
        truth = f.tp[target_origins(year)+1].reshape(24, 301, 261)
        ref = np.load(R4 / f"{year}_calibrated.npy")
        old = np.load(R4 / f"{year}_mean3_0.3.npy")
        w = np.asarray(cal["leave_block_out_weights"][i])[g, 1]
        rows = json.loads((OUT / f"{year}.json").read_text()) if append else [dict(model="submission04", **score(ref, truth))]
        for config in configs:
            new = predict(f, config)
            np.save(ART / f"{year}_{config}.npy", new)
            for fraction in (.5, 1.):
                pred = np.maximum(ref+fraction*w*(new-old), 0)
                row = dict(model=f"{config}_{fraction:g}", **score(pred, truth))
                rows.append(row)
                np.save(ART / f"{year}_{row['model']}.npy", pred)
                print(year, row["model"], row["rmse"], flush=True)
        save_json(OUT / f"{year}.json", rows)


def select():
    rows = {y:json.loads((OUT / f"{y}.json").read_text()) for y in YEARS}
    ranking = []
    for name in [r["model"] for r in rows[YEARS[0]]]:
        candidates = [next(r for r in rows[y] if r["model"] == name) for y in YEARS]
        ranking.append(dict(model=name, rmse=float(np.sqrt(np.mean([r["rmse"]**2 for r in candidates]))),
                            second_year_rmse=float(np.sqrt(np.mean([r["year2_rmse"]**2 for r in candidates]))),
                            folds_improved=sum(r["rmse"] < rows[y][0]["rmse"] for y,r in zip(YEARS,candidates)),
                            years_improved=sum(r[k] < rows[y][0][k] for y,r in zip(YEARS,candidates)
                                               for k in ("year1_rmse", "year2_rmse"))))
    ranking.sort(key=lambda r:r["rmse"])
    ref = next(r for r in ranking if r["model"] == "submission04")
    eligible = [r for r in ranking if r["rmse"] < ref["rmse"] and r["second_year_rmse"] < ref["second_year_rmse"]
                and r["folds_improved"] >= 3 and r["years_improved"] >= 6]
    report = dict(selected=eligible[0]["model"] if eligible else "submission04", ranking=ranking,
                  holdout_evaluated=False, caveat="Retrospective development selection, inherited cross-fitted S04 weights. Not an independent test.")
    save_json(OUT / "selection.json", report)
    print(json.dumps(report, indent=2), flush=True)


def regional():
    evaluate(("regional16",), append=True)


def complement():
    truth = np.load(CACHE / "tp.npy",mmap_mode="r")
    for year in YEARS:
        pred = .5*np.load(ART / f"{year}_regional16_0.5.npy")+.5*np.load(ART / f"{year}_rbf16_0.5.npy")
        np.save(ART / f"{year}_complement_0.5.npy",pred)
        rows = json.loads((OUT / f"{year}.json").read_text())
        rows = [r for r in rows if r["model"] != "complement_0.5"]
        rows.append(dict(model="complement_0.5",**score(pred,truth[target_origins(year)+1])))
        save_json(OUT / f"{year}.json",rows)


def final(experimental=False):
    choice = json.loads((OUT / "selection.json").read_text())
    promoted = choice["selected"] != "submission04"
    if not promoted and not experimental:
        raise RuntimeError("No qualifying candidate. Do not submit a duplicate.")
    selected = choice["selected"] if promoted else choice["ranking"][0]["model"]
    if selected == "submission04":
        raise RuntimeError("No numerical improvement to export")
    path = ROOT / "submissions/submission_05.csv"
    if path.exists():
        raise FileExistsError(path)
    config, fraction = selected.split("_")
    f = Features(2023, final=True)
    new = predict(f, config, final=True)
    oldmodel = joblib.load(R4 / "final_mean3.joblib")
    origins = target_origins(2023); take = np.arange(origins[-1]+1)
    raw = np.load(R3 / "coarse_weather.npy", mmap_mode="r")[take]
    z = oldmodel["pca"].transform((raw-oldmodel["monthly_means"][take%12])/oldmodel["scale"])/oldmodel["pc_scale"]
    old = np.maximum(f.climo[(origins+1)%12]+seasonal_design(memory(z, origins, "mean3"), origins)@oldmodel["coefficients"][.3],0).reshape(24,301,261)
    cal = json.loads((REPORT / "round4/calibration.json").read_text())
    weights = np.asarray(cal["final_weights"])[groups(),1]
    with xr.open_dataset(R4 / "submission_04_predictions.nc") as ds:
        pred = np.maximum(ds.tp_mm_day.values+float(fraction)*weights*(new-old),0)
    with xr.open_dataset(RAW / "teste_features.nc") as grid:
        da = xr.DataArray(pred,dims=("time","lat","lon"),coords={d:grid[d] for d in ("time","lat","lon")},name="tp_mm_day")
        da.attrs.update(units="mm/day",model=selected)
        da.to_netcdf(ART / "submission_05_predictions.nc")
        report = export_csv(da,grid,path,RAW / "sample_submission.csv")
    report.update(model=selected,development_selection=choice,promoted=promoted,
                  experimental=not promoted, warning=None if promoted else "Failed stability gate: only 4/8 years improved. S04 remains reference.",uploaded=False,public_score=None,
                  training_targets_end="2022-12",csv_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    save_json(path.with_suffix(".json"),report)
    print(json.dumps(report,indent=2),flush=True)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=("diagnostic","evaluate","regional","complement","select","final"))
    parser.add_argument("--experimental",action="store_true",help="Export top numerical candidate without claiming promotion")
    args=parser.parse_args()
    if args.stage == "final":
        final(args.experimental)
    else:
        globals()[args.stage]()
