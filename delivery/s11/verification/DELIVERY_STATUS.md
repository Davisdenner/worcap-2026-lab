# S11 delivery verification status

## Passed

- Official training files were reread into a new isolated cache. No old model
  prediction array was used to fit the final base learners.
- Every final base learner was refitted and all inference parameters saved.
- The resulting CSV is byte-identical to the submitted S11, SHA-256
  `8b871e4fa982045ee1c59abb19ff9e4954444aaf96de22052daa3de22e64b26f`.
- A new Python 3.11.1 virtual environment, without system site packages, was
  installed using the included offline Windows x64 wheels. `pip check` passed.
- Source copied into a standalone delivery directory was used to refit the
  models again under that clean environment, then run separate inference.
  That second CSV also exactly matched S11. The freshly regenerated raw cache
  was reused for this second training; old research caches were not used.
- Each offline package retained license files. Packaged files matched the
  installed distribution RECORD hashes; these are local repacks, not original
  publisher wheels. The online package-index installation attempt did not resolve
  the versions in this environment.
- 67 repository tests passed with the documented single-thread configuration,
  including unchanged rejection criteria for the historically rejected S11.
- Original submissions and frozen experimental code remain unchanged.
- The four-page English PDF was rendered and every page visually inspected.

## Scope limitations

Final ensemble calibration was reproduced from archived official-only OOF
covariance sufficient statistics and the frozen S10 prior. Historical search
and all past calibration-fold predictions were not regenerated from raw data.
Both clean-environment runs used the same Windows host. There is no claim of
validation on another OS, processor family or independently downloaded packages.
Inference supports the official 24-month calendar and grid, not arbitrary domains.

## Pending entrant closeout

- Explicit approval of the code's OSI license (MIT was proposed).
- Team name, member names, contacts, backgrounds and division of work.
- Private result and rank when announced; sponsor-specific closeout requirements.

The archive is therefore a technical draft, not a legal certification or an
automatically submitted sponsor deliverable. No new candidate or Kaggle upload
was produced. Internal validation gates remain in force.
