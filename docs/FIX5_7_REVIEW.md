> Follow-up: this folder adds optional service and fast-safety guards. See
> [FIX567_GUARD_REVIEW.md](FIX567_GUARD_REVIEW.md). Historical outcomes below
> describe the original unguarded policies; fresh comparisons are in `guarded_results/`.

# Limitations 5–7: implemented robustness variants and remaining evidence gaps

These changes need no other assistant. They are opt-in and keep the original
headline/economics model available as an explicitly idealized reference.

## 5. Information timing and online arrivals

`robustness.Policy` configures observation delay and advance job knowledge.
`causal_mpc_schedule()` uses only jobs announced by their release time when
advance knowledge is disabled. Unknown job energy/deadlines cannot affect an
earlier decision. Per-hour traces retain visible job IDs and the latest observed
hour for audit.

Delayed demand/renewable estimates use the current forecast plus the most recent
available residual. Future periods retain their forecasts. No actual observation
after the cutoff is read. Zero delay reproduces the original nowcast controller.
Prices/carbon and exogenous forecasts are still known; no job-arrival forecasting
is added. Battery state is known from executed battery commands.

There is no secret current-hour safety correction in delayed runs: delayed
commands are executed and scored on actual demand/green. Capacity or grid
violations are explicitly reported. This tests latency rather than pretending
that delayed observations guarantee feasible physical operation. EDF references
have the same observations and compute assumptions as their paired MPC method.
Within-hour fluctuations and actual sensing/control hardware are not simulated.

## 6. Compute realism

Optional per-job ramp limits apply to total IT power, including startup from
zero and shutdown to zero. The strict LP enforces them. If the strict problem
is infeasible, the existing fallback can relax ramp bounds with an explicit
penalty. `evaluate()` independently counts ramp violations and excess, marks the
run degraded, and adds the penalty. A ramp relaxation is never described as a
hard guarantee.

Optional checkpoint/compute overhead is an **amortized energy-efficiency proxy**:
useful work = job IT energy * (1-overhead_fraction). It consumes facility energy
and capacity but does not complete useful work. The controller, EDF reference,
remaining-work updates and evaluator use the same efficiency. Useful job
requirements remain unchanged between policies. The tested sensitivity uses 5%
overhead and a 2 MW/job/hour ramp limit, both explicit engineering assumptions.
The overhead applies to all flexible jobs, not inference.

This is not a measured per-pause/checkpoint model. Per-resume fixed costs,
minimum run times, whole GPU/server allocation, idle power and workload-specific
checkpoint behavior remain unimplemented. Compute remains continuous. These
extensions require further model choices and calibration, not Claude access.

## 7. Broader synthetic validation

`robustness_experiments.py` runs predeclared held-out seeds 100–119 against three
synthetic stress profiles: typical, reduced green supply, and increased inference.
Each profile tests original information, online arrivals, delayed online arrivals,
ramp-only, overhead-only and combined policies. Every policy has a matching EDF
reference. Controls are fixed before interpreting held-out performance.

The generator now offers `screen_feasibility=False`, retaining the first random
draw, and records screening/attempt metadata. The robustness study uses this
option, preventing selection of only easy/feasible scenarios. Original generator
defaults remain unchanged for comparability. All feasible, degraded and exogenous
overload outcomes are retained. Paired savings are suppressed when any pair is
infeasible. Reports include worst-case SLA/capacity/grid/ramp violations, overhead,
penalties, per-seed data, paired 95% intervals, and auditable example decision traces.

These are not measured seasons or real operational validation. No operational
trace was supplied. More seeds improve synthetic coverage but cannot establish
external validity; real traces, real arrival processes and calibrated profiles
remain necessary. No real-data claim is made.

## Commands

```bash
python robustness_experiments.py --quick --output-dir robustness-smoke
python robustness_experiments.py --output-dir robustness_results
python -m pytest -q
```

The full run targets 20 seeds × 3 profiles × 6 policies × 2 methods = 720 runs.
The quick run targets 2 seeds × 2 profiles × 3 policies × 2 methods = 24 runs.
Outputs are four CSVs, two JSON audit/manifest files, and a Markdown report.
The ordinary experiment outputs are separate and retain their original assumptions.

## Verified outcomes and remaining controller limitations

The full study completed 720 method runs from 20 unique unscreened seeds,
three profiles, six policies and two methods. These are not 720 independent
seeds. Every method summary contains 20 runs and counts reconcile with raw data.

For the typical profile, informed MPC was feasible in 19/20 cases; online MPC
in 8/20; delayed online MPC in 0/20. Online EDF was feasible in 19/20. Removing
future-job knowledge exposes deadline failures: energy-aware MPC defers work
into capacity later needed by new arrivals. Delayed demand estimates expose
capacity violations. These are controller performance limitations, not errors
to omit. Ramp/overhead assumptions expose additional service or ramp failures.
Overall, 278 of 720 method runs were feasible and 442 were degraded. No group
met the all-pairs-feasible rule; all 54 ordinary paired savings estimates are
therefore suppressed rather than cherry-picked.

Original headline claims remain restricted to idealized information and compute
assumptions. This implements missing models/tests; it does not fix the
controller's online robustness or establish operational feasibility.
Arrival-aware planning, safety intervention/reserves, measured sensing delays,
per-resume/GPU modeling and real trace calibration remain open. None require
Claude specifically; they require further design and/or data. Controls were
not retuned on this held-out set after seeing its failures.

Verification: the 118-test full suite passed, then two additional targeted
ramp-penalty consistency tests passed (120 distinct tests total). Checks cover
future-observation and unreleased-job leakage, zero-overhead equivalence,
startup/shutdown ramps, emergency penalties, overhead accounting, unscreened
reproducibility, held-out seed validation, generated outputs and subhourly delay.
