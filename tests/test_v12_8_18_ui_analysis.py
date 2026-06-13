import tempfile
import unittest
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for item in (ROOT, TOOLS):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from tools.replay_web import selection_profile
from tools.replay_report import charts_html, data_quality_table, recommendations_table


CSV_HEADER = "schema;datetime_local;grid_power_w;soc;zendure_actual_power_w\n"


def write_csv(path: Path, rows):
    path.write_text(CSV_HEADER + "".join(f"ZEC-MEASUREMENT-V2;{ts};0;50;0\n" for ts in rows), encoding="utf-8")


class V12818UiAnalysisTests(unittest.TestCase):
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

    def test_mqtt_effect_chart_uses_absolute_bar_basis_and_all_category_infos(self):
        html = charts_html({
            "fair_regulator_quality": {},
            "deadband": {},
            "operating_state_matrix": [
                {"mode": "NIGHT_DISCHARGE", "seconds": 120, "percent": 50},
                {"mode": "HOLD_OUTSIDE_DEADBAND", "seconds": 60, "percent": 25},
                {"mode": "CROSS_CHARGE_BLOCK", "seconds": 60, "percent": 25},
            ],
            "command_efficiency": {
                "improved_count": 367, "improved_percent": 22.8,
                "neutral_count": 808, "no_effect_percent": 50.3,
                "worse_count": 432, "worse_percent": 26.9,
                "unknown_count": 30,
            },
        })
        self.assertIn("Balkenbasis: absolute Anzahl Kommandos", html)
        self.assertIn("NIGHT_DISCHARGE", html)
        self.assertIn("HOLD_OUTSIDE_DEADBAND", html)
        self.assertIn("CROSS_CHARGE_BLOCK", html)
        self.assertIn("Feste Nacht-Basisentladung", html)
        self.assertIn("Das Kommando konnte nicht belastbar bewertet werden", html)

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
