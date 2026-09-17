"""Conferência independente das amostras adicionais contra os arrays oficiais."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'): os.environ[k]='1'
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from src import round19 as r
from src.round19_history import EARLY,ART
from src.competition import VARIABLES,CACHE


def main():
    r.locked()
    rain=np.load(CACHE/'tp.npy',mmap_mode='r').reshape(996,-1)
    fields=[np.load(CACHE/f'{v}.npy',mmap_mode='r').reshape(996,-1) for v in VARIABLES]
    records=[]
    for year in EARLY:
        x,y=r.samples(year); rng=np.random.default_rng(r.old.SEED+year)
        if x.shape!=(49152,23) or y.shape!=(49152,) or not np.isfinite(x).all() or not np.isfinite(y).all(): raise ValueError('Amostra inválida')
        max_error=0.
        for m,o in enumerate(r.old.target_origins(year)):
            cells=rng.choice(78561,2048,replace=False); sl=slice(m*2048,(m+1)*2048)
            np.testing.assert_array_equal(x[sl,0],-60+(cells//261)*.25)
            np.testing.assert_array_equal(x[sl,1],-90+(cells%261)*.25)
            for j in range(9): np.testing.assert_array_equal(x[sl,14+j],fields[j][o,cells])
            reconstructed=y[sl].astype(float)+x[sl,5].astype(float)
            actual=rain[o+1,cells].astype(float)
            # x e y armazenam duas quantizações float32 independentes.
            tolerance=np.abs(np.spacing(x[sl,5])).astype(float)+np.abs(np.spacing(y[sl])).astype(float)
            if np.any(abs(reconstructed-actual)>tolerance+1e-12): raise ValueError('Alvo/resíduo não reconstrói chuva oficial')
            max_error=max(max_error,float(np.max(abs(reconstructed-actual))))
        records.append(dict(block=year,sha256=r.old.digest(ART/f'{year}_samples.npz'),
            full_atmospheric_sample_equality=True,residual_plus_reference_matches_official_target_within_float32_quantization=True,
            max_reconstruction_error=max_error,last_base_training_target=f'{year-1}-12'))
    r.old.save_json(r.OUT/'history_audit.json',dict(passed=True,official_only=True,additional_examples=196608,blocks=records))
    print('PASS: 196608 exemplos adicionais, coordenadas, atmosfera e alvos oficiais',flush=True)


if __name__=='__main__': main()
