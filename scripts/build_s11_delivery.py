"""Build a standalone, allowlisted S11 archive; no raw data or credentials."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
DELIVERY=ROOT/'delivery/s11'
STAGE=ROOT/'delivery/build/s11'
SOURCES=('competition.py','round2.py','round3.py','round4.py','round6.py','round9.py',
         'round10.py','round11.py','round12.py','round15.py','round15_experimental.py','submission.py','s11_delivery.py')


def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()


def stage():
    if STAGE.exists(): raise FileExistsError(STAGE)
    STAGE.mkdir(parents=True)
    for name in ('README.md','entry_points.md','requirements.txt','THIRD_PARTY_NOTICES.md','TEAM_INFO.json'):
        shutil.copyfile(DELIVERY/name,STAGE/name)
    for directory in ('models','evidence','wheels'):
        shutil.copytree(DELIVERY/directory,STAGE/directory)
    (STAGE/'src').mkdir()
    for name in SOURCES: shutil.copyfile(ROOT/'src'/name,STAGE/'src'/name)
    config=dict(raw='data/raw',cache='work/cache',models='models',output='work/output',evidence='evidence')
    (STAGE/'SETTINGS.json').write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
    print('STAGED',STAGE)


def finalize():
    if not STAGE.exists(): raise FileNotFoundError('Run stage first')
    # Refresh delivery docs after verification; original code/model bytes stay fixed.
    for name in ('README.md','entry_points.md','THIRD_PARTY_NOTICES.md','TEAM_INFO.json','check_delivery.py'):
        shutil.copyfile(DELIVERY/name,STAGE/name)
    for name in SOURCES:
        if not (STAGE/'src'/name).exists(): shutil.copyfile(ROOT/'src'/name,STAGE/'src'/name)
        if digest(ROOT/'src'/name)!=digest(STAGE/'src'/name): raise ValueError('Staged source changed')
    (STAGE/'experiments').mkdir(exist_ok=True)
    for n in ('2','3','4','6','9','10','11','12','15','15_EXPERIMENTAL'):
        shutil.copyfile(ROOT/f'experiments/ROUND{n}.md',STAGE/f'experiments/ROUND{n}.md')
    for name in ('MODEL_SUMMARY.pdf','LICENSE'):
        if (DELIVERY/name).exists(): shutil.copyfile(DELIVERY/name,STAGE/name)
    (STAGE/'verification').mkdir(exist_ok=True)
    for p in (DELIVERY/'verification').iterdir():
        if p.suffix in ('.json','.md'): shutil.copyfile(p,STAGE/'verification'/p.name)
    dirs=sorted({'.'}|{p.relative_to(STAGE).as_posix() for p in STAGE.rglob('*') if p.is_dir() and '__pycache__' not in p.parts})
    (STAGE/'directory_structure.txt').write_text('\n'.join(dirs)+'\n',encoding='utf-8')
    # Explicit file allowlist excludes smoke-test work directories and configs.
    files=[p for p in STAGE.iterdir() if p.is_file() and p.name not in ('PACKAGE_MANIFEST.json','SETTINGS_SMOKE.json')]
    for directory in ('src','models','evidence','wheels','verification','experiments'):
        files.extend(p for p in (STAGE/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    manifest={p.relative_to(STAGE).as_posix():dict(bytes=p.stat().st_size,sha256=digest(p)) for p in files}
    target=STAGE/'PACKAGE_MANIFEST.json'
    target.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    archive=ROOT/'delivery/s11_delivery_draft.zip'
    if archive.exists(): raise FileExistsError(archive)
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files+[target]: z.write(p,p.relative_to(STAGE).as_posix())
    with zipfile.ZipFile(archive) as z:
        bad=z.testzip()
        if bad: raise ValueError(bad)
        for name,entry in manifest.items():
            if hashlib.sha256(z.read(name)).hexdigest()!=entry['sha256']: raise ValueError(name)
    report=dict(file=archive.relative_to(ROOT).as_posix(),bytes=archive.stat().st_size,
                sha256=digest(archive),files=len(files)+1,archive_crc_and_all_hashes_passed=True,
                original_data_included=False,credentials_included=False,
                status='Technical draft pending entrant identity and license confirmation')
    (ROOT/'delivery/s11_archive.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('stage',choices=('stage','finalize'))
    globals()[p.parse_args().stage]()
