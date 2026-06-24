import csv
import json
import tempfile
import unittest
from pathlib import Path

from measurement_v4_contract import STANDARD_HEADER, header_hash
from tools import replay_web
from tools.replay_core import AnalysisLimits, analyze_files


class MeasurementV4Rc4Tests(unittest.TestCase):
    def _write_v4_fixture(self, base: Path) -> Path:
        csv_path = base / "zendure_measurements_v4_20260623T000000Z.csv"
        row = {field: "" for field in STANDARD_HEADER}
        row.update({
            "schema_version": "4",
            "cycle_index": "1",
            "measurement_time_utc": "2026-06-23T00:00:00.000Z",
            "measurement_epoch_ms": "1782172800000",
            "cycle_duration_ms": "42",
            "config_control_hash": "hash1",
            "operating_mode": "AUTO",
            "control_intent": "NEUTRAL",
            "control_input_valid": "1",
            "safe_state_active": "0",
            "grid_power_w": "12.0",
            "grid_power_valid": "1",
            "grid_power_fresh": "1",
            "zendure_actual_power_w": "0",
            "zendure_actual_power_valid": "1",
            "zendure_actual_power_fresh": "1",
            "zendure_soc_percent": "88",
            "control_soc_percent": "88",
            "zendure_soc_valid": "1",
            "zendure_soc_fresh": "1",
            "target_final_w": "0",
            "target_final_reason": "DEADBAND",
            "command_action": "SUPPRESSED",
            "command_suppressed_reason": "NO_CHANGE",
            "command_sent_flag": "0",
            "command_mqtt_connected": "1",
        })
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=STANDARD_HEADER, delimiter=";")
            writer.writeheader()
            writer.writerow(row)
        manifest = {"schema_version": 4, "files": [{
            "measurement_file_id": "mf_test",
            "logical_stream_id": "ls_test",
            "file_role": "primary_measurement",
            "profile": "standard",
            "schema_version": 4,
            "file_name": csv_path.name,
            "relative_path": csv_path.name,
            "header_hash": header_hash(STANDARD_HEADER),
            "first_measurement_epoch_ms": 1782172800000,
            "last_measurement_epoch_ms": 1782172800000,
            "row_count": 1,
            "rotation_reason": "SERVICE_START",
            "created_time_utc": "2026-06-23T00:00:00Z",
            "closed_time_utc": "",
        }]}
        (base / "zec_measurement_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        snapshots = {"schema_version": 4, "snapshots": [{
            "config_control_hash": "hash1",
            "schema_version": 4,
            "controller_version": "12.10.0-rc4",
            "created_time_utc": "2026-06-23T00:00:00Z",
            "source": "test",
            "control_parameters": {"MAX_CHARGE_POWER_W": 2400, "MAX_DISCHARGE_POWER_W": 2400},
        }]}
        (base / "zec_config_snapshots.json").write_text(json.dumps(snapshots), encoding="utf-8")
        (base / "zec_runtime_events.jsonl").write_text('{"event_time_utc":"2026-06-23T00:00:00Z","event_type":"logging_file_opened"}\n', encoding="utf-8")
        return csv_path

    def test_v4_analysis_runs_in_core(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = self._write_v4_fixture(Path(tmp))
            result = analyze_files([str(csv_path)], limits=AnalysisLimits(max_files=2, max_total_bytes=1024 * 1024, max_rows=100))
            self.assertEqual("ZEC-MEASUREMENT-V4", result["schema"])
            self.assertEqual(1, result["rows"])
            self.assertEqual("standard", result["v4_analysis"]["profile"])
            self.assertEqual(42.0, result["v4_analysis"]["cycle_duration_ms_max"])

    def test_v4_selection_profile_is_not_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = self._write_v4_fixture(Path(tmp))
            profile = replay_web.selection_profile([csv_path], {})
            self.assertEqual("v4", profile["schema_family"])
            self.assertFalse(profile["rejected"])
            self.assertIn("V4-Ist-Datenanalyse", profile["risk_text"])

    def test_ui_help_texts_do_not_contain_rc_history(self):
        text = Path("web_ui.py").read_text(encoding="utf-8")
        self.assertNotIn("RC3 ergänzt", text)
        self.assertNotIn("Gesamt ohne Sleep", text)
        self.assertIn("Aktive Zykluszeit", text)


if __name__ == "__main__":
    unittest.main()
