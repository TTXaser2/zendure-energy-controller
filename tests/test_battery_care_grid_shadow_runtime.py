# SPDX-License-Identifier: AGPL-3.0-or-later
"""CP14: real controller-sourced shadow intent, not device authorization."""
import time
import unittest
from unittest.mock import patch

from battery_care_policy import CareStage
from tests.test_battery_care_discharge_floor import care_cfg
from tests.test_operation_priority import fresh_state, make_controller, OkShelly


class CareGridShadowRuntime(unittest.TestCase):
    def make(self, *, soc=20, cfg=None):
        cfg = cfg or care_cfg()
        state = fresh_state(soc)
        ctrl, state, mqtt, _ = make_controller(cfg, state=state, shelly=OkShelly(0))
        with state.lock:
            state.mqtt_command_path_valid = True
            state.zendure_flash_protection_active = True
            state.zendure_command_state_complete = True
            state.command_state_gate_state = "READY"
            state.grid_power_valid = True
            state.raw_grid_power = 100.
            state.grid_power_sample_epoch = time.time()
            state.actual_zendure_power_valid = True
            state.zendure_power_observation_signed_w = 0.
            state.zendure_power_observation_direction = "NEUTRAL"
            state.zendure_power_observation_updated_epoch = time.time()
        return ctrl, state, mqtt, cfg

    def test_fresh_emergency_is_shadow_only(self):
        ctrl, state, mqtt, cfg = self.make()
        ctrl._battery_care_grid_shadow_step(cfg)
        d = ctrl._care_grid_shadow_decision
        self.assertEqual(d.stage, CareStage.EMERGENCY_REQUESTED)
        self.assertEqual(d.requested_charge_w, 250)
        self.assertEqual(mqtt.commands, [])

    def test_manual_stop_blocks_shadow_and_clears_episode(self):
        ctrl, state, mqtt, cfg = self.make()
        ctrl._battery_care_grid_shadow_step(cfg)
        cfg['MANUAL_MODE'] = 'STOP_HOLD'
        ctrl._battery_care_grid_shadow_step(cfg)
        self.assertEqual(ctrl._care_grid_shadow_decision.requested_charge_w, 0)
        self.assertEqual(ctrl._care_grid_shadow_decision.reason, 'manual_stop')
        self.assertEqual(mqtt.commands, [])

    def test_missing_device_ac_evidence_cannot_request_grid(self):
        ctrl, state, mqtt, cfg = self.make()
        with state.lock:
            state.zendure_power_observation_direction = 'CONFLICT'
        ctrl._battery_care_grid_shadow_step(cfg)
        self.assertEqual(ctrl._care_grid_shadow_decision.requested_charge_w, 0)
        self.assertEqual(mqtt.commands, [])

    def test_emergency_shadow_excludes_only_economic_crosscharge_veto(self):
        ctrl, state, mqtt, cfg = self.make()
        with state.lock:
            state.cross_charge_guard_latched = True
        ctrl._battery_care_grid_shadow_step(cfg)
        self.assertTrue(ctrl._care_grid_shadow_decision.allow_emergency_cross_charge_exception)
        self.assertEqual(mqtt.commands, [])

    def test_command_uncertain_still_blocks_emergency_shadow(self):
        ctrl, state, mqtt, cfg = self.make()
        with state.lock:
            state.command_uncertain_mqtt_active = True
        ctrl._battery_care_grid_shadow_step(cfg)
        self.assertEqual(ctrl._care_grid_shadow_decision.requested_charge_w, 0)
        self.assertEqual(mqtt.commands, [])


if __name__ == '__main__':
    unittest.main()
