"""Retreino do corretor S12 e inferência usando motor S11 e evidências OOF oficiais."""
import hashlib
from pathlib import Path
from . import s11_delivery as base
import joblib
import numpy as np
import xarray as xr
from sklearn.ensemble import HistGradientBoostingRegressor
from .round4 import groups
from .round11 import blend
from .round19_history import feature_rows

ROOT=Path(__file__).resolve().parents[1]


def evidence(c):
    root=c.get('s12_evidence',ROOT/'delivery/s12/evidence')
    manifest=base.read(root/'manifest.json')
    expected=base.read(ROOT/'configs/modelos.json')['versoes']['s12']['evidencias_sha256']
    if base.digest(root/'manifest.json')!=expected: raise ValueError('Evidências S12 alteradas')
    if manifest['source_hashes']!=base.read(c['evidence']/'official_sources.json'): raise ValueError('Fontes divergentes')
    return root,manifest


def prepare(c):
    evidence(c); base.prepare(c)


def train(c):
    root,record=evidence(c)
    # Componentes já treinados podem ser compartilhados com S10/S11, após verificação.
    path=c['models']/'manifest.json'
    if not path.exists(): base.train(c)
    old=base.read(path)
    for name,h in old['hashes'].items():
        if base.digest(c['models']/name)!=h: raise ValueError('Componente S11 alterado')
    dest=c['models']/'s12_corrector.joblib'
    if dest.exists(): raise FileExistsError(dest)
    xs=[]; ys=[]
    for row in record['blocks']:
        source=root/row['file']
        if base.digest(source)!=row['sha256']: raise ValueError('Exemplo OOF alterado')
        if row['block']+1>2022 or row['base_training_targets_end']!=f"{row['block']-1}-12": raise ValueError('Corte OOF inválido')
        with np.load(source) as z: xs.append(z['x']); ys.append(z['y'])
    x,y=np.concatenate(xs),np.concatenate(ys)
    model=HistGradientBoostingRegressor(**record['tree_parameters']).fit(x,y)
    actual=hashlib.sha256(model.predict(x).tobytes()).hexdigest()
    if actual!=record['training_prediction_sha256']: raise ValueError('Retreino do corretor difere do original')
    joblib.dump(model,dest)
    np.testing.assert_array_equal(model.predict(x),joblib.load(dest).predict(x))
    base.write(c['models']/'s12_manifest.json',dict(corrector_sha256=base.digest(dest),
        evidence_sha256=base.digest(root/'manifest.json'),base_manifest_sha256=base.digest(path),
        training_prediction_sha256=actual,training_targets_end='2022-12',samples=len(x),
        official_only=True,full_oof_research_retrained=False,corrector_retrained=True))
    print('CORRETOR S12 RETREINADO E VERIFICADO',len(x),flush=True)


def predict(c):
    root,record=evidence(c); meta=base.read(c['models']/'s12_manifest.json')
    if base.digest(c['models']/'manifest.json')!=meta['base_manifest_sha256']: raise ValueError('Manifesto base alterado')
    if base.digest(c['models']/'s12_corrector.joblib')!=meta['corrector_sha256']: raise ValueError('Corretor alterado')
    if base.digest(root/'manifest.json')!=meta['evidence_sha256']: raise ValueError('Evidência alterada')
    parent={**c,'version':'s11','output':c['output']/'base_s11'}
    parent_csv=parent['output']/'s11_reproduction.csv'
    if not parent_csv.exists(): base.predict(parent)
    catalog=base.read(ROOT/'configs/modelos.json')
    if base.digest(parent_csv)!=catalog['versoes']['s11']['csv_sha256']: raise ValueError('Base S11 não reproduzida')
    # Verificar componentes contra a previsão combinada, não confiar só no CSV.
    components=[np.load(parent['output']/f'{name}.npy') for name in ('s02','modes','local18','pls16')]
    trop=np.load(parent['output']/'fine32.npy'); w=base.read(c['models']/'weights.json')
    p=np.stack(components[:3]).astype(float)
    s06=np.sum(p*np.asarray(w['base_weights'])[groups()].transpose(3,0,1,2),axis=0)
    s09=.75*s06+.25*components[3]
    pieces=np.stack(components+[blend(s09,trop,1.)]).astype(float)
    ref=np.sum(pieces*np.asarray(w['weights'])[groups()].transpose(3,0,1,2),axis=0)
    with xr.open_dataset(parent['output']/'s11_reproduction.nc') as ds: np.testing.assert_array_equal(ref,ds.tp_mm_day.values)
    prep=joblib.load(c['models']/'preprocessing.joblib'); model=joblib.load(c['models']/'s12_corrector.joblib')
    destination=c['output']/'s12_reproduction.csv'
    if destination.exists(): raise FileExistsError(destination)
    with xr.open_dataset(c['raw']/'teste_features.nc') as test:
        np.testing.assert_array_equal(test.time_origem.values.astype('datetime64[M]'),np.arange('2022-12','2024-12',dtype='datetime64[M]'))
        fields=[test[v].values.reshape(24,-1) for v in base.VARIABLES]
        out=[]
        for month in range(24):
            x=feature_rows(ref.reshape(24,-1),pieces.reshape(5,24,-1),prep['climatology'],fields,month,np.arange(78561),month)
            out.append(np.maximum(ref[month]+.25*model.predict(x).reshape(301,261),0))
        da=xr.DataArray(np.stack(out),dims=('time','lat','lon'),coords={d:test[d] for d in ('time','lat','lon')},name='tp_mm_day')
        da.to_netcdf(c['output']/'s12_reproduction.nc')
        metadata=base.export_csv(da,test,destination,c['raw']/'sample_submission.csv')
    actual=base.digest(destination)
    if actual!=record['expected_csv_sha256']: raise ValueError('S12 reproduzida diferente do CSV original')
    base.write(destination.with_suffix('.json'),dict(**metadata,csv_sha256=actual,
        reproduction_only=True,corrector_retrained=True,identical_to_original=True))
    print('S12 REPRODUZIDA: CSV IDÊNTICO AO ORIGINAL',flush=True)
