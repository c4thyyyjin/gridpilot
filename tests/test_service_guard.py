"""Regression checks for explicit current-telemetry execution and EDF service."""
import copy
import numpy as np
import pytest
from data import Job
from evaluate import evaluate
from mpc import solve_window
from robustness import Policy, causal_mpc_schedule, causal_edf_schedule, service_power
from test_robustness import toy


def test_guard_services_available_work_even_when_later_energy_is_cheaper():
    sc=toy();sc.price[:]=.4;sc.price[0]=1.
    policy=Policy(advance_job_knowledge=False,service_guard=True,fast_safety=True)
    sch=causal_mpc_schedule(sc,100,26,policy)
    assert sch.job_power[0,0]==pytest.approx(4)
    assert evaluate(sc,sch)["feasible"]


def test_delayed_optimizer_and_current_safety_have_separate_observation_cutoffs():
    sc=toy();sc.inference_act[0]=19
    policy=Policy(observation_delay_h=1,advance_job_knowledge=False,service_guard=True,fast_safety=True)
    for fn in (lambda:causal_mpc_schedule(sc,100,26,policy),lambda:causal_edf_schedule(sc,26,policy)):
        sch=fn();trace=sch.info["decision_trace"][0]
        assert trace["observed_through"]==-1
        assert trace["safety_observed_through"]==0
        assert trace["inference_estimate"]==4
        assert sch.job_power[:,0].sum()<=1+1e-7
        assert evaluate(sc,sch)["capacity_violation_hours"]==0


def test_safety_cannot_read_future_actuals_or_unannounced_jobs():
    sc=toy();other=copy.deepcopy(sc)
    other.inference_act[3:]=19;other.solar_act[3:]=100
    other.jobs[1].energy_mwh=1000
    policy=Policy(observation_delay_h=1,advance_job_knowledge=False,service_guard=True,fast_safety=True)
    a=causal_mpc_schedule(sc,100,26,policy);b=causal_mpc_schedule(other,100,26,policy)
    np.testing.assert_allclose(a.job_power[:,:3],b.job_power[:,:3],atol=1e-7)
    np.testing.assert_allclose(a.charge[:3],b.charge[:3],atol=1e-7)
    assert a.info["decision_trace"][:3]==b.info["decision_trace"][:3]


def test_ramp_down_power_reserved_before_higher_priority_new_work():
    sc=toy();sc.jobs=[Job("new","batch",1,3,4,4),Job("running","training",0,6,10,4)]
    policy=Policy(ramp_mw_per_hour=1)
    power=service_power(sc,1,np.array([4.,10.]),np.array([0.,3.]),17.,policy)
    assert power[1]>=2-1e-7
    assert power.sum()<=3+1e-7
    assert power[0]<=1+1e-7


def test_fixed_current_service_survives_infeasible_future_fallback():
    sc=toy();sc.jobs=[Job("impossible","batch",0,1,10,4)]
    jp,_,_,_,fallback=solve_window(sc,0,100,np.array([10.]),10.,26,current_power=np.array([2.]))
    assert fallback
    assert jp[0,0]==pytest.approx(2)


def test_impossible_job_is_still_reported_by_guard():
    sc=toy();sc.jobs=[Job("impossible","batch",0,1,10,4)]
    sch=causal_mpc_schedule(sc,100,26,Policy(service_guard=True,fast_safety=True))
    assert not evaluate(sc,sch)["feasible"]
    assert evaluate(sc,sch)["unmet_job_mwh"]>=6-1e-6
