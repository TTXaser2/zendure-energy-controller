"""Release-blocking coverage for a structured SMA Speedwire/OBIS decoder."""
import struct
import unittest
from sma_energy_meter import parse_sma_energy_meter_packet, SmaEnergyMeterClient
from sma_packet_fixtures import make_packet


class ParserSecurityContract(unittest.TestCase):
    def test_valid_including_unknown_records_and_eight_byte_energy(self):
        p = make_packet(extra_records=[
            (b'\x00\x01\x08\x00', struct.pack('>Q', 123456789)),
            (b'\x00\x03\x04\x00', struct.pack('>I', 42)),
            (b'\x90\x00\x00\x00', b'\x01\x02\x03\x04'),
        ])
        r = parse_sma_energy_meter_packet(p)
        self.assertEqual(r.grid_power_w, 1000.0)
        self.assertEqual((r.susy_id, r.serial_number), (999, 1234567890))

    def test_payload_signature_is_not_a_record(self):
        # The 8-byte energy payload contains an apparently valid OBIS signature.
        false = b'\x00\x01\x04\x00' + struct.pack('>I', 199999)
        packet = make_packet(import_w=0, export_w=0,
                             extra_records=[(b'\x00\x01\x08\x00', false)])
        self.assertEqual(parse_sma_energy_meter_packet(packet).grid_power_w, 0.0)

    def test_wrong_protocol_group_signature_and_tag(self):
        good = make_packet()
        bad = [make_packet(protocol=0x6065), make_packet(group=2),
               b'BAD\x00' + good[4:], good[:6] + b'\x02\xa1' + good[8:],
               good[:14] + b'\x00\x20' + good[16:]]
        for packet in bad:
            with self.subTest(packet=packet[:20].hex()):
                self.assertIsNone(parse_sma_energy_meter_packet(packet))

    def test_truncation_extension_and_bad_record_lengths(self):
        good = make_packet(extra_records=[(b'\x00\x01\x08\x00', struct.pack('>Q', 4))])
        for packet in (good[:i] for i in range(len(good))):
            self.assertIsNone(parse_sma_energy_meter_packet(packet))
        self.assertIsNone(parse_sma_energy_meter_packet(good + b'\x00'))
        bad = make_packet(extra_records=[(b'\x00\x03\x09\x00', b'12345678')])
        self.assertIsNone(parse_sma_energy_meter_packet(bad))

    def test_duplicate_sum_record_is_rejected(self):
        p = make_packet(extra_records=[(b'\x00\x01\x04\x00', struct.pack('>I', 1111))])
        self.assertIsNone(parse_sma_energy_meter_packet(p))

    def test_susy_serial_filter_two_devices(self):
        client = SmaEnergyMeterClient()
        a = parse_sma_energy_meter_packet(make_packet(susy=999, serial=1234567890))
        b = parse_sma_energy_meter_packet(make_packet(susy=999, serial=1901402945))
        self.assertTrue(client._matches_filter(a, 999, 1234567890))
        self.assertFalse(client._matches_filter(b, 999, 1234567890))
        self.assertFalse(client._matches_filter(a, 999, 1901402945))


if __name__ == '__main__':
    unittest.main()
