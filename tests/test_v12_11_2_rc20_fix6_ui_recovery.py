import json
import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from config_manager import DEFAULT_CONFIG
from operational_events import OperationalEventJournal
from tests.test_operation_priority import OkShelly, base_cfg, fresh_state, make_controller
from web_ui import build_graph_page, build_settings_page, build_status_view_payload, measurement_availability


class Rc20Fix6SocBoundaryTests(unittest.TestCase):
    def test_max_soc_is_normal_hold_not_safe_state(self):
        cfg = base_cfg(MAX_SOC_PERCENT=99, DEADBAND_W=80)
        state = fresh_state(100)
        with state.lock:
            state.last_input_power = 500
        controller, state, mqtt, _ = make_controller(cfg, state=state, shelly=OkShelly(-1000))
        controller.is_night_discharge_active = lambda _cfg: False

        controller.run_once(cfg)

        self.assertEqual("HOLD", state.current_mode)
        self.assertEqual(0, state.safe_state_counter)
        self.assertIn("MAX_SOC", state.active_limiters)
        self.assertEqual("AUTO -> MAX_SOC -> HOLD", state.technical_control_path)
        self.assertEqual(0, state.last_input_power)
        self.assertEqual(0, state.last_output_power)
        self.assertTrue(any(cmd[0] == "input" and cmd[1] == 0 for cmd in mqtt.commands))

    def test_missing_soc_remains_true_safe_state(self):
        cfg = base_cfg(MAX_SOC_PERCENT=99)
        state = fresh_state(80)
        with state.lock:
            state.battery_soc = None
            state.last_soc_update_epoch = None
        controller, state, _, _ = make_controller(cfg, state=state, shelly=OkShelly(-1000))
        controller.is_night_discharge_active = lambda _cfg: False

        controller.run_once(cfg)

        self.assertEqual("SAFE_STATE", state.current_mode)
        self.assertGreater(state.safe_state_counter, 0)

    def test_status_payload_treats_max_soc_hold_as_system_ok(self):
        snap = fresh_state(100).snapshot()
        snap.update({
            "current_mode": "HOLD",
            "control_reason": "Ladung beendet: Maximal-SOC erreicht",
            "active_limiters": ["MAX_SOC"],
            "grid_power_valid": True,
            "raw_grid_power": -900,
            "second_battery_data_valid": True,
            "second_battery_data_fresh": True,
            "zendure_mqtt_overall_status": "ZENDURE_MQTT_OK",
            "zendure_command_state_complete": True,
            "zendure_flash_protection_active": True,
        })
        payload = build_status_view_payload(dict(DEFAULT_CONFIG), snap, events=[])
        self.assertNotEqual("bad", payload["system"]["kind"])
        self.assertNotIn("Safe-State aktiv", payload["system"]["warnings"])

    def test_open_error_event_marks_global_system_status_bad(self):
        snap = fresh_state(70).snapshot()
        snap.update({
            "current_mode": "HOLD",
            "grid_power_valid": True,
            "raw_grid_power": 0,
            "second_battery_data_valid": True,
            "zendure_mqtt_overall_status": "ZENDURE_MQTT_OK",
            "zendure_command_state_complete": True,
        })
        payload = build_status_view_payload(dict(DEFAULT_CONFIG), snap, events=[{
            "status": "open",
            "severity": "error",
            "event_type": "mqtt",
            "title": "MQTT-Verbindung getrennt",
        }])
        self.assertEqual("bad", payload["system"]["kind"])
        self.assertEqual("Fehler 1", payload["system"]["label"])
        self.assertIn("Offenes Betriebsereignis: MQTT-Verbindung getrennt", payload["system"]["warnings"])


