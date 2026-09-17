"""S13 experimental: exceções explícitas, sem promoção automática."""
import argparse
import importlib.metadata
import json
import sys
from functools import lru_cache
from pathlib import Path
import joblib
import numpy as np
import xarray as xr
from . import round24 as r
from . import round20 as parent
from .round17_experimental import confirmation_passes,shift_passes
from .submission import export_csv

NAME='transporte_lag_norte_b0.5'
ART=r.old.ROOT/'data/processed/round24_experimental'
OUT=r.old.REPORT/'round24_experimental'
PROTOCOL=r.old.ROOT/'experiments/ROUND24_EXPERIMENTAL.md'
S12_HASH='bba1f8b279447868170b6b2f9b18ee2cc723b891c25627c91438c7725d3aead8'
INITIAL_PROTOCOL_HASH='95dfc2b7d2594df51b461cd0b5cc6e38ca847ba0df091adab7446b0e71265bb0'
INITIAL_EXPORTER_HASH='6e579bb3145e9c8375ec5bb640510858e6fc74caf11b964a6f50155ba830217b'


def authorize(user_authorized):
    if not user_authorized: raise PermissionError('Pedido experimental explícito obrigatório')
    r.locked(); ART.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
    selection=r.old.read(r.OUT/'selection.json')
    chosen=next(v for v in selection['ranking'] if v['model']==NAME)
    refs=np.array([r.old.read(r.OUT/f'{year}.json')[0]['monthly_rmse'] for year in r.old.DEV])
    ref_second=float(np.sqrt(np.mean(refs[:,12:]**2)))
    if (selection['selected'] is not None or chosen['passed'] or
        selection['minimum_relative_gain']!=.003 or
        r.CONFIGS[NAME]!=('transporte_lag','norte',.5) or
        not 0<chosen['relative_gain']<.003):
        raise ValueError('Candidata divergente da exceção solicitada')
    if not (chosen['second_year_rmse']<ref_second and chosen['blocks_improved']>=5 and
            chosen['years_improved']>=9 and chosen['months_improved']>=80 and
            chosen['worst_annual_relative_change']<=.005):
        raise ValueError('Critério de estabilidade não dispensado falhou')
    protected=[r.OUT/'selection.json',r.OUT/'protocol.json',
               r.old.ROOT/'submissions/submission_12.csv',
               r.old.ROOT/'submissions/submission_12.json']
    hashes={p.relative_to(r.old.ROOT).as_posix():r.old.digest(p) for p in protected}
    if hashes['submissions/submission_12.csv']!=S12_HASH: raise ValueError('S12 alterada')
    official=r.old.read(r.old.ROOT/'delivery/s11/evidence/official_sources.json')
    test_path=r.old.RAW/'teste_features.nc'
    if r.old.digest(test_path)!=official['teste_features.nc']: raise ValueError('Teste oficial alterado')
    sample=r.old.RAW/'sample_submission.csv'
    if not sample.exists(): raise FileNotFoundError(sample)
    obj=dict(candidate=NAME,user_authorized=True,
        waived_gate='development_minimum_gain_only',
        confirmation_and_test_shift_mandatory=True,
        automatic_promotion_passed=False,upload_authorized=False,official_only=True,
        experimental_protocol_sha256=r.old.digest(PROTOCOL),
        exporter_sha256=r.old.digest(Path(__file__)),
        research_protocol=r.old.read(r.OUT/'protocol.json'),
        historical_candidate=chosen,protected_hashes=hashes,
        test_features_sha256=official['teste_features.nc'],
        sample_sha256=r.old.digest(sample))
    path=OUT/'authorization.json'
    if path.exists():
        original=r.old.read(path)
        if (original['experimental_protocol_sha256']!=INITIAL_PROTOCOL_HASH or
            original['exporter_sha256']!=INITIAL_EXPORTER_HASH or
            {k:v for k,v in original.items() if k not in ('experimental_protocol_sha256','exporter_sha256')}!=
            {k:v for k,v in obj.items() if k not in ('experimental_protocol_sha256','exporter_sha256')}):
            raise ValueError('Registro experimental original mudou')
        return chosen,original
    r.old.save_json(path,obj)
    return chosen,obj


def check_protected(auth):
    for name,expected in auth['protected_hashes'].items():
        if r.old.digest(r.old.ROOT/name)!=expected: raise ValueError(f'Artefato protegido alterado: {name}')


@lru_cache(maxsize=1)
def test_weather():
    path=r.old.RAW/'teste_features.nc'
    with xr.open_dataset(path) as ds:
        expected=np.arange('2022-12','2024-12',dtype='datetime64[M]')
        np.testing.assert_array_equal(ds.time_origem.values.astype('datetime64[M]'),expected)
        variables=tuple(np.asarray(ds[name].values,np.float32)
                        for name in ('shum_850','u_850','v_850'))
    for old_array,new_array in zip(r.fields(),variables):
        np.testing.assert_array_equal(old_array[-1],new_array[0])
    return variables


