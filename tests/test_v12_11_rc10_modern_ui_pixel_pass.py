import unittest

from config_manager import DEFAULT_CONFIG
from state import ControllerState
from web_ui import build_graph_page, build_status_page


class V1211Rc10ModernUiPixelPassTests(unittest.TestCase):
    def test_status_page_uses_mockup_style_shell_and_hides_legacy_nav(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg["UI_DARK_MODE"] = False
        snap = ControllerState().snapshot()
        snap.update({"current_mode":"AUTO", "battery_soc":82, "zendure_mqtt_overall_status":"ZENDURE_MQTT_OK", "grid_power_valid":True, "raw_grid_power":-123.4, "measurement_log_status":"off"})
        html = build_status_page(cfg, snap)
        self.assertIn('class="zec-status-v2"', html)
        self.assertIn('class="zec-topbar"', html)
        self.assertIn('ZENDURE', html)
        self.assertIn('class="zec-main-grid"', html)
        self.assertIn('id="expertMenu"', html)
        self.assertNotIn('<div class="nav">', html)

    def test_graph_page_uses_mockup_style_dashboard_components(self):
        html = build_graph_page(dict(DEFAULT_CONFIG))
        self.assertIn("zec-modern-body", html)
        self.assertIn("zec-chart-card", html)
        self.assertIn("zec-kpi-strip", html)
        self.assertIn("Aktive Signale / Quellen", html)
        self.assertIn("/graph_old", html)


if __name__ == "__main__":
    unittest.main()
