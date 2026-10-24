import numpy as np
import pytest

from reporting import METRICS, aggregate, paired_comparisons, run_stress


def samples(base=(100, 100, 100), actual=(90, 80, 70)):
    rows = []
    for method, values in (("baseline", base), ("MPC", actual)):
        for seed, value in enumerate(values):
            rows.append(dict(batch=0, seed=seed, method=method, status="feasible",
                             feasible=True, objective=value, cost_cny=value, co2_t=value))
    return rows


def test_paired_t_interval_matches_hand_calculation():
    summary, pairs = paired_comparisons(samples())
    r = summary[summary.metric == "objective"].iloc[0]
    # Three gains 10,20,30: mean=20, sample SD=10, df=2 t(0.975)=4.30265273.
    margin = 4.302652729911275 * 10 / np.sqrt(3)
    assert r.gain_pct_mean == pytest.approx(20)
    assert r.gain_pct_ci_low == pytest.approx(20 - margin)
    assert r.gain_pct_ci_high == pytest.approx(20 + margin)
    assert r.saving_mean == pytest.approx(20)
    assert r.n_pairs == 3 and r.eligible
    assert len(pairs) == 9


def test_pairing_uses_seed_not_row_order():
    rows = samples()
    expected, _ = paired_comparisons(rows)
    shuffled, _ = paired_comparisons(rows[:3] + rows[3:][::-1])
    np.testing.assert_allclose(expected.gain_pct_mean, shuffled.gain_pct_mean)


def test_mean_percentage_differs_from_ratio_of_means():
    summary, _ = paired_comparisons(samples((100, 200), (90, 100)))
    assert summary.iloc[0].gain_pct_mean == pytest.approx(30)
    assert summary.iloc[0].saving_mean == pytest.approx(55)


def test_infeasible_pair_retained_and_disqualifies_whole_comparison():
    rows = samples()
    rows[-1].update(status="degraded", feasible=False)
    summary, pairs = paired_comparisons(rows)
    assert not summary.eligible.any()
    assert (summary.n_pairs == 3).all() and (summary.n_feasible_pairs == 2).all()
    assert summary.gain_pct_mean.isna().all()
    assert len(pairs) == 9
    assert pairs.loc[~pairs.pair_feasible, "gain_pct"].isna().all()


def test_missing_seed_is_an_error_not_silent_dropping():
    with pytest.raises(ValueError, match="identical seed"):
        paired_comparisons(samples()[:-1])


def test_duplicate_pair_is_rejected():
    rows = samples()
    with pytest.raises(ValueError, match="duplicate"):
        paired_comparisons(rows + [rows[0]])


def test_single_seed_has_mean_but_no_confidence_interval():
    summary, _ = paired_comparisons(samples((100,), (80,)))
    assert (summary.gain_pct_mean == 20).all()
    assert summary.gain_pct_ci_low.isna().all()
    assert (summary.ci_status == "insufficient_pairs").all()


def test_zero_baseline_keeps_absolute_savings_without_fake_percentage():
    summary, _ = paired_comparisons(samples((0, 0), (0, 0)))
    assert (summary.saving_mean == 0).all()
    assert summary.gain_pct_mean.isna().all()
    assert (summary.percentage_status == "zero_baseline").all()


def test_worst_case_and_affected_run_counts_do_not_average_away_failure():
    clean = dict.fromkeys(METRICS, 0)
    clean.update(status="feasible", feasible=True)
    bad = dict(clean, status="degraded", feasible=False, battery_violation=True,
               sla_violations=2, capacity_violation_hours=3, grid_limit_violation_hours=4,
               unmet_job_mwh=5, grid_overflow_mwh=6, inference_overload_hours=7, fallback_hours=8)
    r = aggregate([clean, clean, bad])
    for key in ("battery_violation", "sla_violations", "capacity_violation_hours",
                "grid_limit_violation_hours", "unmet_job_mwh", "grid_overflow_mwh",
                "inference_overload_hours", "fallback_hours"):
        assert r[f"max_{key}"] == bad[key]
        assert r[f"total_{key}"] == bad[key]
        assert r[f"runs_with_{key}"] == 1


@pytest.mark.parametrize("where", ["setup", "action"])
def test_stress_failures_propagate_and_always_restore_config(where):
    events = []
    def setup():
        events.append("setup")
        if where == "setup":
            raise RuntimeError("unexpected setup failure")
    def action():
        events.append("action")
        raise RuntimeError("unexpected model failure")
    with pytest.raises(RuntimeError, match="unexpected"):
        run_stress(setup, action, lambda: events.append("restored"))
    assert events[-1] == "restored"
