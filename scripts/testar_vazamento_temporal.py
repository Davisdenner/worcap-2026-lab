r"""Prova mecânica de que a previsão de cada mês não usa nenhuma outra linha
do `teste_features.nc`.

POR QUE ISTO EXISTE. As linhas do arquivo de teste se sobrepõem: os campos
atmosféricos que a linha de 2023-02 traz como "mês de origem" são o estado de
2023-01, que é o ALVO da linha anterior. Para 23 dos 24 meses existe, dentro do
próprio arquivo oficial, o estado atmosférico do mês que deveria ser previsto.
Usá-lo transforma previsão em estimativa, e a organização declarou que isso
está fora das regras.

Ler o código sugere que este pipeline não faz isso: `round19_history.feature_rows`
indexa `fields[j][origin, cells]` com um escalar e `s12_delivery.predict` passa
`origin = month`. Mas leitura de código não é demonstração.

MÉTODO. Caixa-preta, atacando o arquivo de entrada. Embaralhamos as linhas de
uma paridade (pares ou ímpares) entre si e deixamos a outra metade intacta.
Então, numa única execução:

  invariância  Os 12 meses da paridade INTACTA têm de sair bit a bit idênticos.
               Se algum lesse uma linha embaralhada, mudaria.
  controle     Os 12 meses da paridade EMBARALHADA têm de MUDAR. Isso prova
               que o teste tem poder de detecção, e vem de graça na mesma
               execução.

Duas execuções cobrem os 24 meses nos dois papéis. O embaralhamento é uma
permutação sem ponto fixo das próprias linhas, não ruído: os campos continuam
fisicamente reais e finitos, só pertencem ao mês errado.

ALCANCE, dito com precisão. A partição por paridade detecta vazamento entre
linhas de paridades diferentes, o que inclui **todo par adjacente** — e
adjacência é exatamente o mecanismo que existe neste arquivo, já que a linha
i+1 carrega a atmosfera do alvo da linha i. Um vazamento entre linhas da mesma
paridade (distância 2, 4, ...) não seria visto; `--distancia3` troca a partição
para módulo 3 e cobre também esses, ao custo de três execuções por camada.

DUAS CAMADAS. O pipeline recusa-se a prosseguir se a base S11 reproduzida não
bater com o hash oficial (`s12_delivery.predict`, "Base S11 não reproduzida").
Isso é uma guarda de integridade correta — não se alimenta o pipeline com um
arquivo adulterado e se obtém submissão — mas impede medir as duas camadas de
uma vez. Então cada partição roda duas vezes:

  camada S11  execução direta com o teste perturbado. Ela morre na guarda, mas
              só depois de escrever `s11_reproduction.nc`, que é o que
              comparamos.
  camada S12  a base S11 de referência é copiada por cima, a guarda passa, e a
              inferência do corretor roda lendo o teste perturbado. Com a base
              fixa, qualquer diferença veio exclusivamente de `fields`.

Nenhuma submissão é gerada e nenhum modelo é retreinado: só reexecuta a
inferência sobre os componentes já treinados.

Pré-requisito: `s12_corrector.joblib` e `s12_manifest.json` já presentes na
pasta `models`. Se existirem de uma execução anterior, NÃO rode `treinar` de
novo — ele recusa sobrescrever e levanta `FileExistsError`, que é proteção e
não erro. A checagem abaixo diz se falta alguma coisa.

Uso (na raiz do repositório):

    .\.venv\Scripts\python.exe scripts\testar_vazamento_temporal.py
    .\.venv\Scripts\python.exe scripts\testar_vazamento_temporal.py --distancia3

Cerca de sete minutos no modo padrão.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import xarray as xr

REPO_ROOT = Path(__file__).resolve().parent.parent
SETTINGS = REPO_ROOT / 'configs' / 'reproducao.json'
WORK = REPO_ROOT / 'data' / 'processed' / 'vazamento'
OUT_JSON = REPO_ROOT / 'reports' / 'competition' / 'vazamento_temporal.json'
MESES = 24
SEED = 20260920

VARIAVEIS = ('cloud_cover', 'geopotential_850', 'rel_hum_850', 'shum_850',
             'surface_pressure', 't2', 'temperature_850', 'u_850', 'v_850')


def rotulo_mes(m: int) -> str:
    return f'{2023 + m // 12}-{m % 12 + 1:02d}'


def caminhos_absolutos() -> dict:
    bruto = json.loads(SETTINGS.read_text(encoding='utf-8'))
    base = SETTINGS.resolve().parent
    return {k: (base / v).resolve() for k, v in bruto.items()}


def permutacao(rng: np.random.Generator, moveis: list[int]) -> np.ndarray:
    """Desloca `moveis` entre si sem deixar nenhum no lugar."""
    if len(moveis) < 2:
        raise ValueError('Preciso de ao menos duas linhas para embaralhar')
    ordem = np.arange(MESES)
    for _ in range(1000):
        sorteio = rng.permutation(moveis)
        if all(a != b for a, b in zip(moveis, sorteio)):
            ordem[moveis] = sorteio
            return ordem
    raise RuntimeError('Não consegui construir um deslocamento sem ponto fixo')


def escrever_teste(origem: Path, destino: Path, ordem: np.ndarray) -> None:
    """Copia o teste_features.nc reordenando SÓ as variáveis atmosféricas."""
    with xr.open_dataset(origem) as ds:
        faltando = [v for v in VARIAVEIS if v not in ds.variables]
        if faltando:
            raise ValueError(f'Variáveis ausentes no teste_features.nc: {faltando}')
        novo = ds.load().copy(deep=True)
        for nome in VARIAVEIS:
            novo[nome].values = ds[nome].values[ordem]
        # time, time_origem, lag_meses e tp_ultima_obs ficam intactos: quem muda
        # de lugar é só o estado atmosférico, o único canal por onde um
        # vazamento entre linhas teria de passar.
        destino.parent.mkdir(parents=True, exist_ok=True)
        novo.to_netcdf(destino)


def montar_raw(raw_original: Path, destino: Path, teste: Path) -> None:
    """Pasta raw com os oficiais (hardlink) e o teste indicado (cópia)."""
    destino.mkdir(parents=True, exist_ok=True)
    for arquivo in raw_original.iterdir():
        if not arquivo.is_file() or arquivo.name == 'teste_features.nc':
            continue
        alvo = destino / arquivo.name
        if alvo.exists():
            continue
        try:
            os.link(arquivo, alvo)
        except OSError:
            shutil.copy2(arquivo, alvo)
    shutil.copy2(teste, destino / 'teste_features.nc')


def escrever_settings(config: dict, raw: Path, saida: Path) -> Path:
    saida.mkdir(parents=True, exist_ok=True)
    ajuste = saida / 'reproducao.json'
    ajuste.write_text(json.dumps({
        'raw': str(raw), 'cache': str(config['cache']),
        'models': str(config['models']), 'output': str(saida / 'saidas'),
        'evidence': str(config['evidence']),
        's12_evidence': str(config['s12_evidence']),
    }, indent=2), encoding='utf-8')
    return ajuste


def prever(ajuste: Path, rotulo: str) -> subprocess.CompletedProcess:
    inicio = time.perf_counter()
    processo = subprocess.run(
        [sys.executable, '-m', 'src.reproducao', 'prever', '--versao', 's12',
         '--settings', str(ajuste)],
        cwd=REPO_ROOT, capture_output=True, text=True,
        encoding='utf-8', errors='replace')
    print(f'  {rotulo}: {time.perf_counter() - inicio:.0f}s')
    return processo


def exigir(caminho: Path, processo: subprocess.CompletedProcess, rotulo: str) -> Path:
    if caminho.exists():
        return caminho
    print((processo.stdout or '')[-1500:] or '(sem stdout)')
    print((processo.stderr or '')[-1500:] or '(sem stderr)', file=sys.stderr)
    raise RuntimeError(f'{rotulo}: nao produziu {caminho.name}')


def campo(nc: Path, mes: int) -> np.ndarray:
    with xr.open_dataset(nc) as ds:
        return np.array(ds.tp_mm_day.values[mes], dtype=np.float64)


def comparar(ref_nc: Path, novo_nc: Path, intactos: list[int],
             embaralhados: list[int], camada: str) -> list[dict]:
    """Invariância nos meses intactos, controle negativo nos embaralhados."""
    linhas = []
    for mes in range(MESES):
        base, obtido = campo(ref_nc, mes), campo(novo_nc, mes)
        desvio = float(np.abs(base - obtido).max())
        igual = bool(np.array_equal(base, obtido))
        if mes in intactos:
            papel, ok = 'invariancia', igual
        elif mes in embaralhados:
            papel, ok = 'controle', not igual
        else:
            continue
        linhas.append(dict(camada=camada, mes=mes, rotulo=rotulo_mes(mes),
                           papel=papel, desvio_maximo=desvio, aprovado=ok))
    falhas = [l for l in linhas if not l['aprovado']]
    inv = [l for l in linhas if l['papel'] == 'invariancia']
    ctl = [l for l in linhas if l['papel'] == 'controle']
    print(f'    {camada}: {len(inv)} meses intactos, desvio maximo '
          f'{max(l["desvio_maximo"] for l in inv):.3e}')
    print(f'    {camada}: {len(ctl)} meses embaralhados, desvio minimo '
          f'{min(l["desvio_maximo"] for l in ctl):.3e}')
    for l in falhas:
        if l['papel'] == 'invariancia':
            print(f'    FALHA  {l["rotulo"]} mudou sem sua linha ter sido tocada '
                  f'(desvio {l["desvio_maximo"]:.3e})')
        else:
            print(f'    INCONCLUSIVO  {l["rotulo"]} nao mudou mesmo com a linha '
                  f'embaralhada; o teste nao detecta nada aqui')
    return linhas


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--distancia3', action='store_true',
                        help='particiona por modulo 3 em vez de paridade')
    args = parser.parse_args()

    modulo = 3 if args.distancia3 else 2
    config = caminhos_absolutos()
    raw_original = config['raw']
    teste_original = raw_original / 'teste_features.nc'
    if not teste_original.exists():
        raise SystemExit(f'Nao encontrei {teste_original}')
    faltam = [n for n in ('s12_corrector.joblib', 's12_manifest.json',
                          'manifest.json', 'preprocessing.joblib')
              if not (config['models'] / n).exists()]
    if faltam:
        raise SystemExit(f'Faltam componentes treinados em {config["models"]}: '
                         + ', '.join(faltam)
                         + '\nRode: src.reproducao preparar --versao s12 e depois treinar --versao s12')

    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    rng = np.random.default_rng(SEED)

    print('Referencia: previsao com o arquivo oficial intacto')
    montar_raw(raw_original, WORK / 'ref' / 'raw', teste_original)
    ajuste = escrever_settings(config, WORK / 'ref' / 'raw', WORK / 'ref')
    proc = prever(ajuste, 'referencia')
    ref_s12 = exigir(WORK / 'ref/saidas/s12/s12_reproduction.nc', proc, 'referencia')
    ref_base = WORK / 'ref/saidas/s12/base_s11'
    ref_s11 = exigir(ref_base / 's11_reproduction.nc', proc, 'referencia')

    linhas = []
    for classe in range(modulo):
        embaralhados = [m for m in range(MESES) if m % modulo == classe]
        intactos = [m for m in range(MESES) if m % modulo != classe]
        print(f'\nParticao {classe + 1}/{modulo}: embaralhando '
              f'{len(embaralhados)} linhas, preservando {len(intactos)}')

        tag = WORK / f'p{classe}'
        escrever_teste(teste_original, tag / 'teste_features.nc',
                       permutacao(rng, embaralhados))
        montar_raw(raw_original, tag / 'raw', tag / 'teste_features.nc')
        ajuste = escrever_settings(config, tag / 'raw', tag)

        # Camada S11: morre na guarda de integridade, mas escreve o NetCDF antes.
        proc = prever(ajuste, 'camada S11')
        nc = exigir(tag / 'saidas/s12/base_s11/s11_reproduction.nc', proc, 'camada S11')
        linhas += comparar(ref_s11, nc, intactos, embaralhados, 'S11')

        # Camada S12: base de referencia por cima, para isolar o corretor.
        shutil.rmtree(tag / 'saidas/s12/base_s11')
        shutil.copytree(ref_base, tag / 'saidas/s12/base_s11')
        proc = prever(ajuste, 'camada S12')
        nc = exigir(tag / 'saidas/s12/s12_reproduction.nc', proc, 'camada S12')
        linhas += comparar(ref_s12, nc, intactos, embaralhados, 'S12')

    aprovado = all(l['aprovado'] for l in linhas)
    print('\n' + '=' * 66)
    print('APROVADO: cada mes depende exclusivamente da sua propria linha.'
          if aprovado else
          'REPROVADO ou INCONCLUSIVO: veja as linhas marcadas acima.')
    print('=' * 66)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(dict(
        pergunta='A previsao de cada mes usa alguma outra linha do teste_features.nc?',
        metodo=('Particao das 24 linhas por modulo; embaralhamento sem ponto fixo '
                'de uma classe; invariancia nas demais e controle negativo na classe '
                'embaralhada. Duas camadas: S11 direta e corretor S12 com base fixa.'),
        modulo=modulo, variaveis_embaralhadas=list(VARIAVEIS), semente=SEED,
        alcance=('Detecta vazamento entre linhas de classes diferentes, o que inclui '
                 'todo par adjacente -- o unico mecanismo presente neste arquivo.'),
        comparacoes=linhas, aprovado=aprovado,
        csv_gerado=False, submissao=False,
    ), indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'\nRelatorio: {OUT_JSON}')
    print(f'Area de trabalho: {WORK} (apague quando quiser)')
    return 0 if aprovado else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
