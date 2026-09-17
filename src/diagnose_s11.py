"""Diagnóstico descritivo S11 em previsões históricas fora do treino.

Somente 2009–2020. Não acessa alvos de 2023/2024, não ajusta modelos e não
exporta submissões. Classes de chuva observada servem apenas ao diagnóstico.
"""
import os
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import json
from pathlib import Path
import numpy as np
import xarray as xr
from .competition import ROOT, CACHE, RAW, REPORT, save_json
from .round2 import target_origins
from .round4 import groups
from .round11 import blend
from .round15 import combine
from .round9 import digest, read

OUT = REPORT / 's11_diagnostic'
YEARS = (2009, 2011, 2013, 2015, 2017, 2019)


def verified_prediction(year):
    if year not in YEARS + (2021, 2023):
        raise ValueError('Corte não registrado')
    art = ROOT / 'data/processed/round15'
    record = read(art / f'{year}_components.json')
    for path, expected in record['component_sources'].items():
        if digest(ROOT / path) != expected:
            raise ValueError(f'Componente alterado: {path}')
    w = read(art / f'{year}_joint1_weights.json')
    if any(y + 2 > year for y in w['calibration_blocks']):
        raise ValueError('Calibração temporal inválida')
    # A ordem é explicitada pelos nomes, sem depender da ordem do JSON.
    base = ROOT / 'data/processed/round9'
    first = [np.load(base / f'{year}_{name}.npy') for name in ('s02', 'modes', 'local18', 'pls16')]
    s09 = np.load(ROOT / f'data/processed/round10/{year}_s09.npy')
    tropical = np.load(ROOT / f'data/processed/round11/{year}_fine32.npy')
    pieces = np.stack(first + [blend(s09, tropical, 1.)]).astype(float)
    pred = combine(pieces, np.asarray(w['weights']))
    saved = art / f'{year}_joint1.npy'
    np.testing.assert_array_equal(pred, np.load(saved))
    return pred


def audit_rain():
    expected = read(ROOT / 'delivery/s11/evidence/official_sources.json')['treino_tp.nc']
    if digest(RAW / 'treino_tp.nc') != expected:
        raise ValueError('Chuva oficial alterada')
    cached = np.load(CACHE / 'tp.npy', mmap_mode='r')
    with xr.open_dataset(RAW / 'treino_tp.nc') as ds:
        for start in range(0, 996, 48):
            np.testing.assert_array_equal(cached[start:start+48], ds.tp.isel(time=slice(start,start+48)).values)
    return dict(official_tp_sha256=expected, cache_equal=True)


def statistics(pred, truth):
    delta = pred - truth
    return dict(n=int(delta.size), sum_error=float(delta.sum()),
                sum_squared_error=float(np.sum(delta**2)),
                sum_observed=float(truth.sum()), sum_predicted=float(pred.sum()))


def describe(accumulator):
    result = {}
    for family, values in accumulator.items():
        total = sum(v['sum_squared_error'] for v in values.values())
        result[family] = []
        for name, v in values.items():
            n = v['n']
            result[family].append(dict(group=name, count=n, rmse=float(np.sqrt(v['sum_squared_error']/n)),
                bias=v['sum_error']/n, mean_observed=v['sum_observed']/n,
                mean_predicted=v['sum_predicted']/n, sse_fraction=v['sum_squared_error']/total,
                count_fraction=n/sum(z['n'] for z in values.values())))
    return result


