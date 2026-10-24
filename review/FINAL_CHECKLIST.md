> Post-checklist update: step 1 is now complete; see
> [STEP1_VERIFICATION.md](STEP1_VERIFICATION.md). The current full suite passes
> 206 tests, current results have been fully regenerated, storage loss accounting
> and oracle provenance have additional fixes/tests, and results/ is trackable.
> Historical findings below describe the pre-correction audit. Public GitHub,
> a fresh remote installation and actual school submission remain unverified.

# Final project audit and checklist

Reviewed: 2026-10-24, America/Los_Angeles client date.
Project: step6 fix567 improved. This audit adds this checklist only; it does not
change source code, tests or numeric results. Items below separate reproduced
bugs, submission tasks, and optional improvements. No finite audit proves the
absence of all defects.

## Verification completed

- [x] Latest complete suite rerun: **166 passed in 197.97 seconds**. The 24,072
  warnings are PuLP deprecations; passing tests do not cover the new edge cases below.
- [x] `pip check`: no broken requirements in the existing locked environment.
  This was not a fresh installation or a test on every platform.
- [x] Existing CLI test regenerated 15 CSV tables, RESULTS.md and seven PNGs in
  a temporary empty output directory.
- [x] Seven supplied PNGs decoded and inspected together for presentation clarity.
- [x] Main, improved and fresh CSV numeric fields checked for infinities.
- [x] Improved/fresh studies each contain 1,080 unique method records from 20
  seeds, with seed sets matching manifests. They are not 1,080 independent draws.
- [x] Guarded regression: 346/360 feasible method runs. Guarded fresh: 354/360.
  Both supplied studies report zero guarded capacity/grid/battery/ramp violations.
- [x] Prior review independently replayed 18 fresh schedules and all ten
  regression/fresh failed-case oracle diagnostics. Both entire studies were
  not rerun in this audit.
- [x] Current README, solo contribution record, AI disclosure, service-quota
  wording, reference labels and seed provenance are present. They supersede
  explicitly historical review findings; those tasks are not blank templates now.

## Priority 1 — correctness fixes before final submission/interface

- [x] **Reject non-finite schedules before scoring.** `evaluate.py:39–41` converts
  arrays but does not check shape or finiteness. Reproduction: put NaN in
  `charge[0]` or in a job's in-window power on an otherwise valid baseline.
  Result: `feasible=True`, `objective=NaN`. Add shape/finiteness validation for
  schedule arrays and relevant scenario inputs; add NaN/infinity/malformed-array
  regression tests. Invalid data should raise a clear validation error or be
  explicitly infeasible, never feasible with an undefined objective.
- [x] **Check battery lower bounds.** `evaluate.py:78–81` checks upper power bounds
  and SoC but not negative charge/discharge. On seed 42 baseline, set charge=-1 MW
  and discharge=-0.9025 MW in every hour. SoC is unchanged and the scorer accepts
  it as feasible, lowering objective from 724031.39 to 716083.60 CNY. Enforce
  nonnegative powers with a numerical tolerance and test this case. Existing
  scheduler LPs have nonnegative bounds; this reproduction is a scorer gap,
  not evidence that stored solver schedules contain negative powers.
- [x] **Define and correct green share with storage.** `evaluate.py` divides all
  renewable input, including energy lost in charging/storage, by facility load.
  A valid two-hour all-renewable case returns **105.4017%**: facility load 1 MW
  each hour; green [3,0] MW; charge [1/0.9025,0], discharge [0,1] MW. Choose a
  documented metric: renewable fraction of supplied source energy including
  storage losses, or a load-served renewable fraction with explicit battery
  provenance/start-state assumptions. These answer different questions; do not
  just clip percentages to 100. Test units, zero-load behavior and storage cases.
  Refresh affected reports/results after changing the definition. Cost/CO2 need
  not change just because this reporting definition changes.

These findings were independently reproduced without changing project source.
They are missing tests despite the otherwise passing suite.

## Priority 2 — clarity, parameter support and reproducibility

- [x] **Label ineligible stress bars.** `experiments.py:256–259` passes NaN savings
  to barh, leaving blank rows in assumption_stress.png. Add an explicit
  “ineligible: service/physical failure” annotation rather than letting a blank
  row resemble zero savings. Keep suppressed gains suppressed.
- [x] **Clarify the battery plot's comparison.** `experiments.py:225` calls it
  “Value of storage on top of job shifting”, but the plotted percentage is versus
  simple EDF and already shows about 15% gain at zero battery. Rename it as
  combined job-shifting/storage benefit versus EDF, or plot incremental storage
  gain relative to zero-battery MPC. The economics code already uses the latter
  reference for attributing battery value.
- [x] **Lock hourly resolution or repair generator time units.** `data.py:103–130`
  omits DT_H in generated energy and feasibility screening. With DT_H=.5, the
  default draw still passes check_feasible while six jobs cannot individually
  fit their energy in their windows. Existing evidence uses DT_H=1. Keep that
  fixed and reject unsupported resolutions, or consistently update generation,
  horizons/windows, screening and tests before offering a resolution control.
- [x] **Bind oracle diagnostics to saved run settings.**
  `check_guarded_deadlines.py:19–28` rebuilds cases with hardcoded .3 error and
  current config/POLICIES/PROFILES, not the recorded manifest. Current supplied
  defaults matched in the prior replay. For configurable runs, reconstruct from
  saved settings or reject mismatches; record relevant battery/PUE/timestep
  settings so later config changes cannot silently change the diagnosed problem.
