import os
import tempfile
import unittest

from tools.replay_core import LEGACY_V3_SCHEMA, analyze_file


class ReplayCoreTests(unittest.TestCase):
    def test_analyze_file_accepts_only_v3_and_calculates_energy(self):
        content = (
            "schema;controller_version;epoch;dt_s;grid_power_w;zendure_soc_percent;mode;technical_limiters;mqtt_commands_sent_in_cycle;charge_acceptance_state\n"
            f"{LEGACY_V3_SCHEMA};12.7;1000;3;1200;50;DISCHARGE;;1;ok\n"
            f"{LEGACY_V3_SCHEMA};12.7;1003;3;-600;99;NIGHT_DISCHARGE;SMA_DISCHARGE;0;limited\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(content)
            name = f.name
        try:
            result = analyze_file(name, min_soc_percent=15, max_soc_percent=99)
            self.assertEqual(result["rows"], 2)
            self.assertGreater(result["grid_import_kwh"], 0)
            self.assertGreater(result["grid_export_kwh"], 0)
            self.assertEqual(result["cross_charge_events"], 1)
            self.assertEqual(result["charge_acceptance_states"]["limited"], 1)
        finally:
            os.remove(name)


if __name__ == "__main__":
    unittest.main()
