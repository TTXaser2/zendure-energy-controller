import csv
import os
import tempfile
import threading
import time
import unittest
import sys
import types

import requests

if "paho" not in sys.modules:
    paho = types.ModuleType("paho")
    paho_mqtt = types.ModuleType("paho.mqtt")
    paho_client = types.ModuleType("paho.mqtt.client")
    paho_client.CallbackAPIVersion = types.SimpleNamespace(VERSION2=object())
    paho_client.Client = lambda *args, **kwargs: types.SimpleNamespace(
        on_message=None, on_connect=None, on_disconnect=None,
        username_pw_set=lambda *a, **k: None, connect=lambda *a, **k: None,
        loop_start=lambda *a, **k: None, subscribe=lambda *a, **k: None,
        publish=lambda *a, **k: types.SimpleNamespace(rc=0),
    )
    sys.modules["paho"] = paho
    sys.modules["paho.mqtt"] = paho_mqtt
    sys.modules["paho.mqtt.client"] = paho_client

from csv_logger import CsvRotatingLogger
from controller_logic import ZendureController
from tests.test_operation_priority import DummyConfigManager, RecordingMqtt, OkShelly, NoopLogger, fresh_state, base_cfg
from measurement_v4 import MeasurementV4Logger, build_v4_row
from measurement_v4_contract import (
    RC17_STANDARD_HEADER,
    STANDARD_HEADER,
    EXTENDED_HEADER,
    header_hash,
)
from tests.test_measurement_v4_writer import base_config, base_row
from zendure_local_api import (
    ZendureLocalApiClient,
    ZendureLocalApiConfigSnapshot,
    ZendureLocalApiWorker,
    WORKER_BACKOFF,
    WORKER_STOPPED,
    parse_local_api_report,
)


def api_config(**overrides):
    cfg = {
        "ZENDURE_LOCAL_API_USE_FOR_TELEMETRY": True,
        "ZENDURE_LOCAL_IP": "192.0.2.10",
        "ZENDURE_LOCAL_API_POLL_INTERVAL_SECONDS": 1,
        "ZENDURE_LOCAL_API_TIMEOUT_SECONDS": 5,
        "ZENDURE_LOCAL_API_CONTROL_TIMEOUT_CAP_SECONDS": 1.5,
        "ZENDURE_LOCAL_API_ERROR_BACKOFF_SECONDS": 0,
        "ZENDURE_LOCAL_API_SOC_PRIORITY": "properties_first",
        "ZENDURE_LOCAL_API_TELEMETRY_FALLBACK_ONLY": True,
        "DEVICE_ID": "HEADUNIT-1",
    }
    cfg.update(overrides)
    return cfg


def payload(level=55, grid=321):
    return {
        "sn": "HEADUNIT-1",
        "properties": {
            "electricLevel": level,
            "gridInputPower": grid,
            "outputHomePower": 0,
            "packInputPower": grid - 10,
            "outputPackPower": 0,
            "gridOffPower": 0,
            "solarInputPower": 0,
            "smartMode": 1,
            "acMode": "Input mode",
            "inputLimit": 500,
            "outputLimit": 0,
            "inverseMaxPower": 2000,
            "chargeMaxLimit": 2400,
            "gridOffMode": "off",
            "hyperTmp": 3151,
        },
        "packData": [{"sn": "PACK-1", "socLevel": level - 1, "maxTemp": 3131, "power": grid - 10}],
    }


class ScriptedClient(ZendureLocalApiClient):
    def __init__(self, results):
        # Do not create a real requests Session in unit tests.
        self.results = list(results)
        self.calls = 0
        self.recreated = 0
        self.closed = 0
        self.last_poll_epoch = None
        self.backoff_until_epoch = None
        self.consecutive_error_count = 0

    def fetch_report_once(self, config):
        self.calls += 1
        item = self.results[min(self.calls - 1, len(self.results) - 1)]
        if callable(item):
            item = item()
        if isinstance(item, BaseException):
            raise item
        return item

    def recreate_session(self):
        self.recreated += 1

    def close_session(self):
        self.closed += 1


