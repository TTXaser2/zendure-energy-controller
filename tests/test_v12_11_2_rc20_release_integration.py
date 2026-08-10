import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import version
from config_manager import DEFAULT_CONFIG


ROOT = Path(__file__).resolve().parents[1]


class Rc20ReleaseIntegrationTests(unittest.TestCase):
    def test_version_is_rc20_without_measurement_schema_change(self):
        self.assertEqual("12.12.1", version.APP_VERSION)
        self.assertEqual("V12.12.1", version.APP_VERSION_LABEL)
        self.assertEqual("ZEC-MEASUREMENT-V3", version.CSV_SCHEMA)

    def test_migration_cli_check_apply_and_idempotence(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "config.json"
            cfg = dict(DEFAULT_CONFIG)
            cfg["DEVICE_ID"] = "TESTDEVICE"
            cfg["SERVICE_RESTART_COMMAND"] = "arbitrary shell"
            cfg["CUSTOM_EXTENSION"] = {"preserved": True}
            path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
            os.chmod(path, 0o600)
            backup = Path(td) / "config.before-rc20.json"

            check = subprocess.run(
                [sys.executable, str(ROOT / "tools/migrate_rc19_to_rc20.py"),
                 "--config", str(path), "--check-only", "--json"],
                cwd=ROOT, check=True, capture_output=True, text=True,
            )
            checked = json.loads(check.stdout)
            self.assertTrue(checked["changed"])
            self.assertNotEqual(checked["before_file_revision"], checked["after_file_revision"])
            self.assertIn("MIG-RC20-REMOVE-FREE-RESTART-COMMAND", checked["steps"])
            before = path.read_bytes()

            applied = subprocess.run(
                [sys.executable, str(ROOT / "tools/migrate_rc19_to_rc20.py"),
                 "--config", str(path), "--backup", str(backup), "--json"],
                cwd=ROOT, check=True, capture_output=True, text=True,
            )
            result = json.loads(applied.stdout)
            self.assertEqual("migrated", result["status"])
            self.assertEqual(before, backup.read_bytes())
            migrated = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn("SERVICE_RESTART_COMMAND", migrated)
            self.assertEqual({"preserved": True}, migrated["CUSTOM_EXTENSION"])
            self.assertEqual(0o600, path.stat().st_mode & 0o777)
            self.assertEqual(0o600, backup.stat().st_mode & 0o777)

            second = subprocess.run(
                [sys.executable, str(ROOT / "tools/migrate_rc19_to_rc20.py"),
                 "--config", str(path), "--check-only", "--json"],
                cwd=ROOT, check=True, capture_output=True, text=True,
            )
            second_result = json.loads(second.stdout)
            self.assertFalse(second_result["changed"])
            self.assertEqual("no_op", second_result["status"])
            self.assertEqual([], second_result["steps"])


    def test_migration_accepts_rc19_unset_legacy_capacity_forms(self):
        from settings_runtime import migrate_rc19_to_rc20

        for legacy in (None, "", "   "):
            with self.subTest(legacy=legacy):
                migrated, steps = migrate_rc19_to_rc20({
                    "ZENDURE_BATTERY_CAPACITY_KWH": legacy,
                    "CUSTOM_EXTENSION": "preserved",
                })
                self.assertNotIn("ZENDURE_BATTERY_CAPACITY_KWH", migrated)
                self.assertNotIn("ZENDURE_BATTERY_CAPACITY_WH", migrated)
                self.assertEqual("preserved", migrated["CUSTOM_EXTENSION"])
                self.assertIn("MIG-RC20-REMOVE-CAPACITY-KWH", steps)

    def test_migration_accepts_rc19_numeric_string_capacity(self):
        from settings_runtime import migrate_rc19_to_rc20

        migrated, steps = migrate_rc19_to_rc20({
            "ZENDURE_BATTERY_CAPACITY_KWH": " 5.28 ",
        })
        self.assertEqual(5280, migrated["ZENDURE_BATTERY_CAPACITY_WH"])
        self.assertNotIn("ZENDURE_BATTERY_CAPACITY_KWH", migrated)
        self.assertIn("MIG-RC20-CAPACITY-KWH-TO-WH", steps)

    def test_migration_rejects_non_numeric_legacy_capacity(self):
        from settings_runtime import migrate_rc19_to_rc20

        for legacy in (True, "5,28", "invalid", 0, -1, "nan", "inf"):
            with self.subTest(legacy=legacy):
                with self.assertRaisesRegex(ValueError, "ZENDURE_BATTERY_CAPACITY_KWH_INVALID"):
                    migrate_rc19_to_rc20({"ZENDURE_BATTERY_CAPACITY_KWH": legacy})

    def test_updater_is_exact_sequential_atomic_and_rollback_capable(self):
        script = (ROOT / "tools/update_zendure_controller.sh").read_text(encoding="utf-8")
        self.assertIn('EXPECTED_VERSION="v12_12_1"', script)
        self.assertIn('EXPECTED_SOURCE_RC19="12.11.2-rc19"', script)
        self.assertIn('EXPECTED_SOURCE_V12114_VERSION="12.11.4"', script)
        self.assertIn('EXPECTED_SOURCE_V12114_BUILD_ID="v12.11.4-20260807"', script)
        self.assertIn('EXPECTED_SOURCE_V12116_VERSION="12.11.6"', script)
        self.assertIn('EXPECTED_SOURCE_V12116_BUILD_ID="v12.11.6-20260808"', script)
        self.assertIn('EXPECTED_SOURCE_FIX5_BUILD_ID="rc20-audit-fix5-20260806"', script)
        self.assertIn('EXPECTED_TARGET_BUILD_ID="v12.12.1-20260810"', script)
        self.assertIn('TARGET_PACKAGE_VERSION" = "12.12.1"', script)
        self.assertIn("migrate_rc19_to_rc20.py", script)
        self.assertIn("--check-only", script)
        self.assertIn("recover_on_error", script)
        self.assertIn('sudo tar -xzf "$BACKUP" -C /opt', script)
        self.assertIn("evaluate_installation_readiness.py", script)
        self.assertIn("weder ready=true noch einen stabilen sicheren Übergangszustand", script)
        self.assertIn('EXPECTED_SOURCE_FIX6_BUILD_ID="rc20-audit-fix6-20260806"', script)
        self.assertIn("zendure-controller-restart", script)
        self.assertIn("visudo -cf", script)
        self.assertNotIn("SERVICE_RESTART_COMMAND", script)

    def test_updater_has_no_mandatory_node_runtime_dependency(self):
        script = (ROOT / "tools/update_zendure_controller.sh").read_text(encoding="utf-8")
        self.assertIn("verify_source_manifest", script)
        self.assertIn("command -v node", script)
        self.assertIn("Node.js ist nicht installiert; keine Produktivabhängigkeit", script)
        self.assertEqual(2, script.count("node --check"))

    def test_preflight_failure_does_not_touch_productive_services(self):
        script = (ROOT / "tools/update_zendure_controller.sh").read_text(encoding="utf-8")
        branch = script.index('if [ "$INSTALLATION_STARTED" -eq 0 ]')
        early_exit = script.index('exit "$exit_code"', branch)
        service_stop = script.index("sudo systemctl stop", branch)
        self.assertLess(early_exit, service_stop)
        preflight_passed = script.index('echo "Paketpreflight und Config-Migrationspreflight bestanden."')
        installation_start = script.index("INSTALLATION_STARTED=1")
        regular_stop = script.index('echo "Stoppe Dienste..."')
        self.assertLess(preflight_passed, installation_start)
        self.assertLess(installation_start, regular_stop)

    def test_err_trap_is_not_inherited_into_preflight_subshell(self):
        script = (ROOT / "tools/update_zendure_controller.sh").read_text(encoding="utf-8")
        self.assertIn("set -euo pipefail", script)
        self.assertNotIn("set -Eeuo pipefail", script)
        self.assertIn("trap 'recover_on_error $?' ERR", script)
        self.assertIn('${BASH_SUBSHELL:-0}', script)
        self.assertGreaterEqual(script.count("trap - ERR"), 3)
        self.assertNotIn("trap recover_on_error ERR", script)

    def test_preflight_disables_real_restart_and_escalates_resource_warnings(self):
        script = (ROOT / "tools/update_zendure_controller.sh").read_text(encoding="utf-8")
        self.assertIn('ZEC_INSTALLER_PREFLIGHT=1', script)
        self.assertIn('PYTHONWARNINGS="error::ResourceWarning"', script)
        web_ui = (ROOT / "web_ui.py").read_text(encoding="utf-8")
        self.assertIn('os.environ.get("ZEC_INSTALLER_PREFLIGHT") == "1"', web_ui)

    def test_release_manifest_must_not_ship_runtime_logs(self):
        manifest = (ROOT / "V12_12_1_SOURCE_MANIFEST.sha256").read_text(encoding="utf-8")
        self.assertNotIn("./logs/", manifest)
        self.assertNotIn(".sqlite3", manifest)

    def test_restart_helper_is_fixed_and_has_no_user_payload(self):
        helper = (ROOT / "systemd/zendure-controller-restart").read_text(encoding="utf-8")
        sudoers = (ROOT / "systemd/zendure-controller-sudoers").read_text(encoding="utf-8")
        self.assertEqual(
            "#!/bin/bash\nset -euo pipefail\n/bin/systemctl restart zendure-controller.service\n",
            helper,
        )
        self.assertIn("NOPASSWD: /usr/local/sbin/zendure-controller-restart", sudoers)
        self.assertNotIn("ALL", sudoers.split("NOPASSWD:", 1)[1])

    def test_example_config_is_valid_json_without_free_restart_command(self):
        cfg = json.loads((ROOT / "config.example.json").read_text(encoding="utf-8"))
        self.assertNotIn("SERVICE_RESTART_COMMAND", cfg)
        self.assertIn("HEADLESS_MODE", cfg)
        self.assertIn("UI_MODE", cfg)


if __name__ == "__main__":
    unittest.main()