- [x] **Qualify untested assumption effects.** ASSUMPTIONS.md still suggests finer
  resolution increases savings, higher PUE barely changes percentage savings,
  and idle power only adds a harmless constant. These are not established by
  this audit and may fail with fixed battery/grid limits or controllable idle
  servers. Present them as hypotheses/limitations or supply sensitivity evidence.
- [ ] **Verify tariff numbers or label them illustrative.** The cited July 2025
  tariff PDF was inaccessible through the browsing tool in this audit. Confirm
  the exact voltage/customer/rate row and components manually from a trustworthy
  copy; do not describe unverified numbers as independently checked. This is
  an access/verification gap, not proof the source or values are wrong.
- [ ] **Strengthen selected source citations.** The official MEE table supports
  the rounded national 2022 carbon mean (.5366 -> .537); Uptime's own 2025 survey
  supports weighted-average PUE 1.54. Prefer these primary sources over a summary.
  PUE 1.2, hourly carbon shape, battery wear/capital costs and workload profiles
  remain explicit assumptions, not verified site measurements.

Primary sources checked:
- MEE/NBS national carbon factor, table 1:
  https://www.mee.gov.cn/xxgk2018/xxgk/xxgk01/202412/t20241226_1099413.html
- Uptime Institute 2025 survey (PUE context):
  https://datacenter.uptimeinstitute.com/rs/711-RIA-145/images/2025.Annual.Survey.Report.pdf?version=0

## Priority 3 — finish the actual submission

- [ ] **Confirm exact event cutoff/timezone and submission status immediately.**
  The supplied course brief lists October 17–24 and says to follow event notices
  for the exact cutoff. This audit did not access school announcements or your
  private SHSID Learn account; do not assume a local calendar date guarantees time.
- [ ] **Create one clean final release folder.** Publish the latest project, not
  the parent workspace with all ZIPs, older versions and registration documents.
  Keep .venv, caches, .DS_Store, private identifiers and credentials out.
- [ ] **Verify/create the public GitHub repository.** No .git directory or public
  repository URL was found in the latest local folder. A repository elsewhere
  could exist; it was not verified. Put the correct public URL in the submission.
- [x] **Decide which evidence to track.** Current .gitignore excludes results/,
  so a normal git add will omit the main numerical report/CSVs. Deliberately
  include representative evidence or update ignore rules; do not accidentally
  omit evidence expected by README. Keep reproduction commands regardless.
- [ ] **Test the exact public checkout.** Clone into an empty directory, install
  documented dependencies, run tests and the README demo, regenerate outputs,
  and check which source/results files actually arrived. Local output regeneration
  is verified; a public fresh-clone installation is not.
- [ ] **Prepare a short submission description in your own words.** Include the
  user need, why the design is useful/distinctive, how it works, results and
  limitations. README contains technical context, but no private portal text or
  completed submission was inspected. Do not claim a new optimality theorem.
- [ ] **Package readable test evidence.** Supply a compact expected/actual table
  and a saved final test summary: objective equality, independent solvers,
  forecast-error capacity, unknown-job causality, impossible cases, battery/grid
  bounds, and the new invalid-input/green-share cases after they are fixed.
- [ ] **Confirm private solo identity/registration and submit.** Public solo
  contribution and AI records are present; complete the actual portal fields
  and verify submitted status/receipt rather than merely saving a draft.
- [ ] **Personally rehearse the explanation.** Be able to explain MW versus MWh,
  PUE, lambda units, SoC/efficiencies, strict versus fallback, fast safety versus
  delayed optimization, EDF versus matched laxity reference, and why tested LP
  optimality does not prove an online heuristic is globally optimal. AI-generated
  explanations and automated tests cannot establish personal understanding.

## Optional interface and presentation preparation

- [ ] **Interactive dashboard — optional, not a missing requirement.** No app.py,
  web frontend or Streamlit dependency currently exists in the latest folder.
  If built, reuse the current schedulers/evaluator, restrict supported inputs,
  show the correct reference, mark synthetic data, and withhold savings on
  infeasible runs. Cache results and show solver/error status; avoid changing
  global config across concurrent sessions without isolation.
- [ ] **Current-guard demo chart.** Existing seven figures illustrate the original
  headline/economics model. A clearly labeled current-guard timeline/summary would
  improve the demo; do not present original-model savings as the guard's results.
- [ ] **If shortlisted:** prepare the specified five-minute presentation/live demo
  and three-minute Q&A. No slide deck or demo script was found locally. Prepare
  an offline fallback (saved chart/output or recording) and a tested failure case.
- [ ] **Maintenance, not an urgent blocker:** consider a license for intended reuse,
  a simple automated CI run, and a planned PuLP migration. The current <4 pin and
  tested lock avoid an immediate major-version migration requirement.

## Honest limits that need disclosure rather than last-minute scope expansion

- Synthetic data and assumed hourly profiles; no measured operational validation.
- Continuous compute, amortized overhead and illustrative ramp limits, not whole
  GPU allocation or measured checkpoint behavior.
- Current fast-stage telemetry/actuation is assumed; this is not a within-hour
  physical latency guarantee.
- Online laxity ignores future job competition/unknown arrivals; no universal
  deadline or global optimality claim.
- Combined-policy infeasible cases remain in data; do not hide them.
- Original approximately 20.54% objective saving and fresh guarded approximately
  4.92–5.09% saving use different assumptions/references and must stay separate.
- Financial sensitivity screens use assumed costs and annual repetition; they
  are not vendor quotes, applicable bills or investment advice.

The core technical brief is substantially addressed. The most important new
code fixes are evaluator input validation and green-share accounting. The
submission blockers that cannot be verified from this workspace are the final
public checkout and actual school submission. A dashboard is an enhancement.
