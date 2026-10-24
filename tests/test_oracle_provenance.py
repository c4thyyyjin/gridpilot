from dataclasses import asdict
import copy
import json
import pandas as pd
import pytest
import config as C
import check_guarded_deadlines as D
from robustness import Policy
from test_robustness import toy


def test_saved_config_restores_types_and_caller_state(tmp_path,monkeypatch):
    original_energy=C.BATT_ENERGY_MWH;original_hours=copy.deepcopy(C.TOU_HOURS)
    (tmp_path/'manifest.json').write_text(json.dumps({'config_snapshot':{
        'BATT_ENERGY_MWH':4.,'TOU_HOURS':{'1':'peak'},'TRAIN_WINDOW_H':[3,5]}}))
    def inspect(_):
        assert C.BATT_ENERGY_MWH==4
        assert C.TOU_HOURS=={1:'peak'}
        assert C.TRAIN_WINDOW_H==(3,5)
        raise RuntimeError('intentional failure')
    monkeypatch.setattr(D,'_check',inspect)
    with pytest.raises(RuntimeError,match='intentional'):D.check(tmp_path)
    assert C.BATT_ENERGY_MWH==original_energy and C.TOU_HOURS==original_hours


def test_oracle_uses_saved_policy_and_forecasts(tmp_path,monkeypatch):
    meta={'config_snapshot':{},'forecast_error':.2,'lambda_cny_per_tonne':123,
          'grid_limit_mw':19,'profiles':{'typical':[2,3,4]},
          'policies':{'guarded_online':asdict(Policy(checkpoint_overhead_fraction=.2,ramp_mw_per_hour=1))}}
    (tmp_path/'manifest.json').write_text(json.dumps(meta))
    pd.DataFrame([dict(method='MPC',policy='guarded_online',feasible=False,seed=220,profile='typical')]).to_csv(tmp_path/'runs.csv',index=False)
    def generate(seed,forecast_error,screen_feasibility):
        assert seed==220 and forecast_error==.2 and not screen_feasibility
        return toy()
    def solve(sc,t,lam,remaining,soc,limit,**kwargs):
        assert lam==123 and limit==19
        assert (sc.inference_fc==16).all()
        assert kwargs['work_efficiency']==.8 and kwargs['ramp_mw_per_hour']==1
        return None,None,None,0,False
    monkeypatch.setattr(D,'make_scenario',generate);monkeypatch.setattr(D,'solve_window',solve)
    assert D.check(tmp_path).oracle_feasible.all()
