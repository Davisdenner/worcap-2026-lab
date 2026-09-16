"""Create offline wheels from installed distributions, preserving license notices.

These are locally repacked installed files, NOT independently downloaded PyPI
wheels. This is explicit in the output provenance. No credentials are copied.
"""
import base64
import csv
import hashlib
import importlib.metadata as metadata
import io
import json
from pathlib import Path, PurePosixPath
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'delivery/s11/wheels'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    inventory=[]
    previous=json.loads((OUT/'provenance.json').read_text()) if (OUT/'provenance.json').exists() else []
    for line in (ROOT/'delivery/s11/requirements.txt').read_text().splitlines():
        if not line.strip() or line.startswith('#'): continue
        name,version=line.split('=='); dist=metadata.distribution(name)
        if dist.version!=version: raise ValueError(f'Installed version mismatch: {name}')
        tags=[v.split(': ',1)[1] for v in dist.read_text('WHEEL').splitlines() if v.startswith('Tag: ')]
        tag=tags[-1]  # Prefer Python 3 when a pure wheel declares both py2 and py3.
        filename=f'{name.replace("-","_")}-{version}-{tag}.whl'
        path=OUT/filename
        if path.exists():
            old=next((r for r in previous if r['file']==filename),None)
            if old is None or hashlib.sha256(path.read_bytes()).hexdigest()!=old['sha256']:
                raise ValueError('Existing offline wheel is not verified')
            inventory.append(old)
            continue
        rows=[]; licenses=[]; changed=[]; total=0; dist_info=None
        with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
            for relative in dist.files or []:
                rel=PurePosixPath(str(relative).replace('\\','/'))
                # Console launchers are recreated by pip from entry_points.txt.
                if '..' in rel.parts or rel.suffix=='.pyc' or '__pycache__' in rel.parts: continue
                if rel.name in ('RECORD','INSTALLER','REQUESTED','direct_url.json'): continue
                file=Path(dist.locate_file(relative))
                if not file.is_file(): raise FileNotFoundError(file)
                data=file.read_bytes(); digest=base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()
                if relative.hash and relative.hash.mode=='sha256' and relative.hash.value!=digest: changed.append(str(rel))
                archive.writestr(str(rel),data); rows.append([str(rel),'sha256='+digest,str(len(data))]); total+=len(data)
                if rel.parts[0].endswith('.dist-info'): dist_info=rel.parts[0]
                if any(x in str(rel).lower() for x in ('license','copying','notice')): licenses.append(str(rel))
            if not dist_info: raise ValueError('Missing distribution metadata')
            record=f'{dist_info}/RECORD'; rows.append([record,'',''])
            stream=io.StringIO(newline=''); csv.writer(stream,lineterminator='\n').writerows(rows)
            archive.writestr(record,stream.getvalue())
        inventory.append(dict(name=name,version=version,file=filename,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                              origin='Locally repacked from installed distribution RECORD; not an original publisher wheel',
                              installed_files_differing_from_record=changed,license_files=licenses,uncompressed_bytes=total,
                              license_expression=dist.metadata.get('License-Expression'),license=dist.metadata.get('License')))
        print('OFFLINE WHEEL',filename,flush=True)
    (OUT/'provenance.json').write_text(json.dumps(inventory,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__': main()
