# Guarded online controller

The current controller prioritizes released jobs using laxity: maximum remaining
deliverable energy minus required work. It reserves ramp-down service, allocates
service targets and distributes surplus capacity. A battery LP then plans
storage with current job power fixed. This favors service over price-driven
job shifting. The matched no-battery reference shares the same service heuristic.

The delayed optimizer uses delayed residual-based estimates. A separate fast
execution stage reads current inference and renewable telemetry; traces distinguish
optimizer and execution observation times. Unknown future jobs and future actuals
remain unavailable to the online controller. Prices/carbon and forecasts are
supplied exogenous inputs.

## Service allocation

`service_power()` has three explicitly separated stages, all using only
currently knowable data.

1. **Ramp-down reservation.** Power already committed to keep each
   running job's shutdown trajectory physically ramp-feasible is reserved first.
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

Two helpers make this explicit and testable:

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

Every input to the service logic at hour `t` is knowable at hour `t`:

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

Constraint handling:

- IT capacity is still the hard spare bound; capacity beats service when they
  conflict, and `evaluate()` still reports any excess.
- Ramp limits are enforced in reservation, floor and surplus stages.
- Battery, grid import and SoC constraints are handled in the LP; fallback
  violations remain explicit.
- Impossible jobs are still dispatched what they can physically receive and
  still reported as failures; nothing is hidden.

Across all 360 guarded method runs in the seeds 200–219 study:
capacity violations 0, grid-limit violations 0, battery violations 0, ramp
violation events 0. Fresh seeds 220–239 repeat the same zeros.


## Evidence and scope

Current study outputs are in improved_results/ (regression seeds 200–219) and
fresh_results/ (validation seeds 220–239). Each study contains 1,080 method runs
from 20 unique seeds. Recorded guarded feasibility is 346/360 for regression and
354/360 for fresh validation, including matched no-battery methods. Both have
zero recorded guarded capacity, grid, battery and ramp violations. All seven
regression and three fresh failed MPC cases remain infeasible for the
same-constraint perfect-information oracle.

The remaining fresh failures use the combined ramp/overhead stress policy.
Laxity ignores future competition and service targets are allocated sequentially;
the controller is a heuristic without a universal deadline guarantee. Current
telemetry and timely actuation are assumptions, and checkpoint overhead is an
amortized approximation. See [LIMITATIONS_REVIEW.md](LIMITATIONS_REVIEW.md).

Fresh online/delayed objective gains are about 4.92–5.09% versus the matched
no-battery laxity reference. Combined group gains are suppressed because some
pairs fail. The original headline model's approximately 20.54% gain versus
simple observed-demand EDF uses different information and service assumptions.

Use the README commands to run the controller, tests and studies. Saved manifests
record study configuration and policies for oracle reconstruction. Detailed final
verification is in [review/VERIFICATION.md](../review/VERIFICATION.md).
