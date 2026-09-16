"""Reproduzir versões registradas, sem pesquisa, promoção ou envio ao Kaggle.

Uso: python -m src.reproducao listar
Veja docs/REPRODUCAO.md. Os componentes finais são retreinados; a calibração
usa as evidências históricas congeladas, não uma nova busca de modelos.
"""
from __future__ import annotations
import argparse
import platform
import sys
import time
from pathlib import Path
from . import s11_delivery as motor

ROOT = Path(__file__).resolve().parents[1]
CATALOGO = ROOT / 'configs/modelos.json'


def resolver(versao, catalogo=None):
    catalogo = catalogo or motor.read(CATALOGO)
    if versao == 'melhor':
        versao = catalogo['melhor_publica']
    if versao not in catalogo['versoes']:
        raise ValueError(f'Versão não registrada: {versao}')
    if catalogo['versoes'][versao]['motor'] != 's11_delivery':
        raise ValueError('A versão exige um motor de reprodução ainda não implementado')
    return versao, catalogo['versoes'][versao]


def validar_entradas(c, catalogo):
    for nome, esperado in catalogo['evidencias_sha256'].items():
        if motor.digest(c['evidence'] / nome) != esperado:
            raise ValueError(f'Evidência congelada alterada: {nome}')
    if motor.digest(c['raw'] / 'sample_submission.csv') != catalogo['sample_sha256']:
        raise ValueError('O sample oficial difere da versão utilizada na geração original')


def verificar(c, registro):
    """Comparar com um hash independente, preservado antes da reprodução."""
    csv = c['output'] / f"{c['version']}_reproduction.csv"
    atual = motor.digest(csv)
    if atual != registro['csv_sha256']:
        raise ValueError(f'CSV diferente do original: {atual}; esperado {registro["csv_sha256"]}')
    # Mesmo hash atesta todos os bytes. Também documentar a estrutura explicitamente.
    import numpy as np
    import pandas as pd
    frame = pd.read_csv(csv)
    sample = pd.read_csv(c['raw'] / 'sample_submission.csv', usecols=['id'])
    if list(frame.columns) != ['id', 'tp_mm_day'] or len(frame) != 1885464:
        raise ValueError('Colunas ou número de linhas incorretos')
    if not frame.id.equals(sample.id) or not frame.id.is_unique:
        raise ValueError('IDs ou ordem diferentes do sample oficial')
    if not np.isfinite(frame.tp_mm_day).all() or (frame.tp_mm_day < 0).any():
        raise ValueError('Precipitação inválida')
    relatorio = dict(versao=c['version'], csv_sha256=atual, identico_ao_original=True,
                     linhas=len(frame), ordem_oficial=True, apenas_dados_oficiais=True,
                     nova_candidata=False, enviado=False,
                     escopo='Treino final + inferência; calibração histórica congelada')
    motor.write(c['output'] / 'verificacao.json', relatorio)
    print(f"VERIFICADO: {c['version'].upper()} idêntica ao CSV original ({len(frame)} linhas)")
    return relatorio


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('etapa', choices=('listar', 'preparar', 'treinar', 'prever', 'verificar'))
    parser.add_argument('--versao', default='melhor', help='s10, s11 ou melhor (melhor score público registrado)')
    parser.add_argument('--settings', type=Path, default=ROOT / 'configs/reproducao.json')
    args = parser.parse_args()
    catalogo = motor.read(CATALOGO)
    if args.etapa == 'listar':
        for nome, registro in catalogo['versoes'].items():
            print(f"{nome.upper()}: {registro['public_rmse']:.5f} — {registro['situacao']}")
        print(f"Melhor pública: {catalogo['melhor_publica']}; controle: {catalogo['controle_aprovado']}")
        print('Critério histórico ativo: ganho mínimo relativo de 0,3%, além das condições de estabilidade.')
        return
    versao, registro = resolver(args.versao, catalogo)
    c = motor.settings(args.settings)
    c['version'] = versao
    c['output'] = c['output'] / versao
    validar_entradas(c, catalogo)
    inicio = time.perf_counter()
    if args.etapa == 'verificar':
        verificar(c, registro)
    else:
        etapa = {'preparar': motor.prepare, 'treinar': motor.train, 'prever': motor.predict}[args.etapa]
        etapa(c)
        if args.etapa == 'prever':
            verificar(c, registro)
    import psutil
    import importlib.metadata
    memoria = psutil.Process().memory_info()
    motor.write(c['output'] / f'{args.etapa}_execucao.json', dict(
        versao=versao, etapa=args.etapa, segundos=time.perf_counter()-inicio,
        pico_memoria_bytes=getattr(memoria, 'peak_wset', None),
        python=platform.python_version(), plataforma=platform.platform(), threads=1,
        cpu_logicos=psutil.cpu_count(), ram_bytes=psutil.virtual_memory().total,
        pacotes={p: importlib.metadata.version(p) for p in
                 ('numpy', 'scipy', 'scikit-learn', 'pandas', 'xarray', 'joblib', 'netCDF4')}))
    print(f"Etapa {args.etapa} concluída. Saídas: {c['output']}")


if __name__ == '__main__':
    main()
