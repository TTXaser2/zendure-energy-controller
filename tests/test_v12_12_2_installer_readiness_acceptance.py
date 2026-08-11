import copy
import unittest

from tools.evaluate_installation_readiness import classify


class V12122InstallerReadinessAcceptanceTests(unittest.TestCase):
    def base_payload(self):
        return {
            "status": "degraded",
            "ready": False,
            "version": "12.13.0",
            "build_id": "v12.13.0-20260811",
            "checks": {
                "mqtt": {"ok": True},
                "grid_measurement": {"ok": True},
                "zendure_soc": {"ok": True},
                "cross_charge_second_battery": {"ok": True},
                "command_path": {"ok": True},
                "command_state": {
                    "ok": True,
                    "complete": True,
                    "static_invariant_ok": True,
                    "ac_mode": "Output mode",
                    "input_limit_w": 0,
                    "output_limit_w": 29,
                },
                "command_readback": {
                    "ok": False,
                    "matches_desired": False,
                    "mismatch_fields": "OUTPUT_LIMIT",
                },
                "command_guards": {
                    "ok": False,
                    "uncertain_mqtt_active": True,
                    "not_effective_active": False,
                    "late_effect_guard_active": False,
                    "lifecycle_state": "ACTIVE_BELOW_DIAGNOSTIC_THRESHOLD",
                },
                "zendure_power_telemetry": {"ok": True},
                "controller": {
                    "ok": True,
                    "mode": "DISCHARGE",
                    "consecutive_errors": 0,
                },
            },
            "failed_checks": ["command_readback", "command_guards"],
        }

    def test_real_fix5_post_rollback_transition_is_accepted_without_claiming_ready(self):
        self.assertEqual(
            ("TRANSITIONAL", "LIMIT_READBACK_CONVERGENCE"),
            classify(self.base_payload()),
        )

    def test_fully_ready_payload_is_preferred(self):
        payload = self.base_payload()
        payload["ready"] = True
        payload["failed_checks"] = []
        self.assertEqual(("READY", "FULL_READY"), classify(payload))

    def test_safe_state_is_rejected(self):
        payload = self.base_payload()
        payload["checks"]["controller"]["mode"] = "SAFE_STATE"
        self.assertEqual(("REJECT", "CONTROLLER_SAFE_STATE"), classify(payload))

    def test_static_command_invariant_failure_is_rejected(self):
        payload = self.base_payload()
        payload["checks"]["command_state"]["static_invariant_ok"] = False
        self.assertEqual(("REJECT", "COMMAND_STATE_INCOMPLETE"), classify(payload))

    def test_ac_mode_mismatch_is_rejected(self):
        payload = self.base_payload()
        payload["checks"]["command_readback"]["mismatch_fields"] = "AC_MODE"
        self.assertEqual(("REJECT", "NON_LIMIT_COMMAND_MISMATCH"), classify(payload))

    def test_confirmed_not_effective_guard_is_rejected(self):
        payload = self.base_payload()
        payload["checks"]["command_guards"]["not_effective_active"] = True
        self.assertEqual(("REJECT", "COMMAND_NOT_EFFECTIVE"), classify(payload))

    def test_late_effect_guard_is_rejected(self):
        payload = self.base_payload()
        payload["checks"]["command_guards"]["late_effect_guard_active"] = True
        self.assertEqual(("REJECT", "LATE_EFFECT_GUARD"), classify(payload))

    def test_unrelated_failed_check_is_rejected(self):
        payload = self.base_payload()
        payload["failed_checks"].append("grid_measurement")
        self.assertEqual(("REJECT", "UNSAFE_FAILED_CHECKS"), classify(payload))

    def test_wrong_release_identity_is_rejected(self):
        payload = self.base_payload()
        payload["build_id"] = "rc20-audit-fix6-20260806"
        self.assertEqual(("REJECT", "IDENTITY"), classify(payload))


if __name__ == "__main__":
    unittest.main()
