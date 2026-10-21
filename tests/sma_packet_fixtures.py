"""Canonical spec-conformant SMA EM synthetic UDP frames for regression tests."""
import struct


def make_packet(*, susy=999, serial=1234567890, import_w=1234.5,
                export_w=234.5, extra_records=(), protocol=0x6069,
                group=1, tail=b'\x00\x00\x00\x00'):
    records = b''.join(code + value for code, value in (
        (b'\x00\x01\x04\x00', struct.pack('>I', round(import_w * 10))),
        (b'\x00\x02\x04\x00', struct.pack('>I', round(export_w * 10))),
        *extra_records,
    ))
    payload = struct.pack('>HHII', protocol, susy, serial, 234567) + records
    return (b'SMA\x00' + struct.pack('>HHI', 4, 0x02A0, group) +
            struct.pack('>HH', len(payload), 0x0010) + payload + tail)