def wait_until(predicate, timeout=2.5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


class EventCsv:
    def __init__(self):
        self.events = []
    def write_runtime_event(self, config, event):
        self.events.append(dict(event))
    def close(self):
        pass


class Rc18AsyncLocalApiTests(unittest.TestCase):
    def test_timeout_is_capped_for_background_request(self):
        cfg = ZendureLocalApiConfigSnapshot.from_config(api_config(), generation=7)
        self.assertEqual(7, cfg.generation)
        self.assertEqual(1.5, cfg.effective_timeout_s)
        self.assertTrue(cfg.enabled)

    def test_parser_normalizes_soc_power_command_and_temperatures(self):
        cfg = ZendureLocalApiConfigSnapshot.from_config(api_config(), generation=1)
        data = parse_local_api_report(payload(), cfg)
        self.assertEqual(55, data.selected_api_soc)
        self.assertEqual(321, data.grid_input_power_w)
        self.assertEqual(1, data.smart_mode)
        self.assertEqual("Input mode", data.ac_mode)
        self.assertAlmostEqual(42.0, data.headunit_temperature_c, places=1)
        self.assertEqual(1, len(data.packs))
        self.assertAlmostEqual(40.0, data.packs[0].temperature_c, places=1)

    def test_worker_publishes_successful_latest_only_snapshot(self):
        client = ScriptedClient([payload()])
        worker = ZendureLocalApiWorker(client, api_config())
        worker.start()
        self.assertTrue(wait_until(lambda: worker.latest_snapshot().data_success_sequence >= 1))
        snap = worker.latest_snapshot()
        self.assertTrue(snap.latest_attempt_ok)
        self.assertEqual(1, snap.data_success_sequence)
        self.assertEqual(55, snap.successful_data.selected_api_soc)
        self.assertGreaterEqual(snap.snapshot_sequence, 3)
        worker.request_stop(); worker.join(2)
        self.assertEqual(WORKER_STOPPED, worker.latest_snapshot().worker_state)
        self.assertEqual(1, client.closed)

    def test_failed_attempt_retains_last_successful_data(self):
        client = ScriptedClient([payload(55), requests.Timeout("slow")])
        worker = ZendureLocalApiWorker(client, api_config())
        worker.start()
        self.assertTrue(wait_until(lambda: worker.latest_snapshot().data_success_sequence >= 1))
        self.assertTrue(wait_until(lambda: client.calls >= 2, timeout=3.0))
        self.assertTrue(wait_until(lambda: worker.latest_snapshot().latest_attempt_ok is False))
        snap = worker.latest_snapshot()
        self.assertEqual("TIMEOUT", snap.latest_error_code)
        self.assertEqual(1, snap.data_success_sequence)
        self.assertEqual(55, snap.successful_data.selected_api_soc)
        worker.request_stop(); worker.join(2)

    def test_error_backoff_is_monotonic_and_visible(self):
        client = ScriptedClient([requests.ConnectionError("offline")])
        worker = ZendureLocalApiWorker(client, api_config(ZENDURE_LOCAL_API_ERROR_BACKOFF_SECONDS=2))
        worker.start()
        self.assertTrue(wait_until(lambda: worker.latest_snapshot().latest_attempt_ok is False))
        snap = worker.latest_snapshot()
        self.assertEqual(WORKER_BACKOFF, snap.worker_state)
        self.assertGreater(snap.backoff_remaining_s(), 0)
        self.assertEqual("CONNECTION_ERROR", snap.latest_error_code)
        worker.request_stop(); worker.join(2)

    def test_ip_change_discards_late_old_generation_result(self):
        entered = threading.Event()
        release = threading.Event()
        def delayed():
            entered.set()
            release.wait(2)
            return payload(44)
        client = ScriptedClient([delayed, payload(66)])
        worker = ZendureLocalApiWorker(client, api_config())
        worker.start()
        self.assertTrue(entered.wait(1))
        new_generation = worker.update_config(api_config(ZENDURE_LOCAL_IP="192.0.2.11"))
        release.set()
        self.assertTrue(wait_until(lambda: worker.latest_snapshot().config_generation == new_generation))
        self.assertTrue(wait_until(lambda: worker.latest_snapshot().data_success_sequence >= 1, timeout=3.0))
        snap = worker.latest_snapshot()
        self.assertEqual(66, snap.successful_data.selected_api_soc)
        self.assertEqual(new_generation, snap.successful_data_config_generation)
        self.assertEqual(1, client.recreated)
        worker.request_stop(); worker.join(2)

    def test_disabled_worker_performs_no_request(self):
        client = ScriptedClient([payload()])
        worker = ZendureLocalApiWorker(client, api_config(ZENDURE_LOCAL_API_USE_FOR_TELEMETRY=False))
        worker.start()
        time.sleep(0.08)
        self.assertEqual(0, client.calls)
        worker.request_stop(); worker.join(2)

    def test_rc18_contract_preserves_exact_rc17_header(self):
        self.assertEqual(246, len(STANDARD_HEADER))
        self.assertEqual(249, len(EXTENDED_HEADER))
        self.assertEqual(238, len(RC17_STANDARD_HEADER))
        self.assertEqual("192ccc890c2e1d80", header_hash(RC17_STANDARD_HEADER))
        self.assertEqual("7842bfef39d47f93", header_hash(STANDARD_HEADER))

    def test_eight_cycle_fields_are_present_and_populated(self):
        row = base_row()
        row.update({
            "zendure_local_api_snapshot_sequence": 12,
            "zendure_local_api_success_sequence": 8,
            "zendure_local_api_new_success_applied": True,
            "zendure_local_api_last_success_age_s": 3.25,
            "zendure_local_api_snapshot_valid": True,
            "zendure_local_api_snapshot_stale": False,
            "zendure_local_api_request_duration_ms": 1234.5,
            "zendure_local_api_snapshot_apply_ms": 0.42,
        })
        v4 = build_v4_row(base_config("/tmp"), row)
        self.assertEqual(12, v4["zendure_local_api_snapshot_sequence"])
        self.assertEqual(8, v4["zendure_local_api_success_sequence"])
        self.assertEqual("1", v4["zendure_local_api_new_success_applied"])
        self.assertEqual(3.2, v4["zendure_local_api_last_success_age_s"])
        self.assertEqual(1234.5, v4["zendure_local_api_request_duration_ms"])
        self.assertEqual(0.4, v4["zendure_local_api_snapshot_apply_ms"])

    def test_power_limit_stage_and_flag_are_numerical(self):
        row = base_row()
        row.update({
            "target_raw_w": 2903,
            "target_after_power_limit_w": 2400,
            "target_after_smoothing_w": 2399,
            "target_after_ramp_w": 2397,
            "target_final_w": 2397,
            "technical_limiters": "",
        })
        v4 = build_v4_row(base_config("/tmp"), row)
        self.assertEqual(2400.0, v4["target_limited_w"])
        self.assertEqual("1", v4["target_changed_by_power_limit"])
        self.assertEqual("1", v4["target_changed_by_smoothing"])
        self.assertEqual("1", v4["target_changed_by_step_limit"])

    def test_smoothing_does_not_claim_power_limit(self):
        row = base_row()
        row.update({
            "target_raw_w": 1000,
            "target_after_power_limit_w": 1000,
            "target_after_smoothing_w": 900,
            "target_after_ramp_w": 900,
            "target_final_w": 900,
            "technical_limiters": "",
        })
        v4 = build_v4_row(base_config("/tmp"), row)
        self.assertEqual("0", v4["target_changed_by_power_limit"])
        self.assertEqual("1", v4["target_changed_by_smoothing"])
        self.assertEqual("0", v4["target_changed_by_step_limit"])

    def test_runtime_event_is_staged_until_existing_measurement_write_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = base_config(tmp)
            logger = MeasurementV4Logger()
            logger.write_runtime_event(cfg, {"event_type": "local_api_attempt_completed", "snapshot_sequence": 3})
            event_path = os.path.join(tmp, "zec_runtime_events.jsonl")
            self.assertFalse(os.path.exists(event_path))
            logger.log(cfg, base_row())
            logger.close()
            self.assertTrue(os.path.exists(event_path))
            with open(event_path, encoding="utf-8") as handle:
                content = handle.read()
            self.assertIn("local_api_attempt_completed", content)

    def test_rc17_file_rotates_to_rc18_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_path = os.path.join(tmp, "measurements.csv")
            with open(old_path, "w", encoding="utf-8", newline="") as handle:
                handle.write(";".join(RC17_STANDARD_HEADER) + "\n")
                handle.write(";".join(["4"] + [""] * (len(RC17_STANDARD_HEADER) - 1)) + "\n")
            with open(old_path, "rb") as handle:
                old_bytes = handle.read()
            cfg = base_config(tmp)
            cfg["MEASUREMENT_LOG_FILE"] = "measurements.csv"
            logger = CsvRotatingLogger()
            status = logger.log(cfg, base_row())
            logger.close()
            self.assertEqual("active", status["measurement_log_status"])
            with open(old_path, "rb") as handle:
                self.assertEqual(old_bytes, handle.read())
            new_files = [name for name in os.listdir(tmp) if name.startswith("measurements_schema_rc18_")]
            self.assertEqual(1, len(new_files))
            with open(os.path.join(tmp, new_files[0]), encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle, delimiter=";"))
            self.assertEqual(STANDARD_HEADER, list(rows[0].keys()))

    def make_controller_with_worker(self, worker, cfg=None, state=None):
        cfg = cfg or base_cfg(
            ZENDURE_LOCAL_API_USE_FOR_TELEMETRY=True,
            ZENDURE_LOCAL_IP="192.0.2.10",
            ZENDURE_LOCAL_API_POLL_INTERVAL_SECONDS=1,
            ZENDURE_LOCAL_API_TIMEOUT_SECONDS=5,
            ZENDURE_LOCAL_API_CONTROL_TIMEOUT_CAP_SECONDS=1.5,
            ZENDURE_LOCAL_API_ERROR_BACKOFF_SECONDS=0,
            ZENDURE_LOCAL_API_SOC_PRIORITY="properties_first",
            ZENDURE_LOCAL_API_TELEMETRY_FALLBACK_ONLY=True,
        )
        state = state or fresh_state(80)
        csv = EventCsv()
        controller = ZendureController(
            DummyConfigManager(cfg), state, RecordingMqtt(), OkShelly(0),
            csv, worker, NoopLogger(),
        )
        return controller, state, cfg, csv

    def test_controller_applies_each_success_once_and_preserves_mqtt_priority(self):
        cfg = base_cfg(
            ZENDURE_LOCAL_API_USE_FOR_TELEMETRY=True,
            ZENDURE_LOCAL_IP="192.0.2.10",
            ZENDURE_LOCAL_API_POLL_INTERVAL_SECONDS=1,
            ZENDURE_LOCAL_API_TELEMETRY_FALLBACK_ONLY=True,
        )
        worker = ZendureLocalApiWorker(ScriptedClient([payload()]), cfg)
        parsed = parse_local_api_report(payload(66), worker.current_config())
        now_mono = time.monotonic()
        now_wall = time.time()
        worker._publish(
            config_generation=worker.config_generation,
            worker_state="IDLE",
            latest_attempt_ok=True,
            last_attempt_wall_epoch=now_wall,
            last_attempt_monotonic=now_mono,
            last_success_wall_epoch=now_wall,
            last_success_monotonic=now_mono,
            request_duration_ms=12.0,
            successful_data=parsed,
            successful_data_config_generation=worker.config_generation,
            data_success_sequence=1,
        )
        state = fresh_state(80)
        state.mqtt_battery_soc = 80
        state.last_mqtt_soc_update_epoch = time.time()
        state.last_zendure_power_update_epoch = time.time()
        controller, state, cfg, events = self.make_controller_with_worker(worker, cfg, state)
        self.assertTrue(controller.update_zendure_telemetry_from_local_api_snapshot(cfg))
        self.assertEqual(66, state.local_api_soc)
        self.assertEqual(80, state.battery_soc)  # fresh MQTT remains primary
        self.assertFalse(state.zendure_local_api_fallback_active)
        event_count = len(events.events)
        self.assertFalse(controller.update_zendure_telemetry_from_local_api_snapshot(cfg))
        self.assertEqual(event_count, len(events.events))

    def test_stale_mqtt_uses_success_timestamped_api_fallback(self):
        cfg = base_cfg(
            ZENDURE_LOCAL_API_USE_FOR_TELEMETRY=True,
            ZENDURE_LOCAL_IP="192.0.2.10",
            ZENDURE_LOCAL_API_POLL_INTERVAL_SECONDS=1,
            ZENDURE_LOCAL_API_TELEMETRY_FALLBACK_ONLY=True,
            SOC_STALE_TIMEOUT_SECONDS=5,
            ZENDURE_POWER_STALE_TIMEOUT_SECONDS=5,
        )
        worker = ZendureLocalApiWorker(ScriptedClient([payload()]), cfg)
        parsed = parse_local_api_report(payload(66, 444), worker.current_config())
        success_wall = time.time() - 2
        success_mono = time.monotonic() - 2
        worker._publish(
            config_generation=worker.config_generation,
            worker_state="IDLE",
            latest_attempt_ok=True,
            last_attempt_wall_epoch=success_wall,
            last_attempt_monotonic=success_mono,
            last_success_wall_epoch=success_wall,
            last_success_monotonic=success_mono,
            request_duration_ms=20.0,
            successful_data=parsed,
            successful_data_config_generation=worker.config_generation,
            data_success_sequence=1,
        )
        state = fresh_state(80)
        state.last_mqtt_soc_update_epoch = time.time() - 60
        state.last_zendure_power_update_epoch = time.time() - 60
        controller, state, cfg, events = self.make_controller_with_worker(worker, cfg, state)
        self.assertTrue(controller.update_zendure_telemetry_from_local_api_snapshot(cfg))
        self.assertEqual(66, state.battery_soc)
        self.assertEqual("Lokale API", state.zendure_telemetry_source)
        self.assertTrue(state.zendure_local_api_fallback_active)
        self.assertAlmostEqual(success_wall, state.last_soc_update_epoch, delta=0.01)
        self.assertAlmostEqual(success_wall, state.last_zendure_power_update_epoch, delta=0.01)
        self.assertTrue(any(e.get("event_type") == "local_api_snapshot_applied" for e in events.events))

    def test_blocking_http_request_does_not_block_controller_snapshot_read(self):
        entered = threading.Event()
        release = threading.Event()
        def delayed():
            entered.set()
            release.wait(2)
            return payload()
        cfg = base_cfg(
            ZENDURE_LOCAL_API_USE_FOR_TELEMETRY=True,
            ZENDURE_LOCAL_IP="192.0.2.10",
            ZENDURE_LOCAL_API_POLL_INTERVAL_SECONDS=1,
            ZENDURE_LOCAL_API_TELEMETRY_FALLBACK_ONLY=True,
        )
        worker = ZendureLocalApiWorker(ScriptedClient([delayed]), cfg)
        worker.start()
        self.assertTrue(entered.wait(1))
        controller, state, cfg, events = self.make_controller_with_worker(worker, cfg)
        started = time.perf_counter()
        controller.update_zendure_telemetry_from_local_api_snapshot(cfg)
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 0.05)
        release.set()
        worker.request_stop(); worker.join(2)

    def test_controller_source_contains_no_synchronous_fetch_in_snapshot_apply(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "controller_logic.py"), encoding="utf-8") as handle:
            source = handle.read()
        method = source.split("def update_zendure_telemetry_from_local_api_snapshot", 1)[1].split("\n    def ", 1)[0]
        self.assertNotIn("fetch_report", method)
        self.assertNotIn("requests.", method)
        self.assertIn("latest_snapshot()", method)


if __name__ == "__main__":
    unittest.main()
