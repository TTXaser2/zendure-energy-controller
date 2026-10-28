"""Stage-1 live command arbitration; opt-in, baseline isolation, import exit.

Controller is driven with bounded, already source-validated read-only proposal
instead of forging physical effectiveness from the resulting MQTT commands.
"""
import unittest
from unittest.mock import patch

from tests.test_battery_care_discharge_floor import care_cfg
from tests.test_operation_priority import fresh_state, make_controller, OkShelly


class BatteryCarePvLiveDispatch(unittest.TestCase):
    def make(self, *, cfg=None, grid=0, soc=39, last_input=0):
        cfg = cfg or care_cfg(REST_SURPLUS_HARVEST_ENABLED=False,
                              HARVEST_FAST_CAPTURE_MODE="off")
        state = fresh_state(soc)
        with state.lock:
            state.last_input_power = last_input
        ctrl, state, mqtt, _ = make_controller(cfg, state=state, shelly=OkShelly(grid))
        ctrl.is_night_discharge_active = lambda _: False
        return ctrl, cfg, state, mqtt

    def proposal(self, ctrl, state, candidate, extra, reason="CARE_PV_ATTACK"):
        def apply(_):
            with state.lock:
                state.care_pv_shadow_candidate_w = candidate
                state.care_pv_shadow_extra_w = extra
                state.care_pv_shadow_reason = reason
        ctrl._battery_care_pv_shadow_step = apply

    def test_deadband_pv_request_uses_one_charge_owner(self):
        ctrl, cfg, state, mqtt = self.make()
        self.proposal(ctrl, state, 700, 700)
        ctrl.run_once(cfg)
        self.assertGreater(state.last_input_power, 0)
        self.assertLessEqual(state.last_input_power, 700)
        self.assertTrue(ctrl._care_pv_live_active)
        self.assertEqual(0, ctrl._care_pv_baseline_target_w)
        self.assertIn("BATTERY_CARE_PV", state.technical_control_path)
        self.assertTrue(any(c[0] == "input" and c[1] > 0 for c in mqtt.commands))
        self.assertEqual(1, sum(c[0] == "ac" for c in mqtt.commands))

    def test_fast_overlay_must_not_run_with_active_care_absolute_target(self):
        ctrl, cfg, state, _ = self.make(cfg=care_cfg(HARVEST_FAST_CAPTURE_MODE="active"))
        self.proposal(ctrl, state, 600, 600)
        with patch.object(ctrl, "_fast_capture_step", side_effect=AssertionError("double export")):
            ctrl.run_once(cfg)
        self.assertGreater(state.last_input_power, 0)
        self.assertEqual(0, state.fast_capture_overlay_w)

    def test_grid_import_backoff_withdraws_care_from_isolated_baseline(self):
        ctrl, cfg, state, mqtt = self.make(grid=0)
        self.proposal(ctrl, state, 700, 700)
        ctrl.run_once(cfg)
        before = state.last_input_power
        self.assertGreater(before, 0)
        # Import cancels only Care, never treats last B+Care as next B.
        ctrl.shelly.value = 350
        self.proposal(ctrl, state, 0, 0, "CARE_IMPORT_BACKOFF")
        ctrl.run_once(cfg)
        self.assertEqual(0, state.last_input_power)
        self.assertFalse(ctrl._care_pv_live_active)
        self.assertEqual(0, ctrl._care_pv_baseline_target_w)
        self.assertFalse(any(c[0] == "output" and c[1] > 0 for c in mqtt.commands))

    def test_care_off_return_does_not_latch_last_positive_target(self):
        ctrl, cfg, state, _ = self.make()
        self.proposal(ctrl, state, 800, 800)
        ctrl.run_once(cfg)
        self.assertGreater(state.last_input_power, 0)
        cfg["BATTERY_CARE_ENABLED"] = False
        self.proposal(ctrl, state, 0, 0, "CARE_NOT_ELIGIBLE")
        ctrl.run_once(cfg)
        self.assertEqual(0, state.last_input_power)
        self.assertFalse(ctrl._care_pv_live_active)
        self.assertFalse(ctrl._care_pv_return_to_baseline_pending)

    def test_ineligible_no_effect_on_regular_grid_import_discharge(self):
        ctrl, cfg, state, _ = self.make(cfg=care_cfg(BATTERY_CARE_ENABLED=False),
                                       grid=900, soc=65)
        self.proposal(ctrl, state, 0, 0, "CARE_NOT_ELIGIBLE")
        ctrl.run_once(cfg)
        self.assertGreater(state.last_output_power, 0)
        self.assertFalse(ctrl._care_pv_live_active)

    def test_real_source_adapter_missing_is_not_a_care_command(self):
        ctrl, cfg, state, _ = self.make()
        ctrl.run_once(cfg)  # missing independently confirmed Zendure AC direction
        self.assertFalse(ctrl._care_pv_live_active)
        self.assertEqual(0, state.care_pv_shadow_extra_w)


if __name__ == "__main__":
    unittest.main()
