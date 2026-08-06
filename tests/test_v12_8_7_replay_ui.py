import tempfile
import unittest
from pathlib import Path

import tools.replay_web as replay_web


class V1287ReplayUiTests(unittest.TestCase):
    def test_selection_profile_endpoint_is_registered(self):
        app = replay_web.build_app()
        paths = {route.path for route in app.routes}
        self.assertIn("/selection-profile", paths)

    def test_index_contains_dynamic_profile_and_visible_status_elements(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            logdir = base / "logs"
            logdir.mkdir()
            csv_path = logdir / "zendure_measurements.csv"
            csv_path.write_text(
                "schema;datetime_local;grid_power_w;zendure_target_power_w;zendure_actual_power_w\n"
                "ZEC-MEASUREMENT-V3;2026-06-08 00:00:00;0;0;0\n",
                encoding="utf-8",
            )
            old_project = replay_web.PROJECT_ROOT
            try:
                replay_web.PROJECT_ROOT = base
                app = replay_web.build_app()
                index_route = next(route for route in app.routes if route.path == "/" and "GET" in route.methods)
                class DummyUrl:
                    scheme = "http"
                    hostname = "127.0.0.1"
                class DummyRequest:
                    url = DummyUrl()
                response = index_route.endpoint(DummyRequest(), files=None, file="")
                html = response if isinstance(response, str) else response.body.decode("utf-8")
                self.assertIn('id="filesSelect"', html)
                self.assertIn('id="profileBox"', html)
                self.assertIn('id="statusText"', html)
                self.assertIn('/selection-profile?', html)
                self.assertIn('addEventListener', html)
            finally:
                replay_web.PROJECT_ROOT = old_project

    def test_replay_confirmation_uses_server_gate_and_explicit_second_request(self):
        source = Path(__file__).resolve().parents[1] / "tools" / "replay_web.py"
        text = source.read_text(encoding="utf-8")

        # Current contract: the server rejects an extended analysis until the
        # browser sends a second, explicit request carrying extended_confirm=1.
        self.assertIn("if(js.requires_confirmation)", text)
        self.assertIn("startAnalysis(true)", text)
        self.assertIn("data.append('extended_confirm','1')", text)
        self.assertIn('if profile["needs_confirmation"] and not extended_confirm:', text)
        self.assertIn('status_code=409', text)

        # The obsolete browser confirm-string contract must not return.
        self.assertNotIn("\\n\\nWeiter?", text)


if __name__ == "__main__":
    unittest.main()
