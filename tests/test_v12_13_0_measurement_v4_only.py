import csv
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import version
from config_manager import DEFAULT_CONFIG, validate_config
from csv_logger import GRAPH_EXPORT_SCHEMA, CsvRotatingLogger, measurement_schema_version, rows_to_csv
from measurement_v4_contract import (
    EXTENDED_HEADER,
    MEASUREMENT_SCHEMA_NAME,
    MEASUREMENT_SCHEMA_VERSION,
    STANDARD_HEADER,
)
from settings_registry import SETTINGS_BY_KEY
from settings_runtime import migrate_rc19_to_rc20
from state import ControllerState
from tests.test_measurement_v4_writer import base_config, base_row
from tools.replay_core import CURRENT_MEASUREMENT_SCHEMA, LEGACY_V3_SCHEMA, read_measurement_csv


ROOT = Path(__file__).resolve().parents[1]


class V12130MeasurementV4OnlyTests(unittest.TestCase):
    def test_productive_schema_constants_are_v4(self):
        self.assertEqual("ZEC-MEASUREMENT-V4", MEASUREMENT_SCHEMA_NAME)
        self.assertEqual(4, MEASUREMENT_SCHEMA_VERSION)
        self.assertEqual("ZEC-MEASUREMENT-V4", CURRENT_MEASUREMENT_SCHEMA)
        self.assertFalse(hasattr(version, "CSV_SCHEMA"))

    def test_runtime_schema_selector_is_inert_and_always_v4(self):
        for cfg in ({}, {"MEASUREMENT_SCHEMA_VERSION": "4"}, {"MEASUREMENT_SCHEMA_VERSION": "3"}, {"MEASUREMENT_LOG_SCHEMA": "3"}):
            self.assertEqual("4", measurement_schema_version(cfg))

    def test_config_migrates_historical_schema_3_to_fixed_4(self):
        migrated, changed = validate_config({"MEASUREMENT_SCHEMA_VERSION": "3", "MEASUREMENT_LOG_MODE": "standard"})
        self.assertTrue(changed)
        self.assertEqual("4", migrated["MEASUREMENT_SCHEMA_VERSION"])
        migrated2, changed2 = validate_config(migrated)
        self.assertEqual("4", migrated2["MEASUREMENT_SCHEMA_VERSION"])
        self.assertFalse(changed2)

    def test_missing_schema_marker_normalizes_to_4(self):
        migrated, changed = validate_config({"MEASUREMENT_LOG_MODE": "standard"})
        self.assertTrue(changed)
        self.assertEqual("4", migrated["MEASUREMENT_SCHEMA_VERSION"])

    def test_registry_marker_has_no_legacy_option(self):
        spec = SETTINGS_BY_KEY["MEASUREMENT_SCHEMA_VERSION"]
        self.assertEqual((('4', 'ZEC-MEASUREMENT-V4'),), spec.options)
        self.assertEqual("hidden_migration", spec.visibility.value)
        log_mode = SETTINGS_BY_KEY["MEASUREMENT_LOG_MODE"]
        self.assertNotIn("MEASUREMENT_SCHEMA_VERSION", log_mode.dependency_keys)


    def test_release_migration_normalizes_legacy_schema_marker_idempotently(self):
        migrated, steps = migrate_rc19_to_rc20({"MEASUREMENT_SCHEMA_VERSION": "3"})
        self.assertEqual("4", migrated["MEASUREMENT_SCHEMA_VERSION"])
        self.assertIn("MIG-V12.13-MEASUREMENT-SCHEMA-3-TO-4", steps)
        migrated2, steps2 = migrate_rc19_to_rc20(migrated)
        self.assertEqual(migrated, migrated2)
        self.assertEqual((), steps2)


    def test_installer_accepts_v12_13_0_and_targets_v13_0_1_without_v3_runtime(self):
        script = (ROOT / "tools/update_zendure_controller.sh").read_text(encoding="utf-8")
        self.assertIn('EXPECTED_VERSION="v13_0_1"', script)
        self.assertIn('EXPECTED_SOURCE_VERSION="12.13.0"', script)
        self.assertIn('EXPECTED_SOURCE_BUILD_ID="v12.13.0-20260811"', script)
        self.assertIn('SOURCE_MODE="V12_13_0"', script)
        self.assertIn('EXPECTED_TARGET_BUILD_ID="v13.0.1-20260811"', script)
        self.assertIn('V13_0_1_SOURCE_MANIFEST.sha256', script)
        self.assertIn('backfill_graph_config_timeline.py', script)
        self.assertNotIn('SOURCE_MODE="V12_12_2"', script)

    def test_release_migration_cli_moves_schema_3_to_4_and_then_noops(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "config.json"
            cfg = dict(DEFAULT_CONFIG)
            cfg["DEVICE_ID"] = "TESTDEVICE"
            cfg["MEASUREMENT_SCHEMA_VERSION"] = "3"
            path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
            os.chmod(path, 0o600)

            check = subprocess.run(
                [sys.executable, str(ROOT / "tools/migrate_rc19_to_rc20.py"),
                 "--config", str(path), "--check-only", "--json"],
                cwd=ROOT, check=True, capture_output=True, text=True,
            )
            planned = json.loads(check.stdout)
            self.assertTrue(planned["changed"])
            self.assertIn("MIG-V12.13-MEASUREMENT-SCHEMA-3-TO-4", planned["steps"])
            self.assertEqual("3", json.loads(path.read_text(encoding="utf-8"))["MEASUREMENT_SCHEMA_VERSION"])

            apply = subprocess.run(
                [sys.executable, str(ROOT / "tools/migrate_rc19_to_rc20.py"),
                 "--config", str(path), "--json"],
                cwd=ROOT, check=True, capture_output=True, text=True,
            )
            result = json.loads(apply.stdout)
            self.assertEqual("migrated", result["status"])
            self.assertEqual("4", json.loads(path.read_text(encoding="utf-8"))["MEASUREMENT_SCHEMA_VERSION"])

            second = subprocess.run(
                [sys.executable, str(ROOT / "tools/migrate_rc19_to_rc20.py"),
                 "--config", str(path), "--check-only", "--json"],
                cwd=ROOT, check=True, capture_output=True, text=True,
            )
            no_op = json.loads(second.stdout)
            self.assertFalse(no_op["changed"])
            self.assertEqual("no_op", no_op["status"])

    def test_legacy_marker_cannot_select_v3_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = base_config(tmp)
            cfg["MEASUREMENT_SCHEMA_VERSION"] = "3"
            logger = CsvRotatingLogger()
            try:
                with patch("csv_logger.measurement_schema_version", return_value="3"):
                    status = logger.log(cfg, base_row())
            finally:
                logger.close()
            self.assertEqual("active", status["measurement_log_status"])
            files = list(Path(tmp).glob("zendure_measurements_v4*.csv"))
            self.assertEqual(1, len(files))
            with files[0].open(encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f, delimiter=";"))
            self.assertEqual("4", rows[0]["schema_version"])

    def test_internal_graph_snapshot_has_no_persistent_schema_identity(self):
        state = ControllerState()
        state.record_graph_point(3)
        row = state.snapshot()["graph_history"][-1]
        self.assertNotIn("schema", row)
        self.assertNotIn("schema_version", row)

    def test_graph_csv_is_explicit_non_measurement_export(self):
        text = rows_to_csv([{"grid_power_w": -25, "mode": "HOLD"}])
        self.assertIn(GRAPH_EXPORT_SCHEMA, text)
        self.assertNotIn(LEGACY_V3_SCHEMA, text)
        self.assertNotIn(MEASUREMENT_SCHEMA_NAME, text)
        row = next(csv.DictReader(io.StringIO(text), delimiter=";"))
        self.assertEqual("ZEC-GRAPH-EXPORT-V1", row["schema"])

    def test_v4_header_contract_is_unchanged_from_v12_12_2(self):
        self.assertEqual(246, len(STANDARD_HEADER))
        self.assertEqual(249, len(EXTENDED_HEADER))
        self.assertEqual("7842bfef39d47f93dc39689aa04da7658564af565e5051c24f90b32021d184a7", hashlib.sha256(";".join(STANDARD_HEADER).encode()).hexdigest())
        self.assertEqual("8f61d07e66428a6e8757333d35d5dd73dd3a0975ac9a16714b93dc9b86460e93", hashlib.sha256(";".join(EXTENDED_HEADER).encode()).hexdigest())

    def test_off_mode_creates_no_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = base_config(tmp, mode="off")
            logger = CsvRotatingLogger()
            try:
                status = logger.log(cfg, base_row())
            finally:
                logger.close()
            self.assertEqual("disabled", status["measurement_log_status"])
            self.assertFalse(list(Path(tmp).glob("*.csv")))

    def test_historical_v3_reader_is_still_available_offline(self):
        content = "schema;date;timestamp;grid_power_w;norm_zendure_soc_percent\n" + f"{LEGACY_V3_SCHEMA};2026-06-15;12:00:00;0;75\n"
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(content)
            path = f.name
        try:
            parsed = read_measurement_csv(path)
            self.assertEqual(1, len(parsed.rows))
            self.assertEqual(LEGACY_V3_SCHEMA, parsed.rows[0]["schema"])
        finally:
            os.remove(path)

    def test_no_productive_python_module_contains_v3_measurement_identity(self):
        forbidden = "ZEC-MEASUREMENT-V3"
        offenders = []
        for path in ROOT.glob("*.py"):
            if forbidden in path.read_text(encoding="utf-8", errors="ignore"):
                offenders.append(path.name)
        self.assertEqual([], offenders)

    def test_no_productive_v3_writer_primitives_remain_in_facade(self):
        source = (ROOT / "csv_logger.py").read_text(encoding="utf-8")
        for obsolete in ("_active_file_schema_error", "_rotate_if_needed", "prepare_row", "_get_writer"):
            self.assertNotIn(f"def {obsolete}", source)
        self.assertIn("MeasurementV4Logger", source)


if __name__ == "__main__":
    unittest.main()
