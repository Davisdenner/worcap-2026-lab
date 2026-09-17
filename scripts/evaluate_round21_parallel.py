"""Agenda blocos independentes da rodada 21 em até dois subprocessos."""
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
YEARS = (2011, 2013, 2015, 2017, 2019)


def block(year):
    environment = os.environ.copy()
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
        environment[key] = '1'
    result = subprocess.run([sys.executable, '-m', 'src.round21', 'evaluate', '--year', str(year)],
                            cwd=ROOT, env=environment, capture_output=True, text=True)
    print(result.stdout, flush=True)
    if result.returncode:
        print(result.stderr, flush=True)
        raise RuntimeError(f'Bloco {year} falhou com código {result.returncode}')
    return year


def main():
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(block, year) for year in YEARS]
        for job in as_completed(jobs):
            print('BLOCO CONCLUÍDO', job.result(), flush=True)


if __name__ == '__main__': main()
