r"""As submissões que já existem se combinam melhor do que qualquer uma delas?

CONTEXTO. As 36 rodadas mexeram todas no mesmo lugar: o corretor que se soma à
S11. A grade de frações da Rodada 36 mostra que essa família chegou ao fim — o
melhor resultado é +0,076%, dentro do piso de ruído amostral de ~0,1%.

Uma direção nunca testada: combinar previsões que já existem. A S10 difere da
S12 em DUAS coisas -- a recalibração conjunta de pesos (S10 -> S11) e o corretor
não linear (S11 -> S12) -- enquanto todas as variantes testadas diferem só na
segunda. Se os erros da S10 e da S12 forem suficientemente descorrelacionados,
a combinação bate as duas.

ARITMÉTICA. Para dois preditores com erros de desvio e1, e2 e correlação rho, a
combinação linear ótima tem erro

    e² = e1²·e2²·(1 − rho²) / (e1² + e2² − 2·rho·e1·e2)

Com e1=1,71456 e e2=1,71895 (os scores públicos de S12 e S10), essa fórmula dá:

    rho     RMSE combinado    ganho     peso na S12
    0,999      1,71353       0,00103        1,774
    0,995      1,71405       0,00051        0,756
    0,990      1,71218       0,00238        0,628
    0,985      1,71012       0,00444        0,585
    0,980      1,70801       0,00655        0,564
    0,970      1,70374       0,01082        0,543

Duas coisas a notar, porque elas mudam o desenho do teste. O ganho NÃO é
monótono em rho: perto da colinearidade a combinação ótima extrapola para fora
do intervalo entre os dois modelos (peso 1,774 em rho=0,999) e volta a "ganhar"
muito. Isso é a miragem da Rodada 27 outra vez -- ganho grande disponível
apenas com um peso que você não tem como saber. Por isso **rho alto não
encerra a linha sozinho, e rho baixo não a aprova**: o que decide é se o peso
é estimável.

CRITÉRIOS DECLARADOS ANTES DE RODAR.

  1. O ganho ORACLE (peso ajustado sabendo o alvo) precisa alcançar 0,3%, o
     mesmo limiar de promoção do projeto. Abaixo disso não há o que perseguir,
     porque o causal nunca supera o oracle.
  2. ESTABILIDADE DO PESO. O peso ótimo de cada bloco tem de ficar numa faixa
     estreita: amplitude máxima de 0,5 entre o menor e o maior, e todos dentro
     de [0, 1,5]. Se os pesos oscilarem como os alphas do diagnóstico de
     climatologia oscilaram (0,07 a 0,72), o estimador causal não tem chance e
     o oracle é decorativo.
  3. O ganho CAUSAL -- peso ajustado só em blocos anteriores -- precisa ser
     positivo em pelo menos 4 dos 5 blocos avaliados.

A distância entre oracle e causal é a parede de estimação deste projeto: nove
métodos com de um a 78.561 parâmetros ficaram em ±0,1% enquanto seus oracles
mediam 0,30% a 2,45%. Aqui o estimador tem UM parâmetro, o que é o melhor caso
possível -- e mesmo assim o diagnóstico de janela de climatologia mostrou que
um escalar global não se deixa estimar com cinco blocos. Espere o pior.

Não treina modelo, não lê alvo de teste, não gera CSV, não cria submissão.
Todos os arrays já estão em cache; a execução é de poucos minutos.

Uso (na raiz do repositório):

    .\.venv\Scripts\python.exe scripts\diag_combinacao.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src import round20
from src.competition import CACHE, ROOT
from src.diagnose_s11 import verified_prediction
from src.round11 import blend
from src.round2 import target_origins

YEARS = (2009, 2011, 2013, 2015, 2017, 2019)
EVAL = YEARS[1:]          # o primeiro bloco não tem anterior para ajuste causal
OUT_DIR = ROOT / 'reports' / 'competition' / 'combinacao_diagnostic'
GANHO_ORACLE_MINIMO = 0.003
AMPLITUDE_MAXIMA_PESO = 0.5
FAIXA_PESO = (0.0, 1.5)


def s10(year: int) -> np.ndarray:
    """A S10 é a quinta componente do conjunto: o tropical fino sobre a S09."""
    s09 = np.load(ROOT / f'data/processed/round10/{year}_s09.npy')
    fine = np.load(ROOT / f'data/processed/round11/{year}_fine32.npy')
    return blend(s09, fine, 1.).astype(np.float64)


def rmse(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x * x)))


def peso_otimo(ea: np.ndarray, eb: np.ndarray) -> float:
    """w que minimiza ||w·ea + (1−w)·eb||, sem restringir a [0,1]."""
    d = ea - eb
    denominador = float(d @ d)
    if denominador <= 0:
        return 1.0
    return float(-(eb @ d) / denominador)


def teto_teorico(e1: float, e2: float, rho: float) -> float:
    denominador = e1 ** 2 + e2 ** 2 - 2 * rho * e1 * e2
    if denominador <= 0:
        return float('nan')
    return float(np.sqrt(e1 ** 2 * e2 ** 2 * (1 - rho ** 2) / denominador))


def main() -> None:
    tp = np.load(CACHE / 'tp.npy', mmap_mode='r')
    blocos = {}

    for year in YEARS:
        alvos = target_origins(year) + 1
        verdade = np.asarray(tp[alvos], np.float64).reshape(-1)
        a = np.asarray(round20.reference(year), np.float64).reshape(-1)   # S12
        b = s10(year).reshape(-1)                                          # S10
        c = np.asarray(verified_prediction(year), np.float64).reshape(-1)  # S11
        e12, e10, e11 = a - verdade, b - verdade, c - verdade

        rho_10 = float(np.corrcoef(e12, e10)[0, 1])
        rho_11 = float(np.corrcoef(e12, e11)[0, 1])
        blocos[year] = dict(
            rmse_s12=rmse(e12), rmse_s11=rmse(e11), rmse_s10=rmse(e10),
            rho_s12_s10=rho_10, rho_s12_s11=rho_11,
            peso_otimo_s12=peso_otimo(e12, e10),
            rmse_oracle=rmse(peso_otimo(e12, e10) * e12
                             + (1 - peso_otimo(e12, e10)) * e10),
            produtos=dict(aa=float(e12 @ e12), bb=float(e10 @ e10),
                          ab=float(e12 @ e10), n=int(e12.size)),
        )
        print(f'[bloco] {year}  rho(S12,S10)={rho_10:.4f}  '
              f'rho(S12,S11)={rho_11:.4f}  w*={blocos[year]["peso_otimo_s12"]:.3f}',
              flush=True)
        del verdade, a, b, c, e12, e10, e11

    rho_medio = float(np.mean([b['rho_s12_s10'] for b in blocos.values()]))
    print('\n=== Correlacao dos erros ===')
    print(f'{"bloco":<8}{"RMSE S12":>12}{"RMSE S11":>12}{"RMSE S10":>12}'
          f'{"rho(12,10)":>12}{"w*":>8}{"oracle":>12}')
    for year, b in blocos.items():
        print(f'{year:<8}{b["rmse_s12"]:>12.6f}{b["rmse_s11"]:>12.6f}'
              f'{b["rmse_s10"]:>12.6f}{b["rho_s12_s10"]:>12.4f}'
              f'{b["peso_otimo_s12"]:>8.3f}{b["rmse_oracle"]:>12.6f}')

    # Agregado: RMSE conjunto sobre todos os blocos, que é a métrica do projeto.
    soma = {k: sum(b['produtos'][k] for b in blocos.values()) for k in ('aa', 'bb', 'ab', 'n')}
    e1, e2 = np.sqrt(soma['aa'] / soma['n']), np.sqrt(soma['bb'] / soma['n'])
    rho_global = soma['ab'] / np.sqrt(soma['aa'] * soma['bb'])
    w_global = (soma['bb'] - soma['ab']) / (soma['aa'] + soma['bb'] - 2 * soma['ab'])
    oracle_global = float(np.sqrt(
        (w_global ** 2 * soma['aa'] + (1 - w_global) ** 2 * soma['bb']
         + 2 * w_global * (1 - w_global) * soma['ab']) / soma['n']))
    ganho_oracle = (e1 - oracle_global) / e1

    print(f'\nAgregado: RMSE S12 {e1:.6f}, RMSE S10 {e2:.6f}, rho {rho_global:.4f}')
    print(f'Peso otimo na S12: {w_global:.4f}  (1 = so S12, 0 = so S10)')
    print(f'Oracle da combinacao: {oracle_global:.6f}  '
          f'ganho {100 * ganho_oracle:.3f}%')
    print(f'Teto teorico pela formula com esse rho: '
          f'{teto_teorico(e1, e2, rho_global):.6f}')

    # Causal: peso ajustado SÓ nos blocos anteriores, aplicado ao bloco corrente.
    print('\n=== Causal: peso dos blocos anteriores aplicado ao bloco corrente ===')
    causal_aa = causal_cc = causal_n = 0.0
    linhas = []
    for year in EVAL:
        anteriores = [y for y in YEARS if y < year]
        p = {k: sum(blocos[y]['produtos'][k] for y in anteriores) for k in ('aa', 'bb', 'ab')}
        w = (p['bb'] - p['ab']) / (p['aa'] + p['bb'] - 2 * p['ab'])
        q = blocos[year]['produtos']
        mse_comb = (w ** 2 * q['aa'] + (1 - w) ** 2 * q['bb']
                    + 2 * w * (1 - w) * q['ab']) / q['n']
        melhora = q['aa'] / q['n'] - mse_comb
        causal_aa += q['aa']; causal_cc += mse_comb * q['n']; causal_n += q['n']
        linhas.append(dict(bloco=year, peso_estimado=float(w),
                           peso_otimo=blocos[year]['peso_otimo_s12'],
                           rmse_s12=float(np.sqrt(q['aa'] / q['n'])),
                           rmse_combinacao=float(np.sqrt(mse_comb)),
                           melhorou=bool(melhora > 0)))
        print(f'{year}: w estimado {w:.3f} contra otimo '
              f'{blocos[year]["peso_otimo_s12"]:.3f}  ->  '
              f'{np.sqrt(q["aa"] / q["n"]):.6f} para {np.sqrt(mse_comb):.6f}  '
              f'{"melhorou" if melhora > 0 else "piorou"}')

    rmse_causal = float(np.sqrt(causal_cc / causal_n))
    rmse_s12_eval = float(np.sqrt(causal_aa / causal_n))
    ganho_causal = (rmse_s12_eval - rmse_causal) / rmse_s12_eval
    positivos = sum(l['melhorou'] for l in linhas)
    print(f'\nCausal agregado: {rmse_s12_eval:.6f} para {rmse_causal:.6f}  '
          f'ganho {100 * ganho_causal:.3f}%  em {positivos}/{len(linhas)} blocos')

    pesos = [b['peso_otimo_s12'] for b in blocos.values()]
    amplitude = float(max(pesos) - min(pesos))
    dentro = all(FAIXA_PESO[0] <= p <= FAIXA_PESO[1] for p in pesos)
    estavel = amplitude <= AMPLITUDE_MAXIMA_PESO and dentro
    print(f'\nPeso otimo por bloco: min {min(pesos):.3f}, max {max(pesos):.3f}, '
          f'amplitude {amplitude:.3f}  '
          f'({"estavel" if estavel else "INSTAVEL"} pelo criterio 2)')

    print('\n=== VEREDITO ===')
    if ganho_oracle < GANHO_ORACLE_MINIMO:
        veredito = (f'Oracle de {100 * ganho_oracle:.3f}% abaixo dos '
                    f'{100 * GANHO_ORACLE_MINIMO:.1f}% declarados. Nem sabendo o peso '
                    'de antemao vale a pena. Linha encerrada pelo criterio 1.')
    elif not estavel:
        veredito = (f'Oracle de {100 * ganho_oracle:.3f}% existe, mas o peso otimo '
                    f'varia de {min(pesos):.3f} a {max(pesos):.3f} entre os blocos. '
                    'O peso nao e estimavel, entao o oracle e decorativo. Linha '
                    'encerrada pelo criterio 2.')
    elif ganho_causal <= 0 or positivos < 4:
        veredito = (f'Oracle de {100 * ganho_oracle:.3f}% existe, mas o causal deu '
                    f'{100 * ganho_causal:.3f}% em {positivos}/{len(linhas)} blocos. '
                    'Mais uma vez a parede de estimacao: o sinal e real e nao se '
                    'deixa estimar.')
    else:
        veredito = (f'CANDIDATA. Causal de {100 * ganho_causal:.3f}% em '
                    f'{positivos}/{len(linhas)} blocos, peso agregado '
                    f'{w_global:.3f} na S12. Vale gerar o CSV.')
    print(veredito)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / 'combinacao.json').write_text(json.dumps(dict(
        pergunta='A combinacao de S10 e S12 bate a S12 sozinha?',
        criterios_declarados=dict(ganho_oracle_minimo=GANHO_ORACLE_MINIMO,
                                  amplitude_maxima_peso=AMPLITUDE_MAXIMA_PESO,
                                  faixa_peso=list(FAIXA_PESO)),
        estabilidade_peso=dict(minimo=float(min(pesos)), maximo=float(max(pesos)),
                               amplitude=amplitude, estavel=estavel),
        blocos={str(y): {k: v for k, v in b.items() if k != 'produtos'}
                for y, b in blocos.items()},
        agregado=dict(rmse_s12=float(e1), rmse_s10=float(e2), rho=float(rho_global),
                      peso_otimo=float(w_global), rmse_oracle=oracle_global,
                      ganho_oracle_percent=100 * float(ganho_oracle)),
        causal=dict(blocos=linhas, rmse_s12=rmse_s12_eval, rmse_combinacao=rmse_causal,
                    ganho_percent=100 * float(ganho_causal),
                    blocos_positivos=positivos, blocos_avaliados=len(linhas)),
        veredito=veredito, somente_dado_oficial=True, treino_novo=False,
        alvo_de_teste_lido=False, csv_gerado=False,
    ), indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"\nGravado em {OUT_DIR / 'combinacao.json'}")


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
