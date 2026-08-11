import os
import tempfile
import unittest

from tools.replay_core import LEGACY_V3_SCHEMA, AnalysisLimits, analyze_files, summary_csv


class ReplayV128Tests(unittest.TestCase):
    def _write_csv(self, rows):
        header = (
            "schema;controller_version;epoch;dt_s;datetime_local;grid_power_w;zendure_target_power_w;"
            "zendure_actual_power_w;second_battery_power_w;second_battery_discharge_power_w;zendure_soc_percent;"
            "mode;technical_limiters;mqtt_commands_sent_in_cycle;charge_acceptance_state\n"
        )
        content = header + "".join(rows)
        f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
        f.write(content)
        f.close()
        return f.name

    def test_multi_file_analysis_reports_regulator_and_cross_charge_quality(self):
        f1 = self._write_csv([
            f"{LEGACY_V3_SCHEMA};12.8;1000;3;2026-05-29 10:00:00;50;0;0;0;0;50;HOLD;;0;ok\n",
            f"{LEGACY_V3_SCHEMA};12.8;1003;3;2026-05-29 10:00:03;-300;500;120;-500;500;51;CHARGE;SMA_DISCHARGE;1;ok\n",
        ])
        f2 = self._write_csv([
            f"{LEGACY_V3_SCHEMA};12.8;1006;3;2026-05-29 10:00:06;250;-400;-350;0;0;50;DISCHARGE;;1;ok\n",
        ])
        try:
            result = analyze_files([f2, f1], limits=AnalysisLimits(max_files=3, max_total_bytes=1_000_000, max_rows=1000))
            self.assertEqual(result["file_count"], 2)
            self.assertEqual(result["rows"], 3)
            self.assertIn("regulator_quality", result)
            self.assertGreater(result["regulator_quality"]["p95_abs_grid_w"], 0)
            self.assertEqual(result["cross_charge"]["critical_overlap_events"], 1)
            self.assertIn(result["cross_charge"]["rating"], {"yellow", "red"})
            self.assertTrue(any(e["type"] == "cross_charge_overlap" for e in result["events"]))
            self.assertIn("cross_charge_rating", summary_csv(result))
        finally:
            os.remove(f1)
            os.remove(f2)

    def test_multi_file_limits_reject_too_many_files(self):
        f = self._write_csv([f"{LEGACY_V3_SCHEMA};12.8;1000;3;2026-05-29 10:00:00;0;0;0;0;0;50;HOLD;;0;ok\n"])
        try:
            with self.assertRaises(ValueError):
                analyze_files([f, f], limits=AnalysisLimits(max_files=0, max_total_bytes=1_000_000, max_rows=1000))
        finally:
            os.remove(f)


if __name__ == "__main__":
    unittest.main()
