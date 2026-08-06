# SPDX-License-Identifier: AGPL-3.0-or-later

import math
import unittest

from settings_codecs import format_value, parse_value
from settings_registry import SETTINGS_BY_KEY


class TestS11Codecs(unittest.TestCase):
    def test_bool_is_strict_and_not_truthy(self):
        spec = SETTINGS_BY_KEY["HEADLESS_MODE"]
        self.assertIs(True, parse_value(spec, True).value)
        self.assertIs(False, parse_value(spec, "false").value)
        for invalid in (1, 0, "False", " false", "yes", None):
            with self.subTest(invalid=invalid):
                self.assertFalse(parse_value(spec, invalid).ok)

    def test_int_rejects_bool_float_whitespace_and_leading_zero(self):
        spec = SETTINGS_BY_KEY["MQTT_PORT"]
        self.assertEqual(1883, parse_value(spec, "1883").value)
        for invalid in (True, 1883.0, " 1883", "1883 ", "01883", "1.5"):
            with self.subTest(invalid=invalid):
                self.assertFalse(parse_value(spec, invalid).ok)

    def test_int_range_is_enforced_without_clamping(self):
        spec = SETTINGS_BY_KEY["MQTT_PORT"]
        self.assertFalse(parse_value(spec, 0).ok)
        self.assertFalse(parse_value(spec, 65536).ok)
        self.assertEqual(1, parse_value(spec, 1).value)
        self.assertEqual(65535, parse_value(spec, 65535).value)

    def test_optional_int_accepts_only_none_empty_or_integer(self):
        spec = SETTINGS_BY_KEY["NIGHT_DISCHARGE_STOP_SOC_PERCENT"]
        self.assertIsNone(parse_value(spec, None).value)
        self.assertIsNone(parse_value(spec, "").value)
        self.assertEqual(20, parse_value(spec, "20").value)
        self.assertFalse(parse_value(spec, " ").ok)
        self.assertFalse(parse_value(spec, 20.0).ok)

    def test_harvest_absolute_w_codec_maps_zero_to_ratio_fallback(self):
        spec = SETTINGS_BY_KEY["HARVEST_PRIMARY_CHARGE_RESTART_W"]
        self.assertIsNone(parse_value(spec, 0).value)
        self.assertIsNone(parse_value(spec, "0").value)
        self.assertEqual(1900, parse_value(spec, "1900").value)
        self.assertFalse(parse_value(spec, "1900 W").ok)

    def test_float_is_finite_and_locale_independent(self):
        spec = SETTINGS_BY_KEY["SMOOTHING_FACTOR"]
        self.assertEqual(0.25, parse_value(spec, "0.25").value)
        self.assertEqual(0.25, parse_value(spec, ".25").value)
        for invalid in (True, "0,25", " 0.25", math.inf, math.nan):
            with self.subTest(invalid=invalid):
                self.assertFalse(parse_value(spec, invalid).ok)

    def test_time_codec_normalizes_only_key_specific_hour_width(self):
        spec = SETTINGS_BY_KEY["HARVEST_HIGH_SMA_SOC_PROFILE_START_TIME"]
        self.assertEqual("09:30", parse_value(spec, "9:30").value)
        self.assertEqual("09:30", parse_value(spec, "09:30").value)
        for invalid in (" 09:30", "24:00", "9:3", "09.30"):
            with self.subTest(invalid=invalid):
                self.assertFalse(parse_value(spec, invalid).ok)

    def test_optional_mm_dd_rejects_february_29_and_invalid_days(self):
        spec = SETTINGS_BY_KEY["HARVEST_SEASON_PARALLEL_START_MM_DD"]
        self.assertIsNone(parse_value(spec, "").value)
        self.assertEqual("03-01", parse_value(spec, "03-01").value)
        for invalid in ("02-29", "04-31", "2-01", " 03-01"):
            with self.subTest(invalid=invalid):
                self.assertFalse(parse_value(spec, invalid).ok)

    def test_enum_preserves_case_and_rejects_unknown(self):
        spec = SETTINGS_BY_KEY["MANUAL_MODE"]
        self.assertEqual("AUTO", parse_value(spec, "AUTO").value)
        self.assertFalse(parse_value(spec, "auto").ok)
        self.assertFalse(parse_value(spec, " AUTO").ok)

    def test_string_is_lossless_and_not_trimmed(self):
        spec = SETTINGS_BY_KEY["DEVICE_ID"]
        self.assertEqual(" ABC ", parse_value(spec, " ABC ").value)

    def test_secret_format_never_returns_secret(self):
        spec = SETTINGS_BY_KEY["MQTT_PASSWORD"]
        secret = "super-secret-value"
        result = parse_value(spec, secret)
        self.assertTrue(result.ok)
        self.assertEqual("set", format_value(spec, result.value))
        self.assertNotIn(secret, repr(result.issue))


if __name__ == "__main__":
    unittest.main()
