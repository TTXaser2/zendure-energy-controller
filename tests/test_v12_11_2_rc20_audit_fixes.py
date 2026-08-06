import asyncio
import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from starlette.requests import Request

from config_manager import CONFIG_SCHEMA, ConfigManager, DEFAULT_CONFIG
from settings_model import build_settings_model
from operational_events import OperationalEventJournal
from settings_runtime import (
    LastGoodStore,
    LEGACY_MIGRATION_MATRIX,
    STARTUP_RECOVERY_WAITING,
    migrate_rc19_to_rc20,
    parse_full_candidate,
)
from state import ControllerState
from storage_inventory import StorageInventory
from web_ui import APP_BUILD_ID, APP_VERSION, build_ready_payload, build_settings_page, create_app, trigger_service_restart

ROOT = Path(__file__).resolve().parents[1]


def endpoint(app, path, method):
    method = method.upper()
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return route.endpoint
    raise AssertionError(f"Route {method} {path} missing")


def request(path, *, method="GET", body=None, csrf="", origin="http://testserver"):
    data = json.dumps(body or {}).encode("utf-8")
    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": data, "more_body": False}

    headers = [(b"host", b"testserver")]
    if origin:
        headers.append((b"origin", origin.encode()))
    if csrf:
        headers.extend([(b"cookie", f"zec_settings_csrf={csrf}".encode()), (b"x-csrf-token", csrf.encode())])
    return Request({
        "type": "http", "method": method, "scheme": "http",
        "server": ("testserver", 80), "client": ("127.0.0.1", 1234),
        "path": path, "query_string": b"", "headers": headers,
    }, receive)


