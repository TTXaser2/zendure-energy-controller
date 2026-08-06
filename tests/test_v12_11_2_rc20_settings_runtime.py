import json
import os
import tempfile
import unittest
from pathlib import Path

from config_manager import ConfigManager, DEFAULT_CONFIG
from settings_runtime import (
    STARTUP_NORMAL,
    STARTUP_RECOVERY_ACTIVE,
    STARTUP_RECOVERY_WAITING,
    atomic_write,
    migrate_rc19_to_rc20,
    pretty_json_bytes,
    stable_read,
)


class Rc20SettingsRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.path = Path(self.tempdir.name) / "config.json"

    def full_config(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg["DEVICE_ID"] = "TESTDEVICE"
        cfg["MQTT_BROKER"] = "127.0.0.1"
        return cfg

    def write(self, value):
        self.path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        os.chmod(self.path, 0o600)

    def manager(self):
        manager = ConfigManager(str(self.path))
        manager.load()
        return manager

    def test_valid_startup_has_full_effective_view_and_exact_file_revision(self):
        cfg = self.full_config()
        cfg.pop("LOG_RAW_RESPONSE")
        self.write(cfg)
        manager = self.manager()
        self.assertEqual(STARTUP_NORMAL, manager.startup_mode())
        self.assertTrue(manager.control_allowed())
        self.assertEqual(False, manager.get()["LOG_RAW_RESPONSE"])
        self.assertIn("LOG_RAW_RESPONSE", manager.status()["inherited_default_keys"])
        self.assertEqual(stable_read(str(self.path)).revision, manager.configured_revision())

    def test_commit_does_not_materialise_unrelated_inherited_defaults(self):
        cfg = self.full_config()
        cfg.pop("LOG_RAW_RESPONSE")
        self.write(cfg)
        manager = self.manager()
        base = manager.configured_revision()
        candidate = manager.candidate_base_config()
        candidate["HEADLESS_MODE"] = True
        manager.commit_candidate(candidate, base)
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertTrue(saved["HEADLESS_MODE"])
        self.assertNotIn("LOG_RAW_RESPONSE", saved)
        self.assertNotIn("MEASUREMENT_DB_MAINTENANCE_MODE", saved)

    def test_invalid_runtime_file_keeps_last_valid_effective_snapshot(self):
        self.write(self.full_config())
        manager = self.manager()
        before = manager.get()
        self.path.write_text('{"HEADLESS_MODE": false,', encoding="utf-8")
        _cfg, changed = manager.reload_if_needed()
        self.assertFalse(changed)
        self.assertEqual(before, manager.get())
        self.assertEqual("invalid_runtime", manager.status()["config_health"])
        self.assertTrue(manager.control_allowed())

    def test_valid_live_reload_applies_headless_without_restart(self):
        cfg = self.full_config()
        cfg["HEADLESS_MODE"] = True
        self.write(cfg)
        manager = self.manager()
        cfg["HEADLESS_MODE"] = False
        self.write(cfg)
        _effective, changed = manager.reload_if_needed()
        self.assertTrue(changed)
        self.assertFalse(manager.get()["HEADLESS_MODE"])
        self.assertFalse(manager.pending_restart())

    def test_commit_emits_one_controller_reload_edge_for_subsystem_refresh(self):
        self.write(self.full_config())
        manager = self.manager()
        candidate = manager.candidate_base_config()
        candidate["ZENDURE_LOCAL_API_TIMEOUT_SECONDS"] = 7
        manager.commit_candidate(candidate, manager.configured_revision())
        cfg, changed = manager.reload_if_needed()
        self.assertTrue(changed)
        self.assertEqual(7, cfg["ZENDURE_LOCAL_API_TIMEOUT_SECONDS"])
        _cfg, changed_again = manager.reload_if_needed()
        self.assertFalse(changed_again)

    def test_restart_setting_is_configured_but_not_effective_until_process_restart(self):
        cfg = self.full_config()
        self.write(cfg)
        manager = self.manager()
        candidate = manager.candidate_base_config()
        candidate["WEB_PORT"] = 8081
        result = manager.commit_candidate(candidate, manager.configured_revision())
        self.assertEqual(8081, manager.get_configured()["WEB_PORT"])
        self.assertEqual(8080, manager.get()["WEB_PORT"])
        self.assertIn("WEB_PORT", result["pending_restart_keys"])

    def test_cas_rejects_changed_file_bytes_even_when_semantically_equal(self):
        cfg = self.full_config()
        self.write(cfg)
        manager = self.manager()
        old = manager.configured_revision()
        self.path.write_text(json.dumps(cfg, sort_keys=True) + "\n", encoding="utf-8")
        candidate = manager.candidate_base_config()
        candidate["HEADLESS_MODE"] = True
        with self.assertRaisesRegex(RuntimeError, "CONFIG_REVISION_CONFLICT"):
            manager.commit_candidate(candidate, old)

    def test_secret_is_redacted_in_both_views(self):
        cfg = self.full_config()
        cfg["MQTT_PASSWORD"] = "top-secret"
        self.write(cfg)
        manager = self.manager()
        self.assertEqual({"secret_set": True}, manager.redacted_config(configured=True)["MQTT_PASSWORD"])
        self.assertNotIn("top-secret", json.dumps(manager.status()))

    def test_stable_ready_promotes_once_per_typed_revision(self):
        self.write(self.full_config())
        manager = self.manager()
        self.assertFalse(manager.observe_ready(True, now_monotonic=10.0)["promoted"])
        result = manager.observe_ready(True, now_monotonic=311.0)
        self.assertTrue(result["promotion_scheduled"])
        self.assertTrue(manager.wait_for_promotion())
        self.assertEqual("promoted", manager.status()["last_promotion"]["status"])
        second = manager.observe_ready(True, now_monotonic=700.0)
        self.assertFalse(second["promotion_scheduled"])
        store = manager.status()["last_good_store"]
        self.assertIn(store["selected_slot"], ("A", "B"))

    def test_invalid_primary_can_wait_then_activate_valid_last_good_without_repair_write(self):
        self.write(self.full_config())
        first = self.manager()
        first.observe_ready(True, now_monotonic=1.0)
        first.observe_ready(True, now_monotonic=302.0)
        self.assertTrue(first.wait_for_promotion())
        pointer_before = Path(str(self.path) + ".last-good.current").read_bytes()
        self.path.write_text('{"broken":', encoding="utf-8")
        second = ConfigManager(str(self.path))
        second.load()
        self.assertEqual(STARTUP_RECOVERY_WAITING, second.startup_mode())
        self.assertFalse(second.control_allowed())
        second.observe_ready(True, now_monotonic=1000.0)
        self.assertEqual(STARTUP_RECOVERY_ACTIVE, second.startup_mode())
        self.assertTrue(second.control_allowed())
        self.assertEqual(pointer_before, Path(str(self.path) + ".last-good.current").read_bytes())

    def _build_two_last_good_generations(self):
        self.write(self.full_config())
        manager = self.manager()
        manager.observe_ready(True, now_monotonic=0)
        manager.observe_ready(True, now_monotonic=301)
        self.assertTrue(manager.wait_for_promotion())
        candidate = manager.candidate_base_config()
        candidate["DEADBAND_W"] = 95
        manager.commit_candidate(candidate, manager.configured_revision())
        manager.observe_ready(True, now_monotonic=400)
        manager.observe_ready(True, now_monotonic=701)
        self.assertTrue(manager.wait_for_promotion())
        return manager

    def test_missing_pointer_selects_unique_higher_valid_generation_without_mtime(self):
        manager = self._build_two_last_good_generations()
        pointer = Path(str(self.path) + ".last-good.current")
        pointer.unlink()
        self.path.write_text('{"broken":', encoding="utf-8")
        recovered = ConfigManager(str(self.path))
        recovered.load()
        self.assertEqual(STARTUP_RECOVERY_WAITING, recovered.startup_mode())
        status = recovered.status()["last_good_store"]
        self.assertEqual("higher_generation_B", status["selection_reason"])
        self.assertEqual("B", status["selected_slot"])
        self.assertFalse(pointer.exists())

    def test_pointer_only_repair_changes_no_slot_bytes_and_preserves_recovery_state(self):
        manager = self._build_two_last_good_generations()
        slot_b = Path(str(self.path) + ".last-good.B")
        slot_b.write_text('{"corrupt":', encoding="utf-8")
        self.path.write_text('{"broken":', encoding="utf-8")
        recovered = ConfigManager(str(self.path))
        recovered.load()
        self.assertEqual(STARTUP_RECOVERY_WAITING, recovered.startup_mode())
        status = recovered.status()
        self.assertTrue(status["last_good_store_repair_required"])
        self.assertEqual("A", status["last_good_store"]["selected_slot"])
        slot_paths = [Path(str(self.path) + suffix) for suffix in (
            ".last-good.A", ".last-good.A.manifest.json", ".last-good.B", ".last-good.B.manifest.json"
        )]
        before = {path.name: path.read_bytes() for path in slot_paths}
        result = recovered.last_good_store.repair_pointer(status["last_good_store_revision"], "A")
        self.assertEqual("repaired", result["status"])
        self.assertEqual(STARTUP_RECOVERY_WAITING, recovered.startup_mode())
        self.assertEqual(before, {path.name: path.read_bytes() for path in slot_paths})
        pointer = json.loads(Path(str(self.path) + ".last-good.current").read_text(encoding="utf-8"))
        self.assertEqual("A", pointer["slot"])

    def test_productive_rc19_cross_charge_and_harvest_are_compatible_without_future_switch(self):
        cfg = self.full_config()
        cfg["CROSS_CHARGE_ENABLED"] = True
        cfg["REST_SURPLUS_HARVEST_ENABLED"] = True
        cfg["SECOND_BATTERY_MAX_CHARGE_POWER_W"] = 2300
        cfg.pop("SECOND_BATTERY_INTEGRATION_ENABLED", None)
        self.write(cfg)
        manager = self.manager()
        self.assertTrue(manager.control_allowed())
        self.assertTrue(manager.get()["SECOND_BATTERY_INTEGRATION_ENABLED"])
        self.assertNotIn("SECOND_BATTERY_INTEGRATION_ENABLED", json.loads(self.path.read_text(encoding="utf-8")))

    def test_rc19_migration_is_narrow_idempotent_and_preserves_unknown(self):
        cfg = self.full_config()
        cfg["SERVICE_RESTART_COMMAND"] = "arbitrary shell"
        cfg["CUSTOM_EXTENSION"] = {"x": 1}
        migrated, steps = migrate_rc19_to_rc20(cfg)
        self.assertNotIn("SERVICE_RESTART_COMMAND", migrated)
        self.assertEqual({"x": 1}, migrated["CUSTOM_EXTENSION"])
        self.assertNotIn("MEASUREMENT_DB_MAINTENANCE_MODE", migrated)
        second, second_steps = migrate_rc19_to_rc20(migrated)
        self.assertEqual(migrated, second)
        self.assertEqual(tuple(), second_steps)
        self.assertIn("MIG-RC20-REMOVE-FREE-RESTART-COMMAND", steps)

    def test_internal_manual_completion_preserves_pending_and_absent_defaults(self):
        cfg = self.full_config()
        cfg.pop("LOG_RAW_RESPONSE")
        cfg["CUSTOM_EXTENSION"] = "preserve"
        self.write(cfg)
        manager = self.manager()
        candidate = manager.candidate_base_config()
        candidate["WEB_PORT"] = 8081
        manager.commit_candidate(candidate, manager.configured_revision())
        manager.update_internal_live_setting("MANUAL_MODE", "AUTO")
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertNotIn("LOG_RAW_RESPONSE", saved)
        self.assertEqual("preserve", saved["CUSTOM_EXTENSION"])
        self.assertEqual(8081, saved["WEB_PORT"])
        self.assertEqual(8080, manager.get()["WEB_PORT"])
        self.assertIn("WEB_PORT", manager.pending_restart_keys())

    def test_unknown_key_change_is_current_and_last_good_remains_valid(self):
        cfg = self.full_config()
        cfg["CUSTOM_EXTENSION"] = {"revision": 1}
        self.write(cfg)
        manager = self.manager()
        candidate = manager.candidate_base_config()
        candidate["CUSTOM_EXTENSION"] = {"revision": 2}
        manager.commit_candidate(candidate, manager.configured_revision())
        self.assertEqual({"revision": 2}, manager.get()["CUSTOM_EXTENSION"])
        manager.observe_ready(True, now_monotonic=0)
        result = manager.observe_ready(True, now_monotonic=301)
        self.assertTrue(result["promotion_scheduled"])
        self.assertTrue(manager.wait_for_promotion())
        selected, status = manager.last_good_store.select_recovery()
        self.assertIsNotNone(selected, status)
        self.assertTrue(selected.valid)
        self.assertEqual({"revision": 2}, selected.config["CUSTOM_EXTENSION"])

    def test_config_and_last_good_files_are_mode_0600(self):
        self.write(self.full_config())
        manager = self.manager()
        candidate = manager.candidate_base_config()
        candidate["HEADLESS_MODE"] = True
        manager.commit_candidate(candidate, manager.configured_revision())
        self.assertEqual(0o600, os.stat(self.path).st_mode & 0o777)
        # Return to normal and promote this revision.
        candidate = manager.candidate_base_config()
        candidate["HEADLESS_MODE"] = False
        manager.commit_candidate(candidate, manager.configured_revision())
        manager.observe_ready(True, now_monotonic=0)
        manager.observe_ready(True, now_monotonic=301)
        self.assertTrue(manager.wait_for_promotion())
        for suffix in (".last-good.current", ".last-good.A", ".last-good.A.manifest.json", ".last-good.B", ".last-good.B.manifest.json"):
            path = Path(str(self.path) + suffix)
            if path.exists():
                self.assertEqual(0o600, os.stat(path).st_mode & 0o777, suffix)


if __name__ == "__main__":
    unittest.main()
