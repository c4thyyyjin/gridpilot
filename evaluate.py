"""The ONE scorer every method goes through (baseline, greedy, LP). Scores against ACTUAL values.

A Schedule holds:
  job_power  : array (n_jobs, T)  IT MW given to each job in each hour
  charge     : array (T,)         MW drawn from the facility bus into the battery
  discharge  : array (T,)         MW delivered from the battery to the facility bus

Hourly energy balance (facility side):
  load = (inference_act + sum(job_power)) * PUE
  green_used + grid + discharge = load + charge,   green_used <= green_act
Green energy is used first; unused green is curtailed. Grid fills the rest.
"""
from dataclasses import dataclass, field
import numpy as np
import config as C

TOL = 1e-6
_DEFAULT_LIMIT = object()


def _validate_schedule(sc, sch, dt):
    """Reject malformed schedules instead of scoring them.

    Two failure modes were observed before this check:

    * Negative battery power slipped past the magnitude-only limit check, so a
      negative charge/discharge pair reduced net load and artificially lowered
      cost while still reporting a valid objective.
    * NaN job or battery values made every comparison False (all violations are
      written as ``x > limit``), so the run could be classified from an empty
      set of violations, with a NaN objective. NaN is not a feasible schedule.

    Shapes are checked too, because a silently short array would broadcast and
    score the wrong hours.
    """
    if not isinstance(sc.T, (int, np.integer)) or sc.T <= 0:
        raise ValueError("scenario length must be a positive integer")
    for name in ("price", "grid_co2", "solar_fc", "wind_fc", "solar_act",
                 "wind_act", "inference_fc", "inference_act"):
        array = np.asarray(getattr(sc, name), float)
        if array.shape != (sc.T,) or not np.all(np.isfinite(array)):
            raise ValueError(f"{name} must contain {sc.T} finite hourly values")
        if name not in ("price", "grid_co2") and (array < -TOL).any():
            raise ValueError(f"{name} must be nonnegative")
    jp = np.asarray(sch.job_power, float)
    ch = np.asarray(sch.charge, float)
    dis = np.asarray(sch.discharge, float)
    expected = (len(sc.jobs), sc.T)
    if jp.shape != expected:
        raise ValueError(f"job_power must have shape {expected}, got {jp.shape}")
    if ch.shape != (sc.T,) or dis.shape != (sc.T,):
        raise ValueError(f"charge/discharge must have shape {(sc.T,)}, got {ch.shape}/{dis.shape}")
    for name, array in (("job_power", jp), ("charge", ch), ("discharge", dis)):
        if not np.all(np.isfinite(array)):
            hours = np.argwhere(~np.isfinite(array))
            raise ValueError(f"{name} contains non-finite values at {hours[:5].tolist()}")
        if (array < -TOL).any():
            hours = np.argwhere(array < -TOL)
            raise ValueError(f"{name} contains negative power at {hours[:5].tolist()}")
    if not np.isfinite(dt) or dt <= 0:
        raise ValueError("time step must be positive and finite")
    return jp, ch, dis


@dataclass
class Schedule:
    job_power: np.ndarray
    charge: np.ndarray
    discharge: np.ndarray
    info: dict = field(default_factory=dict)   # optional diagnostics from the scheduler (e.g. fallback hours)

    @staticmethod
    def empty(n_jobs, T):
        return Schedule(np.zeros((n_jobs, T)), np.zeros(T), np.zeros(T))


