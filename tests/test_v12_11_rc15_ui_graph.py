import unittest
from datetime import datetime, timedelta

import web_ui
import version


class TestRC15UiGraphPolish(unittest.TestCase):
    def test_version_label_rc15(self):
        self.assertEqual(version.APP_VERSION_LABEL, "V14.1.3")

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

    def test_greenfield_graph_has_true_24h_and_48h_range_controls(self):
        from pathlib import Path
        html = web_ui.build_graph_page({"UI_DARK_MODE": False})
        js = Path(web_ui.__file__).resolve().parent.joinpath("static/graph_v14_1.js").read_text(encoding="utf-8")
        self.assertIn('data-gf-preset="24h"', html)
        self.assertIn('data-gf-preset="48h"', html)
        self.assertIn("MAX_WINDOW_MS = 48 * 60 * 60 * 1000", js)

    def test_graph_page_uses_v3_linear_axis_and_48h_range_guard(self):
        from pathlib import Path
        html = web_ui.build_graph_page({"UI_DARK_MODE": False})
        js = Path(web_ui.__file__).resolve().parent.joinpath("static/graph_v14_1.js").read_text(encoding="utf-8")
        self.assertIn("interaction:{mode:'nearest',intersect:false}", js)
        self.assertIn("type:'linear'", js)
        self.assertIn("MAX_WINDOW_MS = 48 * 60 * 60 * 1000", js)
        self.assertIn("Analyse-Workspace", html)


if __name__ == "__main__":
    unittest.main()
