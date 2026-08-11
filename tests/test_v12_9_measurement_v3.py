import csv
import os
import tempfile
import unittest
from unittest.mock import patch

from config_manager import validate_config
from csv_logger import CsvRotatingLogger, estimate_retention_hours, measurement_log_mode, rows_to_csv, GRAPH_EXPORT_SCHEMA
from measurement_v4_contract import EXTENDED_HEADER, STANDARD_HEADER
from state import ControllerState
from tools.replay_core import LEGACY_V3_SCHEMA, read_measurement_csv


class V129MeasurementCompatibilityTests(unittest.TestCase):
    def test_v4_contract_contains_required_diagnostic_fields(self):
        required = {
            "schema_version",
            "scenario_grid_without_zendure_w",
            "target_raw_w",
            "target_final_w",
            "command_sent_flag",
            "zendure_mqtt_status",
            "zendure_mqtt_live_confirmed",
        }
        self.assertTrue(required.issubset(set(STANDARD_HEADER)))
        self.assertGreater(len(EXTENDED_HEADER), len(STANDARD_HEADER))

    def test_graph_export_has_own_non_measurement_identity(self):
        text = rows_to_csv([{"grid_power_w": 0, "mode": "HOLD"}])
        rows = list(csv.DictReader(__import__("io").StringIO(text), delimiter=";"))
        self.assertEqual(GRAPH_EXPORT_SCHEMA, rows[0]["schema"])
        self.assertEqual("1.0", rows[0]["schema_version"])

    def test_legacy_csv_log_enabled_is_translated_to_measurement_mode(self):
        self.assertEqual(measurement_log_mode({"CSV_LOG_ENABLED": True}), "standard")
        self.assertEqual(measurement_log_mode({"CSV_LOG_ENABLED": False}), "off")

        migrated, changed = validate_config({"CSV_LOG_ENABLED": True, "CSV_LOG_MAX_BYTES": 123456})
        self.assertTrue(changed)
        self.assertEqual(migrated["MEASUREMENT_LOG_MODE"], "standard")
        self.assertEqual(migrated["MEASUREMENT_LOG_MAX_BYTES"], 123456)
        self.assertEqual(migrated["MEASUREMENT_SCHEMA_VERSION"], "4")

        migrated_off, _ = validate_config({"CSV_LOG_ENABLED": False})
        self.assertEqual(migrated_off["MEASUREMENT_LOG_MODE"], "off")

    def test_retention_estimate_is_positive_and_v4_disk_guard_pauses_logging(self):
        hours = estimate_retention_hours({
            "MEASUREMENT_LOG_MAX_BYTES": 25_000_000,
            "MEASUREMENT_LOG_BACKUP_COUNT": 5,
            "MEASUREMENT_LOG_ESTIMATED_ROW_BYTES": 4096,
            "INTERVAL_SECONDS": 3,
        })
        self.assertIsNotNone(hours)
        self.assertGreater(hours, 0)

        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
                "MEASUREMENT_LOG_MODE": "standard",
                "MEASUREMENT_LOG_DIR": tmp,
                "MEASUREMENT_LOG_FILE": "zendure_measurements.csv",
                "MEASUREMENT_LOG_MIN_FREE_DISK_MB": 500,
            }
            logger = CsvRotatingLogger()
            self.addCleanup(logger.close)
            with patch("measurement_v4.MeasurementV4Logger._free_disk_mb", return_value=1):
                status = logger.log(cfg, {"epoch": 1, "mode": "HOLD", "grid_power_w": 0})
            self.assertEqual(status["measurement_log_status"], "paused_disk_low")
            self.assertFalse(any(name.endswith(".csv") for name in os.listdir(tmp)))

    def test_historical_v3_reader_remains_offline_read_only(self):
        content = "schema;date;timestamp;grid_power_w;norm_zendure_soc_percent\n" + f"{LEGACY_V3_SCHEMA};2026-06-15;12:00:00;0;75\n"
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(content)
            path = f.name
        try:
            parsed = read_measurement_csv(path)
            self.assertEqual(parsed.rows[0]["schema"], LEGACY_V3_SCHEMA)
        finally:
            os.remove(path)

    def test_replay_rejects_v2_without_legacy_parser(self):
        content = "schema;date;timestamp;grid_power_w\nZEC-MEASUREMENT-V2;2026-06-15;12:00:00;0\n"
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(content)
            path = f.name
        try:
            with self.assertRaisesRegex(ValueError, "historische V3|V3-Dateien"):
                read_measurement_csv(path)
        finally:
            os.remove(path)

    def test_zendure_mqtt_aggregate_detects_retained_only_and_live_ok(self):
        state = ControllerState()
        cfg = {
            "MQTT_CONNECTED": True,
            "ZENDURE_MQTT_CRITICAL_GROUP_STALE_SECONDS": 60,
            "ZENDURE_MQTT_AFTER_RESTART_GRACE_SECONDS": 60,
        }
        state.mark_zendure_mqtt_connect(100.0)
        state.track_zendure_mqtt_topic("Zendure/soc", "50", True, "soc", now=101.0)
        state.track_zendure_mqtt_topic("Zendure/power", "0", True, "headunit_power", now=101.0)
        state.update_zendure_mqtt_status(cfg, now=102.0)
        snap = state.snapshot()
        self.assertEqual(snap["zendure_mqtt_overall_status"], "ZENDURE_MQTT_RETAINED_ONLY")
        self.assertTrue(snap["zendure_mqtt_retained_only"])

        state.track_zendure_mqtt_topic("Zendure/soc", "51", False, "soc", now=103.0)
        state.track_zendure_mqtt_topic("Zendure/power", "10", False, "headunit_power", now=103.0)
        state.update_zendure_mqtt_status(cfg, now=104.0)
        snap = state.snapshot()
        self.assertEqual(snap["zendure_mqtt_overall_status"], "ZENDURE_MQTT_OK")
        self.assertTrue(snap["zendure_mqtt_live_confirmed"])


if __name__ == "__main__":
    unittest.main()