class Rc20Fix6EventReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = str(Path(self.tmp.name) / "events.sqlite3")
        self.cfg = {"OPERATIONAL_EVENTS_DB_PATH": self.db}
        self.journal = OperationalEventJournal(lambda: self.cfg, type("S", (), {"snapshot": lambda self: {}})())

    def _insert_open(self, conn, key, event_type, title):
        conn.execute(
            "INSERT INTO operational_events(event_type,severity,title,detail,started_at,ended_at,status,dedupe_key,detail_json,occurrence_count) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (event_type, "warning", title, "old", time.time()-1000, None, "open", key, "{}", 1),
        )
        conn.commit()

    def test_resolve_closes_all_duplicate_open_rows(self):
        conn = self.journal._connect()
        try:
            self._insert_open(conn, "mqtt", "mqtt", "old-1")
            self._insert_open(conn, "mqtt", "mqtt", "old-2")
            self.journal._resolve(conn, "mqtt", "MQTT wiederhergestellt", "gesund")
            open_count = conn.execute("SELECT COUNT(*) FROM operational_events WHERE dedupe_key='mqtt' AND status='open'").fetchone()[0]
            self.assertEqual(0, open_count)
        finally:
            conn.close()

    def test_healthy_startup_reconciles_mqtt_and_telemetry(self):
        conn = self.journal._connect()
        try:
            self._insert_open(conn, "mqtt", "mqtt", "old mqtt")
            self._insert_open(conn, "zendure_telemetry", "zendure_telemetry", "old telemetry")
            healthy = {
                "current_mode": "HOLD",
                "mqtt_connected": True,
                "zendure_mqtt_overall_status": "ZENDURE_MQTT_OK",
                "measurement_log_status": "active",
                "command_effect_category": "COMMAND_EFFECTIVE",
            }
            with patch("operational_events.time.monotonic", side_effect=[100.0, 107.0]):
                self.journal._observe(conn, healthy)
                self.journal._observe(conn, healthy)
            rows = conn.execute("SELECT dedupe_key,status FROM operational_events WHERE dedupe_key IN ('mqtt','zendure_telemetry')").fetchall()
            self.assertTrue(rows)
            self.assertTrue(all(status == "resolved" for _, status in rows))
        finally:
            conn.close()


class Rc20Fix6SettingsUiTests(unittest.TestCase):
    def test_settings_uses_shared_navigation_and_live_status_dot(self):
        html = build_settings_page({}, system_payload={"kind":"bad","label":"Safe-State","warnings":["x"]}, server_time="12:00:00")
        self.assertIn('class="zec-topbar"', html)
        self.assertIn('href="/"', html)
        self.assertIn('href="/graph"', html)
        self.assertIn('href="/settings"', html)
        self.assertIn('id="globalStatusNavDot"', html)
        self.assertNotIn("uni-meter", html)


    def test_graph_uses_the_same_shared_navigation_shell(self):
        html = build_graph_page(dict(DEFAULT_CONFIG))
        self.assertIn('class="zec-topbar"', html)
        self.assertIn('class="is-active" href="/graph"', html)
        self.assertIn('id="globalStatusNavDot"', html)
        self.assertIn('/static/status_v2.css', html)
        self.assertNotIn('class="zec-nav-modern"', html)
        self.assertIn('let graphRequestInFlight = false;', html)
        self.assertEqual(1, html.count('let graphRequestInFlight = false;'))

    def test_preview_close_reenables_review_by_recomputing_bar(self):
        script = Path(__file__).resolve().parents[1].joinpath("static/settings_v2.js").read_text(encoding="utf-8")
        self.assertIn("function closePreview()", script)
        self.assertIn("app.preview = null", script)
        self.assertIn("updateBar();", script[script.index("function closePreview()"):script.index("async function commit()")])
        self.assertIn("CATEGORY_PATHS", script)
        self.assertIn("content.classList.remove('loading')", script)
        self.assertIn("function storageGet(key, fallback)", script)
        self.assertIn("function storageSet(key, value)", script)
        self.assertNotIn("mode: localStorage.getItem", script)
        self.assertNotIn("<span>◉</span>", script)


class Rc20Fix6StorageInventoryTests(unittest.TestCase):
    def test_manifest_and_cache_avoid_repeated_csv_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            csv_path = base / "zendure_measurements_v4_test.csv"
            csv_path.write_text("measurement_time_utc;epoch_ms\n2026-08-06T10:00:00Z;1786010400000\n", encoding="utf-8")
            manifest = {"schema_version":4,"files":[{
                "relative_path": csv_path.name,
                "row_count": 1,
                "first_measurement_epoch_ms": 1786010400000,
                "last_measurement_epoch_ms": 1786010400000,
            }]}
            (base / "zec_measurement_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            cfg = dict(DEFAULT_CONFIG)
            cfg.update({"MEASUREMENT_LOG_DIR": tmp, "MEASUREMENT_LOG_FALLBACK_DIR":"", "MEASUREMENT_LOG_MODE":"standard"})
            with patch("web_ui.resolve_log_path", return_value=(str(csv_path), False, "test")):
                first = measurement_availability(cfg)
                second = measurement_availability(cfg)
            self.assertEqual(1, first["inventory_files_from_manifest"])
            self.assertEqual(0, first["inventory_files_scanned"])
            self.assertEqual(1, second["inventory_files_reused"])
            self.assertEqual(0, second["inventory_files_scanned"])
            self.assertEqual(1, second["row_count"])


if __name__ == "__main__":
    unittest.main()
