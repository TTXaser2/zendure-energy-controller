"""A meter that never supplied a fresh grid sample still needs a stable event."""
import time
from unittest.mock import patch
from operational_events import OperationalEventJournal
from state import ControllerState


def test_missing_first_grid_observation_has_grace_hysteresis_and_recovery(tmp_path):
    s=ControllerState()
    s.startup_epoch=time.time()-60
    cfg={'OPERATIONAL_EVENTS_DB_PATH':str(tmp_path/'events.sqlite3'),
         'GRID_METER_SOURCE':'sma_energy_meter_udp',
         'SMA_ENERGY_METER_STALE_TIMEOUT_SECONDS':15}
    journal=OperationalEventJournal(lambda:cfg,s)
    db=journal._connect()
    try:
        snap={'current_mode':'HOLD','mqtt_connected':True,
              'grid_power_age_seconds':None,'grid_power_valid':False,'grid_power_validity_reason':'GRID_UNKNOWN'}
        with patch('operational_events.time.monotonic',return_value=100):journal._observe(db,snap)
        with patch('operational_events.time.monotonic',return_value=107):journal._observe(db,snap)
        rows=db.execute("SELECT status,detail FROM operational_events WHERE event_type='grid_telemetry_stale'").fetchall()
        assert len(rows)==1 and rows[0][0]=='open'
        assert 'GRID_NEVER_RECEIVED' in rows[0][1]
        with patch('operational_events.time.monotonic',return_value=109):journal._observe(db,snap)
        assert db.execute("SELECT COUNT(*) FROM operational_events WHERE event_type='grid_telemetry_stale'").fetchone()[0]==1
        healthy=dict(snap,grid_power_age_seconds=1,grid_power_valid=True,grid_power_validity_reason='OK')
        with patch('operational_events.time.monotonic',return_value=111):journal._observe(db,healthy)
        with patch('operational_events.time.monotonic',return_value=116):journal._observe(db,healthy)
        assert db.execute("SELECT status FROM operational_events WHERE event_type='grid_telemetry_stale'").fetchone()[0]=='resolved'
    finally: db.close()


def test_missing_sample_during_initial_grace_does_not_open_event(tmp_path):
    state=ControllerState()
    cfg={'OPERATIONAL_EVENTS_DB_PATH':str(tmp_path/'events.sqlite3'),
         'GRID_METER_SOURCE':'sma_energy_meter_udp', 'SMA_ENERGY_METER_STALE_TIMEOUT_SECONDS':15}
    journal=OperationalEventJournal(lambda:cfg,state)
    db=journal._connect()
    try:
        snap={'current_mode':'AUTO','mqtt_connected':True,'grid_power_age_seconds':None,'grid_power_valid':False}
        with patch('operational_events.time.monotonic',return_value=100):journal._observe(db,snap)
        with patch('operational_events.time.monotonic',return_value=120):journal._observe(db,snap)
        assert db.execute("SELECT COUNT(*) FROM operational_events WHERE event_type='grid_telemetry_stale'").fetchone()[0]==0
    finally: db.close()
