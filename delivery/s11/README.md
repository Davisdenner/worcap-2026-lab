# S11 precipitation forecasting delivery

This package reproduces S11, public RMSE **1.71718** as reported by the entrant.
It is a technical delivery candidate, not a claim of winning rank or private score.
The original submitted CSV is preserved; reproduction output is not a new entry.

## Scope and data

The model uses only the official ERA5 precipitation and nine atmospheric fields.
It predicts January 2023 through December 2024 on the original 301 by 261 grid.
Observed rainfall is never taken from 2023 or 2024. The inference interface expects
the competition's 24-month test schema, including three months of antecedent
atmospheric history supplied in the model. It is not a general weather service.

Download the official files yourself after accepting the competition rules.
Raw competition data are deliberately excluded from the delivery archive.
Change `raw` in SETTINGS.json to their directory. No API token is required by
the local pipeline. Do not put credentials in the archive.

## Environment and installation

Reference host: Windows build 26200, Python 3.11.1, Intel Core i5-1135G7
at 2.40 GHz. Computation is CPU-only, with one BLAS/OpenMP thread.
The NVIDIA MX350 was not used. Measured RAM, core count, process peak memory
and elapsed time are recorded in `verification/*_execution.json`.
Reserve 8 GB of free disk for raw files, caches, models and verification outputs;
16 GB RAM is the reference-machine class, not a measured minimum requirement.

From the extracted archive root, with Python 3.11 installed:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

For the verified offline Windows x64 installation, use the included wheels:

```powershell
.\.venv\Scripts\python.exe -m pip install --no-index --find-links wheels -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

The online package-index attempt could not resolve the pinned versions here.
Offline wheels are locally repacked installed distributions, not publisher
downloads. Their versions, hashes and license files are documented in
`wheels/provenance.json`; none of their packaged files differed from the
installed RECORD checksums. See `verification/DELIVERY_STATUS.md` for the
separate-environment execution tests actually completed.

## Execution

See `entry_points.md`. All input/output roots are specified by SETTINGS.json.
Training and prediction are separate commands. Inference loads saved models,
not previously computed prediction arrays, and does not read training rainfall.
The supplied model files use joblib: load only this trusted, hash-checked package.

Final training regenerates all base learners from official raw-derived arrays.
It does **not** repeat the entire historical model search. The configuration is
frozen to S11; final convex weights are recomputed from archived official-only
out-of-fold covariance sufficient statistics for 2005-2022, with lambda 1.
Those statistics and the S10 prior are fitted historical artifacts, not raw data.
Their provenance is included in `evidence`. No hidden test labels are needed.
The untouched experimental sources and protocols document how those statistics
were originally produced. This distinction is important when evaluating what
has and has not been reproduced from zero.

## Side effects and assumptions

The pipeline creates only the configured cache, model and output directories.
It never edits raw data, never uploads to Kaggle and never overwrites a CSV.
Training refuses existing model files. For an independent rerun, set fresh
directories in a copy of SETTINGS.json; do not delete the original artifacts.
Prepare can verify and reuse its own equal raw-derived arrays after interruption.
Changing package versions or BLAS implementations can cause numerical differences.
Compare arrays and score tolerances as well as exact hashes.

## Validation policy remains active

S11 was an explicit user-authorized exception after failing the original gates.
Its later public gain does not retroactively approve it under those gates.
Future experiments still require the frozen development/confirmation gates;
generation and upload require an explicit user request. This delivery run is
not candidate selection and cannot consume a submission allowance.

Development gates: pooled RMSE improvement at least 0.3%, better second-year
aggregate, at least 5/6 blocks, 9/12 years and 55% of months improved, worst
annual relative degradation at most 0.5%. Confirmation: at least 0.1% aggregate
gain and both years better. Prediction-shift RMS at most twice historical RMS
in each test year. Reused validation periods are not independent holdouts.

## Required entrant closeout

Before sponsor delivery, complete the team identity/contact information and
confirm the chosen OSI license. Private rank/score are unknown until announced.
Any sponsor-specific presentation or documentation approval remains to be
confirmed directly with the organizer. This package does not certify eligibility.

References: https://www.kaggle.com/WinningModelDocumentationGuidelines
and the competition rules supplied by the entrant.
