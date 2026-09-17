"""Agenda os cinco cortes restantes sem alterar o núcleo numérico congelado."""
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
YEARS=(2011,2013,2015,2017,2019)


def block(year):
    env=os.environ.copy()
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'): env[key]='1'
    done=subprocess.run([sys.executable,'-m','src.round24','evaluate','--year',str(year)],
                        cwd=ROOT,env=env,capture_output=True,text=True)
    print(done.stdout,flush=True)
    if done.returncode:
        print(done.stderr,flush=True)
        raise RuntimeError(f'Corte {year} falhou: {done.returncode}')
    return year


def main():
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs=[pool.submit(block,year) for year in YEARS]
        for job in as_completed(jobs): print('BLOCO CONCLUÍDO',job.result(),flush=True)


if __name__=='__main__': main()
