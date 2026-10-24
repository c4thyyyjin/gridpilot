"""Continuous job/battery scheduling with PuLP's bundled CBC solver.

GRID_IMPORT_LIMIT_MW, when configured, bounds hourly facility grid imports.
Plans on forecasts by default; use_forecast=False is an actual-data oracle.
The green-first objective has a convex LP formulation when each hour's grid
cost plus carbon price is at least the nonnegative green equivalent (as in
config.py for nonnegative lambda). Unsupported tariffs are rejected rather
than silently allowing the solver to bypass green-first dispatch.
"""
import numpy as np
import pulp

import config as C
from evaluate import Schedule
from validation import check_green_first


def _build_lp(sc, lam, use_forecast):
    """Return the model and decision variables, also useful for diagnostics."""
    T, dt = sc.T, C.DT_H
    grid_limit = getattr(C, "GRID_IMPORT_LIMIT_MW", None)
    inference = sc.inference_fc if use_forecast else sc.inference_act
    green = sc.green_fc if use_forecast else sc.green_act
    green_rate = 1000 * C.GREEN_PRICE + lam * C.GREEN_CO2
    grid_rate = 1000 * sc.price + lam * sc.grid_co2
    check_green_first(sc, lam)          # shared with HiGHS and MPC (validation.py); raises UnsupportedTariff (a ValueError)

    model = pulp.LpProblem("dc_coschedule", pulp.LpMinimize)
    power = {
        (k, t): pulp.LpVariable(f"job_{k}_{t}", lowBound=0, upBound=j.max_power_mw)
        for k, j in enumerate(sc.jobs)
        for t in range(j.release, j.deadline)
    }
    charge = [pulp.LpVariable(f"charge_{t}", lowBound=0, upBound=C.BATT_POWER_MW) for t in range(T)]
    discharge = [pulp.LpVariable(f"discharge_{t}", lowBound=0, upBound=C.BATT_POWER_MW) for t in range(T)]
    soc = [pulp.LpVariable(f"soc_{t}", lowBound=C.BATT_SOC_MIN * C.BATT_ENERGY_MWH,
                           upBound=C.BATT_SOC_MAX * C.BATT_ENERGY_MWH) for t in range(T + 1)]
    start = C.BATT_SOC_START * C.BATT_ENERGY_MWH
    model += soc[0] == start
    model += soc[T] == start
    for k, j in enumerate(sc.jobs):
        model += dt * pulp.lpSum(power[k, t] for t in range(j.release, j.deadline)) == j.energy_mwh

    costs = []
    for t in range(T):
        it = inference[t] + pulp.lpSum(power[k, t] for k in range(len(sc.jobs)) if (k, t) in power)
        model += it <= C.IT_CAPACITY_MW
        model += soc[t + 1] == soc[t] + dt * (
            C.BATT_EFF_CHARGE * charge[t] - discharge[t] / C.BATT_EFF_DISCHARGE)
        net = C.PUE * it + charge[t] - discharge[t]
        supply = pulp.LpVariable(f"supply_{t}", lowBound=0)
        grid = pulp.LpVariable(f"grid_{t}", lowBound=0, upBound=grid_limit)
        # At optimum: supply=max(net,0), grid=max(supply-green,0).
        # This reproduces evaluate's clipping and green-first accounting,
        # including wasted discharge, without binary variables.
        model += supply >= net
        model += grid >= supply - float(green[t])
        costs.append(dt * (green_rate * supply
                           + float(grid_rate[t] - green_rate) * grid
                           + 1000 * C.BATT_DEGRADATION * discharge[t]))
    model += pulp.lpSum(costs)
    return model, power, charge, discharge


def lp_schedule(sc, lam, use_forecast=True) -> Schedule:
    """Minimize CNY cost + lam * tonnes CO2; raise if CBC cannot find an optimum."""
    model, power, charge, discharge = _build_lp(sc, lam, use_forecast)
    status = model.solve(pulp.PULP_CBC_CMD(msg=False))
    if status != pulp.LpStatusOptimal:
        raise RuntimeError(f"Scheduling LP failed: {pulp.LpStatus[status]}")
    schedule = Schedule.empty(len(sc.jobs), sc.T)
    for (k, t), variable in power.items():
        schedule.job_power[k, t] = variable.value()
    schedule.charge[:] = [v.value() for v in charge]
    schedule.discharge[:] = [v.value() for v in discharge]
    schedule.info["grid_import_limit_mw"] = getattr(C, "GRID_IMPORT_LIMIT_MW", None)
    return schedule
