import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from starlette.requests import Request

from config_bundle import parse_bundle
from config_manager import ConfigManager, DEFAULT_CONFIG
from settings_registry import get_setting, PortabilityClass
from state import ControllerState
from web_ui import create_app


def endpoint(app, path, method):
    method = method.upper()
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return route.endpoint
    raise AssertionError(f"Route {method} {path} missing")


def request(path, *, method="GET", body=None, raw=None, csrf="", origin="http://testserver", query=""):
    data = raw if raw is not None else json.dumps(body or {}).encode("utf-8")
    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": data, "more_body": False}

    headers = [(b"host", b"testserver"), (b"content-length", str(len(data)).encode())]
    if origin:
        headers.append((b"origin", origin.encode()))
    if csrf:
        headers.extend([(b"cookie", f"zec_settings_csrf={csrf}".encode()), (b"x-csrf-token", csrf.encode())])
    return Request({
        "type": "http", "method": method, "scheme": "http",
        "server": ("testserver", 80), "client": ("127.0.0.1", 1234),
        "path": path, "query_string": query.encode(), "headers": headers,
    }, receive)


class V13ConfigRouteIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        path = Path(self.tempdir.name) / "config.json"
        cfg = dict(DEFAULT_CONFIG)
        cfg["DEVICE_ID"] = "TESTDEVICE"
        cfg["HEADLESS_MODE"] = False
        cfg["MQTT_PASSWORD"] = "top-secret-route-test"
        cfg["OPERATIONAL_EVENTS_DB_PATH"] = str(Path(self.tempdir.name) / "operational_events.sqlite3")
        path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        self.manager = ConfigManager(str(path))
        self.manager.load()
        self.app = create_app(self.manager, ControllerState())
        self.csrf = "r" * 40

    def test_v13_routes_are_registered_and_mutations_require_csrf(self):
        for path, method in (
            ("/config-states", "GET"),
            ("/config-states/create", "POST"),
            ("/config-export", "POST"),
            ("/config-profile-export", "POST"),
            ("/config-import/inspect", "POST"),
            ("/config-import/{token}/preview", "POST"),
        ):
            endpoint(self.app, path, method)
        route = endpoint(self.app, "/config-states/create", "POST")
        response = asyncio.run(route(request("/config-states/create", method="POST", body={"name": "No CSRF"})))
        self.assertEqual(403, response.status_code)

    def test_named_state_create_and_list_route(self):
        create_route = endpoint(self.app, "/config-states/create", "POST")
        response = asyncio.run(create_route(request(
            "/config-states/create", method="POST", csrf=self.csrf,
            body={"name": "Guter Stand", "description": "Route integration", "scope_mode": "full_managed"},
        )))
        self.assertEqual(200, response.status_code)
        created = json.loads(response.body)
        self.assertEqual("created", created["status"])
        self.assertEqual("no-store", response.headers.get("cache-control"))

        list_route = endpoint(self.app, "/config-states", "GET")
        listed_response = list_route(request("/config-states"))
        self.assertEqual(200, listed_response.status_code)
        listed = json.loads(listed_response.body)
        self.assertEqual(1, listed["count"])
        self.assertEqual("Guter Stand", listed["items"][0]["name"])
        self.assertFalse(listed["items"][0]["secrets_included"])
        state_file = next((Path(self.tempdir.name) / "config-states").glob("*.zec-config.json"))
        self.assertNotIn(b"top-secret-route-test", state_file.read_bytes())

    def test_portable_profile_export_route_contains_only_portable_nonsecret_keys(self):
        route = endpoint(self.app, "/config-profile-export", "POST")
        response = asyncio.run(route(request(
            "/config-profile-export", method="POST", csrf=self.csrf,
            body={"name": "Teilbares Profil", "description": "portable"},
        )))
        self.assertEqual(200, response.status_code)
        bundle = parse_bundle(bytes(response.body))
        self.assertEqual("portable_profile", bundle.payload["artifact_kind"])
        keys = set(bundle.scope["keys"])
        self.assertTrue(keys)
        self.assertNotIn("MQTT_PASSWORD", keys)
        for key in keys:
            self.assertEqual(PortabilityClass.PORTABLE_PROFILE, get_setting(key).portability_class)
        self.assertNotIn(b"top-secret-route-test", bytes(response.body))

    def test_export_inspect_preview_roundtrip_uses_same_csrf_session(self):
        export_route = endpoint(self.app, "/config-export", "POST")
        exported = asyncio.run(export_route(request(
            "/config-export", method="POST", csrf=self.csrf,
            body={"name": "Route export", "scope_mode": "portable_profile"},
        )))
        self.assertEqual(200, exported.status_code)

        inspect_route = endpoint(self.app, "/config-import/inspect", "POST")
        inspected_response = asyncio.run(inspect_route(request(
            "/config-import/inspect", method="POST", csrf=self.csrf, raw=bytes(exported.body),
        )))
        self.assertEqual(200, inspected_response.status_code)
        inspected = json.loads(inspected_response.body)
        token = inspected["import_token"]

        preview_route = endpoint(self.app, "/config-import/{token}/preview", "POST")
        preview_response = asyncio.run(preview_route(token, request(
            f"/config-import/{token}/preview", method="POST", csrf=self.csrf,
            body={"base_revision": self.manager.cas_revision(), "expert": False, "secrets": {}},
        )))
        self.assertEqual(200, preview_response.status_code)
        preview = json.loads(preview_response.body)
        self.assertIn("preview_id", preview)
        self.assertEqual("no-store", preview_response.headers.get("cache-control"))


if __name__ == "__main__":
    unittest.main()
