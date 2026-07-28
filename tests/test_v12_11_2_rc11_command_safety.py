import csv
import json
import os
import tempfile
import time
import unittest

from tests.test_operation_priority import (
    DummyConfigManager,
    RecordingMqtt,
    OkShelly,
    NoopCsv,
    NoopZendureApi,
    NoopLogger,
    base_cfg,
    fresh_state,
)
from controller_logic import ZendureController
from state import ControllerState
from zendure_power_observation import derive_zendure_power_observation
from csv_logger import CsvRotatingLogger
import operational_events
from web_ui import build_status_view_payload
from measurement_v4_contract import (
    RC10_STANDARD_HEADER,
    RC11_STANDARD_HEADER,
    RC12_STANDARD_HEADER,
    RC13_STANDARD_HEADER,
    STANDARD_HEADER,
)
from measurement_v4 import build_v4_row
from tests.test_measurement_v4_writer import base_config as measurement_base_config, base_row as measurement_base_row




class Rc11CommandSafetyTests(unittest.TestCase):
    def make_controller(self, cfg=None, state=None, mqtt=None):
        cfg = cfg or base_cfg()
        state = state or fresh_state(80)
        mqtt = mqtt or RecordingMqtt()
        controller = ZendureController(
            DummyConfigManager(cfg), state, mqtt, OkShelly(0),
            NoopCsv(), NoopZendureApi(), NoopLogger(),
        )
        return controller, state, mqtt, cfg

    @staticmethod
    def set_live_observation(state, *, signed=None, magnitude=0, direction="NEUTRAL", confidence="HIGH"):
        with state.lock:
            state.zendure_mqtt_overall_status = "ZENDURE_MQTT_OK"
            state.zendure_mqtt_live_confirmed = True
            state.zendure_power_observation_signed_w = signed
            state.zendure_power_observation_magnitude_w = magnitude
            state.zendure_power_observation_direction = direction
            state.zendure_power_observation_confidence = confidence
            state.zendure_power_observation_reason = "test"
            state.zendure_power_observation_updated_epoch = time.time()
            state.actual_zendure_power_valid = True
            state.last_zendure_power_update_epoch = time.time()

    def test_night_end_neutralization_mismatch_forces_full_zero_batch(self):
        cfg = base_cfg(
            COMMAND_NEUTRALIZATION_TIMEOUT_SECONDS=5,
            COMMAND_RESYNC_COOLDOWN_SECONDS=5,
        )
        state = fresh_state(36)
        with state.lock:
            state.current_mode = "NIGHT_DISCHARGE"
            state.technical_control_path = "NIGHT_MODE -> OUTPUT"
            state.last_output_power = 400
        controller, state, mqtt, cfg = self.make_controller(cfg, state)

        self.assertTrue(controller.neutralize_ended_night_discharge_if_needed())
        self.set_live_observation(
            state, signed=-400, magnitude=400,
            direction="DISCHARGE", confidence="HIGH",
        )
        with state.lock:
            state.command_neutralization_since_epoch = time.time() - 6
        controller._command_effect_last_resend_epoch = 0

        controller.update_command_effect_monitor(cfg)

        self.assertTrue(state.command_not_effective_active)
        self.assertEqual(1, state.command_resync_count)
        self.assertEqual("COMMAND_RECOVERY_VERIFYING", state.command_effect_category)
        self.assertIn(("ac", "Output mode", True), mqtt.commands)
        self.assertIn(("input", 0, True), mqtt.commands)
        self.assertIn(("output", 0, True), mqtt.commands)


    def test_new_neutralization_episode_is_not_blocked_by_previous_active_resync(self):
        cfg = base_cfg(
            COMMAND_NEUTRALIZATION_TIMEOUT_SECONDS=5,
            COMMAND_RESYNC_COOLDOWN_SECONDS=120,
        )
        controller, state, mqtt, cfg = self.make_controller(cfg)
        controller._command_effect_last_resend_epoch = time.time()
        controller._publish_neutralization("NIGHT_WINDOW_ENDED", ac_mode="Output mode")
        self.set_live_observation(state, signed=-400, magnitude=400, direction="DISCHARGE", confidence="HIGH")
        with state.lock:
            state.command_neutralization_since_epoch = time.time() - 6

        controller.update_command_effect_monitor(cfg)

        self.assertEqual(1, state.command_resync_count)
        self.assertEqual("COMMAND_RECOVERY_VERIFYING", state.command_effect_category)

    def test_neutralization_mismatch_resync_does_not_repeat_inside_cooldown(self):
        cfg = base_cfg(
            COMMAND_NEUTRALIZATION_TIMEOUT_SECONDS=5,
            COMMAND_RESYNC_COOLDOWN_SECONDS=120,
        )
        controller, state, mqtt, cfg = self.make_controller(cfg)
        controller._publish_neutralization("NIGHT_WINDOW_ENDED", ac_mode="Output mode")
        self.set_live_observation(state, signed=-400, magnitude=400, direction="DISCHARGE", confidence="HIGH")
        with state.lock:
            state.command_neutralization_since_epoch = time.time() - 6

        controller.update_command_effect_monitor(cfg)
        first_count = state.command_resync_count
        controller.update_command_effect_monitor(cfg)

        self.assertEqual(1, first_count)
        self.assertEqual(first_count, state.command_resync_count)

    def test_neutralization_confirmation_is_separate_from_publish(self):
        cfg = base_cfg(COMMAND_NEUTRALIZATION_TIMEOUT_SECONDS=30)
        controller, state, mqtt, cfg = self.make_controller(cfg)
        controller._publish_neutralization("TEST_STOP", ac_mode="Output mode")
        self.assertFalse(state.command_effect_confirmed)
        self.set_live_observation(state, signed=0, magnitude=0, direction="NEUTRAL", confidence="MEDIUM")

        controller.update_command_effect_monitor(cfg)

        self.assertFalse(state.command_neutralization_active)
        self.assertEqual("COMMAND_NEUTRALIZATION_CONFIRMED", state.command_effect_category)
        self.assertTrue(state.command_effect_confirmed)
        self.assertNotEqual("-", state.command_effect_confirmed_time)

    def test_small_same_direction_target_changes_do_not_reset_intent_timer(self):
        cfg = base_cfg(
            COMMAND_EFFECT_TIMEOUT_SECONDS=10,
            COMMAND_EFFECT_FORCE_RESEND_SECONDS=999,
        )
        controller, state, mqtt, cfg = self.make_controller(cfg)
        with state.lock:
            state.last_input_power = 2397
            state.last_output_power = 0
        controller._command_effect_watch_intent = "CHARGE"
        controller._command_effect_watch_target = 120
        controller._command_effect_watch_start_epoch = time.time() - 20
        self.set_live_observation(state, signed=0, magnitude=0, direction="NEUTRAL", confidence="MEDIUM")

        controller.update_command_effect_monitor(cfg)

        self.assertTrue(state.command_not_effective_active)
        self.assertEqual("COMMAND_MISMATCH_CONFIRMED", state.command_effect_category)
        self.assertIn("+2397 W", state.command_not_effective_reason)

    def test_partial_effect_is_not_full_tracking(self):
        cfg = base_cfg(
            COMMAND_EFFECT_TIMEOUT_SECONDS=10,
            COMMAND_EFFECT_FORCE_RESEND_SECONDS=999,
            COMMAND_EFFECT_MIN_W=80,
            COMMAND_EFFECT_TOLERANCE_W=80,
        )
        controller, state, mqtt, cfg = self.make_controller(cfg)
        with state.lock:
            state.last_input_power = 2397
            state.last_output_power = 0
        controller._command_effect_watch_intent = "CHARGE"
        controller._command_effect_watch_target = 2397
        controller._command_effect_watch_start_epoch = time.time() - 20
        controller._command_tracking_mismatch_start_epoch = time.time() - 20
        self.set_live_observation(state, signed=100, magnitude=100, direction="CHARGE", confidence="HIGH")

        controller.update_command_effect_monitor(cfg)

        self.assertTrue(state.command_not_effective_active)
        self.assertEqual("COMMAND_MISMATCH_CONFIRMED", state.command_effect_category)

    def test_below_diagnostic_threshold_is_not_effective(self):
        cfg = base_cfg(COMMAND_EFFECT_MIN_TARGET_W=120)
        controller, state, mqtt, cfg = self.make_controller(cfg)
        with state.lock:
            state.last_input_power = 108
            state.last_output_power = 0
        self.set_live_observation(state, signed=0, magnitude=0, direction="NEUTRAL", confidence="MEDIUM")

        controller.update_command_effect_monitor(cfg)

        self.assertEqual("COMMAND_BELOW_DIAGNOSTIC_THRESHOLD", state.command_effect_category)
        self.assertFalse(state.command_effect_confirmed)
        self.assertFalse(state.command_not_effective_active)

    def test_pack_input_alone_is_battery_discharge_but_grid_side_neutral(self):
        obs = derive_zendure_power_observation(pack_input=399)
        self.assertEqual("NEUTRAL", obs["direction"])
        self.assertEqual("MEDIUM", obs["confidence"])
        self.assertEqual(0, obs["signed_power_w"])
        self.assertEqual(0, obs["magnitude_w"])
        self.assertEqual("DISCHARGE", obs["battery_direction"])
        self.assertEqual(-399, obs["battery_signed_power_w"])

    def test_explicit_sensor_direction_wins_without_using_target(self):
        charging = derive_zendure_power_observation(pack_input=390, grid_input=380)
        discharging = derive_zendure_power_observation(pack_input=390, output_home=400)
        self.assertEqual(380, charging["signed_power_w"])
        self.assertEqual(-400, discharging["signed_power_w"])
        self.assertEqual("HIGH", charging["confidence"])
        self.assertEqual("HIGH", discharging["confidence"])


    def test_identical_desired_state_keeps_sequence_id_across_repeated_publish_attempts(self):
        controller, state, mqtt, cfg = self.make_controller()
        controller._publish_signed_target(400, reason="AUTO_CHARGE")
        first_sequence = state.command_desired_sequence_id
        controller._publish_signed_target(400, reason="AUTO_CHARGE")
        self.assertEqual(first_sequence, state.command_desired_sequence_id)
        self.assertEqual("COMMAND_BATCH_PUBLISHED", state.command_publish_event)

    def test_repeated_same_neutral_episode_is_not_force_sent_each_cycle(self):
        controller, state, mqtt, cfg = self.make_controller()
        controller._publish_signed_target(0, force_zero=True, reason="CROSS_CHARGE_NEUTRALIZATION")
        controller._publish_signed_target(0, force_zero=True, reason="CROSS_CHARGE_NEUTRALIZATION")

        first = mqtt.commands[:3]
        second = mqtt.commands[3:]
        self.assertTrue(all(item[2] is True for item in first))
        self.assertTrue(all(item[2] is False for item in second))




    def test_graph_row_keeps_recovery_state_separate_from_publish_event(self):
        state = ControllerState()
        with state.lock:
            state.command_effect_category = "COMMAND_RECOVERY_VERIFYING"
            state.command_effect_reason = "Full-State-Kommandoabgleich ausgeführt; Wirkung offen."
            state.command_lifecycle_state = "RECOVERY_VERIFYING"
            state.command_not_effective_active = True
            state.command_not_effective_reason = "vorher bestätigter Mismatch"
            state.command_publish_event = "FULL_STATE_RESYNC_SENT"
            state.mqtt_command_path_used_for_control = True
            state.mqtt_commands_sent = 3
        state.record_graph_point(10)
        row = state.graph_history[-1]
        self.assertEqual("COMMAND_RECOVERY_VERIFYING", row["command_effect_category"])
        self.assertEqual("COMMAND_RECOVERY_VERIFYING", row["command_effect_state_category"])
        self.assertEqual("FULL_STATE_RESYNC_SENT", row["command_publish_event"])
        self.assertTrue(row["command_not_effective_active"])

    def test_open_mismatch_prevents_system_ok_and_is_journaled_until_recovery(self):
        state = ControllerState()
        snap = state.snapshot()
        snap.update({
            "grid_power_valid": True,
            "raw_grid_power": 0,
            "second_battery_data_valid": True,
            "command_not_effective_active": True,
            "command_effect_category": "COMMAND_MISMATCH_CONFIRMED",
            "command_effect_state_category": "COMMAND_MISMATCH_CONFIRMED",
            "command_not_effective_reason": "Soll +2397 W, Ist +0 W",
        })
        payload = build_status_view_payload({"MEASUREMENT_DB_ENABLED": False}, snap, events=[])
        self.assertNotEqual("System OK", payload["system"]["label"])
        self.assertIn("Zendure-Sollwert zeigt keine plausible Gerätewirkung", payload["system"]["warnings"])

        with tempfile.TemporaryDirectory() as tmp:
            cfg = {"OPERATIONAL_EVENTS_DB_PATH": os.path.join(tmp, "events.sqlite3")}
            journal = operational_events.OperationalEventJournal(lambda: cfg, state)
            conn = journal._connect()
            journal._previous["command_effect"] = "COMMAND_IDLE"
            journal._observe(conn, snap)
            open_row = conn.execute(
                "SELECT title,status FROM operational_events WHERE event_type='command_effect' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            self.assertEqual(("Zendure-Kommando nicht wirksam", "open"), open_row)

            uncertain = dict(snap)
            uncertain.update({
                "command_effect_category": "COMMAND_TELEMETRY_UNCERTAIN",
                "command_effect_state_category": "COMMAND_TELEMETRY_UNCERTAIN",
                "command_not_effective_active": True,
            })
            journal._observe(conn, uncertain)
            still_open = conn.execute(
                "SELECT status FROM operational_events WHERE event_type='command_effect' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            self.assertEqual(("open",), still_open)

            recovered = dict(snap)
            recovered.update({
                "command_not_effective_active": False,
                "command_effect_category": "COMMAND_TARGET_TRACKING_EFFECTIVE",
                "command_effect_state_category": "COMMAND_TARGET_TRACKING_EFFECTIVE",
                "command_effect_reason": "Sollwerttracking bestätigt",
            })
            journal._observe(conn, recovered)
            resolved = conn.execute(
                "SELECT title,status FROM operational_events WHERE event_type='command_effect' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            conn.close()
            self.assertEqual(("Zendure-Kommandowirkung wiederhergestellt", "resolved"), resolved)

    def test_offgrid_or_battery_discharge_does_not_confirm_grid_discharge(self):
        cfg = base_cfg(COMMAND_EFFECT_TIMEOUT_SECONDS=10, COMMAND_EFFECT_FORCE_RESEND_SECONDS=999)
        controller, state, mqtt, cfg = self.make_controller(cfg)
        with state.lock:
            state.last_output_power = 400
            state.last_input_power = 0
            state.update_zendure_headunit_power("MQTT", pack_input=399)
            state.zendure_mqtt_overall_status = "ZENDURE_MQTT_OK"
            state.zendure_mqtt_live_confirmed = True
        controller._command_effect_watch_intent = "DISCHARGE"
        controller._command_effect_watch_target = -400
        controller._command_effect_watch_start_epoch = time.time() - 120

        controller.update_command_effect_monitor(cfg)

        self.assertEqual("COMMAND_MISMATCH_CONFIRMED", state.command_effect_category)
        self.assertTrue(state.command_not_effective_active)
        self.assertFalse(state.command_effect_confirmed)
        self.assertEqual(0, state.command_resync_count)

    def test_stale_grid_sensor_keeps_grid_neutral_while_pack_discharge_stays_separate(self):
        state = ControllerState()
        now = time.time()
        with state.lock:
            state.actual_zendure_charge_power = 399
            state.actual_zendure_pack_input_update_epoch = now
            state.actual_zendure_grid_input_power = 500
            state.actual_zendure_grid_input_update_epoch = now - 60
            state._refresh_zendure_headunit_power_locked(now=now)
        self.assertEqual("NEUTRAL", state.zendure_power_observation_direction)
        self.assertEqual(0, state.zendure_power_observation_signed_w)
        self.assertEqual(0, state.zendure_power_observation_magnitude_w)
        self.assertEqual(-399, state.zendure_battery_signed_power_w)

    def test_observation_age_uses_direction_evidence_timestamp(self):
        state = ControllerState()
        now = time.time()
        with state.lock:
            state.actual_zendure_charge_power = 500
            state.actual_zendure_pack_input_update_epoch = now
            state.actual_zendure_grid_input_power = 480
            state.actual_zendure_grid_input_update_epoch = now - 10
            state._refresh_zendure_headunit_power_locked(now=now)
        self.assertEqual("CHARGE", state.zendure_power_observation_direction)
        self.assertAlmostEqual(now - 10, state.zendure_power_observation_updated_epoch, places=3)


    def test_cycle_refresh_does_not_make_old_power_observation_fresh_again(self):
        state = ControllerState()
        state.update_zendure_headunit_power("MQTT", grid_input=500)
        original_epoch = state.zendure_power_observation_updated_epoch
        with state.lock:
            state._refresh_zendure_headunit_power_locked(now=float(original_epoch) + 5)
        self.assertEqual(original_epoch, state.zendure_power_observation_updated_epoch)


    def test_v4_records_raw_power_observation_and_command_lifecycle_separately(self):
        row = measurement_base_row()
        row.update({
            "zendure_raw_pack_input_power_w": 399,
            "zendure_raw_grid_input_power_w": 0,
            "zendure_raw_output_home_power_w": 0,
            "zendure_raw_output_pack_power_w": 0,
            "zendure_power_observation_direction": "AMBIGUOUS",
            "zendure_power_observation_confidence": "NONE",
            "zendure_power_observation_signed_w": None,
            "zendure_power_observation_magnitude_w": 399,
            "zendure_power_observation_age_s": 1.2,
            "zendure_power_observation_reason": "Nur packInputPower ist relevant.",
            "command_lifecycle_state": "RECOVERY_VERIFYING",
            "command_desired_sequence_id": 42,
            "command_desired_intent": "NEUTRALIZE",
            "command_desired_ac_mode": "Output mode",
            "command_desired_input_limit_w": 0,
            "command_desired_output_limit_w": 0,
            "command_desired_signed_target_w": 0,
            "command_desired_reason": "NIGHT_WINDOW_ENDED",
            "command_desired_safety_relevant": True,
            "command_publish_event": "FULL_STATE_RESYNC_SENT",
            "command_publish_fields": "ac_mode,input_limit_w,output_limit_w",
            "command_effect_category": "COMMAND_RECOVERY_VERIFYING",
            "command_effect_confirmed": False,
            "command_neutralization_active": True,
            "command_neutralization_reason": "NIGHT_WINDOW_ENDED",
        })
        v4 = build_v4_row(measurement_base_config("/tmp"), row)
        self.assertEqual(399.0, v4["zendure_raw_pack_input_w"])
        self.assertEqual("AMBIGUOUS", v4["zendure_power_observation_direction"])
        self.assertEqual("", v4["zendure_power_observation_signed_w"])
        self.assertEqual(42, v4["command_desired_sequence_id"])
        self.assertEqual("NIGHT_WINDOW_ENDED", v4["command_desired_reason"])
        self.assertEqual("1", v4["command_desired_safety_relevant"])
        self.assertEqual("FULL_STATE_RESYNC_SENT", v4["command_publish_event"])
        self.assertEqual("ac_mode,input_limit_w,output_limit_w", v4["command_publish_fields"])
        self.assertEqual("COMMAND_RECOVERY_VERIFYING", v4["command_effect_category"])
        self.assertEqual("0", v4["command_effect_confirmed"])

    def test_battery_only_flow_does_not_resolve_an_existing_grid_mismatch(self):
        cfg = base_cfg(COMMAND_EFFECT_TIMEOUT_SECONDS=10, COMMAND_EFFECT_FORCE_RESEND_SECONDS=999)
        controller, state, mqtt, cfg = self.make_controller(cfg)
        with state.lock:
            state.last_input_power = 1200
            state.command_not_effective_active = True
            state.command_not_effective_reason = "vorher bestätigter Mismatch"
            state.command_not_effective_since_epoch = time.time() - 60
            state.add_limiter("COMMAND_NOT_EFFECTIVE")
            state.update_zendure_headunit_power("MQTT", pack_input=399)
            state.zendure_mqtt_overall_status = "ZENDURE_MQTT_OK"
            state.zendure_mqtt_live_confirmed = True
        controller._command_effect_watch_intent = "CHARGE"
        controller._command_effect_watch_target = 1200
        controller._command_effect_watch_start_epoch = time.time() - 60

        controller.update_command_effect_monitor(cfg)

        self.assertEqual("COMMAND_MISMATCH_CONFIRMED", state.command_effect_category)
        self.assertTrue(state.command_not_effective_active)
        self.assertIn("+1200 W", state.command_not_effective_reason)
        self.assertIn("COMMAND_NOT_EFFECTIVE", state.active_limiters)

    def test_repeated_identical_deduped_batch_keeps_effect_confirmation(self):
        controller, state, mqtt, cfg = self.make_controller()
        controller._publish_signed_target(400, reason="AUTO_CHARGE")
        with state.lock:
            state.command_effect_confirmed = True
            state.command_effect_confirmed_time = "12:34:56"
        controller._publish_signed_target(400, reason="AUTO_CHARGE")

        self.assertTrue(state.command_effect_confirmed)
        self.assertEqual("12:34:56", state.command_effect_confirmed_time)


    def test_custom_rc10_measurement_file_is_preserved_and_rc14_uses_new_session_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_path = os.path.join(tmp, "custom_measurements.csv")
            with open(old_path, "w", encoding="utf-8", newline="") as f:
                f.write(";".join(RC10_STANDARD_HEADER) + "\n")
                f.write(";".join(["4"] + [""] * (len(RC10_STANDARD_HEADER) - 1)) + "\n")
            cfg = measurement_base_config(tmp)
            cfg["MEASUREMENT_LOG_FILE"] = "custom_measurements.csv"
            logger = CsvRotatingLogger()
            status = logger.log(cfg, measurement_base_row())
            logger.close()

            self.assertEqual("active", status["measurement_log_status"])
            self.assertTrue(os.path.exists(old_path))
            new_files = [
                name for name in os.listdir(tmp)
                if name.startswith("custom_measurements_schema_rc14_") and name.endswith(".csv")
            ]
            self.assertEqual(1, len(new_files))
            with open(os.path.join(tmp, new_files[0]), encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f, delimiter=";"))
            self.assertEqual(STANDARD_HEADER, list(rows[0].keys()))
            self.assertEqual(1, len(rows))
            with open(os.path.join(tmp, "zec_runtime_events.jsonl"), encoding="utf-8") as f:
                events = [json.loads(line) for line in f if line.strip()]
            self.assertTrue(any(e.get("rotation_reason") == "HEADER_CHANGED" for e in events))

    def test_custom_rc11_measurement_file_is_preserved_and_rc14_uses_new_session_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_path = os.path.join(tmp, "custom_rc11_measurements.csv")
            with open(old_path, "w", encoding="utf-8", newline="") as f:
                f.write(";".join(RC11_STANDARD_HEADER) + "\n")
                f.write(";".join(["4"] + [""] * (len(RC11_STANDARD_HEADER) - 1)) + "\n")
            cfg = measurement_base_config(tmp)
            cfg["MEASUREMENT_LOG_FILE"] = "custom_rc11_measurements.csv"
            logger = CsvRotatingLogger()
            status = logger.log(cfg, measurement_base_row())
            logger.close()

            self.assertEqual("active", status["measurement_log_status"])
            self.assertTrue(os.path.exists(old_path))
            new_files = [
                name for name in os.listdir(tmp)
                if name.startswith("custom_rc11_measurements_schema_rc14_") and name.endswith(".csv")
            ]
            self.assertEqual(1, len(new_files))
            with open(os.path.join(tmp, new_files[0]), encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f, delimiter=";"))
            self.assertEqual(STANDARD_HEADER, list(rows[0].keys()))
            self.assertEqual(1, len(rows))


    def test_custom_rc12_measurement_file_is_preserved_and_rc14_uses_new_session_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_path = os.path.join(tmp, "custom_rc12_measurements.csv")
            with open(old_path, "w", encoding="utf-8", newline="") as f:
                f.write(";".join(RC12_STANDARD_HEADER) + "\n")
                f.write(";".join(["4"] + [""] * (len(RC12_STANDARD_HEADER) - 1)) + "\n")
            cfg = measurement_base_config(tmp)
            cfg["MEASUREMENT_LOG_FILE"] = "custom_rc12_measurements.csv"
            logger = CsvRotatingLogger()
            status = logger.log(cfg, measurement_base_row())
            logger.close()

            self.assertEqual("active", status["measurement_log_status"])
            self.assertTrue(os.path.exists(old_path))
            new_files = [
                name for name in os.listdir(tmp)
                if name.startswith("custom_rc12_measurements_schema_rc14_") and name.endswith(".csv")
            ]
            self.assertEqual(1, len(new_files))
            with open(os.path.join(tmp, new_files[0]), encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f, delimiter=";"))
            self.assertEqual(STANDARD_HEADER, list(rows[0].keys()))
            self.assertEqual(1, len(rows))

    def test_custom_rc13_measurement_file_is_preserved_and_rc14_uses_new_session_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_path = os.path.join(tmp, "custom_rc13_measurements.csv")
            with open(old_path, "w", encoding="utf-8", newline="") as f:
                f.write(";".join(RC13_STANDARD_HEADER) + "\n")
                f.write(";".join(["4"] + [""] * (len(RC13_STANDARD_HEADER) - 1)) + "\n")
            cfg = measurement_base_config(tmp)
            cfg["MEASUREMENT_LOG_FILE"] = "custom_rc13_measurements.csv"
            logger = CsvRotatingLogger()
            status = logger.log(cfg, measurement_base_row())
            logger.close()

            self.assertEqual("active", status["measurement_log_status"])
            self.assertTrue(os.path.exists(old_path))
            new_files = [
                name for name in os.listdir(tmp)
                if name.startswith("custom_rc13_measurements_schema_rc14_") and name.endswith(".csv")
            ]
            self.assertEqual(1, len(new_files))
            with open(os.path.join(tmp, new_files[0]), encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f, delimiter=";"))
            self.assertEqual(STANDARD_HEADER, list(rows[0].keys()))
            self.assertEqual(1, len(rows))

    def test_force_resend_zero_includes_mode_and_both_limits(self):
        controller, state, mqtt, cfg = self.make_controller()
        controller._publish_neutralization("TEST_ZERO", ac_mode="Output mode")
        mqtt.commands.clear()

        controller._force_resend_signed_target(0, "RESYNC_AFTER_NEUTRALIZATION_MISMATCH")

        self.assertEqual(
            [("ac", "Output mode", True), ("input", 0, True), ("output", 0, True)],
            mqtt.commands,
        )
        self.assertEqual("COMMAND_RECOVERY_VERIFYING", state.command_effect_category)
        self.assertFalse(state.command_effect_confirmed)


if __name__ == "__main__":
    unittest.main()
