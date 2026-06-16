import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config_validator import validate_config_semantics
from csv_logger import CsvRotatingLogger, resolve_log_path


class V1293UsbLoggingTests(unittest.TestCase):
    def test_external_auto_mount_uses_configured_subdir_variant_a(self):
        with tempfile.TemporaryDirectory() as tmp:
            mount = Path(tmp) / "USB"
            mount.mkdir()
            cfg = {
                "MEASUREMENT_LOG_STORAGE_TARGET": "external_mount",
                "MEASUREMENT_LOG_MOUNTPOINT": "",
                "MEASUREMENT_LOG_DIR": "ZEC/logs",
                "MEASUREMENT_LOG_FILE": "zendure_measurements.csv",
                "MEASUREMENT_LOG_ALLOW_SD_FALLBACK": True,
                "MEASUREMENT_LOG_FALLBACK_DIR": str(Path(tmp) / "fallback"),
            }
            with patch("csv_logger.detected_log_mounts", return_value=[{"mountpoint": str(mount), "writable": True, "free_mb": 1000}]):
                path, fallback, reason = resolve_log_path(cfg, allow_fallback=True)
            self.assertFalse(fallback)
            self.assertIn("external_auto", reason)
            self.assertEqual(path, str(mount / "ZEC" / "logs" / "zendure_measurements.csv"))

    def test_validation_accepts_empty_mountpoint_when_auto_mount_is_writable(self):
        with tempfile.TemporaryDirectory() as tmp:
            mount = Path(tmp) / "USB"
            mount.mkdir()
            cfg = {
                "MEASUREMENT_LOG_MODE": "standard",
                "MEASUREMENT_LOG_STORAGE_TARGET": "external_mount",
                "MEASUREMENT_LOG_MOUNTPOINT": "",
                "MEASUREMENT_LOG_DIR": "ZEC/logs",
                "MEASUREMENT_LOG_FILE": "zendure_measurements.csv",
                "MEASUREMENT_LOG_ALLOW_SD_FALLBACK": True,
                "MEASUREMENT_LOG_FALLBACK_DIR": str(Path(tmp) / "fallback"),
            }
            with patch("config_validator._detected_writable_external_mountpoint", return_value=str(mount)):
                issues = validate_config_semantics(cfg, base_dir=tmp)
            codes = {issue.code for issue in issues}
            self.assertNotIn("MEASUREMENT_LOG_EXTERNAL_FALLBACK", codes)
            self.assertNotIn("MEASUREMENT_LOG_TARGET_UNAVAILABLE", codes)

    def test_fallback_row_status_matches_actual_fallback_file(self):
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
            with patch("csv_logger.detected_log_mounts", return_value=[]):
                logger = CsvRotatingLogger()
                try:
                    status = logger.log(cfg, {"datetime_local": "t", "epoch": 1, "grid_power_w": 0})
                finally:
                    logger.close()
            self.assertEqual(status["measurement_log_status"], "active_fallback_sd")
            with (fallback_dir / "zendure_measurements.csv").open(encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f, delimiter=";"))
            self.assertEqual(rows[0]["measurement_log_status"], "active_fallback_sd")
            self.assertIn("SD-Fallback aktiv", rows[0]["measurement_log_status_reason"])

    def test_usb_row_overrides_stale_previous_fallback_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            mount = Path(tmp) / "USB"
            mount.mkdir()
            cfg = {
                "MEASUREMENT_LOG_MODE": "standard",
                "MEASUREMENT_LOG_STORAGE_TARGET": "external_mount",
                "MEASUREMENT_LOG_MOUNTPOINT": str(mount),
                "MEASUREMENT_LOG_DIR": "ZEC/logs",
                "MEASUREMENT_LOG_FILE": "zendure_measurements.csv",
                "MEASUREMENT_LOG_ALLOW_SD_FALLBACK": True,
                "MEASUREMENT_LOG_FALLBACK_DIR": str(Path(tmp) / "fallback"),
                "MEASUREMENT_LOG_MAX_BYTES": 1000000,
                "MEASUREMENT_LOG_BACKUP_COUNT": 2,
                "MEASUREMENT_LOG_MIN_FREE_DISK_MB": 1,
            }
            logger = CsvRotatingLogger()
            try:
                with patch("csv_logger._is_mountpoint", return_value=True):
                    status = logger.log(cfg, {
                        "datetime_local": "t",
                        "epoch": 1,
                        "grid_power_w": 0,
                        "measurement_log_status": "active_fallback_sd",
                        "measurement_log_status_reason": "stale previous state",
                    })
            finally:
                logger.close()
            self.assertEqual(status["measurement_log_status"], "active")
            usb_file = mount / "ZEC" / "logs" / "zendure_measurements.csv"
            self.assertTrue(usb_file.exists())
            self.assertFalse((Path(tmp) / "fallback" / "zendure_measurements.csv").exists())
            with usb_file.open(encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f, delimiter=";"))
            self.assertEqual(rows[0]["measurement_log_status"], "active")
            self.assertEqual(rows[0]["measurement_log_status_reason"], "OK")


if __name__ == "__main__":
    unittest.main()
