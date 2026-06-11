import time
import unittest

from config_manager import DEFAULT_CONFIG, validate_config
from config_validator import split_issues, validate_config_semantics
from csv_logger import CSV_FIELDS
from tests.test_operation_priority import base_cfg, fresh_state, make_controller
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
        self.assertFalse(state.night_discharge_latched_off)
        self.assertIsNone(state.night_discharge_stop_soc_percent)
        self.assertNotIn("NIGHT_RESERVE_SOC", state.active_limiters)

    def test_night_discharge_stops_and_latches_at_reserve_soc(self):
        cfg = base_cfg(NIGHT_DISCHARGE_ENABLED=True, NIGHT_DISCHARGE_STOP_SOC_PERCENT=35)
        controller, state, mqtt, shelly = make_controller(cfg, state=fresh_state(35))
        controller.is_night_discharge_active = lambda _cfg: True

        self._run_full_cycle(controller, cfg)

        self.assertEqual(state.current_mode, "STOP_HOLD")
        self.assertTrue(state.night_discharge_latched_off)
        self.assertEqual(state.night_discharge_stop_soc_percent, 35)
        self.assertIn("NIGHT_RESERVE_SOC", state.active_limiters)
        self.assertIn(("output", 0, True), mqtt.commands)
        self.assertIn("Reserve-SOC 35 % erreicht", state.control_reason)
        self.assertIn("NIGHT_MODE -> RESERVE_SOC", state.technical_control_path)

    def test_reserve_soc_latch_prevents_restart_in_same_night_window(self):
        cfg = base_cfg(NIGHT_DISCHARGE_ENABLED=True, NIGHT_DISCHARGE_STOP_SOC_PERCENT=35)
        state = fresh_state(35)
        controller, state, mqtt, shelly = make_controller(cfg, state=state)
        controller.is_night_discharge_active = lambda _cfg: True

        self._run_full_cycle(controller, cfg)
        mqtt.commands.clear()
        with state.lock:
            state.battery_soc = 37
            state.last_soc_update_epoch = time.time()

        self._run_full_cycle(controller, cfg)

        self.assertEqual(state.current_mode, "STOP_HOLD")
        self.assertTrue(state.night_discharge_latched_off)
        self.assertIn("NIGHT_RESERVE_SOC", state.active_limiters)
        self.assertNotIn(("output", 400, False), mqtt.commands)

    def test_latch_resets_after_leaving_night_window(self):
        cfg = base_cfg(NIGHT_DISCHARGE_ENABLED=True, NIGHT_DISCHARGE_STOP_SOC_PERCENT=35)
        state = fresh_state(35)
        controller, state, mqtt, shelly = make_controller(cfg, state=state)
        active = {"value": True}
        controller.is_night_discharge_active = lambda _cfg: active["value"]

        self._run_full_cycle(controller, cfg)
        self.assertTrue(state.night_discharge_latched_off)

        active["value"] = False
        with state.lock:
            state.battery_soc = 80
            state.last_soc_update_epoch = time.time()
        # AUTO path may fail due missing Shelly, but latch reset happens before that.
        controller.run_once(cfg)

        self.assertFalse(state.night_discharge_latched_off)
        self.assertEqual(state.night_discharge_stop_reason, "none")

    def test_global_min_soc_still_takes_precedence(self):
        cfg = base_cfg(NIGHT_DISCHARGE_ENABLED=True, MIN_SOC_PERCENT=15, NIGHT_DISCHARGE_STOP_SOC_PERCENT=35)
        controller, state, mqtt, shelly = make_controller(cfg, state=fresh_state(15))
        controller.is_night_discharge_active = lambda _cfg: True

        self._run_full_cycle(controller, cfg)

        self.assertEqual(state.current_mode, "SAFE_STATE")
        self.assertIn("MIN_SOC", state.active_limiters)
        self.assertFalse(state.night_discharge_latched_off)

    def test_night_stop_soc_validation_rejects_below_global_min_soc(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg.update(NIGHT_DISCHARGE_ENABLED=True, MIN_SOC_PERCENT=20, NIGHT_DISCHARGE_STOP_SOC_PERCENT=10)
        normalized, _ = validate_config(cfg)
        issues = validate_config_semantics(normalized, current=dict(DEFAULT_CONFIG), perform_live_checks=False)
        buckets = split_issues(issues)
        self.assertTrue(any(issue.code == "NIGHT_STOP_SOC_BELOW_MIN_SOC" for issue in buckets["ERROR"]))

    def test_csv_fields_include_night_reserve_soc_contract(self):
        self.assertIn("night_discharge_stop_soc_percent", CSV_FIELDS)
        self.assertIn("night_discharge_latched_off", CSV_FIELDS)
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
