import csv
import io
import unittest

from csv_logger import GRAPH_EXPORT_SCHEMA, rows_to_csv
from measurement import classify_charge_acceptance, derive_zendure_actual_power, signed_zendure_target_w


class MeasurementCompatibilityTests(unittest.TestCase):
    def test_signed_target_uses_positive_charge_negative_discharge(self):
        self.assertEqual(signed_zendure_target_w(500, 0), 500)
        self.assertEqual(signed_zendure_target_w(0, 400), -400)
        self.assertEqual(signed_zendure_target_w(200, 300), -300)

    def test_zendure_actual_power_sign_convention(self):
        self.assertEqual(derive_zendure_actual_power(grid_input=720, output_home=0)["signed_power_w"], 720)
        self.assertEqual(derive_zendure_actual_power(grid_input=0, output_home=650)["signed_power_w"], -650)
        derived = derive_zendure_actual_power(pack_input=200, output_pack=500)
        self.assertEqual(0, derived["signed_power_w"])
        self.assertEqual(300, derived["battery_signed_power_w"])

    def test_graph_export_is_semicolon_separated_and_not_measurement(self):
        text = rows_to_csv([{"grid_power_w": -120.5, "zendure_target_power_w": 200}])
        first_line = text.splitlines()[0]
        self.assertTrue(first_line.startswith("schema;schema_version;"))
        self.assertNotIn(",", first_line)
        parsed = list(csv.DictReader(io.StringIO(text), delimiter=";"))
        self.assertEqual(parsed[0]["schema"], GRAPH_EXPORT_SCHEMA)
        self.assertEqual(parsed[0]["schema_version"], "1.0")
        self.assertNotEqual(parsed[0]["schema"], "ZEC-MEASUREMENT-V4")

    def test_charge_acceptance_diagnostic_detects_not_accepting(self):
        result = classify_charge_acceptance(
            soc_percent=98,
            max_soc_percent=99,
            target_charge_w=1000,
            actual_charge_w=50,
            grid_power_w=-400,
        )
        self.assertEqual(result["state"], "not_accepting")


if __name__ == "__main__":
    unittest.main()