def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    OUT.mkdir(parents=True, exist_ok=True)
    audit = audit_rain()
    tp = np.load(CACHE/'tp.npy', mmap_mode='r')
    lat, lon = np.meshgrid(np.arange(-60,15.01,.25),np.arange(-90,-24.99,.25),indexing='ij')
    acc = {}; hashes = {}; monthly_bias = []; spatial_bias = []
    def add(family, name, p, y):
        if not p.size:
            return
        value = statistics(p, y)
        dest = acc.setdefault(family, {}).setdefault(str(name), {key: 0 for key in value})
        for key in value:
            dest[key] += value[key]
    for cutoff in YEARS:
        pred = verified_prediction(cutoff)
        truth = tp[target_origins(cutoff)+1].astype(float)
        hashes[str(cutoff)] = digest(ROOT / f'data/processed/round15/{cutoff}_joint1.npy')
        monthly_bias.extend((pred-truth).mean(axis=(1,2)).tolist())
        spatial_bias.append((pred-truth).mean(axis=0))
        add('global', '2009–2020', pred, truth)
        for m in range(12): add('mes', m+1, pred[m::12], truth[m::12])
        for offset in (0,1): add('ano', cutoff+offset, pred[12*offset:12*(offset+1)], truth[12*offset:12*(offset+1)])
        for name, months in [('DJF',[11,0,1]),('MAM',[2,3,4]),('JJA',[5,6,7]),('SON',[8,9,10])]:
            take=np.isin(np.arange(24)%12, months)
            add('estacao',name,pred[take],truth[take])
        for lower,upper in [(-60,-30),(-30,-15),(-15,0),(0,15.01)]:
            mask=(lat>=lower)&(lat<upper)
            add('latitude',f'{lower}:{upper}',pred[:,mask],truth[:,mask])
        for a in range(-60,15,15):
            for b in range(-90,-25,10):
                mask=(lat>=a)&(lat<(a+15 if a<0 else 15.01))&(lon>=b)&(lon<min(b+10,-24.99))
                add('regiao',f'lat {a}:{a+15}, lon {b}:{min(b+10,-25)}',pred[:,mask],truth[:,mask])
        edges=[0,.5,2,5,10,20,np.inf]
        for name, field in [('chuva_observada',truth),('chuva_prevista',pred)]:
            for lo,hi in zip(edges[:-1],edges[1:]):
                mask=(field>=lo)&(field<hi)
                add(name,f'{lo}:{hi}',pred[mask],truth[mask])
        print('DIAGNÓSTICO',cutoff,flush=True)
    result = describe(acc)
    result.update(audit=audit, prediction_hashes=hashes, development_only=True,
                  reused_periods=True, observed_intensity_is_diagnostic_only=True,
                  spatial_bias_rms=float(np.sqrt(np.mean(np.mean(spatial_bias,axis=0)**2))),
                  monthly_global_bias_rms=float(np.sqrt(np.mean(np.asarray(monthly_bias)**2))))
    save_json(OUT/'diagnostic.json',result)
    lines=['# Diagnóstico histórico S11 — 2009–2020','',
           'Previsões fora do treino, períodos já reutilizados na seleção. Somente dados oficiais.',
           f"RMSE: {result['global'][0]['rmse']:.6f}; viés médio: {result['global'][0]['bias']:.6f} mm/dia.",'']
    for family,title in [('latitude','Faixas de latitude'),('estacao','Estações'),('chuva_observada','Intensidade observada'),('chuva_prevista','Intensidade prevista'),('regiao','Regiões com maior participação no erro')]:
        lines += [f'## {title}','','| Grupo | RMSE | Viés previsão − observado | % do erro quadrático | % das amostras |','| --- | ---: | ---: | ---: | ---: |']
        rows=sorted(result[family],key=lambda v:-v['sse_fraction'])
        if family=='regiao': rows=rows[:10]
        for v in rows: lines.append(f"| {v['group']} | {v['rmse']:.4f} | {v['bias']:.4f} | {100*v['sse_fraction']:.2f}% | {100*v['count_fraction']:.2f}% |")
        lines += ['']
    lines += ['Classes de chuva observada usam o alvo apenas para análise; não são atributos disponíveis na inferência.',
              'Subestimação condicionada a valores observados altos não prova, por si só, que multiplicar todas as previsões melhora o RMSE.',
              'Nenhuma nova candidata ou submissão foi produzida pelo diagnóstico.']
    (OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(result['global'],ensure_ascii=False),flush=True)


if __name__=='__main__': main()
