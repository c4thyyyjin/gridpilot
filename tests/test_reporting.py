import numpy as np
import pandas as pd
import pytest

import config as C
from data import make_scenario
from evaluate import Schedule, evaluate
from mpc import open_loop_schedule
from reporting import METRICS, aggregate, feasible_gain


def row(status="feasible", objective=100.0):
    r = dict.fromkeys(METRICS, 0.0)
    r.update(status=status, feasible=status == "feasible", objective=objective,
             penalized_objective=objective, cost_cny=objective)
    return r


def test_infeasible_runs_cannot_claim_savings():
    failed = row("degraded", objective=1.0)
    failed.update(unmet_job_mwh=10, penalized_objective=1_000_001)
    frame = pd.DataFrame({"baseline": aggregate([row(), row()]),
                          "MPC": aggregate([row(objective=50), failed])}).T
    assert np.isnan(feasible_gain(frame)["MPC"])
    assert frame.loc["MPC", "max_unmet_job_mwh"] == 10
    assert frame.loc["MPC", "feasible_runs"] == 1
    assert frame.loc["MPC", "degraded_runs"] == 1
    assert frame.loc["MPC", "penalized_objective"] > 100


def test_infeasible_baseline_disqualifies_all_comparisons():
    frame = pd.DataFrame({"baseline": aggregate([row("exogenous_overload")]),
                          "MPC": aggregate([row(objective=50)])}).T
    assert feasible_gain(frame).isna().all()


def test_feasible_savings_are_preserved():
    frame = pd.DataFrame({"baseline": aggregate([row()]),
                          "MPC": aggregate([row(objective=80)])}).T
    assert feasible_gain(frame)["MPC"] == pytest.approx(20)


def test_custom_limit_survives_config_changes(monkeypatch):
    sc = make_scenario()
    sch = open_loop_schedule(sc, 100, grid_limit=1.0)
    monkeypatch.setattr(C, "GRID_IMPORT_LIMIT_MW", 1000)
    result = evaluate(sc, sch)
    assert result["grid_import_limit_mw"] == 1
    assert result["grid_overflow_mwh"] > 0
    assert result["status"] == "degraded"
    overridden = evaluate(sc, sch, grid_limit=1000)
    assert overridden["grid_overflow_mwh"] == 0
    assert overridden["grid_import_limit_mw"] == 1000


def test_explicit_unlimited_overrides_metadata():
    sc = make_scenario()
    sch = Schedule.empty(len(sc.jobs), sc.T)
    sch.info["grid_import_limit_mw"] = 0
    assert evaluate(sc, sch)["grid_overflow_mwh"] > 0
    assert evaluate(sc, sch, grid_limit=None)["grid_overflow_mwh"] == 0


def test_feasibility_ranks_before_any_finite_penalty():
    sc = make_scenario()
    sch = open_loop_schedule(sc, 100, grid_limit=1)
    degraded = evaluate(sc, sch)
    feasible = evaluate(sc, open_loop_schedule(sc, 100, grid_limit=26))
    assert feasible["feasible"]
    assert not degraded["feasible"]
    assert feasible["comparison_key"] < degraded["comparison_key"]


@pytest.mark.parametrize("limit", [-1, float("nan")])
def test_invalid_evaluation_limit_is_rejected(limit):
    sc = make_scenario()
    with pytest.raises(ValueError, match="grid limit"):
        evaluate(sc, Schedule.empty(len(sc.jobs), sc.T), grid_limit=limit)
