import unittest
from datetime import datetime, timedelta

import web_ui
import version


class TestRC15UiGraphPolish(unittest.TestCase):
    def test_version_label_rc15(self):
        self.assertEqual(version.APP_VERSION_LABEL, "V12.11.2-RC3")

    def test_zendure_mqtt_warning_is_card_local_not_global_strip(self):
        cfg = {"UI_DARK_MODE": False, "NIGHT_DISCHARGE_ENABLED": False}
        snap = {"current_mode":"HOLD", "raw_grid_power":-40, "grid_power_valid":True, "battery_soc":100, "zendure_mqtt_overall_status":"ZENDURE_MQTT_RETAINED_ONLY", "zendure_mqtt_live_confirmed":False, "measurement_log_status":"active"}
        html = web_ui.build_status_page(cfg, snap)
        self.assertIn('class="zec-storage-layout', html)
        self.assertIn('class="zec-soc-ring', html)
        self.assertIn('data-zec="zendure.command_warning"', html)
        self.assertIn('Zendure Live-Status', html)
        self.assertIn('Zendure-App', html)
        self.assertNotIn('zec-alert-strip', html)

    def test_status_soc_chart_tooltip_uses_x_axis_non_intersect(self):
        html = web_ui.build_modern_soc_day_section({})
        self.assertIn("interaction:{mode:'nearest', axis:'x', intersect:false}", html)
        self.assertIn("tooltip:{mode:'nearest', intersect:false", html)
        self.assertIn("pointHitRadius:18", html)

    def test_graph_payload_last_24h_axis_is_full_24_hours(self):
        now = datetime.now()
        rows = []
        for delta_min, soc in [(70, 80), (40, 82), (10, 84)]:
            dt = now - timedelta(minutes=delta_min)
            rows.append({"date": dt.date().isoformat(), "timestamp": dt.strftime("%H:%M:%S"), "grid_power": -100, "soc": soc})
        payload = web_ui.build_graph_view_payload({}, {"graph_history": rows}, range_name="24h", resolution="1min")
        r = payload["range"]
        self.assertEqual(r["name"], "24h")
        self.assertAlmostEqual(r["axis_duration_hours"], 24.0, places=2)
        self.assertIn("–", r["label"])

    def test_graph_page_uses_x_axis_tooltip_and_range_label(self):
        html = web_ui.build_graph_page({"UI_DARK_MODE": False})
        self.assertIn("interaction:{mode:'index', axis:'x', intersect:false}", html)
        self.assertIn("tooltip:{mode:'index', intersect:false", html)
        self.assertIn("rangeText = r.label", html)
        self.assertIn("axis_duration_hours", web_ui.build_graph_view_payload({}, {}, range_name="24h")["range"])


if __name__ == "__main__":
    unittest.main()
