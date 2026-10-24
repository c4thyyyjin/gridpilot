"""Rolling-horizon (MPC) scheduler + window LP with grid import limit.

Every hour t0 the controller:
  1. observes the ACTUAL inference load and green output of hour t0 (nowcast) and the true battery SoC,
  2. re-solves the LP over hours t0..T-1 using actual values for t0 and FORECASTS for later hours,
  3. commits only hour t0's decisions, then moves on.

What is and is not guaranteed
  * Battery limits (power, SoC window, end SoC) are always hard constraints. They can always be met.
  * Strict problem first: every window is first solved with HARD job-energy and grid-limit constraints.
  * Fallback: only if that strict LP is infeasible (e.g. an impossible deadline, a grid limit too low for the
    load) the window is re-solved with penalised slack (config.PEN_*). The hours where this happened are recorded
    in Schedule.info["fallback_hours"], and evaluate() reports the resulting unmet_job_mwh / grid_overflow_mwh and
    a penalised objective, while feasibility is ranked separately from monetary penalties.
  * If inference ALONE exceeds IT capacity in an hour, no schedule can be feasible. Jobs get 0 power that hour
    (we never add load on top of an overload) and evaluate() flags the run as status="exogenous_overload".
  * Tariffs where grid price (+ carbon term) is below the green price are REJECTED with UnsupportedTariff
    (validation.py): the green-first LP is not valid there.

solve_window(..., nowcast=False, t0=0) is the open-loop plan (one solve at hour 0, forecasts only).
"""
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix
import config as C
from evaluate import Schedule
from validation import check_green_first



class InfeasibleWindow(RuntimeError):
    """The strict (hard-constraint) window LP has no solution."""


