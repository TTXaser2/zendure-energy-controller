import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from starlette.requests import Request

from config_manager import ConfigManager, DEFAULT_CONFIG
from settings_model import build_settings_model
from state import ControllerState
from web_ui import create_app, build_settings_page, RESTART_HELPER_PATH


def endpoint(app, path, method):
    method = method.upper()
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return route.endpoint
    raise AssertionError(f"Route {method} {path} missing")


def request(path, *, method="GET", body=None, csrf="", origin="http://testserver"):
    data = json.dumps(body or {}).encode("utf-8")
    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": data, "more_body": False}

    headers = [(b"host", b"testserver")]
    if origin:
        headers.append((b"origin", origin.encode()))
    if csrf:
        headers.extend([(b"cookie", f"zec_settings_csrf={csrf}".encode()), (b"x-csrf-token", csrf.encode())])
    return Request({
        "type": "http", "method": method, "scheme": "http",
        "server": ("testserver", 80), "client": ("127.0.0.1", 1234),
        "path": path, "query_string": b"", "headers": headers,
    }, receive)


class Rc20SettingsUiTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        path = Path(self.tempdir.name) / "config.json"
        cfg = dict(DEFAULT_CONFIG)
        cfg["DEVICE_ID"] = "TESTDEVICE"
        cfg["HEADLESS_MODE"] = False
        cfg["OPERATIONAL_EVENTS_DB_PATH"] = str(Path(self.tempdir.name) / "operational_events.sqlite3")
        path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        self.manager = ConfigManager(str(path))
        self.manager.load()
        self.state = ControllerState()
        self.app = create_app(self.manager, self.state)

    def test_page_is_new_application_shell_with_accessible_assets(self):
        html = build_settings_page(self.manager.get(), csrf_token="abc")
        self.assertIn("settings_v2.css", html)
        self.assertIn("settings_v2.js", html)
        self.assertIn("ZEC Settings", html)
        self.assertIn("Änderungen prüfen", html)
        self.assertIn("Standard", html)
        self.assertIn("Experte", html)

    def test_model_exposes_active_categories_and_hides_future_release_keys(self):
        model = build_settings_model(self.manager, self.state.snapshot(), csrf_token="abc")
        keys = {
            item["key"]
            for category in model["categories"]
            for section in category["sections"]
            for item in section["settings"]
        }
        self.assertIn("DEADBAND_W", keys)
        self.assertIn("HEADLESS_MODE", keys)
        self.assertNotIn("MEASUREMENT_DB_MAINTENANCE_MODE", keys)
        self.assertNotIn("SERVICE_RESTART_COMMAND", keys)
        self.assertGreaterEqual(len(model["categories"]), 10)

    def test_navigation_groups_follow_operational_order(self):
        script = (Path(__file__).resolve().parents[1] / "static/settings_v2.js").read_text(encoding="utf-8")
        expected = "['A. Betrieb','B. Regelung & Speicherstrategie','C. Geräte & Schnittstellen','D. Daten, System & Diagnose']"
        self.assertIn(expected, script)

    def test_model_never_exposes_secret_value(self):
        candidate = self.manager.candidate_base_config()
        candidate["MQTT_PASSWORD"] = "secret-value"
        self.manager.commit_candidate(candidate, self.manager.configured_revision())
        model = build_settings_model(self.manager, self.state.snapshot(), csrf_token="abc")
        text = json.dumps(model)
        self.assertNotIn("secret-value", text)
        mqtt_password = next(
            item for category in model["categories"] for section in category["sections"]
            for item in section["settings"] if item["key"] == "MQTT_PASSWORD"
        )
        self.assertTrue(mqtt_password["secret_set"])
        self.assertIsNone(mqtt_password["configured"])

    def test_preview_requires_csrf_and_same_origin(self):
        route = endpoint(self.app, "/settings/preview", "POST")
        response = asyncio.run(route(request("/settings/preview", method="POST", body={"confirmation": "RESTART_SERVICE"})))
        self.assertEqual(403, response.status_code)
        response = asyncio.run(route(request("/settings/preview", method="POST", body={}, csrf="x" * 40, origin="http://evil")))
        self.assertEqual(403, response.status_code)

    def test_preview_and_commit_routes_change_only_explicit_key(self):
        token = "x" * 40
        preview_route = endpoint(self.app, "/settings/preview", "POST")
        preview_response = asyncio.run(preview_route(request(
            "/settings/preview", method="POST", csrf=token,
            body={
                "base_revision": self.manager.cas_revision(),
                "changes": {"DEADBAND_W": {"op": "set", "value": 95}},
                "secrets": {},
            },
        )))
        self.assertEqual(200, preview_response.status_code)
        preview = json.loads(preview_response.body)
        commit_route = endpoint(self.app, "/settings/commit", "POST")
        commit_response = asyncio.run(commit_route(request(
            "/settings/commit", method="POST", csrf=token,
            body={"preview_id": preview["preview_id"], "confirmations": preview["confirmations_required"]},
        )))
        self.assertEqual(200, commit_response.status_code)
        self.assertEqual(95, self.manager.get()["DEADBAND_W"])

    def test_legacy_write_routes_are_tombstones(self):
        for path in ("/settings/validate", "/save-config"):
            route = endpoint(self.app, path, "POST")
            response = asyncio.run(route(request(path, method="POST")))
            self.assertEqual(410, response.status_code)

    def test_headless_blocks_web_settings_but_manual_reload_restores_it(self):
        candidate = self.manager.candidate_base_config()
        candidate["HEADLESS_MODE"] = True
        self.manager.commit_candidate(candidate, self.manager.configured_revision())
        route = endpoint(self.app, "/settings", "GET")
        response = route(request("/settings"))
        self.assertEqual(403, response.status_code)
        raw = self.manager.candidate_base_config()
        raw["HEADLESS_MODE"] = False
        Path(self.manager.path).write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
        self.manager.reload_if_needed()
        response = route(request("/settings"))
        self.assertEqual(200, response.status_code)

    def test_restart_route_fails_closed_when_fixed_helper_is_unavailable(self):
        candidate = self.manager.candidate_base_config()
        candidate["WEB_SERVICE_RESTART_ENABLED"] = True
        self.manager.commit_candidate(candidate, self.manager.configured_revision())
        token = "x" * 40
        route = endpoint(self.app, "/restart-service", "POST")
        # The result must not depend on whether the productive host already has
        # the fixed helper installed.  Explicitly model the unavailable-helper
        # branch named by this test.
        with patch("web_ui.os.path.isfile", return_value=False), patch("web_ui.os.access", return_value=False):
            response = asyncio.run(route(request("/restart-service", method="POST", csrf=token, body={"confirmation": "RESTART_SERVICE"})))
        self.assertEqual(503, response.status_code)
        self.assertIn("RESTART_HELPER_UNAVAILABLE", response.body.decode("utf-8"))

    def test_restart_contract_uses_fixed_helper_only(self):
        self.assertEqual("/usr/local/sbin/zendure-controller-restart", RESTART_HELPER_PATH)
        self.assertNotIn("SERVICE_RESTART_COMMAND", build_settings_page(self.manager.get(), csrf_token="abc"))


if __name__ == "__main__":
    unittest.main()
