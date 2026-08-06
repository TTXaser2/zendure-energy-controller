import re
import tempfile
import unittest
from pathlib import Path

from csv_logger import CsvRotatingLogger
from state import ControllerState
from tools import replay_web
from tools.replay_report import charts_html, mode_quality_table
from version import CSV_SCHEMA
from web_ui import build_settings_page, build_status_page


class V1291StabilizationTests(unittest.TestCase):
    def test_logger_pauses_once_when_existing_active_file_is_not_v3(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "zendure_measurements.csv"
            path.write_text("schema;date;grid_power_w\nZEC-MEASUREMENT-V2;2026-06-15;0\n", encoding="utf-8")
            cfg = {
                "MEASUREMENT_LOG_MODE": "standard",
                "MEASUREMENT_LOG_DIR": tmp,
                "MEASUREMENT_LOG_FILE": "zendure_measurements.csv",
                "MEASUREMENT_LOG_MIN_FREE_DISK_MB": 0,
            }
            logger = CsvRotatingLogger()
            self.addCleanup(logger.close)
            status = logger.log(cfg, {"schema": CSV_SCHEMA})
            self.assertEqual(status["measurement_log_status"], "paused_invalid_schema")
            self.assertIn("ZEC-MEASUREMENT-V3-Header", status["measurement_log_status_reason"])
            self.assertIn("ZEC-MEASUREMENT-V2", path.read_text(encoding="utf-8"))

    def test_zendure_mqtt_warning_auto_clears_when_live_topics_return(self):
        state = ControllerState()
        cfg = {
            "MQTT_CONNECTED": True,
            "ZENDURE_MQTT_CRITICAL_GROUP_STALE_SECONDS": 60,
            "ZENDURE_MQTT_AFTER_RESTART_GRACE_SECONDS": 10,
        }
        state.mark_zendure_mqtt_connect(0.0)
        state.track_zendure_mqtt_topic("Zendure/soc", "50", True, "soc", now=1.0)
        state.track_zendure_mqtt_topic("Zendure/power", "0", True, "headunit_power", now=1.0)
        state.update_zendure_mqtt_status(cfg, now=20.0)
        self.assertIn(state.snapshot()["zendure_mqtt_overall_status"], {"ZENDURE_MQTT_RETAINED_ONLY", "ZENDURE_MQTT_AFTER_BROKER_RESTART_NO_LIVE_UPDATES"})

        state.track_zendure_mqtt_topic("Zendure/soc", "51", False, "soc", now=21.0)
        state.track_zendure_mqtt_topic("Zendure/power", "25", False, "headunit_power", now=21.0)
        state.update_zendure_mqtt_status(cfg, now=22.0)
        snap = state.snapshot()
        self.assertEqual(snap["zendure_mqtt_overall_status"], "ZENDURE_MQTT_OK")
        self.assertFalse(snap["zendure_mqtt_retained_only"])
        self.assertFalse(snap["zendure_mqtt_partial_stale"])
        self.assertFalse(snap["zendure_mqtt_after_broker_restart_no_live_updates"])

    def test_replay_profile_accepts_only_v3_and_worker_protection_is_visible(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "old.csv"
            bad.write_text("schema;date;grid_power_w\nZEC-MEASUREMENT-V2;2026-06-15;0\n", encoding="utf-8")
            profile = replay_web.selection_profile([bad], {})
            self.assertTrue(profile["rejected"])
            self.assertIn("gültigen unterstützten Measurement-Dateien", profile["risk_text"])
            self.assertGreaterEqual(profile["worker_memory_limit_mb"], 128)

    def test_analysis_worker_is_subprocess_based(self):
        source = Path(replay_web.__file__).read_text(encoding="utf-8")
        self.assertIn("subprocess.Popen", source)
        self.assertIn("worker_memory_limit_mb", source)
        worker = Path(replay_web.__file__).with_name("replay_worker.py")
        self.assertTrue(worker.exists())

    def test_percent_charts_use_0_to_100_scale_and_show_rest_categories(self):
        html = charts_html({
            "fair_regulator_quality": {"controllable_percent": 24.8, "non_controllable_percent": 0.0},
            "deadband": {
                "inside_deadband_seconds": 3600,
                "inside_deadband_percent": 50.0,
                "outside_deadband_with_reserve_seconds": 600,
                "outside_deadband_with_reserve_percent": 8.0,
                "outside_deadband_without_reserve_seconds": 3000,
                "outside_deadband_without_reserve_percent": 42.0,
                "inside_extended_band_seconds": 7200,
                "inside_extended_band_percent": 100.0,
            },
            "operating_state_matrix": [
                {"mode": "NIGHT_DISCHARGE", "seconds": 6000, "percent": 86.7},
                {"mode": "AUTO_DISCHARGE", "seconds": 920, "percent": 13.3},
            ],
            "command_efficiency": {},
        })
        self.assertIn("im Zielband / toleriert", html)
        self.assertIn("außerhalb ohne Reserve", html)
        self.assertIn("Erweitertes Zielband inkl. Deadband", html)
        self.assertIn("86,7 %", html)
        self.assertRegex(html, r"NIGHT_DISCHARGE: 1 h 40 min / 86,7 %.*?style='width:86\.7%'", re.S)
        self.assertNotIn("0 s / 100 %", html)

    def test_mode_matrix_uses_net_import_export_labels_with_info(self):
        html = mode_quality_table({
            "operating_state_matrix": [{
                "mode": "NIGHT_DISCHARGE",
                "samples": 10,
                "seconds": 600,
                "grid_import_kwh": 0.001,
                "grid_export_kwh": 0.002,
                "avg_abs_grid_w": 3.8,
                "controllable_avg_w": 1.0,
                "non_controllable_avg_w": 0.0,
                "inside_target_percent": 99.0,
                "mqtt_commands": 0,
            }]
        })
        self.assertIn("Netzbezug kWh", html)
        self.assertIn("Einspeisung kWh", html)
        self.assertIn("öffentlichen Netz", html)

    def test_settings_shell_loads_measurement_explanations_from_current_model(self):
        html = build_settings_page({}, saved=False)
        script = (Path(__file__).resolve().parents[1] / "static" / "settings_v2.js").read_text(encoding="utf-8")
        self.assertIn('id="settingsContent"', html)
        self.assertIn("c.description", script)
        self.assertNotIn("legacy-settings-contract", html)

    def test_status_page_shows_zendure_mqtt_recovery_hint(self):
        s = ControllerState().snapshot()
        s.update({"zendure_mqtt_overall_status":"ZENDURE_MQTT_RETAINED_ONLY", "zendure_mqtt_live_confirmed":False})
        cfg = {"MANUAL_MODE":"AUTO", "NIGHT_DISCHARGE_ENABLED":False, "MEASUREMENT_LOG_MODE":"off"}
        html = build_status_page(cfg, s)
        self.assertIn("Zendure Live-Status", html)
        self.assertIn("Zendure-App", html)
        self.assertIn('data-zec="zendure.command_warning"', html)

    def test_update_script_cleans_stale_tests_but_not_v2_logs(self):
        script = (Path(__file__).resolve().parents[1] / "tools" / "update_zendure_controller.sh").read_text(encoding="utf-8")
        self.assertIn("rsync -a --delete \"$DIR/tests/\" \"$TARGET/tests/\"", script)
        self.assertNotIn("V2-Messdaten-Bereinigung", script)
        self.assertIn("recover_on_error", script)


if __name__ == "__main__":
    unittest.main()
