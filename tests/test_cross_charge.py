import unittest

from config_manager import DEFAULT_CONFIG
from cross_charge import parse_second_battery_value, second_battery_topics, normalize_discharge_power_w, display_power_w


class CrossChargeMappingTests(unittest.TestCase):
    def test_evcc_profile_expands_base_topic(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg["SECOND_BATTERY_SOURCE_PROFILE"] = "evcc_standard"
        cfg["SECOND_BATTERY_EVCC_BASE_TOPIC"] = "evcc/site/battery/devices/1/"
        self.assertEqual(second_battery_topics(cfg)["power"], "evcc/site/battery/devices/1/power")
        self.assertEqual(second_battery_topics(cfg)["soc"], "evcc/site/battery/devices/1/soc")
        self.assertEqual(second_battery_topics(cfg)["capacity"], "evcc/site/battery/devices/1/capacity")

    def test_custom_topics_are_used_directly(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg["SECOND_BATTERY_SOURCE_PROFILE"] = "custom"
        cfg["SECOND_BATTERY_POWER_TOPIC"] = "home/battery/power"
        cfg["SECOND_BATTERY_SOC_TOPIC"] = "home/battery/soc"
        cfg["SECOND_BATTERY_CAPACITY_TOPIC"] = "home/battery/capacity"
        self.assertEqual(second_battery_topics(cfg)["power"], "home/battery/power")

    def test_number_payload_and_units_are_normalized(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg["SECOND_BATTERY_SOURCE_PROFILE"] = "custom"
        cfg["SECOND_BATTERY_POWER_UNIT"] = "kW"
        cfg["SECOND_BATTERY_CAPACITY_UNIT"] = "Wh"
        self.assertEqual(parse_second_battery_value("power", "-1.25", cfg), -1250.0)
        self.assertEqual(parse_second_battery_value("capacity", "13000", cfg), 13.0)

    def test_json_payload_path_is_read(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg["SECOND_BATTERY_SOURCE_PROFILE"] = "custom"
        cfg["SECOND_BATTERY_POWER_PAYLOAD_TYPE"] = "json"
        cfg["SECOND_BATTERY_POWER_JSON_PATH"] = "battery.power"
        self.assertEqual(parse_second_battery_value("power", '{"battery":{"power":-850}}', cfg), -850.0)

    def test_discharge_sign_and_display_power(self):
        self.assertEqual(normalize_discharge_power_w(500, 1), 500.0)
        self.assertEqual(normalize_discharge_power_w(-500, -1), 500.0)
        self.assertEqual(display_power_w(500, 1), -500.0)
        self.assertEqual(display_power_w(-500, -1), -500.0)


if __name__ == "__main__":
    unittest.main()
