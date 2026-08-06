import unittest

from web_ui import build_health_payload, build_ready_payload


class HealthReadyTests(unittest.TestCase):
    def test_health_is_minimal_liveness_payload(self):
        payload = build_health_payload({"uptime_seconds": 123})
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["alive"])
        self.assertNotIn("checks", payload)

    def test_ready_detects_all_required_checks_ok(self):
        cfg = {"SHELLY_STALE_TIMEOUT_SECONDS": 15, "SOC_STALE_TIMEOUT_SECONDS": 90, "CROSS_CHARGE_ENABLED": False}
        snap = {
            "mqtt_connected": True,
            "last_shelly_update_age_seconds": 1,
            "grid_power_valid": True,
            "last_soc_update_age_seconds": 1,
            "soc_valid": True,
            "battery_soc": 80,
            "zendure_telemetry_source": "MQTT",
            "zendure_local_api_fallback_active": False,
            "mqtt_command_path_available": True,
            "mqtt_command_path_fresh": True,
            "mqtt_command_path_valid": True,
            "actual_zendure_power_valid": True,
            "zendure_command_state_complete": True,
            "zendure_command_smart_mode": 1,
            "zendure_command_ac_mode": "Input mode",
            "zendure_command_input_limit_w": 0,
            "zendure_command_output_limit_w": 0,
            "command_desired_sequence_id": 0,
            "command_uncertain_mqtt_active": False,
            "command_not_effective_active": False,
            "command_late_effect_guard_active": False,
            "command_lifecycle_state": "IDLE",
            "current_mode": "HOLD",
            "consecutive_errors": 0,
            "last_error": "none",
            "last_error_time": "-",
            "uptime_seconds": 123,
        }
        payload = build_ready_payload(cfg, snap)
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["ready"])
        self.assertEqual(payload["failed_checks"], [])


if __name__ == "__main__":
    unittest.main()
