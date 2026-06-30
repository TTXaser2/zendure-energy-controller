import struct
import unittest

from config_validator import validate_config_semantics
from sma_energy_meter import parse_sma_energy_meter_packet, SmaEnergyMeterClient


class SmaEnergyMeterParserTests(unittest.TestCase):
    def test_parser_decodes_signed_grid_power_from_obis_values(self):
        packet = b"SMA\x00" + b"x" * 12
        packet += b"\x00\x01\x04\x00" + struct.pack(">I", 12345)  # 1234.5 W import
        packet += b"abcd"
        packet += b"\x00\x02\x04\x00" + struct.pack(">I", 2345)   # 234.5 W export
        reading = parse_sma_energy_meter_packet(packet, received_epoch=1000.0)
        self.assertIsNotNone(reading)
        self.assertEqual(reading.grid_power_w, 1000.0)
        self.assertEqual(reading.consumption_power_w, 1234.5)
        self.assertEqual(reading.feedin_power_w, 234.5)

    def test_parser_returns_none_without_known_power_values(self):
        self.assertIsNone(parse_sma_energy_meter_packet(b"SMA\x00" + b"x" * 20))


class SmaDirectConfigValidatorTests(unittest.TestCase):
    def test_sma_direct_control_source_warns_experimental(self):
        cfg = {
            "GRID_METER_SOURCE": "sma_energy_meter_udp",
            "SMA_ENERGY_METER_GROUP": "239.12.255.254",
            "SMA_ENERGY_METER_PORT": 9522,
            "MQTT_BROKER": "127.0.0.1",
            "DEVICE_ID": "dev",
        }
        issues = validate_config_semantics(cfg)
        codes = {i.code for i in issues}
        self.assertIn("SMA_DIRECT_AS_CONTROL_SOURCE", codes)
        self.assertNotIn("SHELLY_IP_MISSING", codes)

    def test_passive_sma_direct_is_info_when_shelly_is_control_source(self):
        cfg = {
            "GRID_METER_SOURCE": "shelly_http",
            "SHELLY_IP": "127.0.0.1",
            "SMA_ENERGY_METER_PASSIVE_ENABLED": True,
            "MQTT_BROKER": "127.0.0.1",
            "DEVICE_ID": "dev",
        }
        issues = validate_config_semantics(cfg)
        codes = {i.code for i in issues}
        self.assertIn("SMA_DIRECT_PASSIVE_ENABLED", codes)
        self.assertNotIn("GRID_SOURCE_INVALID", codes)


if __name__ == "__main__":
    unittest.main()
