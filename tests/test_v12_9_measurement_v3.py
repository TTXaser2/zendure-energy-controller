import csv
import io
import os
import tempfile
import unittest

from config_manager import validate_config
from csv_logger import (
    CSV_FIELDS,
    CsvRotatingLogger,
    estimate_retention_hours,
    measurement_log_mode,
    rows_to_csv,
)
from state import ControllerState
from tools.replay_core import read_measurement_csv
from version import CSV_SCHEMA


class V129MeasurementV3Tests(unittest.TestCase):
    def test_v3_contract_contains_standard_diagnostic_fields(self):
        required = {
            "schema",
            "schema_version",
            "measurement_profile",
            "scenario_grid_without_zendure_w",
            "target_raw_w",
            "target_after_deadband_w",
            "target_final_w",
            "mqtt_command_sent",
            "zendure_mqtt_overall_status",
            "zendure_mqtt_live_confirmed",
            "zendure_mqtt_retained_only",
            "zendure_mqtt_partial_stale",
            "zendure_mqtt_after_broker_restart_no_live_updates",
            "zendure_mqtt_missing_critical_groups",
            "zendure_mqtt_stale_critical_groups",
        }
        self.assertEqual(CSV_SCHEMA, "ZEC-MEASUREMENT-V3")
        self.assertTrue(required.issubset(set(CSV_FIELDS)))

    def test_standard_and_extended_use_same_header_but_standard_blanks_extended_json(self):
        logger = CsvRotatingLogger()
        self.addCleanup(logger.close)
        base_row = {
            "schema": CSV_SCHEMA,
            "zendure_mqtt_topic_groups_json": '{"soc":{"fresh":true}}',
            "zendure_mqtt_topics_json": '{"topic":{"age_s":1}}',
            "zendure_units_json": '[{"unit_id":"primary"}]',
        }
        standard = logger.prepare_row({"MEASUREMENT_LOG_MODE": "standard"}, base_row)
        extended = logger.prepare_row({"MEASUREMENT_LOG_MODE": "extended"}, base_row)

        self.assertEqual(standard["measurement_profile"], "standard")
        self.assertEqual(extended["measurement_profile"], "extended")
        self.assertEqual(standard["zendure_mqtt_topics_json"], "")
        self.assertEqual(extended["zendure_mqtt_topics_json"], '{"topic":{"age_s":1}}')

        text = rows_to_csv([standard, extended])
        header = text.splitlines()[0]
        self.assertIn("zendure_mqtt_topics_json", header)
        rows = list(csv.DictReader(io.StringIO(text), delimiter=";"))
        self.assertEqual(rows[0]["measurement_profile"], "standard")
        self.assertEqual(rows[1]["measurement_profile"], "extended")

    def test_legacy_csv_log_enabled_is_translated_to_measurement_mode(self):
        self.assertEqual(measurement_log_mode({"CSV_LOG_ENABLED": True}), "standard")
        self.assertEqual(measurement_log_mode({"CSV_LOG_ENABLED": False}), "off")

        migrated, changed = validate_config({"CSV_LOG_ENABLED": True, "CSV_LOG_MAX_BYTES": 123456})
        self.assertTrue(changed)
        self.assertEqual(migrated["MEASUREMENT_LOG_MODE"], "standard")
        self.assertEqual(migrated["MEASUREMENT_LOG_MAX_BYTES"], 123456)

        migrated_off, _ = validate_config({"CSV_LOG_ENABLED": False})
        self.assertEqual(migrated_off["MEASUREMENT_LOG_MODE"], "off")

    def test_retention_estimate_is_positive_and_disk_guard_pauses_logging(self):
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
            logger._free_disk_mb = lambda directory: 1
            status = logger.log(cfg, {"schema": CSV_SCHEMA})
            self.assertEqual(status["measurement_log_status"], "paused_disk_low")
            self.assertFalse(os.path.exists(os.path.join(tmp, "zendure_measurements.csv")))

    def test_replay_rejects_v2_without_legacy_parser(self):
        content = "schema;date;timestamp;grid_power_w\nZEC-MEASUREMENT-V2;2026-06-15;12:00:00;0\n"
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(content)
            path = f.name
        try:
            with self.assertRaisesRegex(ValueError, "ZEC-MEASUREMENT-V3"):
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
