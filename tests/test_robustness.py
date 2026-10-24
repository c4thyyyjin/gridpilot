import copy
import numpy as np
import pytest

import config as C
from data import Job, Scenario, make_scenario
from evaluate import Schedule,evaluate
from mpc import mpc_schedule
from robustness import Policy,available_estimates,causal_mpc_schedule,causal_edf_schedule


def toy():
    T=6
    zero=np.zeros(T)
    return Scenario(T,np.array([.4,.6,.8,.4,.8,.6]),np.full(T,.5),zero.copy(),zero.copy(),
                    zero.copy(),zero.copy(),np.full(T,4.),np.full(T,4.),
                    [Job("a","training",0,4,4.,4.),Job("future","batch",3,6,3.,3.)])


def test_default_variant_matches_original_mpc():
    sc=toy()
    a=mpc_schedule(sc,100,26);b=causal_mpc_schedule(sc,100,26)
    np.testing.assert_allclose(a.job_power,b.job_power,atol=1e-7)
    np.testing.assert_allclose(a.charge,b.charge,atol=1e-7)
    assert evaluate(sc,a)["objective"]==pytest.approx(evaluate(sc,b)["objective"])


def test_delay_never_reads_current_or_future_actual_values():
    sc=toy();other=copy.deepcopy(sc)
    other.inference_act[2:]=19;other.solar_act[2:]=100
    policy=Policy(observation_delay_h=1,advance_job_knowledge=False)
    a=causal_mpc_schedule(sc,100,26,policy);b=causal_mpc_schedule(other,100,26,policy)
    np.testing.assert_allclose(a.job_power[:,:3],b.job_power[:,:3],atol=1e-7)
    np.testing.assert_allclose(a.charge[:3],b.charge[:3],atol=1e-7)
    assert a.info["decision_trace"][2]["observed_through"]==1


def test_unannounced_job_cannot_change_earlier_decisions():
    sc=toy();other=copy.deepcopy(sc);other.jobs[1].energy_mwh=1000
    policy=Policy(advance_job_knowledge=False)
    a=causal_mpc_schedule(sc,100,26,policy);b=causal_mpc_schedule(other,100,26,policy)
    np.testing.assert_allclose(a.job_power[:,:3],b.job_power[:,:3],atol=1e-7)
    np.testing.assert_allclose(a.charge[:3],b.charge[:3],atol=1e-7)
    assert "future" not in a.info["decision_trace"][2]["visible_job_ids"]
    assert "future" in a.info["decision_trace"][3]["visible_job_ids"]


def test_checkpoint_overhead_consumes_energy_not_useful_work():
    sc=toy();policy=Policy(checkpoint_overhead_fraction=.1)
    sch=causal_mpc_schedule(sc,100,26,policy);m=evaluate(sc,sch)
    assert m["feasible"]
    assert sch.job_power.sum()*C.DT_H==pytest.approx(7/.9)
    assert m["compute_overhead_mwh"]==pytest.approx(7/.9-7)
    manual=Schedule.empty(2,6);manual.job_power[0,0]=4;manual.job_power[1,3]=3
    m=evaluate(sc,manual,work_efficiency=.9)
    assert m["unmet_job_mwh"]==pytest.approx(.7)
    assert m["sla_violations"]==2


def test_ramp_limits_include_launch_and_shutdown():
    sc=toy();policy=Policy(ramp_mw_per_hour=1.)
    for fn in (lambda:causal_mpc_schedule(sc,100,26,policy),lambda:causal_edf_schedule(sc,26,policy)):
        sch=fn();m=evaluate(sc,sch)
        assert m["ramp_violation_events"]==0
        assert np.max(np.abs(np.diff(np.pad(sch.job_power,((0,0),(1,1))),axis=1)))<=1+1e-6


def test_conflicting_ramp_and_service_constraints_are_reported():
    sc=toy();sc.jobs=[Job("impossible","batch",0,1,4.,4.)]
    sch=causal_mpc_schedule(sc,100,26,Policy(ramp_mw_per_hour=.1))
    m=evaluate(sc,sch)
    assert sch.info["fallback_hours"]
    assert not m["feasible"]
    assert m["unmet_job_mwh"]>0 or m["ramp_violation_events"]>0
    assert m["penalized_objective"]>m["objective"]


def test_delayed_plan_does_not_secretly_use_actual_for_protection():
    sc=toy();sc.inference_act[0]=22
    sch=causal_mpc_schedule(sc,100,26,Policy(observation_delay_h=1))
    assert sch.info["decision_trace"][0]["inference_estimate"]==4
    assert evaluate(sc,sch)["status"]=="exogenous_overload"


def test_unscreened_scenarios_keep_first_draw_and_record_policy():
    a=make_scenario(100,forecast_error=.3,screen_feasibility=False)
    b=make_scenario(100,forecast_error=.3,screen_feasibility=False)
    assert a.generation_attempts==1 and not a.generation_screened
    np.testing.assert_array_equal(a.inference_act,b.inference_act)


@pytest.mark.parametrize("kwargs",[dict(observation_delay_h=-1),dict(observation_delay_h=.5),
                                    dict(checkpoint_overhead_fraction=1),dict(ramp_mw_per_hour=0)])
def test_invalid_assumptions_rejected(kwargs):
    with pytest.raises(ValueError):Policy(**kwargs)


def test_observation_delay_is_in_hours_with_subhourly_steps(monkeypatch):
    sc=toy();sc.inference_act[0]=10
    monkeypatch.setattr(C,"DT_H",.5)
    assert available_estimates(sc,1,1)[3]==-1
    assert available_estimates(sc,1,1)[0]==4
    assert available_estimates(sc,2,1)[3]==0
    assert available_estimates(sc,2,1)[0]==10


def test_evaluator_penalizes_ramp_violations_without_hiding_completed_work():
    sc=toy();sc.jobs=[Job("a","training",0,1,4.,4.)]
    sch=Schedule.empty(1,6);sch.job_power[0,0]=4
    m=evaluate(sc,sch,ramp_mw_per_hour=1)
    assert m["sla_violations"]==0
    assert m["ramp_violation_events"]==2
    assert m["ramp_excess_mwh"]==6
    assert m["status"]=="degraded"
    assert m["penalized_objective"]==pytest.approx(m["objective"]+6*C.PEN_RAMP_CNY_PER_MWH)


def test_relaxed_solver_ramp_penalty_matches_evaluator(monkeypatch):
    from mpc import solve_window
    sc=toy();sc.jobs=[Job("a","training",0,1,4.,4.)]
    monkeypatch.setattr(C,"PEN_RAMP_CNY_PER_MWH",1.)
    jp,ch,dis,obj,fallback=solve_window(sc,0,100,np.array([4.]),
                                       C.BATT_SOC_START*C.BATT_ENERGY_MWH,26,
                                       ramp_mw_per_hour=.1)
    m=evaluate(sc,Schedule(jp,ch,dis),100,ramp_mw_per_hour=.1)
    assert fallback and m["ramp_violation_events"]>0
    assert obj==pytest.approx(m["penalized_objective"],abs=.01)
