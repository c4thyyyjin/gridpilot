"""Finding #3: every LP implementation must reject tariffs the green-first formulation cannot represent."""
import numpy as np
import config as C
from data import make_scenario
from evaluate import evaluate
from validation import check_green_first, UnsupportedTariff
from mpc import mpc_schedule, open_loop_schedule
from scheduler_highs import lp_schedule_highs

GL = 26.0


def _impls():
    """All available LP implementations; CBC/PuLP one is included only if pulp is installed."""
    out = [("highs", lambda sc, lam: lp_schedule_highs(sc, lam)),
           ("mpc-open-loop", lambda sc, lam: open_loop_schedule(sc, lam, GL)),
           ("mpc-rolling", lambda sc, lam: mpc_schedule(sc, lam, GL))]
    try:
        from scheduler import lp_schedule
        out.append(("cbc", lambda sc, lam: lp_schedule(sc, lam)))
    except ImportError:          # PuLP not installed: skip only the CBC path, never mask other errors
        pass
    return out


def _raises_value_error(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


def test_cheap_tariff_rejected_by_every_implementation():
    sc = make_scenario(); sc.price = np.full(sc.T, 0.20)           # grid 0.20 < green 0.30
    for name, f in _impls():
        assert _raises_value_error(lambda: f(sc, 100)), f"{name} did not reject a cheap tariff"


def test_a_single_cheap_hour_is_enough_to_reject():
    sc = make_scenario(); sc.price = sc.price.copy(); sc.price[40] = 0.25
    for name, f in _impls():
        assert _raises_value_error(lambda: f(sc, 0)), f"{name} accepted a tariff with one cheap hour"


def test_boundary_grid_rate_equal_to_green_rate_is_accepted():
    sc = make_scenario(); sc.price = np.full(sc.T, C.GREEN_PRICE)
    check_green_first(sc, 0)                                       # equal rates: allowed
    assert evaluate(sc, lp_schedule_highs(sc, 0))["status"] == "feasible"


def test_guard_is_about_the_objective_rate_not_the_raw_price():
    """Price 0.29 < green 0.30, but with a carbon price the grid objective rate is above the green rate -> valid,
    and then the LP objective must equal the scorer's objective (proves the guard's condition is sufficient)."""
    sc = make_scenario(); sc.price = np.full(sc.T, 0.29)
    lam = 1000
    check_green_first(sc, lam)                                     # must not raise
    sch, obj = lp_schedule_highs(sc, lam, return_obj=True)
    assert abs(obj - evaluate(sc, sch, lam)["objective"]) / obj < 1e-6


def test_negative_lambda_with_invalid_objective_rates_is_rejected():
    sc = make_scenario()
    for name, f in _impls():
        assert _raises_value_error(lambda: f(sc, -1000)), f"{name} accepted invalid objective rates produced by negative lambda"


def test_error_message_names_the_problem():
    sc = make_scenario(); sc.price = np.full(sc.T, 0.20)
    try:
        check_green_first(sc, 100)
    except UnsupportedTariff as e:
        msg = str(e)
        assert "hour" in msg and "green rate" in msg and "MILP" in msg
    else:
        raise AssertionError("expected UnsupportedTariff")


def test_default_scenarios_and_lambda_sweep_still_pass_the_guard():
    for s in range(5):
        sc = make_scenario(s)
        for lam in C.LAMBDA_SWEEP:
            check_green_first(sc, lam)


def test_every_lp_implementation_uses_the_shared_guard():
    """Wiring check that works even where PuLP (CBC) cannot be imported: no implementation may keep a private copy
    of the rule, otherwise they can drift apart again."""
    for path in ("scheduler.py", "scheduler_highs.py", "mpc.py"):
        src = open(path).read()
        assert "from validation import check_green_first" in src and "check_green_first(sc, lam)" in src, path
    assert "grid objective rates >=" not in open("scheduler.py").read()      # old private copy removed
