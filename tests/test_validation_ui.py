import unittest

from config_validator import ValidationIssue
from config_manager import DEFAULT_CONFIG
from web_ui import build_restart_service_page, build_save_result_message, build_validation_messages


class ValidationUiTests(unittest.TestCase):
    def test_error_takes_precedence_over_warning_modal(self):
        issues = [
            ValidationIssue("ERROR", "Fehlerhafte feste Entladung", {"MANUAL_FIXED_DISCHARGE_TARGET_SOC"}, "Manueller Modus", "MANUAL_DISCHARGE_SOC_TOO_LOW"),
            ValidationIssue("WARNING", "Manueller Modus uebersteuert Automatik", {"MANUAL_MODE"}, "Manueller Modus", "MANUAL_FIXED_MODE_ACTIVE"),
        ]
        html = build_validation_messages(issues, validation_state="error")
        self.assertIn("Konfiguration wurde nicht gespeichert", html)
        self.assertIn("Zusätzliche Warnungen", html)
        self.assertNotIn("Konfiguration enthält Warnungen</h2>", html)
        self.assertNotIn("Trotz Warnungen speichern", html)
        self.assertEqual(html.count("id='validationModal'"), 1)

    def test_warning_without_error_has_confirm_button(self):
        issues = [ValidationIssue("WARNING", "Auffällige Regelparameter", {"DEADBAND_W"}, "Regelung", "AGGRESSIVE_CONTROL_PARAMS")]
        html = build_validation_messages(issues, validation_state="warning")
        self.assertIn("Konfiguration enthält Warnungen", html)
        self.assertIn("Trotz Warnungen speichern", html)
        self.assertEqual(html.count("id='validationModal'"), 1)

    def test_restart_required_message_contains_restart_form_when_enabled(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg["WEB_SERVICE_RESTART_ENABLED"] = True
        html = build_save_result_message(cfg, saved=True, restart_required=True, restart_keys="WEB_PORT,MQTT_BROKER")
        self.assertIn("Dienst jetzt neu starten", html)
        self.assertIn("Web Port", html)
        self.assertIn("MQTT Broker", html)

    def test_restart_required_message_contains_manual_command_when_disabled(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg["WEB_SERVICE_RESTART_ENABLED"] = False
        html = build_save_result_message(cfg, saved=True, restart_required=True, restart_keys="WEB_PORT")
        self.assertIn("sudo systemctl restart zendure-controller.service", html)
        self.assertNotIn("Dienst jetzt neu starten", html)

    def test_restart_page_uses_absolute_redirect_to_new_port(self):
        cfg = dict(DEFAULT_CONFIG)
        html = build_restart_service_page(cfg, enabled=True, redirect_url="http://192.168.0.40:8085/status")
        self.assertIn("http://192.168.0.40:8085/status", html)
        self.assertNotIn("window.location.href='/status'", html)



if __name__ == "__main__":
    unittest.main()
