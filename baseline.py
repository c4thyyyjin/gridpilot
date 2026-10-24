"""Baseline 'no scheduling': jobs run as soon as released, earliest-deadline-first when IT capacity is short.
No battery. This is what a data center does without any power-aware logic."""
import numpy as np
import config as C
from evaluate import Schedule, evaluate, summary
from data import make_scenario


def _baseline(sc, observed) -> Schedule:
    """observed=False: capacity is planned on the FORECAST inference load ("forecast-planned baseline").
    observed=True : capacity is allocated each hour from the ACTUAL inference load that hour, i.e. the same
                    information the MPC scheduler has at hour t ("observed-demand baseline", the fair comparison).
    Both run jobs ASAP, earliest-deadline-first, with no battery and no look-ahead."""
    n, T = len(sc.jobs), sc.T
    sch = Schedule.empty(n, T)
    remaining = np.array([j.energy_mwh for j in sc.jobs])
    for t in range(T):
        inf_t = sc.inference_act[t] if observed else sc.inference_fc[t]
        spare = max(C.IT_CAPACITY_MW - inf_t, 0.0)
        active = [k for k, j in enumerate(sc.jobs) if j.release <= t < j.deadline and remaining[k] > 1e-9]
        for k in sorted(active, key=lambda k: sc.jobs[k].deadline):
            p = min(sc.jobs[k].max_power_mw, remaining[k] / C.DT_H, spare)
            sch.job_power[k, t] = p
            remaining[k] -= p * C.DT_H
            spare -= p
    return sch


def baseline_observed(sc) -> Schedule:
    """THE baseline for all main comparisons: same information as the MPC scheduler (sees actual load each hour)."""
    return _baseline(sc, observed=True)


def baseline_forecast_planned(sc) -> Schedule:
    """Weaker reference: plans capacity on forecast inference, so it can exceed capacity when forecasts are wrong.
    Reported only as a secondary row; never use it as the main comparison."""
    return _baseline(sc, observed=False)


baseline_schedule = baseline_observed   # backwards-compatible name -> the fair baseline (no silent weak default)


if __name__ == "__main__":
    sc = make_scenario()
    m = evaluate(sc, baseline_observed(sc))
    print(f"Scenario: seed={sc.seed}, {len(sc.jobs)} jobs, T={sc.T} h")
    print(f"Mean facility load      : {m['load_mwh']/sc.T:6.1f} MW")
    print(f"Mean green supply       : {sc.green_act.mean():6.1f} MW")
    for k, v in summary(m).items():
        print(f"{k:26s}: {v:,.2f}" if isinstance(v, float) else f"{k:26s}: {v}")
