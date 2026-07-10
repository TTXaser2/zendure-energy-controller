import unittest

from measurement_v4 import build_v4_row
from tests.test_measurement_v4_writer import base_config, base_row
from tests.test_v12_11_1_rc1_high_sma_harvest import cfg_high, make
from tests.test_v12_10_rc6_cross_charge import state_with_second_battery
from tests.test_operation_priority import OkShelly


class Rc2CrossChargeDiagnosticsTests(unittest.TestCase):
    def test_v4_maps_cross_charge_guard_flags_even_when_reason_is_auto_grid_export(self):
        row = base_row()
        row.update({
            "mode": "CHARGE",
            "second_battery_power_w": -320.0,
            "second_battery_valid": True,
            "second_battery_fresh": True,
            "cross_charge_guard_active": True,
            "cross_charge_guard_limited": True,
            "target_raw_w": 2490.0,
            "target_after_smoothing_w": 2377.0,
            "target_after_ramp_w": 2057.0,
            "target_final_w": 2057.0,
            # RC1 productive data could still carry a generic AUTO reason here.
            # The V4 row must nevertheless expose the active Cross-Charge guard.
            "control_reason": "AUTO_GRID_EXPORT",
        })
        v4 = build_v4_row(base_config("/tmp"), row)
        self.assertEqual("CROSS_CHARGE_REDUCED", v4["target_final_reason"])
        self.assertEqual("1", v4["control_cross_charge_detected"])
        self.assertEqual("1", v4["control_cross_charge_limited"])
        self.assertEqual("1", v4["target_changed_by_cross_charge"])

    def test_v4_maps_cross_charge_from_limiter_summary(self):
        row = base_row()
        row.update({
            "mode": "CHARGE",
            "cross_charge_guard_active": False,
            "cross_charge_guard_limited": False,
            "technical_limiters": "CROSS_CHARGE",
            "target_final_w": 1200.0,
            "control_reason": "AUTO_GRID_EXPORT",
        })
        v4 = build_v4_row(base_config("/tmp"), row)
        self.assertEqual("CROSS_CHARGE_REDUCED", v4["target_final_reason"])
        self.assertEqual("1", v4["control_cross_charge_detected"])
        self.assertEqual("1", v4["control_cross_charge_limited"])

    def test_cross_charge_guard_corrects_existing_auto_charge_target_in_real_rc1_pattern(self):
        cfg = cfg_high(
            CROSS_CHARGE_SIGNIFICANT_W=80,
            MAX_CHARGE_POWER_W=2400,
            MAX_POWER_STEP_W=5000,
            SMOOTHING_FACTOR=1.0,
            CONTROL_GAIN=1.0,
        )
        state = state_with_second_battery(-320, soc=90)
        with state.lock:
            state.rest_surplus_harvest_active = False
            state.rest_surplus_harvest_reason = "NONE"
            state.last_input_power = 2377
            state.last_target_before_smoothing = 2490
            state.last_target_after_smoothing = 2377
            state.last_target_after_ramp = 2377
            state.battery_soc = 50
        controller, state, mqtt = make(cfg, state=state, shelly=OkShelly(63))

        controller.run_once(cfg)

        self.assertEqual(2057, state.last_input_power)
        self.assertIn("CROSS_CHARGE", state.active_limiters)
        self.assertIn("Cross-Charge", state.control_reason)
        self.assertIn("CROSS_CHARGE", state.technical_control_path)

    def test_zendure_capacity_diagnostic_falls_back_from_wh_config(self):
        cfg = cfg_high(ZENDURE_BATTERY_CAPACITY_KWH=None, ZENDURE_BATTERY_CAPACITY_WH=5280)
        state = state_with_second_battery(+2000, soc=80)
        with state.lock:
            state.sma_battery_capacity_kwh = 13.0
            state.battery_soc = 50
        controller, state, mqtt = make(cfg, state=state, shelly=OkShelly(-500))

        controller.run_once(cfg)

        self.assertEqual("diagnostic", state.harvest_capacity_mode)
        self.assertIsNotNone(state.primary_remaining_capacity_kwh)
        self.assertAlmostEqual(2.587, state.zendure_remaining_capacity_kwh, places=3)


if __name__ == "__main__":
    unittest.main()
