import os
import subprocess
import unittest
from pathlib import Path

import web_ui
import version

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


class TestRC14UiPolish(unittest.TestCase):
    def test_version_label_rc14(self):
        self.assertEqual(version.APP_VERSION_LABEL, "V12.11.2-RC3")

    def test_status_page_uses_neutral_night_context_and_svg_icons(self):
        cfg = {"UI_DARK_MODE":False, "NIGHT_DISCHARGE_ENABLED":True, "NIGHT_START_HOUR":21, "NIGHT_START_MINUTE":30, "NIGHT_END_HOUR":5, "NIGHT_END_MINUTE":30, "NIGHT_DISCHARGE_POWER_W":400}
        snap = {"current_mode":"SAFE_STATE", "raw_grid_power":-2160, "grid_power_valid":True, "battery_soc":100, "zendure_mqtt_overall_status":"ZENDURE_MQTT_OK", "measurement_log_status":"active"}
        html = web_ui.build_status_page(cfg, snap)
        self.assertIn('class="zec-icon"', html)
        self.assertIn('data-zec="mode.projection"', html)
        self.assertIn('SAFE_STATE', html)
        self.assertNotIn('Nachtmodus-Prognose', html)

    def test_mini_sparkline_has_axes_scale_and_no_fake_curve(self):
        html = web_ui._mini_svg_sparkline([-1500, -1000, -500, 0, 250])
        self.assertIn("mini-axis", html)
        self.assertIn("mini-grid", html)
        self.assertIn("mini-zero", html)
        self.assertIn("letzte 48 Punkte", html)
        self.assertIn("aktuell", html)
        self.assertIn("kW", html)
        fallback = web_ui._mini_svg_sparkline([])
        self.assertIn("keine Verlaufshistorie verfügbar", fallback)

    def test_crash_tool_exists_and_desktop_shortcut_references_it(self):
        crash_tool = TOOLS / "collect_zec_crash_package.sh"
        self.assertTrue(crash_tool.exists())
        self.assertTrue(os.access(crash_tool, os.X_OK))
        subprocess.run(["bash", "-n", str(crash_tool)], check=True)
        tool_text = crash_tool.read_text(encoding="utf-8")
        self.assertIn("journalctl -k", tool_text)
        self.assertIn("mmc|blk|sda|usb", tool_text)
        shortcut_text = (TOOLS / "create_desktop_shortcuts.sh").read_text(encoding="utf-8")
        self.assertIn("ZEC_Crashpaket_erstellen.desktop", shortcut_text)
        self.assertIn("collect_zec_crash_package.sh --pause", shortcut_text)


if __name__ == "__main__":
    unittest.main()
