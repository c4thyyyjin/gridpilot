import copy
from pathlib import Path
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

import config as C
import experiments
from plotting import plot_pareto


def config_snapshot():
    return {k: copy.deepcopy(v) for k, v in vars(C).items() if k.isupper()}


def test_import_has_no_outputs_argparse_or_plotting(tmp_path):
    project = str(Path(experiments.__file__).resolve().parent)
    code = f'''
import sys
sys.path.insert(0, {project!r})
sys.argv = ["unrelated-program", "--this-is-not-an-experiments-argument"]
import experiments
assert "matplotlib.pyplot" not in sys.modules
from pathlib import Path
assert list(Path.cwd().iterdir()) == []
'''
    p = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr


@pytest.mark.parametrize("fail", [False, True])
def test_runner_restores_config_styles_cwd_and_caller_figures(monkeypatch, tmp_path, fail):
    before = config_snapshot()
    cwd = Path.cwd()
    existing = plt.figure()
    original_dpi = plt.rcParams["figure.dpi"]
    paths = []
    def fake_run(quick, output_dir):
        assert C.LAMBDA_DEFAULT == 321
        paths.append(output_dir)
        C.BATT_ENERGY_MWH = 999
        C.PRICE_LEVELS["new"] = 999
        C.LAMBDA_SWEEP.append(999)
        C.TEMPORARY_EXPERIMENT_KEY = 123
        plt.rcParams["figure.dpi"] = 12
        plt.figure()
        if fail:
            raise RuntimeError("injected experiment failure")
    monkeypatch.setattr(experiments, "_run_experiments", fake_run)
    try:
        if fail:
            with pytest.raises(RuntimeError, match="injected"):
                experiments.run_experiments(True, tmp_path, {"LAMBDA_DEFAULT": 321})
        else:
            experiments.run_experiments(True, tmp_path, {"LAMBDA_DEFAULT": 321})
        assert config_snapshot() == before
        assert paths == [tmp_path.resolve()]
        assert Path.cwd() == cwd
        assert plt.rcParams["figure.dpi"] == original_dpi
        assert plt.get_fignums() == [existing.number]
    finally:
        plt.close(existing)


def test_unknown_config_is_rejected_and_restored(tmp_path):
    before = config_snapshot()
    with pytest.raises(ValueError, match="unknown config"):
        experiments.run_experiments(output_dir=tmp_path,
                                    config_overrides={"LAMBDA_DEFAULT": 321, "TYPO_CONFIG": 1})
    assert config_snapshot() == before
    assert not list(tmp_path.iterdir())


def test_main_routes_cli_options_without_running(monkeypatch, tmp_path):
    config = tmp_path / "settings.json"
    config.write_text('{"LAMBDA_DEFAULT": 321}')
    calls = []
    monkeypatch.setattr(experiments, "run_experiments", lambda **kw: calls.append(kw))
    experiments.main(["--quick", "--output-dir", str(tmp_path / "outputs"), "--config", str(config)])
    assert calls == [dict(quick=True, output_dir=tmp_path / "outputs",
                          config_overrides={"LAMBDA_DEFAULT": 321})]


def test_pareto_labels_are_grouped_separate_and_complete(tmp_path):
    frame = pd.DataFrame({"lambda": [0,100,500,1000,2000,5000,10000,20000],
                          "co2": [421,409,409,408.9,405,398,394,392],
                          "cost": [533000,533200,533200,533300,539000,561000,591000,610000],
                          "base_co2": [441]*8, "base_cost": [679000]*8})
    fig, ax = plot_pareto(frame, tmp_path / "pareto.png")
    try:
        labels = ax.texts
        assert len(labels) < len(frame)
        assert any("100, 500, 1000" in a.get_text() for a in labels)
        fig.canvas.draw()
        boxes = [a.get_bbox_patch().get_window_extent(fig.canvas.get_renderer()) for a in labels]
        for i, box in enumerate(boxes):
            assert all(not box.overlaps(other) for other in boxes[i + 1:])
        x, y = ax.lines[0].get_data()
        np.testing.assert_allclose(x, frame.co2)
        np.testing.assert_allclose(y, frame.cost / 1000)
        assert (tmp_path / "pareto.png").stat().st_size > 1000
    finally:
        plt.close(fig)
