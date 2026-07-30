import os
import tempfile
import time
import unittest

import operational_events
import version
from state import ControllerState
from web_ui import build_status_page, build_status_view_payload


from pathlib import Path
class V12112Rc5OperationsDashboardTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual("12.11.2-rc17", version.APP_VERSION)
        self.assertEqual("V12.11.2-RC17", version.APP_VERSION_LABEL)

    def test_four_lower_cards_and_calendar_hotfix_are_present(self):
        snap = ControllerState().snapshot()
        snap.update({"grid_power_valid": True, "raw_grid_power": 0, "battery_soc": 50})
        html = build_status_page({"INTERVAL_SECONDS": 2, "MEASUREMENT_DB_ENABLED": False}, snap)
        for token in ("Messdaten / Logging", "Systemressourcen", "Controller &amp; Schnittstellen", "Betriebsereignisse"):
            self.assertIn(token, html)
        self.assertIn("Systemlast (1/5/15 Min.)", html)
        self.assertIn("Letzter ausgeführter Zendure-Kommandoabgleich", html)
        self.assertIn("Wirkung anschließend bestätigt", html)
        js = Path("static/status_v2.js").read_text(encoding="utf-8")
        self.assertIn("showPicker", js)
        self.assertIn("renderEvents", js)

    def test_last_cycle_values_are_direct_not_averaged(self):
        snap = ControllerState().snapshot()
        snap.update({
            "last_cycle_total_ms": 86.4,
            "last_cycle_completed_epoch": time.time(),
            "last_cycle_timing_json": '{"control_decision_ms":3.4,"measurement_logging_ms":18.0}',
            "grid_power_valid": True,
            "raw_grid_power": 0,
        })
        payload = build_status_view_payload({"INTERVAL_SECONDS": 3, "MEASUREMENT_DB_ENABLED": False}, snap, events=[])
        self.assertEqual(86.4, payload["diag"]["loop_ms"])
        self.assertEqual(3.4, payload["diag"]["control_ms"])
        self.assertEqual(18.0, payload["diag"]["measurement_logging_ms"])

    def test_event_journal_persists_transitions_outside_controller_state(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = {"OPERATIONAL_EVENTS_DB_PATH": os.path.join(td, "events.sqlite3")}
            state = ControllerState()
            journal = operational_events.OperationalEventJournal(lambda: cfg, state)
            conn = journal._connect()
            journal._previous = {"mqtt_connected": True, "mode": "AUTO", "resync_count": 0, "zendure_telemetry": "ZENDURE_MQTT_OK", "command_effect": "effective", "measurement_logging": "active"}
            snap = state.snapshot()
            snap.update({"mqtt_connected": False, "current_mode": "AUTO", "zendure_mqtt_overall_status": "ZENDURE_MQTT_OK", "command_effect_category": "effective", "measurement_log_status": "active"})
            journal._observe(conn, snap)
            row = conn.execute("SELECT title,status FROM operational_events ORDER BY id DESC LIMIT 1").fetchone()
            conn.close()
            self.assertEqual(("MQTT-Verbindung getrennt", "open"), row)


if __name__ == "__main__":
    unittest.main()
