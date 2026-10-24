"""Illustrative operating/investment accounting, separate from dispatch optimization.

Annualization repeats the simulated block; its peak is a monthly-peak proxy.
Economic inputs are sensitivity assumptions, not market quotes or real tariffs.
"""
import math
import numpy as np
import pandas as pd
from reporting import aggregate, paired_comparisons


def nonnegative(value, name):
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return value


def capital_recovery_factor(rate, years):
    rate = nonnegative(rate, "discount rate")
    years = float(years)
    if not math.isfinite(years) or years <= 0:
        raise ValueError("life must be positive and finite")
    if rate == 0:
        return 1 / years
    return rate / -math.expm1(-years * math.log1p(rate))


def annual_costs(run, *, energy_cost, power_cost, years, discount, fixed_om,
                 demand_rate, billing_basis, annual_hours=8760):
    energy_cost = nonnegative(energy_cost, "energy cost")
    power_cost = nonnegative(power_cost, "power cost")
    fixed_om = nonnegative(fixed_om, "fixed maintenance fraction")
    demand_rate = nonnegative(demand_rate, "demand rate")
    annual_hours = nonnegative(annual_hours, "annual hours")
    hours = float(run["horizon_hours"])
    if not math.isfinite(hours) or hours <= 0 or annual_hours == 0:
        raise ValueError("horizon and annual hours must be positive")
    if billing_basis not in {"contracted_capacity", "measured_peak"}:
        raise ValueError("unknown demand billing basis")
    capex = 1000 * (nonnegative(run["battery_mwh"], "battery energy") * energy_cost
                    + nonnegative(run["battery_power_mw"], "battery power") * power_cost)
    annual_capital = capex * capital_recovery_factor(discount, years)
    annual_om = capex * fixed_om
    annual_operating = float(run["cost_cny"]) * annual_hours / hours
    annual_carbon = float(run["co2_t"]) * annual_hours / hours
    billed_mw = run["grid_limit_mw"] if billing_basis == "contracted_capacity" else run["peak_grid_mw"]
    defined = demand_rate == 0 or (billed_mw is not None and math.isfinite(float(billed_mw)))
    annual_demand = (0.0 if demand_rate == 0 else
                     nonnegative(billed_mw, "billed power") * 1000 * demand_rate * 12) if defined else np.nan
    eligible = bool(run["feasible"]) and defined
    return dict(capex_cny=capex, annualized_capital_cny=annual_capital,
                annual_fixed_om_cny=annual_om, annual_operating_cny=annual_operating,
                annual_demand_cny=annual_demand, annual_co2_t=annual_carbon,
                annual_total_cny=annual_operating + annual_capital + annual_om + annual_demand
                if eligible else np.nan,
                economics_eligible=eligible,
                economics_status="feasible" if eligible else
                                 "infeasible_dispatch" if not run["feasible"] else "undefined_contract")


def grid_cap_summary(rows):
    """Paired cap-minus-uncapped effects; realized MPC effects can be signed."""
    mpc = [r for r in rows if r["method"] == "MPC"]
    reference = {r["seed"]: r for r in mpc if r["grid_limit_mw"] is None}
    if not reference:
        raise ValueError("uncapped MPC reference required")
    result = []
    for label in dict.fromkeys(r["grid_limit_label"] for r in mpc):
        group = [r for r in mpc if r["grid_limit_label"] == label]
        if len({r["seed"] for r in group}) != len(group) or set(r["seed"] for r in group) != set(reference):
            raise ValueError("grid caps must have unique identical seed sets")
        pair_rows = []
        for candidate in group:
            pair_rows.extend([dict(reference[candidate["seed"]], batch=0, method="baseline"),
                              dict(candidate, batch=0, method="MPC")])
        stats, _ = paired_comparisons(pair_rows)
        summary = dict(grid_limit_label=label, grid_limit_mw=group[0]["grid_limit_mw"], **aggregate(group))
        for metric in ("cost_cny", "objective"):
            stat = stats[stats.metric == metric].iloc[0]
            summary[f"{metric}_delta_vs_uncapped"] = -stat.saving_mean
            summary[f"{metric}_delta_ci_low"] = -stat.saving_ci_high
            summary[f"{metric}_delta_ci_high"] = -stat.saving_ci_low
            summary["comparison_eligible"] = bool(stat.eligible)
        result.append(summary)
    return pd.DataFrame(result)


