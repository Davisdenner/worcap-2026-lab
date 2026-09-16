# Third party and data notices

Original project code is separate from its third-party dependencies. NumPy,
SciPy, scikit-learn, pandas, xarray, joblib, netCDF4 and their dependencies retain
their own license terms. The release builder includes the installed distribution
license files and metadata; consult that inventory before redistribution.
Offline third-party wheels are bundled for the exact Windows x64 environment.
They are locally repacked from installed distributions, not original publisher
downloads. Their original license files and distribution metadata are retained
inside each wheel; origins and file hashes are in `wheels/provenance.json`.
No Python runtime or proprietary GPU library is bundled.

Official competition data are not relicensed by the code license and are not
included in the archive. Their use remains subject to the competition rules
and the original data terms, including the stated noncommercial limitation.

Contains modified Copernicus Climate Change Service information 2026.
Neither the European Commission nor ECMWF is responsible for any use that
may be made of the Copernicus information or data it contains.

No NOAA observations or NOAA-derived S07/S08 models are part of S11.
The full research repository retains historical experiments for transparency;
the delivery package includes only dependencies of the official-only solution.