def evaluate(sc, sch: Schedule, lam=C.LAMBDA_DEFAULT, grid_limit=_DEFAULT_LIMIT, *,
             work_efficiency=None, ramp_mw_per_hour=_DEFAULT_LIMIT):
    """Score actual flows; explicit limit overrides schedule metadata, then config.

    None means unlimited. Feasibility is ranked separately from monetary penalties.
    """
    T, dt = sc.T, C.DT_H
    if not np.isfinite(lam):
        raise ValueError("lambda must be finite")
    jp, ch, dis = _validate_schedule(sc, sch, dt)

    efficiency = sch.info.get("work_efficiency", 1.0) if work_efficiency is None else work_efficiency
    if not np.isfinite(efficiency) or not 0 < efficiency <= 1:
        raise ValueError("work efficiency must be in (0,1]")
    ramp = sch.info.get("ramp_mw_per_hour") if ramp_mw_per_hour is _DEFAULT_LIMIT else ramp_mw_per_hour
    ramp_events, ramp_excess = 0, 0.0
    if ramp is not None:
        if not np.isfinite(ramp) or ramp <= 0:
            raise ValueError("ramp limit must be positive and finite")
        transitions = np.diff(np.pad(jp, ((0, 0), (1, 1))), axis=1)
        excess = np.maximum(np.abs(transitions) - ramp * dt, 0)
        ramp_events = int((excess > 1e-4).sum())
        ramp_excess = float(excess.sum() * dt)
        if ramp_excess < 1e-6:
            ramp_excess = 0.0
    # ---- SLA / constraint checks ------------------------------------------------
    sla = 0
    unmet = 0.0
    for k, j in enumerate(sc.jobs):
        outside = jp[k].copy()
        outside[j.release:j.deadline] = 0
        done = jp[k, j.release:j.deadline].sum() * dt * efficiency
        unmet += max(j.energy_mwh - done, 0.0)
        if (outside > TOL).any() or done < j.energy_mwh - 1e-4 or (jp[k] > j.max_power_mw + TOL).any() or (jp[k] < -TOL).any():
            sla += 1
    unmet = 0.0 if unmet < 1e-6 else unmet
    it_total = sc.inference_act + jp.sum(axis=0)
    inf_overload_h = int((sc.inference_act > C.IT_CAPACITY_MW + 1e-9).sum())   # impossible to serve whatever we do
    cap_viol_h = int((it_total > C.IT_CAPACITY_MW + 1e-4).sum())

    # battery state of charge
    soc = np.empty(T + 1)
    soc[0] = C.BATT_SOC_START * C.BATT_ENERGY_MWH
    for t in range(T):
        soc[t + 1] = soc[t] + (C.BATT_EFF_CHARGE * ch[t] - dis[t] / C.BATT_EFF_DISCHARGE) * dt
    lo, hi = C.BATT_SOC_MIN * C.BATT_ENERGY_MWH, C.BATT_SOC_MAX * C.BATT_ENERGY_MWH
    batt_viol = bool(
        (soc < lo - 1e-4).any() or (soc > hi + 1e-4).any()
        or abs(soc[-1] - soc[0]) > 1e-3
        or (ch > C.BATT_POWER_MW + TOL).any() or (dis > C.BATT_POWER_MW + TOL).any())
    # (charging and discharging in the same hour is wasteful but not illegal; the cost already penalises it)

    # ---- energy flows -----------------------------------------------------------
    load = it_total * C.PUE
    load_mwh = load.sum() * dt
    net = load + ch - dis                       # what green + grid must supply
    wasted_discharge = np.maximum(-net, 0)      # battery output nobody needed
    net = np.maximum(net, 0)
    green_used = np.minimum(sc.green_act, net)
    grid = net - green_used
    curtailed = sc.green_act - green_used

    # Renewable load service with a well-mixed battery. Initial stored energy
    # is conservatively nonrenewable. Within each slot, discharge serves load
    # first; external green serves the remaining load before charging. Charging
    # is mixed before withdrawal. Surplus discharge may recycle through charging;
    # solve its color fraction algebraically rather than inventing green energy.
    # This attribution convention changes no physical dispatch, cost or CO2.
    stored_green = 0.0
    green_served_direct = 0.0
    green_served_stored = 0.0
    for t in range(T):
        charge = max(float(ch[t]), 0.0)
        discharge = max(float(dis[t]), 0.0)
        demand = max(float(load[t]), 0.0)
        battery_to_load = min(discharge, demand)
        direct = min(float(green_used[t]), demand - battery_to_load)
        green_to_charge = max(float(green_used[t]) - direct, 0.0)
        recycled = min(max(discharge - demand, 0.0), charge)
        mixed_energy = soc[t] + C.BATT_EFF_CHARGE * charge * dt
        denominator = mixed_energy - C.BATT_EFF_CHARGE * recycled * dt
        fraction = ((stored_green + C.BATT_EFF_CHARGE * green_to_charge * dt)
                    / denominator) if denominator > TOL else 0.0
        fraction = float(np.clip(fraction, 0.0, 1.0))
        green_served_direct += direct * dt
        green_served_stored += fraction * battery_to_load * dt
        # Withdrawn energy is discharge/eta_dis, including conversion losses.
        stored_green = fraction * max(float(soc[t + 1]), 0.0)
    green_served = green_served_direct + green_served_stored
    green_share_pct = 100 * green_served / load_mwh if load_mwh > 0 else 0.0
    # Normalize floating-point roundoff at the mathematical upper bound only.
    if abs(green_share_pct - 100.0) < 1e-10:
        green_share_pct = 100.0

    cost = (grid * sc.price * 1000 + green_used * C.GREEN_PRICE * 1000
            + dis * C.BATT_DEGRADATION * 1000).sum() * dt           # CNY
    co2 = (grid * sc.grid_co2 + green_used * C.GREEN_CO2).sum() * dt  # tonnes
    if grid_limit is _DEFAULT_LIMIT:
        grid_limit = sch.info.get("grid_import_limit_mw", getattr(C, "GRID_IMPORT_LIMIT_MW", None))
    limit = np.inf if grid_limit is None else float(grid_limit)
    if np.isnan(limit) or limit < 0:
        raise ValueError("grid limit must be nonnegative or None")
    overflow = float(np.maximum(grid - limit, 0).sum() * dt)
    overflow = 0.0 if overflow < 1e-6 else overflow
    objective = cost + lam * co2
    # Monetary penalties quantify service loss; they do not replace feasibility checks.
    penalized = objective + C.PEN_UNMET_CNY_PER_MWH * unmet + C.PEN_GRID_OVERFLOW_CNY_PER_MWH * overflow + getattr(C, "PEN_RAMP_CNY_PER_MWH", 100_000.0) * ramp_excess
    if inf_overload_h > 0:
        status = "exogenous_overload"      # inference alone exceeds IT capacity: no schedule can be fully feasible
    elif sla or cap_viol_h or batt_viol or overflow > 0 or ramp_events:
        status = "degraded"
    else:
        status = "feasible"
    return {
        "work_efficiency": efficiency,
        "compute_overhead_mwh": float(jp.sum() * dt * (1-efficiency)),
        "ramp_violation_events": ramp_events,
        "ramp_excess_mwh": ramp_excess,
        "cost_cny": cost,
        "co2_t": co2,
        "objective": objective,
        "penalized_objective": penalized,
        "feasible": status == "feasible",
        "comparison_key": (status != "feasible", penalized),
        "grid_import_limit_mw": limit,
        "fallback_hours": len(sch.info.get("fallback_hours", [])),
        "status": status,
        "unmet_job_mwh": unmet,
        "grid_overflow_mwh": overflow,
        "inference_overload_hours": inf_overload_h,
        "green_share_pct": green_share_pct,
        "green_served_mwh": green_served,
        "green_served_direct_mwh": green_served_direct,
        "green_served_stored_mwh": green_served_stored,
        "green_drawn_mwh": green_used.sum() * dt,
        "curtailed_mwh": curtailed.sum() * dt,
        "peak_grid_mw": grid.max(),
        "grid_mwh": grid.sum() * dt,
        "load_mwh": load_mwh,
        "sla_violations": sla,
        "capacity_violation_hours": cap_viol_h,
        "battery_violation": batt_viol,
        "grid_limit_violation_hours": int((grid > limit + 1e-4).sum()),
        "wasted_discharge_mwh": wasted_discharge.sum() * dt,
        "grid_series": grid, "green_used_series": green_used, "soc_series": soc,
    }


SCALAR_KEYS = ["cost_cny", "co2_t", "objective", "green_share_pct", "curtailed_mwh",
               "peak_grid_mw", "sla_violations", "capacity_violation_hours", "battery_violation", "grid_limit_violation_hours",
               "penalized_objective", "unmet_job_mwh", "grid_overflow_mwh", "inference_overload_hours", "status"]


def summary(m):
    return {k: m[k] for k in SCALAR_KEYS}
