# Limitations 9 and 10

## Experiment lifecycle and configuration

`experiments.py` now has a guarded CLI `main(argv=None)` and an importable
`run_experiments(quick=False, output_dir=".", config_overrides=None)` API.
Argument parsing, output creation, plotting and experiment execution occur only
on an explicit call. State for each run is local, so repeated calls do not
accumulate results. No process-wide chdir or run-state globals are used.

Output locations are explicit Paths. The CLI accepts `--output-dir` and optional
`--config` JSON. Known config constants may be overridden; unknown keys raise.
JSON lists for tuple constants and numeric tariff-hour keys are normalized.
The controller reads the current shared penalty constants when solving, so
config overrides and evaluator penalties cannot drift due to import-time copies.

Every run snapshots config constants and restores them in finally, including
mutable dictionaries/lists and temporary keys. Plot styles and figures created
by the run are cleaned up, while existing caller figures are retained. The
battery sweep also restores its settings in finally. Unexpected errors propagate.
The runner is intended for sequential use; shared config is not thread-local.

## Reproducibility and documentation

`requirements-lock.txt` pins the runtime/test dependency graph and was installed
into an empty virtual environment. `requirements.txt` retains version ranges.
An unused Streamlit dependency was removed. The README now documents implemented
methods, actual commands, paths, configuration, statistics and limitations rather
than a nonexistent greedy method or unfilled sections.

The tested lock targets CPython 3.13.5/macOS ARM64. It does not pin the OS, fonts,
Python interpreter or installer and does not promise identical pixels across
platforms. Solver and platform versions still need to be reported with results.

## Pareto labels

`plotting.plot_pareto()` draws unchanged points and groups labels within 12 display
pixels. Groups are placed in a separate column, sorted by cost and joined to their
anchors with leader lines. Long groups wrap. Infeasible/undefined coordinates are
excluded. Regression tests verify separated label boxes and unchanged point data;
the full regenerated Pareto figure is inspected visually.

## Verification

The dependency lock installed in a fresh environment and pip check reported no
broken requirements. All 88 tests passed there, including six new lifecycle and
label-layout cases. Full five-seed regeneration in an empty explicit output
directory reproduced all eleven CSV tables to rtol=1e-10 / atol=1e-7. Five PNGs
were verified; the regenerated Pareto plot was inspected visually. Outputs were
copied into the project results/ and figures/ directories. Controller/evaluator
consistency with overridden penalty rates was also checked. PuLP deprecation
notices remain, and the lock intentionally keeps PuLP below 4.
