"""Focussed S3 and independent 1-Hz telemetry contract tests (dev checkpoint)."""
import sys
import time
import types
from unittest.mock import patch

import pytest

if 'paho' not in sys.modules:
    paho = types.ModuleType('paho')
    pm = types.ModuleType('paho.mqtt')
    pc = types.ModuleType('paho.mqtt.client')
    pc.CallbackAPIVersion = types.SimpleNamespace(VERSION2=object())
    pc.Client = lambda *args, **kwargs: types.SimpleNamespace(
        on_message=None,on_connect=None,on_disconnect=None,
        username_pw_set=lambda *a,**k:None,
        connect=lambda *a,**k:None,loop_start=lambda *a,**k:None,
        subscribe=lambda *a,**k:None,publish=lambda *a,**k:types.SimpleNamespace(rc=0),
    )
    sys.modules.update({'paho':paho,'paho.mqtt':pm,'paho.mqtt.client':pc})

from controller_logic import ZendureController
from state import ControllerState
from settings_registry import SETTINGS_BY_KEY, SurfaceState
from settings_validation import ValidationContext, validate_candidate
from live_status import build_live_status


def _s3_controller():
    # The functions are pure or depend only on supplied cfg and profile clock.
    return object.__new__(ZendureController)


def test_legacy_clock_defaults_differential():
    ctrl = _s3_controller()
    cfg = {}
    expected = [(569,'default',0.50,30),(570,'morning',0.60,60),
                (689,'morning',0.60,60),(690,'midday',0.50,30),
                (869,'midday',0.50,30),(870,'afternoon',0.35,15),
                (1079,'afternoon',0.35,15),(1080,'default',0.50,30)]
    for minute,name,share,confirm in expected:
        with patch.object(ctrl,'_profile_clock_minutes',return_value=minute):
            p=ctrl._harvest_time_profile(cfg)
        assert (p['name'],p['share'],p['entry_confirm_s'])==(name,share,confirm)


def test_configurable_profile_and_disabled_legacy():
    ctrl = _s3_controller()
    cfg={'HARVEST_HIGH_SMA_SOC_PROFILE_START_TIME':'07:20',
         'HARVEST_HIGH_SMA_SOC_PROFILE_MIDDAY_START_TIME':'10:30',
         'HARVEST_HIGH_SMA_SOC_PROFILE_AFTERNOON_START_TIME':'13:00',
         'HARVEST_HIGH_SMA_SOC_PROFILE_END_TIME':'16:30',
         'HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_MORNING_SECONDS':42}
    with patch.object(ctrl,'_profile_clock_minutes',return_value=445):
        assert ctrl._harvest_time_profile(cfg)['entry_confirm_s']==42
    cfg['HARVEST_HIGH_SMA_SOC_TIME_PROFILE_ENABLED']=False
    with patch.object(ctrl,'_profile_clock_minutes',return_value=445):
        assert ctrl._harvest_time_profile(cfg)['name']=='default'


def test_season_opt_in_only_and_cyclic_calendar():
    ctrl = _s3_controller()
    assert ctrl._s3_season_policy({'HARVEST_SEASON_MODE':'sma_priority'})['effective']=='legacy_parallel'
    assert ctrl._s3_season_policy({'HARVEST_SEASON_POLICY_ENABLED':True,'HARVEST_SEASON_MODE':'sma_priority'})['effective']=='sma_priority'
    assert ctrl._s3_calendar_parallel('12-31','11-01','02-15')
    assert ctrl._s3_calendar_parallel('01-01','11-01','02-15')
    assert not ctrl._s3_calendar_parallel('10-15','11-01','02-15')
    assert ctrl._s3_calendar_parallel('02-29','11-01','03-01')
    assert ctrl._s3_calendar_parallel('01-01','01-01','01-01')


def test_registry_operational_with_safe_defaults():
    for key in ('HARVEST_SEASON_MODE','HARVEST_SEASON_POLICY_ENABLED',
                'HARVEST_HIGH_SMA_SOC_PROFILE_START_TIME',
                'HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_MORNING_SECONDS'):
        assert SETTINGS_BY_KEY[key].surface_state is SurfaceState.OPERATIONAL
    assert SETTINGS_BY_KEY['HARVEST_SEASON_POLICY_ENABLED'].default_new_install is False


def test_calendar_validation_wrap_and_missing():
    cfg={'HARVEST_SEASON_POLICY_ENABLED':True,'HARVEST_SEASON_MODE':'calendar',
         'HARVEST_SEASON_PARALLEL_START_MM_DD':'11-01',
         'HARVEST_SEASON_PARALLEL_END_MM_DD':'02-15'}
    issues=validate_candidate(cfg,ValidationContext())
    assert 'VAL-014' not in {x.code for x in issues}
    cfg['HARVEST_SEASON_PARALLEL_START_MM_DD']='02-29'
    assert 'VAL-014' in {x.code for x in validate_candidate(cfg,ValidationContext())}
    cfg['HARVEST_SEASON_POLICY_ENABLED']=False
    assert 'VAL-014' not in {x.code for x in validate_candidate(cfg,ValidationContext())}


