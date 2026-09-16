"""Compare isolated retraining to original immutable S11; read-only to models."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr

ROOT=Path(__file__).resolve().parents[1]


def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'delivery/s11/verification')
    args=parser.parse_args(); output=args.output
    checks={}
    for name,source in {
        's02':'round9/2023_s02.npy','modes':'round9/2023_modes.npy',
        'local18':'round9/2023_local18.npy','pls16':'round9/2023_pls16.npy',
        'fine32':'round11/2023_fine32.npy',
    }.items():
        a=np.load(output/f'{name}.npy'); b=np.load(ROOT/'data/processed'/source)
        checks[name]=dict(max_abs_difference=float(np.max(np.abs(a.astype(float)-b))),
                          rms_difference=float(np.sqrt(np.mean((a.astype(float)-b)**2))),
                          exact=bool(np.array_equal(a,b)))
    with xr.open_dataset(output/'s11_reproduction.nc') as ds:
        actual=ds.tp_mm_day.values.copy()
    with xr.open_dataset(ROOT/'data/processed/round15_experimental/submission_11_predictions.nc') as ds:
        original=ds.tp_mm_day.values.copy()
    delta=actual-original
    csv=output/'s11_reproduction.csv'; frame=pd.read_csv(csv)
    official=pd.read_csv(ROOT/'data/raw/sample_submission.csv')
    expected=json.loads((ROOT/'submissions/submission_11.json').read_text())['csv_sha256']
    result=dict(components=checks,full_prediction_max_abs_difference=float(np.max(abs(delta))),
                full_prediction_rms_difference=float(np.sqrt(np.mean(delta**2))),
                original_csv_sha256=expected,reproduced_csv_sha256=digest(csv),
                exact_csv=digest(csv)==expected,exact_netcdf_values=bool(np.array_equal(actual,original)),
                rows=len(frame),official_id_order=frame.id.equals(official.id),
                numeric_tolerance=1e-5,passed=bool(np.max(abs(delta))<=1e-5),
                scope='Base models refitted from official raw-derived arrays; fixed final calibration from archived OOF sufficient statistics',
                new_candidate=False,uploaded=False)
    (output/'reproduction_comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
    assert list(frame)==['id','tp_mm_day'] and len(frame)==1885464 and frame.id.is_unique
    assert result['official_id_order'] and np.isfinite(frame.tp_mm_day).all() and (frame.tp_mm_day>=0).all()
    assert digest(ROOT/'submissions/submission_11.csv')==expected
    assert result['passed'], 'Retraining does not reproduce original S11 within declared tolerance'


if __name__=='__main__': main()
