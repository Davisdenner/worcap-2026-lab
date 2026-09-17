"""Empacotar exemplos OOF oficiais congelados da S12; não treina ou exporta CSV."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'): os.environ[k]='1'
import hashlib
import shutil
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import joblib
import numpy as np
from src import round17 as r


def main():
    r.locked(); r.audit()
    dest=r.ROOT/'delivery/s12/evidence'; dest.mkdir(parents=True,exist_ok=True)
    original=r.read(r.ROOT/'submissions/submission_12.json')
    model=joblib.load(r.ART/'2023_meta15.joblib')
    if r.digest(r.ART/'2023_meta15.joblib')!=original['final_model']['sha256']: raise ValueError('Modelo original alterado')
    records=[]; xs=[]
    for year in r.HISTORY:
        x,y=r.samples(year); xs.append(x)
        source=r.ART/f'{year}_samples.npz'; target=dest/source.name
        if target.exists():
            if r.digest(target)!=r.digest(source): raise ValueError('Evidência existente diferente')
        else: shutil.copyfile(source,target)
        records.append(dict(file=target.name,**r.read(source.with_suffix('.json'))))
    manifest=dict(reference='S12',official_only=True,blocks=records,
        description='Exemplos OOF congelados; são dados derivados, não pesos treinados. Incluídos para retreinar o corretor sem repetir a pesquisa histórica.',
        source_hashes=r.read(r.ROOT/'delivery/s11/evidence/official_sources.json'),
        audit=r.read(r.OUT/'audit.json'),features=r.FEATURES,tree_parameters=dict(max_leaf_nodes=15,**r.TREE),
        fraction=.25,sample_sha256=original['sample_sha256'],expected_csv_sha256=original['csv_sha256'],
        training_prediction_sha256=hashlib.sha256(model.predict(np.concatenate(xs)).tobytes()).hexdigest(),
        frozen_source_sha256={p:r.digest(r.ROOT/'src'/p) for p in ('round17.py','round16.py','diagnose_s11.py')})
    path=dest/'manifest.json'
    if path.exists() and r.read(path)!=manifest: raise ValueError('Manifesto existente diferente')
    if not path.exists(): r.save_json(path,manifest)
    print('EVIDÊNCIAS S12',len(records),'blocos;',sum((dest/r['file']).stat().st_size for r in records),'bytes',flush=True)


if __name__=='__main__': main()
