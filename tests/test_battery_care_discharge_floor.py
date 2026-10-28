"""CP08: Care seasonal discharge-floor gates; no Care charging authority yet."""
import unittest
from unittest.mock import patch

from tests.test_operation_priority import base_cfg, fresh_state, make_controller, OkShelly


def care_cfg(**changes):
    cfg = base_cfg(
        MANUAL_MODE="AUTO", NIGHT_DISCHARGE_ENABLED=False,
        BATTERY_CARE_ENABLED=True,
        BATTERY_CARE_SEASON_START_MM_DD="01-01",
        BATTERY_CARE_SEASON_END_MM_DD="12-31",
        BATTERY_CARE_RESERVE_SOC_PERCENT=40,
        BATTERY_CARE_GRID_TRIGGER_SOC_PERCENT=30,
        BATTERY_CARE_EMERGENCY_SOC_PERCENT=20,
        BATTERY_CARE_GRID_CHARGE_MAX_POWER_W=250,
        CROSS_CHARGE_ENABLED=False,
        REST_SURPLUS_HARVEST_ENABLED=False,
        DEADBAND_W=80, MOVING_AVERAGE_SAMPLES=1,
    )
    cfg.update(changes)
    return cfg


class CareFloorIntegrationTests(unittest.TestCase):
    def make(self, *, cfg=None, soc=40, grid=0, output=0, mode="HOLD"):
        cfg = cfg or care_cfg()
        state = fresh_state(soc)
        with state.lock:
            state.last_output_power = output
            state.current_mode = mode
        ctrl, state, mqtt, shelly = make_controller(cfg, state=state, shelly=OkShelly(grid))
        ctrl.is_night_discharge_active = lambda _: False
        return ctrl, cfg, state, mqtt, shelly

    def test_care_off_has_identical_deadband_hold_of_prior_discharge(self):
        ctrl, cfg, state, mqtt, _ = self.make(cfg=care_cfg(BATTERY_CARE_ENABLED=False), output=320)
        ctrl.run_once(cfg)
        self.assertEqual(320, state.last_output_power)
        self.assertNotIn("BATTERY_CARE_RESERVE", state.active_limiters)

    def test_in_season_deadband_holding_discharge_is_neutralized(self):
        ctrl, cfg, state, mqtt, _ = self.make(output=320)
        ctrl.run_once(cfg)
        self.assertEqual(0, state.last_output_power)
        self.assertEqual("HOLD", state.current_mode)
        self.assertIn("BATTERY_CARE_RESERVE", state.active_limiters)
        self.assertFalse(any(x[0] == "output" and x[1] > 0 for x in mqtt.commands))
        self.assertIn(("output", 0, True), mqtt.commands)

    def test_active_output_neutralized_before_cross_charge_and_deadband(self):
        ctrl, cfg, state, mqtt, _ = self.make(output=250, grid=10)
        def unexpected(_):
            raise AssertionError("cross-charge must not precede the Care floor")
        ctrl.cross_charge_guard_corrects_existing_target = unexpected
        ctrl.run_once(cfg)
        self.assertEqual(0, state.last_output_power)
        self.assertIn("BATTERY_CARE_RESERVE", state.active_limiters)

    def test_import_below_reserve_cannot_resume_discharge(self):
        ctrl, cfg, state, mqtt, _ = self.make(soc=39, grid=1200, output=0)
        ctrl.run_once(cfg)
        self.assertEqual(0, state.last_output_power)
        self.assertFalse(any(x[0] == "output" and x[1] > 0 for x in mqtt.commands))

    def test_above_reserve_auto_discharge_still_possible(self):
        ctrl, cfg, state, mqtt, _ = self.make(soc=41, grid=1000)
        ctrl.run_once(cfg)
        self.assertGreater(state.last_output_power, 0)
        self.assertNotIn("BATTERY_CARE_RESERVE", state.active_limiters)

    def test_out_of_season_or_missing_or_invalid_care_config_is_legacy(self):
        variations = (
            care_cfg(BATTERY_CARE_SEASON_START_MM_DD="01-01", BATTERY_CARE_SEASON_END_MM_DD="01-01"),
            care_cfg(BATTERY_CARE_RESERVE_SOC_PERCENT=None),
            care_cfg(BATTERY_CARE_GRID_TRIGGER_SOC_PERCENT=39),
            care_cfg(BATTERY_CARE_ENABLED=False),
        )
        for cfg in variations:
            with self.subTest(cfg=cfg):
                ctrl, _, state, _, _ = self.make(cfg=cfg, output=320)
                ctrl.run_once(cfg)
                self.assertEqual(320, state.last_output_power)

    def test_night_stop_raises_to_care_floor_but_keeps_higher_night_reserve(self):
        ctrl, cfg, _, _, _ = self.make()
        self.assertEqual(40, ctrl._effective_night_stop_soc(cfg))
        cfg["NIGHT_DISCHARGE_STOP_SOC_PERCENT"] = 50
        self.assertEqual(50, ctrl._effective_night_stop_soc(cfg))
        cfg["BATTERY_CARE_ENABLED"] = False
        self.assertEqual(50, ctrl._effective_night_stop_soc(cfg))

    def test_night_running_at_care_reserve_pauses_without_auto_reopen(self):
        cfg = care_cfg(NIGHT_DISCHARGE_ENABLED=True, NIGHT_DISCHARGE_STOP_SOC_PERCENT=35)
        ctrl, cfg, state, mqtt, _ = self.make(cfg=cfg, output=400, mode="NIGHT_DISCHARGE", grid=650)
        with state.lock:
            state.technical_control_path = "NIGHT_MODE -> OUTPUT"
        ctrl.is_night_discharge_active = lambda _: True
        ctrl.run_once(cfg)
        self.assertEqual(0, state.last_output_power)
        self.assertFalse(any(x[0] == "output" and x[1] > 0 for x in mqtt.commands))
        self.assertEqual(1, sum(x[0] == "ac" for x in mqtt.commands),
                         "NIGHT pause and AUTO must not issue two neutral batches")

    def test_night_care_reserve_still_allows_real_export_charge(self):
        cfg = care_cfg(NIGHT_DISCHARGE_ENABLED=True, NIGHT_DISCHARGE_STOP_SOC_PERCENT=35)
        ctrl, cfg, state, mqtt, _ = self.make(cfg=cfg, output=400, mode="NIGHT_DISCHARGE", grid=-1900)
        with state.lock:
            state.technical_control_path = "NIGHT_MODE -> OUTPUT"
        ctrl.is_night_discharge_active = lambda _: True
        ctrl.run_once(cfg)
        self.assertEqual("CHARGE", state.current_mode)
        self.assertGreater(state.last_input_power, 0)
        self.assertFalse(any(x[0] == "output" and x[1] > 0 for x in mqtt.commands))

    def test_deadband_at_floor_does_not_repeatedly_force_neutralization(self):
        ctrl, cfg, state, mqtt, _ = self.make(output=320)
        ctrl.run_once(cfg)
        after_one = len(mqtt.commands)
        ctrl.run_once(cfg)
        self.assertEqual(0, state.last_output_power)
        self.assertFalse(any(x[0] == "output" and x[1] > 0 for x in mqtt.commands))
        self.assertLessEqual(len(mqtt.commands) - after_one, 3)

    def test_higher_normal_min_soc_remains_effective(self):
        cfg = care_cfg(MIN_SOC_PERCENT=50)
        ctrl, cfg, state, mqtt, _ = self.make(cfg=cfg, soc=45, grid=850)
        self.assertEqual(50, ctrl._effective_auto_min_soc(cfg))
        ctrl.run_once(cfg)
        self.assertEqual(0, state.last_output_power)
        self.assertIn("MIN_SOC", state.active_limiters)

    def test_manual_fixed_mode_remains_explicit_user_choice(self):
        cfg = care_cfg(MANUAL_MODE="FIXED_DISCHARGE")
        ctrl, cfg, state, mqtt, _ = self.make(cfg=cfg, output=0)
        ctrl.run_once(cfg)
        self.assertEqual("MANUAL_FIXED_DISCHARGE", state.current_mode)

    def test_manual_stop_absolutely_blocks_care_output(self):
        cfg = care_cfg(MANUAL_MODE="STOP_HOLD")
        ctrl, cfg, state, mqtt, _ = self.make(cfg=cfg, output=200)
        ctrl.run_once(cfg)
        self.assertEqual("STOP_HOLD", state.current_mode)
        self.assertFalse(any(x[0] == "output" and x[1] > 0 for x in mqtt.commands))


if __name__ == "__main__":
    unittest.main()
