import json
import numpy as np
import pandas as pd
import pytest

import robustness_experiments as R
from test_robustness import toy


def test_validation_writes_all_outcomes_and_manifest(monkeypatch,tmp_path):
    calls=[]
    def generate(seed,forecast_error,screen_feasibility):
        assert not screen_feasibility
        calls.append(seed)
        sc=toy();sc.seed=seed;sc.generation_attempts=1;sc.generation_screened=False
        return sc
    monkeypatch.setattr(R,"make_scenario",generate)
    raw,summary,stats=R.run_validation(tmp_path,seeds=[100,101],quick=True)
    assert len(raw)==2*3*2*2
    assert set(raw.source)=={"synthetic_unscreened"}
    assert not raw.duplicated(["batch","method","seed"]).any()
    assert (summary.feasible_runs+summary.degraded_runs+summary.overload_runs==summary.runs).all()
    assert stats.loc[~stats.eligible,"gain_pct_mean"].isna().all()
    assert not np.isinf(raw.select_dtypes("number").to_numpy()).any()
    manifest=json.loads((tmp_path/"manifest.json").read_text())
    assert manifest["seeds"]==[100,101] and not manifest["generator_feasibility_screen"]
    assert (tmp_path/"decision_traces.json").exists()
    assert "No real operational traces" in (tmp_path/"RESULTS.md").read_text()
    assert len(list(tmp_path.glob("*.csv")))==4


@pytest.mark.parametrize("seeds", [[0],[42],[100,100],[]])
def test_validation_rejects_development_or_duplicate_seeds(tmp_path,seeds):
    with pytest.raises(ValueError):R.run_validation(tmp_path,seeds=seeds,quick=True)
