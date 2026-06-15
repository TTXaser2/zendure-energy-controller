import time
import unittest

from tests.test_operation_priority import base_cfg, fresh_state, make_controller, OkShelly
from state import ControllerState
from csv_logger import CSV_FIELDS
from mqtt_bridge import MqttBridge
from mqtt_topic_filter import mqtt_topic_matches_filter


class DummyMsg:
    def __init__(self, topic, payload="42"):
        self.topic = topic
        self.payload = str(payload).encode("utf-8")


class V12811FlowContractTests(unittest.TestCase):
    def _run_full_cycle(self, controller, cfg):
        start = time.time()
        controller.run_once(cfg)
        controller.finish_cycle(cfg, start)

    def test_night_discharge_marks_grid_not_required_but_soc_and_mqtt_required(self):
        cfg = base_cfg(NIGHT_DISCHARGE_ENABLED=True)
        controller, state, mqtt, shelly = make_controller(cfg)
        controller.is_night_discharge_active = lambda _cfg: True

        self._run_full_cycle(controller, cfg)

        self.assertEqual(shelly.calls, 1)
        self.assertEqual(state.current_mode, "NIGHT_DISCHARGE")
        self.assertFalse(state.grid_power_used_for_control)
        self.assertFalse(state.effective_export_power_valid)
        self.assertEqual(state.control_data_quality, "ok")
        self.assertEqual(state.control_missing_required_sources, [])
        self.assertIn("soc", state.control_required_sources)
        self.assertIn("mqtt_command_path", state.control_required_sources)
        self.assertNotIn("grid", state.control_required_sources)
        self.assertTrue(state.soc_valid)
        self.assertTrue(state.mqtt_command_path_valid)

    def test_auto_discharge_marks_grid_soc_and_mqtt_required_and_valid(self):
        cfg = base_cfg(MANUAL_MODE="AUTO", NIGHT_DISCHARGE_ENABLED=False, DEADBAND_W=20)
        controller, state, mqtt, shelly = make_controller(cfg, shelly=OkShelly(250))
        controller.is_night_discharge_active = lambda _cfg: False

        self._run_full_cycle(controller, cfg)

        self.assertEqual(shelly.calls, 1)
        self.assertEqual(state.current_mode, "DISCHARGE")
        self.assertTrue(state.grid_power_used_for_control)
        self.assertTrue(state.grid_power_valid)
        self.assertTrue(state.soc_valid)
        self.assertTrue(state.mqtt_command_path_valid)
        self.assertEqual(state.control_data_quality, "ok")
        self.assertEqual(state.control_missing_required_sources, [])
        self.assertIn("grid", state.control_required_sources)
        self.assertIn("soc", state.control_required_sources)
        self.assertIn("mqtt_command_path", state.control_required_sources)

    def test_soc_stale_safe_state_reports_missing_required_soc_without_grid_dependency(self):
        cfg = base_cfg(NIGHT_DISCHARGE_ENABLED=True)
        state = ControllerState()
        with state.lock:
            state.battery_soc = 80
            state.last_soc_update_epoch = time.time() - 9999
            state.last_output_power = 400
            state.mqtt_connected = True
        controller, state, mqtt, shelly = make_controller(cfg, state=state)
        controller.is_night_discharge_active = lambda _cfg: True

        self._run_full_cycle(controller, cfg)

        self.assertEqual(shelly.calls, 1)
        self.assertEqual(state.current_mode, "SAFE_STATE")
        self.assertIn("SOC_STALE", state.active_limiters)
        self.assertIn("soc", state.control_required_sources)
        self.assertIn("soc", state.control_missing_required_sources)
        self.assertNotIn("grid", state.control_required_sources)
        self.assertFalse(state.soc_valid)
        self.assertEqual(state.soc_validity_reason, "SOC_STALE")
        self.assertEqual(state.control_data_quality, "missing_required_data")

    def test_csv_fields_include_freshness_contract_columns(self):
        self.assertIn("grid_power_validity_reason", CSV_FIELDS)
        self.assertIn("soc_validity_reason", CSV_FIELDS)
        self.assertIn("mqtt_command_path_valid", CSV_FIELDS)
        self.assertIn("control_required_sources", CSV_FIELDS)
        self.assertIn("control_missing_required_sources", CSV_FIELDS)
        self.assertIn("second_battery_validity_reason", CSV_FIELDS)


