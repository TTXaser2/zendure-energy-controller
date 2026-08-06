import sys
import types
import time
import unittest

if "paho" not in sys.modules:
    paho = types.ModuleType("paho")
    paho_mqtt = types.ModuleType("paho.mqtt")
    paho_client = types.ModuleType("paho.mqtt.client")
    paho_client.CallbackAPIVersion = types.SimpleNamespace(VERSION2=object())
    paho_client.Client = lambda *args, **kwargs: types.SimpleNamespace(
        on_message=None, on_connect=None, on_disconnect=None,
        username_pw_set=lambda *a, **k: None,
        connect=lambda *a, **k: None,
        loop_start=lambda *a, **k: None,
        subscribe=lambda *a, **k: None,
        publish=lambda *a, **k: types.SimpleNamespace(rc=0),
    )
    sys.modules["paho"] = paho
    sys.modules["paho.mqtt"] = paho_mqtt
    sys.modules["paho.mqtt.client"] = paho_client

from tests.test_v12_10_rc9_rest_surplus import cfg_rc9, make
from tests.test_v12_10_rc6_cross_charge import state_with_second_battery
from tests.test_operation_priority import OkShelly


def cfg_high(**overrides):
    cfg = cfg_rc9(
        HARVEST_HIGH_SMA_SOC_ENABLED=True,
        HARVEST_HIGH_SMA_SOC_ENTER_PERCENT=75,
        HARVEST_HIGH_SMA_SOC_EXIT_PERCENT=70,
        HARVEST_HIGH_SMA_SOC_MIN_EXPORT_W=300,
        HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_SECONDS=6,
        HARVEST_HIGH_SMA_SOC_HOLD_SECONDS=180,
        HARVEST_HIGH_SMA_SOC_TIME_PROFILE_ENABLED=False,
        HARVEST_PRIMARY_CHARGE_TARGET_SHARE_MIDDAY=0.50,
        HARVEST_PRIMARY_CHARGE_FLOOR_W=700,
        HARVEST_PRIMARY_CHARGE_RESTART_W=2000,
        HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_W=2200,
        ZENDURE_BATTERY_CAPACITY_KWH=5.28,
        MAX_CHARGE_POWER_W=2100,
        MAX_POWER_STEP_W=5000,
        SMOOTHING_FACTOR=1.0,
        CONTROL_GAIN=1.0,
        INTERVAL_SECONDS=3,
    )
    cfg.update(overrides)
    return cfg


class HighSmaSocHarvestRc1Tests(unittest.TestCase):
    def test_latch_recovery_full_sma_soc_export_and_previous_zero_target_charges(self):
        cfg = cfg_high()
        state = state_with_second_battery(+10, soc=100)
        with state.lock:
            state.rest_surplus_harvest_active = True
            state.rest_surplus_harvest_reason = "SMA_FULL_OR_IDLE"
            state.last_input_power = 0
            state.battery_soc = 82
        controller, state, mqtt = make(cfg, state=state, shelly=OkShelly(-3000))
        controller.run_once(cfg)
        self.assertGreater(state.last_input_power, 0)
        self.assertIn(state.rest_surplus_harvest_reason, {"SMA_FULL_OR_IDLE", "LATCH_RECOVERY"})
        self.assertIn("REST_SURPLUS_HARVEST", state.active_limiters)
        self.assertNotEqual("NO_CHANGE", getattr(state, "last_mqtt_command_skipped", ""))

    def test_high_soc_entry_from_75_percent_without_near_limit_uses_charge_pressure(self):
        cfg = cfg_high()
        state = state_with_second_battery(+2000, soc=75)
        with state.lock:
            now = time.time()
            state.last_input_power = 500
            state.battery_soc = 50
            state.actual_zendure_grid_input_power = 500
            state.actual_zendure_discharge_power = 0
            state.actual_zendure_grid_input_update_epoch = now
            state.actual_zendure_output_home_update_epoch = now
        controller, state, mqtt = make(cfg, state=state, shelly=OkShelly(0))
        for _ in range(2):
            controller.run_once(cfg)
        self.assertTrue(state.rest_surplus_harvest_active)
        self.assertEqual("HIGH_SMA_SOC", state.rest_surplus_harvest_reason)
        self.assertGreater(state.last_input_power, 500)
        self.assertGreaterEqual(state.harvest_primary_required_w, 700)

    def test_under_enter_threshold_without_near_limit_does_not_enter_high_soc(self):
        cfg = cfg_high()
        state = state_with_second_battery(+1500, soc=74)
        with state.lock:
            state.battery_soc = 50
        controller, state, mqtt = make(cfg, state=state, shelly=OkShelly(0))
        for _ in range(3):
            controller.run_once(cfg)
        self.assertFalse(state.rest_surplus_harvest_active)
        self.assertNotEqual("HIGH_SMA_SOC", state.rest_surplus_harvest_reason)

    def test_export_capture_prevents_share_from_reducing_existing_charge(self):
        cfg = cfg_high()
        state = state_with_second_battery(+400, soc=80)
        with state.lock:
            now = time.time()
            state.rest_surplus_harvest_active = True
            state.rest_surplus_harvest_reason = "HIGH_SMA_SOC"
            state.last_input_power = 2100
            state.battery_soc = 50
            state.actual_zendure_grid_input_power = 2100
            state.actual_zendure_discharge_power = 0
            state.actual_zendure_grid_input_update_epoch = now
            state.actual_zendure_output_home_update_epoch = now
        controller, state, mqtt = make(cfg, state=state, shelly=OkShelly(0))
        controller.run_once(cfg)
        self.assertEqual(2100, state.last_input_power)
        self.assertEqual("EXPORT_CAPTURE", state.harvest_target_selected_by)
        self.assertEqual(2100.0, state.harvest_export_capture_target_w)

    def test_cross_charge_still_blocks_when_primary_discharges(self):
        cfg = cfg_high(CROSS_CHARGE_SIGNIFICANT_W=80)
        state = state_with_second_battery(-500, soc=90)
        with state.lock:
            state.rest_surplus_harvest_active = True
            state.rest_surplus_harvest_reason = "HIGH_SMA_SOC"
            state.last_input_power = 500
            state.battery_soc = 50
        controller, state, mqtt = make(cfg, state=state, shelly=OkShelly(-1000))
        controller.run_once(cfg)
        self.assertLess(state.last_input_power, 500)
        self.assertIn("CROSS_CHARGE", state.active_limiters)

    def test_capacity_is_diagnostic_only(self):
        cfg = cfg_high(ZENDURE_BATTERY_CAPACITY_WH=5280)
        state = state_with_second_battery(+2000, soc=80)
        with state.lock:
            state.sma_battery_capacity_kwh = 13.0
            state.battery_soc = 50
        controller, state, mqtt = make(cfg, state=state, shelly=OkShelly(-500))
        controller.run_once(cfg)
        self.assertEqual("diagnostic", state.harvest_capacity_mode)
        self.assertIsNotNone(state.primary_remaining_capacity_kwh)
        self.assertIsNotNone(state.zendure_remaining_capacity_kwh)


if __name__ == "__main__":
    unittest.main()
