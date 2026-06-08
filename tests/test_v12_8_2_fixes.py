import unittest

import version
from tools.replay_core import DEFAULT_MAX_FILES
from tools.replay_report import energy_table, text_report
from tools.replay_web import REPLAY_VERSION, safe_limits


class V1282FixTests(unittest.TestCase):
    def test_analysis_tables_use_german_decimal_comma(self):
        html = energy_table({
            "energy": {
                "grid_import_kwh": 0.1417,
                "grid_export_kwh": 24.0859,
                "zendure_charge_kwh": 0.3598,
                "zendure_discharge_kwh": 0.0427,
            }
        })
        self.assertIn("0,1417 kWh", html)
        self.assertIn("24,0859 kWh", html)
        self.assertNotIn("0.1417 kWh", html)

    def test_text_report_uses_german_decimal_comma(self):
        report = text_report({
            "schema": "ZEC-MEASUREMENT-V2",
            "filenames": ["a.csv"],
            "rows": 1,
            "data_quality": {"status": "ok", "avg_dt_s": 3.25, "median_dt_s": 3.25, "max_dt_s": 3.25},
            "energy": {"grid_import_kwh": 0.1417, "grid_export_kwh": 24.0859},
            "regulator_quality": {"avg_abs_grid_w": 12.5, "median_abs_grid_w": 10, "p95_abs_grid_w": 33.3},
            "cross_charge": {},
            "night_discharge": {},
        })
        self.assertIn("0,1417 kWh", report)
        self.assertIn("24,0859 kWh", report)
        self.assertIn("12,5 W", report)

    def test_analysis_file_limit_is_pi_safe_and_version_is_shared(self):
        self.assertEqual(DEFAULT_MAX_FILES, 4)
        self.assertEqual(safe_limits().max_files, 4)
        self.assertEqual(safe_limits().max_total_bytes, 12 * 1024 * 1024)
        self.assertEqual(safe_limits().max_rows, 40_000)
        self.assertEqual(REPLAY_VERSION, "12.8.9")
        self.assertEqual(version.__version__, "12.8.9")


if __name__ == "__main__":
    unittest.main()
