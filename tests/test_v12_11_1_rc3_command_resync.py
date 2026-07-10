import time
import unittest
from datetime import datetime

from controller_logic import ZendureController
from state import ControllerState
from tests.test_operation_priority import DummyConfigManager, RecordingMqtt, OkShelly, NoopCsv, NoopZendureApi, NoopLogger, base_cfg, fresh_state
from web_ui import fixed_mode_projection_text


class Rc3CommandResyncTests(unittest.TestCase):
    def make_controller(self, cfg=None, state=None, mqtt=None):
        cfg = cfg or base_cfg()
        state = state or fresh_state(80)
        mqtt = mqtt or RecordingMqtt()
        return ZendureController(DummyConfigManager(cfg), state, mqtt, OkShelly(0), NoopCsv(), NoopZendureApi(), NoopLogger()), state, mqtt, cfg

    def test_active_nonzero_command_during_no_live_mqtt_is_marked_uncertain(self):
        controller, state, mqtt, cfg = self.make_controller()
        with state.lock:
            state.zendure_mqtt_overall_status = "ZENDURE_MQTT_NO_LIVE"
            state.zendure_mqtt_live_confirmed = False

        controller._publish_signed_target(-400)

        self.assertTrue(state.command_uncertain_mqtt_active)
        self.assertEqual(-400, state.command_uncertain_mqtt_target_w)
        self.assertIn("ZENDURE_MQTT_NO_LIVE", state.command_uncertain_mqtt_status)
        self.assertIn(("ac", "Output mode", False), mqtt.commands)
        self.assertIn(("output", 400, False), mqtt.commands)

    def test_mqtt_recovery_forces_full_resend_of_active_target(self):
        controller, state, mqtt, cfg = self.make_controller()
        controller._last_zendure_mqtt_status = "ZENDURE_MQTT_NO_LIVE"
        with state.lock:
            state.last_input_power = 0
            state.last_output_power = 400
            state.actual_zendure_system_signed_power = 0
            state.actual_zendure_power_valid = True
            state.last_zendure_power_update_epoch = time.time()
            state.zendure_mqtt_overall_status = "ZENDURE_MQTT_OK"
            state.zendure_mqtt_live_confirmed = True
            state.command_uncertain_mqtt_active = True
            state.command_uncertain_mqtt_target_w = -400

        controller.update_command_effect_monitor(cfg)

        self.assertEqual(1, state.command_resync_count)
        self.assertFalse(state.command_uncertain_mqtt_active)
        self.assertIn(("ac", "Output mode", True), mqtt.commands)
        self.assertIn(("input", 0, True), mqtt.commands)
        self.assertIn(("output", 400, True), mqtt.commands)

    def test_missing_device_effect_sets_command_not_effective_and_limiter(self):
        cfg = base_cfg(COMMAND_EFFECT_TIMEOUT_SECONDS=10, COMMAND_EFFECT_FORCE_RESEND_SECONDS=999)
        controller, state, mqtt, cfg = self.make_controller(cfg=cfg)
        controller._last_zendure_mqtt_status = "ZENDURE_MQTT_OK"
        controller._command_effect_watch_target = -400
        controller._command_effect_watch_start_epoch = time.time() - 20
        with state.lock:
            state.last_output_power = 400
            state.actual_zendure_system_signed_power = 0
            state.actual_zendure_power_valid = True
            state.last_zendure_power_update_epoch = time.time()
            state.zendure_mqtt_overall_status = "ZENDURE_MQTT_OK"
            state.zendure_mqtt_live_confirmed = True

        controller.update_command_effect_monitor(cfg)

        self.assertTrue(state.command_not_effective_active)
        self.assertIn("COMMAND_NOT_EFFECTIVE", state.active_limiters)
        self.assertIn("Soll -400 W", state.command_not_effective_reason)

    def test_fixed_discharge_projection_mentions_target_eta_and_followup(self):
        cfg = base_cfg(
            MANUAL_FIXED_DISCHARGE_POWER_W=400,
            MANUAL_FIXED_DISCHARGE_TARGET_SOC=65,
            MANUAL_DISCHARGE_AFTER_TARGET="STOP_HOLD",
            ZENDURE_BATTERY_CAPACITY_WH=5280,
        )
        text = fixed_mode_projection_text(cfg, {"battery_soc": 85}, "MANUAL_FIXED_DISCHARGE")
        self.assertIn("Manuelle feste Entladung bis 65 % SOC", text)
        self.assertIn("voraussichtlich erreicht um", text)
        self.assertIn("danach STOP_HOLD", text)

    def test_fixed_charge_projection_mentions_target_eta_and_followup(self):
        cfg = base_cfg(
            MANUAL_FIXED_CHARGE_POWER_W=800,
            MANUAL_FIXED_CHARGE_TARGET_SOC=90,
            MANUAL_CHARGE_AFTER_TARGET="AUTO",
            ZENDURE_BATTERY_CAPACITY_WH=5280,
        )
        text = fixed_mode_projection_text(cfg, {"battery_soc": 50}, "MANUAL_FIXED_CHARGE")
        self.assertIn("Manuelle feste Ladung bis 90 % SOC", text)
        self.assertIn("voraussichtlich erreicht um", text)
        self.assertIn("danach Automatik-Modus", text)


if __name__ == "__main__":
    unittest.main()
