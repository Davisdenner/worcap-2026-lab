"""Freeze the existing S11 lineage for delivery; never train or upload."""
import hashlib
import json
import shutil
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'delivery/s11/evidence'


def read(p): return json.loads(p.read_text(encoding='utf-8'))


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'frozen_weights.json').exists(): raise FileExistsError('Evidence already frozen')
    weights=read(ROOT/'data/processed/round15/2023_joint1_weights.json')
    weights['base_weights']=read(ROOT/'data/processed/round9/2023_weights.json')['weights']
    (OUT/'frozen_weights.json').write_text(json.dumps(weights,indent=2)+'\n',encoding='utf-8')
    cov=np.stack([np.load(ROOT/f'data/processed/round15/{y}_covariance.npy') for y in weights['calibration_blocks']])
    np.save(OUT/'calibration_covariances.npy',cov)
    sources=read(ROOT/'reports/competition/round9/audit.json')['official_sources']
    (OUT/'official_sources.json').write_text(json.dumps(sources,indent=2)+'\n',encoding='utf-8')
    for name,path in {
        's11_generation.json':'submissions/submission_11.json',
        'historical_selection.json':'reports/competition/round15/selection.json',
        'reused_confirmation.json':'reports/competition/round15_experimental/confirmation.json',
        'leaderboard_observations.json':'reports/competition/leaderboard_observations.json',
    }.items(): shutil.copyfile(ROOT/path,OUT/name)
    for y in weights['calibration_blocks']:
        shutil.copyfile(ROOT/f'data/processed/round15/{y}_covariance.json',OUT/f'{y}_covariance.json')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file()}
    (OUT/'manifest.json').write_text(json.dumps(hashes,indent=2)+'\n',encoding='utf-8')
    print('S11 evidence frozen; no predictions copied')


if __name__=='__main__': main()
