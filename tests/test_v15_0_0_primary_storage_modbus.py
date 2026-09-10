import socket
import struct
import threading
import time

import pytest

from primary_storage_modbus import (
    FC_READ_HOLDING_REGISTERS,
    FC_READ_INPUT_REGISTERS,
    ModbusReadError,
    ModbusTcpReadOnlyClient,
    PrimaryStorageModbusWorker,
    SOURCE_HEALTH_DEGRADED,
    SOURCE_HEALTH_OK,
    SOURCE_HEALTH_STALE,
    SOURCE_HEALTH_STARTING,
    decode_register_value,
    get_primary_storage_template,
    read_primary_storage_once,
)
from state import ControllerState


class FakeClock:
    def __init__(self, value=100.0):
        self.value = float(value)

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += float(seconds)


class FakeClient:
    def __init__(self, host, port, unit_id, timeout_s=1.0):
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.timeout_s = timeout_s
        self.connect_count = 1
        self.request_count = 0
        self.error_count = 0
        self.closed = False
        self.fail_kind = None

    def read_registers(self, fc, address, count):
        self.request_count += 1
        if self.fail_kind == "power" and address == 30775:
            self.error_count += 1
            raise ModbusReadError("FAKE_POWER_FAIL")
        if self.fail_kind == "soc" and address == 30845:
            self.error_count += 1
            raise ModbusReadError("FAKE_SOC_FAIL")
        if address == 30775:
            # -2290 as big-endian signed 32-bit
            raw = (1 << 32) - 2290
            return ((raw >> 16) & 0xFFFF, raw & 0xFFFF)
        if address == 30845:
            return (0, 85)
        raise AssertionError(address)

    def close(self):
        self.closed = True


@pytest.fixture
def cfg():
    return {
        "SECOND_BATTERY_MODBUS_TEMPLATE": "sma_sunny_island",
        "SECOND_BATTERY_MODBUS_HOST": "192.0.2.10",
        "SECOND_BATTERY_MODBUS_PORT": 502,
        "SECOND_BATTERY_MODBUS_UNIT_ID": 3,
        "SECOND_BATTERY_STALE_TIMEOUT_SECONDS": 30,
    }


def test_sunny_island_template_contract():
    t = get_primary_storage_template("sma_sunny_island")
    assert t.display_name_default == "SMA Sunny Island"
    assert t.read_only is True
    assert t.poll_interval_s == 1.0
    assert t.port_default == 502
    assert t.unit_id_default == 3
    assert (t.power.address, t.power.function_code, t.power.count, t.power.data_type) == (30775, 4, 2, "s32")
    assert (t.soc.address, t.soc.function_code, t.soc.count, t.soc.data_type) == (30845, 3, 2, "u32")


def test_unknown_template_fails_closed():
    with pytest.raises(ValueError, match="UNKNOWN_PRIMARY_STORAGE_TEMPLATE"):
        get_primary_storage_template("anything_else")


def test_decode_s32_power_and_u32_soc_and_sentinels():
    t = get_primary_storage_template("sma_sunny_island")
    assert decode_register_value((0, 720), t.power) == 720
    raw = (1 << 32) - 2290
    assert decode_register_value(((raw >> 16) & 0xFFFF, raw & 0xFFFF), t.power) == -2290
    assert decode_register_value((0, 85), t.soc) == 85
    with pytest.raises(ModbusReadError, match="INVALID_SENTINEL"):
        decode_register_value((0x8000, 0), t.power)
    with pytest.raises(ModbusReadError, match="INVALID_SENTINEL"):
        decode_register_value((0xFFFF, 0xFFFF), t.soc)


def test_full_poll_requires_both_reads_and_preserves_native_sign():
    t = get_primary_storage_template("sma_sunny_island")
    c = FakeClient("host", 502, 3)
    poll = read_primary_storage_once(c, t)
    assert poll.power_w == -2290
    assert poll.soc_percent == 85
    assert poll.capacity_kwh is None
    assert c.request_count == 2
    c.fail_kind = "soc"
    with pytest.raises(ModbusReadError, match="FAKE_SOC_FAIL"):
        read_primary_storage_once(c, t)


