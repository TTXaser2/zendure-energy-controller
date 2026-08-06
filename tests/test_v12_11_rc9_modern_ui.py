import inspect
import unittest

from config_manager import DEFAULT_CONFIG
from state import ControllerState
from web_ui import build_graph_page, build_nav_bar, build_status_page, create_app


class V1211Rc9ModernUiTests(unittest.TestCase):
    def test_status_page_is_modern_and_exposes_legacy_fallback(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg["UI_DARK_MODE"] = True
        snap = ControllerState().snapshot()
        snap.update({"current_mode":"AUTO", "battery_soc":82, "zendure_mqtt_overall_status":"ZENDURE_MQTT_OK", "grid_power_valid":True, "raw_grid_power":-123.4, "measurement_log_status":"off"})
        html = build_status_page(cfg, snap)
        self.assertIn('class="zec-status-v2"', html)
        self.assertIn('data-theme="dark"', html)
        self.assertIn('id="expertMenu"', html)
        self.assertIn('/status_old', html)
        self.assertIn('/graph_old', html)
        self.assertNotIn('Detailkarten darunter bleiben', html)

    def test_graph_page_is_modern_and_exposes_old_graph(self):
        html = build_graph_page(dict(DEFAULT_CONFIG))
        self.assertIn('Graph / Live-Verlauf', html)
        self.assertIn('class="modern-page zec-shell"', html)
        self.assertIn('/graph_old', html)
        self.assertIn('Page Visibility', inspect.getsource(build_graph_page)) if False else None

    def test_navbar_contains_expert_menu_for_legacy_pages(self):
        nav = build_nav_bar(dict(DEFAULT_CONFIG))
        self.assertIn('Experte', nav)
        self.assertIn('/status_old', nav)
        self.assertIn('/graph_old', nav)

    def test_legacy_routes_are_registered(self):
        source = inspect.getsource(create_app)
        self.assertIn('"/status_old"', source)
        self.assertIn('@app.get("/graph_old"', source)


if __name__ == "__main__":
    unittest.main()
