"""Post-hoc oracle diagnostic; never used by an online controller or savings test.

Reads study parameters (forecast error, lambda, grid limit, profiles) from the
saved manifest.json rather than current config defaults. This makes the oracle
check reproducible for new manifests with config_snapshot even if config.py
changes between runs. Legacy manifests without that snapshot require their
original config and are not protected against arbitrary config changes.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import config as C
from data import make_scenario
from mpc import solve_window
from robustness import Policy
from experiments import preserved_config


def check(output_dir):
    """Restore recorded configuration for diagnostics, then restore caller state."""
    manifest = json.loads((Path(output_dir) / 'manifest.json').read_text())
    with preserved_config():
        for name, value in manifest.get('config_snapshot', {}).items():
            if not name.isupper() or not hasattr(C, name):
                raise ValueError(f"unknown recorded config key: {name}")
            original = getattr(C, name)
            if isinstance(original, tuple):
                value = tuple(value)
            elif isinstance(original, dict) and original and all(isinstance(k, int) for k in original):
                value = {int(k): v for k,v in value.items()}
            setattr(C, name, value)
        return _check(output_dir)


def _check(output_dir):
    output = Path(output_dir)
    raw = pd.read_csv(output / 'runs.csv')
    manifest = json.loads((output / 'manifest.json').read_text())
    forecast_error = manifest['forecast_error']
    lam = manifest['lambda_cny_per_tonne']
    grid_limit = manifest['grid_limit_mw']
    profiles = manifest['profiles']
    failed = raw[(raw.method == 'MPC') & raw.policy.str.startswith('guarded') & ~raw.feasible]
    rows = []
    for row in failed.itertuples():
        sc = make_scenario(row.seed, forecast_error=forecast_error, screen_feasibility=False)
        solar, wind, inf = profiles[row.profile]
        sc.solar_fc = sc.solar_act * solar
        sc.wind_fc = sc.wind_act * wind
        sc.inference_fc = sc.inference_act * inf
        policy = Policy(**manifest['policies'][row.policy])
        *_, fallback = solve_window(
            sc, 0, lam, np.array([j.energy_mwh for j in sc.jobs]),
            C.BATT_SOC_START * C.BATT_ENERGY_MWH, grid_limit, nowcast=False,
            work_efficiency=policy.efficiency,
            ramp_mw_per_hour=policy.ramp_mw_per_hour)
        rows.append(dict(profile=row.profile, policy=row.policy, seed=row.seed,
                         oracle_feasible=not fallback and bool(
                             np.all(sc.inference_fc <= C.IT_CAPACITY_MW))))
    result = pd.DataFrame(rows, columns=['profile', 'policy', 'seed', 'oracle_feasible'])
    result.to_csv(output / 'deadline_oracle_check.csv', index=False)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('guarded_results'))
    args = parser.parse_args()
    result = check(args.output_dir)
    print(f'{int(result.oracle_feasible.sum())}/{len(result)} failed guarded MPC cases are oracle-feasible')
