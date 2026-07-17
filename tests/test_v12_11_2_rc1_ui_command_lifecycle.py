import time
import unittest

# Import test_operation_priority first; it installs the paho-mqtt test stub.
from tests.test_operation_priority import DummyConfigManager, RecordingMqtt, OkShelly, NoopCsv, NoopZendureApi, NoopLogger, base_cfg, fresh_state
from controller_logic import ZendureController
from state import ControllerState
from web_ui import build_status_page


class V12112Rc1CommandLifecycleAndUiTests(unittest.TestCase):
    def make_controller(self, cfg=None, state=None, mqtt=None):
        cfg = cfg or base_cfg()
        state = state or fresh_state(80)
        mqtt = mqtt or RecordingMqtt()
        return ZendureController(DummyConfigManager(cfg), state, mqtt, OkShelly(0), NoopCsv(), NoopZendureApi(), NoopLogger()), state, mqtt, cfg

    def _active_discharge_state(self, state, target=-400, actual=0, status="ZENDURE_MQTT_OK", live=True):
        with state.lock:
            state.last_input_power = 0
            state.last_output_power = abs(target)
            state.actual_zendure_system_signed_power = actual
            state.actual_zendure_power_valid = True
            state.last_zendure_power_update_epoch = time.time()
            state.zendure_mqtt_overall_status = status
            state.zendure_mqtt_live_confirmed = live

    def test_short_partial_stale_recovery_does_not_resync_identical_target(self):
        cfg = base_cfg(COMMAND_RESYNC_ON_MQTT_RECOVERY_ALWAYS=False, COMMAND_RESYNC_STALE_MIN_SECONDS=30, COMMAND_RESYNC_STALE_MIN_CYCLES=3)
        controller, state, mqtt, cfg = self.make_controller(cfg=cfg)
        controller._last_zendure_mqtt_status = "ZENDURE_MQTT_PARTIAL_STALE"
        controller._mqtt_uncertain_since_epoch = time.time() - 1
        controller._mqtt_uncertain_cycles = 1
        self._active_discharge_state(state, target=-400, actual=-390, status="ZENDURE_MQTT_OK", live=True)

        controller.update_command_effect_monitor(cfg)

        self.assertEqual([], mqtt.commands)
        self.assertEqual(0, state.command_resync_count)
        self.assertFalse(state.command_not_effective_active)

    def test_long_stale_recovery_resends_even_if_target_is_identical(self):
        cfg = base_cfg(COMMAND_RESYNC_ON_MQTT_RECOVERY_ALWAYS=False, COMMAND_RESYNC_STALE_MIN_SECONDS=30, COMMAND_RESYNC_STALE_MIN_CYCLES=3)
        controller, state, mqtt, cfg = self.make_controller(cfg=cfg)
        controller._last_zendure_mqtt_status = "ZENDURE_MQTT_STALE"
        controller._mqtt_uncertain_since_epoch = time.time() - 45
        controller._mqtt_uncertain_cycles = 2
        self._active_discharge_state(state, target=-400, actual=0, status="ZENDURE_MQTT_OK", live=True)

        controller.update_command_effect_monitor(cfg)

        self.assertEqual(1, state.command_resync_count)
        self.assertIn(("ac", "Output mode", True), mqtt.commands)
        self.assertIn(("input", 0, True), mqtt.commands)
        self.assertIn(("output", 400, True), mqtt.commands)

    def test_command_not_effective_recovers_deterministically_when_actual_matches_target(self):
        cfg = base_cfg(COMMAND_EFFECT_TOLERANCE_W=80)
        controller, state, mqtt, cfg = self.make_controller(cfg=cfg)
        controller._last_zendure_mqtt_status = "ZENDURE_MQTT_OK"
        controller._command_effect_watch_target = -400
        controller._command_effect_watch_start_epoch = time.time() - 300
        self._active_discharge_state(state, target=-400, actual=-390, status="ZENDURE_MQTT_OK", live=True)
        with state.lock:
            state.command_not_effective_active = True
            state.command_not_effective_duration_s = 300
            state.add_limiter("COMMAND_NOT_EFFECTIVE")

        controller.update_command_effect_monitor(cfg)

        self.assertFalse(state.command_not_effective_active)
        self.assertNotIn("COMMAND_NOT_EFFECTIVE", state.active_limiters)
        self.assertEqual("COMMAND_EFFECTIVE", state.command_effect_category)

    def test_uncertain_telemetry_is_not_reported_as_confirmed_device_failure(self):
        cfg = base_cfg(COMMAND_EFFECT_TIMEOUT_SECONDS=10)
        controller, state, mqtt, cfg = self.make_controller(cfg=cfg)
        controller._last_zendure_mqtt_status = "ZENDURE_MQTT_OK"
        controller._command_effect_watch_target = -400
        controller._command_effect_watch_start_epoch = time.time() - 30
        self._active_discharge_state(state, target=-400, actual=0, status="ZENDURE_MQTT_STALE", live=False)

        controller.update_command_effect_monitor(cfg)

        self.assertFalse(state.command_not_effective_active)
        self.assertNotIn("COMMAND_NOT_EFFECTIVE", state.active_limiters)
        self.assertEqual("COMMAND_TELEMETRY_UNCERTAIN", state.command_effect_category)

    def test_new_status_page_contains_top_cards_snapshot_and_day_graph_navigation(self):
        cfg = base_cfg()
        snapshot = ControllerState().snapshot()
        snapshot.update({"battery_soc": 82, "grid_power": -120, "raw_grid_power": -120, "grid_power_valid": True, "current_mode": "AUTO"})
        html = build_status_page(cfg, snapshot)
        self.assertIn("Netzleistung", html)
        self.assertIn("Betriebsmodus", html)
        self.assertIn("Zendure / Batterie", html)
        self.assertIn("Primärspeicher", html)
        self.assertIn("Netzleistungsquelle", html)
        self.assertIn("/status-view-data", html)
        self.assertIn("/storage-soc-day-data?date=", html)
        self.assertIn("dayPrev", html)
        self.assertIn("dayToday", html)
        self.assertIn("dayNext", html)


if __name__ == "__main__":
    unittest.main()
