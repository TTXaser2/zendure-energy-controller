import csv
import json
import os
import tempfile
import unittest

from csv_logger import CsvRotatingLogger, measurement_schema_version
from measurement_v4_contract import EXTENDED_HEADER, STANDARD_HEADER
from version import APP_VERSION


def base_config(tmpdir, mode="standard"):
    return {
        "MEASUREMENT_LOG_MODE": mode,
        "MEASUREMENT_SCHEMA_VERSION": "4",
        "MEASUREMENT_LOG_STORAGE_TARGET": "internal_sd",
        "MEASUREMENT_LOG_DIR": tmpdir,
        "MEASUREMENT_LOG_FILE": "zendure_measurements.csv",
        "MEASUREMENT_LOG_MAX_BYTES": 25_000_000,
        "MEASUREMENT_LOG_BACKUP_COUNT": 2,
        "MEASUREMENT_LOG_MIN_FREE_DISK_MB": 1,
        "MEASUREMENT_LOG_FLUSH_EVERY_ROWS": 1,
        "MEASUREMENT_LOG_FLUSH_EVERY_SECONDS": 1,
        "INTERVAL_SECONDS": 3,
        "MAX_CHARGE_POWER_W": 2100,
        "MAX_DISCHARGE_POWER_W": 2100,
        "MIN_SOC_PERCENT": 15,
        "MAX_SOC_PERCENT": 99,
        "MIN_COMMAND_CHANGE_W": 50,
        "NIGHT_DISCHARGE_ENABLED": True,
        "NIGHT_DISCHARGE_POWER_W": 400,
        "NIGHT_START_HOUR": 23,
        "NIGHT_START_MINUTE": 0,
        "NIGHT_END_HOUR": 5,
        "NIGHT_END_MINUTE": 30,
        "NIGHT_DISCHARGE_STOP_SOC_PERCENT": 30,
        "SECOND_BATTERY_SOURCE_PROFILE": "evcc_standard",
    }


def base_row():
    return {
        "cycle_id": 42,
        "epoch_s": 1780000000.123,
        "loop_duration_ms": 321,
        "mode": "CHARGE",
        "mode_duration_s": 9,
        "raw_grid_power_w": -500.0,
        "grid_power_w": -480.0,
        "grid_power_valid": True,
        "grid_power_fresh": True,
        "grid_power_age_s": 2.0,
        "raw_grid_source": "Shelly/UniMeter",
        "actual_zendure_power_w": 430.0,
        "actual_zendure_power_valid": True,
        "actual_zendure_power_age_s": 1.5,
        "zendure_telemetry_source": "MQTT",
        "raw_zendure_soc_percent": 72,
        "norm_zendure_soc_percent": 72,
        "input_soc_used_percent": 72,
        "soc_valid": True,
        "soc_fresh": True,
        "soc_age_s": 2,
        "raw_zendure_soc_source": "MQTT",
        "raw_second_battery_power_w": 1200.0,
        "second_battery_power_w": 1200.0,
        "second_battery_valid": True,
        "second_battery_fresh": True,
        "second_battery_age_s": 3,
        "second_battery_soc_percent": 55,
        "scenario_grid_without_zendure_w": -910.0,
        "scenario_reconstruction_valid": True,
        "input_grid_power_used_w": -480.0,
        "norm_grid_power_smoothed_w": -450.0,
        "grid_power_used_for_control": True,
        "input_effective_export_used_w": 760,
        "input_effective_export_used_for_control": True,
        "deadband_active": False,
        "cross_charge_guard_active": False,
        "target_raw_w": 760,
        "target_after_smoothing_w": 700,
        "target_after_ramp_w": 650,
        "target_after_soc_limits_w": 650,
        "target_final_w": 650,
        "control_reason": "AUTO_GRID_EXPORT",
        "mqtt_command_required": True,
        "mqtt_command_sent": True,
        "zendure_mqtt_connected": True,
        "zendure_mqtt_overall_status": "ZENDURE_MQTT_OK",
        "zendure_mqtt_live_confirmed": True,
        "zendure_mqtt_retained_only": False,
        "zendure_mqtt_partial_stale": False,
        "zendure_mqtt_after_broker_restart_no_live_updates": False,
        "zendure_mqtt_critical_data_age_s": 2,
        "zendure_mqtt_missing_critical_groups": "",
        "zendure_mqtt_stale_critical_groups": "",
        "zendure_pack_data_json": json.dumps([
            {"pack_sn": "HEC_TEST_DEVICE", "temperature_c": 61.4},
            {"pack_sn": "pack_1", "temperature_c": 27.8},
            {"pack_sn": "pack_2", "temperature_c": 31.4},
        ]),
    }


