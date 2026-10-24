# Limitation 4: reporting and statistical evidence

This implements item 4 from the original `LIMITATIONS_REVIEW.md`: preserve
individual runs, include every feasibility flag and slack measure, report
worst-case failures and paired intervals, and propagate unexpected errors.

## Reports

- `run_metrics.csv` retains each seed/method/parameter run, including battery
  violations, status, unmet MWh, grid overflow, and fallback diagnostics.
- `feasibility.csv` retains means and now adds worst-case values, totals, and the
  number of affected runs for SLA, capacity, grid-limit, battery, inference
  overload, fallback, unmet-energy and overflow metrics. Peak grid draw also
  has a maximum across seeds. A small mean cannot conceal a single bad run.
- `paired_seed_savings.csv` matches each candidate with the observed-demand
  baseline by **batch and seed**, retaining the underlying values and both
  feasibility statuses. Duplicate or missing pairs raise an error.
- `paired_comparisons.csv` provides paired results for objective, cost and CO2:
  mean absolute savings, mean per-seed percentage savings, and two-sided 95%
  Student-t confidence intervals. Each experiment section includes these
  intervals and worst-case diagnostics in `RESULTS.md`.
- A candidate/baseline comparison is eligible only when **all** seed pairs are
  feasible. Bad pairs remain in the raw data and disqualify the whole comparison;
  they are not removed to produce an optimistic estimate.
- The lambda sweep now evaluates baseline and MPC in the same batch to preserve
  explicit pairing. Model decisions and objective functions are unchanged.

## Statistical interpretation

For each seed, absolute saving is baseline minus candidate. Percentage saving
is 100 times that difference divided by that seed's baseline. The interval is
mean +/- t(0.975, n-1) * sample standard deviation / sqrt(n). A positive interval
means the generated-seed mean saving is positive under the interval's assumptions.
The per-seed percentage mean differs from the ratio of means used by the older
headline gain column; both are labeled and retained.

Intervals are approximate with only three quick-run or five full-run seeds.
They assume independent seed draws and approximately normal paired differences.
They do not quantify real-site uncertainty or provide simultaneous significance
across all sensitivity comparisons. More seeds/operational data remain limitation 7.

With fewer than two pairs the mean is retained but the interval is undefined.
A zero baseline makes percentage savings undefined while absolute savings can
still be reported. Infeasible comparisons have blank estimates with explicit
counts/status, never fabricated zeros.

## Unexpected failures

`run_stress()` restores configuration in `finally` and propagates setup/model
exceptions. The CLI therefore exits unsuccessfully on an unexpected error;
it cannot convert an error into an apparently valid result row. Regression
tests cover failures both during setup and during the model run.

## Verification

All 82 tests passed, including 11 new statistical/error-handling tests and the
updated quick CLI test checking eleven CSV outputs, paired data, intervals and
worst-case diagnostics. PuLP deprecation notices are unchanged.

The full five-seed run regenerated eleven CSVs, RESULTS.md and five valid PNGs.
It retained 410 runs and 750 paired seed/metric observations. Every
worst-case/affected-run count was checked against the raw runs. Headline MPC mean
per-seed objective saving is 20.524% with a pointwise 95%
paired Student-t interval [18.020%, 23.028%].
