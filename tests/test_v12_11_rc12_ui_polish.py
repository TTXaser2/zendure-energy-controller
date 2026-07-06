import unittest

import web_ui


class TestRC12UiPolish(unittest.TestCase):
    def test_status_page_uses_generic_grid_source_and_no_fake_cpu_sparkline(self):
        cfg = {"UI_DARK_MODE": False, "NIGHT_DISCHARGE_ENABLED": True, "NIGHT_START_HOUR": 21, "NIGHT_START_MINUTE": 30, "NIGHT_END_HOUR": 5, "NIGHT_END_MINUTE": 30, "NIGHT_DISCHARGE_POWER_W": 400}
        snap = {"current_mode": "NIGHT_DISCHARGE", "raw_grid_power": -10, "grid_power_valid": True, "battery_soc": 70, "mqtt_connected": True, "zendure_mqtt_overall_status": "ZENDURE_MQTT_OK", "measurement_log_status": "off", "graph_history": []}
        html = web_ui.build_status_page(cfg, snap)
        self.assertIn("Netzleistungsquelle", html)
        self.assertIn("zec-mode-context", html)
        self.assertIn("keine Verlaufshistorie verfügbar", html)
        self.assertNotIn("SMA Direktquelle", html)

    def test_graph_page_contains_scrollable_events_and_linear_time_axis(self):
        html = web_ui.build_graph_page({})
        self.assertIn("#eventBox", html)
        with open(web_ui.__file__, encoding="utf-8") as src:
            self.assertIn("overflow-y: auto", src.read())
        self.assertIn("axis_start_epoch_ms", html)
        self.assertIn("type:'linear'", html)
        self.assertNotIn("Netz Rohwert','grid_power_raw_w", html)


if __name__ == "__main__":
    unittest.main()
