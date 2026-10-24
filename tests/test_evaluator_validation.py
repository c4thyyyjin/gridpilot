import copy
import numpy as np
import pytest
import config as C
from data import Scenario, make_scenario
from baseline import baseline_observed
from evaluate import Schedule, evaluate


@pytest.mark.parametrize('field',['job_power','charge','discharge'])
@pytest.mark.parametrize('value',[np.nan,np.inf,-np.inf])
def test_nonfinite_schedule_rejected(field,value):
    sc=make_scenario();sch=baseline_observed(sc)
    getattr(sch,field).flat[0]=value
    with pytest.raises(ValueError,match='non-finite'):evaluate(sc,sch)


@pytest.mark.parametrize('field',['charge','discharge'])
def test_negative_battery_rejected(field):
    sc=make_scenario();sch=baseline_observed(sc);getattr(sch,field)[0]=-1
    with pytest.raises(ValueError,match='negative'):evaluate(sc,sch)


@pytest.mark.parametrize('field',['job_power','charge','discharge'])
def test_schedule_shapes_rejected(field):
    sc=make_scenario();sch=baseline_observed(sc);setattr(sch,field,np.zeros(1))
    with pytest.raises(ValueError,match='shape'):evaluate(sc,sch)


@pytest.mark.parametrize('field',['price','grid_co2','solar_act','wind_act','inference_act'])
def test_nonfinite_scenario_rejected(field):
    sc=make_scenario();sch=baseline_observed(sc);getattr(sc,field)[0]=np.nan
    with pytest.raises(ValueError,match=field):evaluate(sc,sch)


def case(load,green):
    load=np.array(load,float);green=np.array(green,float);z=np.zeros(len(load))
    return Scenario(len(load),np.full(len(load),.4),np.full(len(load),.5),
                    green.copy(),z.copy(),green.copy(),z.copy(),
                    load/C.PUE,load/C.PUE,[])


def test_green_storage_mixing_includes_discharge_losses(monkeypatch):
    monkeypatch.setattr(C,'BATT_ENERGY_MWH',4.)
    # 2 MWh initially brown; add 1 MWh green after charging loss.
    # Mixed green fraction is 1/3; withdraw 1 MWh stored, delivering .95.
    sc=case([1.,.95],[1+1/.95,0.]);sch=Schedule.empty(0,2)
    sch.charge[0]=1/.95;sch.discharge[1]=.95
    m=evaluate(sc,sch)
    assert m['feasible']
    assert m['green_served_stored_mwh']==pytest.approx(.95/3)
    assert m['green_served_mwh']==pytest.approx(1+.95/3)
    assert 0<=m['green_share_pct']<=100


def test_repeated_withdrawals_do_not_create_green_energy(monkeypatch):
    monkeypatch.setattr(C,'BATT_ENERGY_MWH',4.)
    sc=case([1.,.475,.475],[1+1/.95,0.,0.]);sch=Schedule.empty(0,3)
    sch.charge[0]=1/.95;sch.discharge[1:]=.475
    m=evaluate(sc,sch)
    assert m['feasible']
    assert m['green_served_stored_mwh']==pytest.approx(.95/3)


def test_direct_green_and_zero_load_have_defined_units(monkeypatch):
    monkeypatch.setattr(C,'DT_H',.5)
    sc=case([2.,2.],[2.,2.]);m=evaluate(sc,Schedule.empty(0,2))
    assert m['green_served_direct_mwh']==pytest.approx(2)
    assert m['green_share_pct']==pytest.approx(100)
    sc=case([0.,0.],[2.,2.]);m=evaluate(sc,Schedule.empty(0,2))
    assert m['green_share_pct']==0 and m['green_served_mwh']==0


def test_generator_rejects_subhourly_even_unscreened(monkeypatch):
    monkeypatch.setattr(C,'DT_H',.5)
    with pytest.raises(ValueError,match='hourly'):make_scenario(screen_feasibility=False)
