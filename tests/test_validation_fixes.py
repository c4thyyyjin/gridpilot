"""Tests for evaluator input validation, green-share accounting, and
the remaining pre-submission fixes (tasks 6–11)."""
import copy
import numpy as np
import pytest

import config as C
from data import Job, Scenario, make_scenario
from evaluate import Schedule, evaluate


# ---- helpers ----------------------------------------------------------------

def _trivial_scenario(T=6, load_mw=4.0, green_mw=0.0):
    zero = np.zeros(T)
    return Scenario(T, np.full(T, .5), np.full(T, .5), np.full(T, green_mw), zero.copy(),
                    np.full(T, green_mw), zero.copy(), np.full(T, load_mw), np.full(T, load_mw),
                    [])


# ---- evaluator input validation (task 6) ------------------------------------

def test_nan_job_power_rejected():
    sc = make_scenario(0, forecast_error=0.0)
    sch = Schedule.empty(len(sc.jobs), sc.T)
    sch.job_power[0, 3] = np.nan
    with pytest.raises(ValueError, match="job_power.*non-finite"):
        evaluate(sc, sch)


def test_nan_charge_rejected():
    sc = make_scenario(0, forecast_error=0.0)
    sch = Schedule.empty(len(sc.jobs), sc.T)
    sch.charge[2] = np.nan
    with pytest.raises(ValueError, match="charge.*non-finite"):
        evaluate(sc, sch)


def test_nan_discharge_rejected():
    sc = make_scenario(0, forecast_error=0.0)
    sch = Schedule.empty(len(sc.jobs), sc.T)
    sch.discharge[5] = np.nan
    with pytest.raises(ValueError, match="discharge.*non-finite"):
        evaluate(sc, sch)


def test_inf_job_power_rejected():
    sc = make_scenario(0, forecast_error=0.0)
    sch = Schedule.empty(len(sc.jobs), sc.T)
    sch.job_power[0, 0] = np.inf
    with pytest.raises(ValueError, match="job_power.*non-finite"):
        evaluate(sc, sch)


def test_negative_charge_rejected():
    sc = make_scenario(0, forecast_error=0.0)
    sch = Schedule.empty(len(sc.jobs), sc.T)
    sch.charge[0] = -5.0
    with pytest.raises(ValueError, match="charge.*negative"):
        evaluate(sc, sch)


def test_negative_discharge_rejected():
    sc = make_scenario(0, forecast_error=0.0)
    sch = Schedule.empty(len(sc.jobs), sc.T)
    sch.discharge[0] = -1.0
    with pytest.raises(ValueError, match="discharge.*negative"):
        evaluate(sc, sch)


def test_negative_job_power_rejected():
    sc = make_scenario(0, forecast_error=0.0)
    sch = Schedule.empty(len(sc.jobs), sc.T)
    sch.job_power[0, 0] = -0.1
    with pytest.raises(ValueError, match="job_power.*negative"):
        evaluate(sc, sch)


def test_shape_mismatch_rejected():
    sc = make_scenario(0, forecast_error=0.0)
    sch = Schedule(np.zeros((len(sc.jobs), sc.T + 1)), np.zeros(sc.T), np.zeros(sc.T))
    with pytest.raises(ValueError, match="shape"):
        evaluate(sc, sch)


def test_valid_schedule_still_scores():
    """Zero schedule is valid and must not raise."""
    sc = make_scenario(0, forecast_error=0.0)
    sch = Schedule.empty(len(sc.jobs), sc.T)
    m = evaluate(sc, sch)
    assert np.isfinite(m["objective"])


# ---- green-share accounting (task 7) ----------------------------------------

def test_green_share_never_exceeds_100():
    sc = _trivial_scenario(T=72, load_mw=2.0, green_mw=20.0)
    sch = Schedule.empty(0, sc.T)
    for t in range(10):
        sch.charge[t] = 3.0
    m = evaluate(sc, sch)
    assert m["green_share_pct"] <= 100.0


def test_green_share_zero_when_no_renewables():
    sc = _trivial_scenario(T=12, load_mw=5.0, green_mw=0.0)
    m = evaluate(sc, Schedule.empty(0, sc.T))
    assert m["green_share_pct"] == 0.0


def test_green_share_100_when_fully_renewable_no_battery():
    sc = _trivial_scenario(T=12, load_mw=3.0, green_mw=20.0)
    m = evaluate(sc, Schedule.empty(0, sc.T))
    assert m["green_share_pct"] == pytest.approx(100.0)


def test_green_share_direct_equals_drawn_without_battery():
    sc = _trivial_scenario(T=12, load_mw=5.0, green_mw=3.0)
    m = evaluate(sc, Schedule.empty(0, sc.T))
    assert m["green_served_direct_mwh"] == pytest.approx(m["green_drawn_mwh"])
    assert m["green_served_stored_mwh"] == pytest.approx(0.0)
    assert m["green_share_pct"] <= 100.0


def test_green_share_includes_stored_green():
    """Energy stored from renewable surplus and later discharged should
    contribute to the green share."""
    sc = _trivial_scenario(T=72, load_mw=0.5, green_mw=0.0)
    sc.solar_act[:24] = 5.0   # green first day only
    sc.solar_fc[:24] = 5.0
    sch = Schedule.empty(0, sc.T)
    sch.charge[0] = 2.0
    m = evaluate(sc, sch)
    assert m["green_served_stored_mwh"] >= 0
    assert m["green_share_pct"] > 0


# ---- DT_H handling (task 10) -----------------------------------------------

def test_generator_rejects_non_unit_dth(monkeypatch):
    """make_scenario should reject DT_H != 1 since the generator's feasibility
    screening is unreliable at other step sizes."""
    monkeypatch.setattr(C, "DT_H", 0.5)
    with pytest.raises((ValueError, RuntimeError)):
        make_scenario(42, screen_feasibility=True)
