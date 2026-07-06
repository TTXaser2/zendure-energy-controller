import csv
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import web_ui
import version

ROOT = Path(__file__).resolve().parents[1]


class TestRC16PerformanceEndpoints(unittest.TestCase):
    def test_version_label_rc16(self):
        self.assertEqual(version.APP_VERSION_LABEL, "V12.11.1-RC1")

    def test_tail_reader_avoids_old_rows_for_recent_window(self):
        now = datetime.now().replace(microsecond=0)
        start = now - timedelta(hours=1)
        with tempfile.NamedTemporaryFile("w", delete=False, newline="", encoding="utf-8") as fh:
            path = fh.name
            writer = csv.DictWriter(fh, fieldnames=["datetime_local", "grid_power_w", "norm_zendure_soc_percent", "mode"])
            writer.writeheader()
            for i in range(5000):
                dt = now - timedelta(days=7) + timedelta(minutes=i)
                writer.writerow({"datetime_local": dt.isoformat(sep=" "), "grid_power_w": "1", "norm_zendure_soc_percent": "50", "mode": "AUTO"})
            for i in range(10):
                dt = start + timedelta(minutes=i * 5)
                writer.writerow({"datetime_local": dt.isoformat(sep=" "), "grid_power_w": str(i), "norm_zendure_soc_percent": str(80+i), "mode": "AUTO"})
        try:
            rows = list(web_ui._read_csv_tail_rows(path, start, now, initial_tail_bytes=2048, max_tail_bytes=65536))
            self.assertTrue(rows)
            self.assertGreaterEqual(float(rows[-1]["norm_zendure_soc_percent"]), 80)
            self.assertTrue(any(web_ui._parse_measurement_dt(r) and web_ui._parse_measurement_dt(r) >= start for r in rows))
        finally:
            os.unlink(path)

    def test_soc_day_section_has_timeout_and_cache_status(self):
        html = web_ui.build_modern_soc_day_section({})
        self.assertIn("AbortController", html)
        self.assertIn("SOC-Tageskurve wird noch vorbereitet", html)
        self.assertIn("payload.cache_status", html)

    def test_status_page_refreshes_grid_mini_sparkline_endpoint(self):
        html = web_ui.build_status_page({"UI_DARK_MODE": False}, {"current_mode":"AUTO", "grid_power_valid":True, "graph_history":[{"grid_power": -100},{"grid_power": -50}]})
        self.assertIn("gridMiniSparkline", html)
        self.assertIn("/grid-mini-sparkline", html)

    def test_graph_page_prevents_overlapping_requests_and_has_timeout(self):
        html = web_ui.build_graph_page({"UI_DARK_MODE": False})
        self.assertIn("graphRequestInFlight", html)
        self.assertIn("AbortController", html)
        self.assertIn("Graphdaten werden noch vorbereitet", html)
        self.assertIn("payload.cache_status", html)

    def test_trace_tool_contains_endpoint_timing_checks(self):
        text = (ROOT / "tools" / "collect_zec_trace.sh").read_text(encoding="utf-8")
        self.assertIn("HTTP / ENDPOINT TIMINGS", text)
        self.assertIn("/soc-day-data", text)
        self.assertIn("/graph-view-data?range=24h&resolution=1min", text)
        self.assertIn("time_starttransfer", text)


if __name__ == "__main__":
    unittest.main()
