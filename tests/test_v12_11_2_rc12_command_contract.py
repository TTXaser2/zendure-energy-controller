import time
import unittest

from tests.test_operation_priority import (
    DummyConfigManager,
    NoopCsv,
    NoopLogger,
    NoopZendureApi,
    OkShelly,
    base_cfg,
    fresh_state,
)
from controller_logic import ZendureController
from mqtt_bridge import MqttBridge
from state import ControllerState
from zendure_power_observation import derive_zendure_power_observation


class SmartRecordingMqtt:
    def __init__(self):
        self.commands = []

    def set_smart_mode(self, enabled=True, force=False):
        self.commands.append(("smart", bool(enabled), bool(force)))
        return True

    def set_ac_mode(self, mode, force=False):
        self.commands.append(("ac", str(mode), bool(force)))
        return True

    def set_input_limit(self, value, force=False):
        self.commands.append(("input", int(value), bool(force)))
        return True

    def set_output_limit(self, value, force=False):
        self.commands.append(("output", int(value), bool(force)))
        return True


class Rc12CommandContractTests(unittest.TestCase):
    def make_controller(self, cfg=None, state=None, mqtt=None):
        cfg = cfg or base_cfg()
        state = state or fresh_state(80)
        mqtt = mqtt or SmartRecordingMqtt()
        controller = ZendureController(
            DummyConfigManager(cfg), state, mqtt, OkShelly(0),
            NoopCsv(), NoopZendureApi(), NoopLogger(),
        )
        return controller, state, mqtt, cfg

    @staticmethod
    def set_command_state(
        state: ControllerState,
        *,
        smart=1,
        ac="Input mode",
        input_limit=0,
        output_limit=0,
        charge_max=2400,
        inverse_max=2000,
        grid_off_mode=2,
    ):
        now = time.time()
        state.update_zendure_command_property("smartMode", smart, "test", now)
        state.update_zendure_command_property("acMode", ac, "test", now)
        state.update_zendure_command_property("inputLimit", input_limit, "test", now)
        state.update_zendure_command_property("outputLimit", output_limit, "test", now)
        state.update_zendure_command_property("chargeMaxLimit", charge_max, "test", now)
        state.update_zendure_command_property("inverseMaxPower", inverse_max, "test", now)
        state.update_zendure_command_property("gridOffMode", grid_off_mode, "test", now)

    @staticmethod
    def set_live(state: ControllerState):
        with state.lock:
            state.zendure_mqtt_overall_status = "ZENDURE_MQTT_OK"
            state.zendure_mqtt_live_confirmed = True
            state.actual_zendure_power_valid = True
            state.last_zendure_power_update_epoch = time.time()

    def test_active_target_enables_smart_mode_before_dynamic_limits(self):
        controller, state, mqtt, _ = self.make_controller()
        self.set_command_state(state, smart=0, ac="Output mode", input_limit=0, output_limit=0)

        applied = controller._publish_signed_target(500, reason="AUTO_CHARGE")

        self.assertEqual(500, applied)
        self.assertEqual([("smart", True, True)], mqtt.commands)
        self.assertEqual("SMART_MODE_ENABLE_SENT", state.command_publish_event)
        self.assertEqual("COMMAND_STATE_VERIFYING", state.command_lifecycle_state)

    def test_after_smart_readback_wrong_mode_gets_one_full_state(self):
        cfg = base_cfg(ZENDURE_COMMAND_STATE_RETRY_SECONDS=30)
        controller, state, mqtt, _ = self.make_controller(cfg)
        self.set_command_state(state, smart=0, ac="Output mode", input_limit=0, output_limit=0)
        controller._publish_signed_target(500, reason="AUTO_CHARGE")
        mqtt.commands.clear()
        self.set_command_state(state, smart=1, ac="Output mode", input_limit=0, output_limit=0)

        controller._publish_signed_target(500, reason="AUTO_CHARGE")
        first = list(mqtt.commands)
        controller._publish_signed_target(500, reason="AUTO_CHARGE")

        self.assertEqual(
            [("ac", "Input mode", True), ("output", 0, True), ("input", 500, True)],
            first,
        )
        self.assertEqual(first, mqtt.commands)
        self.assertEqual("COMMAND_STATE_WAITING", state.command_publish_event)

    def test_same_direction_confirmed_state_updates_only_active_limit(self):
        controller, state, mqtt, _ = self.make_controller()
        self.set_command_state(state, smart=1, ac="Input mode", input_limit=400, output_limit=0)
        controller._publish_signed_target(400, reason="AUTO_CHARGE")
        mqtt.commands.clear()
        self.set_command_state(state, smart=1, ac="Input mode", input_limit=400, output_limit=0)

        controller._publish_signed_target(550, reason="AUTO_CHARGE")

        self.assertEqual([("input", 550, False)], mqtt.commands)
        self.assertEqual("COMMAND_LIMIT_UPDATED", state.command_publish_event)
        self.assertTrue(state.zendure_flash_protection_active)

    def test_direction_change_uses_full_state_without_redundant_smart_write(self):
        controller, state, mqtt, _ = self.make_controller()
        self.set_command_state(state, smart=1, ac="Input mode", input_limit=400, output_limit=0)
        controller._publish_signed_target(450, reason="AUTO_CHARGE")
        mqtt.commands.clear()
        self.set_command_state(state, smart=1, ac="Input mode", input_limit=450, output_limit=0)

        controller._publish_signed_target(-600, reason="AUTO_DISCHARGE")

        self.assertEqual(
            [("ac", "Output mode", True), ("input", 0, True), ("output", 600, True)],
            mqtt.commands,
        )
        self.assertFalse(any(command[0] == "smart" for command in mqtt.commands))

    def test_device_side_discharge_cap_is_applied_and_stored(self):
        cfg = base_cfg(MAX_DISCHARGE_POWER_W=2100)
        controller, state, mqtt, _ = self.make_controller(cfg)
        self.set_command_state(state, smart=1, ac="Output mode", input_limit=0, output_limit=0, inverse_max=2000)

        applied = controller._publish_signed_target(-2100, reason="AUTO_DISCHARGE")

        self.assertEqual(-2000, applied)
        self.assertIn(("output", 2000, True), mqtt.commands)
        self.assertIn("ZENDURE_DEVICE_DISCHARGE_LIMIT", state.active_limiters)
        self.assertEqual(-2000, state.command_desired_signed_target_w)

    def test_output_pack_and_grid_input_are_consistent_charge_evidence(self):
        obs = derive_zendure_power_observation(
            grid_input=74,
            output_pack=74,
            pack_input=0,
            output_home=0,
        )
        self.assertEqual("CHARGE", obs["direction"])
        self.assertEqual(74, obs["signed_power_w"])
        self.assertEqual("CHARGE", obs["battery_direction"])
        self.assertEqual(74, obs["battery_signed_power_w"])

    def test_offgrid_load_is_separate_from_grid_neutralization(self):
        obs = derive_zendure_power_observation(
            grid_input=0,
            output_home=0,
            output_pack=0,
            pack_input=400,
            grid_off=400,
        )
        self.assertEqual("NEUTRAL", obs["grid_direction"])
        self.assertEqual(0, obs["grid_signed_power_w"])
        self.assertEqual("DISCHARGE", obs["battery_direction"])
        self.assertEqual(-400, obs["battery_signed_power_w"])
        self.assertEqual(400, obs["offgrid_power_w"])
        self.assertTrue(obs["offgrid_active"])

    def test_neutralization_is_confirmed_with_active_offgrid_load(self):
        controller, state, mqtt, cfg = self.make_controller()
        self.set_command_state(state, smart=1, ac="Output mode", input_limit=0, output_limit=400)
        state.update_zendure_headunit_power(
            "MQTT", grid_input=0, output_home=0, output_pack=0, pack_input=400, grid_off=400
        )
        self.set_live(state)

        controller._publish_neutralization("TEST_OFFGRID", ac_mode="Output mode")
        controller.update_command_effect_monitor(cfg)

        self.assertEqual("COMMAND_NEUTRALIZATION_CONFIRMED", state.command_effect_category)
        self.assertFalse(state.command_neutralization_active)
        self.assertEqual(400, state.zendure_offgrid_power_w)
        self.assertEqual("FULL_STATE_NEUTRALIZATION_SENT", state.command_publish_event)
        self.assertFalse(any(command[0] == "smart" for command in mqtt.commands))

    def test_high_soc_limited_charge_is_not_command_mismatch(self):
        cfg = base_cfg(
            MAX_SOC_PERCENT=100,
            COMMAND_EFFECT_TIMEOUT_SECONDS=10,
            COMMAND_EFFECT_FORCE_RESEND_SECONDS=20,
            COMMAND_EFFECT_MIN_W=80,
        )
        state = fresh_state(98)
        controller, state, mqtt, _ = self.make_controller(cfg, state)
        self.set_command_state(state, smart=1, ac="Input mode", input_limit=2397, output_limit=0)
        with state.lock:
            state.last_input_power = 2397
            state.last_output_power = 0
            state.grid_power = -5000
        state.update_zendure_headunit_power(
            "MQTT", grid_input=74, output_home=0, output_pack=74, pack_input=0
        )
        self.set_live(state)
        controller._command_effect_watch_intent = "CHARGE"
        controller._command_effect_watch_target = 2397
        controller._command_effect_watch_start_epoch = time.time() - 120
        controller._command_tracking_mismatch_start_epoch = time.time() - 120

        controller.update_charge_acceptance_diagnostic(cfg)
        controller.update_command_effect_monitor(cfg)

        self.assertIn(state.charge_acceptance_state, {"limited", "not_accepting"})
        self.assertEqual("COMMAND_CHARGE_ACCEPTANCE_LIMITED", state.command_effect_category)
        self.assertEqual("ACTIVE_ACCEPTANCE_LIMITED", state.command_lifecycle_state)
        self.assertFalse(state.command_not_effective_active)
        self.assertEqual(0, state.command_resync_count)

    def test_high_soc_battery_charge_without_grid_input_does_not_prove_ac_command(self):
        cfg = base_cfg(
            MAX_SOC_PERCENT=100,
            COMMAND_EFFECT_TIMEOUT_SECONDS=10,
            COMMAND_EFFECT_FORCE_RESEND_SECONDS=999,
            COMMAND_EFFECT_MIN_W=80,
        )
        state = fresh_state(98)
        controller, state, mqtt, _ = self.make_controller(cfg, state)
        self.set_command_state(state, smart=1, ac="Input mode", input_limit=2397, output_limit=0)
        with state.lock:
            state.last_input_power = 2397
            state.last_output_power = 0
            state.grid_power = -5000
        state.update_zendure_headunit_power(
            "MQTT", grid_input=0, output_home=0, output_pack=74, pack_input=0, solar_input=74
        )
        self.set_live(state)
        controller._command_effect_watch_intent = "CHARGE"
        controller._command_effect_watch_target = 2397
        controller._command_effect_watch_start_epoch = time.time() - 120
        controller._command_tracking_mismatch_start_epoch = time.time() - 120

        controller.update_charge_acceptance_diagnostic(cfg)
        controller.update_command_effect_monitor(cfg)

        self.assertNotEqual("COMMAND_CHARGE_ACCEPTANCE_LIMITED", state.command_effect_category)
        self.assertEqual("COMMAND_MISMATCH_CONFIRMED", state.command_effect_category)
        self.assertTrue(state.command_not_effective_active)

    def test_safety_neutralization_supersedes_mismatch_without_fake_recovery(self):
        controller, state, mqtt, cfg = self.make_controller()
        self.set_command_state(state, smart=1, ac="Input mode", input_limit=1200, output_limit=0)
        controller._publish_signed_target(1200, reason="AUTO_CHARGE")
        with state.lock:
            state.command_not_effective_active = True
            state.command_not_effective_reason = "alter Lade-Mismatch"
            state.command_lifecycle_state = "MISMATCH_CONFIRMED"
        mqtt.commands.clear()
        state.update_zendure_headunit_power("MQTT", grid_input=0, output_home=0, grid_off=400, pack_input=400)
        self.set_live(state)

        controller._publish_neutralization("MAX_SOC_LIMIT", ac_mode="Input mode")
        controller.update_command_effect_monitor(cfg)

        self.assertEqual("MISMATCH_SUPERSEDED_BY_SAFETY_NEUTRALIZATION", state.command_mismatch_resolution)
        self.assertEqual("NEUTRALIZATION_CONFIRMED", state.command_lifecycle_state)
        self.assertEqual("COMMAND_NEUTRALIZATION_CONFIRMED", state.command_effect_category)
        self.assertFalse(state.command_not_effective_active)
        self.assertEqual("FULL_STATE_NEUTRALIZATION_SENT", state.command_publish_event)

    def test_verified_local_mqtt_command_topics_are_exact(self):
        device_id = "HEC4NENCN492025"
        cfg = {"DEVICE_ID": device_id}
        bridge = MqttBridge(ControllerState(), lambda: cfg)
        topics = bridge.topics()

        self.assertEqual(
            f"Zendure/switch/{device_id}/smartMode/set", topics["smart_mode"]
        )
        self.assertEqual(
            f"Zendure/select/{device_id}/acMode/set", topics["ac_mode"]
        )
        self.assertEqual(
            f"Zendure/number/{device_id}/inputLimit/set", topics["input_limit"]
        )
        self.assertEqual(
            f"Zendure/number/{device_id}/outputLimit/set", topics["output_limit"]
        )

    def test_runtime_cannot_disable_smart_mode(self):
        cfg = {"DEVICE_ID": "HEC4NENCN492025", "MIN_COMMAND_CHANGE_W": 50}
        bridge = MqttBridge(ControllerState(), lambda: cfg)
        with self.assertRaisesRegex(ValueError, "nicht deaktivieren"):
            bridge.set_smart_mode(False)

    def test_mixed_offgrid_supply_keeps_all_boundaries_separate(self):
        obs = derive_zendure_power_observation(
            grid_input=151,
            output_home=0,
            output_pack=0,
            pack_input=52,
            grid_off=203,
        )
        self.assertEqual("CHARGE", obs["grid_direction"])
        self.assertEqual(151, obs["grid_signed_power_w"])
        self.assertEqual("DISCHARGE", obs["battery_direction"])
        self.assertEqual(-52, obs["battery_signed_power_w"])
        self.assertEqual(203, obs["offgrid_power_w"])
        self.assertEqual(0, obs["power_balance_residual_w"])


if __name__ == "__main__":
    unittest.main()
