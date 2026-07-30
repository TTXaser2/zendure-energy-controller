import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from config_manager import ConfigManager, DEFAULT_CONFIG
from operational_events import OperationalEventJournal
from state import ControllerState
from web_ui import build_status_view_payload, create_app
import version


class V12112Rc6UiDiagnosticsHotfixTests(unittest.TestCase):
    def _make_app(self):
        tempdir = tempfile.TemporaryDirectory()
        cfg_path = os.path.join(tempdir.name, "config.json")
        cfg = dict(DEFAULT_CONFIG)
        cfg["HEADLESS_MODE"] = False
        cfg["OPERATIONAL_EVENTS_DB_PATH"] = os.path.join(tempdir.name, "events.sqlite3")
        manager = ConfigManager(cfg_path)
        manager.save(cfg, create_last_good=False)
        app = create_app(manager, ControllerState())
        self.addCleanup(tempdir.cleanup)
        return app

    @staticmethod
    def _endpoint(app, path, method="GET"):
        for route in app.routes:
            if getattr(route, "path", None) == path and method.upper() in getattr(route, "methods", set()):
                return route.endpoint
        raise AssertionError(f"Route {method} {path} not found")

    def test_version(self):
        self.assertEqual("12.11.2-rc17", version.APP_VERSION)
        self.assertEqual("V12.11.2-RC17", version.APP_VERSION_LABEL)

    def test_wide_desktop_has_four_columns_medium_two_mobile_one(self):
        css = Path("static/status_v2.css").read_text(encoding="utf-8")
        self.assertIn("grid-template-columns:repeat(4,minmax(0,1fr))", css)
        self.assertIn("@media(max-width:1550px)", css)
        self.assertIn("@media(max-width:1120px)", css)
        self.assertIn(".zec-lower-grid{grid-template-columns:repeat(2,minmax(0,1fr))}", css)
        self.assertIn(".zec-lower-grid{grid-template-columns:1fr}", css)

    def test_status_old_route_renders_without_removed_soc_helper(self):
        app = self._make_app()
        page = self._endpoint(app, "/status_old")()
        self.assertIn("Historische Referenzansicht", page)
        self.assertIn("Aktuellen SOC-Tagesgraphen", page)
        self.assertNotIn("build_soc_day_section", page)

    def test_technical_status_codes_are_translated_for_the_card(self):
        snap = ControllerState().snapshot()
        snap.update(
            {
                "mqtt_connected": True,
                "zendure_mqtt_overall_status": "ZENDURE_MQTT_OK",
                "command_effect_category": "no_command",
                "measurement_log_status": "active",
                "measurement_db_status": "queued",
                "measurement_log_active_target_type": "internal_sd",
                "last_cycle_slowest_step": "other_cycle_work_ms",
                "last_cycle_slowest_step_ms": 11.6,
                "last_cycle_completed_epoch": time.time(),
                "grid_power_valid": True,
                "raw_grid_power": 0,
            }
        )
        payload = build_status_view_payload(
            {"INTERVAL_SECONDS": 2, "MEASUREMENT_DB_ENABLED": False, "ZENDURE_LOCAL_API_ENABLED": False},
            snap,
            events=[],
        )
        self.assertEqual("Aktuell", payload["diag"]["mqtt"])
        self.assertEqual("Noch kein relevantes Kommando", payload["diag"]["effect"])
        self.assertEqual("Sonstige, nicht einzeln erfasste Verarbeitung", payload["diag"]["slowest_step"])
        self.assertEqual("Aktiv", payload["logging"]["status"])
        self.assertEqual("Aktiv · asynchron", payload["logging"]["db"])
        self.assertEqual("Interner Systemdatenträger", payload["logging"]["target"])
        self.assertNotIn("ZENDURE_MQTT_OK", payload["diag"]["mqtt"])
        self.assertNotIn("no_command", payload["diag"]["effect"])

    def test_repeated_telemetry_flap_reopens_same_row_semantically(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            cfg = {"OPERATIONAL_EVENTS_DB_PATH": os.path.join(td, "events.sqlite3")}
            state = ControllerState()
            journal = OperationalEventJournal(lambda: cfg, state)
            conn = journal._connect()
            journal._previous = {
                "mqtt_connected": True,
                "mode": "AUTO",
                "resync_count": 0,
                "stable:zendure_telemetry": False,
                "command_effect": "effective",
                "measurement_logging": "active",
            }
            base = state.snapshot()
            base.update({
                "mqtt_connected": True,
                "current_mode": "AUTO",
                "command_effect_category": "effective",
                "measurement_log_status": "active",
                "zendure_mqtt_overall_status": "ZENDURE_MQTT_PARTIAL_STALE",
                "zendure_mqtt_status_reason": "Headunit-Leistung fehlt",
            })
            with patch("operational_events.time.monotonic", side_effect=[0.0, 7.0, 8.0, 15.0, 16.0, 23.0]):
                journal._observe(conn, base)
                journal._observe(conn, base)
                base["zendure_mqtt_overall_status"] = "ZENDURE_MQTT_OK"
                journal._observe(conn, base)
                journal._observe(conn, base)
                base["zendure_mqtt_overall_status"] = "ZENDURE_MQTT_PARTIAL_STALE"
                base["zendure_mqtt_status_reason"] = "SOC fehlt"
                journal._observe(conn, base)
                journal._observe(conn, base)
            row = conn.execute(
                "SELECT title,detail,status,ended_at,occurrence_count FROM operational_events WHERE event_type='zendure_telemetry'"
            ).fetchone()
            conn.close()
            self.assertEqual("Zendure-Telemetrie nicht aktuell", row[0])
            self.assertEqual("SOC fehlt", row[1])
            self.assertEqual("open", row[2])
            self.assertIsNone(row[3])
            self.assertEqual(2, row[4])

    def test_existing_rc5_flap_rows_are_compacted_and_normalised_for_display(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = {"OPERATIONAL_EVENTS_DB_PATH": os.path.join(td, "events.sqlite3")}
            journal = OperationalEventJournal(lambda: cfg, ControllerState())
            conn = journal._connect()
            now = time.time()
            for offset in (0, 60, 120):
                conn.execute(
                    """
                    INSERT INTO operational_events(
                      event_type,severity,title,detail,started_at,ended_at,status,dedupe_key,detail_json,occurrence_count
                    ) VALUES(?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        "zendure_telemetry",
                        "warning",
                        "Zendure-Telemetrie wieder aktuell",
                        "Fehlende/stale kritische Gruppen: headunit_power",
                        now - offset,
                        now - offset,
                        "resolved",
                        "zendure_telemetry",
                        "{}",
                        1,
                    ),
                )
            conn.commit()
            conn.close()
            rows = journal.list_recent(days=2, limit=250)
            self.assertEqual(1, len(rows))
            self.assertEqual("Zendure-Telemetrie wieder aktuell", rows[0]["title"])
            self.assertIn("Datenversorgung vollständig wiederhergestellt", rows[0]["detail"])
            self.assertEqual(3, rows[0]["occurrence_count"])


if __name__ == "__main__":
    unittest.main()
