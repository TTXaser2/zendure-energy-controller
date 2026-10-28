# SPDX-License-Identifier: AGPL-3.0-or-later
"""CP18: only real emergency command-effect failure opens durable incident."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from contextlib import closing
from unittest.mock import patch

from battery_care_policy import CareEpisode
from command_lifecycle import DesiredCommandBatch, INTENT_CHARGE
from operational_events import OperationalEventJournal
from tests import test_battery_care_grid_live_dispatch as grid_fixture


class CareCommandIncidentBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def make(self):
        helper = grid_fixture.GridCareDispatchTests()
        ctrl, cfg, state, mqtt = helper.make()
        ctrl.config_manager.cfg['OPERATIONAL_EVENTS_DB_PATH'] = str(Path(self.temp.name) / 'events.sqlite3')
        ctrl._care_grid_episode = CareEpisode(active_level=3, target_reserve_soc=40)
        ctrl._care_grid_live_active = True
        ctrl._care_emergency_episode_generation = 1
        ctrl._care_emergency_episode_live = True
        ctrl._desired_command_batch = DesiredCommandBatch(
            sequence_id=10, intent=INTENT_CHARGE, smart_mode=1,
            ac_mode='Input mode', input_limit_w=250, output_limit_w=0,
            signed_target_w=250, reason='BATTERY_CARE_EMERGENCY',
            safety_relevant=False, created_epoch=time.time(),
        )
        return ctrl, state

    def test_only_confirmed_emergency_effect_failure_sets_snapshot_incident(self):
        ctrl, state = self.make()
        self.assertFalse(state.snapshot()['care_emergency_failure_confirmed'])
        ctrl._mark_mismatch(target=250, actual_text='+0 W', elapsed_s=120, tolerance_w=30)
        snap = state.snapshot()
        self.assertTrue(snap['care_emergency_failure_confirmed'])
        self.assertEqual(40, snap['care_emergency_incident_reserve_soc'])
        self.assertEqual('COMMAND_MISMATCH_CONFIRMED', state.command_effect_category)
        self.assertTrue(snap['care_emergency_incident_persisted'])
        event_id = snap['care_emergency_failure_event_id']
        self.assertTrue(event_id)
        ctrl._mark_mismatch(target=250, actual_text='+0 W', elapsed_s=130, tolerance_w=30)
        self.assertEqual(event_id, state.snapshot()['care_emergency_failure_event_id'])
        # A new real episode after complete exit may produce a new identity.
        ctrl._care_grid_episode = CareEpisode()
        ctrl._battery_care_persist_episode = lambda ep: None
        ctrl._care_emergency_episode_generation += 1
        ctrl._care_grid_episode = CareEpisode(active_level=3, target_reserve_soc=40)
        ctrl._mark_mismatch(target=250, actual_text='+0 W', elapsed_s=180, tolerance_w=30)
        self.assertNotEqual(event_id, state.snapshot()['care_emergency_failure_event_id'])

    def test_no_false_incident_non_emergency_neutral_or_stale_command(self):
        ctrl, state = self.make()
        state.command_neutralization_since_epoch = time.time() - 120
        ctrl._mark_mismatch(target=0, actual_text='+100 W', elapsed_s=120,
                            tolerance_w=30, neutral=True)
        self.assertFalse(state.care_emergency_failure_confirmed)
        ctrl._desired_command_batch = ctrl._desired_command_batch.__class__(
            **{**ctrl._desired_command_batch.__dict__, 'reason':'BATTERY_CARE_GRID_MAINTENANCE'})
        ctrl._mark_mismatch(target=250, actual_text='+0 W', elapsed_s=120,tolerance_w=30)
        self.assertFalse(state.care_emergency_failure_confirmed)
        ctrl._desired_command_batch = ctrl._desired_command_batch.__class__(
            **{**ctrl._desired_command_batch.__dict__, 'reason':'BATTERY_CARE_EMERGENCY'})
        ctrl._care_grid_live_active = False
        ctrl._mark_mismatch(target=250, actual_text='+0 W', elapsed_s=120,tolerance_w=30)
        self.assertFalse(state.care_emergency_failure_confirmed)

    def test_source_id_not_derived_from_ui_polling_and_physical_not_publish(self):
        _, state = self.make()
        now = time.time()
        state.battery_soc = 9
        state.last_soc_update_epoch = now - 1
        state.soc_fresh = True
        state.soc_valid = True
        a = state.snapshot()
        b = state.snapshot()
        self.assertEqual(a['care_soc_sample_id'], b['care_soc_sample_id'])
        self.assertFalse(a['care_physical_charge_confirmed'])
        state.zendure_power_observation_direction = 'CHARGE'
        state.zendure_power_observation_confidence = 'HIGH'
        state.zendure_power_observation_signed_w = 120
        state.zendure_power_observation_updated_epoch = now - 1
        state.zendure_battery_charge_power_w = 120
        state.actual_zendure_output_pack_update_epoch = now - 1
        self.assertTrue(state.snapshot()['care_physical_charge_confirmed'])
        state.zendure_power_observation_updated_epoch = now - 100
        self.assertFalse(state.snapshot()['care_physical_charge_confirmed'])
        state.zendure_power_observation_updated_epoch = now - 1
        state.actual_zendure_output_pack_update_epoch = now - 100
        self.assertFalse(state.snapshot()['care_physical_charge_confirmed'])
        state.last_soc_update_epoch = now - 1000
        self.assertFalse(state.snapshot()['care_soc_fresh'])

    def test_real_controller_state_to_existing_persistent_journal_restart_and_recovery(self):
        ctrl, state = self.make()
        ctrl._mark_mismatch(target=250, actual_text='+0 W', elapsed_s=120,tolerance_w=30)
        state.battery_soc = 9
        state.last_soc_update_epoch = time.time()
        state.soc_fresh = True
        state.soc_valid = True
        with tempfile.TemporaryDirectory() as td:
            path = str(Path(td)/'events.db')
            j = OperationalEventJournal(lambda: {'OPERATIONAL_EVENTS_DB_PATH': path},state)
            with closing(j._connect()) as conn:
                j._observe_battery_care_incident(conn, state.snapshot())
                row = conn.execute('SELECT status,detail_json FROM operational_events WHERE event_type=?',
                                   ('battery_care_emergency_failure',)).fetchone()
                self.assertEqual('open',row[0])
                self.assertEqual(40, json.loads(row[1])['incident_reserve_soc'])
                # A restart may drop volatile failure signal, but never DB row.
                j = OperationalEventJournal(lambda: {'OPERATIONAL_EVENTS_DB_PATH': path},state)
                state.care_emergency_failure_confirmed = False
                state.battery_soc = 40
                state.last_soc_update_epoch = time.time() - 10
                with patch('operational_events.time.monotonic', return_value=100):
                    j._observe_battery_care_incident(conn, state.snapshot())
                self.assertEqual('open', conn.execute('SELECT status FROM operational_events').fetchone()[0])
                state.last_soc_update_epoch += 1
                with patch('operational_events.time.monotonic', return_value=104):
                    j._observe_battery_care_incident(conn, state.snapshot())
                self.assertEqual('resolved', conn.execute('SELECT status FROM operational_events').fetchone()[0])


if __name__ == '__main__':
    unittest.main()
