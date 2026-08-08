import csv
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import version
from measurement_db import query_graph_points
from tools.import_measurements_to_db import import_files


class TestRC18MeasurementDbImportTool(unittest.TestCase):
    def test_version_label_rc18(self):
        self.assertEqual(version.APP_VERSION_LABEL, "V12.11.7")

    def test_import_tool_imports_existing_measurement_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            csv_path = tmp_path / "zendure_measurements_v4.csv"
            db_path = tmp_path / "zec_measurements.sqlite3"
            with csv_path.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=[
                    "schema", "schema_version", "date", "timestamp", "datetime_local", "epoch_s",
                    "grid_power_w", "zendure_target_power_w", "zendure_actual_power_w",
                    "zendure_soc_percent", "soc_valid", "grid_power_valid", "mode", "raw_grid_source",
                ], delimiter=";")
                writer.writeheader()
                for minute, soc in [(0, 70.0), (1, 71.0), (2, 72.0)]:
                    dt = datetime(2026, 7, 3, 12, minute, 0)
                    writer.writerow({
                        "schema": "ZEC-MEASUREMENT-V4",
                        "schema_version": "4",
                        "date": "2026-07-03",
                        "timestamp": f"12:{minute:02d}:00",
                        "datetime_local": dt.strftime("%Y-%m-%d %H:%M:%S"),
                        "epoch_s": dt.timestamp(),
                        "grid_power_w": -100 + minute,
                        "zendure_target_power_w": 400,
                        "zendure_actual_power_w": 390,
                        "zendure_soc_percent": soc,
                        "soc_valid": "1",
                        "grid_power_valid": "1",
                        "mode": "AUTO_CHARGE",
                        "raw_grid_source": "test",
                    })
            summary = import_files([csv_path], db_path, batch_size=2)
            self.assertEqual(summary["rows_seen"], 3)
            self.assertEqual(summary["rows_imported"], 3)
            self.assertTrue(db_path.exists())
            conn = sqlite3.connect(db_path)
            raw_count = conn.execute("SELECT COUNT(*) FROM measurement_raw").fetchone()[0]
            agg_count = conn.execute("SELECT COUNT(*) FROM measurement_1min").fetchone()[0]
            conn.close()
            self.assertEqual(raw_count, 3)
            self.assertEqual(agg_count, 3)
            cfg = {"MEASUREMENT_DB_ENABLED": True, "MEASUREMENT_DB_PATH": str(db_path)}
            points, meta = query_graph_points(cfg, datetime(2026, 7, 3, 11, 59), datetime(2026, 7, 3, 12, 3))
            self.assertEqual(meta["db_status"], "hit")
            self.assertEqual(len(points), 3)
            self.assertEqual(points[-1]["soc"], 72.0)

    def test_import_tool_cli_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            csv_path = tmp_path / "minimal.csv"
            csv_path.write_text(
                "schema;schema_version;datetime_local;grid_power_w;zendure_soc_percent;soc_valid;mode\n"
                "ZEC-MEASUREMENT-V4;4;2026-07-03 12:00:00;-10;80;1;AUTO_CHARGE\n",
                encoding="utf-8",
            )
            db_path = tmp_path / "dry.sqlite3"
            script = Path(__file__).resolve().parents[1] / "tools" / "import_measurements_to_db.py"
            result = subprocess.run(
                [sys.executable, str(script), "--db-path", str(db_path), "--dry-run", str(csv_path)],
                cwd=str(Path(__file__).resolve().parents[1]),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=20,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("rows_imported: 1", result.stdout)
            self.assertFalse(db_path.exists())


if __name__ == "__main__":
    unittest.main()
