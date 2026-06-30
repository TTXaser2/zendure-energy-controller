import unittest
from unittest.mock import Mock

import requests

from measurement_v4 import build_v4_row
from state import ControllerState
from zendure_local_api import ZendureLocalApiClient


class Rc4GridSourceTests(unittest.TestCase):
    def test_recorded_grid_source_follows_active_sma_source(self):
        state = ControllerState()
        state.raw_grid_source = "SMA Home Manager direkt (UDP)"
        state.raw_grid_power = 2.0
        state.grid_power = 2.0
        state.grid_power_valid = True
        state.grid_power_fresh = True
        state.grid_power_available = True
        state.record_graph_point(10)
        row = state.graph_history[-1]
        self.assertEqual(row["raw_grid_source"], "SMA Home Manager direkt (UDP)")
        v4 = build_v4_row({"MEASUREMENT_LOG_MODE": "standard"}, row)
        self.assertEqual(v4["grid_power_source"], "SMA")

    def test_shelly_compatible_source_stays_shelly_in_v4(self):
        state = ControllerState()
        state.raw_grid_source = "Shelly-kompatible HTTP-Quelle"
        state.raw_grid_power = 10.0
        state.grid_power = 10.0
        state.grid_power_valid = True
        state.grid_power_fresh = True
        state.grid_power_available = True
        state.record_graph_point(10)
        row = state.graph_history[-1]
        v4 = build_v4_row({"MEASUREMENT_LOG_MODE": "standard"}, row)
        self.assertEqual(v4["grid_power_source"], "SHELLY")


class Rc4LocalApiBackoffTests(unittest.TestCase):
    def test_disabled_telemetry_never_polls(self):
        client = ZendureLocalApiClient()
        cfg = {
            "ZENDURE_LOCAL_API_USE_FOR_TELEMETRY": False,
            "ZENDURE_LOCAL_IP": "192.168.0.41",
        }
        self.assertFalse(client.should_poll(cfg))

    def test_failed_request_counts_as_poll_and_enters_backoff(self):
        client = ZendureLocalApiClient()
        client.session.get = Mock(side_effect=requests.Timeout("timeout"))
        cfg = {
            "ZENDURE_LOCAL_API_USE_FOR_TELEMETRY": True,
            "ZENDURE_LOCAL_IP": "192.168.0.41",
            "ZENDURE_LOCAL_API_POLL_INTERVAL_SECONDS": 5,
            "ZENDURE_LOCAL_API_TIMEOUT_SECONDS": 5,
            "ZENDURE_LOCAL_API_CONTROL_TIMEOUT_CAP_SECONDS": 0.2,
            "ZENDURE_LOCAL_API_ERROR_BACKOFF_SECONDS": 30,
        }
        self.assertTrue(client.should_poll(cfg))
        with self.assertRaises(requests.Timeout):
            client.fetch_report(cfg)
        self.assertIsNotNone(client.last_poll_epoch)
        self.assertIsNotNone(client.backoff_until_epoch)
        self.assertEqual(client.consecutive_error_count, 1)
        self.assertFalse(client.should_poll(cfg))

    def test_success_clears_backoff(self):
        client = ZendureLocalApiClient()
        response = Mock()
        response.raise_for_status = Mock()
        response.json = Mock(return_value={"properties": {"electricLevel": 80}})
        client.session.get = Mock(return_value=response)
        cfg = {
            "ZENDURE_LOCAL_API_USE_FOR_TELEMETRY": True,
            "ZENDURE_LOCAL_IP": "192.168.0.41",
            "ZENDURE_LOCAL_API_POLL_INTERVAL_SECONDS": 5,
            "ZENDURE_LOCAL_API_TIMEOUT_SECONDS": 5,
            "ZENDURE_LOCAL_API_CONTROL_TIMEOUT_CAP_SECONDS": 0.2,
            "ZENDURE_LOCAL_API_ERROR_BACKOFF_SECONDS": 30,
        }
        client.backoff_until_epoch = 0
        client.consecutive_error_count = 2
        report = client.fetch_report(cfg)
        self.assertEqual(report["properties"]["electricLevel"], 80)
        self.assertIsNone(client.backoff_until_epoch)
        self.assertEqual(client.consecutive_error_count, 0)


class Rc4SourceTextTests(unittest.TestCase):
    def test_no_status_source_hardcoding_left(self):
        from pathlib import Path
        text = Path("web_ui.py").read_text(encoding="utf-8")
        self.assertNotIn("Quelle: Shelly/UniMeter", text)
        self.assertIn("raw_grid_source", text)

    def test_sma_listener_socket_mode_is_configurable(self):
        from pathlib import Path
        text = Path("sma_energy_meter.py").read_text(encoding="utf-8")
        self.assertIn("SMA_ENERGY_METER_SOCKET_MODE", Path("config.example.json").read_text(encoding="utf-8"))
        self.assertIn("rc3_compatible", text)
        self.assertIn("SO_REUSEPORT", text)


if __name__ == "__main__":
    unittest.main()
