import ast
import json
import os
import tempfile
import unittest
from pathlib import Path

from config_manager import ConfigManager, DEFAULT_CONFIG
from state import ControllerState
from web_ui import build_health_payload, build_ready_payload, create_app

ROOT = Path(__file__).resolve().parents[1]


def endpoint(app, path, method="GET"):
    method = method.upper()
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return route.endpoint
    raise AssertionError(f"Route {method} {path} missing")


class Rc20Fix5RuntimeReadinessTests(unittest.TestCase):
    def test_pristine_controller_state_readiness_snapshot_is_total(self):
        state = ControllerState()
        snapshot = state.readiness_snapshot()
        self.assertIs(snapshot["second_battery_valid"], False)
        self.assertEqual("SECOND_BATTERY_MISSING", snapshot["second_battery_validity_reason"])
        self.assertTrue(build_health_payload(snapshot)["alive"])
        ready = build_ready_payload(DEFAULT_CONFIG, snapshot)
        self.assertIsInstance(ready, dict)
        self.assertFalse(ready["ready"])
        self.assertIsInstance(ready["failed_checks"], list)

    def test_ready_and_health_routes_accept_pristine_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            cfg = dict(DEFAULT_CONFIG)
            cfg.update({
                "DEVICE_ID": "TESTDEVICE",
                "HEADLESS_MODE": False,
                "OPERATIONAL_EVENTS_DB_PATH": str(Path(tmp) / "events.sqlite3"),
            })
            path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
            os.chmod(path, 0o600)
            manager = ConfigManager(str(path))
            manager.load()
            app = create_app(manager, ControllerState())
            health = endpoint(app, "/health")()
            ready = endpoint(app, "/ready")()
            self.assertTrue(health["alive"])
            self.assertEqual("13.0.0", health["version"])
            self.assertIsInstance(ready, dict)
            self.assertFalse(ready["ready"])
            self.assertIn("settings_runtime", ready)

    def test_every_controller_state_self_read_is_declared(self):
        tree = ast.parse((ROOT / "state.py").read_text(encoding="utf-8"))
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "ControllerState")
        fields = {
            node.target.id
            for node in cls.body
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
        }
        methods = {
            node.name
            for node in cls.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        reads = {
            node.attr
            for node in ast.walk(cls)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "self"
            and isinstance(node.ctx, ast.Load)
        }
        self.assertEqual(set(), reads - fields - methods)

    def test_installer_runs_runtime_smoke_before_and_after_copy(self):
        script = (ROOT / "tools/update_zendure_controller.sh").read_text(encoding="utf-8")
        self.assertIn("verify_runtime_readiness_smoke", script)
        self.assertIn('verify_runtime_readiness_smoke "$DIR"', script)
        self.assertIn('verify_runtime_readiness_smoke "$TARGET"', script)
        self.assertGreaterEqual(script.count('PYTHONWARNINGS="error::ResourceWarning"'), 2)


if __name__ == "__main__":
    unittest.main()
