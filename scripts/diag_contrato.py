r"""O que teste_features.nc realmente entrega?

`competition.audit()` verifica que `v[0]` de cada variavel bate com o ultimo
mes de treino (2022-12), mas NAO verifica nada sobre `v[1..23]`. Essa lacuna
decide qual e o problema de verdade:

  CENARIO A -- as 24 entradas sao estados atmosfericos REAIS dos meses de
  origem 2022-12 a 2024-11. Entao cada alvo tem a atmosfera do mes anterior
  observada, o problema e de 1 mes de antecedencia, e a convencao OOF do
  pipeline (origem o -> alvo o+1) esta alinhada com o teste.

  CENARIO B -- as 24 entradas repetem o mesmo campo, ou sao previsoes, ou
  degradam com o lag. Entao o problema real e prever 24 horizontes a partir
  de uma unica origem (lag_meses = 1..24), com antecedencia media de 12,5
  meses. Toda a validacao OOF de 1 mes estaria medindo uma tarefa MUITO mais
  facil que a tarefa avaliada, e o modelo certo seria outro.

O script nao decide nada sozinho: ele imprime a estrutura do arquivo e as
estatisticas que distinguem os dois cenarios.

Nao treina modelo, nao gera CSV, nao cria submissao.

Uso (na raiz do repositorio, com o venv ativado):

    .\.venv\Scripts\python.exe scripts\diag_contrato.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import xarray as xr

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.competition import CACHE, RAW, VARIABLES


def main() -> None:
    path = RAW / 'teste_features.nc'
    print(f'=== Estrutura de {path.name} ===')
    with xr.open_dataset(path) as ds:
        print(ds)
        print('\n--- coordenadas ---')
        for name in ('time', 'time_origem', 'lag_meses'):
            if name in ds.coords or name in ds.variables:
                v = np.asarray(ds[name].values)
                print(f'{name:<14} n={v.size}  primeiro={v[0]}  ultimo={v[-1]}')

        print('\n=== As 24 entradas variam entre si? ===')
        print(f'{"variavel":<20}{"identicas a v[0]":>18}{"desvio entre k":>16}'
              f'{"desvio espacial":>17}{"corr v[0] vs v[23]":>20}')
        for name in VARIABLES:
            v = np.asarray(ds[name].values, np.float64)
            flat = v.reshape(v.shape[0], -1)
            same = int(sum(np.allclose(flat[k], flat[0], equal_nan=True)
                           for k in range(1, flat.shape[0])))
            across = float(np.nanmean(np.nanstd(flat, axis=0)))
            spatial = float(np.nanmean(np.nanstd(flat, axis=1)))
            a, b = flat[0], flat[-1]
            good = np.isfinite(a) & np.isfinite(b)
            c = float(np.corrcoef(a[good], b[good])[0, 1]) if good.sum() > 100 else float('nan')
            print(f'{name:<20}{f"{same}/{flat.shape[0]-1}":>18}{across:>16.5g}'
                  f'{spatial:>17.5g}{c:>20.3f}')

        print('\n=== Alguma entrada k>0 e copia de um mes de treino? ===')
        probe = 'u_850'
        train = np.load(CACHE / f'{probe}.npy', mmap_mode='r')
        tail = np.asarray(train[-6:], np.float64).reshape(6, -1)
        v = np.asarray(ds[probe].values, np.float64)
        flat = v.reshape(v.shape[0], -1)
        for k in (0, 1, 2, 12, 23):
            if k >= flat.shape[0]:
                continue
            hits = [i for i in range(6) if np.allclose(flat[k], tail[i], equal_nan=True)]
            label = ', '.join(f'treino[-{6-i}]' for i in hits) if hits else 'nenhum dos 6 ultimos'
            print(f'{probe} k={k:<3} igual a: {label}')

        if 'tp_ultima_obs' in ds:
            tp = np.load(CACHE / 'tp.npy', mmap_mode='r')
            u = np.asarray(ds.tp_ultima_obs.values, np.float64)
            print(f'\ntp_ultima_obs: shape={u.shape}  '
                  f'igual a tp[-1]: {np.allclose(u.reshape(-1), np.asarray(tp[-1], np.float64).reshape(-1))}')

    sub = RAW / 'sample_submission.csv'
    if sub.exists():
        with sub.open(encoding='utf-8') as f:
            header = f.readline().strip()
            first = f.readline().strip()
            n = 2 + sum(1 for _ in f)
        print(f'\n=== {sub.name} ===')
        print(f'cabecalho : {header}')
        print(f'1a linha  : {first}')
        print(f'linhas    : {n-1} (24 x 78561 = {24*78561})')

    print('\nLeitura: se a coluna "identicas a v[0]" for 23/23, e CENARIO B --'
          '\numa unica origem, 24 horizontes, e sua validacao OOF de 1 mes esta'
          '\nmedindo outra tarefa. Se for 0/23 com correlacao v[0] vs v[23] baixa,'
          '\ne CENARIO A e a convencao do pipeline esta correta.')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
