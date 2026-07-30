import csv
import json
import sys
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch

if "paho" not in sys.modules:
    paho = types.ModuleType("paho")
    paho_mqtt = types.ModuleType("paho.mqtt")
    paho_client = types.ModuleType("paho.mqtt.client")
    paho_client.CallbackAPIVersion = types.SimpleNamespace(VERSION2=object())
    paho_client.Client = lambda *args, **kwargs: types.SimpleNamespace(
        on_message=None, on_connect=None, on_disconnect=None,
        username_pw_set=lambda *a, **k: None,
        connect=lambda *a, **k: None,
        loop_start=lambda *a, **k: None,
        subscribe=lambda *a, **k: None,
        publish=lambda *a, **k: types.SimpleNamespace(rc=0),
    )
    sys.modules["paho"] = paho
    sys.modules["paho.mqtt"] = paho_mqtt
    sys.modules["paho.mqtt.client"] = paho_client

import status_page_v2
import web_ui
from measurement_v4 import build_v4_row
from measurement_v4_contract import RC15_STANDARD_HEADER, RC16_STANDARD_HEADER, STANDARD_HEADER
from tests.test_v12_11_2_rc10_status_preview import _METRICS
from tests.test_v12_10_rc9_rest_surplus import make
from tests.test_v12_11_1_rc1_high_sma_harvest import cfg_high
from tests.test_v12_10_rc6_cross_charge import state_with_second_battery
from tests.test_operation_priority import OkShelly