class V12811MqttDiagnosticFilterTests(unittest.TestCase):
    def test_mqtt_topic_matching_supports_wildcards_and_is_case_sensitive(self):
        self.assertTrue(mqtt_topic_matches_filter("evcc/#", "evcc/site/battery/devices/1/power"))
        self.assertTrue(mqtt_topic_matches_filter("evcc/+/battery/#", "evcc/site/battery/devices/1/power"))
        self.assertTrue(mqtt_topic_matches_filter("Zendure/sensor/+/power", "Zendure/sensor/PACK123/power"))
        self.assertFalse(mqtt_topic_matches_filter("EVCC/#", "evcc/site/battery/devices/1/power"))
        self.assertFalse(mqtt_topic_matches_filter("Zendure/sensor/+/power", "Zendure/sensor/PACK123/socLevel"))

    def test_mqtt_diagnostic_buffer_is_filtered_by_configured_topic(self):
        cfg = base_cfg(
            MQTT_TOPIC_DIAGNOSTIC_ENABLED=True,
            MQTT_TOPIC_DIAGNOSTIC_FILTER="evcc/#",
            MQTT_TOPIC_DIAGNOSTIC_VIEW_MODE="filtered",
            MQTT_TOPIC_DIAGNOSTIC_HISTORY_LIMIT=10,
        )
        state = fresh_state()
        bridge = MqttBridge(state, lambda: cfg)

        bridge.on_message(None, None, DummyMsg("Zendure/sensor/HEC4NENCN492025/electricLevel", "80"))
        bridge.on_message(None, None, DummyMsg("evcc/site/battery/devices/1/power", "120"))

        rows = state.snapshot()["mqtt_topic_diagnostics"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["topic"], "evcc/site/battery/devices/1/power")
        self.assertEqual(rows[0]["diagnostic_filter"], "evcc/#")
        self.assertTrue(rows[0]["diagnostic_filter_matched"])

    def test_mqtt_diagnostic_filter_case_mismatch_captures_nothing_in_filtered_mode(self):
        cfg = base_cfg(
            MQTT_TOPIC_DIAGNOSTIC_ENABLED=True,
            MQTT_TOPIC_DIAGNOSTIC_FILTER="EVCC/#",
            MQTT_TOPIC_DIAGNOSTIC_VIEW_MODE="filtered",
            MQTT_TOPIC_DIAGNOSTIC_HISTORY_LIMIT=10,
        )
        state = fresh_state()
        bridge = MqttBridge(state, lambda: cfg)

        bridge.on_message(None, None, DummyMsg("evcc/site/battery/devices/1/power", "120"))

        self.assertEqual(state.snapshot()["mqtt_topic_diagnostics"], [])

    def test_mqtt_diagnostic_all_mode_keeps_controller_topics(self):
        cfg = base_cfg(
            MQTT_TOPIC_DIAGNOSTIC_ENABLED=True,
            MQTT_TOPIC_DIAGNOSTIC_FILTER="evcc/#",
            MQTT_TOPIC_DIAGNOSTIC_VIEW_MODE="all",
            MQTT_TOPIC_DIAGNOSTIC_HISTORY_LIMIT=10,
        )
        state = fresh_state()
        bridge = MqttBridge(state, lambda: cfg)

        bridge.on_message(None, None, DummyMsg("Zendure/sensor/HEC4NENCN492025/electricLevel", "80"))

        rows = state.snapshot()["mqtt_topic_diagnostics"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["topic"], "Zendure/sensor/HEC4NENCN492025/electricLevel")
        self.assertEqual(rows[0]["diagnostic_view_mode"], "all")
        self.assertFalse(rows[0]["diagnostic_filter_matched"])


if __name__ == "__main__":
    unittest.main()