class Rc20AuditFixTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.config_path = Path(self.tempdir.name) / "config.json"

    def config(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg.update({"DEVICE_ID": "TESTDEVICE", "MQTT_BROKER": "127.0.0.1", "HEADLESS_MODE": False,
                    "OPERATIONAL_EVENTS_DB_PATH": str(Path(self.tempdir.name) / "operational_events.sqlite3")})
        return cfg

    def manager(self):
        self.config_path.write_text(json.dumps(self.config(), indent=2) + "\n", encoding="utf-8")
        os.chmod(self.config_path, 0o600)
        manager = ConfigManager(str(self.config_path))
        manager.load()
        return manager

    def promote(self, manager, start=0.0):
        manager.observe_ready(True, now_monotonic=start, proof_revision="proof-1")
        result = manager.observe_ready(True, now_monotonic=start + 301.0, proof_revision="proof-1")
        self.assertTrue(result["promotion_scheduled"])
        self.assertTrue(manager.wait_for_promotion(3.0))
        self.assertIn(manager.status()["last_promotion"]["status"], {"promoted", "no_op"})

    def healthy_ready_snapshot(self):
        return {
            "uptime_seconds": 100,
            "mqtt_connected": True,
            "last_shelly_update_age_seconds": 1,
            "grid_power_valid": True,
            "battery_soc": 80,
            "last_soc_update_age_seconds": 1,
            "soc_valid": True,
            "zendure_telemetry_source": "MQTT",
            "zendure_local_api_fallback_active": False,
            "mqtt_command_path_available": True,
            "mqtt_command_path_fresh": True,
            "mqtt_command_path_valid": True,
            "actual_zendure_power_valid": True,
            "zendure_command_state_complete": True,
            "zendure_command_smart_mode": 1,
            "zendure_command_ac_mode": "Input mode",
            "zendure_command_input_limit_w": 500,
            "zendure_command_output_limit_w": 0,
            "command_desired_sequence_id": 0,
            "command_readback_matches_desired": False,
            "command_uncertain_mqtt_active": False,
            "command_not_effective_active": False,
            "command_late_effect_guard_active": False,
            "command_lifecycle_state": "ACTIVE_EFFECTIVE",
            "command_resync_count": 0,
            "command_late_effect_guard_activation_count": 0,
            "safe_state_counter": 0,
            "current_mode": "HOLD",
            "consecutive_errors": 0,
            "last_error": "none",
            "last_error_time": "-",
        }

    def test_full_readiness_rejects_each_command_safety_failure(self):
        cfg = {"SHELLY_STALE_TIMEOUT_SECONDS": 15, "SOC_STALE_TIMEOUT_SECONDS": 90, "CROSS_CHARGE_ENABLED": False}
        base = self.healthy_ready_snapshot()
        self.assertTrue(build_ready_payload(cfg, base)["ready"])
        cases = {
            "command_path": ("mqtt_command_path_valid", False),
            "command_state": ("zendure_command_state_complete", False),
            "smart_mode": ("zendure_command_smart_mode", 0),
            "counter_limit": ("zendure_command_output_limit_w", 50),
            "telemetry": ("actual_zendure_power_valid", False),
            "uncertain": ("command_uncertain_mqtt_active", True),
            "mismatch": ("command_not_effective_active", True),
            "late_guard": ("command_late_effect_guard_active", True),
            "readback_mismatch": ("command_desired_sequence_id", 1),
        }
        for name, (key, value) in cases.items():
            with self.subTest(name=name):
                snap = dict(base)
                snap[key] = value
                self.assertFalse(build_ready_payload(cfg, snap)["ready"])

    def test_recovery_waiting_does_not_activate_or_promote_for_each_failed_gate(self):
        cfg = {"SHELLY_STALE_TIMEOUT_SECONDS": 15, "SOC_STALE_TIMEOUT_SECONDS": 90, "CROSS_CHARGE_ENABLED": False}
        cases = {
            "command_path": ("mqtt_command_path_valid", False),
            "command_state": ("zendure_command_state_complete", False),
            "smart_mode": ("zendure_command_smart_mode", 0),
            "counter_limit": ("zendure_command_output_limit_w", 50),
            "telemetry": ("actual_zendure_power_valid", False),
            "uncertain": ("command_uncertain_mqtt_active", True),
            "mismatch": ("command_not_effective_active", True),
            "late_guard": ("command_late_effect_guard_active", True),
            "readback_mismatch": ("command_desired_sequence_id", 1),
        }
        for index, (name, (key, value)) in enumerate(cases.items()):
            with self.subTest(name=name):
                manager = self.manager()
                self.promote(manager, start=1000.0 + index * 1000.0)
                self.config_path.write_text('{"DEADBAND_W": 2000}\n', encoding="utf-8")
                os.chmod(self.config_path, 0o600)
                recovered = ConfigManager(str(self.config_path))
                recovered.load()
                self.assertEqual(STARTUP_RECOVERY_WAITING, recovered.startup_mode())
                snap = self.healthy_ready_snapshot()
                snap[key] = value
                ready = build_ready_payload(cfg, snap)
                self.assertFalse(ready["ready"])
                result = recovered.observe_ready(
                    ready["ready"], now_monotonic=20_000.0 + index, proof_revision=ready["proof_revision"]
                )
                self.assertEqual(STARTUP_RECOVERY_WAITING, recovered.startup_mode())
                self.assertFalse(recovered.control_allowed())
                self.assertFalse(result["promotion_scheduled"])
                self.assertFalse(recovered.status()["promotion_in_flight"])

    def test_promotion_is_nonblocking_single_flight(self):
        manager = self.manager()
        original = manager.last_good_store.promote

        worker_threads = []

        def delayed(*args, **kwargs):
            import threading
            worker_threads.append(threading.current_thread().name)
            time.sleep(0.25)
            return original(*args, **kwargs)

        manager.last_good_store.promote = delayed
        manager.observe_ready(True, now_monotonic=0, proof_revision="p")
        started = time.monotonic()
        result = manager.observe_ready(True, now_monotonic=301, proof_revision="p")
        elapsed = time.monotonic() - started
        self.assertTrue(result["promotion_scheduled"])
        self.assertLess(elapsed, 0.08)
        second = manager.observe_ready(True, now_monotonic=302, proof_revision="p")
        self.assertFalse(second["promotion_scheduled"])
        self.assertTrue(manager.wait_for_promotion(3.0))
        self.assertEqual(["zec-last-good-promotion"], worker_threads)

    def test_invalid_primary_remains_configured_while_last_good_is_effective(self):
        manager = self.manager()
        self.promote(manager)
        bad = self.config()
        bad["DEADBAND_W"] = 2000
        self.config_path.write_text(json.dumps(bad, indent=2) + "\n", encoding="utf-8")
        os.chmod(self.config_path, 0o600)
        recovered = ConfigManager(str(self.config_path))
        recovered.load()
        self.assertEqual(2000, recovered.get_configured()["DEADBAND_W"])
        self.assertNotEqual(2000, recovered.get()["DEADBAND_W"])
        model = build_settings_model(recovered, {})
        item = next(x for c in model["categories"] for sec in c["sections"] for x in sec["settings"] if x["key"] == "DEADBAND_W")
        self.assertEqual(2000, item["configured"])
        self.assertNotEqual(item["configured"], item["effective"])

    def test_runtime_invalid_source_is_explicit(self):
        manager = self.manager()
        self.config_path.write_text('{"HEADLESS_MODE": false,', encoding="utf-8")
        manager.reload_if_needed()
        self.assertEqual("last_valid_runtime", manager.status()["effective_source"])

    def test_last_good_rejects_wide_mode_symlink_and_wrong_owner(self):
        manager = self.manager()
        self.promote(manager)
        selected, _ = manager.last_good_store.select_recovery()
        self.assertIsNotNone(selected)
        slot = selected.slot
        path = Path(manager.last_good_store.config_path_for(slot))
        os.chmod(path, 0o644)
        self.assertFalse(manager.last_good_store.validate_slot(slot).valid)
        os.chmod(path, 0o600)
        wrong_owner_store = LastGoodStore(
            str(self.config_path), APP_VERSION,
            expected_uid=os.geteuid() + 1000,
            expected_gid=os.getegid(),
        )
        self.assertFalse(wrong_owner_store.validate_slot(slot).valid)
        saved = path.with_suffix(path.suffix + ".saved")
        path.rename(saved)
        path.symlink_to(saved)
        self.assertFalse(manager.last_good_store.validate_slot(slot).valid)

    def test_storage_snapshot_get_is_o1_and_refresh_is_single_flight(self):
        calls = []

        def slow_builder():
            calls.append(time.monotonic())
            time.sleep(0.15)
            return {"available": True, "file_count": 5000, "row_count": 10_000_000}

        inventory = StorageInventory(slow_builder)
        started = time.monotonic()
        self.assertEqual("pending", inventory.snapshot()["status"])
        self.assertLess(time.monotonic() - started, 0.02)
        self.assertEqual("scheduled", inventory.refresh_async()["status"])
        self.assertEqual("already_running", inventory.refresh_async()["status"])
        started = time.monotonic()
        self.assertTrue(inventory.snapshot()["refresh_in_flight"])
        self.assertLess(time.monotonic() - started, 0.02)
        self.assertTrue(inventory.wait(2.0))
        self.assertEqual(1, len(calls))
        self.assertEqual(5000, inventory.snapshot()["file_count"])

    def test_storage_http_get_never_invokes_inventory_builder(self):
        manager = self.manager()
        state = ControllerState()
        calls = []
        with patch("web_ui.measurement_availability", side_effect=lambda cfg: calls.append(1) or {"available": True}):
            app = create_app(manager, state)
            data = endpoint(app, "/storage/status", "GET")()
            self.assertEqual("pending", data["status"])
            self.assertEqual([], calls)

    def test_pointer_repair_binds_all_hashes_and_requires_confirmation(self):
        manager = self.manager()
        self.promote(manager)
        Path(str(self.config_path) + ".last-good.current").unlink()
        app = create_app(manager, ControllerState())
        token = "x" * 40
        preview = asyncio.run(endpoint(app, "/admin/last-good-pointer-repair/preview", "POST")(
            request("/admin/last-good-pointer-repair/preview", method="POST", csrf=token, body={})
        ))
        self.assertIsInstance(preview, dict)
        for key in ("generation_id", "typed_revision", "config_hash", "manifest_hash", "store_revision"):
            self.assertTrue(preview.get(key) not in (None, ""), key)
        commit_route = endpoint(app, "/admin/last-good-pointer-repair/commit", "POST")
        missing = asyncio.run(commit_route(request(
            "/admin/last-good-pointer-repair/commit", method="POST", csrf=token,
            body={"action_token": preview["action_token"]},
        )))
        self.assertEqual(422, missing.status_code)
        result = asyncio.run(commit_route(request(
            "/admin/last-good-pointer-repair/commit", method="POST", csrf=token,
            body={"action_token": preview["action_token"], "confirmation": "REPAIR_POINTER"},
        )))
        self.assertEqual("repaired", result["status"])

    def test_installer_preflight_journal_falls_back_to_tmp_not_source_tree(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg["OPERATIONAL_EVENTS_DB_PATH"] = ""
        with patch.dict(os.environ, {"ZEC_INSTALLER_PREFLIGHT": "1"}, clear=False):
            path = OperationalEventJournal(lambda: cfg, ControllerState()).path()
        self.assertTrue(path.startswith(f"/tmp/zec-installer-preflight-{os.getpid()}/"))
        self.assertTrue(path.endswith("zec_operational_events.sqlite3"))

    def test_installer_preflight_blocks_real_restart_subprocess(self):
        with patch.dict(os.environ, {"ZEC_INSTALLER_PREFLIGHT": "1"}, clear=False), \
                patch("web_ui.subprocess.Popen") as popen:
            trigger_service_restart({})
        popen.assert_not_called()

    def test_restart_requires_explicit_confirmation_and_returns_ready_contract(self):
        manager = self.manager()
        candidate = manager.candidate_base_config()
        candidate["WEB_SERVICE_RESTART_ENABLED"] = True
        manager.commit_candidate(candidate, manager.configured_revision())
        app = create_app(manager, ControllerState())
        route = endpoint(app, "/restart-service", "POST")
        token = "x" * 40
        missing = asyncio.run(route(request("/restart-service", method="POST", csrf=token, body={})))
        self.assertEqual(422, missing.status_code)
        with patch("web_ui.os.path.isfile", return_value=True), patch("web_ui.os.access", return_value=True), patch("web_ui.delayed_service_restart"):
            result = asyncio.run(route(request(
                "/restart-service", method="POST", csrf=token,
                body={"confirmation": "RESTART_SERVICE"},
            )))
        self.assertEqual("restart_scheduled", result["status"])
        self.assertEqual(APP_VERSION, result["expected_version"])
        self.assertEqual(APP_BUILD_ID, result["expected_build_id"])
        self.assertIn("build_id=expected_build_id", result["success_condition"])
        self.assertEqual("/ready", result["ready_url"])

    def test_installer_root_artifact_rollback_fixture(self):
        completed = subprocess.run(
            ["bash", str(ROOT / "tests" / "test_installer_root_artifact_transaction.sh")],
            cwd=str(ROOT), check=True, capture_output=True, text=True,
        )
        self.assertIn("PASS", completed.stdout)

    def test_legacy_migration_matrix_is_explicit_and_idempotent(self):
        raw = {
            "ZENDURE_BATTERY_CAPACITY_KWH": 5.28,
            "SMA_DISCHARGE_BLOCK_W": 80,
            "CROSS_CHARGE_RESERVE_W": 100,
            "MEASUREMENT_DB_MAX_QUEUE_ROWS": 5000,
            "HARVEST_CAPACITY_WEIGHTING_MODE": "diagnostic",
            "CUSTOM_EXTENSION": {"keep": True},
        }
        migrated, steps = migrate_rc19_to_rc20(raw)
        self.assertEqual(5280, migrated["ZENDURE_BATTERY_CAPACITY_WH"])
        self.assertEqual(80, migrated["CROSS_CHARGE_SIGNIFICANT_W"])
        self.assertNotIn("ZENDURE_BATTERY_CAPACITY_KWH", migrated)
        self.assertNotIn("SMA_DISCHARGE_BLOCK_W", migrated)
        self.assertNotIn("CROSS_CHARGE_RESERVE_W", migrated)
        self.assertNotIn("MEASUREMENT_DB_MAX_QUEUE_ROWS", migrated)
        self.assertEqual("diagnostic", migrated["HARVEST_CAPACITY_WEIGHTING_MODE"])
        self.assertEqual({"keep": True}, migrated["CUSTOM_EXTENSION"])
        again, second_steps = migrate_rc19_to_rc20(migrated)
        self.assertEqual(migrated, again)
        self.assertEqual((), second_steps)
        self.assertEqual(12, len(LEGACY_MIGRATION_MATRIX))
        self.assertTrue(steps)


    def test_retired_s1_authorities_are_removed_and_conflicts_fail_closed(self):
        retired = {
            "ZENDURE_BATTERY_CAPACITY_KWH", "SMA_DISCHARGE_BLOCK_W",
            "CROSS_CHARGE_RESERVE_W", "MEASUREMENT_DB_MAX_QUEUE_ROWS",
            "HARVEST_IMPORT_EXIT_CONFIRM_SECONDS", "HARVEST_IMPORT_REDUCE_CONFIRM_SECONDS",
            "HARVEST_PRIMARY_BELOW_FLOOR_CONFIRM_SECONDS", "HARVEST_PRIMARY_RESTART_CONFIRM_SECONDS",
            "SERVICE_RESTART_COMMAND",
        }
        example = json.loads((ROOT / "config.example.json").read_text(encoding="utf-8"))
        for key in retired:
            with self.subTest(key=key):
                self.assertNotIn(key, DEFAULT_CONFIG)
                self.assertNotIn(key, CONFIG_SCHEMA)
                self.assertNotIn(key, example)
        self.assertFalse(parse_full_candidate({"SMA_DISCHARGE_BLOCK_W": 80}).valid)
        with self.assertRaisesRegex(ValueError, "CROSS_CHARGE_SIGNIFICANT_W_CONFLICT"):
            migrate_rc19_to_rc20({"SMA_DISCHARGE_BLOCK_W": 80, "CROSS_CHARGE_SIGNIFICANT_W": 100})
        with self.assertRaisesRegex(ValueError, "ZENDURE_BATTERY_CAPACITY_CONFLICT"):
            migrate_rc19_to_rc20({"ZENDURE_BATTERY_CAPACITY_KWH": 5.28, "ZENDURE_BATTERY_CAPACITY_WH": 2400})

    def test_settings_shell_has_real_drawer_mobile_categories_manual_and_no_legacy_template(self):
        html = build_settings_page(self.config())
        script = (ROOT / "static" / "settings_v2.js").read_text(encoding="utf-8")
        for marker in ("searchDrawer", "mobileCategories", "/manual.pdf", "pointerRepairAction"):
            self.assertIn(marker, html)
        self.assertNotIn("legacy-settings-contract", html)
        self.assertIn("pollReady", script)
        self.assertIn("REPAIR_POINTER", script)


if __name__ == "__main__":
    unittest.main()
