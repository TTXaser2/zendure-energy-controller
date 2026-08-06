# SPDX-License-Identifier: AGPL-3.0-or-later

import ast
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import MappingProxyType

import config_manager
from settings_codecs import parse_value
from settings_registry import (
    ApplyClass,
    Editability,
    SETTINGS,
    SETTINGS_BY_KEY,
    category_names,
    registry_snapshot,
)

ROOT = Path(__file__).resolve().parents[1]


class TestS11SettingsRegistry(unittest.TestCase):
    def test_registry_has_all_target_settings_exactly_once(self):
        self.assertEqual(212, len(SETTINGS))
        self.assertEqual(len(SETTINGS), len(SETTINGS_BY_KEY))
        self.assertEqual(list(range(len(SETTINGS))), [spec.order for spec in SETTINGS])

    def test_all_rc19_defaults_are_registered_and_parse(self):
        self.assertEqual(181, len(config_manager.DEFAULT_CONFIG))
        self.assertEqual(set(), set(config_manager.DEFAULT_CONFIG) - set(SETTINGS_BY_KEY))
        for key, value in config_manager.DEFAULT_CONFIG.items():
            with self.subTest(key=key):
                result = parse_value(SETTINGS_BY_KEY[key], value)
                self.assertTrue(result.ok, result.issue)

    def test_all_new_install_defaults_parse(self):
        for spec in SETTINGS:
            with self.subTest(key=spec.key):
                result = parse_value(spec, spec.default_new_install)
                self.assertTrue(result.ok, result.issue)

    def test_dependency_and_validator_references_are_closed(self):
        valid_rule_ids = {"VAL-{:03d}".format(number) for number in range(1, 25)}
        for spec in SETTINGS:
            with self.subTest(key=spec.key):
                self.assertTrue(set(spec.dependency_keys).issubset(SETTINGS_BY_KEY))
                self.assertTrue(set(spec.validator_ids).issubset(valid_rule_ids))

    def test_category_order_is_the_confirmed_information_architecture(self):
        self.assertEqual(
            (
                "Betriebsart & manuelle Steuerung",
                "Zendure-Geräte",
                "Leistungsgrenzen & SOC-Schutz",
                "AUTO-Regelung",
                "Nachtbetrieb",
                "Primärspeicher & SMA",
                "Harvest / Restüberschuss",
                "Cross-Charge-Schutz",
                "Kommandowirkung & Resync",
                "Messdaten & Speicherung",
                "Schnittstellen & Datenquellen",
                "System & Diagnose",
            ),
            category_names(),
        )

    def test_apply_and_editability_classes_are_explicit(self):
        counts = {apply_class: 0 for apply_class in ApplyClass}
        for spec in SETTINGS:
            counts[spec.apply_class] += 1
        self.assertEqual(183, counts[ApplyClass.LIVE_NEXT_CYCLE])
        self.assertEqual(8, counts[ApplyClass.RESTART_REQUIRED])
        self.assertEqual(19, counts[ApplyClass.MIGRATION_ONLY])
        self.assertEqual(1, counts[ApplyClass.PROTECTED_ACTION])
        self.assertEqual(1, counts[ApplyClass.READ_ONLY])
        self.assertEqual(ApplyClass.PROTECTED_ACTION, SETTINGS_BY_KEY["MEASUREMENT_DB_PATH"].apply_class)
        self.assertEqual(Editability.READ_ONLY, SETTINGS_BY_KEY["REPLAY_WEB_PORT"].editability)
        self.assertEqual(Editability.MIGRATION_ONLY, SETTINGS_BY_KEY["SERVICE_RESTART_COMMAND"].editability)

    def test_registry_mapping_is_immutable(self):
        self.assertIsInstance(SETTINGS_BY_KEY, MappingProxyType)
        with self.assertRaises(TypeError):
            SETTINGS_BY_KEY["NEW_KEY"] = SETTINGS[0]
        with self.assertRaises(Exception):
            SETTINGS[0].key = "CHANGED"

    def test_secret_snapshot_never_contains_secret_default_values(self):
        snapshot = registry_snapshot()
        mqtt_password = next(item for item in snapshot["settings"] if item["key"] == "MQTT_PASSWORD")
        self.assertNotIn("default_new_install", mqtt_password)
        self.assertNotIn("default_rc19", mqtt_password)
        self.assertEqual("empty", mqtt_password["default_new_install_state"])
        payload = json.dumps(snapshot, ensure_ascii=False)
        self.assertNotIn('"MQTT_PASSWORD":', payload)

    def test_checked_in_snapshot_matches_python_registry(self):
        expected = json.dumps(registry_snapshot(), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        actual = (ROOT / "generated" / "SETTINGS_REGISTRY_SNAPSHOT.json").read_text(encoding="utf-8")
        self.assertEqual(expected, actual)

    def test_export_tool_reproduces_checked_in_snapshot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "snapshot.json"
            subprocess.run(
                [sys.executable, str(ROOT / "tools" / "export_settings_registry.py"), str(output)],
                cwd=str(ROOT),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                (ROOT / "generated" / "SETTINGS_REGISTRY_SNAPSHOT.json").read_bytes(),
                output.read_bytes(),
            )

    def test_domain_modules_have_no_runtime_or_io_dependencies(self):
        forbidden_import_roots = {
            "sqlite3", "socket", "threading", "subprocess", "flask", "paho",
            "mqtt_bridge", "controller_logic", "config_manager", "web_ui",
        }
        forbidden_calls = {"open", "remove", "unlink", "replace", "rename"}
        for filename in (
            "settings_registry.py", "settings_codecs.py", "settings_validation.py", "settings_apply_policy.py"
        ):
            tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"), filename=filename)
            imports = set()
            calls = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module.split(".")[0])
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        calls.add(node.func.id)
                    elif isinstance(node.func, ast.Attribute):
                        calls.add(node.func.attr)
            with self.subTest(filename=filename):
                self.assertFalse(imports & forbidden_import_roots, imports & forbidden_import_roots)
                self.assertFalse(calls & forbidden_calls, calls & forbidden_calls)


if __name__ == "__main__":
    unittest.main()
