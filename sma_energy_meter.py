# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

"""Passive SMA Energy Meter / Sunny Home Manager 2.0 UDP listener.

The SMA Energy Meter protocol is broadcast locally via UDP multicast, commonly
239.12.255.254:9522.  This client is intentionally conservative: it runs as a
background listener, stores the latest decoded grid power and never blocks the
controller cycle waiting for a packet.  In RC2 it is primarily a diagnostic and
an optional experimental grid source; Shelly/UniMeter remains the default.
"""

from __future__ import annotations

import socket
import struct
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass
class SmaEnergyMeterReading:
    grid_power_w: float
    consumption_power_w: Optional[float]
    feedin_power_w: Optional[float]
    received_epoch: float
    packet_len: int


@dataclass
class SmaEnergyMeterSnapshot:
    enabled: bool = False
    running: bool = False
    configured_group: str = "239.12.255.254"
    configured_port: int = 9522
    configured_interface: str = ""
    last_power_w: Optional[float] = None
    last_consumption_power_w: Optional[float] = None
    last_feedin_power_w: Optional[float] = None
    last_received_epoch: Optional[float] = None
    packet_count: int = 0
    decode_count: int = 0
    error_count: int = 0
    last_error: str = "none"

    @property
    def age_s(self) -> Optional[int]:
        if self.last_received_epoch is None:
            return None
        return max(0, int(time.time() - self.last_received_epoch))


def _read_u32_be(data: bytes, offset: int) -> Optional[int]:
    if offset < 0 or offset + 4 > len(data):
        return None
    value = struct.unpack_from(">I", data, offset)[0]
    if value in (0xFFFFFFFF, 0x7FFFFFFF):
        return None
    return value


def _find_obis_value(data: bytes, code: bytes) -> Optional[float]:
    """Find a 4-byte OBIS code and return the following u32 as Watt.

    Common SMA Energy Meter total instantaneous power values use the OBIS-like
    tags 00 01 04 00 (grid consumption) and 00 02 04 00 (feed-in).  The value is
    transported as 0.1 W in the packet variants used by Sunny Home Manager 2.0 /
    Energy Meter installations.  The parser deliberately scans the packet rather
    than depending on fixed offsets, because firmware versions may include
    additional fields before/after the values.
    """
    start = 0
    while True:
        idx = data.find(code, start)
        if idx < 0:
            return None
        raw = _read_u32_be(data, idx + len(code))
        if raw is not None:
            return raw / 10.0
        start = idx + 1


def parse_sma_energy_meter_packet(data: bytes, received_epoch: Optional[float] = None) -> Optional[SmaEnergyMeterReading]:
    """Decode total grid power from one SMA Energy Meter UDP packet.

    Returns signed grid power using ZEC convention:
      + = grid import / Netzbezug
      - = feed-in / Einspeisung
    """
    if not data or len(data) < 16:
        return None
    consumption = _find_obis_value(data, b"\x00\x01\x04\x00")
    feedin = _find_obis_value(data, b"\x00\x02\x04\x00")
    if consumption is None and feedin is None:
        return None
    c = float(consumption or 0.0)
    f = float(feedin or 0.0)
    return SmaEnergyMeterReading(
        grid_power_w=round(c - f, 1),
        consumption_power_w=round(c, 1) if consumption is not None else None,
        feedin_power_w=round(f, 1) if feedin is not None else None,
        received_epoch=float(received_epoch if received_epoch is not None else time.time()),
        packet_len=len(data),
    )


class SmaEnergyMeterClient:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._sock: Optional[socket.socket] = None
        self._snapshot = SmaEnergyMeterSnapshot()
        self._current_key: Optional[Tuple[str, int, str]] = None

    def ensure_started(self, cfg: Dict[str, Any]) -> None:
        enabled = bool(cfg.get("SMA_ENERGY_METER_PASSIVE_ENABLED", False)) or str(cfg.get("GRID_METER_SOURCE", "shelly_http")) == "sma_energy_meter_udp"
        group = str(cfg.get("SMA_ENERGY_METER_GROUP", "239.12.255.254") or "239.12.255.254")
        port = int(cfg.get("SMA_ENERGY_METER_PORT", 9522) or 9522)
        interface = str(cfg.get("SMA_ENERGY_METER_INTERFACE", "") or "")
        key = (group, port, interface)
        with self._lock:
            self._snapshot.enabled = enabled
            self._snapshot.configured_group = group
            self._snapshot.configured_port = port
            self._snapshot.configured_interface = interface
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
            self._snapshot.running = False
            self._snapshot.last_error = "starting"
        self._thread = threading.Thread(target=self._listen_loop, args=key, name="sma-energy-meter-listener", daemon=True)
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
            raise RuntimeError("SMA Energy Meter: noch kein gültiges Paket empfangen")
        age = time.time() - snap.last_received_epoch
        if age > timeout_s:
            raise RuntimeError(f"SMA Energy Meter: letzter Wert ist nicht aktuell ({int(age)} s, Timeout {timeout_s} s)")
        return float(snap.last_power_w)

    def snapshot(self) -> SmaEnergyMeterSnapshot:
        with self._lock:
            return SmaEnergyMeterSnapshot(**self._snapshot.__dict__)

    def _listen_loop(self, key: Tuple[str, int, str]) -> None:
        group, port, interface = key
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("", port))
            except OSError:
                sock.bind((group, port))
            iface_ip = interface if interface and interface[0].isdigit() else "0.0.0.0"
            mreq = socket.inet_aton(group) + socket.inet_aton(iface_ip)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            sock.settimeout(1.0)
            with self._lock:
                self._sock = sock
                self._snapshot.running = True
                self._snapshot.last_error = "none" if not (interface and not interface[0].isdigit()) else f"Interface '{interface}' ist kein IPv4-Wert; Multicast-Join nutzt 0.0.0.0"
            while not self._stop.is_set():
                try:
                    packet, _addr = sock.recvfrom(4096)
                except socket.timeout:
                    continue
                except OSError as exc:
                    if not self._stop.is_set():
                        self._record_error(str(exc))
                    break
                now = time.time()
                reading = parse_sma_energy_meter_packet(packet, now)
                with self._lock:
                    self._snapshot.packet_count += 1
                    if reading is not None:
                        self._snapshot.decode_count += 1
                        self._snapshot.last_power_w = reading.grid_power_w
                        self._snapshot.last_consumption_power_w = reading.consumption_power_w
                        self._snapshot.last_feedin_power_w = reading.feedin_power_w
                        self._snapshot.last_received_epoch = reading.received_epoch
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

    def _record_error(self, message: str) -> None:
        with self._lock:
            self._snapshot.error_count += 1
            self._snapshot.last_error = message
