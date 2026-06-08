import json
import tempfile
import unittest
from pathlib import Path

from fastapi.responses import JSONResponse

import tools.replay_web as replay_web
from tools.replay_report import charts_html, tracking_table


class V1289ReplayUiTests(unittest.TestCase):
    def _csv(self, path: Path, rows: int = 2) -> None:
        lines = ["schema;datetime_local;grid_power_w;zendure_target_power_w;zendure_actual_power_w"]
        for i in range(rows):
            lines.append(f"ZEC-MEASUREMENT-V2;2026-06-08 00:00:{i:02d};0;0;0")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_selection_profile_limits_are_json_serializable(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            paths = []
            for idx in range(5):
                p = base / f"zendure_measurements_{idx}.csv"
                self._csv(p)
                paths.append(p)
            profile = replay_web.selection_profile(paths, {})
            payload = {"requires_confirmation": True, "profile": profile}
            # This was the V12.8.8 failure path: JSONResponse calls json.dumps directly.
            response = JSONResponse(payload, status_code=409)
            decoded = json.loads(response.body.decode("utf-8"))
            self.assertIn("safe_limits", decoded["profile"])
            self.assertIsInstance(decoded["profile"]["safe_limits"], dict)
            self.assertEqual(decoded["profile"]["extended_limits"]["max_files"], 5)

    def test_index_contains_no_release_notice_but_profile_explanation_and_top_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            logdir = base / "logs"
            logdir.mkdir()
            self._csv(logdir / "zendure_measurements.csv")
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
                self.assertIn('id="top"', html)
                self.assertIn("Informationen zu den ausgewählten Dateien", html)
                self.assertNotIn("korrigiert die JavaScript-Initialisierung", html)
                self.assertIn("Analyse wurde abgebrochen. Bereit", html)
            finally:
                replay_web.PROJECT_ROOT = old_project

    def test_report_labels_and_charts_are_interpretable(self):
        result = {
            "tracking": {"rating": "green", "avg_error_w": 12, "p95_error_w": 34},
            "fair_regulator_quality": {"controllable_percent": 25, "non_controllable_percent": 75},
            "deadband": {
                "inside_deadband_seconds": 3600,
                "inside_deadband_percent": 50,
                "inside_extended_band_seconds": 5400,
                "inside_extended_band_percent": 75,
                "outside_deadband_with_reserve_seconds": 600,
                "outside_deadband_with_reserve_percent": 8,
            },
            "operating_state_matrix": [{"mode": "SAFE_STATE", "seconds": 7200, "percent": 80}],
            "command_efficiency": {"improved_count": 1, "neutral_count": 2, "worse_count": 0, "unknown_count": 3, "improved_percent": 33, "no_effect_percent": 67},
        }
        self.assertIn("95%-Perzentil Soll/Ist-Abweichung", tracking_table(result))
        html = charts_html(result)
        self.assertIn("gewichteten Abweichung", html)
        self.assertIn("h 00 min", html)
        self.assertIn("Bewertbare Basis", html)

    def test_systemd_start_limit_is_in_unit_section(self):
        service = (Path(__file__).resolve().parents[1] / "systemd" / "zendure-replay.service").read_text(encoding="utf-8")
        unit = service.split("[Service]", 1)[0]
        service_section = service.split("[Service]", 1)[1].split("[Install]", 1)[0]
        self.assertIn("StartLimitIntervalSec=300", unit)
        self.assertNotIn("StartLimitIntervalSec", service_section)


if __name__ == "__main__":
    unittest.main()
