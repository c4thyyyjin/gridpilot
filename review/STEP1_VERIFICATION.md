# Post-checklist verification — step 1 complete

Verified in `step6 fix567 improved`, 2026-10-24 (California client date).

## Completed work

- Supplied fixes were inspected and the original 181-test suite ran successfully.
- Corrected a remaining renewable-storage ledger error: stored renewable energy
  now loses the full withdrawn energy, including discharge conversion losses.
  The model explicitly specifies well-mixed storage, conservative nonrenewable
  initial energy, charge-before-withdrawal mixing and discharge-to-load priority.
  Direct service is integrated with DT_H; charging and parked energy are excluded
  from load-service share. Only roundoff at 100% is normalized.
- Added relevant scenario shape/finiteness checks, finite lambda validation,
  repeated-withdrawal energy-accounting checks, zero-load/subhourly scorer units,
  malformed/negative/nonfinite schedule regressions, and saved-oracle-provenance
  tests. The scenario generator remains intentionally hourly-only.
- Oracle manifests now record the complete configuration snapshot. Oracle
  diagnostics restore recorded settings and policies, then restore caller state
  even on failure. Older archived manifests without snapshots still require
  their original configuration.
- Confirmed supplied ineligible-bar labels and total-benefit battery-chart labels;
  repaired a clipped stress-chart title and visually checked the corrected plot.
- Qualified untested finer-resolution/PUE/idle-power effects. Tariff values are
  explicitly illustrative pending exact source-row confirmation. Removed the
  results/ ignore rule so numerical evidence can be tracked in the final repo.

## Final verification

**206 tests passed in 191.78 seconds.** Existing PuLP deprecation warnings remain.
`pip check` reports no broken requirements in the existing locked environment.
This was not a new environment installation or a test on all platforms.

Regenerated in place:

| Output | Completed scope |
|---|---|
| results/, figures/ | Full original five-seed experiment: 15 CSV tables, RESULTS.md, seven PNGs |
| improved_results/ | Full seeds 200–219 regression: 1,080 method runs |
| fresh_results/ | Full seeds 220–239 validation: 1,080 method runs |
| Both current robustness folders | Oracle diagnostics rerun from newly recorded configuration/policies |

Checked numeric CSVs for infinities, green percentages for [0,100], record-key
uniqueness, seed/manifest agreement and guarded physical-limit diagnostics.

Guarded regression remains 346/360 feasible method runs; guarded fresh remains
354/360. Both have zero recorded guarded capacity/grid/battery/ramp violations.
Oracle diagnostics still find zero oracle-feasible cases among seven regression
failures and three fresh failures. The separate original headline MPC objective
is unchanged at 574031.5459986166 CNY including the carbon term. Renewable-share
values use the new documented definition and are refreshed in current outputs.

Archived robustness_results/ and guarded_results/ preserve the older studies and
metric definition. They were not silently rewritten with a different controller.
Use results/, improved_results/ and fresh_results/ for current evidence.

README, AI disclosure, assumptions and this verification report reflect the
changes. Tests and numerical work here were performed by Codex; they do not
assert additional student activities or a completed school submission.

## Step 3 — after publishing the final GitHub repository

Clone the actual remote, not another copy of your working folder. Replace the
URL below. These macOS commands assume Python 3.13, as tested by the project:

```bash
git clone https://github.com/YOUR-USERNAME/YOUR-REPO.git fresh-check
cd fresh-check
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip check
python -m pytest -q
python baseline.py
python experiments.py --quick --output-dir smoke-check
```

If python3 is not Python 3.13, select an installed Python 3.13 interpreter for
creating the environment. Expect 206 passing tests and no broken dependencies.
Check that smoke-check/results has 15 CSVs plus RESULTS.md, and smoke-check/figures
has seven PNGs. Also run the guarded-controller example in README.md and verify
it reports feasible service for the supplied demo case.

Ensure this clone contains the source, tests, requirements, README, AI/solo
contribution records and the intended result evidence. Save the terminal summary
as submission evidence. A failure means repair the published version, push the
fix, and repeat in a fresh checkout. Public GitHub availability, fresh remote
installation and SHSID Learn submitted status remain unverified until performed.
