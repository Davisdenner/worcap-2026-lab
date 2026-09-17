"""Diagnóstico descritivo da S12 em seis blocos históricos fora do treino."""
import numpy as np
from . import diagnose_s11 as base
from . import round20
from .competition import CACHE, REPORT, save_json
from .round2 import target_origins
from .round9 import digest

OUT = REPORT / 's12_diagnostic'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    audit = base.audit_rain()
    tp = np.load(CACHE/'tp.npy', mmap_mode='r')
    lat, lon = np.meshgrid(np.arange(-60, 15.01, .25), np.arange(-90, -24.99, .25), indexing='ij')
    acc, hashes = {}, {}

    def add(family, name, pred, truth):
        value = base.statistics(pred, truth)
        dest = acc.setdefault(family, {}).setdefault(str(name), {key: 0 for key in value})
        for key in value:
            dest[key] += value[key]

    for cutoff in base.YEARS:
        pred = round20.reference(cutoff)
        truth = tp[target_origins(cutoff)+1].astype(float)
        hashes[str(cutoff)] = digest(round20.ART/f'{cutoff}_s12.npy')
        add('global', '2009–2020', pred, truth)
        for low, high in [(-60, -30), (-30, -15), (-15, 0), (0, 15.01)]:
            mask = (lat >= low) & (lat < high)
            add('latitude', f'{low}:{high}', pred[:,mask], truth[:,mask])
        for low in range(-60, 15, 15):
            for west in range(-90, -25, 10):
                mask = ((lat >= low) & (lat < min(low+15, 15.01)) &
                        (lon >= west) & (lon < min(west+10, -24.99)))
                add('regiao', f'lat {low}:{low+15}, lon {west}:{min(west+10,-25)}', pred[:,mask], truth[:,mask])
        for offset in (0, 1):
            add('ano', cutoff+offset, pred[12*offset:12*(offset+1)], truth[12*offset:12*(offset+1)])
        print('DIAGNÓSTICO S12', cutoff, flush=True)
    result = base.describe(acc)
    result.update(audit=audit, prediction_hashes=hashes, development_only=True,
                  reused_periods=True, no_test_targets=True, official_only=True)
    save_json(OUT/'diagnostic.json', result)
    lines = ['# Diagnóstico histórico da S12 — 2009–2020', '',
             'Previsões fora do treino, períodos já reutilizados; somente dados oficiais.',
             f"RMSE total: {result['global'][0]['rmse']:.6f} mm/dia.", '']
    for family in ('latitude', 'regiao'):
        lines += [f'## {family.capitalize()}', '', '| Grupo | RMSE | Viés | SSE % | Pontos % |',
                  '| --- | ---: | ---: | ---: | ---: |']
        rows = sorted(result[family], key=lambda r: -r['sse_fraction'])
        if family == 'regiao': rows = rows[:12]
        for r in rows:
            lines.append(f"| {r['group']} | {r['rmse']:.4f} | {r['bias']:.4f} | "
                         f"{100*r['sse_fraction']:.2f}% | {100*r['count_fraction']:.2f}% |")
        lines.append('')
    lines.append('Diagnóstico descritivo: não escolhe modelos, não gera CSV nem acessa alvos de 2023/2024.')
    (OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print('\n'.join(lines), flush=True)


if __name__ == '__main__': main()
