import tempfile
import unittest
from pathlib import Path

import tools.replay_web as replay_web
from tools.replay_report import charts_html


class V12810ReplayUiTests(unittest.TestCase):
    def _csv(self, path: Path) -> None:
        path.write_text(
            "schema;datetime_local;grid_power_w;zendure_target_power_w;zendure_actual_power_w\n"
            "ZEC-MEASUREMENT-V2;2026-06-08 00:00:00;0;0;0\n",
            encoding="utf-8",
        )

    def test_diagram_term_info_spans_full_bar_row_width(self):
        result = {
            "fair_regulator_quality": {"controllable_percent": 25, "non_controllable_percent": 75},
            "deadband": {},
            "operating_state_matrix": [],
            "command_efficiency": {},
        }
        html = charts_html(result)
        self.assertIn("<span class='barlabel'>beeinflussbar</span>", html)
        self.assertIn("<b class='barvalue'>25 % der gewichteten Abweichung</b><details class='term-info'", html)

    def test_index_disables_start_while_selection_profile_updates(self):
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
                page = response if isinstance(response, str) else response.body.decode("utf-8")
                self.assertIn("let profileUpdating = false", page)
                self.assertIn("Aktualisiere Dateiauswahl…", page)
                self.assertIn("profileRequestSeq", page)
                self.assertIn("Bitte warten: Die Informationen zu den ausgewählten Dateien", page)
            finally:
                replay_web.PROJECT_ROOT = old_project


if __name__ == "__main__":
    unittest.main()
