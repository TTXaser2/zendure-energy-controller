import os
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


class TestRC13SupportTools(unittest.TestCase):
    def test_version_label_rc13(self):
        import version
        self.assertEqual(version.APP_VERSION_LABEL, "V12.11.6")

    def test_support_tools_exist_and_are_shell_syntax_valid(self):
        for name in [
            "collect_zec_trace.sh",
            "run_zec_analysis_package_interactive.sh",
            "create_desktop_shortcuts.sh",
            "collect_zec_crash_package.sh",
        ]:
            path = TOOLS / name
            self.assertTrue(path.exists(), name)
            self.assertTrue(os.access(path, os.X_OK), name)
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("#!/usr/bin/env bash"), name)
            subprocess.run(["bash", "-n", str(path)], check=True)

    def test_trace_tool_uses_correct_runtime_log_path_and_redaction(self):
        text = (TOOLS / "collect_zec_trace.sh").read_text(encoding="utf-8")
        self.assertIn('/opt/zendure-controller/logs', text)
        self.assertIn('zendure_runtime.log', text)
        self.assertIn('zec_trace_latest.txt', text)
        self.assertIn('serial', text.lower())
        self.assertIn('<redacted>', text)

    def test_desktop_shortcuts_reference_packaged_tools(self):
        text = (TOOLS / "create_desktop_shortcuts.sh").read_text(encoding="utf-8")
        self.assertIn("ZEC_Trace_sammeln.desktop", text)
        self.assertIn("ZEC_Diagnosepaket_erstellen.desktop", text)
        self.assertIn("collect_zec_trace.sh --pause", text)
        self.assertIn("run_zec_analysis_package_interactive.sh", text)
        self.assertIn("ZEC_Crashpaket_erstellen.desktop", text)
        self.assertIn("collect_zec_crash_package.sh --pause", text)

    def test_update_script_marks_shell_tools_executable(self):
        text = (TOOLS / "update_zendure_controller.sh").read_text(encoding="utf-8")
        self.assertIn('find "$TARGET" -type f -name "*.sh" -exec chmod 750 {} \\;', text)


if __name__ == "__main__":
    unittest.main()
