"""Orquestra blocos independentes sem alterar o protocolo ou os núcleos congelados."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'): os.environ[key]='1'
import concurrent.futures
import argparse
import gc
import subprocess
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src import round20 as r


def block(year):
    if year not in r.old.DEV: raise ValueError('Bloco de desenvolvimento inválido')
    destination=r.OUT/f'{year}.json'
    if destination.exists(): return year
    print('INICIANDO BLOCO PARALELO',year,flush=True)
    f=r.Features(year); gtrain,gvalid=r.context(f); x,y=r.training(f,gtrain)
    reference=r.reference(year); truth=f.tp[r.target_origins(year)+1].reshape(24,301,261)
    rows=[dict(model='s12',**r.old.metrics(reference,truth,reference))]; direct=[]
    for name in r.MODELS:
        model=r.fitted(f,name,x,y); pred=r.predict(f,name,model,gvalid)
        direct.append(dict(model=name,**r.old.metrics(pred,truth,reference)))
        for a in r.FRACTIONS:
            value=reference+a*(pred-reference)
            rows.append(dict(model=f'{name}_a{a:g}',**r.old.metrics(value,truth,reference)))
        print('AVALIADO',year,name,'RMSE direto',direct[-1]['rmse'],flush=True)
    r.old.save_json(r.OUT/f'{year}_direct.json',direct)
    r.old.save_json(destination,rows)
    print('BLOCO CONCLUÍDO',year,[(row['model'],round(row['rmse'],6)) for row in rows],flush=True)
    del f,x,y,reference,truth,pred,model
    r.old.data.cache_clear(); r.old.reference.cache_clear(); gc.collect()
    return year


def main():
    r.locked()
    if not r.old.read(r.OUT/'audit.json')['passed']: raise ValueError('Auditoria necessária')
    r.old.save_json(r.OUT/'parallel_execution.json',dict(
        driver_sha256=r.old.digest(Path(__file__)),workers=2,threads_per_model=1,
        launch_strategy='subprocess; duas threads apenas para agendamento',
        execution_note='multiprocessing.Pipe indisponível no host; substituído antes de executar blocos paralelos.',
        unchanged_numerical_source_sha256=r.old.digest(r.old.ROOT/'src/round20.py'),
        changes='Somente agendamento de blocos independentes; sem alterações de dados, parâmetros, sementes ou critérios.'))
    pending=[year for year in r.old.DEV if not (r.OUT/f'{year}.json').exists()]
    def launch(year):
        subprocess.run([sys.executable,str(Path(__file__).resolve()),'--block',str(year)],check=True)
        return year
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        tasks=[pool.submit(launch,year) for year in pending]
        for task in concurrent.futures.as_completed(tasks): print('BLOCO VERIFICADO',task.result(),flush=True)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--block',type=int)
    args=parser.parse_args()
    if args.block is None: main()
    else:
        r.locked(); block(args.block)
