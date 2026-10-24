# Limitations and resolution status

All ten original review items have been addressed within the scope below.
The implementation fixes, added experiments and reporting improvements are
complete; this does not mean that the prototype has no modeling limitations.
This document describes the final submission, rather than earlier snapshots.

| Item | Original concern | Final implementation and evidence |
|---|---|---|
| 1 | Baseline used forecasts while scoring used actual inference | Simple observed-demand EDF is the headline baseline. Forecast EDF remains a separately labeled comparison. Feasibility is checked before claiming savings. |
| 2 | Penalized slack could hide unmet work and physical overload | Strict-first MPC uses hard bounds; infeasibility triggers an explicitly recorded fallback. The evaluator reports unmet work, overload, grid/battery/ramp violations and penalties. Infeasible comparisons have no savings claim. |
| 3 | Unsupported tariffs could distort the green-first LP | Shared tariff validation rejects unsupported objective rates in CBC, HiGHS and MPC. Arbitrary cheap-tariff dispatch is outside the supported formulation. |
| 4 | Averages concealed failures and lacked paired uncertainty | Raw per-seed records, worst-case diagnostics, paired savings and pointwise 95% Student-t intervals are retained. Unexpected errors propagate. |
| 5 | Advance job knowledge and ideal observations | Online policies see released jobs only. Delayed optimizer observations and a declared fast current-telemetry execution stage are recorded separately in decision traces. Causality is tested. |
| 6 | Free continuous compute omitted practical restrictions | Optional per-job ramps and amortized overhead are implemented, with ramp-down reservations and laxity-based service targets. Continuous allocation and amortized overhead remain explicit approximations. |
| 7 | Narrow synthetic validation | Unscreened three-profile studies use regression seeds 200–219 and fresh validation seeds 220–239, each with 1,080 method runs from 20 unique seeds. Failed cases remain visible; oracle diagnostics check their modeled feasibility. |
| 8 | Missing capital costs, demand billing and grid-cap sensitivity | Grid-cap sweeps, annualized capital/O&M, alternative demand billing, incremental battery value, NPV and payback screens are implemented. Inputs are illustrative. |
| 9 | Import side effects, fragile configuration and reproduction | Import-safe runner, explicit output/configuration, restoration on failure, dependency lock and current reproduction commands are provided. |
| 10 | Overlapping Pareto labels | Coincident labels are grouped and separated with leader lines; plotted point data are preserved. |

## Current evidence

The recorded final suite has **206 passing tests**. The final verification report
is [review/VERIFICATION.md](../review/VERIFICATION.md).

Fresh guarded MPC feasibility, out of 20 seeds per cell:

| Policy | Typical | Low green | High inference |
|---|---:|---:|---:|
| guarded_online | 20 | 20 | 20 |
| guarded_delayed | 20 | 20 | 20 |
| guarded_combined | 19 | 19 | 19 |

Across 360 fresh guarded method runs, including the matched reference, saved
records report zero capacity, grid, battery and ramp violations. Six method runs
fail job completion: seed 239 under the combined policy, in three profiles and
two methods. The three corresponding MPC cases are also infeasible for the
same-constraint perfect-information oracle. Group savings are suppressed for
these combined-policy comparisons.

## Remaining model and evidence limits

- Data are synthetic 72-hour hourly traces, not measured operational workloads.
  The fresh study has 20 unique seeds; its 1,080 method runs are not independent
  scenarios. Profiles share base draws.
- Compute is continuous. Overhead is an assumed amortized fraction, not a measured
  per-resume cost; GPU blocks, detailed idle-server behavior and within-hour
  dynamics are not modeled.
- The fast executor assumes timely current-hour telemetry and actuation. Delayed
  optimization does not establish a hardware latency guarantee.
- Laxity uses optimistic single-job deliverable energy and ignores future
  competition. Sequential service targets can exceed shared capacity; there is
  no universal deadline guarantee or proof of online global optimality.
- Physically impossible workloads remain infeasible. LP optimality and independent
  solver agreement apply to the stated model and supplied information.
- Tariff and investment inputs are illustrative pending site-specific calibration.
  Demand billing is post-processed, not optimized inside dispatch; repeated-block
  annualization is not an actual annual bill.
- Confidence intervals describe generated-seed comparisons under their assumptions,
  not operational uncertainty or simultaneous significance across all studies.
- The lock was tested on macOS ARM64/Python 3.13.5; it does not guarantee identical
  solver binaries or figure rendering on every platform.

See [CONTROLLER.md](CONTROLLER.md), [ECONOMICS.md](ECONOMICS.md) and
[ASSUMPTIONS.md](../ASSUMPTIONS.md) for technical scope. The separate original
headline gain (about 20.54% versus observed-demand EDF) and fresh guarded gain
(about 4.92–5.09% versus matched no-battery laxity service) use different
references and must not be presented as the same comparison.
