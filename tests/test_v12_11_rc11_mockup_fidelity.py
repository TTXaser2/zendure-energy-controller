import unittest

from config_manager import DEFAULT_CONFIG
from state import ControllerState
from web_ui import build_graph_page, build_status_page


class V1211Rc11MockupFidelityTests(unittest.TestCase):
    def test_status_page_uses_light_mockup_layout_when_dark_mode_off(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg["UI_DARK_MODE"] = False
        snap = ControllerState().snapshot()
        snap.update({"current_mode":"AUTO_CHARGE", "battery_soc":78, "zendure_mqtt_overall_status":"ZENDURE_MQTT_OK", "grid_power_valid":True, "raw_grid_power":-2480.0, "measurement_log_status":"active"})
        html = build_status_page(cfg, snap)
        self.assertIn('data-theme="light"', html)
        self.assertIn('class="zec-main-grid"', html)
        self.assertIn('Zendure / Batterie', html)
        self.assertIn('class="zec-soc-ring', html)
        self.assertIn('class="zec-lower-grid"', html)
        self.assertIn('Systemressourcen', html)
        self.assertIn('Controller &amp; Schnittstellen', html)
        self.assertIn('Betriebsereignisse', html)
        self.assertNotIn('Aktuelle Energieflüsse', html)

    def test_graph_page_keeps_dark_graph_mockup_shell(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg["UI_DARK_MODE"] = False
        html = build_graph_page(cfg)
        self.assertIn("modern-dark", html)
        self.assertIn("zec-chart-card", html)
        self.assertIn("Graph-Verlauf CSV", html)


if __name__ == "__main__":
    unittest.main()
