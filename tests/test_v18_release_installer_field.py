import re, unittest, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class V18FieldInstallSmoke(unittest.TestCase):
 def test_release_identity(self):
  from version import APP_VERSION,APP_BUILD_ID
  self.assertEqual((APP_VERSION,APP_BUILD_ID),('18.0.0','v18.0.0-20261027'))
 def test_standard_installer_not_release_hold(self):
  script=(ROOT/'tools/install_zendure_controller.sh').read_text()
  before=script.split('SCRIPT_DIR=',1)[0]
  self.assertNotRegex(before,r'(?m)^exit 78\s*$')
  self.assertIn('verify_build_evidence_at "$STAGED_ROOT"',script)
  self.assertIn('verify_manifest_at "$STAGED_ROOT"',script)
  self.assertIn('rollback_update()',script)
  self.assertIn('rollback_fresh()',script)
 def test_installer_syntax(self):
  ret=subprocess.run(['bash','-n',str(ROOT/'tools/install_zendure_controller.sh')],capture_output=True)
  self.assertEqual(ret.returncode,0,ret.stderr)
 def test_help_without_mutation(self):
  inst=ROOT/'tools/install_zendure_controller.sh'
  ret=subprocess.run(['bash',str(inst),'v18_0_0','--help'],capture_output=True,text=True,timeout=5)
  self.assertEqual(ret.returncode,0,(ret.stdout,ret.stderr))
  self.assertIn('--preflight-only',ret.stdout)
 def test_datasheet_and_source_protection(self):
  from tools.validate_release_datasheet import validate
  self.assertEqual(validate(ROOT)['status'],'PASS')
