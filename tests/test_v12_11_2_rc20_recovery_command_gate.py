import time
import unittest

# Import the shared test doubles first; that module installs the lightweight
# paho stub required by controller_logic in the test environment.
from tests.test_operation_priority import RecordingMqtt, OkShelly, NoopCsv, NoopZendureApi, NoopLogger, base_cfg
from controller_logic import ZendureController
from state import ControllerState


class RecoveryConfigManager:
    def __init__(self, cfg):
        self.cfg = dict(cfg)
        self.ready_values = []

    def get(self):
        return dict(self.cfg)

    def control_allowed(self):
        return False

    def startup_mode(self):
        return "RECOVERY_LAST_GOOD_WAITING_PREFLIGHT"

    def observe_ready(self, value):
        self.ready_values.append(bool(value))
        return {"promoted": False, "startup_mode": self.startup_mode()}


class Rc20RecoveryCommandGateTests(unittest.TestCase):
    def make_controller(self):
        cfg = base_cfg()
        manager = RecoveryConfigManager(cfg)
        state = ControllerState()
        with state.lock:
            state.mqtt_connected = True
            state.battery_soc = 80
            state.last_soc_update_epoch = time.time()
        mqtt = RecordingMqtt()
        controller = ZendureController(manager, state, mqtt, OkShelly(0), NoopCsv(), NoopZendureApi(), NoopLogger())
        return controller, manager, state, mqtt, cfg

    def test_recovery_waiting_performs_passive_cycle_without_mqtt_commands(self):
        controller, manager, state, mqtt, cfg = self.make_controller()
        controller.run_once(cfg)
        self.assertEqual([], mqtt.commands)
        self.assertEqual("RECOVERY_LAST_GOOD_WAITING_PREFLIGHT", state.current_mode)
        self.assertEqual("CONFIG_RECOVERY_PREFLIGHT", state.technical_control_path)
        self.assertEqual(0, state.current_target_power)

    def test_finish_cycle_skips_command_effect_recovery_when_gate_closed(self):
        controller, manager, state, mqtt, cfg = self.make_controller()
        controller.update_command_effect_monitor = lambda _cfg: (_ for _ in ()).throw(AssertionError("must not execute"))
        controller.run_once(cfg)
        controller.finish_cycle(cfg, time.time())
        self.assertEqual([], mqtt.commands)


if __name__ == "__main__":
    unittest.main()
