import time
import unittest

from controller_logic import ZendureController
from state import ControllerState
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


class Rc13CommandSafetyFollowupTests(unittest.TestCase):
    def make_controller(self, cfg=None, state=None):
        cfg = cfg or base_cfg()
        state = state or fresh_state(80)
        mqtt = SmartRecordingMqtt()
        controller = ZendureController(
            DummyConfigManager(cfg), state, mqtt, OkShelly(0),
            NoopCsv(), NoopZendureApi(), NoopLogger(),
        )
        return controller, state, mqtt, cfg

    @staticmethod
    def set_command_state(state: ControllerState, *, smart=1, ac="Input mode", input_limit=0, output_limit=0, age_s=0):
        now = time.time() - age_s
        state.update_zendure_command_property("smartMode", smart, "test", now)
        state.update_zendure_command_property("acMode", ac, "test", now)
        state.update_zendure_command_property("inputLimit", input_limit, "test", now)
        state.update_zendure_command_property("outputLimit", output_limit, "test", now)
        state.update_zendure_command_property("chargeMaxLimit", 2400, "test", now)
        state.update_zendure_command_property("inverseMaxPower", 2000, "test", now)
        state.update_zendure_command_property("gridOffMode", 2, "test", now)

    @staticmethod
    def set_live_power(state: ControllerState, *, grid_input=0, output_home=0, output_pack=0, pack_input=0, grid_off=0):
        state.update_zendure_headunit_power(
            "MQTT",
            grid_input=grid_input,
            output_home=output_home,
            output_pack=output_pack,
            pack_input=pack_input,
            grid_off=grid_off,
        )
        with state.lock:
            state.zendure_mqtt_overall_status = "ZENDURE_MQTT_OK"
            state.zendure_mqtt_live_confirmed = True
            state.actual_zendure_power_valid = True
            state.last_zendure_power_update_epoch = time.time()

    def test_confirmed_neutralization_is_deduped_across_reason_changes(self):
        controller, state, mqtt, cfg = self.make_controller()
        self.set_command_state(state, smart=1, ac="Output mode", input_limit=0, output_limit=400)
        self.set_live_power(state)

        controller._publish_neutralization("MIN_SOC_LIMIT", ac_mode="Output mode")
        self.assertEqual(3, len(mqtt.commands))
        first_event_id = state.command_publish_event_id

        self.set_command_state(state, smart=1, ac="Output mode", input_limit=0, output_limit=0)
        controller.update_command_effect_monitor(cfg)
        self.assertEqual("COMMAND_NEUTRALIZATION_CONFIRMED", state.command_effect_category)

        controller._publish_neutralization("SAFE_STATE", ac_mode="Output mode")
        self.assertEqual("NEUTRALIZATION_REASON_UPDATED", state.command_publish_event)
        for _ in range(99):
            controller._publish_neutralization("SAFE_STATE", ac_mode="Output mode")

        self.assertEqual(3, len(mqtt.commands))
        self.assertEqual(first_event_id, state.command_publish_event_id)
        self.assertEqual(1, state.command_neutralization_episode_id)

    def test_unconfirmed_neutralization_retries_at_most_once_per_window(self):
        cfg = base_cfg(ZENDURE_COMMAND_STATE_RETRY_SECONDS=30)
        controller, state, mqtt, _ = self.make_controller(cfg)
        # No fresh command-state readback.
        controller._publish_neutralization("MIN_SOC_LIMIT", ac_mode="Output mode")
        first_count = len(mqtt.commands)
        for _ in range(20):
            controller._publish_neutralization("MIN_SOC_LIMIT", ac_mode="Output mode")
        self.assertEqual(4, first_count)  # smart + ac + input + output
        self.assertEqual(first_count, len(mqtt.commands))
        self.assertEqual("SAFETY_NEUTRALIZATION_WAITING", state.command_state_gate_state)
        self.assertGreater(state.command_state_retry_remaining_s, 0)

    def test_stale_smart_mode_value_does_not_unlock_active_limits(self):
        controller, state, mqtt, _ = self.make_controller()
        self.set_command_state(state, smart=1, ac="Input mode", input_limit=400, output_limit=0, age_s=120)

        controller._publish_signed_target(500, reason="AUTO_CHARGE")

        self.assertEqual([("smart", True, True)], mqtt.commands)
        self.assertEqual("WAIT_SMART_MODE_READBACK", state.command_state_gate_state)
        self.assertFalse(state.zendure_flash_protection_active)

    def test_changing_targets_do_not_bypass_full_state_retry_window(self):
        cfg = base_cfg(ZENDURE_COMMAND_STATE_RETRY_SECONDS=30)
        controller, state, mqtt, _ = self.make_controller(cfg)
        # smartMode is fresh, but the remaining command state is incomplete.
        now = time.time()
        state.update_zendure_command_property("smartMode", 1, "test", now)

        controller._publish_signed_target(1800, reason="AUTO_CHARGE")
        first = list(mqtt.commands)
        controller._publish_signed_target(2100, reason="AUTO_CHARGE")
        controller._publish_signed_target(1950, reason="AUTO_CHARGE")

        self.assertEqual(
            [("ac", "Input mode", True), ("output", 0, True), ("input", 1800, True)],
            first,
        )
        self.assertEqual(first, mqtt.commands)
        self.assertEqual(1950, state.command_desired_signed_target_w)
        self.assertEqual("WAIT_FULL_STATE_READBACK", state.command_state_gate_state)

    def test_relative_tracking_tolerance_prevents_false_mismatch(self):
        cfg = base_cfg(
            COMMAND_EFFECT_TOLERANCE_W=80,
            COMMAND_EFFECT_TOLERANCE_PERCENT=10,
            COMMAND_EFFECT_TIMEOUT_SECONDS=10,
        )
        state = fresh_state(90)
        controller, state, mqtt, _ = self.make_controller(cfg, state)
        self.set_command_state(state, smart=1, ac="Input mode", input_limit=2397, output_limit=0)
        with state.lock:
            state.last_input_power = 2397
            state.last_output_power = 0
        controller._desired_command_batch = controller._new_command_batch(2397, reason="AUTO_CHARGE")
        controller._command_effect_watch_intent = "CHARGE"
        controller._command_effect_watch_start_epoch = time.time() - 120
        controller._command_tracking_mismatch_start_epoch = time.time() - 120
        self.set_live_power(state, grid_input=2233, output_pack=2233)

        controller.update_command_effect_monitor(cfg)

        self.assertEqual("COMMAND_TARGET_TRACKING_EFFECTIVE", state.command_effect_category)
        self.assertFalse(state.command_not_effective_active)
        self.assertEqual(0, state.command_resync_count)

    def test_high_soc_taper_is_acceptance_limited_without_resync(self):
        cfg = base_cfg(
            MAX_SOC_PERCENT=100,
            MAX_CHARGE_POWER_W=2400,
            COMMAND_EFFECT_TOLERANCE_W=80,
            COMMAND_EFFECT_TOLERANCE_PERCENT=10,
            COMMAND_EFFECT_TIMEOUT_SECONDS=10,
            COMMAND_EFFECT_FORCE_RESEND_SECONDS=20,
        )
        state = fresh_state(93)
        controller, state, mqtt, _ = self.make_controller(cfg, state)
        self.set_command_state(state, smart=1, ac="Input mode", input_limit=2397, output_limit=0)
        with state.lock:
            state.last_input_power = 2397
            state.last_output_power = 0
            state.grid_power = -3000
        controller._desired_command_batch = controller._new_command_batch(2397, reason="AUTO_CHARGE")
        controller._command_effect_watch_intent = "CHARGE"
        controller._command_effect_watch_start_epoch = time.time() - 600
        controller._command_tracking_mismatch_start_epoch = time.time() - 600
        self.set_live_power(state, grid_input=1900, output_pack=1900)

        controller.update_charge_acceptance_diagnostic(cfg)
        controller.update_command_effect_monitor(cfg)

        self.assertEqual("limited", state.charge_acceptance_state)
        self.assertEqual("COMMAND_CHARGE_ACCEPTANCE_LIMITED", state.command_effect_category)
        self.assertFalse(state.command_not_effective_active)
        self.assertEqual([], mqtt.commands)

    def test_low_soc_severe_undertracking_still_becomes_mismatch(self):
        cfg = base_cfg(
            MAX_SOC_PERCENT=100,
            COMMAND_EFFECT_TOLERANCE_W=80,
            COMMAND_EFFECT_TOLERANCE_PERCENT=10,
            COMMAND_EFFECT_TIMEOUT_SECONDS=10,
            COMMAND_EFFECT_FORCE_RESEND_SECONDS=999,
        )
        state = fresh_state(10)
        controller, state, mqtt, _ = self.make_controller(cfg, state)
        self.set_command_state(state, smart=1, ac="Input mode", input_limit=2397, output_limit=0)
        with state.lock:
            state.last_input_power = 2397
            state.last_output_power = 0
        controller._desired_command_batch = controller._new_command_batch(2397, reason="AUTO_CHARGE")
        controller._command_effect_watch_intent = "CHARGE"
        controller._command_effect_watch_start_epoch = time.time() - 120
        controller._command_tracking_mismatch_start_epoch = time.time() - 120
        self.set_live_power(state, grid_input=100, output_pack=100)

        controller.update_charge_acceptance_diagnostic(cfg)
        controller.update_command_effect_monitor(cfg)

        self.assertEqual("COMMAND_MISMATCH_CONFIRMED", state.command_effect_category)
        self.assertTrue(state.command_not_effective_active)

    def test_publish_event_id_changes_only_on_actual_publish(self):
        controller, state, mqtt, _ = self.make_controller()
        self.set_command_state(state, smart=1, ac="Input mode", input_limit=400, output_limit=0)

        controller._publish_signed_target(550, reason="AUTO_CHARGE")
        first_id = state.command_publish_event_id
        first_epoch = state.command_publish_epoch_s
        self.set_command_state(state, smart=1, ac="Input mode", input_limit=550, output_limit=0)
        controller._publish_signed_target(550, reason="AUTO_CHARGE")

        self.assertEqual(1, first_id)
        self.assertEqual(first_id, state.command_publish_event_id)
        self.assertEqual(first_epoch, state.command_publish_epoch_s)
        self.assertEqual("COMMAND_BATCH_DEDUPED", state.command_publish_event)

    def test_explicit_night_neutralization_satisfies_startup_deadband_guard(self):
        controller, state, mqtt, cfg = self.make_controller()
        self.set_command_state(state, smart=1, ac="Output mode", input_limit=0, output_limit=400)
        controller._publish_neutralization("NIGHT_RESERVE_SOC", ac_mode="Output mode")
        count_after_night = len(mqtt.commands)
        self.set_command_state(state, smart=1, ac="Output mode", input_limit=0, output_limit=0)
        with state.lock:
            state.last_input_power = 0
            state.last_output_power = 0
        controller.handle_deadband(cfg)
        self.assertEqual(count_after_night, len(mqtt.commands))

    def test_neutralization_resync_republishes_even_if_readback_already_says_zero(self):
        controller, state, mqtt, cfg = self.make_controller()
        self.set_command_state(state, smart=1, ac="Output mode", input_limit=0, output_limit=0)
        controller._desired_command_batch = controller._new_command_batch(
            0, reason="MIN_SOC_LIMIT", explicit_neutralize=True, ac_mode="Output mode", safety_relevant=True
        )
        controller._force_resend_signed_target(0, "RESYNC_AFTER_NEUTRALIZATION_MISMATCH")
        self.assertEqual(
            [("ac", "Output mode", True), ("input", 0, True), ("output", 0, True)],
            mqtt.commands,
        )
        self.assertEqual("FULL_STATE_RESYNC_SENT", state.command_publish_event)


if __name__ == "__main__":
    unittest.main()
