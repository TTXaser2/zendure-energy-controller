# SPDX-License-Identifier: AGPL-3.0-or-later

import unittest

from settings_apply_policy import build_apply_plan


class TestS11ApplyPolicy(unittest.TestCase):
    def test_mixed_diff_is_classified_without_values(self):
        effective = {
            "MAX_CHARGE_POWER_W": 2100,
            "MQTT_BROKER": "old-broker",
            "MEASUREMENT_DB_PATH": "/var/lib/zendure-controller/zec_measurements.sqlite3",
            "REPLAY_WEB_PORT": 8090,
            "SERVICE_RESTART_COMMAND": "old",
            "FUTURE_UNKNOWN": 1,
        }
        configured = dict(effective)
        configured.update(
            MAX_CHARGE_POWER_W=2000,
            MQTT_BROKER="new-broker",
            MEASUREMENT_DB_PATH="/tmp/new.sqlite3",
            REPLAY_WEB_PORT=8091,
            SERVICE_RESTART_COMMAND="new",
            FUTURE_UNKNOWN=2,
        )
        plan = build_apply_plan(configured, effective)
        self.assertEqual(("MAX_CHARGE_POWER_W",), plan.live_keys)
        self.assertEqual(("MQTT_BROKER",), plan.restart_keys)
        self.assertEqual(("MEASUREMENT_DB_PATH",), plan.protected_action_keys)
        self.assertEqual(("REPLAY_WEB_PORT",), plan.read_only_keys)
        self.assertEqual(("SERVICE_RESTART_COMMAND",), plan.migration_only_keys)
        self.assertEqual(("FUTURE_UNKNOWN",), plan.unknown_keys)
        self.assertTrue(plan.pending_restart)
        self.assertFalse(plan.valid_for_normal_apply)
        self.assertNotIn("old-broker", repr(plan))
        self.assertNotIn("new-broker", repr(plan))

    def test_live_only_plan_is_valid_and_has_no_pending_restart(self):
        plan = build_apply_plan({"HEADLESS_MODE": False}, {"HEADLESS_MODE": True})
        self.assertEqual(("HEADLESS_MODE",), plan.live_keys)
        self.assertFalse(plan.pending_restart)
        self.assertTrue(plan.valid_for_normal_apply)

    def test_restart_only_plan_sets_pending(self):
        plan = build_apply_plan({"WEB_PORT": 8081}, {"WEB_PORT": 8080})
        self.assertEqual(("WEB_PORT",), plan.restart_keys)
        self.assertTrue(plan.pending_restart)
        self.assertTrue(plan.valid_for_normal_apply)

    def test_no_diff_is_empty(self):
        values = {"HEADLESS_MODE": False, "WEB_PORT": 8080}
        plan = build_apply_plan(values, dict(values))
        self.assertEqual(tuple(), plan.changed_keys)
        self.assertTrue(plan.valid_for_normal_apply)

    def test_input_mappings_are_not_mutated(self):
        configured = {"HEADLESS_MODE": False}
        effective = {"HEADLESS_MODE": True}
        configured_before = dict(configured)
        effective_before = dict(effective)
        build_apply_plan(configured, effective)
        self.assertEqual(configured_before, configured)
        self.assertEqual(effective_before, effective)


if __name__ == "__main__":
    unittest.main()
