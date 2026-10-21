# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

"""Passive SMA Energy Meter / Sunny Home Manager 2.0 UDP listener.

The SMA Energy Meter protocol is broadcast locally via UDP multicast, commonly
239.12.255.254:9522. This client runs as a background listener, stores the
latest decoded grid power and never blocks the controller cycle waiting for a
packet. RC5 keeps the multi-meter safeguards and restores the RC3-compatible
socket default because the live setup showed EVCC + ZEC stability with that
mode. Additional socket modes and packet-gap diagnostics are exposed for
controlled coexistence testing with further local SMA listeners.
"""

from __future__ import annotations

import json
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

try:  # Linux/Raspberry Pi path; tests may monkeypatch the resolver.
    import fcntl  # type: ignore
except Exception:  # pragma: no cover - non-Linux fallback
    fcntl = None  # type: ignore


@dataclass
class SmaEnergyMeterReading:
    grid_power_w: float
    consumption_power_w: Optional[float]
    feedin_power_w: Optional[float]
    received_epoch: float
    packet_len: int
    susy_id: Optional[int] = None
    serial_number: Optional[int] = None
    source_ip: str = ""

    @property
    def device_key(self) -> str:
        if self.serial_number is not None:
            return str(self.serial_number)
        if self.susy_id is not None:
            return f"susy:{self.susy_id}"
        return self.source_ip or "unknown"


@dataclass
class SmaEnergyMeterSnapshot:
    enabled: bool = False
    running: bool = False
    configured_group: str = "239.12.255.254"
    configured_port: int = 9522
    configured_interface: str = ""
    resolved_interface_ip: str = ""
    configured_susy_id: str = ""
    configured_serial: str = ""
    selected_device_key: str = ""
    selected_device_matched: bool = False
    detected_device_count: int = 0
    devices_json: str = "{}"
    last_power_w: Optional[float] = None
    last_consumption_power_w: Optional[float] = None
    last_feedin_power_w: Optional[float] = None
    last_received_epoch: Optional[float] = None
    last_susy_id: Optional[int] = None
    last_serial_number: Optional[int] = None
    packet_count: int = 0
    decode_count: int = 0
    ignored_count: int = 0
    error_count: int = 0
    last_error: str = "none"
    configured_socket_mode: str = "group_bind"
    effective_socket_mode: str = "group_bind"
    bind_address: str = ""
    bind_mode: str = ""
    reuseaddr_enabled: bool = False
    reuseport_requested: bool = False
    reuseport_supported: bool = False
    reuseport_enabled: bool = False
    reuseport_error: str = ""
    multicast_if_set: bool = False
    packet_rate_per_min: float = 0.0
    packet_gap_warn_s: float = 5.0
    last_packet_gap_s: Optional[float] = None
    max_packet_gap_s: Optional[float] = None
    last_large_gap_s: Optional[float] = None
    last_large_gap_epoch: Optional[float] = None

    @property
    def age_s(self) -> Optional[int]:
        if self.last_received_epoch is None:
            return None
        return max(0, int(time.time() - self.last_received_epoch))


def _read_u16_be(data: bytes, offset: int) -> Optional[int]:
    if offset < 0 or offset + 2 > len(data):
        return None
    value = struct.unpack_from(">H", data, offset)[0]
    if value in (0xFFFF,):
        return None
    return value


def _read_u32_be(data: bytes, offset: int) -> Optional[int]:
    if offset < 0 or offset + 4 > len(data):
        return None
    value = struct.unpack_from(">I", data, offset)[0]
    if value in (0xFFFFFFFF, 0x7FFFFFFF):
        return None
    return value


