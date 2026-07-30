import importlib.util
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import measurement_db
import status_page_v2
import version

ROOT = Path(__file__).resolve().parents[1]


class V12112Rc4UiPolishTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual("12.11.2-rc17", version.APP_VERSION)
        self.assertEqual("V12.11.2-RC17", version.APP_VERSION_LABEL)

    def test_status_markup_contains_approved_polish(self):
        payload = {
            "server_time": "12:34:56",
            "system": {"kind": "ok", "label": "System OK", "warnings": []},
            "grid": {"value": "−10 W", "status": "Einspeisung", "source": "SMA", "freshness_text": "aktuell"},
            "mode": {"mode": "AUTO", "text": "Automatik", "target": "0 W", "reason": "Totband", "projection": "", "last_change": "12:30", "status_text": "aktiv"},
            "zendure": {"units": [{"name": "Zendure", "soc": 50}], "soc": 50, "actual": "0 W", "remaining_text": "2,5 kWh", "max_soc_text": "99 %", "source": "MQTT"},
            "primary": {"soc": 60, "actual": "0 W", "status": "Ruhe", "line": "SMA hat Vorrang", "source": "SMA", "freshness_text": "aktuell"},
            "source": {"name": "SMA Energy Meter", "device_line": "korrekt gefiltert", "age_text": "0 s", "packets_text": "120/min", "auto_text": "AUTO nutzt Quelle"},
            "logging": {"status": "aktiv", "target": "SSD", "db": "verfügbar", "db_name": "zec_measurements.sqlite3"},
            "diag": {"mqtt": "OK", "api": "OK", "effect": "OK", "resync": "—", "loop_text": "3 ms", "measurement_logging_text": "aktiv"},
        }
        html = status_page_v2.render_status_page_v2({}, payload, analysis_available=False, analysis_port=8081)
        brand = '<span class="zec-wordmark">ZENDURE</span><span class="zec-product">Energy Controller</span><span class="zec-brand-divider"'
        self.assertIn(brand, html)
        self.assertIn('<details id="expertMenuDetails"', html)
        self.assertIn('id="socDayPickerButton"', html)
        self.assertIn('id="socDayPicker"', html)
        self.assertNotIn('Ganzer Kalendertag 00:00–24:00', html)
        self.assertIn('class="zec-mode-row"', html)
        self.assertIn('data-ring-block="primary"', html)
        self.assertIn('data-zec="primary.caption">SOC aktuell</div>', html)

    def test_frontend_has_dynamic_legend_calendar_and_reason_mapping(self):
        js = (ROOT / "static" / "status_v2.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "status_v2.css").read_text(encoding="utf-8")
        for token in ("Max-SOC", "Nachtreserve", "Min-SOC", "Nachtfenster", "Jetzt"):
            self.assertIn(token, js)
        self.assertIn("fmtReason", js)
        self.assertIn("socDayPicker", js)
        self.assertIn("expertMenuDetails", js)
        self.assertIn("zec-legend-line.is-dashed", css)
        self.assertIn("zec-day-picker-button", css)

    def test_reason_is_persisted_in_raw_and_minute_store(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "zec.sqlite3"
            conn = measurement_db._connect(str(db))
            try:
                point = measurement_db.extract_measurement_point({
                    "measurement_epoch_ms": "1784500000000",
                    "operating_mode": "AUTO_CHARGE",
                    "target_final_reason": "REST_SURPLUS_HARVEST",
                    "zendure_soc_percent": "72",
                    "second_battery_soc_percent": "90",
                    "grid_power_valid": "1",
                })
                self.assertIsNotNone(point)
                measurement_db.write_points(conn, [point])
                raw = conn.execute("SELECT control_reason FROM measurement_raw").fetchone()[0]
                minute = conn.execute("SELECT control_reason_last FROM measurement_1min").fetchone()[0]
                self.assertEqual("REST_SURPLUS_HARVEST", raw)
                self.assertEqual("REST_SURPLUS_HARVEST", minute)
            finally:
                conn.close()
            cfg = {"MEASUREMENT_DB_ENABLED": True, "MEASUREMENT_DB_PATH": str(db)}
            start = datetime.fromtimestamp(1784500000) - timedelta(minutes=1)
            end = start + timedelta(minutes=3)
            points, meta = measurement_db.query_graph_points(cfg, start, end)
            self.assertEqual("hit", meta["db_status"])
            self.assertEqual("REST_SURPLUS_HARVEST", points[0]["control_reason"])
            available = measurement_db.query_measurement_date_range(cfg)
            self.assertTrue(available["available_from"])
            self.assertTrue(available["available_to"])

    def test_reason_backfill_is_idempotent_and_tolerates_nul(self):
        module_path = ROOT / "tools" / "backfill_measurement_reasons.py"
        spec = importlib.util.spec_from_file_location("reason_backfill", module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "zec.sqlite3"
            conn = measurement_db._connect(str(db))
            try:
                point = measurement_db.extract_measurement_point({
                    "measurement_epoch_ms": "1784500000000",
                    "operating_mode": "AUTO_CHARGE",
                    "zendure_soc_percent": "72",
                    "grid_power_valid": "1",
                })
                measurement_db.write_points(conn, [point])
            finally:
                conn.close()
            csv_path = Path(td) / "zendure_measurements_v4_test.csv"
            csv_path.write_bytes(
                b"schema_version;measurement_epoch_ms;operating_mode;target_final_reason;zendure_soc_percent;grid_power_valid\n"
                b"4;1784500000000;AUTO_CHARGE;REST_SURPLUS_\x00HARVEST;72;1\n"
            )
            conn = sqlite3.connect(str(db))
            measurement_db.ensure_schema(conn)
            stats = module.run_backfill(conn, [csv_path], 0)
            self.assertEqual(1, stats["updated"])
            reason = conn.execute("SELECT control_reason_last FROM measurement_1min").fetchone()[0]
            self.assertEqual("REST_SURPLUS_HARVEST", reason)
            stats2 = module.run_backfill(conn, [csv_path], 0)
            self.assertEqual(0, stats2["updated"])
            self.assertEqual(1, stats2["already_complete"])
            conn.close()


if __name__ == "__main__":
    unittest.main()
