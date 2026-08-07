import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import operational_events
import system_metrics
import version
# Installs the paho-mqtt test stub before importing controller_logic.
from tests import test_operation_priority as _operation_priority_stub  # noqa: F401
from controller_logic import ZendureController
from measurement_db import MeasurementDbWriter, extract_measurement_point
from state import ControllerState
from web_ui import build_status_view_payload


class V12112Rc7BacklogReleaseTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual("12.11.6", version.APP_VERSION)
        self.assertEqual("V12.11.6", version.APP_VERSION_LABEL)

    def test_age_zero_is_fresh_not_stale(self):
        state = ControllerState()
        now = 1_000.0
        state.mqtt_connected = True
        state.zendure_mqtt_connect_epoch = now - 100
        state.zendure_mqtt_topics = {
            "Zendure/sensor/device/electricLevel": {
                "topic_group": "soc",
                "last_received_at": now,
                "last_payload_changed_at": now,
                "live_confirmed": True,
                "message_count_since_connect": 1,
                "non_retained_seen_count_since_connect": 1,
            },
            "Zendure/sensor/device/outputHomePower": {
                "topic_group": "headunit_power",
                "last_received_at": now,
                "last_payload_changed_at": now,
                "live_confirmed": True,
                "message_count_since_connect": 1,
                "non_retained_seen_count_since_connect": 1,
            },
        }
        state.update_zendure_mqtt_status(
            {
                "ZENDURE_MQTT_CRITICAL_GROUP_STALE_SECONDS": 90,
                "ZENDURE_MQTT_AFTER_RESTART_GRACE_SECONDS": 30,
            },
            now=now,
        )
        self.assertEqual("ZENDURE_MQTT_OK", state.zendure_mqtt_overall_status)
        self.assertEqual("", state.zendure_mqtt_stale_critical_groups)
        self.assertEqual(0, state.zendure_mqtt_critical_data_age_s)

    def test_suppressed_resync_is_separate_and_confirmed_mismatch_stays_latch_safe(self):
        controller = ZendureController.__new__(ZendureController)
        controller.state = ControllerState()
        controller._last_resync_signature = "-400|RESYNC_AFTER_LONG_STALE"
        controller._last_resync_epoch = 1_000.0
        controller.state.command_resync_reason = "RESYNC_AFTER_RECONNECT"
        cfg = {"COMMAND_RESYNC_COOLDOWN_SECONDS": 120}
        with patch("controller_logic.time.time", return_value=1_050.0):
            permitted = controller._resync_permitted(-400, "RESYNC_AFTER_LONG_STALE", cfg)
        self.assertFalse(permitted)
        self.assertEqual("RESYNC_AFTER_RECONNECT", controller.state.command_resync_reason)
        self.assertEqual(1, controller.state.command_resync_suppressed_count)
        self.assertEqual("RESYNC_SUPPRESSED_COOLDOWN", controller.state.command_resync_suppressed_reason)
        with patch("controller_logic.time.time", return_value=1_051.0):
            self.assertTrue(
                controller._resync_permitted(
                    -400,
                    "RESYNC_AFTER_LONG_STALE",
                    cfg,
                    confirmed_mismatch=True,
                )
            )

    def test_control_timing_excludes_nested_mqtt_setter_time(self):
        controller = ZendureController.__new__(ZendureController)
        controller._cycle_timing_parts = {}

        def operation():
            controller._timed_mqtt_setter(lambda: None)

        with patch("controller_logic.time.perf_counter_ns", side_effect=[0, 2_000_000, 5_000_000, 10_000_000]):
            controller._timed_control_phase(operation)
        self.assertEqual(3.0, controller._cycle_timing_parts["mqtt_command_path_ms"])
        self.assertEqual(7.0, controller._cycle_timing_parts["control_decision_ms"])

    def test_command_effect_timing_excludes_nested_mqtt_resend_time(self):
        controller = ZendureController.__new__(ZendureController)
        controller._cycle_timing_parts = {}

        def operation():
            controller._timed_mqtt_setter(lambda: None)

        with patch("controller_logic.time.perf_counter_ns", side_effect=[0, 1_000_000, 4_000_000, 9_000_000]):
            controller._timed_command_effect_phase(operation)
        self.assertEqual(3.0, controller._cycle_timing_parts["mqtt_command_path_ms"])
        self.assertEqual(6.0, controller._cycle_timing_parts["command_effect_monitor_ms"])

    def test_db_worker_records_real_duration_and_payload_uses_epoch_field(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "measurements.sqlite3")
            point = extract_measurement_point(
                {
                    "measurement_epoch_ms": "1784500000000",
                    "operating_mode": "AUTO",
                    "zendure_soc_percent": "50",
                    "grid_power_valid": "1",
                }
            )
            self.assertIsNotNone(point)
            writer = MeasurementDbWriter()
            try:
                writer._flush(path, [point])
                status = writer.status()
                self.assertIsNotNone(status["measurement_db_last_write_duration_ms"])
                self.assertGreaterEqual(status["measurement_db_last_write_duration_ms"], 0)
                snap = ControllerState().snapshot()
                snap.update(
                    {
                        "grid_power_valid": True,
                        "raw_grid_power": 0,
                        "measurement_db_last_write_epoch_s": time.time() - 2,
                        "measurement_db_last_write_duration_ms": status["measurement_db_last_write_duration_ms"],
                    }
                )
                payload = build_status_view_payload(
                    {"INTERVAL_SECONDS": 2, "MEASUREMENT_DB_ENABLED": True, "MEASUREMENT_DB_PATH": path},
                    snap,
                    events=[],
                )
                self.assertTrue(payload["logging"]["last_write"].startswith("vor "))
                self.assertIsNotNone(payload["diag"]["sqlite_ms"])
            finally:
                writer.close()

    def test_confirmed_mismatch_resync_suffix_is_translated_for_ui(self):
        import web_ui
        self.assertEqual(
            "nach bestätigter Abweichung zwischen Sollwert und Gerätewirkung",
            web_ui._command_resync_public_reason("RESYNC_AFTER_CONFIRMED_MISMATCH_45s"),
        )

    def test_timing_payload_is_hierarchical_and_parent_summaries_are_not_leaf_rows(self):
        snap = ControllerState().snapshot()
        timing = {
            "cycle_total_without_sleep_ms": 40.0,
            "run_once_ms": 30.0,
            "finish_cycle_ms": 10.0,
            "zendure_local_api_ms": 12.0,
            "control_decision_ms": 4.0,
            "mqtt_command_path_ms": 1.0,
            "measurement_logging_ms": 5.0,
            "other_cycle_work_ms": 18.0,
        }
        snap.update(
            {
                "grid_power_valid": True,
                "raw_grid_power": 0,
                "last_cycle_total_ms": 40.0,
                "last_cycle_completed_epoch": time.time(),
                "last_cycle_timing_json": json.dumps(timing),
                "last_cycle_slowest_step": "zendure_local_api_ms",
                "last_cycle_slowest_step_ms": 12.0,
            }
        )
        payload = build_status_view_payload(
            {"INTERVAL_SECONDS": 2, "MEASUREMENT_DB_ENABLED": False}, snap, events=[]
        )
        labels = [row["label"] for row in payload["diag"]["timing_phases"]]
        self.assertIn("Zendure Local API", labels)
        self.assertIn("Regelentscheidung", labels)
        self.assertNotIn("Controller-Hauptteil (Sammelwert)", labels)
        self.assertNotIn("Zyklusabschluss (Sammelwert)", labels)
        self.assertEqual("Zendure Local API", payload["diag"]["slowest_step"])
        self.assertIn("Sonstige, nicht einzeln erfasste Verarbeitung", labels)
        self.assertAlmostEqual(40.0 / 2040.0 * 100.0, payload["diag"]["cycle_active_share_percent"], places=5)

    def test_residual_timing_is_never_selected_as_slowest_measured_phase(self):
        source = Path("controller_logic.py").read_text(encoding="utf-8")
        block = source[source.index("measured_parts = {"):source.index("self.state.set_cycle_timing", source.index("measured_parts = {"))]
        self.assertNotIn('for key in (*leaf_keys, "other_cycle_work_ms")', block)
        self.assertIn("for key in leaf_keys", block)

    def test_timing_statistics_are_bounded_and_include_mean_p95_max(self):
        state = ControllerState()
        for value in range(1, 71):
            state.set_cycle_timing(
                {"cycle_total_without_sleep_ms": float(value)},
                "other_cycle_work_ms",
                float(value),
                float(value),
            )
        stats = json.loads(state.last_cycle_timing_stats_json)
        total = stats["cycle_total_without_sleep_ms"]
        self.assertEqual(60, total["samples"])
        self.assertEqual(40.5, total["mean_ms"])
        self.assertEqual(67.0, total["p95_ms"])
        self.assertEqual(70.0, total["max_ms"])

    def test_telemetry_journal_ignores_one_cycle_flap(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = {"OPERATIONAL_EVENTS_DB_PATH": os.path.join(td, "events.sqlite3")}
            journal = operational_events.OperationalEventJournal(lambda: cfg, ControllerState())
            conn = journal._connect()
            journal._previous["stable:zendure_telemetry"] = False
            with patch("operational_events.time.monotonic", side_effect=[0.0, 2.0, 3.0]):
                journal._stable_incident(
                    conn,
                    "zendure_telemetry",
                    True,
                    title_bad="bad",
                    title_ok="ok",
                    detail_bad="brief",
                    detail_ok="restored",
                )
                journal._stable_incident(
                    conn,
                    "zendure_telemetry",
                    True,
                    title_bad="bad",
                    title_ok="ok",
                    detail_bad="brief",
                    detail_ok="restored",
                )
                journal._stable_incident(
                    conn,
                    "zendure_telemetry",
                    False,
                    title_bad="bad",
                    title_ok="ok",
                    detail_bad="brief",
                    detail_ok="restored",
                )
            count = conn.execute("SELECT COUNT(*) FROM operational_events").fetchone()[0]
            conn.close()
            self.assertEqual(0, count)

    def test_persistent_bad_telemetry_at_observer_start_opens_after_stability_window(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = {"OPERATIONAL_EVENTS_DB_PATH": os.path.join(td, "events.sqlite3")}
            journal = operational_events.OperationalEventJournal(lambda: cfg, ControllerState())
            conn = journal._connect()
            try:
                with patch("operational_events.time.monotonic", side_effect=[0.0, 3.0, 6.1]):
                    for _ in range(3):
                        journal._stable_incident(
                            conn,
                            "zendure_telemetry",
                            True,
                            title_bad="bad",
                            title_ok="ok",
                            detail_bad="persistent",
                            detail_ok="restored",
                        )
                row = conn.execute(
                    "SELECT status,title,detail FROM operational_events ORDER BY id DESC LIMIT 1"
                ).fetchone()
                self.assertEqual(("open", "bad", "persistent"), row)
            finally:
                conn.close()

    def test_swap_activity_uses_vmstat_deltas(self):
        system_metrics._prev_swap = None
        with patch("system_metrics._read", side_effect=["pswpin 10\npswpout 20", "pswpin 12\npswpout 23"]), patch(
            "system_metrics.time.monotonic", side_effect=[100.0, 102.0]
        ), patch("system_metrics.os.sysconf", return_value=4096):
            first = system_metrics._swap_activity()
            second = system_metrics._swap_activity()
        self.assertIsNone(first["swap_in_bytes_per_s"])
        self.assertEqual(4096.0, second["swap_in_bytes_per_s"])
        self.assertEqual(6144.0, second["swap_out_bytes_per_s"])

    def test_frontend_contains_real_date_button_monotone_soc_and_timing_tree(self):
        html = Path("status_page_v2.py").read_text(encoding="utf-8")
        js = Path("static/status_v2.js").read_text(encoding="utf-8")
        css = Path("static/status_v2.css").read_text(encoding="utf-8")
        self.assertIn('id="socDayPickerButton"', html)
        self.assertIn("dayPickerButton.addEventListener('click',openDayPicker)", js)
        self.assertIn("reconstructQuantizedSoc", js)
        self.assertIn("drawQuantizedSocLine", js)
        self.assertIn('id="diagTimingTree"', html)
        self.assertIn(".zec-timing-tree:before", css)
        self.assertIn("@media (pointer:coarse)", css)
        self.assertIn(".zec-day-picker-wrap .zec-day-picker-input{inset:0;width:100%;height:100%", css)
        self.assertNotIn(".zec-day-picker-label input{position:absolute;inset:0", css)

    def test_diagnostic_tool_uses_journalctl_compatible_timestamp(self):
        script = Path("tools/collect_resync_diagnostics.sh").read_text(encoding="utf-8")
        self.assertIn("date '+%Y-%m-%d %H:%M:%S'", script)
        self.assertIn('--since "$START_JOURNAL"', script)
        self.assertNotIn("date --iso-8601=seconds", script)


if __name__ == "__main__":
    unittest.main()