@lru_cache(maxsize=4)
def future_flux(origin):
    if origin<996: return r.flux(origin)
    if origin>1018: raise ValueError('Mês atmosférico fora do teste oficial')
    q,u,v=(arr[origin-995] for arr in test_weather())
    qu=q*u; qv=q*v
    lat=np.deg2rad(np.arange(-60,15.01,.25))
    dx=r.STEP*np.cos(lat)[:,None]
    convergence=-(np.gradient(qu,axis=1)/dx+np.gradient(qv,axis=0)/r.STEP)*1e6
    yi,xi=np.indices(q.shape)
    y_up=np.clip(yi-8*np.sign(v).astype(int),0,300)
    x_up=np.clip(xi-8*np.sign(u).astype(int),0,260)
    upstream=q[y_up,x_up]-q
    result=(qu.ravel(),qv.ravel(),convergence.astype(np.float32).ravel(),upstream.ravel())
    if any(not np.isfinite(v).all() for v in result): raise ValueError('Fluxo não finito')
    return result


def future_extra(origin,cells):
    cells=np.asarray(cells)
    current=future_flux(int(origin)); prev1=future_flux(int(origin)-1)[2]
    prev2=future_flux(int(origin)-2)[2]
    result=np.column_stack([current[0][cells],current[1][cells],current[2][cells],
        prev1[cells],(current[2][cells]+prev1[cells]+prev2[cells])/3,
        current[3][cells]]).astype(np.float32)
    if result.shape!=(len(cells),6) or not np.isfinite(result).all():
        raise ValueError('Atributos futuros inválidos')
    return result


def final_model(cutoff):
    if cutoff not in (2021,2023): raise ValueError('Corte não autorizado')
    years,base,added,target=r.samples(cutoff)
    model=r.fitted(cutoff,'transporte_lag',years,base,added,target)
    meta=r.old.read(r.ART/f'{cutoff}_transporte_lag.json')
    if r.old.digest(r.ART/f'{cutoff}_transporte_lag.joblib')!=meta['sha256']:
        raise ValueError('Modelo final alterado')
    if meta['last_training_target']!=f'{cutoff-1}-12':
        raise ValueError('Alvo de treinamento do corte final inválido')
    return model,meta


def candidate(cutoff,model):
    cells=np.arange(78561)
    global_model=r.old.fitted(cutoff,15)
    s11=r.old.reference(cutoff)
    reference=parent.reference(cutoff)
    prediction=np.empty((24,301,261))
    for month,origin in enumerate(r.old.target_origins(cutoff)):
        x=r.old.matrix(cutoff,month,cells)
        add=r.extra(origin,cells) if origin<996 else future_extra(origin,cells)
        original=global_model.predict(x).reshape(301,261)
        new=model.predict(np.column_stack([x,add])).reshape(301,261)
        np.testing.assert_allclose(np.maximum(s11[month]+.25*original,0),
                                   reference[month],rtol=0,atol=1e-8)
        prediction[month]=np.maximum(s11[month]+.25*(original+
            .5*r.north_mask()*(new-original)),0)
        print('MÊS PREVISTO',cutoff,month+1,flush=True)
    if not np.isfinite(prediction).all() or (prediction<0).any():
        raise ValueError('Previsão inválida')
    return prediction,reference


def confirm(user_authorized=False):
    chosen,auth=authorize(user_authorized)
    path=OUT/'confirmation.json'
    if path.exists():
        result=r.old.read(path)
        if result['candidate']!=NAME: raise ValueError('Confirmação de outra candidata')
        print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
        return result
    model,meta=final_model(2021)
    pred,reference=candidate(2021,model)
    truth=np.load(r.old.CACHE/'tp.npy',mmap_mode='r')[r.old.target_origins(2021)+1]
    before=r.old.metrics(reference,truth,reference)
    after=r.old.metrics(pred,truth,reference)
    result=dict(candidate=NAME,reference=before,result=after,
        relative_gain=1-after['rmse']/before['rmse'],
        passed=confirmation_passes(before,after),
        previously_consumed_period=True,mandatory_gate=True,
        no_post_confirmation_tuning=True,model=meta)
    check_protected(auth); r.old.save_json(path,result)
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
    return result