def _decode_speedwire_emeter(data: bytes) -> Optional[Tuple[int, int, Optional[float], Optional[float]]]:
    """Parse one complete SMA Net 2 / Energy Meter telegram, never scan raw bytes.

    Frame: SMA signature; Tag0 (group); Data2 (protocol 0x6069); end tag.
    Data2 holds a six-byte device address, a four-byte millisecond ticker,
    then length-delimited OBIS records (4-byte current / 8-byte energy).
    Unknown but well-formed records are skipped at their actual boundaries.
    See SMA EMETER-Protocol-TI-en-10, sections 3 and 4.
    """
    if len(data) < 32 or data[:4] != b"SMA\x00":
        return None
    offset = 4
    # Never accept an OBIS-shaped byte sequence in an unrelated protocol/tag.
    if data[offset:offset + 4] != b"\x00\x04\x02\xa0":
        return None
    if data[offset + 4:offset + 8] != b"\x00\x00\x00\x01":
        return None
    offset += 8
    if offset + 4 > len(data):
        return None
    length, tag = struct.unpack_from(">HH", data, offset)
    if tag != 0x0010 or length < 12:
        return None
    data_start = offset + 4
    data_end = data_start + length
    # A complete Data2 frame must end with exactly one empty end-of-data tag.
    if data_end + 4 != len(data) or data[data_end:] != b"\x00\x00\x00\x00":
        return None
    if data[data_start:data_start + 2] != b"\x60\x69":
        return None
    susy, serial = struct.unpack_from(">HI", data, data_start + 2)
    if susy in (0, 0xFFFF) or serial in (0, 0xFFFFFFFF):
        return None
    # Four-byte ticker begins after the device identifier; only records
    # starting after it may influence the measured power.
    offset = data_start + 12
    consumption = feedin = None
    seen_consumption = seen_feedin = False
    while offset < data_end:
        if offset + 4 > data_end:
            return None
        code = data[offset:offset + 4]
        record_type = code[2]
        if record_type == 4:
            value_len = 4
        elif record_type == 8:
            value_len = 8
        elif code == b"\x90\x00\x00\x00":  # manufacturer software version
            value_len = 4
        else:
            # An unknown record length cannot safely be skipped. Reject the
            # whole telegram rather than misinterpret its payload as power.
            return None
        value_offset = offset + 4
        if value_offset + value_len > data_end:
            return None
        if code in (b"\x00\x01\x04\x00", b"\x00\x02\x04\x00"):
            raw = _read_u32_be(data, value_offset)
            if raw is None:
                return None
            value = raw / 10.0
            if code[1] == 1:
                if seen_consumption:
                    return None
                consumption, seen_consumption = value, True
            else:
                if seen_feedin:
                    return None
                feedin, seen_feedin = value, True
        offset = value_offset + value_len
    if offset != data_end or not (seen_consumption or seen_feedin):
        return None
    return susy, serial, consumption, feedin


def parse_sma_energy_meter_packet(data: bytes, received_epoch: Optional[float] = None, source_ip: str = "") -> Optional[SmaEnergyMeterReading]:
    """Return signed grid power only for a structurally valid SMA EM telegram."""
    parsed = _decode_speedwire_emeter(data)
    if parsed is None:
        return None
    susy_id, serial_number, consumption, feedin = parsed
    c = float(consumption or 0.0)
    f = float(feedin or 0.0)
    return SmaEnergyMeterReading(
        grid_power_w=round(c - f, 1),
        consumption_power_w=round(c, 1) if consumption is not None else None,
        feedin_power_w=round(f, 1) if feedin is not None else None,
        received_epoch=float(received_epoch if received_epoch is not None else time.time()),
        packet_len=len(data),
        susy_id=susy_id,
        serial_number=serial_number,
        source_ip=source_ip,
    )


def _cfg_int_or_none(cfg: Dict[str, Any], key: str) -> Optional[int]:
    value = cfg.get(key)
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text, 0)
    except Exception:
        return None