def test_worker_atomic_success_failure_stale_and_recovery(cfg):
    state = ControllerState()
    mono = FakeClock(100.0)
    wall = FakeClock(1_700_000_000.0)
    created = []

    def factory(*args, **kwargs):
        c = FakeClient(*args, **kwargs)
        created.append(c)
        return c

    worker = PrimaryStorageModbusWorker(state, cfg, client_factory=factory, monotonic_fn=mono, wall_time_fn=wall)
    assert state.primary_storage_source_health == SOURCE_HEALTH_STARTING
    assert state.last_sma_battery_update_epoch is None

    worker.poll_once()
    assert state.sma_battery_power == -2290
    assert state.sma_battery_soc == 85
    assert state.primary_storage_source_health == SOURCE_HEALTH_OK
    assert state.primary_storage_last_poll_ok is True
    assert state.primary_storage_consecutive_failures == 0
    first_success = state.primary_storage_last_success_monotonic
    first_epoch = state.last_sma_battery_update_epoch

    created[-1].fail_kind = "soc"
    mono.advance(1)
    wall.advance(1)
    with pytest.raises(ModbusReadError):
        worker.poll_once()
    # Partial poll must not rejuvenate or replace the last valid snapshot.
    assert state.primary_storage_last_success_monotonic == first_success
    assert state.last_sma_battery_update_epoch == first_epoch
    assert state.sma_battery_power == -2290
    assert state.sma_battery_soc == 85
    assert state.primary_storage_source_health == SOURCE_HEALTH_DEGRADED
    assert state.primary_storage_consecutive_failures == 1

    mono.advance(31)
    assert worker.refresh_health() == SOURCE_HEALTH_STALE
    assert state.sma_battery_power == -2290

    created[-1].fail_kind = None
    wall.advance(31)
    worker.poll_once()
    assert state.primary_storage_source_health == SOURCE_HEALTH_OK
    assert state.primary_storage_consecutive_failures == 0
    assert state.primary_storage_last_success_monotonic > first_success


def test_soc_out_of_range_rejected_without_success_update(cfg):
    class BadSocClient(FakeClient):
        def read_registers(self, fc, address, count):
            self.request_count += 1
            if address == 30775:
                return (0, 123)
            return (0, 101)

    state = ControllerState()
    worker = PrimaryStorageModbusWorker(state, cfg, client_factory=BadSocClient)
    with pytest.raises(ModbusReadError, match="SOC_OUT_OF_RANGE"):
        worker.poll_once()
    assert state.last_sma_battery_update_epoch is None
    assert state.primary_storage_last_success_monotonic is None


def test_runtime_client_has_no_write_or_generic_request_api():
    forbidden = {"write_register", "write_registers", "write_coil", "write_coils", "custom_request", "raw_request"}
    assert not forbidden.intersection(dir(ModbusTcpReadOnlyClient))


def _serve_two_fragmented_reads(listener, requests):
    conn, _ = listener.accept()
    with conn:
        for response_registers in ((0xFFFF, 0xF70E), (0, 85)):
            header = b""
            while len(header) < 7:
                header += conn.recv(7 - len(header))
            tid, proto, length, unit = struct.unpack(">HHHB", header)
            body = b""
            while len(body) < length - 1:
                body += conn.recv(length - 1 - len(body))
            fc, address, count = struct.unpack(">BHH", body)
            requests.append((fc, address, count, unit))
            payload = struct.pack(">B", len(response_registers) * 2) + struct.pack(">2H", *response_registers)
            pdu = bytes([fc]) + payload
            response = struct.pack(">HHHB", tid, proto, len(pdu) + 1, unit) + pdu
            # Deliberately fragment every TCP response.
            for byte in response:
                conn.sendall(bytes([byte]))


def test_tcp_client_persistent_connection_fragmented_responses_and_addresses():
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    requests = []
    thread = threading.Thread(target=_serve_two_fragmented_reads, args=(listener, requests), daemon=True)
    thread.start()
    client = ModbusTcpReadOnlyClient("127.0.0.1", listener.getsockname()[1], 3, timeout_s=1.0)
    try:
        poll = read_primary_storage_once(client, get_primary_storage_template("sma_sunny_island"))
        assert poll.power_w == -2290
        assert poll.soc_percent == 85
        assert client.connect_count == 1
        assert client.request_count == 2
        assert requests == [(FC_READ_INPUT_REGISTERS, 30775, 2, 3), (FC_READ_HOLDING_REGISTERS, 30845, 2, 3)]
    finally:
        client.close()
        listener.close()
        thread.join(1.0)


def test_worker_stop_closes_socket(cfg):
    state = ControllerState()
    created = []

    def factory(*args, **kwargs):
        c = FakeClient(*args, **kwargs)
        created.append(c)
        return c

    worker = PrimaryStorageModbusWorker(state, cfg, client_factory=factory)
    worker.poll_once()
    worker.stop()
    assert created[-1].closed is True
