import numpy as np
import config as C
from data import make_scenario
from baseline import baseline_observed
from evaluate import evaluate
from scheduler_highs import lp_schedule_highs
from mpc import open_loop_schedule, mpc_schedule

LAM, GL = 100, 26.0


def test_window_lp_matches_verified_lp_without_cap(monkeypatch):
    monkeypatch.delattr(C, "GRID_IMPORT_LIMIT_MW", raising=False)
    sc = make_scenario()
    a = evaluate(sc, lp_schedule_highs(sc, LAM))["objective"]
    b = evaluate(sc, open_loop_schedule(sc, LAM))["objective"]
    assert abs(a - b) / a < 1e-6


def test_mpc_equals_open_loop_with_perfect_forecast():
    sc = make_scenario(forecast_error=0.0)
    a = evaluate(sc, open_loop_schedule(sc, LAM, GL))["objective"]
    b = evaluate(sc, mpc_schedule(sc, LAM, GL))["objective"]
    assert abs(a - b) / a < 1e-6


def test_grid_limit_is_respected_when_forecast_is_perfect():
    sc = make_scenario()
    m = evaluate(sc, open_loop_schedule(sc, LAM, GL))
    assert m["peak_grid_mw"] <= GL + 1e-6 and m["grid_limit_violation_hours"] == 0


def test_mpc_keeps_all_hard_limits_under_forecast_error():
    for s in range(3):
        sc = make_scenario(s, forecast_error=0.5)
        m = evaluate(sc, mpc_schedule(sc, LAM, GL))
        assert m["sla_violations"] == 0 and m["capacity_violation_hours"] == 0 and not m["battery_violation"]


def test_oracle_is_lower_bound_and_mpc_close_to_it():
    sc = make_scenario(0, forecast_error=0.3)
    orc = evaluate(sc, open_loop_schedule(sc, LAM, GL, use_forecast=False))["objective"]
    mpc = evaluate(sc, mpc_schedule(sc, LAM, GL))["objective"]
    assert orc <= mpc + 1e-6 and mpc <= orc * 1.03


def test_mpc_beats_baseline_under_forecast_error():
    for s in range(3):
        sc = make_scenario(s, forecast_error=0.3)
        base = evaluate(sc, baseline_observed(sc))["objective"]   # the fair baseline
        assert evaluate(sc, mpc_schedule(sc, LAM, GL))["objective"] < 0.9 * base
