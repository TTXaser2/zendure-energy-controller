import tempfile
import unittest
from pathlib import Path

from measurement import derive_zendure_actual_power
from tools.replay_core import AnalysisLimits, LEGACY_V3_SCHEMA, analyze_files
from tools.replay_web import extended_limits, safe_limits, selection_profile


class V1285SafetyTests(unittest.TestCase):
    def _csv(self, directory: str, name: str, rows: int = 3) -> Path:
        path = Path(directory) / name
        with path.open("w", encoding="utf-8") as f:
            f.write("schema;controller_version;epoch;dt_s;datetime_local;grid_power_w;zendure_target_power_w;zendure_actual_power_w;zendure_soc_percent;mode;mqtt_commands_sent_in_cycle;charge_acceptance_state\n")
            for i in range(rows):
                f.write(f"{LEGACY_V3_SCHEMA};12.8.5;{1000+i*3};3;2026-06-01 00:00:{i:02d};0;0;0;50;HOLD;0;ok\n")
        return path

    def test_pack_discharge_is_separate_from_grid_side_command_effect(self):
        derived = derive_zendure_actual_power(pack_input=422, output_home=0, grid_input=0, output_pack=0, requested_output_limit=400)
        self.assertEqual(0, derived["signed_power_w"])
        self.assertEqual(0, derived["discharge_power_w"])
        self.assertEqual(-422, derived["battery_signed_power_w"])
        self.assertEqual(422, derived["battery_discharge_power_w"])

    def test_analysis_limits_are_pi_safe_and_extended_is_separate(self):
        self.assertEqual(safe_limits().max_files, 2)
        self.assertEqual(safe_limits().max_rows, 20_000)
        self.assertEqual(extended_limits().max_files, 3)
        self.assertEqual(extended_limits().max_rows, 35_000)

    def test_row_limit_is_checked_while_reading(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._csv(tmp, "a.csv", rows=5)
            with self.assertRaises(ValueError):
                analyze_files([str(path)], limits=AnalysisLimits(max_files=1, max_total_bytes=10_000_000, max_rows=3))

    def test_selection_profile_rejects_above_extended_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._csv(tmp, "a.csv", rows=5)
            cfg = {
                "ANALYSIS_MAX_FILES": 1,
                "ANALYSIS_MAX_TOTAL_BYTES": 10_000_000,
                "ANALYSIS_MAX_ROWS": 3,
                "ANALYSIS_EXTENDED_MAX_FILES": 1,
                "ANALYSIS_EXTENDED_MAX_TOTAL_BYTES": 10_000_000,
                "ANALYSIS_EXTENDED_MAX_ROWS": 4,
            }
            profile = selection_profile([path], cfg)
            self.assertTrue(profile["rejected"])
            self.assertEqual(profile["risk"], "rejected")


if __name__ == "__main__":
    unittest.main()
