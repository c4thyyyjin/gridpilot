"""Independent LP implementation (SciPy HiGHS) of the same model as scheduler.py (PuLP/CBC).
Used to cross-check scheduler.py: both must give the same optimal objective."""
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix
import config as C
from evaluate import Schedule
from validation import check_green_first


def lp_schedule_highs(sc, lam, use_forecast=True, return_obj=False):
    check_green_first(sc, lam)          # reject tariffs the green-first LP cannot represent (see validation.py)
    T, dt, J = sc.T, C.DT_H, len(sc.jobs)
    grid_limit = getattr(C, "GRID_IMPORT_LIMIT_MW", None)
    inf = sc.inference_fc if use_forecast else sc.inference_act
    G = sc.green_fc if use_forecast else sc.green_act
    g_rate = 1000 * C.GREEN_PRICE + lam * C.GREEN_CO2
    r = 1000 * sc.price + lam * sc.grid_co2
    # variable layout
    idx, n = {}, 0
    for k, j in enumerate(sc.jobs):
        for t in range(j.release, j.deadline):
            idx[("p", k, t)] = n; n += 1
    for name, size in (("c", T), ("d", T), ("s", T + 1), ("u", T), ("g", T)):
        for t in range(size):
            idx[(name, t)] = n; n += 1
    cost = np.zeros(n); lb = np.zeros(n); ub = np.full(n, np.inf)
    for k, j in enumerate(sc.jobs):
        for t in range(j.release, j.deadline):
            ub[idx[("p", k, t)]] = j.max_power_mw
    for t in range(T):
        if grid_limit is not None:
            ub[idx[("g", t)]] = grid_limit
        ub[idx[("c", t)]] = ub[idx[("d", t)]] = C.BATT_POWER_MW
        cost[idx[("u", t)]] = dt * g_rate
        cost[idx[("g", t)]] = dt * (r[t] - g_rate)
        cost[idx[("d", t)]] = dt * 1000 * C.BATT_DEGRADATION
    for t in range(T + 1):
        lb[idx[("s", t)]] = C.BATT_SOC_MIN * C.BATT_ENERGY_MWH
        ub[idx[("s", t)]] = C.BATT_SOC_MAX * C.BATT_ENERGY_MWH
    s0 = C.BATT_SOC_START * C.BATT_ENERGY_MWH
    lb[idx[("s", 0)]] = ub[idx[("s", 0)]] = s0
    lb[idx[("s", T)]] = ub[idx[("s", T)]] = s0
    # equalities: job energy, SoC dynamics
    Aeq = lil_matrix((J + T, n)); beq = np.zeros(J + T)
    for k, j in enumerate(sc.jobs):
        for t in range(j.release, j.deadline):
            Aeq[k, idx[("p", k, t)]] = dt
        beq[k] = j.energy_mwh
    for t in range(T):
        row = J + t
        Aeq[row, idx[("s", t + 1)]] = 1; Aeq[row, idx[("s", t)]] = -1
        Aeq[row, idx[("c", t)]] = -dt * C.BATT_EFF_CHARGE
        Aeq[row, idx[("d", t)]] = dt / C.BATT_EFF_DISCHARGE
    # inequalities: capacity, supply >= net, grid >= supply - green
    Aub = lil_matrix((3 * T, n)); bub = np.zeros(3 * T)
    for t in range(T):
        for k, j in enumerate(sc.jobs):
            if j.release <= t < j.deadline:
                Aub[t, idx[("p", k, t)]] = 1
                Aub[T + t, idx[("p", k, t)]] = C.PUE
        bub[t] = C.IT_CAPACITY_MW - inf[t]
        # PUE*(inf+sum p) + c - d - u <= 0
        Aub[T + t, idx[("c", t)]] = 1; Aub[T + t, idx[("d", t)]] = -1; Aub[T + t, idx[("u", t)]] = -1
        bub[T + t] = -C.PUE * inf[t]
        # u - g <= G
        Aub[2 * T + t, idx[("u", t)]] = 1; Aub[2 * T + t, idx[("g", t)]] = -1
        bub[2 * T + t] = G[t]
    res = linprog(cost, A_ub=Aub.tocsr(), b_ub=bub, A_eq=Aeq.tocsr(), b_eq=beq,
                  bounds=list(zip(lb, ub)), method="highs")
    if res.status != 0:
        raise RuntimeError(res.message)
    x = res.x
    sch = Schedule.empty(J, T)
    for (key, i) in idx.items():
        if key[0] == "p":
            sch.job_power[key[1], key[2]] = x[i]
    for t in range(T):
        sch.charge[t], sch.discharge[t] = x[idx[("c", t)]], x[idx[("d", t)]]
    sch.info["grid_import_limit_mw"] = grid_limit
    return (sch, res.fun) if return_obj else sch
