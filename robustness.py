"""Information-limited MPC and no-battery variants; original defaults unchanged.

Checkpoint overhead is an amortized fraction of consumed compute energy, not a
measured per-pause model. Ramp relaxation is an explicitly reported emergency
fallback when physical/job constraints conflict. Compute remains continuous.
"""
from dataclasses import dataclass, asdict
import copy
import numpy as np

import config as C
from evaluate import Schedule
from mpc import solve_window


@dataclass(frozen=True)
class Policy:
    observation_delay_h: int = 0
    advance_job_knowledge: bool = True
    checkpoint_overhead_fraction: float = 0.0
    ramp_mw_per_hour: float | None = None
    service_guard: bool = False
    fast_safety: bool = False

    def __post_init__(self):
        if not isinstance(self.observation_delay_h, int) or self.observation_delay_h < 0:
            raise ValueError("observation delay must be a nonnegative integer")
        if not np.isfinite(self.checkpoint_overhead_fraction) or not 0 <= self.checkpoint_overhead_fraction < 1:
            raise ValueError("checkpoint overhead fraction must be in [0,1)")
        if self.ramp_mw_per_hour is not None and (not np.isfinite(self.ramp_mw_per_hour) or self.ramp_mw_per_hour <= 0):
            raise ValueError("ramp limit must be positive and finite")

    @property
    def efficiency(self):
        return 1 - self.checkpoint_overhead_fraction


POLICIES = {
    "original": Policy(),
    "online": Policy(advance_job_knowledge=False),
    "delayed_online": Policy(observation_delay_h=1, advance_job_knowledge=False),
    "ramp_online": Policy(advance_job_knowledge=False, ramp_mw_per_hour=2.0),
    "overhead_online": Policy(advance_job_knowledge=False, checkpoint_overhead_fraction=.05),
    "combined": Policy(observation_delay_h=1, advance_job_knowledge=False,
                       checkpoint_overhead_fraction=.05, ramp_mw_per_hour=2.0),
}

POLICIES.update({
    "guarded_online": Policy(advance_job_knowledge=False, service_guard=True, fast_safety=True),
    "guarded_delayed": Policy(observation_delay_h=1, advance_job_knowledge=False,
                              service_guard=True, fast_safety=True),
    "guarded_combined": Policy(observation_delay_h=1, advance_job_knowledge=False,
                               checkpoint_overhead_fraction=.05, ramp_mw_per_hour=2.,
                               service_guard=True, fast_safety=True),
})


def max_deliverable_energy(job, t, previous_power, policy):
    """Maximum useful-work energy a job can still deliver in [t, deadline), causally.

    Uses only information known at time ``t``: the job's own release/deadline,
    power cap, remaining work and the current power level. Future exogenous
    values play no part. Ramp limits are respected in both directions: the
    trajectory rises from the current power at most one ramp step per hour and
    must leave enough room to ramp down to zero at the deadline.

    This deliberately ignores competition from other jobs, so it is an
    optimistic bound. Ranking by this quantity is a heuristic; it does not
    account for competing jobs or guarantee completion.
    """
    slots = job.deadline - t
    if slots <= 0:
        return 0.0
    if policy.ramp_mw_per_hour is None:
        return slots * job.max_power_mw * C.DT_H * policy.efficiency
    step = policy.ramp_mw_per_hour * C.DT_H
    cap = job.max_power_mw
    up = np.empty(slots)
    up[0] = min(max(float(previous_power), 0.0) + step, cap)
    for i in range(1, slots):
        up[i] = min(up[i - 1] + step, cap)
    down = np.empty(slots)
    down[slots - 1] = min(step, cap)
    for i in range(slots - 2, -1, -1):
        down[i] = min(down[i + 1] + step, cap)
    total = float(np.minimum(up, down).sum())
    return total * C.DT_H * policy.efficiency


def job_laxity(job, t, remaining, previous_power, policy):
    """Remaining deliverable energy minus remaining required energy.

    Negative means the job can no longer finish even if it receives all
    capacity from now on. Lower (more negative) is more urgent. Only
    currently known quantities are used.
    """
    return max_deliverable_energy(job, t, previous_power, policy) - remaining