def confirmation_waiver(user_authorized,check,auth):
    if not user_authorized: raise PermissionError('Dispensa da confirmação requer pedido explícito')
    if check['candidate']!=NAME or check['passed'] or confirmation_passes(check['reference'],check['result']):
        raise ValueError('A dispensa não corresponde à confirmação reprovada')
    obj=dict(candidate=NAME,decision='user_requested_exploratory_csv_after_confirmation_failure',
        waived_gates=['development_minimum_gain','confirmation_2021_2022'],
        historical_policy_unchanged=True,automatic_promotion_passed=False,
        upload_authorized=False,test_shift_mandatory=True,
        original_authorization_sha256=r.old.digest(OUT/'authorization.json'),
        failed_confirmation_sha256=r.old.digest(OUT/'confirmation.json'),
        current_protocol_sha256=r.old.digest(PROTOCOL),
        current_exporter_sha256=r.old.digest(Path(__file__)))
    path=OUT/'confirmation_waiver.json'
    if path.exists() and r.old.read(path)!=obj: raise ValueError('Dispensa da confirmação mudou')
    if not path.exists(): r.old.save_json(path,obj)
    check_protected(auth)
    return obj


def export(user_authorized=False,waive_confirmation=False):
    chosen,auth=authorize(user_authorized)
    check=r.old.read(OUT/'confirmation.json')
    if check['candidate']!=NAME: raise ValueError('Confirmação de outra candidata')
    confirmation_ok=bool(check['passed'] and confirmation_passes(check['reference'],check['result']))
    if not confirmation_ok and not waive_confirmation:
        raise ValueError('Confirmação reprovada: dispensa explícita necessária')
    waiver=confirmation_waiver(waive_confirmation,check,auth) if not confirmation_ok else None
    csv=r.old.ROOT/'submissions/submission_13.csv'
    nc=ART/'submission_13_predictions.nc'
    for path in (csv,csv.with_suffix('.json'),nc):
        if path.exists(): raise FileExistsError(path)
    model,meta=final_model(2023)
    pred,reference=candidate(2023,model)
    with xr.open_dataset(r.old.ROOT/'data/processed/round17_experimental/submission_12_predictions.nc') as ds:
        np.testing.assert_allclose(reference,ds.tp_mm_day.values,rtol=0,atol=1e-8)
    historical=chosen['historical_correction_rms']
    rms=[float(np.sqrt(np.mean((pred[sl]-reference[sl])**2)))
         for sl in (slice(0,12),slice(12,24))]
    shift=dict(candidate=NAME,historical_rms=historical,
        maximum_allowed_rms=2*historical,public2023_rms=rms[0],
        private2024_rms=rms[1],passed=shift_passes(rms,historical))
    r.old.save_json(OUT/'test_shift.json',shift)
    if not shift['passed']: raise ValueError('Mudança no teste excede limite: S13 bloqueada')
    check_protected(auth)
    with xr.open_dataset(r.old.RAW/'teste_features.nc') as grid:
        da=xr.DataArray(pred,dims=('time','lat','lon'),
                        coords={d:grid[d] for d in ('time','lat','lon')},name='tp_mm_day')
        da.attrs.update(units='mm/day',model=NAME,official_only='true',experimental='true')
        da.to_netcdf(nc)
        metadata=export_csv(da,grid,csv,r.old.RAW/'sample_submission.csv')
    with xr.open_dataset(nc) as ds:
        np.testing.assert_array_equal(ds.tp_mm_day.values,pred)
    if r.old.digest(csv)==S12_HASH: raise ValueError('S13 idêntica à S12')
    check_protected(auth)
    metadata.update(experiment='round24_experimental',model=NAME,base_model='S12',
        experimental=True,user_authorized=True,automatic_promotion_passed=False,
        waived_gates=waiver['waived_gates'] if waiver else ['development_minimum_gain'],
        minimum_historical_gain_still_active=.003,
        official_data_only=True,external_sources=[],public_score=None,uploaded=False,
        csv_sha256=r.old.digest(csv),predictions_sha256=r.old.digest(nc),
        training_targets_end='2022-12',authorization=auth,
        confirmation_waiver=waiver,development_candidate=chosen,confirmation=check,test_shift=shift,
        final_model=meta,sample_sha256=auth['sample_sha256'],
        versions={name:importlib.metadata.version(name) for name in
                  ('numpy','scipy','scikit-learn','xarray','pandas','joblib')})
    r.old.save_json(csv.with_suffix('.json'),metadata)
    r.old.save_json(OUT/'verification.json',dict(candidate=NAME,
        official_template_verified=True,rows=metadata['rows'],
        s12_unchanged=True,confirmation_passed=confirmation_ok,
        confirmation_waived=waiver is not None,test_shift_passed=True,
        experimental_user_authorized=True,automatic_promotion_passed=False,
        uploaded=False,csv_sha256=metadata['csv_sha256']))
    print('S13 GERADA:',csv,flush=True)
    print(json.dumps(shift,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=('confirm','export'))
    p.add_argument('--user-authorized',action='store_true')
    p.add_argument('--waive-confirmation',action='store_true')
    args=p.parse_args()
    if args.stage=='confirm' and args.waive_confirmation:
        p.error('--waive-confirmation só se aplica a export')
    if args.stage=='confirm': confirm(args.user_authorized)
    else: export(args.user_authorized,args.waive_confirmation)
