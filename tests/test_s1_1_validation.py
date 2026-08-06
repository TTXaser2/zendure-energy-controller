# SPDX-License-Identifier: AGPL-3.0-or-later

import unittest

from settings_codecs import parse_value
from settings_registry import SETTINGS
from settings_validation import ValidationContext, parse_candidate, validate_candidate


def default_candidate():
    values = {}
    for spec in SETTINGS:
        result = parse_value(spec, spec.default_new_install)
        if result.ok:
            values[spec.key] = result.value
    return values


def codes(issues):
    return [issue.code for issue in issues]


class TestS11Validation(unittest.TestCase):
    def setUp(self):
        self.values = default_candidate()

    def assert_has(self, code, values=None, context=None):
        issues = validate_candidate(values or self.values, context)
        self.assertIn(code, codes(issues), issues)
        return issues

    def test_defaults_have_no_blocking_issues(self):
        issues = validate_candidate(self.values)
        self.assertEqual([], [issue for issue in issues if issue.blocking], issues)

    def test_val_001_soc_window(self):
        self.values.update(MIN_SOC_PERCENT=90, MAX_SOC_PERCENT=80)
        self.assert_has("VAL-001")

    def test_val_002_manual_discharge_profile(self):
        self.values.update(MANUAL_MODE="FIXED_DISCHARGE", MANUAL_FIXED_DISCHARGE_TARGET_SOC=10, MANUAL_FIXED_DISCHARGE_POWER_W=0)
        self.assert_has("VAL-002")

    def test_val_003_manual_charge_profile(self):
        self.values.update(MANUAL_MODE="FIXED_CHARGE", MANUAL_FIXED_CHARGE_TARGET_SOC=10, MANUAL_FIXED_CHARGE_POWER_W=0)
        self.assert_has("VAL-003")

    def test_val_004_night_window(self):
        self.values.update(NIGHT_START_HOUR=5, NIGHT_START_MINUTE=0, NIGHT_END_HOUR=5, NIGHT_END_MINUTE=0)
        self.assert_has("VAL-004")

    def test_val_005_night_reserve(self):
        self.values["NIGHT_DISCHARGE_STOP_SOC_PERCENT"] = 5
        self.assert_has("VAL-005")

    def test_val_006_integration_dependency(self):
        self.values.update(SECOND_BATTERY_INTEGRATION_ENABLED=False, CROSS_CHARGE_ENABLED=True)
        self.assert_has("VAL-006")

    def test_val_007_harvest_requires_cross_charge(self):
        self.values.update(SECOND_BATTERY_INTEGRATION_ENABLED=True, CROSS_CHARGE_ENABLED=False, REST_SURPLUS_HARVEST_ENABLED=True)
        self.assert_has("VAL-007")

    def test_val_008_harvest_topics(self):
        self.values.update(SECOND_BATTERY_SOURCE_PROFILE="custom", SECOND_BATTERY_POWER_TOPIC="")
        self.assert_has("VAL-008")

    def test_val_009_harvest_maximum(self):
        self.values.update(SECOND_BATTERY_INTEGRATION_ENABLED=True, CROSS_CHARGE_ENABLED=True, REST_SURPLUS_HARVEST_ENABLED=True, SECOND_BATTERY_MAX_CHARGE_POWER_W=None)
        self.assert_has("VAL-009")

    def test_val_010_harvest_soc_order(self):
        self.values.update(HARVEST_HIGH_SMA_SOC_EXIT_PERCENT=80, HARVEST_HIGH_SMA_SOC_ENTER_PERCENT=75, HARVEST_SMA_FULL_SOC_PERCENT=70)
        self.assert_has("VAL-010")

    def test_val_011_harvest_power_order(self):
        self.values.update(SECOND_BATTERY_MAX_CHARGE_POWER_W=2000, HARVEST_PRIMARY_CHARGE_FLOOR_W=1900, HARVEST_PRIMARY_CHARGE_RESTART_W=1800, HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_W=1950)
        self.assert_has("VAL-011")

    def test_val_012_absolute_override_is_info(self):
        self.values.update(SECOND_BATTERY_MAX_CHARGE_POWER_W=2000, HARVEST_PRIMARY_CHARGE_RESTART_W=1900)
        issues = self.assert_has("VAL-012")
        matching = [issue for issue in issues if issue.code == "VAL-012"]
        self.assertTrue(all(not issue.blocking for issue in matching))

    def test_val_013_harvest_time_order(self):
        self.values["HARVEST_HIGH_SMA_SOC_PROFILE_MIDDAY_START_TIME"] = "08:00"
        self.assert_has("VAL-013")

    def test_val_014_calendar_season(self):
        self.values.update(HARVEST_SEASON_MODE="calendar", HARVEST_SEASON_PARALLEL_START_MM_DD="10-01", HARVEST_SEASON_PARALLEL_END_MM_DD="03-01")
        self.assert_has("VAL-014")

    def test_val_015_grid_source_preflight(self):
        previous = dict(self.values)
        self.values["GRID_METER_SOURCE"] = "sma_energy_meter_udp"
        self.assert_has("VAL-015", context=ValidationContext(previous=previous, grid_source_candidate_ready=False))

    def test_val_016_sma_multi_meter_serial(self):
        self.values.update(GRID_METER_SOURCE="sma_energy_meter_udp", SMA_ENERGY_METER_SERIAL="")
        self.assert_has("VAL-016", context=ValidationContext(sma_multiple_devices_detected=True))

    def test_val_017_restart_classification_is_nonblocking(self):
        previous = dict(self.values)
        self.values["MQTT_BROKER"] = "broker.local"
        issues = self.assert_has("VAL-017", context=ValidationContext(previous=previous))
        issue = next(issue for issue in issues if issue.code == "VAL-017")
        self.assertFalse(issue.blocking)
        self.assertIn("MQTT_BROKER", issue.keys)

    def test_val_018_v4_off_requires_confirmation(self):
        previous = dict(self.values)
        previous["MEASUREMENT_LOG_MODE"] = "standard"
        self.values["MEASUREMENT_LOG_MODE"] = "off"
        self.assert_has("VAL-018", context=ValidationContext(previous=previous))
        self.assertNotIn("VAL-018", codes(validate_candidate(self.values, ValidationContext(previous=previous, irreversible_v4_gap_confirmed=True))))

    def test_val_019_sqlite_enforce_requires_separate_confirmation(self):
        self.values["MEASUREMENT_DB_MAINTENANCE_MODE"] = "enforce"
        self.assert_has("VAL-019")

    def test_val_020_v4_enforce_requires_all_technical_gates(self):
        self.values.update(MEASUREMENT_LOG_MAINTENANCE_MODE="enforce", MEASUREMENT_LOG_RETENTION_MODE="bounded")
        self.assert_has("VAL-020")

    def test_val_021_db_path_requires_protected_migration(self):
        previous = dict(self.values)
        self.values["MEASUREMENT_DB_PATH"] = "/tmp/other.sqlite3"
        self.assert_has("VAL-021", context=ValidationContext(previous=previous))
        self.assertNotIn("VAL-021", codes(validate_candidate(self.values, ValidationContext(previous=previous, protected_storage_migration=True))))

    def test_val_022_restart_action_contract(self):
        self.assert_has("VAL-022", context=ValidationContext(restart_action_requested=True))

    def test_val_023_secret_contract(self):
        issues = self.assert_has("VAL-023", context=ValidationContext(secret_contract_ok=False))
        self.assertNotIn("super-secret", repr(issues))

    def test_val_024_unknown_keys_preserved(self):
        self.assert_has("VAL-024", context=ValidationContext(unknown_keys_preserved=False))

    def test_parse_candidate_preserves_unknown_keys_opaque(self):
        parsed = parse_candidate({"HEADLESS_MODE": False, "FUTURE_UNKNOWN_KEY": {"nested": [1, 2]}})
        self.assertTrue(parsed.valid)
        self.assertEqual(False, parsed.known["HEADLESS_MODE"])
        self.assertEqual({"nested": [1, 2]}, parsed.unknown["FUTURE_UNKNOWN_KEY"])

    def test_parse_issue_does_not_echo_secret_value(self):
        secret = object()
        parsed = parse_candidate({"MQTT_PASSWORD": secret})
        self.assertFalse(parsed.valid)
        self.assertNotIn(repr(secret), repr(parsed.issues))

    def test_custom_broker_and_device_constraints(self):
        self.values["MQTT_BROKER"] = ""
        self.values["DEVICE_ID"] = "bad/device"
        result = codes(validate_candidate(self.values))
        self.assertIn("MQTT_BROKER_MISSING", result)
        self.assertIn("DEVICE_ID_INVALID", result)


if __name__ == "__main__":
    unittest.main()
