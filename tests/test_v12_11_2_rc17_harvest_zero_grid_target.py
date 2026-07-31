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

from command_lifecycle import COMMAND_GATE_READY
from measurement_v4 import build_v4_row
from measurement_v4_contract import RC16_STANDARD_HEADER, STANDARD_HEADER
from tests.test_operation_priority import OkShelly
from tests.test_v12_10_rc6_cross_charge import state_with_second_battery
from tests.test_v12_10_rc9_rest_surplus import make
from tests.test_v12_11_1_rc1_high_sma_harvest import cfg_high


class Rc17HarvestZeroGridTargetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = Path(__file__).resolve().parent / "fixtures" / "rc17_harvest_branch_matrix.json"
        cls.matrix = json.loads(fixture.read_text(encoding="utf-8"))

    def make_case(
        self,
        reason,
        *,
        sma_w,
        zendure_w,
        export_w,
        share=0.50,
        last_input=None,
        reference_direction="CHARGE",
        reference_confidence="HIGH",
        reference_signed=None,
        reference_fresh=True,
        **overrides,
    ):
        cfg = cfg_high(
            HARVEST_HIGH_SMA_SOC_TIME_PROFILE_ENABLED=False,
            HARVEST_PRIMARY_CHARGE_TARGET_SHARE_MIDDAY=share,
            HARVEST_HIGH_SMA_SOC_MIN_EXPORT_W=300,
            CONTROL_GAIN=overrides.pop("CONTROL_GAIN", 0.30),
            SMOOTHING_FACTOR=1.0,
            MAX_POWER_STEP_W=5000,
            MAX_CHARGE_POWER_W=2400,
            **overrides,
        )
        state = state_with_second_battery(sma_w, soc=100 if reason == "SMA_FULL_OR_IDLE" else 80)
        now = 1_800_000_000.0
        with state.lock:
            state.battery_soc = 50
            state.rest_surplus_harvest_active = True
            state.rest_surplus_harvest_reason = reason
            state.last_input_power = zendure_w if last_input is None else last_input
            state.grid_power_valid = True
            state.grid_power_fresh = True
            state.last_shelly_update_epoch = now
            state.effective_export_power = export_w
            state.effective_export_power_valid = True
            state.zendure_power_observation_direction = reference_direction
            state.zendure_power_observation_confidence = reference_confidence
            state.zendure_power_observation_signed_w = zendure_w if reference_signed is None else reference_signed
            state.zendure_power_observation_updated_epoch = now if reference_fresh else now - 16
            state.actual_zendure_grid_input_update_epoch = now
            state.actual_zendure_output_home_update_epoch = now
            state.mqtt_connected = True
            state.mqtt_command_path_valid = True
            state.mqtt_command_path_validity_reason = "OK"
            state.zendure_flash_protection_active = True
            state.zendure_command_state_complete = True
            state.command_state_gate_state = COMMAND_GATE_READY
        controller, state, mqtt = make(cfg, state=state, shelly=OkShelly(-export_w))
        return controller, state, mqtt, cfg, now

    def calculate(self, controller, state, cfg, now, export_w):
        with patch("controller_logic.time.time", return_value=now):
            return controller._rest_surplus_charge_pressure_target(
                cfg, -export_w, int(state.last_input_power or 0)
            )

    def test_near_limit_is_absolute_export_capture(self):
        case = self.matrix["near_limit"]
        controller, state, _, cfg, now = self.make_case(
            "SMA_NEAR_LIMIT", sma_w=case["sma_w"], zendure_w=case["zendure_w"], export_w=case["export_w"]
        )
        result = self.calculate(controller, state, cfg, now, case["export_w"])
        self.assertEqual(case["expected_target_w"], result["target"])
        self.assertEqual("ABSOLUTE_EXPORT_CAPTURE", state.harvest_target_semantics)
        self.assertEqual("EXPORT_CAPTURE", state.harvest_target_selected_by)
        self.assertEqual(case["expected_target_w"], state.harvest_export_capture_target_w)
        self.assertEqual(0.0, state.harvest_network_target_w)

    def test_high_soc_strategic_share_can_exceed_capture(self):
        case = self.matrix["high_share_wins"]
        controller, state, _, cfg, now = self.make_case(
            "HIGH_SMA_SOC", sma_w=case["sma_w"], zendure_w=case["zendure_w"],
            export_w=case["export_w"], share=case["share"]
        )
        result = self.calculate(controller, state, cfg, now, case["export_w"])
        self.assertEqual(case["expected_target_w"], result["target"])
        self.assertEqual(case["expected_primary_w"], state.harvest_primary_share_target_w)
        self.assertEqual("STRATEGIC_SHARE", state.harvest_target_selected_by)
        self.assertEqual("ABSOLUTE_SHARE_OR_EXPORT_CAPTURE", state.harvest_target_semantics)

    def test_high_soc_export_capture_is_hard_lower_bound(self):
        case = self.matrix["high_capture_wins"]
        controller, state, _, cfg, now = self.make_case(
            "HIGH_SMA_SOC", sma_w=case["sma_w"], zendure_w=case["zendure_w"],
            export_w=case["export_w"], share=case["share"]
        )
        result = self.calculate(controller, state, cfg, now, case["export_w"])
        self.assertEqual(case["expected_share_w"], state.harvest_zendure_share_target_w)
        self.assertEqual(case["expected_capture_w"], state.harvest_export_capture_target_w)
        self.assertEqual(case["expected_target_w"], result["target"])
        self.assertEqual("EXPORT_CAPTURE", state.harvest_target_selected_by)

    def test_combined_near_limit_cannot_be_cut_by_share_or_floor(self):
        case = self.matrix["high_capture_wins"]
        controller, state, _, cfg, now = self.make_case(
            "HIGH_SMA_SOC_SMA_NEAR_LIMIT", sma_w=case["sma_w"], zendure_w=case["zendure_w"],
            export_w=case["export_w"], share=case["share"], HARVEST_PRIMARY_CHARGE_FLOOR_W=1700
        )
        result = self.calculate(controller, state, cfg, now, case["export_w"])
        self.assertGreaterEqual(result["target"], state.harvest_export_capture_target_w)
        self.assertEqual(case["expected_capture_w"], result["target"])

    def test_sma_share_is_clamped_to_configured_maximum(self):
        case = self.matrix["sma_max_clamp"]
        controller, state, _, cfg, now = self.make_case(
            "HIGH_SMA_SOC", sma_w=2300, zendure_w=1200, export_w=1000,
            share=case["share"], SECOND_BATTERY_MAX_CHARGE_POWER_W=case["sma_max_w"]
        )
        self.calculate(controller, state, cfg, now, 1000)
        self.assertEqual(case["expected_primary_w"], state.harvest_primary_share_target_w)
        self.assertEqual(case["expected_zendure_share_w"], state.harvest_zendure_share_target_w)
        self.assertEqual(2700.0, state.harvest_primary_share_reserve_w)

    def test_full_idle_uses_c_plus_e_without_profile_reserve(self):
        case = self.matrix["full_idle"]
        controller, state, _, cfg, now = self.make_case(
            "SMA_FULL_OR_IDLE", sma_w=10, zendure_w=case["zendure_w"], export_w=case["export_w"]
        )
        result = self.calculate(controller, state, cfg, now, case["export_w"])
        self.assertEqual(case["expected_target_w"], result["target"])
        self.assertEqual(0.0, state.harvest_profile_reserve_w)
        self.assertEqual(case["export_w"], state.harvest_candidate_delta_w)
        self.assertEqual(case["expected_target_w"], state.harvest_candidate_absolute_w)

    def test_fresh_neutral_reference_captures_complete_export(self):
        controller, state, _, cfg, now = self.make_case(
            "SMA_FULL_OR_IDLE", sma_w=10, zendure_w=0, export_w=600,
            reference_direction="NEUTRAL", reference_confidence="MEDIUM", reference_signed=0
        )
        result = self.calculate(controller, state, cfg, now, 600)
        self.assertEqual(600, result["target"])
        self.assertTrue(state.harvest_reference_charge_valid)
        self.assertEqual("ZENDURE_GRID_PORT_NEUTRAL", state.harvest_reference_charge_source)

    def test_uncertain_reference_uses_incremental_fallback_without_false_absolute_value(self):
        case = self.matrix["fallback"]
        controller, state, _, cfg, now = self.make_case(
            "HIGH_SMA_SOC", sma_w=2000, zendure_w=1500, export_w=case["export_w"],
            last_input=case["last_input_w"], reference_direction="UNKNOWN",
            reference_confidence="NONE", reference_signed=None, CONTROL_GAIN=case["gain"]
        )
        result = self.calculate(controller, state, cfg, now, case["export_w"])
        self.assertEqual(case["expected_target_w"], result["target"])
        self.assertEqual("INCREMENTAL_FALLBACK", state.harvest_target_semantics)
        self.assertEqual("INCREMENTAL_FALLBACK", state.harvest_target_selected_by)
        self.assertFalse(state.harvest_reference_charge_valid)
        self.assertEqual(0.0, state.harvest_candidate_absolute_w)
        self.assertEqual(0.0, state.harvest_total_available_charge_w)

    def test_command_path_readiness_is_diagnostic_not_a_second_gate(self):
        controller, state, _, cfg, now = self.make_case(
            "SMA_FULL_OR_IDLE", sma_w=10, zendure_w=300, export_w=600
        )
        with state.lock:
            state.mqtt_connected = False
            state.mqtt_command_path_valid = False
            state.zendure_flash_protection_active = False
            state.zendure_command_state_complete = False
            state.command_state_gate_state = "UNPROTECTED"
        result = self.calculate(controller, state, cfg, now, 600)
        self.assertEqual(900, result["target"])
        self.assertFalse(state.harvest_command_path_eligible)
        self.assertEqual("MQTT_DISCONNECTED", state.harvest_command_path_block_reason)

    def test_hold_without_origin_uses_export_capture(self):
        controller, state, _, cfg, now = self.make_case(
            "EXPORT_HOLD", sma_w=500, zendure_w=600, export_w=100
        )
        result = self.calculate(controller, state, cfg, now, 100)
        self.assertEqual(700, result["target"])
        self.assertEqual("EXPORT_HOLD_EXPORT_CAPTURE", state.harvest_calculation_branch)
        self.assertEqual("EXPORT_CAPTURE", state.harvest_target_selected_by)

    def test_hold_expiry_semantics_remain_primary_band_limit(self):
        cfg = cfg_high(HARVEST_HIGH_SMA_SOC_HOLD_SECONDS=3)
        state = state_with_second_battery(0, soc=80)
        with state.lock:
            state.battery_soc = 50
            state.rest_surplus_harvest_active = True
            state.rest_surplus_harvest_reason = "HIGH_SMA_SOC"
            state.rest_surplus_hold_remaining_s = 0
        controller, state, _ = make(cfg, state=state, shelly=OkShelly(0))
        controller.update_rest_surplus_harvest_state(cfg, 0)
        self.assertTrue(state.rest_surplus_harvest_active)
        self.assertEqual("HIGH_SMA_SOC", state.rest_surplus_harvest_reason)
        self.assertEqual("PRIMARY_BAND_LIMIT", state.rest_surplus_harvest_block_reason)

    def test_all_time_profiles_have_zero_operational_reserve(self):
        controller, _, _, cfg, _ = self.make_case(
            "HIGH_SMA_SOC", sma_w=2000, zendure_w=500, export_w=300
        )
        for minutes, expected_name, expected_share, expected_entry in (
            (10 * 60, "morning", 0.60, 60),
            (12 * 60, "midday", 0.50, 30),
            (15 * 60, "afternoon", 0.35, 15),
            (20 * 60, "default", 0.50, cfg["HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_SECONDS"]),
        ):
            with self.subTest(profile=expected_name), patch.object(controller, "_profile_clock_minutes", return_value=minutes):
                profile = controller._harvest_time_profile({**cfg, "HARVEST_HIGH_SMA_SOC_TIME_PROFILE_ENABLED": True})
                self.assertEqual(expected_name, profile["name"])
                self.assertAlmostEqual(expected_share, profile["share"])
                self.assertEqual(expected_entry, profile["entry_confirm_s"])
                self.assertEqual(0, profile["reserve_w"])

    def test_rc17_measurement_contract_is_additive_and_reproducible(self):
        self.assertEqual(228, len(RC16_STANDARD_HEADER))
        self.assertEqual(246, len(STANDARD_HEADER))
        row = build_v4_row(cfg_high(), {
            "mode": "CHARGE",
            "epoch_s": 1_800_000_000.0,
            "cycle_id": 1,
            "harvest_network_target_w": 0,
            "harvest_total_available_charge_w": 4000,
            "harvest_primary_share_target_w": 2000,
            "harvest_zendure_share_target_w": 2000,
            "harvest_export_capture_target_w": 2000,
            "harvest_target_selected_by": "BOTH_EQUAL",
            "harvest_calculation_branch": "HIGH_SMA_SOC",
            "harvest_entry_min_export_w": 300,
            "harvest_command_path_eligible": True,
            "harvest_command_path_block_reason": "",
        })
        self.assertEqual(0.0, row["harvest_network_target_w"])
        self.assertEqual(4000.0, row["harvest_total_available_charge_w"])
        self.assertEqual("BOTH_EQUAL", row["harvest_target_selected_by"])
        self.assertEqual("HIGH_SMA_SOC", row["harvest_calculation_branch"])
        self.assertEqual("1", row["harvest_command_path_eligible"])


if __name__ == "__main__":
    unittest.main()
