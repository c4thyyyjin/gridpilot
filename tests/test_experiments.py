"""Exercise the actual CLI from an empty output directory."""
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd


def test_quick_experiments_regenerate_outputs(tmp_path):
    script = Path(__file__).resolve().parents[1] / "experiments.py"
    result = subprocess.run(
        [sys.executable, str(script), "--quick", "--output-dir", str(tmp_path / "generated")], cwd=tmp_path,
        capture_output=True, text=True, timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (tmp_path / "results").exists()
    assert not (tmp_path / "figures").exists()
    tmp_path = tmp_path / "generated"
    expected_csv = {"headline", "pareto", "forecast_error", "battery",
                    "flat_tariff", "assumption_stress", "bias", "run_metrics", "feasibility", "paired_comparisons", "paired_seed_savings", "grid_cap", "grid_cap_economics", "battery_economics", "economics_runs"}
    assert {p.stem for p in (tmp_path / "results").glob("*.csv")} == expected_csv
    for name in expected_csv:
        frame = pd.read_csv(tmp_path / "results" / f"{name}.csv")
        assert not frame.empty
        assert not frame.astype(str).apply(
            lambda column: column.str.contains("failed:", regex=False)).any().any()
        # The first battery increment is intentionally undefined.
        numeric = frame.select_dtypes(include="number").drop(
            columns=["extra_gain_per_10MWh"], errors="ignore")
        # Blank gains intentionally suppress comparisons containing infeasible runs.
        assert not np.isinf(numeric.to_numpy()).any(), name
        if name in {"run_metrics", "feasibility"}:
            assert numeric.drop(columns=["grid_limit_mw"], errors="ignore").notna().all().all(), name
            assert (frame.grid_limit_mw.isna() == (frame.grid_limit_label == "uncapped")).all()
    headline = pd.read_csv(tmp_path / "results" / "headline.csv", index_col=0)
    assert headline.loc["baseline", "status"] == "feasible"
    assert headline.loc["MPC", "status"] == "feasible"
    assert headline.loc["MPC", "objective_gain_%"] > 0
    assert headline.loc["baseline-fc", "status"] == "contains_infeasible_runs"
    assert np.isnan(headline.loc["baseline-fc", "objective_gain_%"])
    assert np.isnan(headline.loc["open-loop", "objective_gain_%"])
    raw = pd.read_csv(tmp_path / "results" / "run_metrics.csv")
    assert {"status", "penalized_objective", "unmet_job_mwh", "grid_overflow_mwh",
            "fallback_hours", "fallback_hour_indices"} <= set(raw.columns)
    assert not raw[(raw.batch == 0) & (raw.method == "MPC") & ~raw.feasible].shape[0]
    stats = pd.read_csv(tmp_path / "results" / "paired_comparisons.csv")
    paired = pd.read_csv(tmp_path / "results" / "paired_seed_savings.csv")
    assert set(stats.n_pairs) == {3}
    eligible = stats[stats.eligible]
    assert not eligible.empty
    assert eligible[["gain_pct_mean", "gain_pct_ci_low", "gain_pct_ci_high"]].notna().all().all()
    assert (eligible.gain_pct_ci_low <= eligible.gain_pct_mean).all()
    assert (eligible.gain_pct_ci_high >= eligible.gain_pct_mean).all()
    assert stats.loc[~stats.eligible, "gain_pct_mean"].isna().all()
    assert not paired.empty and not paired.duplicated(["batch", "method", "seed", "metric"]).any()
    diagnostics = pd.read_csv(tmp_path / "results" / "feasibility.csv")
    assert {"max_battery_violation", "runs_with_battery_violation", "max_fallback_hours",
            "total_grid_limit_violation_hours"} <= set(diagnostics.columns)
    assert "Paired 95% intervals" in (tmp_path / "results" / "RESULTS.md").read_text()
    cap = pd.read_csv(tmp_path / "results" / "grid_cap.csv")
    assert "uncapped" in set(cap.grid_limit_label)
    assert not cap.loc[cap.grid_limit_mw == 10, "comparison_eligible"].any()
    assert cap.loc[~cap.comparison_eligible, "cost_cny_delta_vs_uncapped"].isna().all()
    finance = pd.read_csv(tmp_path / "results" / "battery_economics.csv")
    assert set(finance.billing_basis) == {"contracted_capacity", "measured_peak"}
    reference = finance[finance.battery_mwh == 0]
    assert (reference.annual_net_saving_cny == 0).all()
    assert reference.simple_payback_years.isna().all()
    assert "ASSUMPTIONS, not vendor quotes" in (tmp_path / "results" / "RESULTS.md").read_text()
    assert "Blank gains mean ineligible" in (tmp_path / "results" / "RESULTS.md").read_text()
    assert (tmp_path / "results" / "RESULTS.md").stat().st_size > 0
    expected_figures = {"pareto", "forecast_error", "battery",
                        "assumption_stress", "schedule", "grid_cap", "battery_economics"}
    figures = list((tmp_path / "figures").glob("*.png"))
    assert {p.stem for p in figures} == expected_figures
    for path in figures:
        assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        assert path.stat().st_size > 1000
