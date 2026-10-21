"""Release blocker: global MIN_SOC must never blind night-time grid control."""
import time
import unittest
from tests.test_operation_priority import base_cfg, fresh_state, make_controller, OkShelly, FailingShelly


class NightMinSocGridRegression(unittest.TestCase):
    def make(self, grid, *, soc=15):
        cfg = base_cfg(MANUAL_MODE='AUTO', NIGHT_DISCHARGE_ENABLED=True,
                       NIGHT_DISCHARGE_STOP_SOC_PERCENT=35,
                       MIN_SOC_PERCENT=15, DEADBAND_W=80,
                       MOVING_AVERAGE_SAMPLES=1, REST_SURPLUS_HARVEST_ENABLED=False)
        state = fresh_state(soc)
        with state.lock:
            state.current_mode = 'NIGHT_DISCHARGE'
            state.technical_control_path = 'NIGHT_MODE -> OUTPUT'
            state.last_output_power = 400
        ctrl, state, mqtt, shelly = make_controller(cfg, state=state, shelly=OkShelly(grid))
        ctrl.is_night_discharge_active = lambda _: True
        return ctrl, cfg, state, mqtt, shelly

    def test_min_soc_import_is_fresh_and_blocked(self):
        ctrl, cfg, state, mqtt, shelly = self.make(800)
        ctrl.run_once(cfg)
        self.assertEqual(shelly.calls, 1)
        self.assertTrue(state.grid_power_used_for_control)
        self.assertTrue(state.grid_power_valid)
        self.assertEqual(state.current_mode, 'HOLD')
        self.assertIn('MIN_SOC', state.active_limiters)
        self.assertEqual(state.safe_state_counter, 0)
        self.assertFalse(any(cmd[0] == 'output' and cmd[1] > 0 for cmd in mqtt.commands))
        self.assertIn(('output', 0, True), mqtt.commands)

    def test_min_soc_export_is_still_allowed_to_charge(self):
        ctrl, cfg, state, mqtt, shelly = self.make(-1800)
        ctrl.run_once(cfg)
        self.assertEqual(shelly.calls, 1)
        self.assertTrue(state.grid_power_used_for_control)
        self.assertEqual(state.current_mode, 'CHARGE')
        self.assertGreater(state.last_input_power, 0)
        self.assertFalse(any(cmd[0] == 'output' and cmd[1] > 0 for cmd in mqtt.commands))
        self.assertTrue(any(cmd[0] == 'input' and cmd[1] > 0 for cmd in mqtt.commands))

    def test_min_soc_import_then_export_responds_to_new_grid(self):
        ctrl, cfg, state, mqtt, shelly = self.make(900)
        ctrl.run_once(cfg)
        self.assertEqual(state.current_mode, 'HOLD')
        shelly.value = -2000
        ctrl.run_once(cfg)
        self.assertEqual(shelly.calls, 2)
        self.assertEqual(state.current_mode, 'CHARGE')
        self.assertTrue(state.grid_power_used_for_control)

    def test_min_soc_export_then_import_stops_discharge(self):
        ctrl, cfg, state, mqtt, shelly = self.make(-2000)
        ctrl.run_once(cfg)
        self.assertEqual(state.current_mode, 'CHARGE')
        shelly.value = 900
        ctrl.run_once(cfg)
        self.assertEqual(state.current_mode, 'HOLD')
        self.assertEqual(state.last_input_power, 0)
        self.assertEqual(state.last_output_power, 0)
        self.assertTrue(state.grid_power_used_for_control)

    def test_stale_grid_fails_closed_at_min_soc(self):
        cfg = base_cfg(MANUAL_MODE='AUTO', NIGHT_DISCHARGE_ENABLED=True,
                       NIGHT_DISCHARGE_STOP_SOC_PERCENT=35, MIN_SOC_PERCENT=15,
                       SHELLY_STALE_TIMEOUT_SECONDS=1)
        ctrl, state, mqtt, shelly = make_controller(cfg, state=fresh_state(15), shelly=FailingShelly())
        ctrl.is_night_discharge_active = lambda _: True
        ctrl.run_once(cfg)
        self.assertEqual(shelly.calls, 1)
        self.assertEqual(state.current_mode, 'SAFE_STATE')
        self.assertFalse(state.grid_power_used_for_control)
        self.assertNotIn(('input', 400, False), mqtt.commands)

    def test_night_exit_follows_normal_grid_control(self):
        ctrl, cfg, state, mqtt, shelly = self.make(-1900, soc=20)
        ctrl.is_night_discharge_active = lambda _: False
        ctrl.run_once(cfg)
        self.assertEqual(shelly.calls, 1)
        self.assertTrue(state.grid_power_used_for_control)
        self.assertEqual(state.current_mode, 'CHARGE')
        self.assertTrue(any(c[0]=='input' and c[1]>0 for c in mqtt.commands))


if __name__ == '__main__':
    unittest.main()
