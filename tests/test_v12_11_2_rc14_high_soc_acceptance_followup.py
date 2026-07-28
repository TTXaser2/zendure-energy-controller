import csv
import json
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from tests.test_operation_priority import (
    DummyConfigManager,
    NoopCsv,
    NoopLogger,
    NoopZendureApi,
    OkShelly,
    base_cfg,
    fresh_state,
)
from tests.test_v12_11_2_rc12_command_contract import SmartRecordingMqtt
from controller_logic import ZendureController
from csv_logger import compute_config_control_hash
from measurement_v4 import build_config_snapshot, build_v4_row
from measurement_v4_contract import STANDARD_HEADER, rc13_header_for_profile
from state import ControllerState


FIXTURE_DIR = Path(__file__).with_name("fixtures")
FIXTURE = FIXTURE_DIR / "rc13_taper_episode_20260727.csv"
EXPECTED = FIXTURE_DIR / "rc14_expected_checkpoints.json"


class Rc14HighSocAcceptanceFollowupTests(unittest.TestCase):
    def make_controller(self, cfg=None, state=None):
        cfg = cfg or base_cfg(
            MAX_SOC_PERCENT=100,
            COMMAND_EFFECT_MIN_TARGET_W=120,
            COMMAND_EFFECT_MIN_W=80,
            COMMAND_EFFECT_TOLERANCE_W=80,
            COMMAND_EFFECT_TOLERANCE_PERCENT=10,
            COMMAND_EFFECT_TIMEOUT_SECONDS=10,
            COMMAND_EFFECT_FORCE_RESEND_SECONDS=20,
            DEADBAND_W=80,
        )
        state = state or fresh_state(98)
        mqtt = SmartRecordingMqtt()
        controller = ZendureController(
            DummyConfigManager(cfg), state, mqtt, OkShelly(0),
            NoopCsv(), NoopZendureApi(), NoopLogger(),
        )
        return controller, state, mqtt, cfg

    @staticmethod
    def set_command_state(state: ControllerState, *, now, input_limit, output_limit=0, ac="Input mode", smart=1):
        state.update_zendure_command_property("smartMode", smart, "test", now)
        state.update_zendure_command_property("acMode", ac, "test", now)
        state.update_zendure_command_property("inputLimit", input_limit, "test", now)
        state.update_zendure_command_property("outputLimit", output_limit, "test", now)
        state.update_zendure_command_property("chargeMaxLimit", 2400, "test", now)
        state.update_zendure_command_property("inverseMaxPower", 2000, "test", now)
        state.update_zendure_command_property("gridOffMode", 2, "test", now)

    @staticmethod
    def set_live_cycle(state: ControllerState, *, now, soc, grid_power, grid_input, output_pack, pack_input=0, output_home=0):
        with patch("state.time.time", return_value=now):
            state.update_zendure_headunit_power(
                "MQTT",
                grid_input=grid_input,
                output_home=output_home,
                output_pack=output_pack,
                pack_input=pack_input,
                grid_off=0,
            )
        with state.lock:
            state.battery_soc = soc
            state.last_soc_update_epoch = now
            state.grid_power = grid_power
            state.zendure_mqtt_overall_status = "ZENDURE_MQTT_OK"
            state.zendure_mqtt_live_confirmed = True
            state.actual_zendure_power_valid = True
            state.last_zendure_power_update_epoch = now

    def run_charge_cycle(self, controller, state, cfg, *, now, soc, target, readback, actual, grid):
        self.set_command_state(state, now=now, input_limit=readback)
        self.set_live_cycle(
            state,
            now=now,
            soc=soc,
            grid_power=grid,
            grid_input=max(0, actual),
            output_pack=max(0, actual),
        )
        with state.lock:
            state.last_input_power = target
            state.last_output_power = 0
            state.command_desired_intent = "CHARGE"
            state.command_desired_input_limit_w = target
            state.command_desired_output_limit_w = 0
            state.command_desired_ac_mode = "Input mode"
        controller._desired_command_batch = controller._new_command_batch(target, reason="AUTO_CHARGE")
        if controller._command_effect_watch_intent == "IDLE":
            controller._command_effect_watch_intent = "CHARGE"
            controller._command_effect_watch_start_epoch = now - 120
            controller._command_tracking_mismatch_start_epoch = now - 120
        with ExitStack() as stack:
            stack.enter_context(patch("controller_logic.time.time", return_value=now))
            stack.enter_context(patch("state.time.time", return_value=now))
            controller.update_charge_acceptance_diagnostic(cfg)
            controller.update_command_effect_monitor(cfg)

    def test_productive_checkpoint_162659_uses_readback_reference_without_export_requirement(self):
        controller, state, mqtt, cfg = self.make_controller()
        now = 1_000_000.0
        self.run_charge_cycle(
            controller, state, cfg,
            now=now, soc=98, target=1449, readback=1400, actual=125, grid=-60.6,
        )
        self.assertEqual("COMMAND_CHARGE_ACCEPTANCE_LIMITED", state.command_effect_category)
        self.assertIn("HIGH_SOC_CHARGE_LIMITED", state.command_effect_reason)
        self.assertEqual(1400, state.command_effect_reference_w)
        self.assertFalse(state.command_not_effective_active)
        self.assertEqual([], mqtt.commands)

    def test_productive_checkpoint_162902_does_not_require_site_export(self):
        controller, state, mqtt, cfg = self.make_controller()
        now = 1_000_100.0
        self.run_charge_cycle(
            controller, state, cfg,
            now=now, soc=98, target=1112, readback=1172, actual=74, grid=15.8,
        )
        self.assertEqual("COMMAND_CHARGE_ACCEPTANCE_LIMITED", state.command_effect_category)
        self.assertEqual(1112, state.command_effect_reference_w)
        self.assertFalse(state.command_not_effective_active)
        self.assertEqual([], mqtt.commands)

    def test_max_soc_zero_acceptance_is_confirmed_after_three_cycles_and_six_seconds(self):
        controller, state, mqtt, cfg = self.make_controller()
        start = 2_000_000.0
        categories = []
        for offset in (0.0, 3.1, 6.2):
            self.run_charge_cycle(
                controller, state, cfg,
                now=start + offset, soc=100, target=1532, readback=1532, actual=0, grid=-30.0,
            )
            categories.append(state.command_effect_category)
        self.assertEqual(["COMMAND_PENDING", "COMMAND_PENDING", "COMMAND_CHARGE_ACCEPTANCE_LIMITED"], categories)
        self.assertIn("HIGH_SOC_NOT_ACCEPTING", state.command_effect_reason)
        self.assertEqual(1532, state.command_effect_reference_w)
        self.assertFalse(state.command_not_effective_active)
        self.assertEqual(0, state.command_resync_count)
        self.assertEqual([], mqtt.commands)

    def test_low_soc_zero_effect_remains_mismatch_and_recovery_capable(self):
        controller, state, mqtt, cfg = self.make_controller()
        now = 3_000_000.0
        self.set_command_state(state, now=now, input_limit=2397)
        self.set_live_cycle(state, now=now, soc=10, grid_power=-2000, grid_input=0, output_pack=0)
        with state.lock:
            state.last_input_power = 2397
            state.last_output_power = 0
            state.command_desired_intent = "CHARGE"
        controller._desired_command_batch = controller._new_command_batch(2397, reason="AUTO_CHARGE")
        controller._command_effect_watch_intent = "CHARGE"
        controller._command_effect_watch_start_epoch = now - 130
        controller._command_tracking_mismatch_start_epoch = now - 130
        with patch("controller_logic.time.time", return_value=now), patch("state.time.time", return_value=now):
            controller.update_charge_acceptance_diagnostic(cfg)
            controller.update_command_effect_monitor(cfg)
        self.assertIn(state.command_effect_category, {"COMMAND_MISMATCH_CONFIRMED", "COMMAND_RECOVERY_VERIFYING"})
        self.assertGreaterEqual(state.command_resync_count, 1)
        self.assertTrue(any(item[0] in {"ac", "input", "output"} for item in mqtt.commands))

    def test_wrong_ac_mode_and_counter_limit_block_acceptance_reclassification(self):
        controller, state, _, cfg = self.make_controller()
        now = 4_000_000.0
        self.set_command_state(state, now=now, input_limit=1449, output_limit=50, ac="Output mode")
        self.set_live_cycle(state, now=now, soc=98, grid_power=-500, grid_input=125, output_pack=125)
        with state.lock:
            state.last_input_power = 1449
            state.last_output_power = 0
            state.command_desired_intent = "CHARGE"
        controller._desired_command_batch = controller._new_command_batch(1449, reason="AUTO_CHARGE")
        controller._command_effect_watch_intent = "CHARGE"
        controller._command_effect_watch_start_epoch = now - 120
        controller._command_tracking_mismatch_start_epoch = now - 120
        with patch("controller_logic.time.time", return_value=now), patch("state.time.time", return_value=now):
            controller.update_charge_acceptance_diagnostic(cfg)
            controller.update_command_effect_monitor(cfg)
        self.assertNotEqual("COMMAND_CHARGE_ACCEPTANCE_LIMITED", state.command_effect_category)
        self.assertEqual(0, state.command_effect_reference_w)

    def test_real_rc13_taper_fixture_has_no_mismatch_or_resync_from_first_anchor(self):
        controller, state, mqtt, cfg = self.make_controller()
        anchor_categories = {}
        with FIXTURE.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f, delimiter=";"))
        expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
        self.assertEqual(expected["source"]["rows"], len(rows))
        expected_anchors = {
            item["time_local"][:19]: item["expected"]
            for item in expected["anchor_checkpoints"]
            if item["expected"] == "COMMAND_CHARGE_ACCEPTANCE_LIMITED"
        }
        for row in rows:
            timestamp = row["fixture_time_local"]
            if timestamp < "2026-07-27T16:26:59" or timestamp > "2026-07-27T16:31:32":
                continue
            # Use a stable monotonic timeline derived from the real cycle index;
            # the physical values remain the recorded production values.
            now = 5_000_000.0 + float(row["cycle_index"]) * 3.1
            self.run_charge_cycle(
                controller,
                state,
                cfg,
                now=now,
                soc=float(row["zendure_soc_percent"]),
                target=int(float(row["target_final_w"])),
                readback=int(float(row["zendure_command_input_limit_w"])),
                actual=int(float(row["zendure_grid_signed_power_w"])),
                grid=float(row["grid_power_w"]),
            )
            if timestamp.startswith("2026-07-27T16:26:59") or timestamp.startswith("2026-07-27T16:29:02"):
                anchor_categories[timestamp[:19]] = state.command_effect_category
            self.assertNotIn(state.command_effect_category, {"COMMAND_MISMATCH_CONFIRMED", "COMMAND_NEUTRALIZATION_MISMATCH"})
        self.assertEqual(expected_anchors, anchor_categories)
        self.assertEqual(0, state.command_resync_count)
        self.assertEqual([], mqtt.commands)

    def test_v4_contract_contains_rc14_acceptance_fields(self):
        for field in ("charge_acceptance_state", "charge_acceptance_reason", "command_effect_reference_w"):
            self.assertIn(field, STANDARD_HEADER)
            self.assertNotIn(field, rc13_header_for_profile("standard"))
        row = build_v4_row({}, {
            "charge_acceptance_state": "limited",
            "charge_acceptance_reason": "HIGH_SOC_CHARGE_LIMITED: test",
            "command_effect_reference_w": 1400,
        })
        self.assertEqual("limited", row["charge_acceptance_state"])
        self.assertEqual(1400.0, row["command_effect_reference_w"])

    def test_relative_tolerance_is_in_snapshot_and_control_hash(self):
        cfg_a = base_cfg(COMMAND_EFFECT_TOLERANCE_PERCENT=10)
        cfg_b = base_cfg(COMMAND_EFFECT_TOLERANCE_PERCENT=12)
        snapshot = build_config_snapshot(cfg_a)
        self.assertEqual(10, snapshot["control_parameters"]["COMMAND_EFFECT_TOLERANCE_PERCENT"])
        self.assertNotEqual(compute_config_control_hash(cfg_a), compute_config_control_hash(cfg_b))


if __name__ == "__main__":
    unittest.main()
