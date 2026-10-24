# Fix 3: tariff validity guard for every LP implementation

## Problem
The green-first LP models cost as `green_rate*supply + (grid_rate - green_rate)*grid`. That is only valid when
`grid_rate[t] >= green_rate >= 0` in every hour (rates include the carbon price). Otherwise the solver is paid to
draw extra grid power. Before this fix only the CBC scheduler checked this. On a cheap tariff (0.20 CNY/kWh against a
0.30 green price) the HiGHS scheduler and the MPC/open-loop planner returned a schedule **silently**: the grid
import cap happened to bound the problem, so there was no solver error, but the plan was distorted.

## Behavior
- New `validation.py: check_green_first(sc, lam)` raises `UnsupportedTariff` (a `ValueError`) with the number of bad
  hours, the worst hour and its rates.
- `scheduler.py` (CBC), `scheduler_highs.py` and `mpc.py` (`solve_window`, hence open-loop and rolling) all call it
  first. CBC's private copy of the rule was removed so the three cannot drift apart.
- Negative lambda is not categorically rejected: it is accepted if the resulting objective rates remain valid.
- The rule is about objective rates, not raw price: a price of 0.29 is accepted when the carbon price makes the grid
  objective rate exceed the green rate (and the LP objective then equals the scorer's objective; tested).
- Unsupported tariffs are rejected, not approximated. Supporting them requires an exact formulation, such as a MILP enforcing green-first dispatch;
  the existing dispatch policy in `evaluate.py` can remain unchanged.
- The fallback in `mpc.py` still handles infeasible windows only; a raw unbounded solve still raises.

## Tests
`tests/test_tariff_guard.py` (8 tests): every implementation rejects a cheap tariff; one cheap hour is enough; the
boundary (rate equal to green) is accepted; carbon price can rescue a cheap raw price; a negative lambda producing invalid objective rates is rejected;
message content; all default scenarios and the full lambda sweep still pass; wiring check that no implementation
keeps a private copy of the rule. `test_feasibility.py` now exercises the raw solver for the unbounded case.

## Verification and caveats
- Full regeneration with and without the guard gives identical output in all nine CSVs (the guard changes no
  number).
- The CBC code path was only compile-checked where this fix was written (PuLP unavailable there); run the full suite
  including `test_cross_check.py` and `test_tariff_guard.py` where PuLP is installed.
- Regenerated CSVs differ slightly (at most about 0.04 %) from the previously supplied ones in a different
  environment; this predates the fix (limitation 9, solver tie-breaking / versions).
