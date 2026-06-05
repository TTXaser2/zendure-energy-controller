import unittest
from copy import deepcopy

from config_manager import DEFAULT_CONFIG
from config_validator import split_issues, validate_config_semantics


class ConfigValidatorTests(unittest.TestCase):
    def base_config(self):
        cfg = deepcopy(DEFAULT_CONFIG)
        cfg["ZENDURE_LOCAL_API_USE_FOR_TELEMETRY"] = False
        cfg["ZENDURE_LOCAL_IP"] = ""
        cfg["CSV_LOG_ENABLED"] = False
        cfg["FILE_LOG_ENABLED"] = False
        return cfg

    def severities(self, cfg):
        issues = validate_config_semantics(cfg, current=self.base_config(), perform_live_checks=False, base_dir=".")
        return split_issues(issues), issues

    def test_manual_discharge_below_min_soc_is_error_and_fixed_mode_warning(self):
        cfg = self.base_config()
        cfg["MIN_SOC_PERCENT"] = 15
        cfg["MANUAL_MODE"] = "FIXED_DISCHARGE"
        cfg["MANUAL_FIXED_DISCHARGE_TARGET_SOC"] = 10
        buckets, issues = self.severities(cfg)
        codes = {issue.code for issue in issues}
        self.assertIn("MANUAL_DISCHARGE_SOC_TOO_LOW", codes)
        self.assertIn("MANUAL_FIXED_MODE_ACTIVE", codes)
        self.assertGreaterEqual(len(buckets["ERROR"]), 1)
        self.assertGreaterEqual(len(buckets["WARNING"]), 1)

    def test_manual_charge_above_max_soc_is_error(self):
        cfg = self.base_config()
        cfg["MAX_SOC_PERCENT"] = 90
        cfg["MANUAL_FIXED_CHARGE_TARGET_SOC"] = 95
        buckets, issues = self.severities(cfg)
        self.assertIn("MANUAL_CHARGE_SOC_TOO_HIGH", {issue.code for issue in issues})
        self.assertGreaterEqual(len(buckets["ERROR"]), 1)

    def test_min_soc_must_be_lower_than_max_soc(self):
        cfg = self.base_config()
        cfg["MIN_SOC_PERCENT"] = 80
        cfg["MAX_SOC_PERCENT"] = 80
        buckets, issues = self.severities(cfg)
        self.assertIn("SOC_LIMITS_INVALID", {issue.code for issue in issues})
        self.assertEqual(buckets["ERROR"][0].severity, "ERROR")

    def test_evcc_profile_requires_base_topic(self):
        cfg = self.base_config()
        cfg["CROSS_CHARGE_ENABLED"] = True
        cfg["SECOND_BATTERY_SOURCE_PROFILE"] = "evcc_standard"
        cfg["SECOND_BATTERY_EVCC_BASE_TOPIC"] = ""
        buckets, issues = self.severities(cfg)
        self.assertIn("SECOND_BATTERY_EVCC_BASE_TOPIC_MISSING", {issue.code for issue in issues})
        self.assertTrue(buckets["ERROR"])


    def test_cross_charge_enabled_warns_on_empty_display_name(self):
        cfg = self.base_config()
        cfg["CROSS_CHARGE_ENABLED"] = True
        cfg["SECOND_BATTERY_SOURCE_PROFILE"] = "evcc_standard"
        cfg["SECOND_BATTERY_EVCC_BASE_TOPIC"] = "evcc/site/battery/devices/1"
        cfg["SECOND_BATTERY_DISPLAY_NAME"] = ""
        buckets, issues = self.severities(cfg)
        self.assertIn("SECOND_BATTERY_NAME_EMPTY", {issue.code for issue in issues})
        self.assertFalse(buckets["ERROR"])
        self.assertTrue(buckets["WARNING"])

    def test_restart_relevant_changes_detects_web_port_and_mqtt(self):
        from config_validator import restart_relevant_changes
        current = self.base_config()
        cfg = self.base_config()
        cfg["WEB_PORT"] = 8081
        cfg["MQTT_BROKER"] = "192.168.0.99"
        changed = restart_relevant_changes(cfg, current)
        self.assertIn("WEB_PORT", changed)
        self.assertIn("MQTT_BROKER", changed)


    def test_custom_cross_charge_requires_power_topic_and_json_paths(self):
        cfg = self.base_config()
        cfg["CROSS_CHARGE_ENABLED"] = True
        cfg["SECOND_BATTERY_SOURCE_PROFILE"] = "custom"
        cfg["SECOND_BATTERY_POWER_TOPIC"] = ""
        cfg["SECOND_BATTERY_SOC_TOPIC"] = "home/battery"
        cfg["SECOND_BATTERY_SOC_PAYLOAD_TYPE"] = "json"
        cfg["SECOND_BATTERY_SOC_JSON_PATH"] = ""
        buckets, issues = self.severities(cfg)
        codes = {issue.code for issue in issues}
        self.assertIn("SECOND_BATTERY_POWER_TOPIC_MISSING", codes)
        self.assertIn("SECOND_BATTERY_SOC_JSON_PATH_MISSING", codes)
        self.assertTrue(buckets["ERROR"])

    def test_aggressive_control_params_are_warning_not_error(self):
        cfg = self.base_config()
        cfg["DEADBAND_W"] = 10
        cfg["CONTROL_GAIN"] = 0.8
        cfg["MAX_POWER_STEP_W"] = 500
        buckets, issues = self.severities(cfg)
        self.assertIn("AGGRESSIVE_CONTROL_PARAMS", {issue.code for issue in issues})
        self.assertFalse(buckets["ERROR"])
        self.assertTrue(buckets["WARNING"])

    def test_default_config_uses_quiet_production_logging(self):
        from config_manager import DEFAULT_CONFIG
        self.assertFalse(DEFAULT_CONFIG["DEBUG"])
        self.assertFalse(DEFAULT_CONFIG["LOG_VALUES"])
        self.assertFalse(DEFAULT_CONFIG["LOG_CONTROL"])
        self.assertFalse(DEFAULT_CONFIG["LOG_MQTT"])
        self.assertFalse(DEFAULT_CONFIG["LOG_SOC"])


if __name__ == "__main__":
    unittest.main()