def _solve(sc, t0, lam, remaining, soc0, grid_limit, nowcast, forecast_only, hard,
           work_efficiency=1.0, ramp_mw_per_hour=None, previous_power=None, current_power=None):
    """One LP. hard=True: no slack (unmet energy and grid overflow forced to 0). hard=False: penalised slack."""
    T, dt, J = sc.T, C.DT_H, len(sc.jobs)
    inf = sc.inference_fc.copy(); G = sc.green_fc.copy()
    if nowcast and not forecast_only:
        inf[t0] = sc.inference_act[t0]; G[t0] = sc.green_act[t0]
    g_rate = 1000 * C.GREEN_PRICE + lam * C.GREEN_CO2
    r = 1000 * sc.price + lam * sc.grid_co2
    if not np.isfinite(work_efficiency) or not 0 < work_efficiency <= 1:
        raise ValueError("work efficiency must be in (0,1]")
    if ramp_mw_per_hour is not None and (not np.isfinite(ramp_mw_per_hour) or ramp_mw_per_hour <= 0):
        raise ValueError("ramp limit must be positive and finite")
    previous_power = np.zeros(J) if previous_power is None else np.asarray(previous_power, float)
    H = range(t0, T)
    idx, n = {}, 0
    def new(key):
        nonlocal n
        idx[key] = n; n += 1
    active = [k for k, j in enumerate(sc.jobs) if remaining[k] > 1e-9]
    for k in active:
        j = sc.jobs[k]
        for t in range(max(t0, j.release), j.deadline):
            new(("p", k, t))
        new(("short", k))
    for t in H:
        for nm in ("c", "d", "u", "g", "over"):
            new((nm, t))
    for t in range(t0, T + 1):
        new(("s", t))
    ramp_specs = []
    if ramp_mw_per_hour is not None:
        for k in range(J):
            for t in range(t0, T + 1):
                current = idx.get(("p", k, t))
                prior = idx.get(("p", k, t - 1)) if t > t0 else None
                initial = float(previous_power[k]) if t == t0 else 0.0
                if current is not None or prior is not None or initial:
                    idx[("ramp_slack", k, t)] = n
                    ramp_specs.append((k, t, current, prior, initial, n))
                    n += 1
    cost = np.zeros(n); lb = np.zeros(n); ub = np.full(n, np.inf)
    for k in active:
        j = sc.jobs[k]
        for t in range(max(t0, j.release), j.deadline):
            ub[idx[("p", k, t)]] = j.max_power_mw
        cost[idx[("short", k)]] = C.PEN_UNMET_CNY_PER_MWH
        if hard: ub[idx[("short", k)]] = 0.0
    if current_power is not None:
        current_power = np.asarray(current_power, float)
        if current_power.shape != (J,) or not np.all(np.isfinite(current_power)) or np.any(current_power < 0):
            raise ValueError("current_power must contain one finite nonnegative value per job")
        for k, power in enumerate(current_power):
            key = ("p", k, t0)
            if key not in idx:
                if power > 1e-8:
                    raise ValueError("current power outside an active job window")
            else:
                if power > ub[idx[key]] + 1e-8:
                    raise ValueError("current power exceeds job maximum")
                lb[idx[key]] = ub[idx[key]] = power
    for t in H:
        ub[idx[("c", t)]] = ub[idx[("d", t)]] = C.BATT_POWER_MW
        cost[idx[("u", t)]] = dt * g_rate
        cost[idx[("g", t)]] = dt * (r[t] - g_rate)
        cost[idx[("d", t)]] = dt * 1000 * C.BATT_DEGRADATION
        cost[idx[("over", t)]] = dt * C.PEN_GRID_OVERFLOW_CNY_PER_MWH
        if hard: ub[idx[("over", t)]] = 0.0
    for _, _, _, _, _, slack in ramp_specs:
        cost[slack] = C.PEN_RAMP_CNY_PER_MWH * dt
        if hard:
            ub[slack] = 0
    for t in range(t0, T + 1):
        lb[idx[("s", t)]] = C.BATT_SOC_MIN * C.BATT_ENERGY_MWH
        ub[idx[("s", t)]] = C.BATT_SOC_MAX * C.BATT_ENERGY_MWH
    s_start = C.BATT_SOC_START * C.BATT_ENERGY_MWH
    lb[idx[("s", t0)]] = ub[idx[("s", t0)]] = soc0
    lb[idx[("s", T)]] = ub[idx[("s", T)]] = s_start

    na, nh = len(active), T - t0
    Aeq = lil_matrix((na + nh, n)); beq = np.zeros(na + nh)
    for a, k in enumerate(active):
        j = sc.jobs[k]
        for t in range(max(t0, j.release), j.deadline):
            Aeq[a, idx[("p", k, t)]] = dt * work_efficiency
        Aeq[a, idx[("short", k)]] = 1
        beq[a] = remaining[k]
    for i, t in enumerate(H):
        row = na + i
        Aeq[row, idx[("s", t + 1)]] = 1; Aeq[row, idx[("s", t)]] = -1
        Aeq[row, idx[("c", t)]] = -dt * C.BATT_EFF_CHARGE
        Aeq[row, idx[("d", t)]] = dt / C.BATT_EFF_DISCHARGE
    Aub = lil_matrix((4 * nh, n)); bub = np.zeros(4 * nh)
    for i, t in enumerate(H):
        for k in active:
            if (("p", k, t)) in idx:
                Aub[i, idx[("p", k, t)]] = 1                       # IT capacity
                Aub[nh + i, idx[("p", k, t)]] = C.PUE              # supply >= net
        bub[i] = max(C.IT_CAPACITY_MW - inf[t], 0.0)   # if inference alone > capacity this is 0: jobs get nothing; the overload itself is exogenous
        Aub[nh + i, idx[("c", t)]] = 1; Aub[nh + i, idx[("d", t)]] = -1; Aub[nh + i, idx[("u", t)]] = -1
        bub[nh + i] = -C.PUE * inf[t]
        Aub[2 * nh + i, idx[("u", t)]] = 1; Aub[2 * nh + i, idx[("g", t)]] = -1   # grid >= supply - green
        bub[2 * nh + i] = G[t]
        if grid_limit is not None:                                  # grid - over <= limit
            Aub[3 * nh + i, idx[("g", t)]] = 1; Aub[3 * nh + i, idx[("over", t)]] = -1
            bub[3 * nh + i] = grid_limit
        else:
            bub[3 * nh + i] = 1e9
    if ramp_specs:
        from scipy.sparse import vstack
        ramp_rows = lil_matrix((2 * len(ramp_specs), n))
        ramp_rhs = np.empty(2 * len(ramp_specs))
        step = ramp_mw_per_hour * dt
        for i, (_, _, current, prior, initial, slack) in enumerate(ramp_specs):
            for sign, row in ((1, 2*i), (-1, 2*i+1)):
                if current is not None:
                    ramp_rows[row, current] = sign
                if prior is not None:
                    ramp_rows[row, prior] = -sign
                ramp_rows[row, slack] = -1
                ramp_rhs[row] = step + sign * initial
        Aub = vstack([Aub.tocsr(), ramp_rows.tocsr()])
        bub = np.r_[bub, ramp_rhs]
    res = linprog(cost, A_ub=Aub.tocsr(), b_ub=bub, A_eq=Aeq.tocsr(), b_eq=beq,
                  bounds=list(zip(lb, ub)), method="highs")
    if res.status == 2:
        raise InfeasibleWindow(f"window LP infeasible at t0={t0} (hard={hard})")
    if res.status != 0:
        raise RuntimeError(f"window LP failed at t0={t0}: {res.message}")   # e.g. unbounded: do NOT hide it behind the fallback
    x = res.x
    jp = np.zeros((J, T)); ch = np.zeros(T); dis = np.zeros(T)
    for key, i in idx.items():
        if key[0] == "p":
            jp[key[1], key[2]] = x[i]
    for t in H:
        ch[t], dis[t] = x[idx[("c", t)]], x[idx[("d", t)]]
    return jp, ch, dis, res.fun


