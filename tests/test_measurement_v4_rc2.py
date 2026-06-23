import csv
import json
import os
import tempfile
import unittest
from pathlib import Path

from csv_logger import CsvRotatingLogger
from measurement_v4 import build_config_snapshot, build_v4_row
from measurement_v4_contract import STANDARD_HEADER, header_hash
from tests.test_measurement_v4_writer import base_config, base_row
from tools import replay_web
from version import APP_VERSION


class MeasurementV4Rc2Tests(unittest.TestCase):
    def test_soc_limit_safe_helper_is_logged_as_auto_limiter_not_safe_state(self):
        row = base_row()
        row.update({
            "mode": "SAFE_STATE",
            "control_reason": "Ladung blockiert: Zendure SOC zu hoch",
            "target_final_w": 0,
            "mqtt_command_sent": False,
            "mqtt_command_required": True,
            "mqtt_command_skip_reason": "inputLimit -> 0",
        })
        v4 = build_v4_row(base_config("/tmp"), row, previous_effective_command_w=0)
        self.assertEqual("AUTO", v4["operating_mode"])
        self.assertEqual("NEUTRAL", v4["control_intent"])
        self.assertEqual("MAX_SOC_LIMIT", v4["target_final_reason"])
        self.assertEqual("0", v4["safe_state_active"])
        self.assertEqual("", v4["safe_state_reason"])
        self.assertEqual("0", v4["target_changed_by_safe_state"])
        self.assertEqual("SUPPRESSED", v4["command_action"])
        self.assertEqual("NO_CHANGE", v4["command_suppressed_reason"])

    def test_v3_field_fallbacks_fill_control_inputs(self):
        row = base_row()
        row.pop("input_grid_power_used_w", None)
        row.pop("grid_power_w", None)
        row["grid_power"] = -123.4
        row.pop("input_effective_export_used_w", None)
        row.pop("effective_export_power_w", None)
        row["effective_export_power"] = 456.0
        row["effective_export_power_valid"] = True
        v4 = build_v4_row(base_config("/tmp"), row)
        self.assertEqual(-123.4, v4["control_grid_power_w"])
        self.assertEqual(456.0, v4["control_effective_export_w"])
        self.assertEqual("1", v4["control_effective_export_valid"])

    def test_second_battery_not_missing_required_when_stale_block_disabled_and_not_guarding(self):
        cfg = base_config("/tmp")
        cfg["SECOND_BATTERY_STALE_BLOCK_CHARGE"] = False
        row = base_row()
        row["control_missing_required_sources"] = "second_battery"
        row["cross_charge_guard_active"] = False
        v4 = build_v4_row(cfg, row)
        self.assertEqual(0, v4["control_missing_required_source_mask"])
        self.assertEqual(0, v4["control_missing_required_source_count"])
        self.assertEqual("1", v4["control_input_valid"])

    def test_snapshot_exposes_new_cross_charge_significant_key_from_legacy_key(self):
        cfg = base_config("/tmp")
        cfg.pop("CROSS_CHARGE_SIGNIFICANT_W", None)
        cfg["SMA_DISCHARGE_BLOCK_W"] = 80
        snapshot = build_config_snapshot(cfg)
        params = snapshot["control_parameters"]
        self.assertEqual(80, params["CROSS_CHARGE_SIGNIFICANT_W"])
        self.assertEqual(80, params["SMA_DISCHARGE_BLOCK_W"])

    def test_manifest_created_time_is_stable_and_row_count_matches_written_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = base_config(tmp)
            cfg["MEASUREMENT_LOG_FLUSH_EVERY_ROWS"] = 1000
            logger = CsvRotatingLogger()
            row1 = base_row()
            row2 = base_row()
            row2["cycle_id"] = 43
            row2["epoch_s"] = row1["epoch_s"] + 3
            logger.log(cfg, row1)
            with open(os.path.join(tmp, "zec_measurement_manifest.json"), encoding="utf-8") as f:
                first_manifest = json.load(f)
            created = first_manifest["files"][0]["created_time_utc"]
            logger.log(cfg, row2)
            logger.close()
            with open(os.path.join(tmp, "zendure_measurements_v4.csv"), newline="", encoding="utf-8") as f:
                data_rows = list(csv.DictReader(f, delimiter=";"))
            with open(os.path.join(tmp, "zec_measurement_manifest.json"), encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertEqual(2, len(data_rows))
            self.assertEqual(2, manifest["files"][0]["row_count"])
            self.assertEqual(created, manifest["files"][0]["created_time_utc"])

    def test_replay_selection_profile_recognizes_v4_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            csv_path = base / "zendure_measurements_v4.csv"
            csv_path.write_text(";".join(STANDARD_HEADER) + "\n" + ";".join(["4"] + [""] * (len(STANDARD_HEADER) - 1)) + "\n", encoding="utf-8")
            manifest = {
                "schema_version": 4,
                "files": [{
                    "measurement_file_id": "mf_test",
                    "logical_stream_id": "ls_test",
                    "file_role": "primary_measurement",
                    "profile": "standard",
                    "schema_version": 4,
                    "file_name": csv_path.name,
                    "relative_path": csv_path.name,
                    "header_hash": header_hash(STANDARD_HEADER),
                    "first_measurement_epoch_ms": "",
                    "last_measurement_epoch_ms": "",
                    "row_count": 1,
                    "rotation_reason": "SERVICE_START",
                    "created_time_utc": "2026-06-23T00:00:00Z",
                    "closed_time_utc": "",
                }],
            }
            (base / "zec_measurement_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (base / "zec_config_snapshots.json").write_text(json.dumps({"schema_version": 4, "snapshots": []}), encoding="utf-8")
            (base / "zec_runtime_events.jsonl").write_text('{"event_time_utc":"2026-06-23T00:00:00Z","event_type":"logging_file_opened"}\n', encoding="utf-8")
            profile = replay_web.selection_profile([csv_path], {})
            self.assertEqual("v4", profile["schema_family"])
            self.assertFalse(profile["rejected"])
            self.assertIn("V4-Ist-Datenanalyse", profile["risk_text"])
            self.assertEqual([], profile["schema_errors"])


if __name__ == "__main__":
    unittest.main()
