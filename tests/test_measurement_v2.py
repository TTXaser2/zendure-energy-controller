import csv
import io
import unittest

from csv_logger import CSV_FIELDS, rows_to_csv
from measurement import classify_charge_acceptance, derive_zendure_actual_power, signed_zendure_target_w
from version import CSV_SCHEMA


class MeasurementV2Tests(unittest.TestCase):
    def test_signed_target_uses_positive_charge_negative_discharge(self):
        self.assertEqual(signed_zendure_target_w(500, 0), 500)
        self.assertEqual(signed_zendure_target_w(0, 400), -400)
        self.assertEqual(signed_zendure_target_w(200, 300), -300)

    def test_zendure_actual_power_sign_convention(self):
        self.assertEqual(derive_zendure_actual_power(grid_input=720, output_home=0)["signed_power_w"], 720)
        self.assertEqual(derive_zendure_actual_power(grid_input=0, output_home=650)["signed_power_w"], -650)
        self.assertEqual(derive_zendure_actual_power(pack_input=200, output_pack=500)["signed_power_w"], -500)

    def test_csv_v2_uses_semicolon_and_schema_column(self):
        text = rows_to_csv([{"schema": CSV_SCHEMA, "grid_power_w": -120.5, "zendure_target_power_w": 200}])
        first_line = text.splitlines()[0]
        self.assertIn("schema;controller_version", first_line)
        self.assertNotIn(",", first_line)
        parsed = list(csv.DictReader(io.StringIO(text), delimiter=";"))
        self.assertEqual(parsed[0]["schema"], CSV_SCHEMA)
        self.assertIn("zendure_actual_power_w", CSV_FIELDS)

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
