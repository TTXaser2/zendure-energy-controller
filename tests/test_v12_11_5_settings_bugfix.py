import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path

from starlette.requests import Request

import version
from config_manager import ConfigManager, DEFAULT_CONFIG
from settings_model import build_settings_model
from state import ControllerState
from web_ui import build_settings_page, create_app

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "static" / "settings_v2.js"
CSS = ROOT / "static" / "settings_v2.css"
UPDATER = ROOT / "tools" / "update_zendure_controller.sh"


def endpoint(app, path, method="GET"):
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
        headers.extend([
            (b"cookie", f"zec_settings_csrf={csrf}".encode()),
            (b"x-csrf-token", csrf.encode()),
        ])
    return Request({
        "type": "http", "method": method, "scheme": "http",
        "server": ("testserver", 80), "client": ("127.0.0.1", 1234),
        "path": path, "query_string": b"", "headers": headers,
    }, receive)


class V12115SettingsBugfixTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        cfg_path = Path(self.tempdir.name) / "config.json"
        cfg = dict(DEFAULT_CONFIG)
        cfg.update({
            "DEVICE_ID": "TESTDEVICE",
            "HEADLESS_MODE": False,
            "OPERATIONAL_EVENTS_DB_PATH": str(Path(self.tempdir.name) / "events.sqlite3"),
        })
        cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        os.chmod(cfg_path, 0o600)
        self.manager = ConfigManager(str(cfg_path))
        self.manager.load()
        self.state = ControllerState()
        self.app = create_app(self.manager, self.state)

    def test_release_identity_is_v12_11_5_without_measurement_schema_change(self):
        self.assertEqual("12.11.5", version.APP_VERSION)
        self.assertEqual("V12.11.5", version.APP_VERSION_LABEL)
        self.assertEqual("v12.11.5-20260807", version.APP_BUILD_ID)
        self.assertEqual("ZEC-MEASUREMENT-V3", version.CSV_SCHEMA)

    def test_desktop_scroll_contract_owns_vertical_scroll_in_content_pane(self):
        css = CSS.read_text(encoding="utf-8")
        self.assertIn("html,body.zec-settings-v2{height:100%;overflow:hidden}", css)
        self.assertIn(".settings-app{height:calc(100dvh - 134px);min-height:0;overflow:hidden}", css)
        self.assertIn(".settings-main{height:100%;min-height:0;overflow-y:auto", css)
        self.assertIn(".settings-sidebar{position:relative;top:auto;height:100%;min-height:0;overflow-y:auto", css)
        self.assertIn("scrollCategoryToTop", JS.read_text(encoding="utf-8"))

    def test_mobile_drawer_uses_body_scroll_lock_without_global_touchmove_block(self):
        js = JS.read_text(encoding="utf-8")
        css = CSS.read_text(encoding="utf-8")
        self.assertIn("app.drawerScrollY = window.scrollY", js)
        self.assertIn("document.body.style.top = `-${app.drawerScrollY}px`", js)
        self.assertIn("window.scrollTo({top:app.drawerScrollY", js)
        self.assertIn("body.category-drawer-open{position:fixed", css)
        self.assertIn(".settings-sidebar{overflow-y:auto;overscroll-behavior:contain", css)
        self.assertNotIn("touchmove", js)
        self.assertIn("categoryDrawerBackdrop", js)
        self.assertIn("Escape", js)

    def test_night_window_is_two_logical_hhmm_fields_and_atomic_payload(self):
        js = JS.read_text(encoding="utf-8")
        self.assertIn("Startzeit des Nachtmodus", js)
        self.assertIn("Endzeit des Nachtmodus", js)
        self.assertIn("/^(\\d{2}):(\\d{2})$/", js)
        self.assertIn("changes[pair.hour] = {op:'set'", js)
        self.assertIn("changes[pair.minute] = {op:'set'", js)
        self.assertIn("label:'Nachtfenster'", js)
        self.assertIn("key:'__night_window__'", js)
        self.assertIn("NIGHT_START_HOUR", js)
        self.assertIn("NIGHT_START_MINUTE", js)
        self.assertIn("NIGHT_END_HOUR", js)
        self.assertIn("NIGHT_END_MINUTE", js)

    def test_blocked_422_is_semantic_preview_not_transport_error(self):
        token = "x" * 40
        route = endpoint(self.app, "/settings/preview", "POST")
        response = asyncio.run(route(request(
            "/settings/preview", method="POST", csrf=token,
            body={
                "base_revision": self.manager.cas_revision(),
                "changes": {
                    "MIN_SOC_PERCENT": {"op": "set", "value": 100},
                    "MAX_SOC_PERCENT": {"op": "set", "value": 90},
                },
                "secrets": {},
            },
        )))
        self.assertEqual(422, response.status_code)
        data = json.loads(response.body)
        self.assertEqual("blocked", data["status"])
        self.assertTrue(data["issues"])
        self.assertTrue(any(i.get("blocking") for i in data["issues"]))
        self.assertTrue(any("MIN_SOC_PERCENT" in i.get("keys", []) for i in data["issues"]))
        js = JS.read_text(encoding="utf-8")
        self.assertIn("error.status === 422 && error.data?.status === 'blocked'", js)
        self.assertIn("app.preview = error.data", js)
        self.assertNotIn("Prüfung fehlgeschlagen: ${error.message}", js)

    def test_preview_error_messages_are_status_specific_and_do_not_leak_raw_http(self):
        js = JS.read_text(encoding="utf-8")
        self.assertIn("error.status === 409", js)
        self.assertIn("Konfiguration wurde zwischenzeitlich geändert", js)
        self.assertIn("error.status === 403", js)
        self.assertIn("aus Sicherheitsgründen abgewiesen", js)
        self.assertIn("internen Fehlers", js)
        self.assertIn("Zur Einstellung", js)
        self.assertIn("p.status !== 'ready' || !p.preview_id", js)

    def test_command_resync_standard_mode_has_generic_empty_state_and_visible_count(self):
        model = build_settings_model(self.manager, self.state.snapshot(), csrf_token="abc")
        category = next(c for c in model["categories"] if c["name"] == "Kommandowirkung & Resync")
        settings = [s for section in category["sections"] for s in section["settings"]]
        self.assertEqual(13, len(settings))
        self.assertTrue(all(s["expert"] for s in settings))
        js = JS.read_text(encoding="utf-8")
        self.assertIn("Keine Einstellungen im Standardmodus", js)
        self.assertIn("Expertenmodus anzeigen", js)
        self.assertIn("categoryVisibleCount(c)", js)
        self.assertIn("expertHiddenCount(category)", js)

    def test_pointer_repair_exists_only_in_expert_system_admin_area(self):
        html = build_settings_page(self.manager.get(), csrf_token="abc")
        js = JS.read_text(encoding="utf-8")
        self.assertNotIn('id="pointerRepairAction"', html)
        self.assertNotIn("pointerRepairAction", CSS.read_text(encoding="utf-8"))
        self.assertIn("adminPointerRepairAction", js)
        self.assertIn("Last-Good-Konfigurationsspeicher", js)
        self.assertIn("keine normalen Einstellungen geladen, geändert oder auf Default gesetzt", js)
        self.assertIn("app.mode === 'expert'", js)
        self.assertIn("c.name === 'System & Diagnose' && app.mode === 'expert'", js)
        self.assertIn("REPAIR_POINTER", js)

    def test_client_validation_covers_time_number_enum_and_field_highlighting(self):
        js = JS.read_text(encoding="utf-8")
        for code in ("TIME_FORMAT_INVALID", "NUMBER_INVALID", "VALUE_BELOW_MIN", "VALUE_ABOVE_MAX", "ENUM_INVALID"):
            self.assertIn(code, js)
        self.assertIn("validationIssues", js)
        self.assertIn("issueForKeys", js)
        self.assertIn("has-error", js)
        self.assertIn("targetForSettingKey", js)

    def test_updater_directly_accepts_v12_11_4_and_keeps_transitional_readback_gate(self):
        script = UPDATER.read_text(encoding="utf-8")
        self.assertIn('EXPECTED_VERSION="v12_11_5"', script)
        self.assertIn('EXPECTED_SOURCE_V12114_VERSION="12.11.4"', script)
        self.assertIn('EXPECTED_SOURCE_V12114_BUILD_ID="v12.11.4-20260807"', script)
        self.assertIn('SOURCE_MODE="V12_11_4"', script)
        self.assertIn('EXPECTED_TARGET_BUILD_ID="v12.11.5-20260807"', script)
        self.assertIn("TRANSITIONAL_STREAK", script)
        self.assertIn("INPUT_LIMIT/OUTPUT_LIMIT-Readback", script)
        self.assertIn("PYTHONWARNINGS=\"error::ResourceWarning\"", script)
        self.assertIn("V12_11_5_SOURCE_MANIFEST.sha256", script)


if __name__ == "__main__":
    unittest.main()
