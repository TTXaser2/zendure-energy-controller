import unittest

from zendure_local_api import zendure_temp_to_celsius


class TemperatureNormalizationTests(unittest.TestCase):
    def test_celsius_is_preserved(self):
        self.assertEqual(zendure_temp_to_celsius(44.0), 44.0)

    def test_kelvin_is_converted(self):
        self.assertEqual(zendure_temp_to_celsius(309.1), 36.0)

    def test_deci_kelvin_is_converted(self):
        self.assertEqual(zendure_temp_to_celsius(3170), 43.9)

    def test_implausible_value_is_rejected(self):
        self.assertIsNone(zendure_temp_to_celsius(9999))


if __name__ == "__main__":
    unittest.main()
