import numpy as np
import pytest

from economics import annual_costs, capital_recovery_factor, economics_tables, grid_cap_summary
from reporting import METRICS


def run(seed=0, size=1, cost=100, peak=2, cap=3, feasible=True):
    r = dict.fromkeys(METRICS, 0.0)
    r.update(seed=seed, batch=0, method="MPC", status="feasible" if feasible else "degraded",
             feasible=feasible, battery_mwh=size, battery_power_mw=size/2, cost_cny=cost,
             objective=cost, co2_t=1, peak_grid_mw=peak, grid_limit_mw=cap,
             grid_limit_label="uncapped" if cap is None else f"{cap:g} MW", horizon_hours=24)
    return r


SETTINGS = dict(energy_costs=[1000], base_energy_cost=1000, power_cost=0,
                years=10, discount=0, fixed_om=.01, demand_rates=[0,20], annual_hours=8760)


def test_capital_recovery_factor_hand_values():
    assert capital_recovery_factor(0,10) == .1
    assert capital_recovery_factor(.1,2) == pytest.approx(.576190476190476)


def test_annual_cost_units_and_no_double_counting():
    r = annual_costs(run(),energy_cost=1000,power_cost=100,years=10,discount=0,
                     fixed_om=.01,demand_rate=20,billing_basis="contracted_capacity")
    assert r["capex_cny"] == 1_050_000  # 1 MWh * 1000 + .5 MW * 100 CNY/kW
    assert r["annualized_capital_cny"] == 105_000
    assert r["annual_fixed_om_cny"] == 10_500
    assert r["annual_operating_cny"] == 36_500
    assert r["annual_demand_cny"] == 720_000
    assert r["annual_total_cny"] == 872_000
    peak = annual_costs(run(),energy_cost=1000,power_cost=100,years=10,discount=0,
                       fixed_om=.01,demand_rate=20,billing_basis="measured_peak")
    assert peak["annual_demand_cny"] == 480_000  # alternative, not added to capacity fee


def test_uncapped_contract_cannot_claim_known_positive_capacity_charge():
    kwargs=dict(energy_cost=0,power_cost=0,years=10,discount=0,fixed_om=0,
                demand_rate=20,billing_basis="contracted_capacity")
    r=annual_costs(run(cap=None),**kwargs)
    assert r["economics_status"] == "undefined_contract" and np.isnan(r["annual_total_cny"])
    kwargs["demand_rate"]=0
    assert annual_costs(run(cap=None),**kwargs)["economics_eligible"]


def test_battery_value_uses_zero_battery_job_shifting_reference():
    battery=[run(size=0,cost=200),run(size=1,cost=100)]
    grid,summary,raw=economics_tables([run(cap=None),run(cap=3)],battery,SETTINGS)
    r=summary[(summary.battery_mwh==1)&(summary.billing_basis=="measured_peak")&
              (summary.demand_rate_cny_per_kw_month==0)].iloc[0]
    assert r.annual_cash_saving_cny == 26_500  # 365*100 savings minus 10k fixed maintenance
    assert r.annual_net_saving_cny == -73_500  # subtract capital annuity 100k
    assert r.npv_cny == -735_000
    assert r.simple_payback_years == pytest.approx(1_000_000/26_500)
    ref=summary[summary.battery_mwh==0]
    assert (ref.annual_net_saving_cny==0).all() and ref.simple_payback_years.isna().all()
    assert (ref.npv_cny==0).all()
    assert (ref.economic_eligible_runs==ref.dispatch_feasible_runs).all()
    assert len(raw)>len(battery)


def test_nonpositive_cash_saving_has_no_payback():
    _,summary,_=economics_tables([run(cap=None)], [run(size=0,cost=100),run(size=1,cost=200)], SETTINGS)
    r=summary[summary.battery_mwh==1]
    assert (r.payback_status=="no_positive_cash_saving").all()
    assert r.simple_payback_years.isna().all()


def test_one_infeasible_seed_disqualifies_economic_summary():
    battery=[run(seed=s,size=size,feasible=not(s==1 and size==1)) for s in [0,1] for size in [0,1]]
    grid,summary,raw=economics_tables([run(cap=None),run(cap=1,feasible=False)],battery,SETTINGS)
    assert not summary.loc[summary.battery_mwh==1,"eligible"].any()
    assert summary.loc[summary.battery_mwh==1,"annual_net_saving_cny"].isna().all()
    assert not grid.loc[grid.grid_limit_mw==1,"best_in_tested_sweep"].any()
    assert not raw[~raw.economics_eligible].empty


def test_grid_cost_of_cap_paired_delta_sign_and_infeasible_exclusion():
    rows=[run(seed=s,cap=None,cost=100) for s in range(3)]
    rows += [run(seed=s,cap=3,cost=120) for s in range(3)]
    rows += [run(seed=s,cap=1,cost=10,feasible=False) for s in range(3)]
    out=grid_cap_summary(rows)
    r=out[out.grid_limit_mw==3].iloc[0]
    assert r.cost_cny_delta_vs_uncapped == 20
    assert r.cost_cny_delta_ci_low == 20 and r.cost_cny_delta_ci_high == 20
    assert not out.loc[out.grid_limit_mw==1,"comparison_eligible"].any()
    assert out.loc[out.grid_limit_mw==1,"cost_cny_delta_vs_uncapped"].isna().all()


def test_economics_reference_seeds_must_match():
    with pytest.raises(ValueError,match="identical"):
        economics_tables([run(cap=None)], [run(size=0),run(seed=1,size=1)],SETTINGS)


@pytest.mark.parametrize("rate,years", [(-.1,10),(.1,0),(float("nan"),10),(.1,float("inf"))])
def test_invalid_financing_assumptions_are_rejected(rate,years):
    with pytest.raises(ValueError):capital_recovery_factor(rate,years)
