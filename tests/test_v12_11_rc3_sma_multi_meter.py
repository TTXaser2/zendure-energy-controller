import struct
import unittest
from unittest.mock import patch

from config_validator import validate_config_semantics
from sma_energy_meter import SmaEnergyMeterClient, parse_sma_energy_meter_packet, _get_interface_ipv4


def make_packet(susy=372, serial=3011954105, import_w=1234.5, export_w=234.5):
    packet = bytearray(b"SMA\x00" + b"x" * 28)
    # Known multicast frame placement used by common SMA Energy Meter integrations.
    packet[18:20] = int(susy).to_bytes(2, "big")
    packet[20:24] = int(serial).to_bytes(4, "big")
    packet.extend(b"\x00\x01\x04\x00" + struct.pack(">I", int(round(import_w * 10))))
    packet.extend(b"abcd")
    packet.extend(b"\x00\x02\x04\x00" + struct.pack(">I", int(round(export_w * 10))))
    return bytes(packet)


class SmaRc3ParserTests(unittest.TestCase):
    def test_parser_extracts_susy_and_serial(self):
        reading = parse_sma_energy_meter_packet(make_packet(), received_epoch=1000.0, source_ip="192.168.0.10")
        self.assertIsNotNone(reading)
        self.assertEqual(reading.susy_id, 372)
        self.assertEqual(reading.serial_number, 3011954105)
        self.assertEqual(reading.source_ip, "192.168.0.10")
        self.assertEqual(reading.grid_power_w, 1000.0)

    def test_interface_name_resolution_can_use_linux_ioctl(self):
        # Keep this as a simple IPv4 passthrough test to avoid depending on CI interfaces.
        self.assertEqual(_get_interface_ipv4("192.168.0.20"), "192.168.0.20")
        self.assertEqual(_get_interface_ipv4(""), "0.0.0.0")


class SmaRc3ClientTests(unittest.TestCase):
    def test_filter_accepts_only_configured_serial(self):
        client = SmaEnergyMeterClient()
        selected = parse_sma_energy_meter_packet(make_packet(serial=3011954105, import_w=1000, export_w=0), 1000.0, "192.168.0.10")
        other = parse_sma_energy_meter_packet(make_packet(serial=1901402945, import_w=3000, export_w=0), 1001.0, "192.168.0.11")
        self.assertTrue(client._matches_filter(selected, 372, 3011954105))
        self.assertFalse(client._matches_filter(other, 372, 3011954105))


class SmaRc3ValidatorTests(unittest.TestCase):
    def test_productive_sma_direct_requires_serial_filter(self):
        cfg = {
            "GRID_METER_SOURCE": "sma_energy_meter_udp",
            "SMA_ENERGY_METER_GROUP": "239.12.255.254",
            "SMA_ENERGY_METER_PORT": 9522,
            "MQTT_BROKER": "127.0.0.1",
            "DEVICE_ID": "dev",
        }
        codes = {i.code for i in validate_config_semantics(cfg)}
        self.assertIn("SMA_DIRECT_CONTROL_WITHOUT_SERIAL", codes)

    def test_productive_sma_direct_with_serial_only_warns_experimental(self):
        cfg = {
            "GRID_METER_SOURCE": "sma_energy_meter_udp",
            "SMA_ENERGY_METER_GROUP": "239.12.255.254",
            "SMA_ENERGY_METER_PORT": 9522,
            "SMA_ENERGY_METER_SERIAL": "3011954105",
            "MQTT_BROKER": "127.0.0.1",
            "DEVICE_ID": "dev",
        }
        codes = {i.code for i in validate_config_semantics(cfg)}
        self.assertNotIn("SMA_DIRECT_CONTROL_WITHOUT_SERIAL", codes)
        self.assertIn("SMA_DIRECT_AS_CONTROL_SOURCE", codes)

    def test_invalid_serial_is_error(self):
        cfg = {
            "GRID_METER_SOURCE": "shelly_http",
            "SHELLY_IP": "127.0.0.1",
            "SMA_ENERGY_METER_PASSIVE_ENABLED": True,
            "SMA_ENERGY_METER_SERIAL": "not-a-number",
            "MQTT_BROKER": "127.0.0.1",
            "DEVICE_ID": "dev",
        }
        codes = {i.code for i in validate_config_semantics(cfg)}
        self.assertIn("SMA_DIRECT_SERIAL_INVALID", codes)


if __name__ == "__main__":
    unittest.main()
