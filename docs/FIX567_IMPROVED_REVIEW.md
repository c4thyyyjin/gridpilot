# Laxity-aware online deadline scheduling

This folder is a copy of `step6 fix567`, named `step6 fix567 improved`. It
continues the guard follow-up rather than replacing it: the previous snapshot,
its `guarded_results/`, tests and review document are unchanged. The purpose is
the specific open item recorded in `guarded_results/deadline_oracle_check.csv`:
**19 of 26 failed guarded MPC cases were feasible with perfect future
knowledge**, so the online controller was leaving recoverable deadlines on the
table.

Scheduling changes are in `service_power()` and its helpers in `robustness.py`. No model,
data, tariff, evaluator, experiment or default policy parameter changed.

## What was wrong

The guarded stage served released jobs in strict earliest-deadline-first (EDF)
order and let each job take as much capacity as its per-hour cap allowed before
looking at the next job. That ignores *how much work remains* relative to the
*capacity that remains*.

Concretely (seed 201, high-inference, `guarded_online`), training job T2 had
deadline 71, needed 48.97 MWh at 2.0 MW, and received **exactly zero power for
hours 20–48**. Earlier-deadline jobs with far more slack (jobs that could have
deferred, e.g. 6.1/5.5 MW against 50 % slack) consumed all spare IT capacity.
By the time T2 became the earliest deadline there were only 2–3 hours left and
it could physically deliver only about 4 MWh. A perfect-information LP finishes
the same job with ~4.9 h of spare capacity, so its deadline miss was a dispatch
decision, not a physical impossibility.

Classic EDF optimality results rely on specific scheduling assumptions; they do
not establish optimality for this model with varying shared capacity and per-job
power caps. The improvement below is also a heuristic, not an optimality theorem.

## What changed

`service_power()` now has three explicitly separated stages, all using only
currently knowable data.

1. **Ramp-down reservation (unchanged).** Power already committed to keep each
   running job's shutdown trajectory physically ramp-feasible is reserved first,
   exactly as before.
2. **Service targets, in least-laxity-first order.** Without ramps these are
   average remaining-work quotas; with ramps they are optimistic single-job
   necessary floors. The dispatcher serves the tightest jobs toward each target
   until it is met or
   capacity runs out. A job with plenty of slack now defers work it does not
   need yet instead of front-loading and starving a job that is nearly out of
   time.
3. **Surplus, in least-laxity-first order.** Capacity left after every target is
   met goes to the tightest jobs up to their per-hour caps.

The ordering key is the job's *laxity*: maximum energy still deliverable before
its deadline minus energy still required. Lower is more urgent; below zero
the job cannot finish even with its optimistic single-job trajectory. Zero
means that trajectory is exactly sufficient, with no remaining margin.

Two new helpers make this explicit and testable:

- `max_deliverable_energy(job, t, previous_power, policy)` — the most energy the
  job can still deliver in `[t, deadline)` from its current power level, with
  ramp-up and the ramp-down tail respected.
- `required_power_floor(...)` — a historical function name for a service target.
  Without ramps it returns average remaining work per remaining slot, a quota
  rather than an exact minimum for this hour. With ramps it uses bisection on
  an optimistic single-job trajectory. Competition is omitted; unavailable
  capacity may truncate targets. An unreachable ramped job receives its cap as
  its target and any shortfall remains visible.

## Causality

Every input to the new logic at hour `t` is knowable at hour `t`:

| Input | Source | Future actual? |
|---|---|---|
| `remaining[k]` | accumulating committed power so far | no |
| `job.release`, `job.deadline`, `max_power_mw` | announced job spec | no |
| `previous[k]` | last hour's committed power | no |
| `policy.ramp_mw_per_hour`, `efficiency` | declared assumption | no |
| `inference` | current telemetry (fast stage) | no — hour `t` only |

`max_deliverable_energy` and `required_power_floor` read no scenario arrays at
all; they depend only on job parameters, remaining work and the current power.
No future actuals, no unannounced jobs, no oracle information. The regression
tests `test_laxity_dispatch_preserves_causality` and
`test_laxity_edf_preserves_causality` re-verify this by mutating future actuals
and a not-yet-released job's energy and asserting bit-identical decisions before
the change point.

## Physical constraints

Unchanged and re-verified:

- IT capacity is still the hard spare bound; capacity beats service when they
  conflict, and `evaluate()` still reports any excess.
- Ramp limits are enforced in reservation, floor and surplus stages.
- Battery, grid import and SoC constraints are untouched (they live in the LP).
- Impossible jobs are still dispatched what they can physically receive and
  still reported as failures; nothing is hidden.

Across all 360 guarded method runs in the seeds 200–219 study:
capacity violations 0, grid-limit violations 0, battery violations 0, ramp
violation events 0. Fresh seeds 220–239 repeat the same zeros.

## Results

### Seeds 200–219 (regression set)

Guarded MPC feasible runs out of 20:

| Profile | Policy | Before | After |
|---|---|---:|---:|
| Typical | guarded_online | 20 | **20** |
| Typical | guarded_delayed | 20 | **20** |
| Typical | guarded_combined | 17 | **18** |
| Low green | guarded_online | 20 | **20** |
| Low green | guarded_delayed | 20 | **20** |
| Low green | guarded_combined | 17 | **18** |
| High inference | guarded_online | 16 | **20** |
| High inference | guarded_delayed | 16 | **20** |
| High inference | guarded_combined | 8 | **17** |

