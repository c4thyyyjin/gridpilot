"""Tests for laxity-aware deadline scheduling improvements.

Covers: causality preservation, least-laxity ordering, required-power floors,
ramp-aware deliverable energy, EDF/MPC feasibility agreement, and regression
on the 19 oracle-feasible cases from seeds 200–219.
"""
import copy
import numpy as np
import pytest
from data import Job, make_scenario
from evaluate import evaluate
from robustness import (Policy, causal_mpc_schedule, causal_edf_schedule,
                        service_power, max_deliverable_energy, job_laxity,
                        required_power_floor, POLICIES)
from robustness_experiments import PROFILES
import config as C
from test_robustness import toy


# --- Unit tests for helper functions -----------------------------------------

def test_max_deliverable_no_ramp_is_full_window():
    j = Job("a", "training", 2, 10, 40., 5.)
    policy = Policy()
    assert max_deliverable_energy(j, 2, 0., policy) == pytest.approx(8 * 5 * 1.0)


def test_max_deliverable_respects_ramp_up_and_down():
    j = Job("a", "training", 0, 4, 100., 10.)
    policy = Policy(ramp_mw_per_hour=2.)
    # With step=2: max trajectory is [2, 4, 4, 2] = 12 MW*h
    result = max_deliverable_energy(j, 0, 0., policy)
    assert result == pytest.approx(12.)


def test_max_deliverable_from_nonzero_previous():
    j = Job("a", "training", 0, 4, 100., 10.)
    policy = Policy(ramp_mw_per_hour=2.)
    # From previous=4: up profile [6,8,10,2] capped by down [8,6,4,2] -> [6,6,4,2]=18
    result = max_deliverable_energy(j, 0, 4., policy)
    assert result == pytest.approx(18.)


def test_max_deliverable_past_deadline_is_zero():
    j = Job("a", "training", 0, 5, 10., 5.)
    assert max_deliverable_energy(j, 5, 0., Policy()) == 0.0
    assert max_deliverable_energy(j, 10, 0., Policy()) == 0.0


def test_laxity_positive_for_easy_job():
    j = Job("a", "training", 0, 10, 5., 5.)
    assert job_laxity(j, 0, 5., 0., Policy()) > 0


def test_laxity_negative_for_impossible_job():
    j = Job("a", "training", 0, 2, 50., 5.)
    assert job_laxity(j, 0, 50., 0., Policy()) < 0


def test_required_floor_is_zero_when_done():
    j = Job("a", "training", 0, 10, 5., 5.)
    assert required_power_floor(j, 5, 0., 0., Policy(), 5.) == pytest.approx(0.)


def test_required_floor_exact_for_tight_job():
    """A job that exactly fills its window needs its max power every hour."""
    j = Job("a", "training", 0, 5, 25., 5.)
    assert required_power_floor(j, 0, 25., 0., Policy(), 5.) == pytest.approx(5.)


def test_required_floor_with_ramp():
    j = Job("a", "training", 0, 3, 6., 10.)
    policy = Policy(ramp_mw_per_hour=2.)
    # step=2, slots=3; max profile [p, p+2, 2] for some p, capped by down [6,4,2]
    # deliverable(p) = p + min(p+2,4) + 2
    # Need: 6 MWh at eff=1 -> 6 MW*h of power
    # If p=0: deliver 0+2+2=4 < 6; if p=2: deliver 2+4+2=8 >= 6
    # By bisection: ~1.0 floor
    floor = required_power_floor(j, 0, 6., 0., policy, 10.)
    assert floor >= 0.5
    assert floor <= 2.5


# --- Causality tests ---------------------------------------------------------

def test_laxity_dispatch_preserves_causality():
    """Future actuals and unannounced jobs cannot change earlier decisions."""
    sc = toy(); other = copy.deepcopy(sc)
    other.inference_act[3:] = 19; other.solar_act[3:] = 100
    other.jobs[1].energy_mwh = 1000
    policy = Policy(observation_delay_h=1, advance_job_knowledge=False,
                    service_guard=True, fast_safety=True)
    a = causal_mpc_schedule(sc, 100, 26, policy)
    b = causal_mpc_schedule(other, 100, 26, policy)
    np.testing.assert_allclose(a.job_power[:, :3], b.job_power[:, :3], atol=1e-7)
    np.testing.assert_allclose(a.charge[:3], b.charge[:3], atol=1e-7)
    assert a.info["decision_trace"][:3] == b.info["decision_trace"][:3]


def test_laxity_edf_preserves_causality():
    """Same causality check on EDF reference."""
    sc = toy(); other = copy.deepcopy(sc)
    other.inference_act[3:] = 19
    other.jobs[1].energy_mwh = 1000
    policy = Policy(advance_job_knowledge=False, service_guard=True, fast_safety=True)
    a = causal_edf_schedule(sc, 26, policy)
    b = causal_edf_schedule(other, 26, policy)
    np.testing.assert_allclose(a.job_power[:, :3], b.job_power[:, :3], atol=1e-7)


# --- Service behaviour tests ------------------------------------------------

def test_tight_job_gets_power_alongside_slack_job():
    """A job with low laxity is not starved by a job with an earlier deadline
    that has plenty of slack and remaining capacity."""
    sc = toy()
    # "slack": early deadline but small energy -> lots of laxity
    # "tight": later deadline but needs almost all its window to finish
    sc.jobs = [Job("slack", "batch", 0, 4, 2., 4.),
               Job("tight", "training", 0, 6, 30., 5.)]
    policy = Policy(service_guard=True, fast_safety=True)
    sch = causal_mpc_schedule(sc, 100, 26, policy)
    m = evaluate(sc, sch)
    assert m["feasible"]
    # "tight" should receive substantial power in the first few hours
    assert sch.job_power[1, 0] >= 4.0 - 1e-6


