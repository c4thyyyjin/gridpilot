# Fix 2: feasibility handling and reporting

## Behavior

- MPC first solves a strict window with hard job-energy and grid-import bounds.
  Only infeasibility triggers a penalized fallback; other solver errors raise.
- Fallback hours are retained. Inference-only overload is explicitly classified,
  with zero additional job power in those hours. Physically impossible demand is
  reported, not described as feasible.
- Every optimizer records its effective grid limit in Schedule.info. Evaluation
  resolves the limit in this order: explicit `grid_limit=` argument, schedule
  metadata, config. `None` explicitly means unlimited. Both overflow energy and
  violation-hour counts use the same resolved limit.
- Evaluation exposes status, feasibility, unmet MWh, overflow MWh, fallback count,
  operating objective, and penalized objective. `comparison_key` ranks feasible
  schedules first, then monetary objective. Finite penalties alone do not promise
  that any degraded run costs more than every feasible run.
- Experiment savings require every run of both the method and the observed-demand
  baseline to be feasible. Otherwise the gain is blank, not zero. Infeasible
  runs retain their operating cost, penalties and diagnostics for inspection.
- Pareto plots exclude infeasible candidates. Captions describe observations
  rather than promising universal feasibility. Unexpected stress-test errors
  propagate; stress config is restored in a finally block.

## Outputs

The existing seven experiment CSVs remain, with two additional files:

- `results/run_metrics.csv`: every seed/method/parameter run, including status,
  penalties, unmet energy, overflow, effective evaluation limit, and fallback hours.
- `results/feasibility.csv`: per-method/experiment summaries, feasible/degraded/
  overload counts, mean penalties, and worst-case unmet energy and violations.

`results/RESULTS.md` includes feasibility diagnostics for each experiment section.
The batch column joins individual runs to the summary table and its section.
A blank gain indicates an ineligible comparison; it must not be interpreted as
zero improvement or silently filled with zero.

## Scope

This resolves limitation 2's handling and reporting gaps. It cannot make physically
impossible scenarios feasible. Cheap-tariff support is still limitation 3. Synthetic
data, observation timing, GPU granularity and economic realism remain separate
limitations.

## Validation

All 63 tests passed across the full test set, including custom-limit precedence,
feasibility-aware gains, infeasible-baseline exclusion, overload and fallback
cases, CBC/HiGHS agreement, and quick regeneration. The full five-seed experiment
run regenerated nine CSVs, RESULTS.md, and five verified PNGs. Headline MPC
objective improvement is 20.54%, with all five MPC and baseline runs feasible.