def test_live_source_preferred_even_when_controller_grid_frozen():
    s=ControllerState()
    now=time.time()
    with s.lock:
        s.raw_grid_power=101
        s.grid_power_sample_epoch=now-3700
        s.sma_battery_power=-400
        s.sma_battery_soc=65
        s.last_sma_battery_update_epoch=now
        s.actual_zendure_system_signed_power=320
        s.last_zendure_power_update_epoch=now
        s.battery_soc=48
        s.last_soc_update_epoch=now
    meter=types.SimpleNamespace(snapshot=lambda:types.SimpleNamespace(last_power_w=-1050,last_received_epoch=now))
    data=build_live_status({'GRID_METER_SOURCE':'sma_energy_meter_udp',
                            'SECOND_BATTERY_INTEGRATION_ENABLED':True,
                            'SECOND_BATTERY_SOURCE_PROFILE':'modbus_template'},s,sma_energy_meter_client=meter)
    assert data['grid']['power_w']==-1050
    assert data['grid']['measurement_path']=='sma_udp_receiver'
    assert data['grid']['controller_sample_age_s']>3600
    assert data['primary']['power_w']==400
    assert data['zendure']['power_w']==320


def test_live_stale_never_displays_old_sample_as_fresh():
    s=ControllerState()
    s.grid_power_sample_epoch=time.time()-60
    s.raw_grid_power=560
    data=build_live_status({'GRID_METER_SOURCE':'shelly_http','SHELLY_STALE_TIMEOUT_SECONDS':15},s)
    assert data['grid']['power_w'] is None and data['grid']['last_value_w']==560


def test_grid_event_opens_and_resolves_independent_of_control_loop(tmp_path):
    from operational_events import OperationalEventJournal
    cfg={'OPERATIONAL_EVENTS_DB_PATH':str(tmp_path/'events.sqlite3'),
         'GRID_METER_SOURCE':'sma_energy_meter_udp',
         'SMA_ENERGY_METER_STALE_TIMEOUT_SECONDS':15}
    meter=types.SimpleNamespace(snapshot=lambda:types.SimpleNamespace(last_received_epoch=time.time()))
    journal=OperationalEventJournal(lambda:cfg,ControllerState(),sma_energy_meter_client=meter)
    connection=journal._connect()
    try:
        snap={'current_mode':'HOLD','mqtt_connected':True,
              'grid_power_age_seconds':240,'grid_power_validity_reason':'GRID_STALE'}
        with patch('operational_events.time.monotonic',return_value=100):
            journal._observe(connection,snap)
        with patch('operational_events.time.monotonic',return_value=108):
            journal._observe(connection,snap)
        opened=connection.execute('SELECT title, detail,status FROM operational_events WHERE event_type="grid_telemetry_stale"').fetchall()
        assert len(opened)==1 and opened[0][2]=='open'
        assert 'CONTROLLER_PROCESSING_STALE' in opened[0][1]
        recovered=dict(snap,grid_power_age_seconds=0,grid_power_validity_reason='OK')
        with patch('operational_events.time.monotonic',return_value=109):
            journal._observe(connection,recovered)
        with patch('operational_events.time.monotonic',return_value=114):
            journal._observe(connection,recovered)
        final=connection.execute('SELECT status FROM operational_events WHERE event_type="grid_telemetry_stale"').fetchone()
        assert final[0]=='resolved'
    finally:
        connection.close()


def test_sma_extreme_value_is_never_exposed_as_live_power():
    s=ControllerState()
    now=time.time()
    meter=types.SimpleNamespace(snapshot=lambda:types.SimpleNamespace(last_power_w=-1730098.8,last_received_epoch=now))
    data=build_live_status({'GRID_METER_SOURCE':'sma_energy_meter_udp','GRID_POWER_PLAUSIBILITY_MAX_ABS_W':30000},s,sma_energy_meter_client=meter)
    assert data['grid']['power_w'] is None
    assert data['grid']['plausible'] is False


def test_shelly_live_worker_values_override_stale_controller_snapshot():
    s=ControllerState()
    now=time.time()
    with s.lock:
        s.raw_grid_power=800
        s.grid_power_sample_epoch=now-120
    fake=types.SimpleNamespace(snapshot=lambda:types.SimpleNamespace(last_power_w=-325,last_received_epoch=now))
    d=build_live_status({'GRID_METER_SOURCE':'shelly_http'},s,shelly_sampler=fake)
    assert d['grid']['power_w']==-325
    assert d['grid']['measurement_path']=='shelly_live_worker'
    assert d['grid']['controller_sample_age_s']>100