def economics_tables(grid_rows, battery_rows, settings):
    """Return grid summaries, battery summaries, and every seed-level economic case."""
    records = []
    constants = dict(power_cost=settings["power_cost"], years=settings["years"],
                     discount=settings["discount"], fixed_om=settings["fixed_om"],
                     annual_hours=settings["annual_hours"])
    for analysis, runs, costs in (("grid_cap", grid_rows, [settings["base_energy_cost"]]),
                                  ("battery", battery_rows, settings["energy_costs"])):
        mpc = [r for r in runs if r["method"] == "MPC"]
        for cost in costs:
            for rate in settings["demand_rates"]:
                for basis in ("contracted_capacity", "measured_peak"):
                    for run in mpc:
                        record = dict(analysis=analysis, seed=run["seed"],
                                      grid_limit_label=run["grid_limit_label"], grid_limit_mw=run["grid_limit_mw"],
                                      battery_mwh=run["battery_mwh"], battery_power_mw=run["battery_power_mw"],
                                      dispatch_status=run["status"], energy_cost_cny_per_kwh=cost,
                                      demand_rate_cny_per_kw_month=rate, billing_basis=basis,
                                      horizon_hours=run["horizon_hours"], economic_life_years=constants["years"],
                                      discount_rate=constants["discount"], fixed_om_fraction=constants["fixed_om"],
                                      annual_hours=constants["annual_hours"], power_cost_cny_per_kw=constants["power_cost"])
                        record.update(annual_costs(run, energy_cost=cost, demand_rate=rate,
                                                   billing_basis=basis, **constants))
                        records.append(record)
    raw = pd.DataFrame(records)
    keys = ["energy_cost_cny_per_kwh", "demand_rate_cny_per_kw_month", "billing_basis"]
    # Attribute storage value to storage: reference is MPC job shifting with zero battery.
    battery = raw[raw.analysis == "battery"].copy()
    if battery[battery.battery_mwh == 0].empty:
        raise ValueError("zero-battery MPC reference required")
    battery["payback_status"] = ""
    for column in ("annual_cash_saving_cny", "annual_net_saving_cny", "npv_cny", "simple_payback_years"):
        battery[column] = np.nan
    battery_summaries = []
    for _, group in battery.groupby(keys, sort=False):
        baseline = group[group.battery_mwh == 0].set_index("seed")
        if baseline.index.has_duplicates:
            raise ValueError("duplicate zero-battery seed")
        for size, candidates in group.groupby("battery_mwh", sort=False):
            if candidates.seed.duplicated().any() or set(candidates.seed) != set(baseline.index):
                raise ValueError("battery cases must have identical unique seed sets")
            all_valid = bool(candidates.economics_eligible.all() and baseline.economics_eligible.all())
            for idx, candidate in candidates.iterrows():
                ref = baseline.loc[candidate.seed]
                valid = bool(candidate.economics_eligible and ref.economics_eligible)
                gross = ((ref.annual_operating_cny - candidate.annual_operating_cny)
                         + (ref.annual_demand_cny - candidate.annual_demand_cny))
                cash = gross - candidate.annual_fixed_om_cny
                battery.loc[idx, "annual_cash_saving_cny"] = cash if valid else np.nan
                battery.loc[idx, "annual_net_saving_cny"] = ref.annual_total_cny - candidate.annual_total_cny if valid else np.nan
                battery.loc[idx, "npv_cny"] = (-candidate.capex_cny + cash / capital_recovery_factor(constants["discount"], constants["years"])) if valid else np.nan
                battery.loc[idx, "simple_payback_years"] = candidate.capex_cny / cash if valid and cash > 0 and size > 0 else np.nan
                battery.loc[idx, "payback_status"] = ("ineligible" if not valid else "reference" if size == 0
                                                       else "positive_cash_saving" if cash > 0 else "no_positive_cash_saving")
            updated = battery.loc[candidates.index]
            summary = {k: candidates.iloc[0][k] for k in keys}
            summary.update(battery_mwh=size, n_runs=len(candidates), eligible=all_valid,
                           economic_eligible_runs=int(candidates.economics_eligible.sum()),
                           dispatch_feasible_runs=int((candidates.dispatch_status == "feasible").sum()))
            for col in ("capex_cny", "annualized_capital_cny", "annual_fixed_om_cny", "annual_operating_cny",
                        "annual_demand_cny", "annual_total_cny", "annual_cash_saving_cny", "annual_net_saving_cny", "npv_cny"):
                summary[col] = updated[col].mean() if all_valid else np.nan
            cash_mean = summary["annual_cash_saving_cny"]
            summary["simple_payback_years"] = summary["capex_cny"] / cash_mean if all_valid and size > 0 and cash_mean > 0 else np.nan
            summary["payback_status"] = "ineligible" if not all_valid else "reference" if size == 0 else "positive_cash_saving" if cash_mean > 0 else "no_positive_cash_saving"
            battery_summaries.append(summary)
    # Aggregate only when every seed of a candidate is feasible and its bill is defined.
    grid = raw[raw.analysis == "grid_cap"]
    grid_summaries = []
    for _, candidates in grid.groupby(keys + ["grid_limit_label"], sort=False):
        valid = bool(candidates.economics_eligible.all())
        summary = {k: candidates.iloc[0][k] for k in keys + ["grid_limit_label"]}
        summary.update(grid_limit_mw=candidates.iloc[0].grid_limit_mw, n_runs=len(candidates),
                       eligible=valid, economic_eligible_runs=int(candidates.economics_eligible.sum()),
                           dispatch_feasible_runs=int((candidates.dispatch_status == "feasible").sum()))
        for col in ("annual_operating_cny", "annual_demand_cny", "annualized_capital_cny", "annual_fixed_om_cny", "annual_total_cny"):
            summary[col] = candidates[col].mean() if valid else np.nan
        grid_summaries.append(summary)
    grid_summary = pd.DataFrame(grid_summaries)
    grid_summary["best_in_tested_sweep"] = False
    for _, group in grid_summary.groupby(keys, sort=False):
        valid = group[group.eligible]
        if not valid.empty:
            grid_summary.loc[valid.index, "best_in_tested_sweep"] = np.isclose(valid.annual_total_cny, valid.annual_total_cny.min(), rtol=1e-10, atol=.01)
    raw = pd.concat([grid, battery], ignore_index=True)
    return grid_summary, pd.DataFrame(battery_summaries), raw
