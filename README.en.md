# Monthly precipitation forecasting over South America

Forecasting mean monthly precipitation in mm/day over South America, one month
ahead, on a 301 by 261 grid at 0.25 degrees. Built for the WORCAP 2026
hackathon, organised by the postgraduate programme at INPE, Brazil's National
Institute for Space Research.

Author: Davis Denner ([github.com/Davisdenner](https://github.com/Davisdenner)).
Individual entry. Code under the MIT licence.

**The detailed documentation in this repository is written in Portuguese.**
This file is the English entry point and summarises what the project is, what
it found, and how to reproduce it. Paths to the Portuguese documents are given
throughout, so you can go straight to the source for any claim below.

## Result

Final standing: **11th of 28 homologated teams**, with a combined RMSE of
**1.80817** over 2023 and 2024.

| reference | RMSE | scope |
| --- | ---: | --- |
| 60 year climatology | 1.85468 | 2023, public split |
| this model (S12) | 1.71456 | 2023, public split |
| this model (S12) | 1.80817 | 2023 and 2024 combined, final |

The public leaderboard measured 2023 only and the private one measured 2024.
The two years differ a lot: solving for 2024 alone from the numbers above gives
roughly 1.897, about 10 percent harder than 2023. That gap hit everyone.

Two details worth stating plainly. The official ranking counted only entries
that both submitted to Kaggle before the deadline **and** delivered runnable
code for verification. I moved from 15th on the Kaggle private leaderboard to
11th official because four teams ahead of me did not complete the second
requirement. And the validation used here is conservative rather than
optimistic: out of fold it measured 1.7564 while the 2023 test scored 1.7146.

## The model

```
S12 = max(S11 + 0.25 * corrector, 0)
```

S11 is an ensemble over the official atmospheric fields. The corrector is a
gradient boosted tree trained on S11 residuals using 442,368 out of fold
examples, meaning examples from years the base models never saw during
training. The 0.25 blending fraction was fixed during development and never
retuned afterwards.

Three properties define the system:

**Everything is an anomaly against climatology.** The model predicts the
deviation from what is normal for that month at that point, not the rainfall
itself. The climatology is causal and rebuilt for each evaluation block using
only data available before it.

**Official competition data only**, from version S09 onwards. Earlier versions
S07 and S08 used NOAA sea surface temperature. S07 gained 0.55 percent, and S08
passed development validation and confirmation yet got **worse** on the
leaderboard. That divergence between validation and test is what motivated the
restriction, and it was never lifted.

**Precipitation is never a predictor.** The feature matrix has 55 columns and
none of them is rain. Rain appears only as the label. This keeps training and
test aligned with the contract of the test file, and is part of why validation
comes out conservative.

Method in full: [docs/METODOLOGIA.md](docs/METODOLOGIA.md).
Delivery documentation following Kaggle's winning model guidelines:
[docs/ENTREGA_S12.md](docs/ENTREGA_S12.md).

## Reproduction

The submitted CSV regenerates **byte for byte from an empty clone**, in a fresh
virtual environment with pinned dependencies, in 6.1 minutes. No file is copied
in from outside the repository.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.reproducao preparar  --versao s12
.\.venv\Scripts\python.exe -m src.reproducao treinar   --versao s12
.\.venv\Scripts\python.exe -m src.reproducao prever    --versao s12
.\.venv\Scripts\python.exe -m src.reproducao verificar --versao s12
```

Expected sha256 of the output:
`bba1f8b279447868170b6b2f9b18ee2cc723b891c25627c91438c7725d3aead8`.

That hash was recorded in [configs/modelos.json](configs/modelos.json) **before**
the reproduction was attempted. The ordering matters: a hash computed afterwards
proves nothing.

The whole check is automated in
[scripts/verificar_clone_limpo.ps1](scripts/verificar_clone_limpo.ps1), which
clones the repository into a new directory, reports which required files are
missing from the clone, builds a clean environment, verifies that the two copies
of the pinned dependency list agree, pins the numerical libraries to one thread,
validates every documentation link **inside the clone**, runs the four stages
with timings, and compares the final hash. Report:
[reports/competition/reproducao_clone_limpo.json](reports/competition/reproducao_clone_limpo.json).

The link check runs inside the clone on purpose. Run in the working directory it
sees files that exist on disk but were never committed, and passes. Run in the
clone it sees only what another person would receive.

Step by step guide, including where to obtain the official data:
[docs/REPRODUCAO.md](docs/REPRODUCAO.md).

## What the experiments found

Thirty six rounds ran after S12 and none produced a promotable gain. The
explanation is the durable part of this project, and it is quantified and
reproducible from the JSON files under `reports/competition/`.

**The paired oracle was a mirage.** Round 27 measured an 8.49 percent gap
between S12 and an analogue model, chosen point by point using the observed
value, and five rounds chased it. For two normal errors of similar variance and
correlation rho, that oracle reduces RMSE by a factor of
`sqrt(1 - (2/pi) * sqrt(1 - rho^2))` even when the difference between the two
predictions is pure noise. Inverting for 8.49 percent gives rho around 0.967,
which is exactly the correlation observed. The entire gap was explained with no
exploitable signal in it.

**The estimation wall.** Nine methods from unrelated families, with parameter
counts from **one** to **78,561**, all landed between -0.1 and +0.1 percent,
while the oracles of those same methods measured 0.30, 0.40, 0.76 and 2.45
percent. The signal is real and repeatable; what fails is estimating it. The
sharpest case is the climatology window diagnostic, where the estimator was a
single global scalar: oracle values stayed between 0.25 and 0.35 while causal
ones swung from 0.07 to 0.72. Five strongly correlated residual blocks do not
contain enough independent information to calibrate even one parameter.

**One submission carried no information the other lacked.** Combining two
existing submissions gave an oracle gain of exactly zero. The reason is
structural: the error correlation between them, 0.9809, equals the ratio of
their RMSE values, 0.98089. That identity means the weaker model's error is the
stronger model's error plus an orthogonal component, so there is nothing to
extract.

**Where the error lives.** 62.4 percent of all squared error sits at latitudes
at or above -10 degrees, which is 101 of the 301 grid rows. One third of the map
holds two thirds of the loss.

Full synthesis, with the vocabulary defined for readers new to the project:
[docs/SINTESE_RODADAS_25_34.md](docs/SINTESE_RODADAS_25_34.md).
Index of all rounds: [experiments/README.md](experiments/README.md).

## Method discipline

Every diagnostic declared its decision threshold **in writing, in the script
header, before running**. Several lines of investigation were closed by those
pre declared criteria rather than by judgement after the fact, and the
[protocol](experiments/PROTOCOL.md) required a 0.3 percent minimum gain plus
stability across blocks, years and months before any variant could replace the
reference.

The reports record mistakes as well as results, including two design errors of
my own: a diagnostic criterion anchored on the wrong quantity, and two rounds
built on a feature whose availability in the test period I failed to check
before building.

## What remains open

The three leading teams finished between 1.58 and 1.62, roughly 9 percent ahead
of fifth place. This project never explained that gap and does not claim to.

The most likely explanation, identified here by elimination and supported by the
final standings, is seasonal dynamical forecasts. Models such as NMME and ECMWF
SEAS5, initialised in the origin month, carry information about the target month
that no statistical method over reanalysis can recover, because it is not there.
The team that publicly described using them finished fifth. That direction is
permitted by the rules and was never attempted here.

## Repository layout

| path | contents |
| --- | --- |
| `src/` | 4 modules reproduce a submission; the other 41 are research history |
| `docs/` | delivery, method, reproduction guide, synthesis |
| `experiments/` | frozen protocol per round, hash locked |
| `reports/` | metrics, decisions and verification records |
| `scripts/` | diagnostics, audits and the verification tools |
| `delivery/s12/evidence/` | frozen out of fold examples, verified by sha256 |
| `data/raw/` | official data, not redistributed, obtained separately |

The protocol files under `experiments/ROUND*.md` are hash locked: each round
module stores `protocol_sha256` and fails if the text changed. They record what
was decided before a round ran, so they are deliberately not editable
afterwards.