class Rc16RcbAbsoluteTargetTests(unittest.TestCase):
    def make_case(self, *, last_input=300, export_w=600, entry_min_export_w=250):
        cfg = cfg_high(
            HARVEST_HIGH_SMA_SOC_MIN_EXPORT_W=entry_min_export_w,
            HARVEST_HIGH_SMA_SOC_TIME_PROFILE_ENABLED=False,
            CONTROL_GAIN=1.0,
            SMOOTHING_FACTOR=1.0,
            MAX_POWER_STEP_W=5000,
            MAX_CHARGE_POWER_W=2400,
        )
        state = state_with_second_battery(+10, soc=100)
        now = 1_800_000_000.0
        with state.lock:
            state.battery_soc = 50
            state.rest_surplus_harvest_active = True
            state.rest_surplus_harvest_reason = "SMA_FULL_OR_IDLE"
            state.last_input_power = last_input
            state.grid_power_valid = True
            state.grid_power_fresh = True
            state.last_shelly_update_epoch = now
            state.effective_export_power = int(export_w)
            state.effective_export_power_valid = True
            state.zendure_power_observation_direction = "CHARGE"
            state.zendure_power_observation_confidence = "HIGH"
            state.zendure_power_observation_signed_w = last_input
            state.zendure_power_observation_updated_epoch = now
            state.actual_zendure_grid_input_update_epoch = now
            state.actual_zendure_output_home_update_epoch = now
        controller, state, mqtt = make(cfg, state=state, shelly=OkShelly(-export_w))
        return controller, state, mqtt, cfg, now

    def test_rc17_full_idle_formula_300_plus_600_is_900(self):
        controller, state, _, cfg, now = self.make_case()
        with patch("controller_logic.time.time", return_value=now):
            result = controller._rest_surplus_charge_pressure_target(cfg, -600, 300)

        self.assertEqual(900, result["target"])
        self.assertEqual("ABSOLUTE_EXPORT_CAPTURE", state.harvest_target_semantics)
        self.assertEqual(300.0, state.harvest_reference_charge_w)
        self.assertEqual("ZENDURE_GRID_PORT_OBSERVATION", state.harvest_reference_charge_source)
        self.assertEqual("HIGH", state.harvest_reference_charge_confidence)
        self.assertTrue(state.harvest_reference_charge_valid)
        self.assertEqual(0.0, state.harvest_profile_reserve_w)
        self.assertEqual(600.0, state.harvest_candidate_delta_w)
        self.assertEqual(900.0, state.harvest_candidate_absolute_w)
        self.assertEqual("EXPORT_CAPTURE", state.harvest_limiter_reason)

    def test_profile_reserve_no_longer_reduces_existing_absolute_target(self):
        controller, state, _, cfg, now = self.make_case(last_input=600, export_w=100, entry_min_export_w=250)
        # An already active SMA_FULL_OR_IDLE episode may remain in hold below
        # the entry threshold. The signed delta must then reduce the absolute
        # target rather than falling back to the historical half-allocation.
        with patch("controller_logic.time.time", return_value=now):
            result = controller._rest_surplus_charge_pressure_target(cfg, -100, 600)
        self.assertEqual(100.0, state.harvest_candidate_delta_w)
        self.assertEqual(700, result["target"])
        self.assertEqual("ABSOLUTE_EXPORT_CAPTURE", state.harvest_target_semantics)
        self.assertEqual(700.0, state.harvest_candidate_absolute_w)

    def test_export_is_fully_added_even_when_equal_to_historical_reserve(self):
        controller, state, _, cfg, now = self.make_case(last_input=600, export_w=250, entry_min_export_w=250)
        with patch("controller_logic.time.time", return_value=now):
            result = controller._rest_surplus_charge_pressure_target(cfg, -250, 600)
        self.assertEqual(250.0, state.harvest_candidate_delta_w)
        self.assertEqual(850, result["target"])
        self.assertEqual(850.0, state.harvest_candidate_absolute_w)

    def test_fresh_neutral_grid_port_is_valid_zero_reference(self):
        controller, state, _, cfg, now = self.make_case(last_input=0)
        with state.lock:
            state.zendure_power_observation_direction = "NEUTRAL"
            state.zendure_power_observation_confidence = "MEDIUM"
            state.zendure_power_observation_signed_w = 0
        with patch("controller_logic.time.time", return_value=now):
            result = controller._rest_surplus_charge_pressure_target(cfg, -600, 0)

        self.assertEqual(600, result["target"])
        self.assertTrue(state.harvest_reference_charge_valid)
        self.assertEqual("ZENDURE_GRID_PORT_NEUTRAL", state.harvest_reference_charge_source)
        self.assertEqual(0.0, state.harvest_reference_charge_w)

    def test_neutral_without_fresh_explicit_grid_topics_uses_fallback(self):
        controller, state, _, cfg, now = self.make_case(last_input=300)
        with state.lock:
            state.zendure_power_observation_direction = "NEUTRAL"
            state.zendure_power_observation_confidence = "MEDIUM"
            state.zendure_power_observation_signed_w = 0
            state.actual_zendure_grid_input_update_epoch = None
            state.actual_zendure_output_home_update_epoch = None
        with patch("controller_logic.time.time", return_value=now):
            result = controller._rest_surplus_charge_pressure_target(cfg, -600, 300)

        self.assertEqual(900, result["target"])
        self.assertEqual("INCREMENTAL_FALLBACK", state.harvest_target_semantics)
        self.assertFalse(state.harvest_reference_charge_valid)
        self.assertEqual("REFERENCE_VALUE_MISSING", state.harvest_reference_fallback_reason)
        self.assertEqual("NONE", state.harvest_reference_charge_source)
        self.assertEqual(0.0, state.harvest_candidate_absolute_w)

    def test_stale_reference_uses_incremental_auto_fallback(self):
        controller, state, _, cfg, now = self.make_case(last_input=300)
        with state.lock:
            state.zendure_power_observation_updated_epoch = now - 16
        with patch("controller_logic.time.time", return_value=now):
            result = controller._rest_surplus_charge_pressure_target(cfg, -600, 300)

        self.assertEqual(900, result["target"])
        self.assertEqual("INCREMENTAL_FALLBACK", state.harvest_target_semantics)
        self.assertEqual("REFERENCE_STALE", state.harvest_reference_fallback_reason)
        self.assertFalse(state.harvest_reference_charge_valid)

    def test_conflict_and_discharge_never_become_charge_reference(self):
        for direction, expected_reason, signed in (
            ("CONFLICT", "REFERENCE_CONFLICT", None),
            ("DISCHARGE", "REFERENCE_DISCHARGE", -400),
        ):
            with self.subTest(direction=direction):
                controller, state, _, cfg, now = self.make_case(last_input=300)
                with state.lock:
                    state.zendure_power_observation_direction = direction
                    state.zendure_power_observation_confidence = "NONE" if direction == "CONFLICT" else "HIGH"
                    state.zendure_power_observation_signed_w = signed
                with patch("controller_logic.time.time", return_value=now):
                    result = controller._rest_surplus_charge_pressure_target(cfg, -600, 300)
                self.assertEqual(900, result["target"])
                self.assertFalse(state.harvest_reference_charge_valid)
                self.assertEqual(expected_reason, state.harvest_reference_fallback_reason)
                self.assertEqual(0.0, state.harvest_reference_charge_w)

    def test_large_input_time_skew_uses_fallback(self):
        controller, state, _, cfg, now = self.make_case(last_input=300)
        with state.lock:
            state.last_shelly_update_epoch = now
            state.zendure_power_observation_updated_epoch = now - 15.1
        # Keep reference age just within a separately patched time origin to
        # isolate the explicit source-skew check.
        with patch("controller_logic.time.time", return_value=now):
            result = controller._rest_surplus_charge_pressure_target(cfg, -600, 300)
        self.assertEqual("INCREMENTAL_FALLBACK", state.harvest_target_semantics)
        self.assertIn(state.harvest_reference_fallback_reason, {"REFERENCE_STALE", "INPUT_TIME_SKEW"})
        self.assertEqual(900, result["target"])

    def test_full_control_pipeline_preserves_smoothing_step_and_single_direction(self):
        controller, state, mqtt, cfg, now = self.make_case(last_input=300)
        # Make the raw grid-port data itself consistent with the already
        # observed 300 W charge. The normal run_once housekeeping recomputes the
        # independent observation before RC-B evaluates it.
        with state.lock:
            current = time.time()
            state.actual_zendure_grid_input_power = 300
            state.actual_zendure_discharge_power = 0
            state.actual_zendure_grid_input_update_epoch = current
            state.actual_zendure_output_home_update_epoch = current
            state.zendure_command_smart_mode = 1
            state.zendure_command_ac_mode = "Input mode"
            state.zendure_command_input_limit_w = 300
            state.zendure_command_output_limit_w = 0
            state.zendure_command_smart_mode_updated_epoch = current
            state.zendure_command_ac_mode_updated_epoch = current
            state.zendure_command_input_limit_updated_epoch = current
            state.zendure_command_output_limit_updated_epoch = current
            state.zendure_command_state_updated_epoch = current
            state.zendure_command_state_complete = True
            state.zendure_flash_protection_active = True
        controller.is_night_discharge_active = lambda _cfg: False
        controller.run_once(cfg)

        self.assertEqual(900, state.last_input_power)
        self.assertEqual(0, state.last_output_power)
        self.assertEqual("ABSOLUTE_EXPORT_CAPTURE", state.harvest_target_semantics)
        self.assertIn(("input", 900, False), mqtt.commands)
        self.assertEqual(0, state.command_ac_mode_change_count)
        self.assertFalse(any(cmd[0] == "ac" and cmd[1] != "Input mode" for cmd in mqtt.commands))
        self.assertFalse(any(cmd[0] == "output" and cmd[1] > 0 for cmd in mqtt.commands))

    def test_existing_max_power_step_still_limits_absolute_target(self):
        controller, state, mqtt, cfg, _ = self.make_case(last_input=300)
        cfg["MAX_POWER_STEP_W"] = 150
        with state.lock:
            current = time.time()
            state.actual_zendure_grid_input_power = 300
            state.actual_zendure_discharge_power = 0
            state.actual_zendure_grid_input_update_epoch = current
            state.actual_zendure_output_home_update_epoch = current
            state.zendure_command_smart_mode = 1
            state.zendure_command_ac_mode = "Input mode"
            state.zendure_command_input_limit_w = 300
            state.zendure_command_output_limit_w = 0
            state.zendure_command_smart_mode_updated_epoch = current
            state.zendure_command_ac_mode_updated_epoch = current
            state.zendure_command_input_limit_updated_epoch = current
            state.zendure_command_output_limit_updated_epoch = current
            state.zendure_command_state_updated_epoch = current
            state.zendure_command_state_complete = True
            state.zendure_flash_protection_active = True
        controller.is_night_discharge_active = lambda _cfg: False
        controller.run_once(cfg)
        self.assertEqual(900.0, state.harvest_candidate_absolute_w)
        self.assertEqual(450, state.last_input_power)
        self.assertIn(("input", 450, False), mqtt.commands)

    def test_existing_charge_cap_still_limits_absolute_target(self):
        controller, state, mqtt, cfg, _ = self.make_case(last_input=1800, export_w=800, entry_min_export_w=150)
        cfg["MAX_CHARGE_POWER_W"] = 2400
        cfg["MAX_POWER_STEP_W"] = 5000
        with state.lock:
            current = time.time()
            state.actual_zendure_grid_input_power = 1800
            state.actual_zendure_discharge_power = 0
            state.actual_zendure_grid_input_update_epoch = current
            state.actual_zendure_output_home_update_epoch = current
            state.zendure_command_smart_mode = 1
            state.zendure_command_ac_mode = "Input mode"
            state.zendure_command_input_limit_w = 1800
            state.zendure_command_output_limit_w = 0
            state.zendure_command_smart_mode_updated_epoch = current
            state.zendure_command_ac_mode_updated_epoch = current
            state.zendure_command_input_limit_updated_epoch = current
            state.zendure_command_output_limit_updated_epoch = current
            state.zendure_command_state_updated_epoch = current
            state.zendure_command_state_complete = True
            state.zendure_flash_protection_active = True
        controller.is_night_discharge_active = lambda _cfg: False
        controller.run_once(cfg)
        self.assertEqual(2600.0, state.harvest_candidate_absolute_w)
        self.assertEqual(2400, state.last_input_power)
        self.assertIn(("input", 2400, False), mqtt.commands)

    def test_product_evidence_fixture_reconstructs_old_and_new_targets(self):
        fixture_dir = Path(__file__).resolve().parent / "fixtures"
        with (fixture_dir / "rc16_expected_sma_full_or_idle.json").open(encoding="utf-8") as f:
            expected = json.load(f)
        with (fixture_dir / "rc10_sma_full_or_idle_underallocation.csv").open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f, delimiter=";"))

        self.assertEqual(expected["rows"], len(rows))
        for row in rows:
            charge = float(row["observed_charge_w"])
            export = float(row["remaining_export_w"])
            reserve = float(row["profile_reserve_w"])
            old = float(row["rc10_target_w"])
            absolute = float(row["rc16_absolute_target_w"])
            self.assertAlmostEqual(export - reserve, old, delta=1.0)
            self.assertAlmostEqual(charge + export - reserve, absolute, delta=1.0)
            self.assertGreaterEqual(absolute, old)
        self.assertAlmostEqual(expected["representative_old_target_w"], float(rows[0]["rc10_target_w"]), delta=1.0)
        self.assertAlmostEqual(expected["representative_new_target_w"], float(rows[0]["rc16_absolute_target_w"]), delta=1.0)

    def test_status_payload_exposes_absolute_harvest_equation(self):
        controller, state, _, cfg, now = self.make_case()
        with patch("controller_logic.time.time", return_value=now):
            controller._rest_surplus_charge_pressure_target(cfg, -600, 300)
        snapshot = state.snapshot()
        snapshot.update({
            "grid_power_valid": True,
            "raw_grid_power": -600,
            "rest_surplus_export_w": 600,
            "second_battery_data_valid": True,
            "second_battery_data_fresh": True,
            "last_cycle_completed_epoch": time.time(),
        })
        with patch("web_ui.get_system_metrics", return_value=_METRICS), patch("web_ui.replay_service_available", return_value=True):
            payload = web_ui.build_status_view_payload(cfg, snapshot, events=[])
        self.assertEqual("0-W-Netzziel: 300 W + 600 W = 900 W", payload["primary"]["harvest_calculation"])
        html = status_page_v2.render_status_page_v2(cfg, payload, analysis_available=True, analysis_port=8090)
        self.assertIn("Harvest-Rechnung", html)
        self.assertIn("0-W-Netzziel: 300 W + 600 W", html)

    def test_rc16_v4_contract_and_row_are_additive(self):
        self.assertEqual(217, len(RC15_STANDARD_HEADER))
        self.assertEqual(228, len(RC16_STANDARD_HEADER))
        self.assertEqual(238, len(STANDARD_HEADER))
        row = build_v4_row(cfg_high(), {
            "mode": "CHARGE",
            "epoch_s": 1_800_000_000.0,
            "cycle_id": 1,
            "harvest_target_semantics": "ABSOLUTE_EXPORT_CAPTURE",
            "harvest_reference_charge_w": 300,
            "harvest_reference_charge_source": "ZENDURE_GRID_PORT_OBSERVATION",
            "harvest_reference_charge_confidence": "HIGH",
            "harvest_reference_charge_age_s": 1.2,
            "harvest_reference_charge_valid": True,
            "harvest_reference_fallback_reason": "",
            "harvest_profile_reserve_w": 0,
            "harvest_candidate_delta_w": 350,
            "harvest_candidate_absolute_w": 650,
            "harvest_input_time_skew_s": 0.8,
        })
        self.assertEqual("ABSOLUTE_EXPORT_CAPTURE", row["harvest_target_semantics"])
        self.assertEqual(300.0, row["harvest_reference_charge_w"])
        self.assertEqual("1", row["harvest_reference_charge_valid"])
        self.assertEqual(350.0, row["harvest_candidate_delta_w"])
        self.assertEqual(650.0, row["harvest_candidate_absolute_w"])
        self.assertEqual(0.8, row["harvest_input_time_skew_s"])


if __name__ == "__main__":
    unittest.main()