def _energy_after(job, t, first_power, policy):
    """Energy deliverable from a ramp-feasible profile that starts at ``first_power``.

    The profile rises by at most one ramp step per hour toward the power cap
    and is truncated so it can still ramp down to zero by the deadline. This is
    the quantity a running job controls by choosing this hour's power.
    """
    slots = job.deadline - t
    if slots <= 0:
        return 0.0
    if policy.ramp_mw_per_hour is None:
        return min(first_power, job.max_power_mw) * slots * C.DT_H * policy.efficiency
    step = policy.ramp_mw_per_hour * C.DT_H
    cap = job.max_power_mw
    up = np.empty(slots)
    up[0] = min(max(float(first_power), 0.0), cap)
    for i in range(1, slots):
        up[i] = min(up[i - 1] + step, cap)
    down = np.empty(slots)
    down[slots - 1] = min(step, cap)
    for i in range(slots - 2, -1, -1):
        down[i] = min(down[i + 1] + step, cap)
    return float(np.minimum(up, down).sum()) * C.DT_H * policy.efficiency


def required_power_floor(job, t, remaining, previous_power, policy, cap):
    """Current service target, computed only from known job parameters.

    Without ramps this is an average remaining-work quota, not the minimum
    power needed right now: a job may defer this hour and catch up later.
    With ramps, bisection finds the smallest first-slot power whose optimistic
    single-job ramp trajectory can deliver the remaining work. The caller
    supplies the admissible cap and reserves mandatory ramp-down power.
    Neither branch accounts for competition or guarantees completion.
    The historical function name is retained for API compatibility.
    """
    slots = job.deadline - t
    if slots <= 0:
        return 0.0
    if remaining <= 1e-9:
        return 0.0
    if policy.ramp_mw_per_hour is None:
        return min(remaining / (C.DT_H * policy.efficiency * slots), cap)
    step = policy.ramp_mw_per_hour * C.DT_H
    low, high = 0.0, cap
    if _energy_after(job, t, high, policy) < remaining - 1e-9:
        return cap                               # already unreachable; give what is allowed
    for _ in range(40):
        mid = (low + high) / 2
        if _energy_after(job, t, mid, policy) >= remaining - 1e-9:
            high = mid
        else:
            low = mid
    return high


def service_power(sc, t, remaining, previous, inference, policy):
    """Deadline-aware service with ramp-down reservations.

    Three stages, all using only released jobs and currently known data:

    1. Ramp-down reservation: power already needed to keep every running
       job's shutdown trajectory physically ramp-feasible.
    2. Service targets in least-laxity-first order: average-work quotas without
       ramps, optimistic single-job necessary floors with ramps. Available
       capacity is allocated toward these targets; they may be truncated when
       targets compete. This reduces starvation without guaranteeing service.
    3. Surplus in least-laxity-first order: any capacity left after every
       target is met goes to the tightest jobs, up to their per-hour caps.

    Pure earliest-deadline-first (the previous behaviour) is the special case
    where stage 2 is disabled: it ignores remaining work and therefore cannot
    distinguish a nearly finished early job from one with a large backlog.

    Only released jobs enter. If reservations exceed available capacity,
    capacity takes precedence; evaluate() still reports the resulting
    emergency ramp loss.
    """
    power = np.zeros(len(sc.jobs))
    spare = max(C.IT_CAPACITY_MW - inference, 0.)
    active = [k for k,j in enumerate(sc.jobs) if j.release <= t < j.deadline and remaining[k] > 1e-9]
    upper = {}
    for k in active:
        job = sc.jobs[k]
        cap = min(job.max_power_mw, remaining[k] / (C.DT_H * policy.efficiency))
        if policy.ramp_mw_per_hour is not None:
            step = policy.ramp_mw_per_hour * C.DT_H
            slots = job.deadline - t
            cap = min(cap, previous[k] + step, slots * step)
            low, high = 0., cap
            budget = remaining[k] / (C.DT_H * policy.efficiency)
            for _ in range(40):
                mid = (low + high) / 2
                if sum(max(mid-i*step, 0) for i in range(slots)) <= budget:
                    low = mid
                else:
                    high = mid
            cap = low
            power[k] = min(max(previous[k]-step, 0.), cap)
        upper[k] = cap
    reserved = power.sum()
    if reserved > spare:
        power *= spare / reserved
        return power
    spare -= reserved
    # Least-laxity-first: jobs that are furthest behind relative to their
    # remaining deliverable capacity are served first.
    order = sorted(active, key=lambda k: (
        job_laxity(sc.jobs[k], t, remaining[k], previous[k], policy),
        sc.jobs[k].deadline, k))
    for k in order:                              # stage 2: service targets
        floor = required_power_floor(sc.jobs[k], t, remaining[k], previous[k], policy, upper[k])
        extra = min(max(floor - power[k], 0.0), spare)
        power[k] += extra
        spare -= extra
    for k in order:                              # stage 3: remaining surplus
        extra = min(upper[k]-power[k], spare)
        power[k] += extra
        spare -= extra
    return power


