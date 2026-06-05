import os
import tempfile
import unittest

from tools.replay_core import CSV_SCHEMA, analyze_files
from tools.replay_report import command_efficiency_table, deadband_table, fair_regulator_table, recommendations_table, summary_cards


class V1283AnalysisTests(unittest.TestCase):
    def _write_csv(self, rows):
        header = (
            "schema;controller_version;epoch;dt_s;datetime_local;grid_power_w;zendure_target_power_w;"
            "zendure_actual_power_w;second_battery_power_w;second_battery_discharge_power_w;zendure_soc_percent;"
            "mode;technical_limiters;mqtt_commands_sent_in_cycle;charge_acceptance_state\n"
        )
        f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
        f.write(header + "".join(rows))
        f.close()
        return f.name

    def test_fair_quality_separates_non_controllable_max_soc_export(self):
        f = self._write_csv([
            f"{CSV_SCHEMA};12.8.4;1000;3;2026-05-29 12:00:00;-4000;2100;0;0;0;99;SAFE_STATE;;0;not_accepting\n",
            f"{CSV_SCHEMA};12.8.4;1003;3;2026-05-29 12:00:03;-200;300;250;0;0;50;CHARGE;;1;ok\n",
        ])
        try:
            result = analyze_files([f], max_soc_percent=99, max_charge_power_w=2100, max_discharge_power_w=2100)
            fair = result["fair_regulator_quality"]
            self.assertGreater(fair["non_controllable_percent"], 80)
            self.assertLess(fair["controllable_percent"], 20)
            self.assertIn("recommendations", result)
            self.assertIn("Beeinflussbare", fair_regulator_table(result))
            self.assertIn("Deadband", deadband_table(result))
            self.assertIn("MQTT", command_efficiency_table(result))
            self.assertIn("card", summary_cards(result))
            self.assertIn("Empfehlung", recommendations_table(result))
        finally:
            os.remove(f)


if __name__ == "__main__":
    unittest.main()
