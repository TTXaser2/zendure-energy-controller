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
        self.assertEqual(246, len(STANDARD_HEADER))
        self.assertEqual(len(STANDARD_HEADER), len(set(STANDARD_HEADER)))
        self.assertEqual("schema_version", STANDARD_HEADER[0])
        self.assertEqual("command_resync_reason", STANDARD_HEADER[-1])
        for field in STANDARD_HEADER:
            self.assertFalse(field.endswith("_json"), field)
        for field in (
            "command_readback_matches_desired",
            "command_late_effect_guard_active",
            "command_late_effect_guard_activation_count",
            "command_ac_mode_change_count",
            "physical_power_direction_change_count",
            "zendure_device_inverse_max_power_source",
            "zendure_device_inverse_max_power_age_s",
            "harvest_target_semantics",
            "harvest_reference_charge_w",
            "harvest_reference_charge_valid",
            "harvest_candidate_delta_w",
            "harvest_candidate_absolute_w",
            "harvest_input_time_skew_s",
            "harvest_network_target_w",
            "harvest_total_available_charge_w",
            "harvest_primary_share_target_w",
            "harvest_zendure_share_target_w",
            "harvest_export_capture_target_w",
            "harvest_target_selected_by",
            "harvest_calculation_branch",
            "harvest_entry_min_export_w",
            "harvest_command_path_eligible",
            "harvest_command_path_block_reason",
        ):
            self.assertIn(field, STANDARD_HEADER)

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
