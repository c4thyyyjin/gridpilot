"""Overload / infeasible cases: the scheduler must not crash, must not hide the failure, and degraded runs
must never look cheaper than complete ones."""
import numpy as np
import config as C
from data import make_scenario, Job
from baseline import baseline_observed
from evaluate import evaluate
from mpc import mpc_schedule, open_loop_schedule, solve_window, InfeasibleWindow, _solve

LAM, GL = 100, 26.0


def test_normal_run_is_strict_feasible_with_no_fallback():
    for s in range(3):
        sc = make_scenario(s, forecast_error=0.3)
        sch = mpc_schedule(sc, LAM, GL)
        m = evaluate(sc, sch)
        assert m["status"] == "feasible" and sch.info["fallback_hours"] == []
        assert m["unmet_job_mwh"] == 0 and m["grid_overflow_mwh"] == 0
        assert abs(m["penalized_objective"] - m["objective"]) < 1e-6


def test_impossible_job_is_reported_not_hidden():
    sc = make_scenario()
    sc.jobs = sc.jobs + [Job("X", "batch", 10, 14, 200.0, 50.0)]   # 200 MWh in 4 h needs 50 MW > 20 MW capacity
    sch = mpc_schedule(sc, LAM, GL)                                # must not raise
    m = evaluate(sc, sch)
    assert sch.info["fallback_hours"], "strict LP should have been infeasible -> fallback used and logged"
    assert m["status"] == "degraded" and m["sla_violations"] >= 1 and m["unmet_job_mwh"] > 50
    # the incomplete job must not look cheap: penalty dominates
    assert m["penalized_objective"] > m["objective"] + 0.99 * C.PEN_UNMET_CNY_PER_MWH * m["unmet_job_mwh"]
    # the open-loop planner behaves the same way
    ol = open_loop_schedule(sc, LAM, GL)
    assert ol.info["fallback_hours"] == [0] and evaluate(sc, ol)["unmet_job_mwh"] > 50


def _with_limit(limit, fn):
    old = C.GRID_IMPORT_LIMIT_MW
    C.GRID_IMPORT_LIMIT_MW = limit
    try:
        return fn()
    finally:
        C.GRID_IMPORT_LIMIT_MW = old


def test_grid_limit_is_protected_before_deadlines():
    """Documented priority: when limit and deadlines conflict, jobs are shed first (grid limit is physical)."""
    sc = make_scenario()
    sch = mpc_schedule(sc, LAM, grid_limit=5.0)
    m = _with_limit(5.0, lambda: evaluate(sc, sch))
    assert sch.info["fallback_hours"]
    assert m["grid_overflow_mwh"] == 0 and m["unmet_job_mwh"] > 0 and m["status"] == "degraded"
    assert m["penalized_objective"] > m["objective"]


def test_unavoidable_grid_overflow_is_reported():
    """A 1 MW limit cannot even cover inference at night with no green: overflow is unavoidable and must show up."""
    sc = make_scenario()
    sch = mpc_schedule(sc, LAM, grid_limit=1.0)
    m = _with_limit(1.0, lambda: evaluate(sc, sch))
    assert m["grid_overflow_mwh"] > 0 and m["status"] == "degraded"
    assert m["penalized_objective"] > m["objective"] + 0.99 * C.PEN_GRID_OVERFLOW_CNY_PER_MWH * m["grid_overflow_mwh"]


def test_inference_alone_above_capacity_is_flagged_and_jobs_get_zero_power():
    sc = make_scenario(0, forecast_error=0.3)
    sc.inference_act = sc.inference_act.copy(); sc.inference_act[30:33] = 22.0     # exceeds 20 MW IT capacity
    sch = mpc_schedule(sc, LAM, GL)                                                # must not raise
    m = evaluate(sc, sch)
    assert m["status"] == "exogenous_overload" and m["inference_overload_hours"] == 3
    assert np.allclose(sch.job_power[:, 30:33], 0.0)           # we never stack job load on top of an overload
    assert m["capacity_violation_hours"] == 3                  # only the unavoidable hours violate capacity


def test_penalized_objective_is_never_below_objective():
    sc = make_scenario(1, forecast_error=0.5)
    for sch in (baseline_observed(sc), mpc_schedule(sc, LAM, GL), open_loop_schedule(sc, LAM, GL)):
        m = evaluate(sc, sch)
        assert m["penalized_objective"] >= m["objective"] - 1e-9


def test_unbounded_models_are_not_swallowed_by_the_fallback():
    """The fallback is for INFEASIBLE windows only. A mathematically unbounded model (cheap tariff, finding #3)
    must still raise, never silently produce a schedule. (Guard bypassed here by calling the raw solver.)"""
    sc = make_scenario(); sc.price = np.full(sc.T, 0.20)       # grid cheaper than green -> unbounded green-first LP
    rem = np.array([j.energy_mwh for j in sc.jobs])
    try:
        _solve(sc, 0, LAM, rem, C.BATT_SOC_START * C.BATT_ENERGY_MWH, None, False, False, True)   # raw solver: guard bypassed
    except InfeasibleWindow:
        raise AssertionError("unbounded model was misreported as infeasible")
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected an error for an unbounded model")
