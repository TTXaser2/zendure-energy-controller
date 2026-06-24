import time
import unittest

from tests.test_operation_priority import base_cfg, fresh_state, make_controller, OkShelly


def state_with_second_battery(power_display_w, soc=80):
    state = fresh_state(soc)
    now = time.time()
    # Controller display convention: positive = second battery charging, negative = discharging.
    # Raw EVCC default with SECOND_BATTERY_DISCHARGE_SIGN=1 is inverse for display.
    raw_power = -float(power_display_w)
    with state.lock:
        state.sma_battery_power = raw_power
        state.sma_battery_display_power = float(power_display_w)
        state.sma_battery_discharge_power = max(0.0, -float(power_display_w))
        state.sma_battery_soc = 80.0
        state.last_sma_battery_update_epoch = now
        state.second_battery_data_fresh = True
        state.second_battery_data_valid = True
        state.second_battery_data_available = True
    return state


class SymmetricCrossChargeRc6Tests(unittest.TestCase):
    def base_cross_cfg(self, **overrides):
        cfg = base_cfg(
            MANUAL_MODE="AUTO",
            NIGHT_DISCHARGE_ENABLED=False,
            CROSS_CHARGE_ENABLED=True,
            SECOND_BATTERY_DISCHARGE_SIGN=1,
            CROSS_CHARGE_SIGNIFICANT_W=80,
            SMA_DISCHARGE_BLOCK_W=80,
            CROSS_CHARGE_RESERVE_W=0,
            MIN_EFFECTIVE_SURPLUS_FOR_CHARGE_W=0,
            CONTROL_GAIN=1.0,
            SMOOTHING_FACTOR=1.0,
            MAX_POWER_STEP_W=5000,
            MAX_CHARGE_POWER_W=2400,
            MAX_DISCHARGE_POWER_W=2400,
            DEADBAND_W=20,
            MODE_CHANGE_LOCK_SECONDS=0,
        )
        cfg.update(overrides)
        return cfg

    def test_sma_discharges_zendure_charge_is_reduced_proportionally(self):
        cfg = self.base_cross_cfg()
        state = state_with_second_battery(-1000, soc=50)
        controller, state, mqtt, _ = make_controller(cfg, state=state, shelly=OkShelly(-2200))
        controller.is_night_discharge_active = lambda _cfg: False

        controller.run_once(cfg)

        self.assertEqual(1200, state.last_input_power)
        self.assertEqual(0, state.last_output_power)
        self.assertIn("CROSS_CHARGE", state.active_limiters)
        self.assertIn("Cross-Charge", state.control_reason)
        self.assertIn(("input", 1200, False), mqtt.commands)

    def test_sma_discharges_stronger_than_charge_target_blocks_to_zero(self):
        cfg = self.base_cross_cfg()
        state = state_with_second_battery(-1000, soc=50)
        controller, state, mqtt, _ = make_controller(cfg, state=state, shelly=OkShelly(-600))
        controller.is_night_discharge_active = lambda _cfg: False

        controller.run_once(cfg)

        self.assertEqual(0, state.last_input_power)
        self.assertEqual(0, state.last_output_power)
        self.assertIn("CROSS_CHARGE", state.active_limiters)
        self.assertIn(("input", 0, True), mqtt.commands)
        self.assertIn(("output", 0, True), mqtt.commands)

    def test_sma_charges_zendure_discharge_is_reduced_proportionally(self):
        cfg = self.base_cross_cfg()
        state = state_with_second_battery(+1000, soc=50)
        controller, state, mqtt, _ = make_controller(cfg, state=state, shelly=OkShelly(+2200))
        controller.is_night_discharge_active = lambda _cfg: False

        controller.run_once(cfg)

        self.assertEqual(0, state.last_input_power)
        self.assertEqual(1200, state.last_output_power)
        self.assertIn("CROSS_CHARGE", state.active_limiters)
        self.assertIn("Cross-Charge", state.control_reason)
        self.assertIn(("output", 1200, False), mqtt.commands)

    def test_sma_charges_stronger_than_discharge_target_blocks_to_zero(self):
        cfg = self.base_cross_cfg()
        state = state_with_second_battery(+1000, soc=50)
        controller, state, mqtt, _ = make_controller(cfg, state=state, shelly=OkShelly(+600))
        controller.is_night_discharge_active = lambda _cfg: False

        controller.run_once(cfg)

        self.assertEqual(0, state.last_input_power)
        self.assertEqual(0, state.last_output_power)
        self.assertIn("CROSS_CHARGE", state.active_limiters)
        self.assertIn(("input", 0, True), mqtt.commands)
        self.assertIn(("output", 0, True), mqtt.commands)

    def test_below_engage_threshold_without_latch_keeps_golden_behavior(self):
        cfg = self.base_cross_cfg(CROSS_CHARGE_SIGNIFICANT_W=80)
        state = state_with_second_battery(+79, soc=50)
        controller, state, _, _ = make_controller(cfg, state=state, shelly=OkShelly(+600))
        controller.is_night_discharge_active = lambda _cfg: False

        controller.run_once(cfg)

        self.assertEqual(600, state.last_output_power)
        self.assertNotIn("CROSS_CHARGE", state.active_limiters)

    def test_latched_hysteresis_stays_active_until_release_threshold(self):
        cfg = self.base_cross_cfg(CROSS_CHARGE_SIGNIFICANT_W=80)
        state = state_with_second_battery(+85, soc=50)
        controller, state, _, _ = make_controller(cfg, state=state, shelly=OkShelly(+600))
        controller.is_night_discharge_active = lambda _cfg: False
        controller.run_once(cfg)
        self.assertTrue(state.cross_charge_guard_latched)

        with state.lock:
            state.sma_battery_power = -70  # display +70 charging, below engage but above release 40
        controller.run_once(cfg)
        self.assertTrue(state.cross_charge_guard_latched)
        self.assertIn("CROSS_CHARGE", state.active_limiters)

        with state.lock:
            state.sma_battery_power = -30  # display +30 charging, below release
        controller.run_once(cfg)
        self.assertFalse(state.cross_charge_guard_latched)

    def test_no_cross_charge_in_night_discharge(self):
        cfg = self.base_cross_cfg(NIGHT_DISCHARGE_ENABLED=True)
        state = state_with_second_battery(+1000, soc=50)
        controller, state, mqtt, shelly = make_controller(cfg, state=state, shelly=OkShelly(+600))
        controller.is_night_discharge_active = lambda _cfg: True

        controller.run_once(cfg)

        self.assertEqual(shelly.calls, 1)
        self.assertEqual("NIGHT_DISCHARGE", state.current_mode)
        self.assertEqual(400, state.last_output_power)
        self.assertNotIn("CROSS_CHARGE", state.active_limiters)

    def test_stale_second_battery_keeps_golden_behavior(self):
        cfg = self.base_cross_cfg(SECOND_BATTERY_STALE_TIMEOUT_SECONDS=1)
        state = state_with_second_battery(+1000, soc=50)
        with state.lock:
            state.last_sma_battery_update_epoch = time.time() - 99
        controller, state, _, _ = make_controller(cfg, state=state, shelly=OkShelly(+600))
        controller.is_night_discharge_active = lambda _cfg: False

        controller.run_once(cfg)

        self.assertEqual(600, state.last_output_power)
        self.assertNotIn("CROSS_CHARGE", state.active_limiters)


if __name__ == "__main__":
    unittest.main()
