import unittest

import web_ui


class TestRC12UiPolish(unittest.TestCase):
    def test_status_page_uses_generic_grid_source_and_no_fake_cpu_sparkline(self):
        cfg = {"UI_DARK_MODE": False, "NIGHT_DISCHARGE_ENABLED": True, "NIGHT_START_HOUR": 21, "NIGHT_START_MINUTE": 30, "NIGHT_END_HOUR": 5, "NIGHT_END_MINUTE": 30, "NIGHT_DISCHARGE_POWER_W": 400}
        snap = {"current_mode":"NIGHT_DISCHARGE", "raw_grid_power":-10, "grid_power_valid":True, "battery_soc":70, "zendure_mqtt_overall_status":"ZENDURE_MQTT_OK", "measurement_log_status":"off"}
        html = web_ui.build_status_page(cfg, snap)
        self.assertIn("Netzleistungsquelle", html)
        self.assertIn('data-zec="mode.projection"', html)
        self.assertIn('id="gridMiniChart"', html)
        self.assertNotIn("SMA Direktquelle", html)
        self.assertNotIn("CPU-Sparkline", html)

    def test_graph_page_contains_state_timeline_and_linear_time_axis(self):
        root = __import__('pathlib').Path(web_ui.__file__).resolve().parent
        html = web_ui.build_graph_page({})
        js = (root / "static" / "graph_v14_1.js").read_text(encoding="utf-8")
        self.assertIn('id="gfStateTimeline"', html)
        self.assertIn("type:'linear'", js)
        self.assertIn("OPERATING_MODE", js)
        self.assertIn("CONTROL_INTENT", js)
        self.assertIn("CONTROL_REASON", js)
        self.assertNotIn("/graph-view-data", js)


if __name__ == "__main__":
    unittest.main()
