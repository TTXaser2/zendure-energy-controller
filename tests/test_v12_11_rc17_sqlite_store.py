import os
import tempfile
import time
import unittest
from datetime import datetime, timedelta

import version
from csv_logger import CsvRotatingLogger
from measurement_db import query_graph_points, resolve_measurement_db_path
from web_ui import build_graph_view_payload, build_status_page


class TestRC17SqliteGraphStore(unittest.TestCase):
    def test_version_label_rc17(self):
        self.assertEqual(version.APP_VERSION_LABEL, "V12.12.0")

    def test_db_writes_even_when_csv_logging_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
                "MEASUREMENT_LOG_MODE": "off",
                "MEASUREMENT_SCHEMA_VERSION": "3",
                "MEASUREMENT_LOG_DIR": tmp,
                "MEASUREMENT_DB_ENABLED": True,
                "MEASUREMENT_DB_FILE": "test.sqlite3",
                "INTERVAL_SECONDS": 3,
            }
            logger = CsvRotatingLogger()
            row = {
                "date": "2026-07-03",
                "timestamp": "12:00:00",
                "datetime_local": "2026-07-03 12:00:00",
                "epoch_s": datetime(2026, 7, 3, 12, 0, 0).timestamp(),
                "grid_power_w": -123.0,
                "zendure_target_power_w": 100.0,
                "zendure_actual_power_w": 95.0,
                "zendure_soc_percent": 77.0,
                "soc_valid": True,
                "mode": "AUTO_CHARGE",
            }
            status = logger.log(cfg, row)
            self.assertIn("measurement_db_status", status)
            logger.close()
            self.assertTrue(os.path.exists(resolve_measurement_db_path(cfg)))
            points, meta = query_graph_points(cfg, datetime(2026, 7, 3, 11, 59), datetime(2026, 7, 3, 12, 1))
            self.assertEqual(meta.get("db_status"), "hit")
            self.assertEqual(len(points), 1)
            self.assertEqual(points[0]["soc"], 77.0)

    def test_graph_payload_prefers_sqlite_db_when_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            now = datetime.now()
            cfg = {
                "MEASUREMENT_LOG_MODE": "off",
                "MEASUREMENT_SCHEMA_VERSION": "3",
                "MEASUREMENT_LOG_DIR": tmp,
                "MEASUREMENT_DB_ENABLED": True,
                "MEASUREMENT_DB_FILE": "test.sqlite3",
            }
            logger = CsvRotatingLogger()
            logger.log(cfg, {
                "datetime_local": now.strftime("%Y-%m-%d %H:%M:%S"),
                "epoch_s": now.timestamp(),
                "grid_power_w": -42,
                "zendure_soc_percent": 66,
                "soc_valid": True,
                "mode": "AUTO_CHARGE",
            })
            logger.close()
            payload = build_graph_view_payload(cfg, {"graph_history": []}, range_name="24h", resolution="1min")
            self.assertEqual(payload["source"], "measurement_db_1min")
            self.assertEqual(payload["cache_status"], "db_hit")
            self.assertGreaterEqual(len(payload["points"]), 1)

    def test_status_page_mentions_sqlite_store(self):
        cfg = {"MEASUREMENT_LOG_MODE": "off", "MEASUREMENT_DB_ENABLED": True, "MEASUREMENT_LOG_DIR": "logs"}
        snap = {
            "current_mode": "AUTO_CHARGE",
            "raw_grid_power": -1,
            "grid_power": -1,
            "grid_power_valid": True,
            "mqtt_connected": True,
            "zendure_mqtt_overall_status": "ZENDURE_MQTT_OK",
            "measurement_log_status": "disabled",
            "measurement_db_status": "active",
            "battery_soc": 80,
            "zendure_system_signed_power": 0,
            "last_input_power": 0,
            "last_output_power": 0,
            "graph_history": [],
        }
        html = build_status_page(cfg, snap)
        self.assertIn("SQLite-Graphspeicher", html)
        self.assertIn("DB-Datei", html)