def available_estimates(sc, t, delay):
    """Current estimate: forecast + latest observable residual; future stays forecast.

    No actual value after t-delay is accessed. With zero delay this is the
    current actual; before the first observation it is the original forecast.
    Delay is in hours and rounded up to whole slots when DT_H is fractional.
    """
    if not np.isfinite(C.DT_H) or C.DT_H <= 0:
        raise ValueError("time step must be positive and finite")
    observed = t - int(np.ceil(delay / C.DT_H))
    values = []
    for forecast, actual in ((sc.inference_fc, sc.inference_act),
                             (sc.solar_fc, sc.solar_act), (sc.wind_fc, sc.wind_act)):
        residual = actual[observed] - forecast[observed] if observed >= 0 else 0.0
        values.append(max(float(forecast[t] + residual), 0.0))
    return (*values, observed)


def _info(policy, grid_limit, trace, fallback):
    return dict(policy=asdict(policy), work_efficiency=policy.efficiency,
                ramp_mw_per_hour=policy.ramp_mw_per_hour,
                grid_import_limit_mw=grid_limit, fallback_hours=fallback,
                decision_trace=trace)


def causal_mpc_schedule(sc, lam, grid_limit=None, policy=Policy()):
    sch = Schedule.empty(len(sc.jobs), sc.T)
    remaining = np.array([j.energy_mwh for j in sc.jobs])
    previous = np.zeros(len(sc.jobs))
    soc = C.BATT_SOC_START * C.BATT_ENERGY_MWH
    trace, fallback = [], []
    for t in range(sc.T):
        inf, solar, wind, observed = available_estimates(sc, t, policy.observation_delay_h)
        visible = [k for k,j in enumerate(sc.jobs) if policy.advance_job_knowledge or j.release <= t]
        view = copy.copy(sc)
        view.jobs = [sc.jobs[k] for k in visible]
        view.inference_fc = sc.inference_fc.copy(); view.inference_fc[t] = inf
        view.solar_fc = sc.solar_fc.copy(); view.solar_fc[t] = solar
        view.wind_fc = sc.wind_fc.copy(); view.wind_fc[t] = wind
        # nowcast=False is essential: a delayed planner cannot read the current actual.
        jp,ch,dis,_,fb = solve_window(view,t,lam,remaining[visible],soc,grid_limit,nowcast=False,
                                     work_efficiency=policy.efficiency,
                                     ramp_mw_per_hour=policy.ramp_mw_per_hour,
                                     previous_power=previous[visible])
        planned = jp[:,t].copy()
        if policy.service_guard or policy.fast_safety:
            # Explicit second-stage controller: current telemetry, never future actuals.
            safety_inf = float(sc.inference_act[t]) if policy.fast_safety else inf
            safety_green = float(sc.green_act[t]) if policy.fast_safety else solar+wind
            if policy.service_guard:
                committed = service_power(sc,t,remaining,previous,safety_inf,policy)[visible]
            else:
                committed = planned.copy()
                spare = max(C.IT_CAPACITY_MW-safety_inf,0.)
                if committed.sum() > spare:
                    committed *= spare / committed.sum()
            view.inference_fc[t] = safety_inf
            view.solar_fc[t] = safety_green
            view.wind_fc[t] = 0.
            jp,ch,dis,_,safety_fb = solve_window(
                view,t,lam,remaining[visible],soc,grid_limit,nowcast=False,
                work_efficiency=policy.efficiency,ramp_mw_per_hour=policy.ramp_mw_per_hour,
                previous_power=previous[visible],current_power=committed)
            fb = fb or safety_fb
        for local,k in enumerate(visible):
            sch.job_power[k,t] = jp[local,t]
        sch.charge[t],sch.discharge[t] = ch[t],dis[t]
        remaining = np.maximum(remaining - sch.job_power[:,t]*C.DT_H*policy.efficiency, 0)
        previous = sch.job_power[:,t].copy()
        soc += (C.BATT_EFF_CHARGE*ch[t] - dis[t]/C.BATT_EFF_DISCHARGE)*C.DT_H
        if fb: fallback.append(t)
        trace.append(dict(hour=t,observed_through=observed,visible_job_ids=[sc.jobs[k].id for k in visible],
                          inference_estimate=inf,green_estimate=solar+wind,
                          safety_observed_through=t if policy.fast_safety else observed,
                          planned_job_power=planned.tolist(),
                          committed_job_power=sch.job_power[visible,t].tolist()))
    sch.info = _info(policy,grid_limit,trace,fallback)
    return sch


