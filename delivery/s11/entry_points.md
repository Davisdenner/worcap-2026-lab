# Entry points

Run these commands from the extracted package root, after editing SETTINGS.json.
The ZIP includes `src/` and frozen experimental sources. From the working
repository instead, run at its root and use `--settings delivery/s11/SETTINGS.json`.

## Use the supplied trained model

```powershell
.\.venv\Scripts\python.exe -m src.s11_delivery predict --settings SETTINGS.json
```

Requires the official `teste_features.nc` and `sample_submission.csv` in `raw`,
the supplied models and an empty output destination. Produces
`s11_reproduction.csv` and a labeled NetCDF under the configured output root.
This is a reproduction of an already submitted candidate, not a new submission.

## Refit the final configuration

Set fresh cache, models and output paths in SETTINGS.json, retaining evidence.

```powershell
.\.venv\Scripts\python.exe -m src.s11_delivery prepare --settings SETTINGS.json
.\.venv\Scripts\python.exe -m src.s11_delivery train --settings SETTINGS.json
.\.venv\Scripts\python.exe -m src.s11_delivery predict --settings SETTINGS.json
```

Prepare requires the official training files and test file. Train fits every
final base learner from the resulting raw-derived arrays; it recomputes fixed
combiner weights from the included historical covariance statistics. It does
not rerun model selection or regenerate all historical folds from raw data.
The calibration years, covariance hashes and original generation metadata
are in evidence. Original source stages are retained for methodological audit,
not advertised as a clean one-command full historical replay.

## Integrity checks

```powershell
.\.venv\Scripts\python.exe check_delivery.py
.\.venv\Scripts\python.exe check_delivery.py --predictions work/output/s11_reproduction.csv
```

Every inference run verifies serialized model hashes. Compare the resulting
CSV to the original expected SHA-256 in evidence/s11_generation.json and review
the numeric comparisons recorded under verification. Never change a model to
force agreement with the public leaderboard.
