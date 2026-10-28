# SPDX-License-Identifier: AGPL-3.0-or-later
"""CP16 real SQLite grid latch, restart, STOP and fail-closed differential."""
import sqlite3
from contextlib import closing
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from battery_care_episode_store import CareEpisodeStore, CareEpisodePersistenceError
from battery_care_policy import CareEpisode, CareStage
from tests.test_battery_care_grid_shadow_runtime import CareGridShadowRuntime
from tests.test_battery_care_discharge_floor import care_cfg
from tests.test_operation_priority import fresh_state, make_controller, OkShelly


class PersistentCareGridEpisodes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = str(Path(self.tmp.name) / 'operational.sqlite3')
        self.cfg = care_cfg(OPERATIONAL_EVENTS_DB_PATH=self.db)
        self.store = CareEpisodeStore(lambda: self.cfg)

    def controller(self, soc):
        state = fresh_state(soc)
        ctrl, state, mqtt, _ = make_controller(self.cfg, state=state, shelly=OkShelly(150))
        now = time.time()
        with state.lock:
            state.mqtt_command_path_valid = True
            state.zendure_flash_protection_active = True
            state.zendure_command_state_complete = True
            state.command_state_gate_state = 'READY'
            state.grid_power_valid = True
            state.raw_grid_power = 150.0
            state.grid_power_sample_epoch = now
            state.actual_zendure_power_valid = True
            state.zendure_power_observation_signed_w = 0.0
            state.zendure_power_observation_direction = 'NEUTRAL'
            state.zendure_power_observation_updated_epoch = now
        return ctrl, state, mqtt

    def test_disabled_default_does_not_create_db(self):
        self.cfg['BATTERY_CARE_ENABLED'] = False
        ctrl, _, _ = self.controller(20)
        ctrl._battery_care_clear_latch_for_explicit_stop()
        self.assertFalse(Path(self.db).exists())

    def test_single_active_episode_stores_only_level_and_original_reserve(self):
        self.store.save(CareEpisode(active_level=3,target_reserve_soc=40,
                                    last_soc_sample_id='pre-restart-old',
                                    completed_sample_count=1))
        restored = self.store.load()
        self.assertEqual((3,40), (restored.active_level,restored.target_reserve_soc))
        self.assertIsNone(restored.last_soc_sample_id)
        self.assertEqual(0,restored.completed_sample_count)
        self.store.save(CareEpisode())
        self.assertEqual(0,self.store.load().active_level)

    def test_emergency_restart_survives_soc_rebound_above_e_and_later_lower_r(self):
        ctrl, state, _ = self.controller(19)
        ctrl._battery_care_grid_shadow_step(self.cfg)
        self.assertEqual(CareStage.EMERGENCY_REQUESTED,ctrl._care_grid_shadow_decision.stage)
        self.assertEqual((3,40),self.store.signature(self.store.load()))
        # Process restart / user's later configuration change: N/E remain valid.
        self.cfg['BATTERY_CARE_RESERVE_SOC_PERCENT'] = 35
        restarted, _, _ = self.controller(36)
        restarted._battery_care_grid_shadow_step(self.cfg)
        self.assertEqual(CareStage.EMERGENCY_REQUESTED,restarted._care_grid_shadow_decision.stage)
        self.assertEqual(40,restarted._care_grid_episode.target_reserve_soc)
        self.assertTrue(restarted._care_grid_persistence_ready)

    def test_regular_episode_survives_restart_above_n_below_original_r(self):
        self.store.save(CareEpisode(active_level=2, target_reserve_soc=40))
        ctrl, _, _ = self.controller(35)
        ctrl._battery_care_grid_shadow_step(self.cfg)
        self.assertEqual(CareStage.GRID_REQUESTED, ctrl._care_grid_shadow_decision.stage)
        self.assertFalse(ctrl._care_grid_shadow_decision.allow_emergency_cross_charge_exception)
        self.assertEqual(40, ctrl._care_grid_episode.target_reserve_soc)

    def test_emergency_survives_calendar_end_but_no_new_episode_starts(self):
        self.cfg['BATTERY_CARE_SEASON_START_MM_DD'] = '01-01'
        self.cfg['BATTERY_CARE_SEASON_END_MM_DD'] = '01-01'
        self.store.save(CareEpisode(active_level=3,target_reserve_soc=40))
        ctrl, _, _ = self.controller(34)
        ctrl._battery_care_grid_shadow_step(self.cfg)
        self.assertEqual(CareStage.EMERGENCY_REQUESTED,ctrl._care_grid_shadow_decision.stage)
        self.store.save(CareEpisode())
        other, _, _ = self.controller(19)
        other._battery_care_grid_shadow_step(self.cfg)
        self.assertEqual(CareStage.OUT_OF_SEASON,other._care_grid_shadow_decision.stage)
        self.assertEqual(0,other._care_grid_episode.active_level)

    def test_stop_in_real_run_once_before_sensor_gate_clears_persistent_latch(self):
        self.store.save(CareEpisode(active_level=3,target_reserve_soc=40))
        self.cfg['MANUAL_MODE'] = 'STOP_HOLD'
        ctrl, _, _ = self.controller(19)
        ctrl.run_once(self.cfg)
        self.assertEqual(0,self.store.load().active_level)

    def test_restart_does_not_trust_stale_ac_direction_for_a_new_command(self):
        self.store.save(CareEpisode(active_level=3,target_reserve_soc=40))
        ctrl, state, mqtt = self.controller(32)
        with state.lock:
            state.zendure_power_observation_direction = 'UNKNOWN'
        ctrl._battery_care_grid_shadow_step(self.cfg)
        self.assertIsNotNone(ctrl._care_grid_shadow_decision)
        self.assertEqual(0,ctrl._care_grid_shadow_decision.requested_charge_w)
        self.assertFalse(ctrl._battery_care_grid_dispatch(self.cfg))
        self.assertEqual([],mqtt.commands)
        self.assertEqual((3,40), self.store.signature(self.store.load()))

    def test_restart_does_not_auto_resolve_at_original_r_on_first_soc_sample(self):
        self.store.save(CareEpisode(active_level=3,target_reserve_soc=40))
        ctrl, _, _ = self.controller(40)
        ctrl._battery_care_grid_shadow_step(self.cfg)
        self.assertEqual(CareStage.EMERGENCY_REQUESTED,ctrl._care_grid_shadow_decision.stage)
        self.assertEqual(1,ctrl._care_grid_episode.completed_sample_count)
        self.assertEqual(3,self.store.load().active_level)

    def test_early_manual_stop_clears_latch_with_no_sensor_access(self):
        self.store.save(CareEpisode(active_level=2,target_reserve_soc=40))
        ctrl, _, _ = self.controller(35)
        ctrl._battery_care_clear_latch_for_explicit_stop()
        self.assertEqual(0,self.store.load().active_level)
        self.assertFalse(ctrl._care_grid_clear_failed)

    def test_corrupt_or_missing_db_blocks_shadow_not_invents_target(self):
        self.store.save(CareEpisode(active_level=2,target_reserve_soc=40))
        with closing(sqlite3.connect(self.db)) as conn:
            with conn:
                conn.execute('DROP TABLE battery_care_grid_episode')
                conn.execute('CREATE TABLE battery_care_grid_episode(slot INTEGER PRIMARY KEY,active_level INTEGER,reserve_soc INTEGER,recorded_at REAL)')
                conn.execute('INSERT INTO battery_care_grid_episode VALUES(1,9,5,0)')
        ctrl, _, _ = self.controller(19)
        ctrl._battery_care_grid_shadow_step(self.cfg)
        self.assertIsNone(ctrl._care_grid_shadow_decision)
        self.assertFalse(ctrl._care_grid_persistence_ready)
        self.assertFalse(ctrl._battery_care_grid_dispatch(self.cfg))

    def test_db_write_failure_cannot_publish_emergency_command(self):
        ctrl, _, mqtt = self.controller(19)
        with patch.object(ctrl._care_grid_episode_store,'save',side_effect=CareEpisodePersistenceError('disk full')):
            ctrl._battery_care_grid_shadow_step(self.cfg)
        self.assertIsNone(ctrl._care_grid_shadow_decision)
        self.assertFalse(ctrl._care_grid_persistence_ready)
        self.assertFalse(ctrl._battery_care_grid_dispatch(self.cfg))
        self.assertEqual([],mqtt.commands)

    def test_explicit_stop_failure_remains_fail_closed(self):
        ctrl, _, _ = self.controller(19)
        with patch.object(ctrl._care_grid_episode_store,'save',side_effect=CareEpisodePersistenceError('disk full')):
            with patch.object(ctrl._care_grid_episode_store,'exists',return_value=True):
                ctrl._battery_care_clear_latch_for_explicit_stop()
        self.assertTrue(ctrl._care_grid_clear_failed)
        ctrl._battery_care_grid_shadow_step(self.cfg)
        self.assertIsNone(ctrl._care_grid_shadow_decision)


if __name__=='__main__':
    unittest.main()
