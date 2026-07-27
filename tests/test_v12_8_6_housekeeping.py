import time
import unittest

from tests.test_operation_priority import base_cfg, fresh_state, make_controller, OkShelly


class V1286HousekeepingTests(unittest.TestCase):
    def _state_with_second_battery(self, raw_power=90.0, stale_display=-360.0, soc=80):
        state = fresh_state(soc)
        now = time.time()
        with state.lock:
            state.sma_battery_power = raw_power
            state.sma_battery_display_power = stale_display
            state.sma_battery_discharge_power = abs(stale_display)
            state.sma_battery_soc = 87.0
            state.last_sma_battery_update_epoch = now
            state.last_sma_battery_update_time = "23:50:27"
        return state

    def test_night_discharge_refreshes_second_battery_display_before_early_return(self):
        cfg = base_cfg(NIGHT_DISCHARGE_ENABLED=True, CROSS_CHARGE_ENABLED=True, SECOND_BATTERY_DISCHARGE_SIGN=1)
        state = self._state_with_second_battery(raw_power=90.0, stale_display=-360.0)
        controller, state, mqtt, shelly = make_controller(cfg, state=state)
        controller.is_night_discharge_active = lambda _cfg: True

        controller.run_once(cfg)

        self.assertEqual(shelly.calls, 1)
        self.assertEqual(state.current_mode, "NIGHT_DISCHARGE")
        self.assertEqual(state.sma_battery_display_power, -90.0)
        self.assertEqual(state.sma_battery_discharge_power, 90.0)
        self.assertTrue(state.second_battery_data_fresh)
        self.assertFalse(state.second_battery_data_used_for_control)

    def test_stop_hold_refreshes_second_battery_display_even_without_soc(self):
        cfg = base_cfg(MANUAL_MODE="STOP_HOLD", CROSS_CHARGE_ENABLED=True, SECOND_BATTERY_DISCHARGE_SIGN=1)
        state = self._state_with_second_battery(raw_power=87.0, stale_display=-360.0)
        with state.lock:
            state.battery_soc = None
            state.last_soc_update_epoch = None
            state.last_input_power = 500
        controller, state, mqtt, shelly = make_controller(cfg, state=state)

        controller.run_once(cfg)

        self.assertEqual(shelly.calls, 1)
        self.assertEqual(state.current_mode, "STOP_HOLD")
        self.assertEqual(state.sma_battery_display_power, -87.0)
        self.assertEqual(state.sma_battery_discharge_power, 87.0)

    def test_auto_cross_charge_uses_fresh_second_battery_after_grid_measurement(self):
        cfg = base_cfg(
            MANUAL_MODE="AUTO",
            NIGHT_DISCHARGE_ENABLED=False,
            CROSS_CHARGE_ENABLED=True,
            SECOND_BATTERY_DISCHARGE_SIGN=1,
            DEADBAND_W=20,
            CROSS_CHARGE_RESERVE_W=100,
            MIN_EFFECTIVE_SURPLUS_FOR_CHARGE_W=50,
        )
        state = self._state_with_second_battery(raw_power=90.0, stale_display=-360.0, soc=50)
        controller, state, mqtt, shelly = make_controller(cfg, state=state, shelly=OkShelly(-1000))
        controller.is_night_discharge_active = lambda _cfg: False

        controller.run_once(cfg)

        self.assertEqual(shelly.calls, 1)
        self.assertEqual(state.sma_battery_display_power, -90.0)
        self.assertEqual(state.sma_battery_discharge_power, 90.0)
        # RC6 keeps effective export as the real export candidate; symmetric
        # Cross-Charge reduction is applied later to the signed target so it is
        # not subtracted twice.
        self.assertEqual(state.effective_export_power, 1000)
        self.assertTrue(state.second_battery_data_used_for_control)
        self.assertTrue(state.grid_power_used_for_control)

    def test_finish_cycle_recalculates_zendure_actual_power_after_mode_target_change(self):
        cfg = base_cfg(NIGHT_DISCHARGE_ENABLED=True)
        state = fresh_state(80)
        with state.lock:
            now = time.time()
            state.actual_zendure_charge_power = 399
            state.actual_zendure_pack_input_update_epoch = now
            state.actual_zendure_discharge_power = 0
            state.actual_zendure_output_home_update_epoch = now
            state.actual_zendure_grid_input_power = 0
            state.actual_zendure_grid_input_update_epoch = now
            state.actual_zendure_output_pack_power = 0
            state.actual_zendure_output_pack_update_epoch = now
        controller, state, mqtt, shelly = make_controller(cfg, state=state)
        controller.is_night_discharge_active = lambda _cfg: True

        start = time.time()
        controller.run_once(cfg)
        controller.finish_cycle(cfg, start)

        self.assertEqual(state.last_output_power, 400)
        self.assertEqual(state.actual_zendure_system_signed_power, 0)
        self.assertEqual(state.actual_zendure_system_discharge_power, 0)
        self.assertEqual(state.zendure_battery_signed_power_w, -399)
        self.assertEqual(state.zendure_battery_discharge_power_w, 399)


if __name__ == "__main__":
    unittest.main()
