import re
import tempfile
import time
import unittest
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for item in (ROOT, TOOLS):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from config_manager import DEFAULT_CONFIG
from tests.test_operation_priority import OkShelly, base_cfg, fresh_state, make_controller
from tools.replay_web import selection_profile
from tools.replay_report import charts_html, data_quality_table, recommendations_table
from web_ui import build_status_page


CSV_HEADER = "schema;datetime_local;grid_power_w;soc;zendure_actual_power_w\n"


def write_csv(path: Path, rows):
    path.write_text(CSV_HEADER + "".join(f"ZEC-MEASUREMENT-V3;{ts};0;50;0\n" for ts in rows), encoding="utf-8")


class V12819UiAnalysisTests(unittest.TestCase):
    def _run_full_cycle(self, controller, cfg):
        start = time.time()
        controller.run_once(cfg)
        controller.finish_cycle(cfg, start)

    def test_status_page_shows_current_grid_measurement_in_fixed_night_mode(self):
        cfg = base_cfg(NIGHT_DISCHARGE_ENABLED=True)
        controller, state, mqtt, shelly = make_controller(cfg, state=fresh_state(62), shelly=OkShelly(-6.7))
        controller.is_night_discharge_active = lambda _cfg: True

        self._run_full_cycle(controller, cfg)
        html = build_status_page(cfg, state.snapshot())

        self.assertIn("-6.7 W", html)
        self.assertIn("aktueller Messwert", html)
        self.assertIn("Geglätteter AUTO-Regelwert: n.a.", html)
        self.assertIn("nicht regelrelevant", html)
        self.assertFalse(state.grid_power_used_for_control)
        self.assertTrue(state.grid_power_valid)

    def test_status_page_shows_current_grid_measurement_in_stop_hold(self):
        cfg = base_cfg(MANUAL_MODE="STOP_HOLD")
        state = fresh_state(62)
        with state.lock:
            state.last_output_power = 400
        controller, state, mqtt, shelly = make_controller(cfg, state=state, shelly=OkShelly(123.4))

        self._run_full_cycle(controller, cfg)
        html = build_status_page(cfg, state.snapshot())

        self.assertIn("123.4 W", html)
        self.assertIn("aktueller Messwert", html)
        self.assertIn("Geglätteter AUTO-Regelwert: n.a.", html)
        self.assertFalse(state.grid_power_used_for_control)
        self.assertEqual(state.current_mode, "STOP_HOLD")

    def test_selection_profile_uses_global_min_start_and_max_end_for_multiple_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            newer = tmp_path / "zendure_measurements_1.csv"
            older = tmp_path / "zendure_measurements_2.csv"
            write_csv(newer, ["2026-06-12 02:26:53", "2026-06-12 06:07:37"])
            write_csv(older, ["2026-06-11 22:40:25", "2026-06-12 02:26:50"])
            profile = selection_profile([newer, older], {})
            self.assertEqual(profile["period_start"], "2026-06-11 22:40:25")
            self.assertEqual(profile["period_end"], "2026-06-12 06:07:37")
            self.assertFalse(profile["period_inverted"])

    def test_mqtt_effect_chart_uses_proportional_absolute_widths_and_zero_has_no_fill(self):
        html = charts_html({
            "fair_regulator_quality": {},
            "deadband": {},
            "operating_state_matrix": [
                {"mode": "NIGHT_DISCHARGE", "seconds": 120, "percent": 50},
                {"mode": "HOLD_OUTSIDE_DEADBAND", "seconds": 60, "percent": 25},
                {"mode": "CROSS_CHARGE_BLOCK", "seconds": 60, "percent": 25},
            ],
            "command_efficiency": {
                "improved_count": 37, "improved_percent": 27.4,
                "neutral_count": 75, "no_effect_percent": 55.6,
                "worse_count": 23, "worse_percent": 17.0,
                "unknown_count": 0,
            },
        })
        self.assertIn("Balkenbasis: absolute Anzahl Kommandos", html)
        self.assertIn("Feste Nacht-Basisentladung", html)
        self.assertIn("Das Kommando konnte nicht belastbar bewertet werden", html)
        widths = [float(x) for x in re.findall(r"style='width:([0-9.]+)%'", html)]
        # Last four widths belong to MQTT effect: improved, neutral, worse, unknown.
        improved, neutral, worse, unknown = widths[-4:]
        self.assertGreater(neutral, improved)
        self.assertGreater(improved, worse)
        self.assertEqual(unknown, 0.0)
        self.assertIn("bar zero", html)
        self.assertIn("barbox empty", html)

    def test_data_quality_warning_is_specific_and_quantified(self):
        result = {
            "rows": 1000,
            "duration_seconds": 3600,
            "data_quality": {
                "status": "warning",
                "warnings": ["12 Zeilen ohne Netzleistung."],
                "gap_events": 2,
                "missing_grid_rows": 12,
                "missing_soc_rows": 0,
                "missing_zendure_actual_rows": 5,
                "safe_state_seconds": 180,
            },
            "recommendations": [{"severity": "warning", "topic": "Datenbasis", "text": "Datenbasis eingeschränkt: 2 größere Zeitlücken; 12 Zeilen ohne Netzleistung (1,2 %)."}],
        }
        dq_html = data_quality_table(result)
        rec_html = recommendations_table(result)
        self.assertIn("12 von 1000 Zeilen", dq_html)
        self.assertIn("1,2 %", dq_html)
        self.assertIn("SAFE_STATE", dq_html)
        self.assertIn("Datenbasis eingeschränkt", rec_html)


if __name__ == "__main__":
    unittest.main()
