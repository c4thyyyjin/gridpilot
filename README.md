# AI Data Center Power–Computing Co-Scheduling

HackSHSID 2026 · Track 2 (Huawei / Hithium)

GridPilot schedules flexible training/batch
jobs and battery use under changing inference demand, electricity prices,
carbon intensity and renewable supply. The goal is lower cost and emissions
within a clearly stated service and physical operating envelope.

The latest change uses job laxity (remaining deliverable energy minus remaining
required work), service quotas and ramp-down reservations to avoid starving long
jobs. A separate fast execution stage uses current telemetry and replans battery
use. Unknown future jobs and future actual demand/renewables are unavailable to
the online controller. These are synthetic simulations, not operational validation.

## Methods and comparisons

- **Simple observed-demand EDF:** earliest-deadline-first jobs without a battery;
  the simple reference for the original headline experiment.
- **Forecast EDF:** secondary baseline using forecast inference capacity.
- **Open-loop LP:** one forecast-based compute/battery plan.
- **MPC:** strict LP replanning each hour; a penalized fallback is logged only
  after strict infeasibility. Original experiments assume advance job knowledge.
- **Guarded online/delayed MPC:** released jobs only; a laxity-based heuristic fixes
  current job service, and an LP plans the battery. Delayed optimizer estimates
  are distinct from current telemetry available to the fast execution stage.
- **Matched no-battery laxity reference:** uses the identical guarded job-service
  heuristic without the battery. The function retains its historical name,
  `causal_edf_schedule`, but guarded mode is not plain EDF. This comparison
  isolates battery value; it does not measure improvement over simple EDF.
- **Oracle:** full-horizon LP with perfect future information, used as a model
  benchmark and infeasibility diagnostic, never to inform online decisions.
- **Independent LP verification:** PuLP/CBC and SciPy/HiGHS solve the same stated LP.

LP solver optimality applies to its model and supplied information. It does not
prove global optimality of rolling decisions or the guarded service heuristic.
Service failures stay visible; savings are suppressed if any paired run fails.

## Installation

The tested lock was installed on macOS ARM64, CPython 3.13.5:

```bash
python3 -m venv .venv
source .venv/bin/activate
# Windows activation: .venv\Scripts\activate
python -m pip install -r requirements-lock.txt
```

requirements.txt lists supported development ranges. The lock is not a guarantee
of identical binaries/fonts across platforms. The prototype runs from Python/CLI;
there is no required dashboard or Streamlit app.

## Run the current guarded controller

From the project folder:

```bash
python - <<'PY'
from data import make_scenario
from robustness import POLICIES, causal_mpc_schedule
from evaluate import evaluate
import config as C

sc = make_scenario(220, forecast_error=.3, screen_feasibility=False)
sch = causal_mpc_schedule(sc, C.LAMBDA_DEFAULT, C.GRID_IMPORT_LIMIT_MW,
                          policy=POLICIES['guarded_delayed'])
m = evaluate(sc, sch, C.LAMBDA_DEFAULT)
print({k: m[k] for k in ['feasible', 'objective', 'cost_cny', 'co2_t',
                        'sla_violations', 'capacity_violation_hours']})
PY
python -m pytest -q
```

The current full suite passed **206 tests**. Validation, storage-accounting
and regeneration evidence are recorded in review/STEP1_VERIFICATION.md. Tests cover independent
solvers, evaluator equality, causality, service/ramp/battery limits, explicit
fallbacks, paired statistics, economics and output regeneration.

## Reproduce studies without overwriting supplied evidence

```bash
# Original headline/economics model: 15 CSV tables and RESULTS.md in results/,
# plus seven PNGs in figures/, under the selected output parent.
python experiments.py --quick --output-dir output-quick
python experiments.py --output-dir output-full

# Regression study: seeds 200–219, which informed the latest development.
python robustness_experiments.py --output-dir output-regression
python check_guarded_deadlines.py --output-dir output-regression

# Fresh validation study: seeds 220–239.
python - <<'PY'
from robustness_experiments import run_validation
run_validation('output-fresh', seeds=range(220, 240))
PY
python check_guarded_deadlines.py --output-dir output-fresh
```

Each full robustness study is 20 seeds × three profiles × nine policies × two
methods = 1,080 method runs. These are 20 unique seeds, not 1,080 independent
scenarios. Each has four CSVs, manifest/decision-trace JSON and RESULTS.md; the
oracle diagnostic adds a fifth CSV. The robustness `--quick` mode exercises
legacy policies as a smoke check, not the full guarded-policy comparison.

The original experiment runner supports `--config settings.json` and
`run_experiments(quick=True, output_dir=..., config_overrides=...)`. Config keys
are names from config.py, for example `{"LAMBDA_DEFAULT":100}`. Imports do not
start experiments; configuration and plotting styles are restored after runs.
Unexpected errors propagate rather than being presented as successful old output.

## Results and provenance

| Folder | Meaning |
|---|---|
| results/, figures/ | Original headline/economics experiment; advance job knowledge and original compute assumptions |
| improved_results/ | Current laxity-guard regression study, seeds 200–219 |
| fresh_results/ | Current fresh validation study, seeds 220–239 |

Earlier archived studies are excluded from this submission folder. Historical
review documents may refer to those development snapshots. Current evidence is
in results/, improved_results/ and fresh_results/.

Fresh guarded MPC feasibility, out of 20 seeds per cell:

| Policy | Typical | Low green | High inference |
|---|---:|---:|---:|
| guarded_online | 20 | 20 | 20 |
| guarded_delayed | 20 | 20 | 20 |
| guarded_combined | 19 | 19 | 19 |

The fresh combined failures all involve seed 239 and remain infeasible for the
same-constraint perfect-information oracle. Across 360 fresh guarded method
runs, saved records show zero capacity, grid, battery and ramp violations.
Fresh online/delayed objective gains are about **4.92–5.09% against the matched
no-battery laxity reference**. Combined group savings are suppressed.

The separate original headline MPC objective gain is about **20.54% against
simple observed EDF**. Different information/service assumptions and references
make that unsuitable as the guarded online controller's savings claim.

Raw runs and seed pairs retain failures. Pointwise paired 95% Student-t intervals
are supplied, with monetary comparisons suppressed when any pair is infeasible.
Synthetic sample sizes and shared base draws limit generalization.

## Assumptions and limits

The model uses synthetic 72-hour hourly traces and continuous compute. Original
runs have free checkpointing; optional overhead is an assumed amortized fraction,
not a measured per-resume cost. Optional ramps do not model whole GPU allocation.
Green share measures renewable load service with a mixed battery and nonrenewable
initial stored energy; it excludes losses and green energy still in storage.
Fast current-hour sensing/actuation is an assumption, even when the optimizer
has delayed observations. Laxity ignores future competition and provides no
universal deadline guarantee. Unsupported cheap tariffs are rejected consistently.

Grid-cap and battery economic screens include illustrative capital/O&M/demand
charges and repeated-block annualization; they are not actual bills or investment
recommendations. See ASSUMPTIONS.md, docs/FIX8_REVIEW.md and
docs/FIX567_IMPROVED_REVIEW.md for assumptions, tradeoffs and failure cases.

Solo student project; no human teammates. Individual contribution/progress:
docs/TEAM.md. AI tools assisted with implementation and checking.
AI contributions/checks: docs/AI_USE.md. Submission audit:
review/REQUIREMENTS_AUDIT.md. Verify the actual public repository contents and
submission separately; successful local execution does not establish either.
