import os
import tempfile
import unittest

from starlette.requests import Request

from config_manager import ConfigManager, DEFAULT_CONFIG
from state import ControllerState
from web_ui import create_app


def make_request(path: str = "/mqtt-diagnostics") -> Request:
    if "?" in path:
        clean_path, query = path.split("?", 1)
    else:
        clean_path, query = path, ""
    return Request({
        "type": "http",
        "method": "GET",
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345),
        "path": clean_path,
        "query_string": query.encode("utf-8"),
        "headers": [],
    })


class V12813MqttDiagnosticsRouteTests(unittest.TestCase):
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

    def test_get_mqtt_diagnostics_route_returns_page_without_testclient_dependency(self):
        app, state = self.make_app()
        state.add_mqtt_diagnostic(
            "evcc/site/battery",
            "123",
            diagnostic_filter="evcc/#",
            diagnostic_filter_matched=True,
        )

        page = self.endpoint(app, "/mqtt-diagnostics", "GET")(make_request())

        self.assertIn("MQTT Topic-Diagnose", page)
        self.assertIn("Diagnosetabelle leeren", page)
        self.assertIn("evcc/site/battery", page)

    def test_clear_route_redirects_and_page_shows_cleared_notice(self):
        app, state = self.make_app()
        state.add_mqtt_diagnostic(
            "evcc/site/battery",
            "123",
            diagnostic_filter="evcc/#",
            diagnostic_filter_matched=True,
        )

        response = self.endpoint(app, "/mqtt-diagnostics/clear", "POST")()

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/mqtt-diagnostics?cleared=1")
        self.assertEqual(state.snapshot()["mqtt_topic_diagnostics"], [])

        page = self.endpoint(app, "/mqtt-diagnostics", "GET")(make_request("/mqtt-diagnostics?cleared=1"))
        self.assertIn("Diagnosetabelle wurde geleert", page)

    def test_get_mqtt_diagnostics_route_respects_headless_mode(self):
        app, state = self.make_app(headless=True)
        state.add_mqtt_diagnostic(
            "evcc/site/battery",
            "123",
            diagnostic_filter="evcc/#",
            diagnostic_filter_matched=True,
        )

        page = self.endpoint(app, "/mqtt-diagnostics", "GET")(make_request())

        self.assertIn("Headless Mode", page)
        self.assertNotIn("evcc/site/battery", page)


if __name__ == "__main__":
    unittest.main()