def causal_edf_schedule(sc, grid_limit=None, policy=Policy()):
    """No-battery reference with identical information and compute assumptions.

    Guarded policies use the shared laxity allocator, not plain EDF. The
    historical function name remains; unguarded policies still dispatch EDF.
    """
    sch = Schedule.empty(len(sc.jobs),sc.T)
    remaining = np.array([j.energy_mwh for j in sc.jobs])
    previous = np.zeros(len(sc.jobs))
    trace = []
    for t in range(sc.T):
        inf,solar,wind,observed = available_estimates(sc,t,policy.observation_delay_h)
        if policy.service_guard or policy.fast_safety:
            current_inf = float(sc.inference_act[t]) if policy.fast_safety else inf
            sch.job_power[:,t] = service_power(sc,t,remaining,previous,current_inf,policy)
            remaining = np.maximum(remaining-sch.job_power[:,t]*C.DT_H*policy.efficiency,0)
            previous = sch.job_power[:,t].copy()
            trace.append(dict(hour=t,observed_through=observed,
                              safety_observed_through=t if policy.fast_safety else observed,
                              visible_job_ids=[j.id for j in sc.jobs if j.release<=t],
                              inference_estimate=inf,green_estimate=solar+wind))
            continue
        spare = max(C.IT_CAPACITY_MW-inf,0)
        active = [k for k,j in enumerate(sc.jobs) if j.release<=t<j.deadline and remaining[k]>1e-9]
        for k in sorted(active,key=lambda k:sc.jobs[k].deadline):
            job = sc.jobs[k]
            p = min(job.max_power_mw,remaining[k]/(C.DT_H*policy.efficiency),spare)
            if policy.ramp_mw_per_hour is not None:
                step = policy.ramp_mw_per_hour*C.DT_H
                slots = job.deadline-t
                p = min(p,previous[k]+step,slots*step)
                # Leave enough remaining work for a ramp-down tail; no fake idle work.
                low,high = 0.0,p
                budget = remaining[k]/(C.DT_H*policy.efficiency)
                for _ in range(40):
                    mid=(low+high)/2
                    needed = sum(max(mid-i*step,0) for i in range(slots))
                    if needed<=budget: low=mid
                    else: high=mid
                p=low
            sch.job_power[k,t]=p
            remaining[k]-=p*C.DT_H*policy.efficiency
            spare-=p
        previous=sch.job_power[:,t].copy()
        trace.append(dict(hour=t,observed_through=observed,
                          visible_job_ids=[j.id for j in sc.jobs if policy.advance_job_knowledge or j.release<=t],
                          inference_estimate=inf,green_estimate=solar+wind))
    sch.info=_info(policy,grid_limit,trace,[])
    return sch
