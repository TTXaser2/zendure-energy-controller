import subprocess
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).parents[1]
class FastFieldAcceptanceContractTests(unittest.TestCase):
    def test_v17_acceptance_identity_and_fast_contract(self):
        text=(ROOT/"tools"/"v17_field_acceptance.py").read_text(encoding="utf-8")
        self.assertIn('EXPECTED_VERSION = "17.0.1"',text); self.assertIn('EXPECTED_BUILD_ID = "v17.0.1-20260922"',text)
        for token in ("fast_capture_field_analyzer","fast_capture_runtime_surface","fast_capture_setting_surface"): self.assertIn(token,text)
        proc=subprocess.run([sys.executable,str(ROOT/"tools"/"fast_capture_field_analysis.py"),"--describe","--json"],capture_output=True,text=True,check=False)
        self.assertEqual(0,proc.returncode); self.assertIn("ZEC_FAST_CAPTURE_FIELD_ANALYSIS_V1",proc.stdout)
    def test_analysis_package_opt_in(self):
        text=(ROOT/"tools"/"create_zec_analysis_package.sh").read_text(encoding="utf-8")
        self.assertIn("--with-fast-capture-report",text); self.assertIn("fast_capture_field_analysis.py",text); self.assertIn("with_fast_capture_report=$WITH_FAST_CAPTURE_REPORT",text)
if __name__=="__main__": unittest.main()
