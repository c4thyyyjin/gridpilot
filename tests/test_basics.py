import numpy as np
import config as C
from data import make_scenario, check_feasible
from evaluate import Schedule, evaluate
from baseline import baseline_observed, baseline_forecast_planned


def test_scenario_is_reproducible():
    a, b = make_scenario(1), make_scenario(1)
    assert np.allclose(a.solar_fc, b.solar_fc) and [j.energy_mwh for j in a.jobs] == [j.energy_mwh for j in b.jobs]


def test_scenario_feasible_for_many_seeds():
    for s in range(10):
        assert check_feasible(make_scenario(s))


def test_workload_shares_match_assumptions():
    sc = make_scenario()
    tr = sum(j.energy_mwh for j in sc.jobs if j.kind == "training")
    ba = sum(j.energy_mwh for j in sc.jobs if j.kind == "batch")
    inf = sc.inference_fc.sum()
    tot = tr + ba + inf
    assert abs(inf / tot - C.SHARE_INFERENCE) < 0.01
    assert abs(tr / tot - C.SHARE_TRAINING) < 0.01
    assert abs(ba / tot - C.SHARE_BATCH) < 0.01


def test_baseline_meets_all_deadlines():
    sc = make_scenario()
    m = evaluate(sc, baseline_observed(sc))
    assert m["sla_violations"] == 0 and m["capacity_violation_hours"] == 0


def test_hand_computed_cost_and_co2():
    """No jobs, no inference, no green: cost/CO2 must equal a hand calculation."""
    sc = make_scenario()
    sc.jobs = []
    sc.inference_act = np.full(sc.T, 10.0 / C.PUE)       # facility load = 10 MW
    sc.solar_act = np.zeros(sc.T); sc.wind_act = np.zeros(sc.T)
    m = evaluate(sc, Schedule.empty(0, sc.T))
    assert np.isclose(m["cost_cny"], (10 * sc.price * 1000).sum())
    assert np.isclose(m["co2_t"], (10 * sc.grid_co2).sum())
    assert m["green_share_pct"] == 0


def test_green_used_first_and_curtailed():
    sc = make_scenario()
    sc.jobs = []
    sc.inference_act = np.full(sc.T, 5.0 / C.PUE)        # 5 MW load
    sc.solar_act = np.full(sc.T, 8.0); sc.wind_act = np.zeros(sc.T)
    m = evaluate(sc, Schedule.empty(0, sc.T))
    assert m["grid_mwh"] == 0 and np.isclose(m["curtailed_mwh"], 3.0 * sc.T)


def test_battery_energy_conservation_and_violation_flag():
    sc = make_scenario(); sc.jobs = []
    sch = Schedule.empty(0, sc.T)
    sch.charge[0] = 5.0                                  # charge but never discharge -> end SoC != start
    assert evaluate(sc, sch)["battery_violation"]
    sch.discharge[1] = 5.0 * C.BATT_EFF_CHARGE * C.BATT_EFF_DISCHARGE   # exactly returns the stored energy
    assert not evaluate(sc, sch)["battery_violation"]
    over = Schedule.empty(0, sc.T); over.charge[0] = C.BATT_POWER_MW     # 10 -> 19.5 MWh > 95 % cap
    assert evaluate(sc, over)["battery_violation"]


def test_missing_a_job_is_flagged():
    sc = make_scenario()
    sch = baseline_observed(sc)
    sch.job_power[0, :] = 0
    assert evaluate(sc, sch)["sla_violations"] >= 1


def test_observed_baseline_equals_forecast_baseline_without_error():
    sc = make_scenario(forecast_error=0.0)
    assert np.allclose(baseline_observed(sc).job_power, baseline_forecast_planned(sc).job_power)


def test_observed_baseline_never_exceeds_capacity_under_forecast_error():
    for s in range(5):
        sc = make_scenario(s, forecast_error=0.6)
        m = evaluate(sc, baseline_observed(sc))
        assert m["capacity_violation_hours"] == 0
        assert evaluate(sc, baseline_forecast_planned(sc))["capacity_violation_hours"] > 0   # the weak one did violate


def test_experiments_use_the_fair_baseline_for_main_comparison():
    """Guard: experiments.py must route 'baseline' to baseline_observed; the forecast-planned one only as 'baseline-fc'."""
    import re
    src = open("experiments.py").read()
    assert 'if method == "baseline": return baseline_observed(sc)' in src
    uses = [l for l in src.splitlines() if "baseline_forecast_planned(" in l and "import" not in l]
    assert len(uses) == 1 and '"baseline-fc"' in uses[0]
    assert "baseline_schedule" not in src
