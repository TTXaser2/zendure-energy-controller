import unittest

from config_manager import DEFAULT_CONFIG
from state import ControllerState
from web_ui import build_mqtt_diagnostics_page, build_restart_service_page, status_url_after_restart


class DummyUrl:
    scheme = "http"
    hostname = "192.168.0.40"


class DummyRequest:
    url = DummyUrl()


class V12812UiFixTests(unittest.TestCase):
    def test_mqtt_diagnostic_page_contains_clear_button(self):
        cfg = dict(DEFAULT_CONFIG)
        html = build_mqtt_diagnostics_page(cfg, [{"topic": "evcc/site/battery", "payload": "123"}])
        self.assertIn("/mqtt-diagnostics/clear", html)
        self.assertIn("Diagnosetabelle leeren", html)
        self.assertIn("MQTT-Diagnosetabelle wirklich leeren", html)

    def test_mqtt_diagnostic_clear_removes_existing_rows_and_allows_new_rows(self):
        state = ControllerState()
        state.add_mqtt_diagnostic("evcc/site/battery", "123", diagnostic_filter="evcc/#", diagnostic_filter_matched=True)
        state.add_mqtt_diagnostic("evcc/site/grid", "456", diagnostic_filter="evcc/#", diagnostic_filter_matched=True)

        removed = state.clear_mqtt_diagnostics()

        self.assertEqual(removed, 2)
        self.assertEqual(state.snapshot()["mqtt_topic_diagnostics"], [])

        state.add_mqtt_diagnostic("evcc/site/battery", "789", diagnostic_filter="evcc/#", diagnostic_filter_matched=True)
        rows = state.snapshot()["mqtt_topic_diagnostics"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["payload"], "789")

    def test_restart_redirect_targets_main_page_not_status_path(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg["WEB_PORT"] = 8085

        url = status_url_after_restart(DummyRequest(), cfg)
        page = build_restart_service_page(cfg, enabled=True, redirect_url=url)

        self.assertEqual(url, "http://192.168.0.40:8085/")
        self.assertIn("http://192.168.0.40:8085/", page)
        self.assertIn("Hauptseite öffnen", page)
        self.assertNotIn("/status", page)
        self.assertNotIn("Statusseite", page)


if __name__ == "__main__":
    unittest.main()