def test_mpc_edf_feasibility_agreement():
    """MPC and EDF must agree on feasibility when using same service policy."""
    sc = toy()
    sc.jobs = [Job("a", "training", 0, 4, 12., 4.),
               Job("b", "batch", 1, 6, 15., 5.)]
    policy = Policy(advance_job_knowledge=False, service_guard=True, fast_safety=True)
    sch_m = causal_mpc_schedule(sc, 100, 26, policy)
    sch_e = causal_edf_schedule(sc, 26, policy)
    m = evaluate(sc, sch_m, work_efficiency=policy.efficiency)
    e = evaluate(sc, sch_e, work_efficiency=policy.efficiency)
    assert m["feasible"] == e["feasible"]


def test_ramp_constrained_floor_prevents_last_minute_shortfall():
    """Under ramp limits, jobs get enough power to keep a ramp-feasible finish
    trajectory alive, rather than being deferred until too late."""
    sc = toy()
    sc.jobs = [Job("urgent", "training", 0, 6, 10., 5.),
               Job("needy", "training", 0, 6, 18., 4.)]
    policy = Policy(ramp_mw_per_hour=2., service_guard=True, fast_safety=True)
    sch = causal_mpc_schedule(sc, 100, 26, policy)
    m = evaluate(sc, sch, work_efficiency=policy.efficiency, ramp_mw_per_hour=2.)
    # Both should complete without deadline violations
    assert m["unmet_job_mwh"] < 0.01


# --- Regression on oracle-feasible cases from seeds 200–219 ------------------

ORACLE_FEASIBLE_CASES = [
    ("typical", "guarded_combined", 202),
    ("low_green", "guarded_combined", 202),
    ("high_inference", "guarded_online", 201),
    ("high_inference", "guarded_online", 202),
    ("high_inference", "guarded_online", 206),
    ("high_inference", "guarded_online", 209),
    ("high_inference", "guarded_delayed", 201),
    ("high_inference", "guarded_delayed", 202),
    ("high_inference", "guarded_delayed", 206),
    ("high_inference", "guarded_delayed", 209),
    ("high_inference", "guarded_combined", 200),
    ("high_inference", "guarded_combined", 201),
    ("high_inference", "guarded_combined", 203),
    ("high_inference", "guarded_combined", 204),
    ("high_inference", "guarded_combined", 205),
    ("high_inference", "guarded_combined", 206),
    ("high_inference", "guarded_combined", 209),
    ("high_inference", "guarded_combined", 210),
    ("high_inference", "guarded_combined", 219),
]


@pytest.mark.parametrize("profile,policy_name,seed", ORACLE_FEASIBLE_CASES)
def test_oracle_feasible_case_now_passes(profile, policy_name, seed):
    """Every case that the oracle proves feasible is now served successfully."""
    sc = make_scenario(seed, forecast_error=.3, screen_feasibility=False)
    solar, wind, inference = PROFILES[profile]
    sc.solar_fc *= solar; sc.solar_act *= solar
    sc.wind_fc *= wind; sc.wind_act *= wind
    sc.inference_fc *= inference; sc.inference_act *= inference
    policy = POLICIES[policy_name]
    for method, fn in (("MPC", lambda: causal_mpc_schedule(sc, C.LAMBDA_DEFAULT,
                                                           C.GRID_IMPORT_LIMIT_MW, policy)),
                       ("EDF", lambda: causal_edf_schedule(sc, C.GRID_IMPORT_LIMIT_MW, policy))):
        sch = fn()
        m = evaluate(sc, sch, C.LAMBDA_DEFAULT,
                     work_efficiency=policy.efficiency,
                     ramp_mw_per_hour=policy.ramp_mw_per_hour)
        assert m["feasible"], (f"{method} {profile}/{policy_name}/seed={seed}: "
                               f"unmet={m['unmet_job_mwh']:.3f}, status={m['status']}")


# --- Oracle-infeasible cases stay failed (no false claims) -------------------

ORACLE_INFEASIBLE_CASES = [
    ("typical", "guarded_combined", 208),
    ("typical", "guarded_combined", 214),
    ("low_green", "guarded_combined", 208),
    ("low_green", "guarded_combined", 214),
    ("high_inference", "guarded_combined", 202),
    ("high_inference", "guarded_combined", 208),
    ("high_inference", "guarded_combined", 214),
]


@pytest.mark.parametrize("profile,policy_name,seed", ORACLE_INFEASIBLE_CASES)
def test_oracle_infeasible_case_stays_failed(profile, policy_name, seed):
    """Cases infeasible even with future knowledge must remain failed."""
    sc = make_scenario(seed, forecast_error=.3, screen_feasibility=False)
    solar, wind, inference = PROFILES[profile]
    sc.solar_fc *= solar; sc.solar_act *= solar
    sc.wind_fc *= wind; sc.wind_act *= wind
    sc.inference_fc *= inference; sc.inference_act *= inference
    policy = POLICIES[policy_name]
    sch = causal_mpc_schedule(sc, C.LAMBDA_DEFAULT, C.GRID_IMPORT_LIMIT_MW, policy)
    m = evaluate(sc, sch, C.LAMBDA_DEFAULT,
                 work_efficiency=policy.efficiency,
                 ramp_mw_per_hour=policy.ramp_mw_per_hour)
    assert not m["feasible"]