def solve_window(sc, t0, lam, remaining, soc0, grid_limit=None, nowcast=True, forecast_only=False,
                 work_efficiency=1.0, ramp_mw_per_hour=None, previous_power=None, current_power=None):
    """Plan hours t0..T-1: strict LP first, penalised fallback only if strict is infeasible.
    Returns (job_power[J,T], charge[T], discharge[T], objective, used_fallback)."""
    check_green_first(sc, lam)          # raises UnsupportedTariff; the fallback below is for infeasible windows only
    try:
        return (*_solve(sc, t0, lam, remaining, soc0, grid_limit, nowcast, forecast_only, hard=True,
                         work_efficiency=work_efficiency, ramp_mw_per_hour=ramp_mw_per_hour, previous_power=previous_power, current_power=current_power), False)
    except InfeasibleWindow:
        return (*_solve(sc, t0, lam, remaining, soc0, grid_limit, nowcast, forecast_only, hard=False,
                         work_efficiency=work_efficiency, ramp_mw_per_hour=ramp_mw_per_hour, previous_power=previous_power, current_power=current_power), True)


def open_loop_schedule(sc, lam, grid_limit=None, use_forecast=True):
    """One solve at hour 0. use_forecast=False => oracle that knows the actual future."""
    rem = np.array([j.energy_mwh for j in sc.jobs])
    if use_forecast:
        jp, ch, dis, _, fb = solve_window(sc, 0, lam, rem, C.BATT_SOC_START * C.BATT_ENERGY_MWH,
                                          grid_limit, nowcast=False)
    else:
        import copy
        o = copy.copy(sc); o.inference_fc, o.solar_fc, o.wind_fc = sc.inference_act, sc.solar_act, sc.wind_act
        jp, ch, dis, _, fb = solve_window(o, 0, lam, rem, C.BATT_SOC_START * C.BATT_ENERGY_MWH,
                                          grid_limit, nowcast=False)
    return Schedule(jp, ch, dis, {"fallback_hours": [0] if fb else [], "grid_import_limit_mw": grid_limit})


def mpc_schedule(sc, lam, grid_limit=None) -> Schedule:
    T, dt, J = sc.T, C.DT_H, len(sc.jobs)
    sch = Schedule.empty(J, T)
    rem = np.array([j.energy_mwh for j in sc.jobs])
    soc = C.BATT_SOC_START * C.BATT_ENERGY_MWH
    fallback_hours = []
    for t0 in range(T):
        jp, ch, dis, _, fb = solve_window(sc, t0, lam, rem, soc, grid_limit, nowcast=True)
        if fb: fallback_hours.append(t0)
        sch.job_power[:, t0] = jp[:, t0]
        sch.charge[t0], sch.discharge[t0] = ch[t0], dis[t0]
        rem = np.maximum(rem - jp[:, t0] * dt, 0.0)
        soc += (C.BATT_EFF_CHARGE * ch[t0] - dis[t0] / C.BATT_EFF_DISCHARGE) * dt
    sch.info = {"fallback_hours": fallback_hours, "grid_import_limit_mw": grid_limit}
    return sch