All guarded method runs: **308/360 → 346/360 feasible**. Total unmet energy
**357.68 → 38.65 MWh**. Runs with any unmet work: 52 → 14.

- Previously-feasible guarded runs now failing: **0**.
- Previously-failing guarded runs now feasible: **38**.
- `deadline_oracle_check.csv`: **19/26 → 0/7** oracle-feasible failures.

The seven remaining failures were already oracle-infeasible: the
perfect-information LP cannot finish them under the same physical assumptions
either. No oracle-feasible failure remains in this regression set; this is not a
universal guarantee for other workloads.

### Fresh seeds 220–239 (not used during development)

| Policy | Typical | Low green | High inference |
|---|---:|---:|---:|
| guarded_online | 20/20 | 20/20 | 20/20 |
| guarded_delayed | 20/20 | 20/20 | 20/20 |
| guarded_combined | 19/20 | 19/20 | 19/20 |

The only fresh failures are seed 239 under `guarded_combined`, and the oracle
reports **0/3 oracle-feasible** for them: they stay failed under perfect future
knowledge too. No parameter was retuned after seeing these results.

### Matched no-battery laxity reference

`causal_edf_schedule` shares `service_power()`, so the reference receives the
identical improvement. MPC-versus-matched-reference feasibility agreement is **180/180
pairs** (seeds 200–219) and **180/180 pairs** (fresh seeds 220–239). The battery
still cannot outperform its fixed service stage, which is the property the
previous review required; only dispatch improved, for both methods.

Price-driven job shifting is still deliberately surrendered by the guard. Where
`guarded_online`/`guarded_delayed` are fully feasible, paired objective savings
against the matched no-battery laxity reference remain +5.1 % typical, +5.3 % low green, +5.1 % high
inference (seeds 200–219); fresh seeds give +5.0 %, +5.1 %, +4.9 %. Savings are
still suppressed whenever any pair is infeasible.

### Cost of the improvement

Across the 308 guarded runs that were feasible before and after, cost rose
0.12 % and CO2 0.22 %: serving a job earlier is
sometimes a less price-selective choice. Across all 360, mean objective change
is +0.21 % (median +0.10 %). That is the explicit price of completing 38 more
runs and 319 MWh more work; it is reported, not traded away silently.

## Remaining limitations

1. **Genuine infeasibility remains.** Seven seeds 200–219 cases and one seed
   239 case cannot be completed even by a perfect-information LP. They stay in
   the raw results as failures with their unmet energy.
2. **Ramp × checkpoint interaction.** The remaining failures are all
   `guarded_combined`. Isolation runs show each ingredient alone is feasible on
   those seeds (`delay_only`, `overhead_only`, `ramp_only` pass); the failure
   requires the 2 MW/h ramp limit *and* the 5 % checkpoint overhead together,
   which only affects the combined stress policy.
3. **Laxity uses a capacity-free bound.** `max_deliverable_energy` assumes the
   job could use its own cap in every future hour, ignoring competition. That
   is optimistic for absolute feasibility and provides no conservative ranking guarantee, so
   tight multi-job hours can still mis-order when several jobs race the same
   deadline.
4. **Sequential floors, not one LP.** Floors are allocated greedily in laxity
   order; when floors jointly exceed capacity they are simply truncated. An
   LP over released jobs could optimize a chosen modeled objective, but would
   still lack unknown arrivals and future actuals and would add a solve per hour.
5. **Instability risk of laxity ordering.** Least-laxity-first can in principle
   switch service between near-equal jobs more often than EDF. No ramp or
   capacity violation appeared in 720 guarded runs, but job-level switching was
   not instrumented.
6. **Unchanged modeling assumptions.** Current-hour telemetry and timely
   actuation remain assumptions; hourly granularity, continuous compute,
   amortized checkpoint overhead, synthetic profiles and the absence of real
   workload traces all remain from the earlier review. This is not operational
   validation.
7. **Small cost regression.** The 0.12 % cost / 0.22 % CO2 increase on
   still-feasible runs is a real trade-off of proactive service, not noise.

## Reproduction

```bash
python -m pytest -q                       # 166 tests
python robustness_experiments.py --output-dir output-regression   # seeds 200-219
python check_guarded_deadlines.py --output-dir output-regression
python -c "from robustness_experiments import run_validation; \
           run_validation('output-fresh', seeds=range(220,240))" # fresh
```

New tests live in `tests/test_improved_scheduling.py` (40 tests): helper
semantics, ramp trajectory bounds, causality for MPC and the matched no-battery reference, laxity
ordering, MPC/matched-reference feasibility agreement, all 19 formerly oracle-feasible cases,
and the 7 oracle-infeasible cases staying failed. Full suite: **166 passed**
(126 original + 40 new).


Renewable-share accounting was corrected after this comparison. Historical
green-share deltas from the previous drawn-energy/load definition are omitted.
Current results use mixed-battery renewable load-service attribution described
in ASSUMPTIONS.md. Scheduling, objective and feasibility comparisons are unchanged.
