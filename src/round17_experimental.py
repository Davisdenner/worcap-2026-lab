"""S12 autorizada: dispensar só o ganho de desenvolvimento; demais gates obrigatórios."""
import argparse
import importlib.metadata
import json
import sys
from pathlib import Path
from . import round17 as r
import numpy as np
import xarray as xr
from .submission import export_csv

NAME='meta15_a0.25'
ART=r.ROOT/'data/processed/round17_experimental'
OUT=r.REPORT/'round17_experimental'
PROTOCOL=r.ROOT/'experiments/ROUND17_EXPERIMENTAL.md'
S11_HASH='8b871e4fa982045ee1c59abb19ff9e4954444aaf96de22052daa3de22e64b26f'
S10_HASH='57862493c62936b291c03cff3bd4c53fd486ab38a08108f908a8f74b5aada46e'


def confirmation_passes(before,after):
    return bool(after['rmse']<=before['rmse']*.999 and
                all(after[k]<before[k] for k in ('year1_rmse','year2_rmse')))


def shift_passes(rms,historical):
    return bool(len(rms)==2 and historical>0 and
                all(np.isfinite(v) and 0<=v<=2*historical for v in rms))


def authorize(user_authorized):
    if not user_authorized: raise PermissionError('Autorização experimental explícita obrigatória')
    frozen=r.locked()
    selection=r.read(r.OUT/'selection.json')
    chosen=next(row for row in selection['ranking'] if row['model']==NAME)
    records={y:r.read(r.OUT/f'{y}.json') for y in r.DEV}
    ref_second=float(np.sqrt(np.mean(np.asarray([records[y][0]['monthly_rmse'][12:] for y in r.DEV])**2)))
    if (selection['selected'] is not None or chosen['passed'] or
        selection['minimum_relative_gain']!=.003 or r.CONFIGS[NAME]!=(15,.25) or
        not 0<chosen['relative_gain']<.003):
        raise ValueError('Estado da candidata diferente da exceção autorizada')
    if not (chosen['second_year_rmse']<ref_second and chosen['blocks_improved']>=5 and
            chosen['years_improved']>=9 and chosen['months_improved']>=80 and
            chosen['worst_annual_relative_change']<=.005):
        raise ValueError('A exceção não dispensa os critérios de estabilidade')
    protected=[r.OUT/'selection.json',r.OUT/'protocol.json',
               r.ROOT/'submissions/submission_10.csv',r.ROOT/'submissions/submission_10.json',
               r.ROOT/'submissions/submission_11.csv',r.ROOT/'submissions/submission_11.json']
    hashes={p.relative_to(r.ROOT).as_posix():r.digest(p) for p in protected}
    if hashes['submissions/submission_10.csv']!=S10_HASH or hashes['submissions/submission_11.csv']!=S11_HASH:
        raise ValueError('Submissão anterior alterada')
    ART.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
    obj=dict(candidate=NAME,original_protocol=frozen,original_selection=selection,
        experimental_protocol_sha256=r.digest(PROTOCOL),exporter_sha256=r.digest(Path(__file__)),
        user_authorized=True,waived_gate='development_minimum_gain_only',
        confirmation_and_shift_mandatory=True,automatic_promotion_passed=False,
        protected_hashes=hashes,official_only=True,upload_authorized=False)
    path=OUT/'authorization.json'
    if path.exists() and r.read(path)!=obj: raise ValueError('Registro de autorização mudou')
    if not path.exists(): r.save_json(path,obj)
    return chosen,obj


def check_protected(authorization):
    for filename,expected in authorization['protected_hashes'].items():
        if r.digest(r.ROOT/filename)!=expected: raise ValueError('Artefato protegido alterado')


def confirm(user_authorized=False):
    chosen,authorization=authorize(user_authorized)
    path=OUT/'confirmation.json'
    if path.exists():
        result=r.read(path)
        if result['candidate']!=NAME: raise ValueError('Confirmação de outra candidata')
        print(json.dumps(result,ensure_ascii=False,indent=2)); return result
    # A mesma implementação congelada da rodada; a seleção automática não é modificada.
    leaves,fraction=r.CONFIGS[NAME]
    ref=r.reference(2021); pred=np.maximum(ref+fraction*r.correction(2021,leaves),0)
    model_meta=r.read(r.ART/'2021_meta15.json')
    if model_meta['last_training_target']!='2020-12': raise ValueError('Corte de treinamento incorreto')
    truth=np.load(r.CACHE/'tp.npy',mmap_mode='r')[r.target_origins(2021)+1]
    before,after=r.metrics(ref,truth,ref),r.metrics(pred,truth,ref)
    result=dict(candidate=NAME,reference=before,result=after,passed=confirmation_passes(before,after),
        relative_gain=1-after['rmse']/before['rmse'],previously_consumed_period=True,
        diagnostic_only=False,mandatory_gate=True,no_post_confirmation_tuning=True,
        training_blocks=model_meta['training_blocks'],last_training_target=model_meta['last_training_target'],
        model_sha256=model_meta['sha256'])
    check_protected(authorization)
    r.save_json(path,result); print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
    return result