def _get_interface_ipv4(interface: str) -> str:
    """Resolve an interface name like 'eth0' to its local IPv4 address.

    If *interface* already looks like an IPv4 address it is returned unchanged.
    Empty string means automatic interface selection via 0.0.0.0.
    """
    iface = str(interface or "").strip()
    if not iface:
        return "0.0.0.0"
    try:
        socket.inet_aton(iface)
        return iface
    except OSError:
        pass
    if fcntl is None:
        raise RuntimeError(f"Interface '{iface}' kann auf diesem System nicht zu einer IPv4-Adresse aufgelöst werden")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        packed = struct.pack("256s", iface.encode("utf-8")[:15])
        res = fcntl.ioctl(s.fileno(), 0x8915, packed)  # SIOCGIFADDR
        return socket.inet_ntoa(res[20:24])
    finally:
        s.close()


def _device_record(reading: SmaEnergyMeterReading) -> Dict[str, Any]:
    return {
        "susy_id": reading.susy_id,
        "serial_number": reading.serial_number,
        "source_ip": reading.source_ip,
        "last_power_w": reading.grid_power_w,
        "last_consumption_power_w": reading.consumption_power_w,
        "last_feedin_power_w": reading.feedin_power_w,
        "last_received_epoch": reading.received_epoch,
        "packet_len": reading.packet_len,
        "packet_count": 1,
    }


SUPPORTED_SOCKET_MODES = {
    "auto",
    "rc3_compatible",
    "reuseport",
    "reuseaddr_only",
    "unimeter_like",
    "group_bind",
}


def normalize_socket_mode(value: Any) -> str:
    text = str(value or "group_bind").strip().lower().replace("-", "_")
    if text == "auto":
        return "group_bind"
    if text not in SUPPORTED_SOCKET_MODES:
        return "group_bind"
    return text


def _cfg_float(cfg: Dict[str, Any], key: str, default: float) -> float:
    try:
        return float(cfg.get(key, default))
    except Exception:
        return float(default)


