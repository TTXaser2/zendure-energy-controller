import os
import tempfile
import unittest

from config_manager import ConfigManager, DEFAULT_CONFIG
from state import ControllerState
from web_ui import build_mqtt_diagnostics_page, create_app


class V12814MqttDiagnosticsPollingTests(unittest.TestCase):
    def make_app(self, headless=False):
        tempdir = tempfile.TemporaryDirectory()
        cfg_path = os.path.join(tempdir.name, "config.json")
        cfg = dict(DEFAULT_CONFIG)
        cfg["HEADLESS_MODE"] = headless
        manager = ConfigManager(cfg_path)
        manager.save(cfg, create_last_good=False)
        state = ControllerState()
        app = create_app(manager, state)
        self.addCleanup(tempdir.cleanup)
        return app, state

    def endpoint(self, app, path, method):
        method = method.upper()
        for route in app.routes:
            if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
                return route.endpoint
        raise AssertionError(f"Route {method} {path} not found")

    def test_diagnostics_page_contains_polling_endpoint_and_manual_refresh(self):
        cfg = dict(DEFAULT_CONFIG)
        html = build_mqtt_diagnostics_page(cfg, [])

        self.assertIn("/mqtt-diagnostics/data", html)
        self.assertIn("refreshMqttDiagnostics", html)
        self.assertIn("Aktualisieren", html)
        self.assertIn("Live-Aktualisierung", html)

    def test_data_endpoint_returns_current_rows_after_clear_and_new_message(self):
        app, state = self.make_app()
        data_endpoint = self.endpoint(app, "/mqtt-diagnostics/data", "GET")
        clear_endpoint = self.endpoint(app, "/mqtt-diagnostics/clear", "POST")

        state.add_mqtt_diagnostic("evcc/site/battery", "old", diagnostic_filter="evcc/#", diagnostic_filter_matched=True)
        self.assertEqual(data_endpoint()["count"], 1)

        clear_endpoint()
        data = data_endpoint()
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["rows"], [])

        state.add_mqtt_diagnostic("evcc/site/battery", "new", diagnostic_filter="evcc/#", diagnostic_filter_matched=True)
        data = data_endpoint()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["rows"][0]["payload"], "new")

    def test_data_endpoint_respects_headless_mode_without_exposing_rows(self):
        app, state = self.make_app(headless=True)
        state.add_mqtt_diagnostic("evcc/site/battery", "123", diagnostic_filter="evcc/#", diagnostic_filter_matched=True)

        data = self.endpoint(app, "/mqtt-diagnostics/data", "GET")()

        self.assertTrue(data["headless"])
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["rows"], [])


if __name__ == "__main__":
    unittest.main()