def export(user_authorized=False):
    chosen,authorization=authorize(user_authorized)
    check=r.read(OUT/'confirmation.json')
    if check['candidate']!=NAME or not check['passed'] or not confirmation_passes(check['reference'],check['result']):
        raise ValueError('Confirmação reprovada: não gerar S12')
    csv=r.ROOT/'submissions/submission_12.csv'; nc=ART/'submission_12_predictions.nc'
    for path in (csv,csv.with_suffix('.json'),nc):
        if path.exists(): raise FileExistsError(path)
    leaves,fraction=r.CONFIGS[NAME]
    ref=r.reference(2023); delta=r.correction(2023,leaves)
    pred=np.maximum(ref+fraction*delta,0)
    final_meta=r.read(r.ART/'2023_meta15.json')
    if final_meta['last_training_target']!='2022-12': raise ValueError('Corte final incorreto')
    # Inferência independente com modelo recarregado, sem novo ajuste.
    import joblib
    model=joblib.load(r.ART/'2023_meta15.joblib')
    if r.digest(r.ART/'2023_meta15.joblib')!=final_meta['sha256']: raise ValueError('Modelo final alterado')
    for month in range(24):
        reproduced=model.predict(r.matrix(2023,month,np.arange(78561))).reshape(301,261)
        np.testing.assert_array_equal(delta[month],reproduced)
    historical=chosen['historical_correction_rms']
    rms=[float(np.sqrt(np.mean((pred[s]-ref[s])**2))) for s in (slice(0,12),slice(12,24))]
    shift=dict(candidate=NAME,historical_rms=historical,maximum_allowed_rms=2*historical,
        public2023_rms=rms[0],private2024_rms=rms[1],passed=shift_passes(rms,historical))
    r.save_json(OUT/'test_shift.json',shift)
    if not shift['passed']: raise ValueError('Limite de mudança reprovado: não gerar S12')
    with xr.open_dataset(r.RAW/'teste_features.nc') as grid:
        da=xr.DataArray(pred,dims=('time','lat','lon'),coords={d:grid[d] for d in ('time','lat','lon')},name='tp_mm_day')
        da.attrs.update(units='mm/day',model=NAME,official_only='true',experimental='true')
        da.to_netcdf(nc)
        metadata=export_csv(da,grid,csv,r.RAW/'sample_submission.csv')
    with xr.open_dataset(nc) as ds: np.testing.assert_array_equal(ds.tp_mm_day.values,pred)
    check_protected(authorization)
    metadata.update(experiment='round17_experimental',model=NAME,base_model='S11',
        experimental=True,user_authorized=True,automatic_promotion_passed=False,
        waived_gate='development_minimum_gain_only',minimum_historical_gain_still_active=.003,
        official_data_only=True,external_sources=[],public_score=None,uploaded=False,
        csv_sha256=r.digest(csv),predictions_sha256=r.digest(nc),training_targets_end='2022-12',
        authorization=authorization,development_candidate=chosen,confirmation=check,test_shift=shift,
        final_model=final_meta,sample_sha256=r.digest(r.RAW/'sample_submission.csv'),
        versions={p:importlib.metadata.version(p) for p in ('numpy','scipy','scikit-learn','xarray','pandas','joblib')})
    r.save_json(csv.with_suffix('.json'),metadata)
    r.save_json(OUT/'verification.json',dict(candidate=NAME,full_model_reload_prediction_match=True,
        netcdf_roundtrip_exact=True,official_template_verified=True,rows=metadata['rows'],
        s10_s11_and_selection_unchanged=True,confirmation_passed=True,test_shift_passed=True,
        automatic_promotion_passed=False,experimental_user_authorized=True,uploaded=False,
        csv_sha256=metadata['csv_sha256']))
    print('S12 GERADA:',csv,flush=True)
    print(json.dumps(shift,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('confirm','export'))
    parser.add_argument('--user-authorized',action='store_true')
    args=parser.parse_args(); globals()[args.stage](args.user_authorized)
