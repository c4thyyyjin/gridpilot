"""Feasibility-aware aggregation shared by experiments and tests."""
import numpy as np
import pandas as pd

METRICS = ["objective", "penalized_objective", "cost_cny", "co2_t",
           "green_share_pct", "curtailed_mwh", "peak_grid_mw", "sla_violations",
           "capacity_violation_hours", "grid_limit_violation_hours",
           "battery_violation", "unmet_job_mwh", "grid_overflow_mwh",
           "inference_overload_hours", "fallback_hours"]


def aggregate(rows):
    frame = pd.DataFrame(rows)
    result = frame[METRICS].mean().to_dict()
    result.update(runs=len(frame), feasible_runs=int(frame.feasible.sum()),
                  degraded_runs=int((frame.status == "degraded").sum()),
                  overload_runs=int((frame.status == "exogenous_overload").sum()))
    result["all_feasible"] = result["feasible_runs"] == result["runs"]
    result["status"] = "feasible" if result["all_feasible"] else "contains_infeasible_runs"
    for key in ("unmet_job_mwh", "grid_overflow_mwh", "capacity_violation_hours",
                "grid_limit_violation_hours", "sla_violations", "battery_violation",
                "inference_overload_hours", "fallback_hours", "peak_grid_mw"):
        result[f"max_{key}"] = frame[key].max()
        if key != "peak_grid_mw":
            result[f"total_{key}"] = frame[key].sum()
            result[f"runs_with_{key}"] = int((frame[key] > 0).sum())
    return result


def feasible_gain(frame, column="objective"):
    """No ordinary savings claim unless every compared run is feasible."""
    base = frame.loc["baseline", column]
    valid = frame.all_feasible.astype(bool) & bool(frame.loc["baseline", "all_feasible"])
    return (100 * (1 - frame[column] / base)).where(valid & (base != 0), np.nan)


def paired_comparisons(rows, confidence=0.95):
    """Student-t intervals on within-seed savings; never drop failed pairs.

    Returns (summaries, individual pairs). Intervals describe uncertainty across
    generated seeds at one parameter setting, not uncertainty about real sites.
    """
    from scipy.stats import t as student_t

    if not 0 < confidence < 1:
        raise ValueError("confidence must be between zero and one")
    frame = pd.DataFrame(rows)
    if frame.duplicated(["batch", "method", "seed"]).any():
        raise ValueError("duplicate batch/method/seed")
    summaries, pairs = [], []

    def estimate(values):
        values = np.asarray(values, float)
        mean = float(values.mean())
        if len(values) < 2:
            return mean, np.nan, np.nan
        margin = float(student_t.ppf((1 + confidence) / 2, len(values) - 1)
                       * values.std(ddof=1) / np.sqrt(len(values)))
        return mean, mean - margin, mean + margin

    for batch, group in frame.groupby("batch", sort=False):
        baseline = group[group.method == "baseline"].set_index("seed")
        if baseline.empty:
            raise ValueError("paired comparisons require a baseline in every batch")
        for method, candidate in group.groupby("method", sort=False):
            if method == "baseline":
                continue
            candidate = candidate.set_index("seed")
            if set(candidate.index) != set(baseline.index):
                raise ValueError("paired methods must have identical seed sets")
            candidate = candidate.loc[baseline.index]
            valid = baseline.feasible.astype(bool) & candidate.feasible.astype(bool)
            all_valid = bool(valid.all())
            for metric in ("objective", "cost_cny", "co2_t"):
                base = baseline[metric].to_numpy(float)
                actual = candidate[metric].to_numpy(float)
                if not (np.isfinite(base).all() and np.isfinite(actual).all()):
                    raise ValueError("paired metrics must be finite")
                delta = base - actual
                pct = np.divide(100 * delta, base, out=np.full(len(base), np.nan), where=base != 0)
                for i, seed in enumerate(baseline.index):
                    pairs.append({"batch": batch, "method": method, "seed": seed,
                                  "metric": metric, "baseline_value": base[i],
                                  "method_value": actual[i], "pair_feasible": bool(valid.iloc[i]),
                                  "baseline_status": baseline.loc[seed, "status"],
                                  "method_status": candidate.loc[seed, "status"],
                                  "saving": delta[i] if valid.iloc[i] else np.nan,
                                  "gain_pct": pct[i] if valid.iloc[i] else np.nan})
                summary = {"batch": batch, "method": method, "metric": metric,
                           "n_pairs": len(base), "n_feasible_pairs": int(valid.sum()),
                           "eligible": all_valid, "confidence": confidence,
                           "status": "feasible" if all_valid else "infeasible_runs",
                           "ci_status": "available" if all_valid and len(base) >= 2 else
                                        "insufficient_pairs" if all_valid else "ineligible",
                           "percentage_status": "defined" if np.all(base != 0) else "zero_baseline"}
                for prefix, values in (("saving", delta), ("gain_pct", pct)):
                    estimated = estimate(values) if all_valid and np.isfinite(values).all() else (np.nan,) * 3
                    for suffix, value in zip(("mean", "ci_low", "ci_high"), estimated):
                        summary[f"{prefix}_{suffix}"] = value
                summaries.append(summary)
    return pd.DataFrame(summaries), pd.DataFrame(pairs)


def run_stress(setup, action, teardown):
    """Restore config even if setup/action fails; propagate unexpected errors."""
    try:
        setup()
        return action()
    finally:
        teardown()
