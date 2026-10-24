# Online service and explicit fast-safety follow-up

This folder is a copy of `step6 fix4910`, named `step6 fix567`. Prior snapshots
and results remain unchanged. This follow-up addresses controller failures exposed
by the earlier limitations 5–7 study; it does not supply missing real-world data.

## Changes

- `guarded_online`, `guarded_delayed` and `guarded_combined` are opt-in policies.
  Original policies remain available as controls. Existing headline experiments
  continue to use their original controller.
- The service stage executes released jobs in earliest-deadline order immediately,
  rather than allowing energy prices to postpone all known work. It reserves the
  power needed to ramp down already-running jobs before allocating extra work.
  Only released jobs affect this stage; unknown arrivals remain unknown.
- The delayed optimizer still receives its delayed residual-based estimate. A
  separate, explicitly declared fast stage reads current inference and renewable
  power, computes service within current capacity, and replans battery dispatch.
  The battery LP fixes current job power in both strict and fallback solves.
  It uses forecasts for future hours and sees only announced jobs. Both paired
  EDF and MPC policies receive this current-telemetry capability.
- MPC traces distinguish `observed_through` (optimizer) from
  `safety_observed_through` (execution). They retain planned and committed job
  power, so interventions and the expanded information assumption are visible.
- `service_guard=True` sacrifices price-driven job shifting. The battery retains
  optimization; this is a conservative service policy rather than a claim of
  retaining all the earlier flexible-job savings.

## Limits that remain

Current-hour telemetry and timely actuation are explicit assumptions of the fast
stage. It is an hourly simulation, not a hardware implementation or within-hour
latency guarantee. Inference alone above capacity cannot be fixed by scheduling.
Conflicting ramp, capacity or deadline constraints remain scored failures; a
sudden load increase can make a mandatory ramp-down trajectory impossible. No
online controller can guarantee arbitrary unannounced workloads meet deadlines.
Grid limits below physically necessary demand can still require reported slack.

Checkpoint overhead is still an assumed amortized fraction, rather than a
calibrated per-resume cost. Compute remains continuous. Actual workload traces,
GPU granularity and hardware calibration remain open. Thus limitations 5 and 6
have stronger implementations, and 7 has broader synthetic evidence; none is a
claim of operational validation.

## Reproduction

```bash
python -m pytest -q
python robustness_experiments.py --output-dir guarded_results
```

The full fresh comparison uses seeds 200–219, three profiles, nine policies and
two methods: 1,080 method runs from 20 unique seeds. Seeds 100–119 informed the
fix and are no longer treated as untouched validation data. All first generator
draws are retained, including failed cases. Every policy has the same-capability
EDF reference. Monetary comparisons remain suppressed if any paired run fails.
See `guarded_results/RESULTS.md`, raw CSVs and trace/manifest JSON for outcomes.

## Verified outcomes

All 126 tests passed. The complete fresh study produced 1,080 unique method
runs (20 seeds × 3 profiles × 9 policies × 2 methods), with group counts checked.

MPC feasible runs out of 20:

| Profile | Legacy online | Legacy delayed | Guarded online | Guarded delayed | Guarded combined |
|---|---:|---:|---:|---:|---:|
| Typical | 9 | 0 | 20 | 20 | 17 |
| Low green | 10 | 0 | 20 | 20 | 17 |
| High inference | 4 | 0 | 16 | 16 | 8 |

Across all 360 guarded method runs, capacity, grid, battery and ramp violations
were zero. 308/360 were fully feasible; the 52 failures were deadline misses
shared identically by paired EDF and MPC. Equal service is deliberate; battery
optimization must not claim better job completion than its fixed EDF service stage.

An additional perfect-information, full-horizon LP checks the 26 failed guarded
MPC cases: **19/26 are feasible with future knowledge**, and seven are infeasible
even for that oracle under the same physical assumptions. Thus the remaining
misses cannot all be blamed on impossible inputs. EDF admission/service is still
a heuristic, and online uncertainty remains a substantive limitation. No retuning
was performed after inspecting fresh-seed results.

Reproduce that diagnostic with `python check_guarded_deadlines.py`. It writes
`guarded_results/deadline_oracle_check.csv`; it never informs online decisions.
The guard repairs the tested physical-limit violations and improves service;
it does **not** fully solve online deadline scheduling or limitations 5–7.
