"""Verify packaged file hashes and optionally the reproduced S11 CSV."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''): h.update(block)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--predictions',type=Path)
    args=p.parse_args(); root=Path(__file__).resolve().parent
    manifest=json.loads((root/'PACKAGE_MANIFEST.json').read_text())
    for name,item in manifest.items():
        file=(root/name).resolve()
        if not file.is_relative_to(root) or not file.is_file(): raise ValueError(name)
        if file.stat().st_size!=item['bytes'] or sha(file)!=item['sha256']: raise ValueError(name)
    print('PASS: package file hashes',len(manifest))
    if args.predictions:
        expected=json.loads((root/'evidence/s11_generation.json').read_text())['csv_sha256']
        actual=sha(args.predictions)
        if actual!=expected: raise ValueError('CSV differs from original S11; investigate numerical environment, never alter predictions to match a leaderboard')
        print('PASS: reproduced CSV exactly matches original S11',actual)


if __name__=='__main__': main()
