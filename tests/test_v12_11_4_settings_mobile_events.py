import tempfile
import time
import unittest
from pathlib import Path

from config_manager import DEFAULT_CONFIG
from operational_events import OperationalEventJournal
from state import ControllerState
from web_ui import build_settings_page, build_status_view_payload


class V12114MobileSettingsRegressionTests(unittest.TestCase):
    def test_mobile_drawer_has_real_backdrop_and_aria_contract(self):
        page = build_settings_page(dict(DEFAULT_CONFIG), csrf_token="x")
        self.assertIn('id="settingsSidebar"', page)
        self.assertIn('id="categoryDrawerBackdrop"', page)
        self.assertIn('aria-controls="settingsSidebar"', page)
        script = Path(__file__).resolve().parents[1].joinpath("static/settings_v2.js").read_text(encoding="utf-8")
        self.assertIn("function setCategoryDrawerOpen(open)", script)
        self.assertIn("$('#categoryDrawerBackdrop').onclick", script)
        css = Path(__file__).resolve().parents[1].joinpath("static/settings_v2.css").read_text(encoding="utf-8")
        self.assertIn(".settings-sidebar{display:block;top:170px", css)
        self.assertIn(".category-drawer-backdrop", css)

    def test_category_selection_resets_document_scroll(self):
        script = Path(__file__).resolve().parents[1].joinpath("static/settings_v2.js").read_text(encoding="utf-8")
        start = script.index("function selectCategory(name)")
        end = script.index("function renderNav()", start)
        block = script[start:end]
        self.assertIn("scrollCategoryToTop();", block)
        self.assertIn("window.scrollTo({top:0", script)

    def test_preview_modal_owns_scroll_and_stays_above_save_bar(self):
        script = Path(__file__).resolve().parents[1].joinpath("static/settings_v2.js").read_text(encoding="utf-8")
        self.assertIn("function lockPreviewScroll()", script)
        self.assertIn("function unlockPreviewScroll()", script)
        css = Path(__file__).resolve().parents[1].joinpath("static/settings_v2.css").read_text(encoding="utf-8")
        self.assertIn(".modal-backdrop{z-index:160", css)
        self.assertIn(".modal-body{flex:1 1 auto;min-height:0;overflow-y:auto", css)
        self.assertIn("body.preview-open{position:fixed", css)
        self.assertIn("position:sticky;bottom:0", css)

    def test_expert_system_category_exposes_protected_restart_action(self):
        script = Path(__file__).resolve().parents[1].joinpath("static/settings_v2.js").read_text(encoding="utf-8")
        self.assertIn("c.name === 'System & Diagnose'", script)
        self.assertIn("app.mode === 'expert'", script)
        self.assertIn('id="adminRestartAction"', script)
        self.assertIn("adminRestart.onclick = restart", script)

    def test_mobile_document_overflow_guards_do_not_change_nav_scroll_contract(self):
        css = Path(__file__).resolve().parents[1].joinpath("static/settings_v2.css").read_text(encoding="utf-8")
        self.assertIn("overflow-x:hidden", css)
        status_css = Path(__file__).resolve().parents[1].joinpath("static/status_v2.css").read_text(encoding="utf-8")
        self.assertIn("overflow-x:auto", status_css)


class V12114LegacyEventReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = str(Path(self.tmp.name) / "events.sqlite3")
        self.journal = OperationalEventJournal(
            lambda: {"OPERATIONAL_EVENTS_DB_PATH": self.db},
            type("S", (), {"snapshot": lambda self: {}})(),
        )

    def _legacy_open(self, conn, event_type, dedupe_key, title):
        conn.execute(
            "INSERT INTO operational_events(event_type,severity,title,detail,started_at,ended_at,status,dedupe_key,detail_json,occurrence_count) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (event_type, "warning", title, "legacy", time.time() - 5000, None, "open", dedupe_key, "{}", 1),
        )
        conn.commit()

    def test_healthy_live_state_resolves_legacy_rows_with_empty_or_wrong_dedupe_key(self):
        conn = self.journal._connect()
        try:
            self._legacy_open(conn, "zendure_telemetry", "", "Zendure-Telemetrie nicht aktuell")
            self._legacy_open(conn, "zendure_telemetry", "legacy:headunit", "Zendure-Telemetrie nicht aktuell")
            self.journal._resolve(conn, "zendure_telemetry", "Zendure-Telemetrie wieder aktuell", "gesund")
            rows = conn.execute(
                "SELECT status FROM operational_events WHERE event_type='zendure_telemetry'"
            ).fetchall()
            self.assertEqual([("resolved",), ("resolved",)], rows)
        finally:
            conn.close()

    def test_mqtt_resolution_does_not_close_unrelated_event_types(self):
        conn = self.journal._connect()
        try:
            self._legacy_open(conn, "mqtt", "old:mqtt", "MQTT getrennt")
            self._legacy_open(conn, "command_effect", "command_effect", "Command nicht wirksam")
            self.journal._resolve(conn, "mqtt", "MQTT wiederhergestellt", "gesund")
            states = dict(conn.execute("SELECT event_type,status FROM operational_events").fetchall())
            self.assertEqual("resolved", states["mqtt"])
            self.assertEqual("open", states["command_effect"])
        finally:
            conn.close()


class V12114WarningCounterTests(unittest.TestCase):
    def test_header_counts_open_warning_groups_not_only_unique_titles(self):
        state = ControllerState()
        with state.lock:
            state.battery_soc = 75
            state.last_soc_update_epoch = time.time()
        snapshot = state.snapshot()
        snapshot.update({
            "current_mode": "HOLD",
            "grid_power_valid": True,
            "raw_grid_power": 0,
            "second_battery_data_valid": True,
            "zendure_mqtt_overall_status": "ZENDURE_MQTT_OK",
            "zendure_command_state_complete": True,
        })
        events = [
            {"status": "open", "severity": "warning", "event_type": "zendure_telemetry", "title": "Zendure-Telemetrie nicht aktuell"},
            {"status": "open", "severity": "warning", "event_type": "zendure_telemetry", "title": "Zendure-Telemetrie nicht aktuell"},
        ]
        payload = build_status_view_payload(dict(DEFAULT_CONFIG), snapshot, events=events)
        self.assertEqual("warn", payload["system"]["kind"])
        self.assertEqual("Warnung 2", payload["system"]["label"])
        self.assertEqual(1, len([x for x in payload["system"]["warnings"] if x.startswith("Offenes Betriebsereignis:")]))


if __name__ == "__main__":
    unittest.main()
