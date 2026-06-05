import unittest

from web_ui import signed_power


class PowerSignFormattingTests(unittest.TestCase):
    def test_signed_power_uses_plus_for_charge(self):
        self.assertEqual(signed_power(120), "+120 W")

    def test_signed_power_uses_minus_for_discharge(self):
        self.assertEqual(signed_power(-120), "-120 W")

    def test_signed_power_zero_has_no_sign(self):
        self.assertEqual(signed_power(0), "0 W")


if __name__ == "__main__":
    unittest.main()
