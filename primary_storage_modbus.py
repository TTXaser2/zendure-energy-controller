# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

"""Read-only native primary-storage Modbus/TCP source support.

V15.0.0 intentionally implements only the Modbus read functions required by
versioned ZEC templates.  There is no write API and no generic raw-request API.
All socket I/O is designed to run in :class:`PrimaryStorageModbusWorker`, never
in the controller cycle or HTTP request path.
"""

from __future__ import annotations

import socket
import struct
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Mapping, Optional, Tuple


SOURCE_PROFILE_MODBUS_TEMPLATE = "modbus_template"
SOURCE_TYPE_MODBUS_TCP = "modbus_tcp"

SOURCE_HEALTH_STARTING = "STARTING"
SOURCE_HEALTH_OK = "OK"
SOURCE_HEALTH_DEGRADED = "DEGRADED"
SOURCE_HEALTH_STALE = "STALE"

FC_READ_HOLDING_REGISTERS = 3
FC_READ_INPUT_REGISTERS = 4
_ALLOWED_READ_FUNCTIONS = frozenset({FC_READ_HOLDING_REGISTERS, FC_READ_INPUT_REGISTERS})


class ModbusReadError(RuntimeError):
    """Classified failure of a read-only Modbus/TCP request."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = str(code or "MODBUS_ERROR")
        self.detail = str(detail or "")
        super().__init__(f"{self.code}: {self.detail}" if self.detail else self.code)


@dataclass(frozen=True)
class RegisterDefinition:
    address: int
    function_code: int
    count: int
    data_type: str
    scale: float = 1.0
    invalid_raw: Optional[int] = None

    def __post_init__(self) -> None:
        if self.function_code not in _ALLOWED_READ_FUNCTIONS:
            raise ValueError("template register must use read-only FC03/FC04")
        if self.count <= 0:
            raise ValueError("register count must be positive")
        if self.data_type not in {"s32", "u32"}:
            raise ValueError(f"unsupported register data type: {self.data_type}")


@dataclass(frozen=True)
class PrimaryStorageTemplate:
    template_id: str
    display_name_default: str
    protocol: str
    read_only: bool
    poll_interval_s: float
    port_default: int
    unit_id_default: int
    power: RegisterDefinition
    soc: RegisterDefinition


SMA_SUNNY_ISLAND_TEMPLATE = PrimaryStorageTemplate(
    template_id="sma_sunny_island",
    display_name_default="SMA Sunny Island",
    protocol=SOURCE_TYPE_MODBUS_TCP,
    read_only=True,
    poll_interval_s=1.0,
    port_default=502,
    unit_id_default=3,
    power=RegisterDefinition(
        address=30775,
        function_code=FC_READ_INPUT_REGISTERS,
        count=2,
        data_type="s32",
        scale=1.0,
        invalid_raw=0x80000000,
    ),
    soc=RegisterDefinition(
        address=30845,
        function_code=FC_READ_HOLDING_REGISTERS,
        count=2,
        data_type="u32",
        scale=1.0,
        invalid_raw=0xFFFFFFFF,
    ),
)

PRIMARY_STORAGE_TEMPLATES: Mapping[str, PrimaryStorageTemplate] = {
    SMA_SUNNY_ISLAND_TEMPLATE.template_id: SMA_SUNNY_ISLAND_TEMPLATE,
}


def get_primary_storage_template(template_id: Any) -> PrimaryStorageTemplate:
    key = str(template_id or "").strip().lower()
    template = PRIMARY_STORAGE_TEMPLATES.get(key)
    if template is None:
        raise ValueError(f"UNKNOWN_PRIMARY_STORAGE_TEMPLATE:{key or '<empty>'}")
    if not template.read_only:
        raise ValueError(f"PRIMARY_STORAGE_TEMPLATE_NOT_READ_ONLY:{key}")
    return template


def resolve_modbus_endpoint(cfg: Mapping[str, Any], template: PrimaryStorageTemplate) -> Tuple[str, int, int]:
    host = str(cfg.get("SECOND_BATTERY_MODBUS_HOST", "") or "").strip()
    if not host:
        raise ValueError("SECOND_BATTERY_MODBUS_HOST_REQUIRED")
    port = int(cfg.get("SECOND_BATTERY_MODBUS_PORT", template.port_default) or template.port_default)
    unit_id = int(cfg.get("SECOND_BATTERY_MODBUS_UNIT_ID", template.unit_id_default))
    if not 1 <= port <= 65535:
        raise ValueError("SECOND_BATTERY_MODBUS_PORT_RANGE")
    if not 0 <= unit_id <= 255:
        raise ValueError("SECOND_BATTERY_MODBUS_UNIT_ID_RANGE")
    return host, port, unit_id


def decode_register_value(registers: Tuple[int, ...], definition: RegisterDefinition) -> float:
    if len(registers) != definition.count:
        raise ModbusReadError("REGISTER_COUNT_MISMATCH", f"expected={definition.count} got={len(registers)}")
    raw = 0
    for value in registers:
        if not 0 <= int(value) <= 0xFFFF:
            raise ModbusReadError("REGISTER_VALUE_RANGE")
        raw = (raw << 16) | int(value)
    if definition.invalid_raw is not None and raw == int(definition.invalid_raw):
        raise ModbusReadError("INVALID_SENTINEL")
    if definition.data_type == "s32":
        if raw & 0x80000000:
            raw -= 0x100000000
    elif definition.data_type != "u32":
        raise ModbusReadError("UNSUPPORTED_DATA_TYPE", definition.data_type)
    return float(raw) * float(definition.scale)


@dataclass(frozen=True)
class PrimaryStoragePoll:
    power_w: float
    soc_percent: float
    capacity_kwh: Optional[float]
    source_profile: str
    source_type: str
    template_id: str
    endpoint: str
    unit_id: int
    request_duration_ms: float


class ModbusTcpReadOnlyClient:
    """Minimal persistent Modbus/TCP client restricted to FC03 and FC04."""

    def __init__(self, host: str, port: int, unit_id: int, *, timeout_s: float = 1.0) -> None:
        self.host = str(host)
        self.port = int(port)
        self.unit_id = int(unit_id)
        self.timeout_s = max(0.05, float(timeout_s))
        self._sock: Optional[socket.socket] = None
        self._transaction_id = 0
        self.connect_count = 0
        self.request_count = 0
        self.error_count = 0

    def close(self) -> None:
        sock, self._sock = self._sock, None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass

    def _ensure_connected(self) -> socket.socket:
        if self._sock is not None:
            return self._sock
        try:
            sock = socket.create_connection((self.host, self.port), timeout=self.timeout_s)
            sock.settimeout(self.timeout_s)
        except OSError as exc:
            self.error_count += 1
            raise ModbusReadError("CONNECT_FAILED", exc.__class__.__name__) from exc
        self._sock = sock
        self.connect_count += 1
        return sock

    @staticmethod
    def _recv_exact(sock: socket.socket, size: int) -> bytes:
        parts = bytearray()
        while len(parts) < size:
            chunk = sock.recv(size - len(parts))
            if not chunk:
                raise ModbusReadError("CONNECTION_CLOSED")
            parts.extend(chunk)
        return bytes(parts)

    def read_registers(self, function_code: int, address: int, count: int) -> Tuple[int, ...]:
        if int(function_code) not in _ALLOWED_READ_FUNCTIONS:
            raise ValueError("only Modbus read function codes 3 and 4 are allowed")
        if not 0 <= int(address) <= 0xFFFF or not 1 <= int(count) <= 125:
            raise ValueError("invalid Modbus register range")
        self._transaction_id = (self._transaction_id + 1) & 0xFFFF
        if self._transaction_id == 0:
            self._transaction_id = 1
        tid = self._transaction_id
        pdu = struct.pack(">BHH", int(function_code), int(address), int(count))
        request = struct.pack(">HHHB", tid, 0, len(pdu) + 1, self.unit_id) + pdu
        sock = self._ensure_connected()
        self.request_count += 1
        try:
            sock.sendall(request)
            mbap = self._recv_exact(sock, 7)
            rx_tid, protocol_id, length, rx_unit = struct.unpack(">HHHB", mbap)
            if rx_tid != tid:
                raise ModbusReadError("TRANSACTION_ID_MISMATCH", f"expected={tid} got={rx_tid}")
            if protocol_id != 0:
                raise ModbusReadError("PROTOCOL_ID_MISMATCH", str(protocol_id))
            if rx_unit != self.unit_id:
                raise ModbusReadError("UNIT_ID_MISMATCH", f"expected={self.unit_id} got={rx_unit}")
            if length < 2 or length > 254:
                raise ModbusReadError("INVALID_MBAP_LENGTH", str(length))
            body = self._recv_exact(sock, length - 1)
            rx_fc = body[0]
            if rx_fc == (int(function_code) | 0x80):
                code = body[1] if len(body) > 1 else -1
                raise ModbusReadError("MODBUS_EXCEPTION", str(code))
            if rx_fc != int(function_code):
                raise ModbusReadError("FUNCTION_CODE_MISMATCH", f"expected={function_code} got={rx_fc}")
            expected_bytes = int(count) * 2
            if len(body) < 2 or body[1] != expected_bytes or len(body[2:]) != expected_bytes:
                raise ModbusReadError("BYTE_COUNT_MISMATCH")
            return tuple(struct.unpack(f">{count}H", body[2:]))
        except (OSError, ModbusReadError) as exc:
            self.error_count += 1
            self.close()
            if isinstance(exc, ModbusReadError):
                raise
            raise ModbusReadError("TRANSPORT_ERROR", exc.__class__.__name__) from exc


def read_primary_storage_once(
    client: ModbusTcpReadOnlyClient,
    template: PrimaryStorageTemplate,
    *,
    monotonic_fn: Callable[[], float] = time.monotonic,
) -> PrimaryStoragePoll:
    if not template.read_only:
        raise ValueError("template must be read-only")
    started = monotonic_fn()
    power_regs = client.read_registers(template.power.function_code, template.power.address, template.power.count)
    soc_regs = client.read_registers(template.soc.function_code, template.soc.address, template.soc.count)
    power = decode_register_value(power_regs, template.power)
    soc = decode_register_value(soc_regs, template.soc)
    if not 0.0 <= soc <= 100.0:
        raise ModbusReadError("SOC_OUT_OF_RANGE", str(soc))
    duration_ms = max(0.0, (monotonic_fn() - started) * 1000.0)
    return PrimaryStoragePoll(
        power_w=power,
        soc_percent=soc,
        capacity_kwh=None,
        source_profile=SOURCE_PROFILE_MODBUS_TEMPLATE,
        source_type=SOURCE_TYPE_MODBUS_TCP,
        template_id=template.template_id,
        endpoint=f"{client.host}:{client.port}",
        unit_id=client.unit_id,
        request_duration_ms=duration_ms,
    )


def probe_primary_storage_modbus(
    cfg: Mapping[str, Any],
    *,
    client_factory: Callable[..., ModbusTcpReadOnlyClient] = ModbusTcpReadOnlyClient,
) -> Dict[str, Any]:
    """Run one bounded read-only draft connection test without mutating runtime state."""
    template = get_primary_storage_template(cfg.get("SECOND_BATTERY_MODBUS_TEMPLATE", "sma_sunny_island"))
    host, port, unit_id = resolve_modbus_endpoint(cfg, template)
    client = client_factory(host, port, unit_id, timeout_s=1.5)
    try:
        poll = read_primary_storage_once(client, template)
        return {
            "status": "ok",
            "read_only": True,
            "template_id": template.template_id,
            "device": template.display_name_default,
            "endpoint": f"{host}:{port}",
            "unit_id": unit_id,
            "power_w": poll.power_w,
            "soc_percent": poll.soc_percent,
            "response_time_ms": round(float(poll.request_duration_ms), 3),
            "function_codes": [template.power.function_code, template.soc.function_code],
        }
    finally:
        client.close()


class PrimaryStorageModbusWorker:
    """Background collector that atomically publishes complete primary-storage polls."""

    def __init__(
        self,
        state: Any,
        config: Mapping[str, Any],
        *,
        client_factory: Callable[..., ModbusTcpReadOnlyClient] = ModbusTcpReadOnlyClient,
        monotonic_fn: Callable[[], float] = time.monotonic,
        wall_time_fn: Callable[[], float] = time.time,
    ) -> None:
        self.state = state
        self.config = dict(config)
        self.template = get_primary_storage_template(self.config.get("SECOND_BATTERY_MODBUS_TEMPLATE", "sma_sunny_island"))
        self.host, self.port, self.unit_id = resolve_modbus_endpoint(self.config, self.template)
        self._client_factory = client_factory
        self._monotonic = monotonic_fn
        self._wall_time = wall_time_fn
        self._client: Optional[ModbusTcpReadOnlyClient] = None
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._archived_connect_count = 0
        self._archived_request_count = 0
        self._archived_error_count = 0
        self._publish_starting_state()

    def _publish_starting_state(self) -> None:
        with self.state.lock:
            self.state.primary_storage_source_profile = SOURCE_PROFILE_MODBUS_TEMPLATE
            self.state.primary_storage_source_type = SOURCE_TYPE_MODBUS_TCP
            self.state.primary_storage_template_id = self.template.template_id
            self.state.primary_storage_endpoint = f"{self.host}:{self.port}"
            self.state.primary_storage_unit_id = self.unit_id
            self.state.primary_storage_source_health = SOURCE_HEALTH_STARTING
            self.state.primary_storage_last_poll_ok = None
            self.state.primary_storage_last_error_code = ""

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="primary-storage-modbus", daemon=True)
        self._thread.start()

    def stop(self, timeout_s: float = 3.0) -> None:
        self._stop.set()
        client = self._client
        if client is not None:
            client.close()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(max(0.0, float(timeout_s)))
        self._thread = None
        self._client = None

    def _client_stats(self) -> Tuple[int, int, int]:
        client = self._client
        return (
            self._archived_connect_count + int(getattr(client, "connect_count", 0) or 0),
            self._archived_request_count + int(getattr(client, "request_count", 0) or 0),
            self._archived_error_count + int(getattr(client, "error_count", 0) or 0),
        )

    def _discard_client(self) -> None:
        client, self._client = self._client, None
        if client is None:
            return
        self._archived_connect_count += int(getattr(client, "connect_count", 0) or 0)
        self._archived_request_count += int(getattr(client, "request_count", 0) or 0)
        self._archived_error_count += int(getattr(client, "error_count", 0) or 0)
        client.close()

    def poll_once(self) -> PrimaryStoragePoll:
        if self._client is None:
            self._client = self._client_factory(self.host, self.port, self.unit_id, timeout_s=1.0)
        attempt_mono = self._monotonic()
        attempt_wall = self._wall_time()
        with self.state.lock:
            self.state.primary_storage_last_attempt_monotonic = attempt_mono
            self.state.primary_storage_last_attempt_epoch = attempt_wall
        try:
            poll = read_primary_storage_once(self._client, self.template, monotonic_fn=self._monotonic)
        except Exception as exc:
            code = exc.code if isinstance(exc, ModbusReadError) else exc.__class__.__name__.upper()
            self._publish_failure(code)
            raise
        self._publish_success(poll)
        return poll

    def _publish_success(self, poll: PrimaryStoragePoll) -> None:
        now_mono = self._monotonic()
        now_wall = self._wall_time()
        connect_count, request_count, error_count = self._client_stats()
        with self.state.lock:
            self.state.sma_battery_power = float(poll.power_w)
            self.state.sma_battery_soc = float(poll.soc_percent)
            self.state.sma_battery_capacity_kwh = poll.capacity_kwh
            self.state.last_sma_battery_update_epoch = now_wall
            self.state.last_sma_battery_update_monotonic = now_mono
            self.state.last_sma_battery_update_time = datetime.fromtimestamp(now_wall).strftime("%Y-%m-%d %H:%M:%S")
            self.state.primary_storage_source_profile = poll.source_profile
            self.state.primary_storage_source_type = poll.source_type
            self.state.primary_storage_template_id = poll.template_id
            self.state.primary_storage_endpoint = poll.endpoint
            self.state.primary_storage_unit_id = poll.unit_id
            self.state.primary_storage_source_health = SOURCE_HEALTH_OK
            self.state.primary_storage_last_poll_ok = True
            self.state.primary_storage_last_success_monotonic = now_mono
            self.state.primary_storage_last_success_epoch = now_wall
            self.state.primary_storage_consecutive_failures = 0
            self.state.primary_storage_last_error_code = ""
            self.state.primary_storage_request_duration_ms = float(poll.request_duration_ms)
            self.state.primary_storage_connect_count = connect_count
            self.state.primary_storage_request_count = request_count
            self.state.primary_storage_error_count = error_count
            self.state.primary_storage_data_available = True

    def _publish_failure(self, error_code: str) -> None:
        now_mono = self._monotonic()
        connect_count, request_count, error_count = self._client_stats()
        timeout_s = float(self.config.get("SECOND_BATTERY_STALE_TIMEOUT_SECONDS", 30) or 30)
        with self.state.lock:
            self.state.primary_storage_last_poll_ok = False
            self.state.primary_storage_consecutive_failures += 1
            self.state.primary_storage_last_error_code = str(error_code or "MODBUS_ERROR")
            self.state.primary_storage_connect_count = connect_count
            self.state.primary_storage_request_count = request_count
            self.state.primary_storage_error_count = error_count
            last_success = self.state.primary_storage_last_success_monotonic
            if last_success is None:
                self.state.primary_storage_source_health = SOURCE_HEALTH_STARTING
            elif max(0.0, now_mono - float(last_success)) <= timeout_s:
                self.state.primary_storage_source_health = SOURCE_HEALTH_DEGRADED
            else:
                self.state.primary_storage_source_health = SOURCE_HEALTH_STALE

    def refresh_health(self) -> str:
        now_mono = self._monotonic()
        timeout_s = float(self.config.get("SECOND_BATTERY_STALE_TIMEOUT_SECONDS", 30) or 30)
        with self.state.lock:
            last_success = self.state.primary_storage_last_success_monotonic
            if last_success is None:
                health = SOURCE_HEALTH_STARTING
            elif max(0.0, now_mono - float(last_success)) > timeout_s:
                health = SOURCE_HEALTH_STALE
            elif self.state.primary_storage_last_poll_ok is False:
                health = SOURCE_HEALTH_DEGRADED
            else:
                health = SOURCE_HEALTH_OK
            self.state.primary_storage_source_health = health
            return health

    def _run(self) -> None:
        interval = max(0.1, float(self.template.poll_interval_s))
        next_poll = self._monotonic()
        while not self._stop.is_set():
            now = self._monotonic()
            if now < next_poll:
                self.refresh_health()
                self._stop.wait(min(0.25, next_poll - now))
                continue
            try:
                self.poll_once()
            except Exception:
                self._discard_client()
            finally:
                next_poll = max(next_poll + interval, self._monotonic())
        self._discard_client()
