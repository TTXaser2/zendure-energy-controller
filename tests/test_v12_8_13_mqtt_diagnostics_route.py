import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from config_manager import ConfigManager, DEFAULT_CONFIG
from state import ControllerState
from web_ui import create_app


class V12813MqttDiagnosticsRouteTests(unittest.TestCase):
    def make_client(self, headless=False):
        tempdir = tempfile.TemporaryDirectory()
        cfg_path = os.path.join(tempdir.name, "config.json")
        cfg = dict(DEFAULT_CONFIG)
        cfg["HEADLESS_MODE"] = headless
        manager = ConfigManager(cfg_path)
        manager.save(cfg, create_last_good=False)
        state = ControllerState()
        app = create_app(manager, state)
        client = TestClient(app)
        self.addCleanup(tempdir.cleanup)
        return client, state

    def test_get_mqtt_diagnostics_route_returns_page(self):
        client, state = self.make_client()
        state.add_mqtt_diagnostic(
            "evcc/site/battery",
            "123",
            diagnostic_filter="evcc/#",
            diagnostic_filter_matched=True,
        )

        response = client.get("/mqtt-diagnostics")

        self.assertEqual(response.status_code, 200)
        self.assertIn("MQTT Topic-Diagnose", response.text)
        self.assertIn("Diagnosetabelle leeren", response.text)
        self.assertIn("evcc/site/battery", response.text)

    def test_clear_route_redirects_and_page_shows_cleared_notice(self):
        client, state = self.make_client()
        state.add_mqtt_diagnostic(
            "evcc/site/battery",
            "123",
            diagnostic_filter="evcc/#",
            diagnostic_filter_matched=True,
        )

        response = client.post("/mqtt-diagnostics/clear", follow_redirects=False)

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/mqtt-diagnostics?cleared=1")
        self.assertEqual(state.snapshot()["mqtt_topic_diagnostics"], [])

        page = client.get(response.headers["location"])
        self.assertEqual(page.status_code, 200)
        self.assertIn("Diagnosetabelle wurde geleert", page.text)

    def test_get_mqtt_diagnostics_route_respects_headless_mode(self):
        client, state = self.make_client(headless=True)
        state.add_mqtt_diagnostic(
            "evcc/site/battery",
            "123",
            diagnostic_filter="evcc/#",
            diagnostic_filter_matched=True,
        )

        response = client.get("/mqtt-diagnostics")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Headless Mode", response.text)
        self.assertNotIn("evcc/site/battery", response.text)


if __name__ == "__main__":
    unittest.main()