class SmaEnergyMeterClient:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._sock: Optional[socket.socket] = None
        self._snapshot = SmaEnergyMeterSnapshot()
        self._devices: Dict[str, Dict[str, Any]] = {}
        self._current_key: Optional[Tuple[str, int, str, str, str]] = None

    def ensure_started(self, cfg: Dict[str, Any]) -> None:
        enabled = bool(cfg.get("SMA_ENERGY_METER_PASSIVE_ENABLED", False)) or str(cfg.get("GRID_METER_SOURCE", "shelly_http")) == "sma_energy_meter_udp"
        group = str(cfg.get("SMA_ENERGY_METER_GROUP", "239.12.255.254") or "239.12.255.254")
        port = int(cfg.get("SMA_ENERGY_METER_PORT", 9522) or 9522)
        interface = str(cfg.get("SMA_ENERGY_METER_INTERFACE", "") or "")
        susy_filter = str(cfg.get("SMA_ENERGY_METER_SUSY_ID", "") or "").strip()
        serial_filter = str(cfg.get("SMA_ENERGY_METER_SERIAL", "") or "").strip()
        socket_mode = normalize_socket_mode(cfg.get("SMA_ENERGY_METER_SOCKET_MODE", "group_bind"))
        gap_warn_s = max(1.0, _cfg_float(cfg, "SMA_ENERGY_METER_PACKET_GAP_WARN_SECONDS", 5.0))
        key = (group, port, interface, susy_filter, serial_filter, socket_mode, gap_warn_s)
        with self._lock:
            self._snapshot.enabled = enabled
            self._snapshot.configured_group = group
            self._snapshot.configured_port = port
            self._snapshot.configured_interface = interface
            self._snapshot.configured_susy_id = susy_filter
            self._snapshot.configured_serial = serial_filter
            self._snapshot.configured_socket_mode = socket_mode
            self._snapshot.packet_gap_warn_s = gap_warn_s
        if not enabled:
            self.stop()
            return
        with self._lock:
            if self._thread and self._thread.is_alive() and self._current_key == key:
                return
        self.stop()
        self._stop.clear()
        with self._lock:
            self._current_key = key
            self._devices = {}
            self._snapshot.running = False
            self._snapshot.last_error = "starting"
            self._snapshot.devices_json = "{}"
            self._snapshot.detected_device_count = 0
            self._snapshot.packet_count = 0
            self._snapshot.decode_count = 0
            self._snapshot.ignored_count = 0
            self._snapshot.error_count = 0
            self._snapshot.packet_rate_per_min = 0.0
            self._snapshot.last_packet_gap_s = None
            self._snapshot.max_packet_gap_s = None
            self._snapshot.last_large_gap_s = None
            self._snapshot.last_large_gap_epoch = None
        self._thread = threading.Thread(target=self._listen_loop, args=(key,), name="sma-energy-meter-listener", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        sock = self._sock
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass
        with self._lock:
            self._sock = None
            self._snapshot.running = False
            self._current_key = None

    def read_grid_power(self, cfg: Dict[str, Any]) -> float:
        self.ensure_started(cfg)
        timeout_s = int(cfg.get("SMA_ENERGY_METER_STALE_TIMEOUT_SECONDS", cfg.get("SHELLY_STALE_TIMEOUT_SECONDS", 15)) or 15)
        snap = self.snapshot()
        if snap.last_power_w is None or snap.last_received_epoch is None:
            raise RuntimeError("SMA Energy Meter: noch kein gültiges Paket vom ausgewählten Gerät empfangen")
        age = time.time() - snap.last_received_epoch
        if age > timeout_s:
            raise RuntimeError(f"SMA Energy Meter: letzter Wert ist nicht aktuell ({int(age)} s, Timeout {timeout_s} s)")
        return float(snap.last_power_w)

    def snapshot(self) -> SmaEnergyMeterSnapshot:
        with self._lock:
            return SmaEnergyMeterSnapshot(**self._snapshot.__dict__)

    def _listen_loop(self, key: Tuple[Any, ...]) -> None:
        group, port, interface, susy_filter_text, serial_filter_text, socket_mode, gap_warn_s = key
        susy_filter = int(susy_filter_text, 0) if susy_filter_text else None
        serial_filter = int(serial_filter_text, 0) if serial_filter_text else None
        try:
            iface_ip = _get_interface_ipv4(interface)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            reuseaddr_enabled = False
            reuseport_requested = socket_mode in {"rc3_compatible", "reuseport"}
            reuseport_supported = bool(hasattr(socket, "SO_REUSEPORT"))
            reuseport_enabled = False
            reuseport_error = ""
            bind_address = ""
            bind_mode = ""
            multicast_if_set = False

            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            reuseaddr_enabled = True
            if reuseport_requested and reuseport_supported:
                try:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                    reuseport_enabled = True
                except OSError as exc:
                    reuseport_error = str(exc)
            elif reuseport_requested and not reuseport_supported:
                reuseport_error = "SO_REUSEPORT not supported"

            try:
                if socket_mode == "group_bind":
                    sock.bind((group, port))
                    bind_address = group
                    bind_mode = "group"
                else:
                    sock.bind(("", port))
                    bind_address = "0.0.0.0"
                    bind_mode = "wildcard"
            except OSError as exc:
                sock.bind((group, port))
                bind_address = group
                bind_mode = f"fallback_group_after_{exc.__class__.__name__}"

            mreq = socket.inet_aton(group) + socket.inet_aton(iface_ip)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            if socket_mode != "unimeter_like":
                try:
                    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(iface_ip))
                    multicast_if_set = True
                except OSError:
                    multicast_if_set = False
            sock.settimeout(1.0)
            listener_started = time.time()
            last_packet_epoch: Optional[float] = None
            with self._lock:
                self._sock = sock
                self._snapshot.running = True
                self._snapshot.resolved_interface_ip = iface_ip
                self._snapshot.last_error = "none"
                self._snapshot.effective_socket_mode = str(socket_mode)
                self._snapshot.bind_address = bind_address
                self._snapshot.bind_mode = bind_mode
                self._snapshot.reuseaddr_enabled = reuseaddr_enabled
                self._snapshot.reuseport_requested = reuseport_requested
                self._snapshot.reuseport_supported = reuseport_supported
                self._snapshot.reuseport_enabled = reuseport_enabled
                self._snapshot.reuseport_error = reuseport_error
                self._snapshot.multicast_if_set = multicast_if_set
            while not self._stop.is_set():
                try:
                    packet, addr = sock.recvfrom(4096)
                except socket.timeout:
                    continue
                except OSError as exc:
                    if not self._stop.is_set():
                        self._record_error(str(exc))
                    break
                now = time.time()
                packet_gap = None if last_packet_epoch is None else max(0.0, now - last_packet_epoch)
                last_packet_epoch = now
                source_ip = addr[0] if addr else ""
                reading = parse_sma_energy_meter_packet(packet, now, source_ip=source_ip)
                with self._lock:
                    self._snapshot.packet_count += 1
                    elapsed = max(1.0, now - listener_started)
                    self._snapshot.packet_rate_per_min = round(float(self._snapshot.packet_count) * 60.0 / elapsed, 1)
                    if packet_gap is not None:
                        rounded_gap = round(float(packet_gap), 3)
                        self._snapshot.last_packet_gap_s = rounded_gap
                        if self._snapshot.max_packet_gap_s is None or rounded_gap > float(self._snapshot.max_packet_gap_s):
                            self._snapshot.max_packet_gap_s = rounded_gap
                        if rounded_gap >= float(gap_warn_s):
                            self._snapshot.last_large_gap_s = rounded_gap
                            self._snapshot.last_large_gap_epoch = now
                    if reading is not None:
                        self._snapshot.decode_count += 1
                        self._record_device_locked(reading)
                        if self._matches_filter(reading, susy_filter, serial_filter):
                            self._snapshot.selected_device_matched = True
                            self._snapshot.selected_device_key = reading.device_key
                            self._snapshot.last_power_w = reading.grid_power_w
                            self._snapshot.last_consumption_power_w = reading.consumption_power_w
                            self._snapshot.last_feedin_power_w = reading.feedin_power_w
                            self._snapshot.last_received_epoch = reading.received_epoch
                            self._snapshot.last_susy_id = reading.susy_id
                            self._snapshot.last_serial_number = reading.serial_number
                        else:
                            self._snapshot.ignored_count += 1
                            if serial_filter is not None or susy_filter is not None:
                                self._snapshot.last_error = "Paket von anderem SMA Energy Meter ignoriert"
                    else:
                        self._snapshot.error_count += 1
                        self._snapshot.last_error = "Paket empfangen, aber kein bekannter Gesamtleistungswert dekodiert"
        except Exception as exc:
            self._record_error(str(exc))
        finally:
            with self._lock:
                self._snapshot.running = False
            try:
                if self._sock is not None:
                    self._sock.close()
            except Exception:
                pass

    @staticmethod
    def _matches_filter(reading: SmaEnergyMeterReading, susy_filter: Optional[int], serial_filter: Optional[int]) -> bool:
        if serial_filter is not None and reading.serial_number != serial_filter:
            return False
        if susy_filter is not None and reading.susy_id != susy_filter:
            return False
        return True

    def _record_device_locked(self, reading: SmaEnergyMeterReading) -> None:
        key = reading.device_key
        if key in self._devices:
            record = self._devices[key]
            record.update(_device_record(reading))
            record["packet_count"] = int(record.get("packet_count", 0)) + 1
        else:
            self._devices[key] = _device_record(reading)
        self._snapshot.detected_device_count = len(self._devices)
        self._snapshot.devices_json = json.dumps(self._devices, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def _record_error(self, message: str) -> None:
        with self._lock:
            self._snapshot.error_count += 1
            self._snapshot.last_error = message
