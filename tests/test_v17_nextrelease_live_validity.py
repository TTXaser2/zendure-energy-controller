"""1-Hz data-path must fail closed on invalid/unavailable telemetry."""
import time
from types import SimpleNamespace
from unittest.mock import patch
from state import ControllerState
from live_status import build_live_status


def test_live_snapshot_never_raises_on_none_or_nonnumeric_grid():
    state = ControllerState()
    state.raw_grid_power = None
    assert build_live_status({'GRID_METER_SOURCE':'shelly_http'},state)['grid']['power_w'] is None
    state.raw_grid_power = 'garbage'
    assert build_live_status({'GRID_METER_SOURCE':'shelly_http'},state)['grid']['power_w'] is None


def test_grid_nan_inf_future_timestamp_not_fresh():
    state = ControllerState()
    now = time.time()
    for raw in (float('nan'),float('inf'),float('-inf')):
        source=SimpleNamespace(snapshot=lambda:SimpleNamespace(last_power_w=raw,last_received_epoch=now))
        d=build_live_status({'GRID_METER_SOURCE':'sma_energy_meter_udp'},state,sma_energy_meter_client=source)
        assert d['grid']['power_w'] is None and d['grid']['fresh'] is False
    future=SimpleNamespace(snapshot=lambda:SimpleNamespace(last_power_w=100,last_received_epoch=now+1000))
    d=build_live_status({'GRID_METER_SOURCE':'sma_energy_meter_udp'},state,sma_energy_meter_client=future)
    assert d['grid']['power_w'] is None and d['grid']['fresh'] is False


def test_primary_source_switch_never_exposes_previous_profile_sample():
    state = ControllerState()
    with state.lock:
        state.sma_battery_power=-250
        state.sma_battery_soc=66
        state.last_sma_battery_update_epoch=time.time()
        state.primary_storage_source_profile='modbus_template'
    d=build_live_status({'SECOND_BATTERY_INTEGRATION_ENABLED':True,'SECOND_BATTERY_SOURCE_PROFILE':'evcc_standard'},state)
    assert not d['primary']['fresh']
    assert d['primary']['power_w'] is None and d['primary']['soc_percent'] is None
    assert not d['primary']['source_matches_config']


def test_zendure_soc_is_independent_of_power_age():
    state=ControllerState()
    with state.lock:
        state.actual_zendure_system_signed_power=230
        state.last_zendure_power_update_epoch=time.time()-80
        state.battery_soc=63
        state.last_soc_update_epoch=time.time()
    d=build_live_status({},state)
    assert d['zendure']['power_w'] is None
    assert d['zendure']['soc_percent']==63
    assert d['zendure']['soc_fresh']
