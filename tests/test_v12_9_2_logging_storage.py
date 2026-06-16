import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from csv_logger import CsvRotatingLogger, detected_log_mounts, resolve_log_path, rows_to_csv
from tools.replay_core import analyze_file
from tools.replay_web import selection_profile


class V1292LoggingStorageTests(unittest.TestCase):
    def test_bool_values_are_written_as_1_0_and_v3_soc_is_read(self):
        csv_text = rows_to_csv([
            {
                "datetime_local": "2026-06-16 10:00:00",
                "epoch": 1,
                "dt_s": 3,
                "grid_power_w": 0,
                "norm_zendure_soc_percent": 75,
                "soc_available": True,
                "soc_fresh": True,
                "soc_valid": True,
                "zendure_actual_power_w": 0,
                "mode": "AUTO_DISCHARGE",
            }
        ])
        self.assertIn(";1;", csv_text)
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(csv_text)
            name = f.name
        try:
            result = analyze_file(name)
            self.assertEqual(result["data_quality"]["missing_soc_rows"], 0)
        finally:
            os.remove(name)

    def test_external_mount_falls_back_to_limited_sd_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
                "MEASUREMENT_LOG_STORAGE_TARGET": "external_mount",
                "MEASUREMENT_LOG_MOUNTPOINT": "/definitely/not/a/mount",
                "MEASUREMENT_LOG_ALLOW_SD_FALLBACK": True,
                "MEASUREMENT_LOG_FALLBACK_DIR": str(Path(tmp) / "fallback"),
                "MEASUREMENT_LOG_FILE": "zendure_measurements.csv",
            }
            path, fallback, reason = resolve_log_path(cfg, allow_fallback=True)
            self.assertTrue(fallback)
            self.assertIn("fallback", path)
            self.assertIn("fallback_sd_active", reason)

    def test_logger_uses_buffered_file_handle_and_flushes_by_row_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
                "MEASUREMENT_LOG_MODE": "standard",
                "MEASUREMENT_LOG_DIR": tmp,
                "MEASUREMENT_LOG_FILE": "m.csv",
                "MEASUREMENT_LOG_MAX_BYTES": 1000000,
                "MEASUREMENT_LOG_BACKUP_COUNT": 2,
                "MEASUREMENT_LOG_MIN_FREE_DISK_MB": 1,
                "MEASUREMENT_LOG_FLUSH_EVERY_ROWS": 2,
                "MEASUREMENT_LOG_FLUSH_EVERY_SECONDS": 999,
            }
            logger = CsvRotatingLogger()
            try:
                logger.log(cfg, {"datetime_local": "t1", "epoch": 1, "grid_power_w": 0, "norm_zendure_soc_percent": 75})
                self.assertIsNotNone(logger._fh)
                logger.log(cfg, {"datetime_local": "t2", "epoch": 2, "grid_power_w": 0, "norm_zendure_soc_percent": 75})
                self.assertEqual(logger._rows_since_flush, 0)
            finally:
                logger.close()

    def test_small_selection_is_allowed_even_when_memavailable_is_tight(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.csv"
            path.write_text(rows_to_csv([{"datetime_local": "2026-06-16 10:00:00", "epoch": 1, "dt_s": 3, "grid_power_w": 0, "norm_zendure_soc_percent": 75}]), encoding="utf-8")
            with patch("tools.replay_web._meminfo_available_mb", return_value=120):
                profile = selection_profile([path], {})
            self.assertFalse(profile["rejected"])
            self.assertEqual(profile["risk"], "pi-safe")


if __name__ == "__main__":
    unittest.main()
