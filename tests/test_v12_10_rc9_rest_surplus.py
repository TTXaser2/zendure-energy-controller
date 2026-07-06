import csv
import sys
import time
import types
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

from config_manager import DEFAULT_CONFIG
from controller_logic import ZendureController
from measurement_v4 import build_v4_row
from state import ControllerState
from tests.test_operation_priority import DummyConfigManager, RecordingMqtt, OkShelly, NoopCsv, NoopZendureApi, NoopLogger, fresh_state
from tests.test_v12_10_rc6_cross_charge import state_with_second_battery


def cfg_rc9(**overrides):
    cfg = dict(DEFAULT_CONFIG)
    cfg.update({
        "MANUAL_MODE": "AUTO",
        "NIGHT_DISCHARGE_ENABLED": False,
        "CROSS_CHARGE_ENABLED": True,
        "SECOND_BATTERY_DISCHARGE_SIGN": 1,
        "SECOND_BATTERY_MAX_CHARGE_POWER_W": 2300,
        "REST_SURPLUS_HARVEST_ENABLED": True,
        "REST_SURPLUS_MIN_EXPORT_W": 80,
        "REST_SURPLUS_ENTRY_CONFIRM_SECONDS": 30,
        "SECOND_BATTERY_CHARGE_SATURATION_MARGIN_W": 100,
        "HARVEST_HIGH_SMA_SOC_ENABLED": False,
        "HARVEST_HIGH_SMA_SOC_TIME_PROFILE_ENABLED": False,
        "MIN_EFFECTIVE_SURPLUS_FOR_CHARGE_W": 150,
        "CONTROL_GAIN": 1.0,
        "SMOOTHING_FACTOR": 1.0,
        "MAX_POWER_STEP_W": 5000,
        "MAX_CHARGE_POWER_W": 2400,
        "MAX_DISCHARGE_POWER_W": 2400,
        "DEADBAND_W": 20,
        "INTERVAL_SECONDS": 3,
        "MODE_CHANGE_LOCK_SECONDS": 0,
    })
    cfg.update(overrides)
    return cfg


def make(cfg, state=None, shelly=None):
    state = state or state_with_second_battery(+2250, soc=50)
    mqtt = RecordingMqtt()
    controller = ZendureController(DummyConfigManager(cfg), state, mqtt, shelly or OkShelly(-100), NoopCsv(), NoopZendureApi(), NoopLogger())
    controller.is_night_discharge_active = lambda _cfg: False
    return controller, state, mqtt


class RestSurplusHarvestRc9Tests(unittest.TestCase):
    def test_entry_requires_confirmed_duration_before_charging(self):
        cfg = cfg_rc9()
        controller, state, mqtt = make(cfg)
        for _ in range(9):
            controller.run_once(cfg)
            self.assertFalse(state.rest_surplus_harvest_active)
            self.assertEqual(0, state.last_input_power)
        controller.run_once(cfg)
        self.assertTrue(state.rest_surplus_harvest_active)
        self.assertGreaterEqual(state.rest_surplus_entry_progress_s, 30)
        self.assertEqual(100, state.last_input_power)
        self.assertIn("REST_SURPLUS_HARVEST", state.active_limiters)
        self.assertIn("Restüberschuss-Ernte", state.control_reason)
        self.assertIn(("input", 100, False), mqtt.commands)

    def test_harvest_stays_active_and_holds_when_sma_charge_drops_but_no_import(self):
        cfg = cfg_rc9()
        state = state_with_second_battery(+2250, soc=50)
        with state.lock:
            state.rest_surplus_harvest_active = True
            state.last_input_power = 200
        controller, state, mqtt = make(cfg, state=state, shelly=OkShelly(0))
        controller.run_once(cfg)
        self.assertTrue(state.rest_surplus_harvest_active)
        self.assertEqual(200, state.last_input_power)
        self.assertEqual("HOLD", state.current_mode)

    def test_grid_import_reduces_existing_harvest_charge(self):
        cfg = cfg_rc9(MAX_POWER_STEP_W=50, SMA_GUARD_RAMP_DOWN_W=50)
        state = state_with_second_battery(+1000, soc=50)
        with state.lock:
            state.rest_surplus_harvest_active = True
            state.last_input_power = 200
        controller, state, mqtt = make(cfg, state=state, shelly=OkShelly(+250))
        controller.run_once(cfg)
        self.assertEqual(150, state.last_input_power)
        self.assertEqual("GRID_IMPORT_REDUCE", state.rest_surplus_exit_reason)

    def test_v4_row_contains_harvest_diagnostics_and_reason(self):
        row = {
            "mode": "CHARGE",
            "epoch_s": 1780000000.0,
            "cycle_id": 1,
            "control_reason": "Restüberschuss-Ernte: Primärspeicher nahe Ladegrenze",
            "target_final_w": 300,
            "rest_surplus_harvest_active": True,
            "rest_surplus_harvest_eligible": True,
            "rest_surplus_entry_progress_s": 30,
            "rest_surplus_exit_reason": "",
            "second_battery_charge_pressure_w": 2380,
            "second_battery_charge_saturation_threshold_w": 2200,
            "rest_surplus_export_w": 300,
            "grid_power_valid": True,
            "grid_power_fresh": True,
            "soc_valid": True,
            "soc_fresh": True,
            "mqtt_command_required": True,
            "mqtt_command_sent": True,
            "zendure_mqtt_connected": True,
        }
        v4 = build_v4_row(cfg_rc9(), row)
        self.assertEqual("REST_SURPLUS_HARVEST", v4["target_final_reason"])
        self.assertEqual("1", v4["rest_surplus_harvest_active"])
        self.assertEqual(2380.0, v4["second_battery_charge_pressure_w"])


if __name__ == "__main__":
    unittest.main()
