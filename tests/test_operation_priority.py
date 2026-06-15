import sys
import time
import types
import unittest

# Unit tests use a RecordingMqtt fake. controller_logic imports mqtt_bridge for
# type hints, and mqtt_bridge imports paho-mqtt, which is not required here.
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
from state import ControllerState


class DummyConfigManager:
    def __init__(self, cfg):
        self.cfg = dict(cfg)
        self.saved = []

    def get(self):
        return self.cfg

    def save(self, cfg):
        self.saved.append(dict(cfg))
        self.cfg = dict(cfg)


class RecordingMqtt:
    def __init__(self):
        self.commands = []

    def set_ac_mode(self, mode, force=False):
        self.commands.append(("ac", mode, force))

    def set_input_limit(self, value, force=False):
        self.commands.append(("input", int(value), force))

    def set_output_limit(self, value, force=False):
        self.commands.append(("output", int(value), force))


class FailingShelly:
    def __init__(self):
        self.calls = 0

    def read_grid_power(self, cfg):
        self.calls += 1
        raise RuntimeError("UniMeter nicht erreichbar")


class OkShelly:
    def __init__(self, value):
        self.value = value
        self.calls = 0

    def read_grid_power(self, cfg):
        self.calls += 1
        return self.value


class NoopCsv:
    def log(self, cfg, row):
        pass


class NoopZendureApi:
    def should_poll(self, cfg):
        return False


class NoopLogger:
    def log(self, cfg, message):
        pass


def base_cfg(**overrides):
    cfg = dict(DEFAULT_CONFIG)
    cfg.update({
        "DEBUG": False,
        "LOG_VALUES": False,
        "LOG_CONTROL": False,
        "LOG_MANUAL": False,
        "LOG_MQTT": False,
        "LOG_SOC": False,
        "SAFE_STATE_ON_SHELLY_ERROR": True,
        "SHELLY_STALE_TIMEOUT_SECONDS": 1,
        "MIN_SOC_PERCENT": 15,
        "MAX_SOC_PERCENT": 99,
        "NIGHT_DISCHARGE_POWER_W": 400,
        "MANUAL_FIXED_DISCHARGE_POWER_W": 600,
        "MANUAL_FIXED_DISCHARGE_TARGET_SOC": 30,
        "MANUAL_FIXED_CHARGE_POWER_W": 700,
        "MANUAL_FIXED_CHARGE_TARGET_SOC": 90,
    })
    cfg.update(overrides)
    return cfg


def fresh_state(soc=80):
    state = ControllerState()
    now = time.time()
    with state.lock:
        state.battery_soc = soc
        state.last_soc_update_epoch = now
        state.mqtt_connected = True
    return state


def make_controller(cfg, state=None, shelly=None, mqtt=None):
    state = state or fresh_state()
    mqtt = mqtt or RecordingMqtt()
    shelly = shelly or FailingShelly()
    controller = ZendureController(
        DummyConfigManager(cfg),
        state,
        mqtt,
        shelly,
        NoopCsv(),
        NoopZendureApi(),
        NoopLogger(),
    )
    return controller, state, mqtt, shelly


class OperationPriorityTests(unittest.TestCase):
    def test_night_discharge_refreshes_grid_for_display_but_does_not_depend_on_it(self):
        cfg = base_cfg(NIGHT_DISCHARGE_ENABLED=True)
        controller, state, mqtt, shelly = make_controller(cfg)
        controller.is_night_discharge_active = lambda _cfg: True

        controller.run_once(cfg)

        self.assertEqual(shelly.calls, 1)
        self.assertEqual(state.current_mode, "NIGHT_DISCHARGE")
        self.assertIn(("output", 400, False), mqtt.commands)
        self.assertNotIn(("output", 0, True), mqtt.commands)
        self.assertNotIn("SHELLY_STALE", state.active_limiters)
        self.assertFalse(state.grid_power_used_for_control)

    def test_night_discharge_still_requires_fresh_soc(self):
        cfg = base_cfg(NIGHT_DISCHARGE_ENABLED=True)
        state = ControllerState()
        with state.lock:
            state.battery_soc = 80
            state.last_soc_update_epoch = time.time() - 9999
            state.last_output_power = 400
        controller, state, mqtt, shelly = make_controller(cfg, state=state)
        controller.is_night_discharge_active = lambda _cfg: True

        controller.run_once(cfg)

        self.assertEqual(shelly.calls, 1)
        self.assertEqual(state.current_mode, "SAFE_STATE")
        self.assertIn("SOC_STALE", state.active_limiters)
        self.assertIn(("output", 0, True), mqtt.commands)

    def test_manual_fixed_discharge_does_not_depend_on_shelly_grid_data(self):
        cfg = base_cfg(MANUAL_MODE="FIXED_DISCHARGE")
        controller, state, mqtt, shelly = make_controller(cfg)

        controller.run_once(cfg)

        self.assertEqual(shelly.calls, 1)
        self.assertEqual(state.current_mode, "MANUAL_FIXED_DISCHARGE")
        self.assertIn(("output", 600, False), mqtt.commands)

    def test_manual_fixed_charge_does_not_depend_on_shelly_grid_data(self):
        cfg = base_cfg(MANUAL_MODE="FIXED_CHARGE")
        controller, state, mqtt, shelly = make_controller(cfg, state=fresh_state(40))

        controller.run_once(cfg)

        self.assertEqual(shelly.calls, 1)
        self.assertEqual(state.current_mode, "MANUAL_FIXED_CHARGE")
        self.assertIn(("input", 700, False), mqtt.commands)

    def test_manual_stop_hold_does_not_depend_on_shelly_or_soc(self):
        cfg = base_cfg(MANUAL_MODE="STOP_HOLD")
        state = ControllerState()
        with state.lock:
            state.battery_soc = None
            state.last_input_power = 350
            state.last_output_power = 0
        controller, state, mqtt, shelly = make_controller(cfg, state=state)

        controller.run_once(cfg)

        self.assertEqual(shelly.calls, 1)
        self.assertEqual(state.current_mode, "STOP_HOLD")
        self.assertIn(("input", 0, True), mqtt.commands)

    def test_auto_grid_control_keeps_shelly_safe_state_behavior(self):
        cfg = base_cfg(MANUAL_MODE="AUTO", NIGHT_DISCHARGE_ENABLED=False)
        controller, state, mqtt, shelly = make_controller(cfg)
        controller.is_night_discharge_active = lambda _cfg: False

        controller.run_once(cfg)

        self.assertEqual(shelly.calls, 1)
        self.assertEqual(state.current_mode, "SAFE_STATE")
        self.assertIn("SHELLY_STALE", state.active_limiters)

    def test_auto_normal_control_still_uses_shelly_grid_data(self):
        cfg = base_cfg(MANUAL_MODE="AUTO", NIGHT_DISCHARGE_ENABLED=False, DEADBAND_W=80)
        controller, state, mqtt, shelly = make_controller(cfg, shelly=OkShelly(250))
        controller.is_night_discharge_active = lambda _cfg: False

        controller.run_once(cfg)

        self.assertEqual(shelly.calls, 1)
        self.assertEqual(state.current_mode, "DISCHARGE")
        self.assertTrue(any(cmd[0] == "output" and cmd[1] > 0 for cmd in mqtt.commands))


if __name__ == "__main__":
    unittest.main()
