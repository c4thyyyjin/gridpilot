"""Shared input validation for every LP scheduler (CBC, HiGHS, MPC).

The LP models green-first dispatch with   cost = green_rate*supply + (grid_rate - green_rate)*grid .
That is a correct, convex reformulation ONLY IF, in every hour,
        grid_rate[t] >= green_rate >= 0,
with   grid_rate[t] = 1000*price[t] + lam*grid_co2[t]   (CNY/MWh incl. carbon price)
       green_rate   = 1000*GREEN_PRICE + lam*GREEN_CO2.
Otherwise the coefficient (grid_rate - green_rate) is negative and the solver is paid to draw extra grid power:
the model is unbounded, or (if some other cap bounds it) silently returns a distorted schedule.

Supporting such tariffs requires an exact formulation, for example a MILP with
binary variables enforcing green-first dispatch. The current green-first policy
in evaluate.py can remain unchanged. Until then these tariffs are REJECTED, not approximated.
Lambda is validated through the resulting objective rates; negative lambda alone
is not rejected when those rates satisfy the condition above.
"""
import numpy as np
import config as C


class UnsupportedTariff(ValueError):
    """Grid objective rate below the green rate in some hour (or negative green rate): model not valid."""


def check_green_first(sc, lam):
    green_rate = 1000 * C.GREEN_PRICE + lam * C.GREEN_CO2
    grid_rate = 1000 * np.asarray(sc.price, float) + lam * np.asarray(sc.grid_co2, float)
    if not np.isfinite(green_rate) or not np.all(np.isfinite(grid_rate)):
        raise UnsupportedTariff("non-finite price / carbon / lambda")
    if green_rate < 0:
        raise UnsupportedTariff(f"green rate {green_rate:.1f} CNY/MWh is negative (lambda={lam})")
    bad = np.flatnonzero(grid_rate < green_rate - 1e-9)
    if bad.size:
        t = int(bad[np.argmin(grid_rate[bad])])
        raise UnsupportedTariff(
            f"{bad.size} hour(s) have grid rate below green rate {green_rate:.1f} CNY/MWh "
            f"(worst: hour {t}, grid rate {grid_rate[t]:.1f} = price {sc.price[t]:.3f} CNY/kWh*1000 + lambda*{sc.grid_co2[t]:.3f}). "
            f"The green-first LP is unbounded/invalid here; raise the tariff or lambda, or model dispatch with a MILP.")