class MeasurementV4WriterTests(unittest.TestCase):
    def test_schema_selector_defaults_legacy_without_explicit_key(self):
        self.assertEqual("3", measurement_schema_version({}))
        self.assertEqual("4", measurement_schema_version({"MEASUREMENT_SCHEMA_VERSION": "4"}))

    def test_standard_v4_writes_csv_manifest_snapshot_and_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            logger = CsvRotatingLogger()
            status = logger.log(base_config(tmp), base_row())
            logger.close()
            self.assertEqual("active", status["measurement_log_status"])
            csv_files = [name for name in os.listdir(tmp) if name.startswith("zendure_measurements_v4") and name.endswith(".csv")]
            self.assertEqual(1, len(csv_files))
            csv_path = os.path.join(tmp, csv_files[0])
            self.assertTrue(os.path.exists(csv_path))
            with open(csv_path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f, delimiter=";"))
            self.assertEqual(STANDARD_HEADER, rows[0].keys().__iter__().__self__ if False else list(rows[0].keys()))
            self.assertEqual("4", rows[0]["schema_version"])
            self.assertEqual("AUTO", rows[0]["operating_mode"])
            self.assertEqual("CHARGE", rows[0]["control_intent"])
            self.assertEqual("SENT", rows[0]["command_action"])
            self.assertEqual("650.0", rows[0]["command_effective_w"])
            self.assertNotIn("measurement_log_status", rows[0])
            self.assertNotIn("zendure_pack_temperatures_json", rows[0])

            with open(os.path.join(tmp, "zec_measurement_manifest.json"), encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertEqual(1, manifest["files"][0]["row_count"])
            self.assertEqual("primary_measurement", manifest["files"][0]["file_role"])
            self.assertEqual("standard", manifest["files"][0]["profile"])

            with open(os.path.join(tmp, "zec_config_snapshots.json"), encoding="utf-8") as f:
                snapshots = json.load(f)
            self.assertEqual(APP_VERSION, snapshots["snapshots"][0]["controller_version"])
            self.assertNotIn("MQTT_PASSWORD", json.dumps(snapshots))

            runtime_path = os.path.join(tmp, "zec_runtime_events.jsonl")
            self.assertTrue(os.path.exists(runtime_path))
            with open(runtime_path, encoding="utf-8") as f:
                self.assertIn("logging_file_opened", f.read())

    def test_extended_v4_appends_three_json_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            logger = CsvRotatingLogger()
            logger.log(base_config(tmp, mode="extended"), base_row())
            logger.close()
            csv_files = [name for name in os.listdir(tmp) if name.startswith("zendure_measurements_v4") and name.endswith(".csv")]
            self.assertEqual(1, len(csv_files))
            csv_path = os.path.join(tmp, csv_files[0])
            with open(csv_path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f, delimiter=";"))
            self.assertEqual(EXTENDED_HEADER, list(rows[0].keys()))
            pack_json = json.loads(rows[0]["zendure_pack_temperatures_json"])
            headunit_json = json.loads(rows[0]["zendure_headunit_temperatures_json"])
            mqtt_json = json.loads(rows[0]["zendure_mqtt_group_status_json"])
            self.assertEqual(2, pack_json["pack_count"])
            self.assertEqual("HEC_TEST_DEVICE", headunit_json["max_sensor_id"])
            self.assertEqual("ZENDURE_MQTT_OK", mqtt_json["overall_status"])


if __name__ == "__main__":
    unittest.main()
