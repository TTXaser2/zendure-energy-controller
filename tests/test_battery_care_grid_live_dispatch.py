# SPDX-License-Identifier: AGPL-3.0-or-later
"""Stage 2/3 grid request: central publisher and economic exception only."""
import time
import unittest
from unittest.mock import patch

from battery_care_policy import CareDecision, CareEpisode, CareStage
from tests.test_battery_care_discharge_floor import care_cfg
from tests.test_operation_priority import fresh_state, make_controller, OkShelly


class GridCareDispatchTests(unittest.TestCase):
    def make(self, *, soc=20, cfg=None):
        cfg = cfg or care_cfg(HARVEST_FAST_CAPTURE_MODE="off", REST_SURPLUS_HARVEST_ENABLED=False)
        state = fresh_state(soc)
        ctrl, state, mqtt, _ = make_controller(cfg, state=state, shelly=OkShelly(150))
        ctrl.is_night_discharge_active = lambda _: False
        now = time.time()
        with state.lock:
            state.mqtt_command_path_valid = True
            state.zendure_flash_protection_active = True
            state.zendure_command_state_complete = True
            state.command_state_gate_state = 'READY'
            state.zendure_mqtt_live_confirmed = True
            state.zendure_mqtt_overall_status = 'OK'
            state.grid_power_valid = True
            state.grid_power_sample_epoch = now
            state.raw_grid_power = 150.
            state.actual_zendure_power_valid = True
            state.zendure_power_observation_signed_w = 0.
            state.zendure_power_observation_direction = 'NEUTRAL'
            state.zendure_power_observation_updated_epoch = now
        return ctrl, cfg, state, mqtt

    def direct(self, ctrl, stage, *, exception=False, watts=250):
        ctrl._care_grid_shadow_decision = CareDecision(
            stage, 40, watts, 0, exception,
            'synthetic_test_source_gates_checked_separately',
            CareEpisode(active_level=3 if exception else 2, target_reserve_soc=40),
        )
        ctrl.state.care_pv_shadow_extra_w = 0
        # Synthetic direct-dispatch fixture: the real source->policy adapter
        # and durable-latch gate have separate integration tests.
        ctrl._care_grid_persistence_ready = True

    def test_emergency_uses_existing_command_owner_not_cross_charge(self):
        ctrl, cfg, state, mqtt = self.make()
        self.direct(ctrl, CareStage.EMERGENCY_REQUESTED, exception=True)
        with patch.object(ctrl, '_apply_symmetric_cross_charge_limit',
                          side_effect=AssertionError('economic veto applied')):
            self.assertTrue(ctrl._battery_care_grid_dispatch(cfg))
        self.assertTrue(ctrl._care_grid_live_active)
        self.assertEqual(state.last_input_power, 250)
        self.assertEqual(state.last_output_power, 0)
        self.assertTrue(any(x[0]=='input' and x[1]==250 for x in mqtt.commands))
        self.assertIn('EMERGENCY', state.technical_control_path)

    def test_regular_grid_passes_cross_charge_veto(self):
        ctrl, cfg, state, mqtt = self.make(soc=30)
        self.direct(ctrl, CareStage.GRID_REQUESTED)
        with patch.object(ctrl, '_apply_symmetric_cross_charge_limit',
                          return_value={'target':0, 'active':True}) as veto:
            self.assertTrue(ctrl._battery_care_grid_dispatch(cfg))
            veto.assert_called_once()
        self.assertFalse(ctrl._care_grid_live_active)
        self.assertFalse(any(x[0]=='input' and x[1]>0 for x in mqtt.commands))

    def test_exit_neutralizes_once_and_cannot_latch_old_care_power(self):
        ctrl, cfg, state, mqtt = self.make()
        self.direct(ctrl, CareStage.EMERGENCY_REQUESTED, exception=True)
        self.assertTrue(ctrl._battery_care_grid_dispatch(cfg))
        self.direct(ctrl, CareStage.COMPLETED, watts=0)
        self.assertTrue(ctrl._battery_care_grid_dispatch(cfg))
        self.assertEqual(0, state.last_input_power)
        self.assertFalse(ctrl._care_grid_live_active)
        n=len(mqtt.commands)
        self.assertFalse(ctrl._battery_care_grid_dispatch(cfg))
        self.assertEqual(n, len(mqtt.commands))

    def test_existing_discharge_gets_neutral_step_before_grid(self):
        ctrl, cfg, state, mqtt = self.make()
        self.direct(ctrl, CareStage.EMERGENCY_REQUESTED, exception=True)
        with state.lock:
            state.last_output_power = 300
        self.assertTrue(ctrl._battery_care_grid_dispatch(cfg))
        self.assertEqual(0, state.last_output_power)
        self.assertFalse(ctrl._care_grid_live_active)
        self.assertFalse(any(x[0]=='input' and x[1]>0 for x in mqtt.commands))

    def test_stage_one_pv_evidence_outprioritizes_new_grid(self):
        ctrl, cfg, state, mqtt = self.make()
        self.direct(ctrl, CareStage.EMERGENCY_REQUESTED, exception=True)
        with state.lock:
            state.care_pv_shadow_extra_w = 400
        self.assertFalse(ctrl._battery_care_grid_dispatch(cfg))
        self.assertEqual([], mqtt.commands)

    def test_full_run_once_emergency_uses_one_existing_publisher(self):
        ctrl, cfg, state, mqtt = self.make()
        # Source qualification is tested separately; drive the actual branch
        # to ensure grid import AUTO would not reroute to discharge.
        ctrl._battery_care_pv_shadow_step = lambda _: None
        ctrl._battery_care_grid_shadow_step = lambda _: self.direct(
            ctrl, CareStage.EMERGENCY_REQUESTED, exception=True)
        ctrl.run_once(cfg)
        self.assertEqual(state.last_input_power, 250)
        self.assertEqual(state.last_output_power, 0)
        self.assertEqual(state.current_mode, 'CHARGE')
        self.assertTrue(any(x[0]=='input' and x[1]==250 for x in mqtt.commands))
        self.assertFalse(any(x[0]=='output' and x[1]>0 for x in mqtt.commands))

    def test_live_device_cap_loss_neutralizes_earlier_grid_request(self):
        ctrl, cfg, state, mqtt = self.make()
        self.direct(ctrl, CareStage.EMERGENCY_REQUESTED, exception=True)
        ctrl._battery_care_grid_dispatch(cfg)
        self.assertTrue(ctrl._care_grid_live_active)
        with patch.object(ctrl, '_fast_capture_effective_zendure_limit_w', return_value=0):
            self.assertTrue(ctrl._battery_care_grid_dispatch(cfg))
        self.assertEqual(0, state.last_input_power)
        self.assertFalse(ctrl._care_grid_live_active)

    def test_hardware_cap_is_not_exceeded(self):
        ctrl, cfg, state, mqtt = self.make()
        self.direct(ctrl, CareStage.EMERGENCY_REQUESTED, exception=True, watts=250)
        with patch.object(ctrl, '_fast_capture_effective_zendure_limit_w', return_value=120):
            ctrl._battery_care_grid_dispatch(cfg)
        self.assertEqual(state.last_input_power, 120)


if __name__=='__main__':
    unittest.main()
