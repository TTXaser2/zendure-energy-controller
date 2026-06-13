import time
import unittest

from config_manager import DEFAULT_CONFIG, validate_config
from config_validator import split_issues, validate_config_semantics
from csv_logger import CSV_FIELDS
from tests.test_operation_priority import OkShelly, base_cfg, fresh_state, make_controller
from web_ui import apply_night_time_form_fields, build_settings_page, parse_hhmm


class V12815NightModeReserveSocTests(unittest.TestCase):
    def _run_full_cycle(self, controller, cfg):
        start = time.time()
        controller.run_once(cfg)
        controller.finish_cycle(cfg, start)

    def test_night_discharge_without_stop_soc_behaves_like_before(self):
        cfg = base_cfg(NIGHT_DISCHARGE_ENABLED=True, NIGHT_DISCHARGE_STOP_SOC_PERCENT=None)
        controller, state, mqtt, shelly = make_controller(cfg, state=fresh_state(35))
        controller.is_night_discharge_active = lambda _cfg: True

        self._run_full_cycle(controller, cfg)

        self.assertEqual(state.current_mode, "NIGHT_DISCHARGE")
        self.assertIn(("output", 400, False), mqtt.commands)
        self.assertIsNone(state.night_discharge_stop_soc_percent)
        self.assertEqual(state.night_discharge_stop_reason, "none")
        self.assertNotIn("NIGHT_RESERVE_SOC", state.active_limiters)

    def test_night_discharge_reserve_soc_pauses_fixed_night_mode_and_uses_auto_grid_control(self):
        cfg = base_cfg(NIGHT_DISCHARGE_ENABLED=True, NIGHT_DISCHARGE_STOP_SOC_PERCENT=35, DEADBAND_W=80)
        state = fresh_state(35)
        with state.lock:
            state.current_mode = "NIGHT_DISCHARGE"
            state.last_output_power = 400
            state.technical_control_path = "NIGHT_MODE -> OUTPUT"
        controller, state, mqtt, shelly = make_controller(cfg, state=state, shelly=OkShelly(300))
        controller.is_night_discharge_active = lambda _cfg: True

        self._run_full_cycle(controller, cfg)

        self.assertEqual(shelly.calls, 1)
        self.assertEqual(state.night_discharge_stop_soc_percent, 35)
        self.assertEqual(state.night_discharge_stop_reason, "NIGHT_RESERVE_SOC")
        self.assertIn("NIGHT_RESERVE_SOC", state.active_limiters)
        self.assertNotEqual(state.current_mode, "STOP_HOLD")
        self.assertEqual(state.current_mode, "DISCHARGE")
        self.assertIn(("output", 0, True), mqtt.commands)
        self.assertTrue(any(cmd[0] == "output" and cmd[1] > 0 for cmd in mqtt.commands))
        self.assertTrue(state.technical_control_path.startswith("GRID -> DISCHARGE"))

    def test_reserve_soc_allows_fixed_night_discharge_again_when_soc_rises_above_threshold(self):
        cfg = base_cfg(NIGHT_DISCHARGE_ENABLED=True, NIGHT_DISCHARGE_STOP_SOC_PERCENT=35)
        state = fresh_state(35)
        controller, state, mqtt, shelly = make_controller(cfg, state=state, shelly=OkShelly(0))
        controller.is_night_discharge_active = lambda _cfg: True

        self._run_full_cycle(controller, cfg)
        self.assertEqual(state.night_discharge_stop_reason, "NIGHT_RESERVE_SOC")
        mqtt.commands.clear()
        with state.lock:
            state.battery_soc = 37
            state.last_soc_update_epoch = time.time()

        self._run_full_cycle(controller, cfg)

        self.assertEqual(state.current_mode, "NIGHT_DISCHARGE")
        self.assertEqual(state.night_discharge_stop_reason, "none")
        self.assertNotIn("NIGHT_RESERVE_SOC", state.active_limiters)
        self.assertIn(("output", 400, False), mqtt.commands)

    def test_stop_reason_resets_after_leaving_night_window(self):
        cfg = base_cfg(NIGHT_DISCHARGE_ENABLED=True, NIGHT_DISCHARGE_STOP_SOC_PERCENT=35)
        state = fresh_state(35)
        controller, state, mqtt, shelly = make_controller(cfg, state=state, shelly=OkShelly(0))
        active = {"value": True}
        controller.is_night_discharge_active = lambda _cfg: active["value"]

        self._run_full_cycle(controller, cfg)
        self.assertEqual(state.night_discharge_stop_reason, "NIGHT_RESERVE_SOC")

        active["value"] = False
        with state.lock:
            state.battery_soc = 80
            state.last_soc_update_epoch = time.time()
        # AUTO path may fail due missing Shelly, but stop reason reset happens before that.
        controller.run_once(cfg)

        self.assertEqual(state.night_discharge_stop_reason, "none")


    def test_reserve_soc_does_not_reset_existing_auto_discharge_each_cycle(self):
        cfg = base_cfg(NIGHT_DISCHARGE_ENABLED=True, NIGHT_DISCHARGE_STOP_SOC_PERCENT=35, DEADBAND_W=80)
        state = fresh_state(35)
        with state.lock:
            state.current_mode = "DISCHARGE"
            state.last_output_power = 120
            state.technical_control_path = "GRID -> DISCHARGE -> OUTPUT"
        controller, state, mqtt, shelly = make_controller(cfg, state=state, shelly=OkShelly(300))
        controller.is_night_discharge_active = lambda _cfg: True

        self._run_full_cycle(controller, cfg)

        self.assertEqual(shelly.calls, 1)
        self.assertEqual(state.current_mode, "DISCHARGE")
        self.assertNotIn(("output", 0, True), mqtt.commands)
        self.assertGreater(state.last_output_power, 0)
        self.assertIn("NIGHT_RESERVE_SOC", state.active_limiters)

    def test_global_min_soc_still_takes_precedence(self):
        cfg = base_cfg(NIGHT_DISCHARGE_ENABLED=True, MIN_SOC_PERCENT=15, NIGHT_DISCHARGE_STOP_SOC_PERCENT=35)
        controller, state, mqtt, shelly = make_controller(cfg, state=fresh_state(15))
        controller.is_night_discharge_active = lambda _cfg: True

        self._run_full_cycle(controller, cfg)

        self.assertEqual(state.current_mode, "SAFE_STATE")
        self.assertIn("MIN_SOC", state.active_limiters)
        self.assertEqual(state.night_discharge_stop_reason, "none")

    def test_night_stop_soc_validation_rejects_below_global_min_soc(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg.update(NIGHT_DISCHARGE_ENABLED=True, MIN_SOC_PERCENT=20, NIGHT_DISCHARGE_STOP_SOC_PERCENT=10)
        normalized, _ = validate_config(cfg)
        issues = validate_config_semantics(normalized, current=dict(DEFAULT_CONFIG), perform_live_checks=False)
        buckets = split_issues(issues)
        self.assertTrue(any(issue.code == "NIGHT_STOP_SOC_BELOW_MIN_SOC" for issue in buckets["ERROR"]))

    def test_csv_fields_include_night_reserve_soc_contract(self):
        self.assertIn("night_discharge_stop_soc_percent", CSV_FIELDS)
        self.assertNotIn("night_discharge_latched_off", CSV_FIELDS)
        self.assertNotIn("night_discharge_latch_reason", CSV_FIELDS)
        self.assertIn("night_discharge_stop_reason", CSV_FIELDS)


class V12815NightTimeSettingsTests(unittest.TestCase):
    def test_parse_hhmm_accepts_and_normalizes_single_digit_values(self):
        self.assertEqual(parse_hhmm("5:30"), (5, 30))
        self.assertEqual(parse_hhmm("23:0"), (23, 0))
        self.assertEqual(parse_hhmm("05:30"), (5, 30))

    def test_parse_hhmm_rejects_invalid_values(self):
        self.assertIsNone(parse_hhmm("24:00"))
        self.assertIsNone(parse_hhmm("12:75"))
        self.assertIsNone(parse_hhmm("abc"))

    def test_settings_page_uses_two_hhmm_fields_and_hides_four_internal_fields(self):
        cfg = dict(DEFAULT_CONFIG)
        html = build_settings_page(cfg)
        self.assertIn('name="NIGHT_START_TIME"', html)
        self.assertIn('name="NIGHT_END_TIME"', html)
        self.assertIn('value="20:30"', html)
        self.assertIn('value="05:00"', html)
        self.assertNotIn('name="NIGHT_START_HOUR"', html)
        self.assertNotIn('name="NIGHT_START_MINUTE"', html)
        self.assertIn('data-night-time="1"', html)
        self.assertIn('normalizeNightTimeInput', html)

    def test_time_form_fields_are_mapped_to_existing_config_keys(self):
        cfg = dict(DEFAULT_CONFIG)
        issues = apply_night_time_form_fields(cfg, {"NIGHT_START_TIME": "5:30", "NIGHT_END_TIME": "23:0"})
        self.assertEqual(issues, [])
        self.assertEqual(cfg["NIGHT_START_HOUR"], 5)
        self.assertEqual(cfg["NIGHT_START_MINUTE"], 30)
        self.assertEqual(cfg["NIGHT_END_HOUR"], 23)
        self.assertEqual(cfg["NIGHT_END_MINUTE"], 0)

    def test_invalid_time_form_field_returns_validation_error(self):
        cfg = dict(DEFAULT_CONFIG)
        issues = apply_night_time_form_fields(cfg, {"NIGHT_START_TIME": "24:00"})
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "ERROR")
        self.assertEqual(issues[0].code, "NIGHT_START_TIME_INVALID")


if __name__ == "__main__":
    unittest.main()
