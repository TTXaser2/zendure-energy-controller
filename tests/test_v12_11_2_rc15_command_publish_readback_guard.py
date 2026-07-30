import csv
import json
import time
import unittest
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
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

# Import after test_operation_priority has installed the paho-mqtt stub.
from controller_logic import ZendureController
from measurement_v4 import build_v4_row
from mqtt_bridge import MqttBridge
from state import ControllerState
from tests.test_v12_11_2_rc12_command_contract import SmartRecordingMqtt
from tests.test_measurement_v4_writer import base_config as measurement_base_config, base_row as measurement_base_row


class DummyMsg:
    def __init__(self, topic, payload, retain=False):
        self.topic = topic
        self.payload = str(payload).encode("utf-8")
        self.retain = retain


class PublishClient:
    def __init__(self, rc=0):
        self.rc = rc
        self.calls = []

    def publish(self, topic, value, retain=False):
        self.calls.append((topic, str(value), bool(retain)))
        return SimpleNamespace(rc=self.rc)


class Rc15CommandPublishReadbackGuardTests(unittest.TestCase):
    def make_controller(self, cfg=None, state=None):
        cfg = cfg or base_cfg(
            ZENDURE_COMMAND_STATE_RETRY_SECONDS=30,
            COMMAND_EFFECT_TOLERANCE_W=80,
            COMMAND_NEUTRALIZATION_TIMEOUT_SECONDS=30,
            COMMAND_RESYNC_COOLDOWN_SECONDS=120,
        )
        state = state or fresh_state(80)
        mqtt = SmartRecordingMqtt()
        controller = ZendureController(
            DummyConfigManager(cfg), state, mqtt, OkShelly(0),
            NoopCsv(), NoopZendureApi(), NoopLogger(),
        )
        return controller, state, mqtt, cfg

    @staticmethod
    def set_command_state(state, *, now, smart=1, ac="Output mode", input_limit=0, output_limit=0):
        state.update_zendure_command_property("smartMode", smart, "test", now)
        state.update_zendure_command_property("acMode", ac, "test", now)
        state.update_zendure_command_property("inputLimit", input_limit, "test", now)
        state.update_zendure_command_property("outputLimit", output_limit, "test", now)
        state.update_zendure_command_property("inverseMaxPower", 2000, "MQTT", now)
        state.update_zendure_command_property("chargeMaxLimit", 2400, "test", now)

    @staticmethod
    def set_observation(state, *, epoch, signed, direction, magnitude=None, confidence="HIGH"):
        with state.lock:
            state.zendure_mqtt_overall_status = "ZENDURE_MQTT_OK"
            state.zendure_mqtt_live_confirmed = True
            state.zendure_power_observation_signed_w = signed
            state.zendure_power_observation_magnitude_w = abs(int(signed or 0)) if magnitude is None else int(magnitude)
            state.zendure_power_observation_direction = direction
            state.zendure_power_observation_confidence = confidence
            state.zendure_power_observation_reason = "rc15-test"
            state.zendure_power_observation_updated_epoch = epoch
            state.actual_zendure_power_valid = True
            state.last_zendure_power_update_epoch = epoch

    def prepare_unresolved_discharge(self, controller, state, *, now=None, output_limit=2000):
        now = time.time() if now is None else float(now)
        self.set_command_state(
            state, now=now, smart=1, ac="Output mode", input_limit=0, output_limit=output_limit,
        )
        controller._desired_command_batch = controller._new_command_batch(
            -output_limit, reason="MANUAL_FIXED_DISCHARGE"
        )
        controller._last_non_neutral_ac_mode = "Output mode"
        with state.lock:
            state.last_input_power = 0
            state.last_output_power = output_limit
            state.command_desired_intent = "DISCHARGE"
            state.command_not_effective_active = True
            state.command_not_effective_reason = "produktiver Mismatch"
            state.command_lifecycle_state = "MISMATCH_CONFIRMED"
            state.command_effect_category = "COMMAND_MISMATCH_CONFIRMED"

    def test_state_readback_does_not_overwrite_local_publish_history(self):
        cfg = {"DEVICE_ID": "TEST", "MIN_COMMAND_CHANGE_W": 50, "LOG_MQTT": False, "DEBUG": False}
        state = ControllerState()
        bridge = MqttBridge(state, lambda: cfg, NoopLogger())
        client = PublishClient()
        bridge.client = client
        topic = bridge.topics()["output_limit"]

        self.assertTrue(bridge.set_output_limit(2000))
        self.assertEqual(2000, bridge.last_published_values[topic])
        bridge.on_message(None, None, DummyMsg(bridge.topics()["output_limit_state"], 0))

        self.assertEqual(2000, bridge.last_published_values[topic])
        self.assertEqual(0, bridge.last_device_readback_values[topic])
        self.assertFalse(bridge.set_output_limit(2000))
        self.assertEqual(1, len(client.calls))

    def test_real_rc14_fixture_documents_publish_storm_and_constant_effective_target(self):
        fixture_dir = Path(__file__).resolve().parent / "fixtures"
        with (fixture_dir / "rc15_expected_command_events.json").open(encoding="utf-8") as f:
            expected = json.load(f)
        with (fixture_dir / "rc14_fixed_discharge_failure_20260728.csv").open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f, delimiter=";"))

        self.assertEqual(expected["episode_rows"], len(rows))
        self.assertEqual({"-2000.0"}, {row["target_final_w"] for row in rows})
        self.assertEqual({"29"}, {row["command_desired_sequence_id"] for row in rows})
        self.assertEqual({"2000.0"}, {row["zendure_device_inverse_max_power_w"] for row in rows})
        self.assertGreater(len({row["config_control_hash"] for row in rows}), 1)

        counts = Counter(
            row["command_publish_event"]
            for row in rows
            if row["command_sent_flag"] == "1"
        )
        observed = expected["rc14_observed_publish_counts"]
        self.assertEqual(observed["FULL_STATE_COMMAND_SENT"], counts["FULL_STATE_COMMAND_SENT"])
        self.assertEqual(observed["COMMAND_LIMIT_UPDATED"], counts["COMMAND_LIMIT_UPDATED"])
        self.assertEqual(observed["FULL_STATE_RESYNC_SENT"], counts["FULL_STATE_RESYNC_SENT"])
        self.assertEqual(observed["total"], sum(counts.values()))
        self.assertTrue(expected["inverse_max_power_preexisted_manual_command"])
        self.assertLess(
            expected["first_inverse_max_power_2000_evidence_utc"],
            expected["manual_fixed_discharge_activation_utc"],
        )

    def test_real_rc14_readback_sequence_cannot_retrigger_normal_limit_publish(self):
        fixture = Path(__file__).resolve().parent / "fixtures" / "rc14_fixed_discharge_failure_20260728.csv"
        with fixture.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f, delimiter=";"))

        cfg = {"DEVICE_ID": "TEST", "MIN_COMMAND_CHANGE_W": 50, "LOG_MQTT": False, "DEBUG": False}
        state = ControllerState()
        bridge = MqttBridge(state, lambda: cfg, NoopLogger())
        client = PublishClient()
        bridge.client = client
        self.assertTrue(bridge.set_output_limit(2000))

        for row in rows:
            bridge.on_message(
                None, None,
                DummyMsg(bridge.topics()["output_limit_state"], int(float(row["zendure_command_output_limit_w"] or 0))),
            )
            self.assertFalse(bridge.set_output_limit(2000))

        self.assertEqual(1, len(client.calls))
        self.assertEqual(2000, bridge.last_published_values[bridge.topics()["output_limit"]])

    def test_ac_mode_change_counter_counts_only_real_published_changes(self):
        cfg = {"DEVICE_ID": "TEST", "MIN_COMMAND_CHANGE_W": 50, "LOG_MQTT": False, "DEBUG": False}
        state = ControllerState()
        bridge = MqttBridge(state, lambda: cfg, NoopLogger())
        bridge.client = PublishClient()

        self.assertTrue(bridge.set_ac_mode("Output mode", force=True))
        self.assertEqual(0, state.command_ac_mode_change_count)
        self.assertTrue(bridge.set_ac_mode("Output mode", force=True))
        self.assertEqual(0, state.command_ac_mode_change_count)
        self.assertTrue(bridge.set_ac_mode("Input mode", force=True))
        self.assertEqual(1, state.command_ac_mode_change_count)
        self.assertFalse(bridge.set_ac_mode("Input mode", force=False))
        self.assertEqual(1, state.command_ac_mode_change_count)
        self.assertTrue(bridge.set_ac_mode("Output mode", force=True))
        self.assertEqual(2, state.command_ac_mode_change_count)

    def test_physical_direction_counter_ignores_neutral_but_counts_charge_to_discharge(self):
        controller, state, _, cfg = self.make_controller()
        with state.lock:
            state.command_desired_intent = "IDLE"
            state.last_input_power = 0
            state.last_output_power = 0
        for epoch, signed, direction in (
            (1000.0, 300, "CHARGE"),
            (1001.0, 0, "NEUTRAL"),
            (1002.0, -300, "DISCHARGE"),
        ):
            self.set_observation(state, epoch=epoch, signed=signed, direction=direction)
            with ExitStack() as stack:
                stack.enter_context(patch("controller_logic.time.time", return_value=epoch))
                stack.enter_context(patch("state.time.time", return_value=epoch))
                controller.update_command_effect_monitor(cfg)
        self.assertEqual(1, state.physical_power_direction_change_count)

    def test_explicit_publish_failure_does_not_advance_cache_or_counter(self):
        cfg = {"DEVICE_ID": "TEST", "MIN_COMMAND_CHANGE_W": 50, "LOG_MQTT": False, "DEBUG": False}
        state = ControllerState()
        bridge = MqttBridge(state, lambda: cfg, NoopLogger())
        bridge.client = PublishClient(rc=1)
        topic = bridge.topics()["input_limit"]

        self.assertFalse(bridge.set_input_limit(500))
        self.assertNotIn(topic, bridge.last_published_values)
        self.assertEqual(0, state.mqtt_commands_sent)

    def test_unresolved_discharge_to_charge_enters_guard_without_ac_mode_publish(self):
        controller, state, mqtt, _ = self.make_controller()
        self.prepare_unresolved_discharge(controller, state)
        mqtt.commands.clear()

        applied = controller._publish_signed_target(500, reason="AUTO_GRID_EXPORT")

        self.assertEqual(0, applied)
        self.assertTrue(state.command_late_effect_guard_active)
        self.assertEqual("DISCHARGE", state.command_late_effect_guard_previous_intent)
        self.assertEqual("CHARGE", state.command_late_effect_guard_pending_intent)
        self.assertEqual(500, state.command_late_effect_guard_pending_target_w)
        self.assertEqual(
            [("input", 0, True), ("output", 0, True)],
            mqtt.commands,
        )
        self.assertEqual("MISMATCH_HANDOFF_TO_LATE_EFFECT_GUARD", state.command_mismatch_resolution)
        self.assertEqual("LATE_EFFECT_GUARD_NEUTRALIZATION_SENT", state.command_publish_event)

    def test_unresolved_mismatch_same_direction_does_not_enter_guard(self):
        controller, state, mqtt, _ = self.make_controller()
        self.prepare_unresolved_discharge(controller, state)
        mqtt.commands.clear()

        applied = controller._publish_signed_target(-1500, reason="MANUAL_FIXED_DISCHARGE")

        self.assertEqual(-1500, applied)
        self.assertFalse(state.command_late_effect_guard_active)
        self.assertEqual([("output", 1500, False)], mqtt.commands)

    def test_normal_effective_direction_change_does_not_enter_guard(self):
        controller, state, mqtt, _ = self.make_controller()
        self.set_command_state(state, now=time.time(), ac="Output mode", output_limit=400)
        controller._desired_command_batch = controller._new_command_batch(-400, reason="AUTO_GRID_IMPORT")
        with state.lock:
            state.command_not_effective_active = False
        mqtt.commands.clear()

        applied = controller._publish_signed_target(500, reason="AUTO_GRID_EXPORT")

        self.assertEqual(500, applied)
        self.assertFalse(state.command_late_effect_guard_active)
        self.assertEqual(
            [("ac", "Input mode", True), ("output", 0, True), ("input", 500, True)],
            mqtt.commands,
        )

    def test_guard_does_not_repeat_zero_publish_while_pending_changes(self):
        controller, state, mqtt, _ = self.make_controller()
        self.prepare_unresolved_discharge(controller, state)
        mqtt.commands.clear()
        controller._publish_signed_target(500, reason="AUTO_GRID_EXPORT")
        first = list(mqtt.commands)

        for target in range(550, 1050, 50):
            controller._publish_signed_target(target, reason="AUTO_GRID_EXPORT")

        self.assertEqual(first, mqtt.commands)
        self.assertEqual(1000, state.command_late_effect_guard_pending_target_w)
        self.assertEqual(11, state.command_late_effect_guard_blocked_command_count)

    def _activate_guard_for_release_test(self):
        controller, state, mqtt, cfg = self.make_controller()
        self.prepare_unresolved_discharge(controller, state)
        mqtt.commands.clear()
        with patch("controller_logic.time.monotonic", return_value=100.0):
            controller._publish_signed_target(500, reason="AUTO_GRID_EXPORT")
        with state.lock:
            state.last_input_power = 0
            state.last_output_power = 0
        return controller, state, mqtt, cfg

    def test_guard_release_uses_monotonic_time_and_two_distinct_observations(self):
        controller, state, _, cfg = self._activate_guard_for_release_test()

        for epoch, mono in ((1000.0, 100.0), (1007.0, 107.0)):
            self.set_command_state(state, now=epoch, ac="Output mode", input_limit=0, output_limit=0)
            self.set_observation(state, epoch=epoch, signed=0, direction="NEUTRAL")
            with ExitStack() as stack:
                stack.enter_context(patch("controller_logic.time.time", return_value=epoch))
                stack.enter_context(patch("controller_logic.time.monotonic", return_value=mono))
                stack.enter_context(patch("state.time.time", return_value=epoch))
                controller.update_command_effect_monitor(cfg)

        self.assertFalse(state.command_late_effect_guard_active)
        self.assertEqual("LATE_EFFECT_GUARD_RELEASED", state.command_mismatch_resolution)
        self.assertEqual("COMMAND_NEUTRALIZATION_CONFIRMED", state.command_effect_category)

    def test_identical_telemetry_is_not_counted_twice(self):
        controller, state, _, cfg = self._activate_guard_for_release_test()
        epoch = 1000.0
        self.set_command_state(state, now=epoch, ac="Output mode", input_limit=0, output_limit=0)
        self.set_observation(state, epoch=epoch, signed=0, direction="NEUTRAL")
        for mono in (100.0, 110.0):
            with ExitStack() as stack:
                stack.enter_context(patch("controller_logic.time.time", return_value=epoch + (mono - 100.0)))
                stack.enter_context(patch("controller_logic.time.monotonic", return_value=mono))
                stack.enter_context(patch("state.time.time", return_value=epoch + (mono - 100.0)))
                controller.update_command_effect_monitor(cfg)

        self.assertTrue(state.command_late_effect_guard_active)
        self.assertEqual(1, controller._late_effect_guard_neutral_observation_count)

    def test_thirty_second_interval_releases_after_second_fresh_observation_not_three_cycles(self):
        controller, state, _, cfg = self._activate_guard_for_release_test()
        for epoch, mono in ((1000.0, 100.0), (1030.0, 130.0)):
            self.set_command_state(state, now=epoch, ac="Output mode", input_limit=0, output_limit=0)
            self.set_observation(state, epoch=epoch, signed=0, direction="NEUTRAL")
            with ExitStack() as stack:
                stack.enter_context(patch("controller_logic.time.time", return_value=epoch))
                stack.enter_context(patch("controller_logic.time.monotonic", return_value=mono))
                stack.enter_context(patch("state.time.time", return_value=epoch))
                controller.update_command_effect_monitor(cfg)
        self.assertFalse(state.command_late_effect_guard_active)

    def test_zero_readback_with_old_physical_discharge_keeps_guard_active(self):
        controller, state, _, cfg = self._activate_guard_for_release_test()
        epoch = 1000.0
        self.set_command_state(state, now=epoch, ac="Output mode", input_limit=0, output_limit=0)
        self.set_observation(state, epoch=epoch, signed=-1999, direction="DISCHARGE")
        with patch("controller_logic.time.time", return_value=epoch), patch("controller_logic.time.monotonic", return_value=107.0), patch("state.time.time", return_value=epoch):
            controller.update_command_effect_monitor(cfg)
        self.assertTrue(state.command_late_effect_guard_active)
        self.assertIn("physische Neutralität fehlt", state.command_effect_reason)

    def test_stale_zero_readback_keeps_guard_active(self):
        controller, state, _, cfg = self._activate_guard_for_release_test()
        now = 1100.0
        self.set_command_state(state, now=1000.0, ac="Output mode", input_limit=0, output_limit=0)
        self.set_observation(state, epoch=now, signed=0, direction="NEUTRAL")
        with patch("controller_logic.time.time", return_value=now), patch("controller_logic.time.monotonic", return_value=107.0), patch("state.time.time", return_value=now):
            controller.update_command_effect_monitor(cfg)
        self.assertTrue(state.command_late_effect_guard_active)
        self.assertIn("0/0-Readback", state.command_effect_reason)

    def test_rc15_diagnostics_are_serialized_into_measurement_v4(self):
        row = measurement_base_row()
        row.update({
            "command_readback_matches_desired": False,
            "command_readback_mismatch_fields": "OUTPUT_LIMIT",
            "command_late_effect_guard_active": True,
            "command_late_effect_guard_previous_intent": "DISCHARGE",
            "command_late_effect_guard_pending_intent": "CHARGE",
            "command_late_effect_guard_pending_target_w": 500,
            "command_late_effect_guard_duration_s": 7.2,
            "command_late_effect_guard_reason": "test",
            "command_late_effect_guard_activation_count": 2,
            "command_late_effect_guard_blocked_command_count": 4,
            "command_ac_mode_change_count": 3,
            "physical_power_direction_change_count": 1,
            "zendure_device_inverse_max_power_source": "MQTT",
            "zendure_device_inverse_max_power_age_s": 1.5,
        })
        v4 = build_v4_row(measurement_base_config("/tmp"), row)
        self.assertEqual("0", v4["command_readback_matches_desired"])
        self.assertEqual("OUTPUT_LIMIT", v4["command_readback_mismatch_fields"])
        self.assertEqual("1", v4["command_late_effect_guard_active"])
        self.assertEqual("DISCHARGE", v4["command_late_effect_guard_previous_intent"])
        self.assertEqual("CHARGE", v4["command_late_effect_guard_pending_intent"])
        self.assertEqual(500.0, v4["command_late_effect_guard_pending_target_w"])
        self.assertEqual(2, v4["command_late_effect_guard_activation_count"])
        self.assertEqual(4, v4["command_late_effect_guard_blocked_command_count"])
        self.assertEqual("MQTT", v4["zendure_device_inverse_max_power_source"])
        self.assertEqual(1.5, v4["zendure_device_inverse_max_power_age_s"])

    def test_readback_match_diagnostics_are_separate_from_state_completeness(self):
        controller, state, _, cfg = self.make_controller()
        now = time.time()
        self.set_command_state(state, now=now, ac="Output mode", input_limit=0, output_limit=0)
        controller._desired_command_batch = controller._new_command_batch(-2000, reason="MANUAL_FIXED_DISCHARGE")

        controller._update_command_readback_diagnostics(cfg)

        self.assertTrue(state.zendure_command_state_complete)
        self.assertFalse(state.command_readback_matches_desired)
        self.assertEqual("OUTPUT_LIMIT", state.command_readback_mismatch_fields)
        self.assertEqual("MQTT", state.zendure_device_inverse_max_power_source)


if __name__ == "__main__":
    unittest.main()
