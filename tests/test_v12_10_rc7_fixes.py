import csv
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from csv_logger import CsvRotatingLogger
from measurement_v4 import build_v4_row
from tests.test_measurement_v4_writer import base_config, base_row
from tools import replay_web


class V12100Rc7FixTests(unittest.TestCase):
    def test_v4_safe_state_reason_is_empty_when_v4_mode_is_not_safe_state(self):
        row = base_row()
        row.update({
            "mode": "SAFE_STATE",
            "safe_state_active": True,
            "control_reason": "Ladung blockiert: Zendure SOC zu hoch",
            "target_final_w": 0,
            "active_limiters": "MAX_SOC",
            "zendure_mqtt_overall_status": "ZENDURE_MQTT_STALE",
        })
        v4 = build_v4_row(base_config("/tmp"), row)
        self.assertEqual("0", v4["safe_state_active"])
        self.assertEqual("", v4["safe_state_reason"])
        self.assertEqual("MAX_SOC_LIMIT", v4["target_final_reason"])

    def test_v4_control_fields_fall_back_when_primary_input_fields_are_empty(self):
        row = base_row()
        row.update({
            "input_grid_power_used_w": "",
            "grid_power_w": -123.4,
            "input_effective_export_used_w": "",
            "effective_export_power_w": 123.4,
            "input_effective_export_used_for_control": "",
            "effective_export_power_used_for_control": True,
        })
        v4 = build_v4_row(base_config("/tmp"), row)
        self.assertEqual(-123.4, v4["control_grid_power_w"])
        self.assertEqual(123.4, v4["control_effective_export_w"])
        self.assertEqual("1", v4["control_effective_export_valid"])

    def test_cross_charge_flags_do_not_mark_low_surplus_as_cross_charge(self):
        row = base_row()
        row.update({
            "control_path": "GRID -> CHARGE_RAMP_DOWN",
            "technical_control_path": "GRID -> CHARGE_RAMP_DOWN",
            "active_limiters": "LOW_EFFECTIVE_SURPLUS",
            "cross_charge_guard_active": False,
            "target_final_w": 0,
            "control_reason": "Keine sichere PV-Überschussladung",
        })
        v4 = build_v4_row(base_config("/tmp"), row)
        self.assertEqual("0", v4["control_cross_charge_detected"])
        self.assertEqual("0", v4["control_cross_charge_limited"])
        self.assertEqual("0", v4["target_changed_by_cross_charge"])

    def test_v4_rotation_uses_short_non_cascading_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = base_config(tmp)
            cfg["MEASUREMENT_LOG_MAX_BYTES"] = 1
            logger = CsvRotatingLogger()
            try:
                logger.log(cfg, base_row())
                logger.log(cfg, {**base_row(), "cycle_id": 2, "epoch_s": 1780000003.0})
                logger.log(cfg, {**base_row(), "cycle_id": 3, "epoch_s": 1780000006.0})
            finally:
                logger.close()
            csv_files = sorted(name for name in os.listdir(tmp) if name.startswith("zendure_measurements_v4") and name.endswith(".csv"))
            self.assertGreaterEqual(len(csv_files), 2)
            self.assertTrue(all(name.count("T") <= 1 for name in csv_files), csv_files)

    def test_replay_preflight_exposes_resource_estimate(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            csv_path = base / "zendure_measurements_v4.csv"
            from measurement_v4_contract import STANDARD_HEADER, header_hash
            csv_path.write_text(";".join(STANDARD_HEADER) + "\n" + ";".join(["4"] + [""] * (len(STANDARD_HEADER) - 1)) + "\n", encoding="utf-8")
            manifest = {"schema_version": 4, "files": [{"measurement_file_id": "mf", "logical_stream_id": "ls", "file_role": "primary_measurement", "profile": "standard", "schema_version": 4, "file_name": csv_path.name, "relative_path": csv_path.name, "header_hash": header_hash(STANDARD_HEADER), "row_count": 1, "rotation_reason": "SERVICE_START"}]}
            (base / "zec_measurement_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (base / "zec_config_snapshots.json").write_text(json.dumps({"schema_version": 4, "snapshots": []}), encoding="utf-8")
            with patch("tools.replay_web._meminfo_available_mb", return_value=500), patch("tools.replay_web._loadavg_1min", return_value=0.1):
                profile = replay_web.selection_profile([csv_path], {})
            self.assertFalse(profile["rejected"])
            self.assertIn("estimated_worker_rss_mb", profile)
            self.assertIn("estimated_ram_reserve_mb", profile)
            self.assertIn("loadavg_1min", profile)

    def test_package_tool_skips_replay_report_by_default(self):
        script = Path(__file__).resolve().parents[1] / "tools" / "create_zec_analysis_package.sh"
        text = script.read_text(encoding="utf-8")
        self.assertIn("WITH_REPLAY_REPORT=0", text)
        self.assertIn("--with-replay-report", text)
        self.assertIn("Skipping replay report by default", text)
        self.assertIn("timeout --kill-after=5s", text)


if __name__ == "__main__":
    unittest.main()
