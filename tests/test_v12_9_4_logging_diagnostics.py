# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.

import csv
import inspect
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from csv_logger import CSV_FIELDS, CsvRotatingLogger, resolve_log_target
from web_ui import build_status_page


class V1294LoggingDiagnosticsTests(unittest.TestCase):
    def test_usb_runtime_diagnostics_are_not_added_to_measurement_schema(self):
        forbidden_fields = {
            "measurement_primary_path",
            "measurement_primary_mountpoint",
            "measurement_primary_exists",
            "measurement_primary_is_mount",
            "measurement_primary_writable",
            "measurement_primary_free_mb",
            "measurement_primary_failure_reason",
            "measurement_primary_exception",
            "measurement_fallback_count_since_start",
            "measurement_last_fallback_time",
            "measurement_last_fallback_reason",
        }
        self.assertTrue(forbidden_fields.isdisjoint(set(CSV_FIELDS)))

    def test_fallback_diagnostics_are_returned_for_runtime_log_and_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
                "MEASUREMENT_LOG_STORAGE_TARGET": "external_mount",
                "MEASUREMENT_LOG_MOUNTPOINT": "/not/a/mount",
                "MEASUREMENT_LOG_DIR": "ZEC/logs",
                "MEASUREMENT_LOG_FILE": "zendure_measurements.csv",
                "MEASUREMENT_LOG_ALLOW_SD_FALLBACK": True,
                "MEASUREMENT_LOG_FALLBACK_DIR": str(Path(tmp) / "fallback"),
            }
            with patch("csv_logger.detected_log_mounts", return_value=[]):
                target = resolve_log_target(cfg, allow_fallback=True)
        self.assertTrue(target["fallback_active"])
        self.assertEqual(target["active_target_type"], "fallback_sd")
        self.assertEqual(target["primary_failure_reason"], "external_mount_unavailable")
        self.assertIn("fallback_sd_active", target["status_reason"])

    def test_fallback_event_is_counted_once_until_state_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            fallback_dir = Path(tmp) / "fallback"
            cfg = {
                "MEASUREMENT_LOG_MODE": "standard",
                "MEASUREMENT_LOG_STORAGE_TARGET": "external_mount",
                "MEASUREMENT_LOG_MOUNTPOINT": "/not/a/mount",
                "MEASUREMENT_LOG_DIR": "ZEC/logs",
                "MEASUREMENT_LOG_FILE": "zendure_measurements.csv",
                "MEASUREMENT_LOG_ALLOW_SD_FALLBACK": True,
                "MEASUREMENT_LOG_FALLBACK_DIR": str(fallback_dir),
                "MEASUREMENT_LOG_FALLBACK_MAX_BYTES": 1000000,
                "MEASUREMENT_LOG_FALLBACK_BACKUP_COUNT": 2,
                "MEASUREMENT_LOG_MIN_FREE_DISK_MB": 1,
            }
            logger = CsvRotatingLogger()
            try:
                with patch("csv_logger.detected_log_mounts", return_value=[]):
                    first = logger.log(cfg, {"datetime_local": "t1", "epoch": 1, "grid_power_w": 0})
                    second = logger.log(cfg, {"datetime_local": "t2", "epoch": 2, "grid_power_w": 0})
            finally:
                logger.close()
        self.assertTrue(first["measurement_fallback_event"])
        self.assertFalse(second["measurement_fallback_event"])
        self.assertEqual(first["measurement_fallback_count_since_start"], 1)
        self.assertEqual(second["measurement_fallback_count_since_start"], 1)

    def test_controller_runtime_log_formatter_contains_primary_failure_details(self):
        from pathlib import Path as _Path
        source = _Path("controller_logic.py").read_text(encoding="utf-8")
        self.assertIn("fallback_to_sd", source)
        self.assertIn("measurement_primary_failure_reason", source)
        self.assertIn("measurement_primary_exception", source)


    def test_status_page_source_no_longer_shows_schema_line_in_logging_card(self):
        source = inspect.getsource(build_status_page)
        self.assertNotIn("Schema: {CSV_SCHEMA}", source)
        self.assertIn("measurement_log_details", source)


if __name__ == "__main__":
    unittest.main()
