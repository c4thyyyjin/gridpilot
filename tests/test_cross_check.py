"""Compare independently assembled PuLP/CBC and SciPy/HiGHS LPs.

Perfect forecasts let evaluate() check both solver objectives against the
same physical accounting. Optimal power schedules may differ due to ties.
"""
import numpy as np
import pulp
import pytest

import config as C
from data import make_scenario
from evaluate import evaluate
from scheduler import lp_schedule
from scheduler_highs import lp_schedule_highs


@pytest.mark.parametrize("grid_limit", [None, 26.0], ids=["uncapped", "cap26"])
@pytest.mark.parametrize("seed", [0, 1, 2, 3, 42])
@pytest.mark.parametrize("lam", [0, 100, 1000])
def test_cbc_and_highs_objectives_agree(monkeypatch, seed, lam, grid_limit):
    if grid_limit is None:
        monkeypatch.delattr(C, "GRID_IMPORT_LIMIT_MW", raising=False)
    else:
        monkeypatch.setattr(C, "GRID_IMPORT_LIMIT_MW", grid_limit, raising=False)
    sc = make_scenario(seed=seed, forecast_error=0)
    cbc_objectives = []
    original_solve = pulp.LpProblem.solve

    def capture_objective(model, *args, **kwargs):
        status = original_solve(model, *args, **kwargs)
        assert status == pulp.LpStatusOptimal
        cbc_objectives.append(pulp.value(model.objective))
        return status

    monkeypatch.setattr(pulp.LpProblem, "solve", capture_objective)
    cbc_schedule = lp_schedule(sc, lam)
    highs_schedule, highs_objective = lp_schedule_highs(sc, lam, return_obj=True)
    assert len(cbc_objectives) == 1
    cbc_objective = cbc_objectives[0]
    assert np.isfinite(cbc_objective) and np.isfinite(highs_objective)
    # 0.1% relative tolerance, with a tiny floor for an objective near zero.
    assert cbc_objective == pytest.approx(highs_objective, rel=0.001, abs=1e-6)

    for schedule, objective in ((cbc_schedule, cbc_objective),
                                (highs_schedule, highs_objective)):
        metrics = evaluate(sc, schedule, lam)
        assert metrics["sla_violations"] == 0
        assert metrics["capacity_violation_hours"] == 0
        assert not metrics["battery_violation"]
        assert metrics["grid_limit_violation_hours"] == 0
        if grid_limit is not None:
            assert metrics["peak_grid_mw"] <= grid_limit + 1e-4
        assert metrics["objective"] == pytest.approx(objective, rel=1e-7, abs=0.01)
        for k, job in enumerate(sc.jobs):
            assert schedule.job_power[k].sum() * C.DT_H == pytest.approx(
                job.energy_mwh, rel=0, abs=1e-4)
