# Limitation 8: grid capacity, storage capital cost and demand billing

Item 8 of LIMITATIONS_REVIEW.md identified missing capital costs, demand charges
and a grid-limit sweep. These analyses are now implemented separately from the
original dispatch objective. They are scenario screens, not a tariff-calibrated
investment recommendation or a demand-charge-optimal controller.

## Grid connection sweep

The full run tests 10, 16, 20, 24, 26, 28 MW and uncapped imports; quick mode tests
10 MW, the configured limit and uncapped. Each candidate uses the same seed,
battery, prices and forecast error. The reference for the **cost of a cap** is
uncapped MPC, not the EDF baseline. `grid_cap.csv` reports cost/objective changes,
paired 95% Student-t intervals and worst-case feasibility diagnostics. A realized
MPC delta can be negative because different plans interact with forecast errors;
it is not a claim that a constraint improves a perfect-information optimum.
Infeasible cap/reference pairs disqualify the comparison, with blank cost deltas.
The cap plot shows those cases explicitly rather than treating shed work as savings.

`grid_cap_economics.csv` ranks only feasible, priced candidates under each billing
assumption. `best_in_tested_sweep` means best among the tested schedules/caps,
not a globally optimal connection contract. Capacity-charge billing cannot price
an uncapped contract at a positive rate; those cells are undefined and cannot win.
Economic summaries distinguish dispatch_feasible_runs from economic_eligible_runs:
the latter additionally requires defined billing. Raw dispatch_status is retained.

## Configurable economic assumptions

The values below are **illustrative sensitivity inputs**, not vendor quotations,
verified Chinese tariffs or a claim about the current market:

| Input | Default assumption |
|---|---|
| Installed all-in battery cost | 500, 1000, 1500 CNY/kWh |
| Additional power-specific cost | 0 CNY/kW; use only if not already in the all-in quote |
| Economic life | 10 years |
| Discount rate | 8% per year, constant purchasing-power convention |
| Fixed non-throughput maintenance | 1.5% of installed capital per year |
| Demand charge | 0, 20, 40 CNY/kW/month |
| Billing alternatives | Contracted capacity OR measured peak, never both |
| Annualization | Repeat each simulated block to 8760 hours; repeat its peak each month |

Every input is in config.py and can be overridden using the existing JSON config
interface. Seed-level records retain financing, rate, size, horizon and billing
assumptions in `economics_runs.csv`.

## Formulas and attribution

For battery energy E in MWh and power P in MW:

- CAPEX = 1000 * (E * installed_CNY_per_kWh + P * extra_CNY_per_kW).
- Capital recovery factor CRF = r / (1 - (1+r)^(-n)); at r=0, CRF=1/n.
- Annual capital cost = CAPEX * CRF; fixed O&M = CAPEX * fixed_OM_fraction.
- Annual operating cost = evaluator cost * 8760 / simulated_hours. This already
  includes charging losses and the throughput-degradation charge; fixed O&M
  excludes those costs to avoid counting them twice.
- Annual demand bill = billed_MW * 1000 * CNY_per_kW_month * 12. Billed power is
  either contracted capacity or the observed block peak, according to the case.
- Annual total = operating + demand + annualized capital + fixed O&M.
- Storage savings compare each size against **zero-battery MPC job shifting** on
  the same seeds and contract. Savings from job shifting are not attributed to storage.
- Annual cash saving = reference operating/demand cost minus candidate
  operating/demand cost minus fixed O&M.
- Simple payback = CAPEX / positive annual cash saving; otherwise undefined.
  The zero-battery reference also has no payback value. A positive simple payback
  can exceed the assumed project life; it is not a profitability guarantee.
- NPV = -CAPEX + annual_cash_saving / CRF, with no salvage, tax, subsidy, extra
  replacement payment or monetized carbon credit. Degradation is already expensed.
  Annualized net savings separately subtract the capital annuity; NPV/payback
  do not subtract the annuity again. Summary payback is CAPEX divided by mean
  annual cash savings, rather than the mean of individual-seed payback ratios.

Annualization and capital recovery follow the standard annuity approach described
in the [ATB equations and definitions](https://atb.nlr.gov/electricity/2025/equations_%26_variables).
This source supports the methodology, not the illustrative CNY assumptions.

## Outputs and remaining scope

Four CSVs are added: `grid_cap.csv`, `grid_cap_economics.csv`,
`battery_economics.csv`, `economics_runs.csv`. Two figures are added:
`grid_cap.png` and `battery_economics.png`. Existing per-seed, feasibility and
paired-statistics files also include the grid-cap sweep. There are fifteen CSVs
and seven PNGs in a full or quick regeneration.

Economic costs are post-processed for energy/carbon-optimized schedules. Demand
charges have not been added to the hourly controller's objective. Its monthly
history, ratchets and demand-response billing are not modeled. A 72-hour peak is
not a measured monthly maximum, and repeated-block annual costs are not an actual
yearly bill. Real investment/contract decisions need vendor quotes, site tariffs,
seasonal traces and demand-aware dispatch. Item 8's missing analyses are addressed;
their numerical conclusions remain conditional on the stated assumptions.

## Verification

All 100 tests passed in the locked environment. Twelve economics unit tests
cover cost units, annualization, zero-interest capital recovery, alternative
billing, an unpriced uncapped contract, zero-battery attribution, NPV/payback,
infeasible cases, paired cap deltas and invalid financing/seed inputs. The
quick CLI test regenerates fifteen CSVs and seven figures, retaining infeasible
cap cases without savings claims.

The final full run regenerated fifteen CSVs and seven verified PNGs, including
660 seed-level economic cases. The 26 MW cap added 369.61 CNY
per 72-hour block versus uncapped MPC (mean across five seeds), and
401.95 CNY to the priced-carbon objective. The 10 MW cap
was infeasible and excluded from cost/economic savings rankings. Both new plots
were inspected visually; affected tests passed again after plot/numerical cleanup.
