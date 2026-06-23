import unittest

from measurement_v4_contract import (
    EXTENDED_FIELDS,
    EXTENDED_HEADER,
    MISSING_REQUIRED_SOURCE_BITS,
    STANDARD_HEADER,
    ZENDURE_MQTT_GROUP_BITS,
    header_hash,
)


class MeasurementV4ContractTests(unittest.TestCase):
    def test_standard_header_is_exact_and_unique(self):
        self.assertEqual(116, len(STANDARD_HEADER))
        self.assertEqual(len(STANDARD_HEADER), len(set(STANDARD_HEADER)))
        self.assertEqual("schema_version", STANDARD_HEADER[0])
        self.assertEqual("command_delta_w", STANDARD_HEADER[-1])
        for field in STANDARD_HEADER:
            self.assertFalse(field.endswith("_json"), field)

    def test_extended_header_is_standard_plus_three_json_fields(self):
        self.assertEqual(STANDARD_HEADER + EXTENDED_FIELDS, EXTENDED_HEADER)
        self.assertEqual([
            "zendure_pack_temperatures_json",
            "zendure_headunit_temperatures_json",
            "zendure_mqtt_group_status_json",
        ], EXTENDED_FIELDS)

    def test_bitmask_contracts_are_stable(self):
        self.assertEqual(1, MISSING_REQUIRED_SOURCE_BITS["GRID_POWER"])
        self.assertEqual(2, MISSING_REQUIRED_SOURCE_BITS["ZENDURE_SOC"])
        self.assertEqual(4, MISSING_REQUIRED_SOURCE_BITS["ZENDURE_MQTT_COMMAND_PATH"])
        self.assertEqual(1, ZENDURE_MQTT_GROUP_BITS["ZENDURE_SOC"])
        self.assertEqual(2, ZENDURE_MQTT_GROUP_BITS["ZENDURE_HEADUNIT_POWER"])
        self.assertEqual(64, ZENDURE_MQTT_GROUP_BITS["ZENDURE_TEMPERATURES"])

    def test_header_hash_is_stable_for_semicolon_header_line(self):
        self.assertEqual(header_hash(STANDARD_HEADER), header_hash(list(STANDARD_HEADER)))
        self.assertNotEqual(header_hash(STANDARD_HEADER), header_hash(EXTENDED_HEADER))


if __name__ == "__main__":
    unittest.main()
