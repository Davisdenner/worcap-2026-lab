"""Explicitly authorized experimental S11 export; original R15 gates unchanged."""
from __future__ import annotations

import argparse
import importlib.metadata
import numpy as np
import xarray as xr

from . import round15 as r
from .competition import ROOT, RAW, CACHE, save_json
from .submission import export_csv

ART = ROOT / 'data/processed/round15_experimental'
OUT = ROOT / 'reports/competition/round15_experimental'
PROTOCOL = ROOT / 'experiments/ROUND15_EXPERIMENTAL.md'
NAME = 'joint1'
S10_HASH = '57862493c62936b291c03cff3bd4c53fd486ab38a08108f908a8f74b5aada46e'


def run(user_authorized=False):
    if not user_authorized:
        raise PermissionError('Explicit experimental authorization required')
    destination = ROOT / 'submissions/submission_11.csv'
    for path in (destination, destination.with_suffix('.json'), ART / 'submission_11_predictions.nc'):
        if path.exists():
            raise FileExistsError(path)
    frozen = r.locked()
    selection = r.r9.read(r.OUT / 'selection.json')
    chosen = selection['ranking'][0]
    if chosen['model'] != NAME or chosen['passed'] or selection['selected'] is not None:
        raise RuntimeError('Expected original failed joint1 selection')
    protected = [r.OUT / 'selection.json', ROOT / 'submissions/submission_10.csv',
                 ROOT / 'submissions/submission_10.json']
    before_hashes = {str(p): r.r9.digest(p) for p in protected}
    if before_hashes[str(protected[1])] != S10_HASH:
        raise RuntimeError('S10 reference changed')
    ART.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    # Diagnostic only: same candidate, no post-result tuning or reselection.
    pred = r.candidates(2021, (NAME,))[NAME]
    ref = r.r12.baseline(2021)
    truth = np.load(CACHE / 'tp.npy', mmap_mode='r')[r.target_origins(2021) + 1]
    old, new = r.r9.metrics(ref, truth, ref), r.r9.metrics(pred, truth, ref)
    confirmation = dict(candidate=NAME, reference=old, result=new,
                        previously_consumed_period=True, diagnostic_only=True,
                        no_post_confirmation_tuning=True,
                        passed=new['rmse'] <= old['rmse'] * .999 and
                        all(new[k] < old[k] for k in ('year1_rmse', 'year2_rmse')))
    save_json(OUT / 'confirmation.json', confirmation)
    print('REUSED DIAGNOSTIC', old['rmse'], new['rmse'], flush=True)
    del pred, ref, truth

    pred = r.candidates(2023, (NAME,))[NAME]
    pieces, ref, prior = r.components(2023)
    weights_record = r.r9.read(r.ART / '2023_joint1_weights.json')
    weights = np.asarray(weights_record['weights'])
    np.testing.assert_array_equal(pred, r.combine(pieces, weights))
    if weights_record['last_calibration_target'] != '2022-12':
        raise RuntimeError('Unexpected calibration endpoint')
    historical = chosen['historical_correction_rms']
    rms = [float(np.sqrt(np.mean((pred[s] - ref[s]) ** 2)))
           for s in (slice(0, 12), slice(12, 24))]
    shift = dict(historical_rms=historical, public2023_rms=rms[0],
                 private2024_rms=rms[1], passed=all(v <= 2 * historical for v in rms))
    save_json(OUT / 'test_shift.json', shift)
    nc_path = ART / 'submission_11_predictions.nc'
    with xr.open_dataset(RAW / 'teste_features.nc') as grid:
        da = xr.DataArray(pred, dims=('time', 'lat', 'lon'),
                          coords={d: grid[d] for d in ('time', 'lat', 'lon')}, name='tp_mm_day')
        da.attrs.update(units='mm/day', model=NAME, official_only='true', experimental='true')
        da.to_netcdf(nc_path)
        metadata = export_csv(da, grid, destination, RAW / 'sample_submission.csv')
    with xr.open_dataset(nc_path) as ds:
        np.testing.assert_array_equal(ds.tp_mm_day.values, r.combine(pieces, weights))
    if {str(p): r.r9.digest(p) for p in protected} != before_hashes:
        raise RuntimeError('Protected reference or selection changed')
    metadata.update(experiment='round15_experimental', model=NAME, base_model='S10',
                    experimental=True, user_authorized=True, automatic_promotion_passed=False,
                    authorization='Explicit user request to export best failed R15 candidate; no upload',
                    official_data_only=True, external_sources=[], public_score=None, uploaded=False,
                    csv_sha256=r.r9.digest(destination), training_targets_end='2022-12',
                    protocol=frozen, experimental_protocol_sha256=r.r9.digest(PROTOCOL),
                    exporter_sha256=r.r9.digest(ROOT / 'src/round15_experimental.py'),
                    audit_sha256=r.r9.digest(r.OUT / 'audit.json'), selection=selection,
                    confirmation=confirmation, test_shift=shift, final_weights=weights_record,
                    artifact_hashes={p.name:r.r9.digest(p) for p in r.ART.glob('2023_*')},
                    predictions_sha256=r.r9.digest(nc_path), protected_hashes=before_hashes,
                    versions={p:importlib.metadata.version(p) for p in
                              ('numpy', 'scipy', 'scikit-learn', 'xarray', 'pandas')})
    save_json(destination.with_suffix('.json'), metadata)
    save_json(OUT / 'verification.json', dict(
        full_prediction_reconstruction=True, netcdf_roundtrip_exact=True,
        official_template_verified=True, s10_and_selection_unchanged=True,
        final_calibration_end='2022-12', automatic_promotion_passed=False,
        experimental_user_authorized=True, uploaded=False, csv_sha256=metadata['csv_sha256']))
    print('EXPORTED', destination, 'SHIFT', shift, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--user-authorized', action='store_true')
    run(parser.parse_args().user_authorized)
