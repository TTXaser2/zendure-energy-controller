import unittest

from config_manager import DEFAULT_CONFIG
from state import ControllerState
from web_ui import build_graph_page, build_status_page


class V1211Rc11MockupFidelityTests(unittest.TestCase):
    def test_status_page_uses_light_mockup_layout_when_dark_mode_off(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg["UI_DARK_MODE"] = False
        snap = ControllerState().snapshot()
        snap.update({
            "current_mode": "AUTO_CHARGE",
            "battery_soc": 78,
            "mqtt_connected": True,
            "zendure_mqtt_overall_status": "ZENDURE_MQTT_OK",
            "grid_power_valid": True,
            "raw_grid_power": -2480.0,
            "grid_power_used_for_control": True,
            "measurement_log_status": "active",
            "measurement_log_mode": "standard",
        })
        html = build_status_page(cfg, snap)
        self.assertIn("modern-light", html)
        self.assertIn("mockup-top-card", html)
        self.assertIn("Zendure (Batterie)", html)
        self.assertIn("soc-ring", html)
        self.assertIn("mockup-footer-grid", html)
        self.assertIn("Systemlaufzeit", html)
        self.assertNotIn("Aktuelle Energieflüsse", html)

    def test_graph_page_keeps_dark_graph_mockup_shell(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg["UI_DARK_MODE"] = False
        html = build_graph_page(cfg)
        self.assertIn("modern-dark", html)
        self.assertIn("zec-chart-card", html)
        self.assertIn("Graph-Verlauf CSV", html)


if __name__ == "__main__":
    unittest.main()
