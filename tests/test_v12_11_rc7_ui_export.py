import json
import os
import tempfile
import unittest
from pathlib import Path

from config_manager import DEFAULT_CONFIG
from web_ui import build_nav_bar, build_graph_view_payload, measurement_availability, build_soc_day_payload
from state import ControllerState


class TestRC7UiExport(unittest.TestCase):
    def test_example_config_contains_no_private_zendure_id(self):
        cfg = json.loads(Path("config.example.json").read_text())
        self.assertNotIn("TEST_DEVICE_001", json.dumps(cfg))
        self.assertNotEqual("TEST_DEVICE_001", DEFAULT_CONFIG.get("DEVICE_ID"))
        self.assertEqual("REPLACE_WITH_ZENDURE_DEVICE_ID", cfg.get("DEVICE_ID"))

    def test_navbar_is_compact_and_graph_csv_is_not_direct_nav_link(self):
        html = build_nav_bar(dict(DEFAULT_CONFIG, REPLAY_WEB_PORT=9))
        self.assertIn('href="/graph"', html)
        self.assertIn('>Graph<', html)
        self.assertIn('href="/measurements"', html)
        self.assertIn('>Messdaten-CSV<', html)
        self.assertIn('>Handbuch<', html)
        self.assertNotIn('/graph-data.csv', html)
        self.assertNotIn('Download Graph CSV', html)
        self.assertNotIn('Download Handbuch', html)

    def test_measurement_availability_logging_disabled_without_files_is_clear(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = dict(DEFAULT_CONFIG)
            cfg["MEASUREMENT_LOG_MODE"] = "off"
            cfg["MEASUREMENT_LOG_DIR"] = td
            cfg["MEASUREMENT_LOG_FALLBACK_DIR"] = os.path.join(td, "fallback")
            cfg["MEASUREMENT_LOG_FILE"] = "zendure_measurements.csv"
            res = measurement_availability(cfg)
            self.assertFalse(res["available"])
            self.assertFalse(res["logging_active"])
            self.assertEqual(0, res["readable_file_count"])

    def test_graph_view_payload_uses_ram_without_measurement_logs(self):
        state = ControllerState()
        state.graph_history.append({
            "date": "2026-07-01",
            "timestamp": "12:00:00",
            "grid_power_w": -12.5,
            "zendure_target_power_w": 100.0,
            "zendure_actual_power_w": 95.0,
            "soc": 78,
            "mode": "AUTO",
            "mode_label": "AUTO",
            "control_reason": "test",
        })
        payload = build_graph_view_payload(dict(DEFAULT_CONFIG), state.snapshot(), range_name="live", resolution="live")
        self.assertEqual("ram_graph_history", payload["source"])
        self.assertEqual(1, len(payload["points"]))
        self.assertTrue(payload["kpis"]["grid_power_w"]["available"])

    def test_soc_day_payload_is_nonfatal_without_logs(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = dict(DEFAULT_CONFIG)
            cfg["MEASUREMENT_LOG_DIR"] = td
            state = ControllerState()
            state.battery_soc = 55
            state.soc_valid = True
            state.zendure_telemetry_source = "MQTT"
            payload = build_soc_day_payload(cfg, state.snapshot())
            self.assertGreaterEqual(len(payload["points"]), 1)
            self.assertEqual(55, payload["points"][-1]["soc"])


if __name__ == "__main__":
    unittest.main()
