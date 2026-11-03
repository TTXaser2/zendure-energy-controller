"""Version-aware fail-closed technical smoke for V18.0.1 noninstallable staging.

This does not replace fresh-extract release/installer or real Pi field validation.
"""
import json
import subprocess
import unittest
from pathlib import Path
from version import APP_VERSION, APP_VERSION_LABEL, APP_BUILD_ID
from tools.verify_release_identity_readiness import shell_installer_identity
from tools.validate_release_datasheet import validate
from tools.verify_uml_release import check as uml_check

ROOT = Path(__file__).resolve().parents[1]

class V1801ReleaseHoldSmoke(unittest.TestCase):
    def test_target_identity_and_source_update_contract(self):
        self.assertEqual((APP_VERSION, APP_VERSION_LABEL, APP_BUILD_ID),
                         ('18.0.1', 'V18.0.1', 'v18.0.1-20261102'))
        vals=shell_installer_identity(ROOT)
        for key,value in dict(EXPECTED_VERSION_ARG='v18_0_1',
             EXPECTED_SOURCE_VERSION='18.0.0', EXPECTED_SOURCE_BUILD_ID='v18.0.0-20261027',
             EXPECTED_TARGET_VERSION='18.0.1', EXPECTED_TARGET_BUILD_ID='v18.0.1-20261102',
             SOURCE_MANIFEST='V18_0_1_SOURCE_MANIFEST.sha256').items():
            self.assertEqual(vals[key],value,key)

    def test_v18_0_1_field_acceptance_identity_and_source_report(self):
        from tools import v18_field_acceptance as field
        self.assertEqual((field.EXPECTED_VERSION, field.EXPECTED_LABEL, field.EXPECTED_BUILD_ID),
                         ('18.0.1', 'V18.0.1', 'v18.0.1-20261102'))
        self.assertEqual(field._expected_update_source(),
                         {'version':'18.0.0', 'build_id':'v18.0.0-20261027'})
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            prior=p/'zec_v18_0_0_install_report_older.json'
            current=p/'zec_v18_0_1_install_report_current.json'
            prior.write_text('{}');current.write_text('{}')
            resolved,kind=field._resolve_install_report(persistent_dir=p)
            self.assertEqual((resolved,kind),(current,'persistent_latest'))

    def test_field_acceptance_never_inherits_old_development_hold(self):
        import ast
        from tools import v18_field_acceptance as field
        tree=ast.parse((ROOT/'tools/v18_field_acceptance.py').read_text())
        for name in ('run_acceptance', 'run_first_install_acceptance'):
            fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==name)
            calls=[x for x in ast.walk(fn) if isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id=='_check']
            self.assertFalse(any(len(x.args)>=2 and isinstance(x.args[1],ast.Constant)
                      and x.args[1].value=='v18_release_candidate_hold' for x in calls),name)
        self.assertEqual(field.FORMAT,'ZEC_V18_0_1_FIELD_ACCEPTANCE_V1')

    def test_battery_care_effect_requires_evidence_but_is_not_general_install_fail(self):
        import ast
        tree=ast.parse((ROOT/'tools/v18_field_acceptance.py').read_text())
        fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='run_acceptance')
        physical=[]
        for call in ast.walk(fn):
            if isinstance(call,ast.Call) and isinstance(call.func,ast.Name) and call.func.id in ('_check','_warn'):
                if len(call.args)>1 and isinstance(call.args[1],ast.Constant) and call.args[1].value=='battery_care_physical_effect':
                    physical.append(call.func.id)
        self.assertEqual(physical,['_warn'])

    def test_fast_capture_analyzer_supports_current_release_and_prior_versions(self):
        from tools import fast_capture_field_analysis as analyzer
        contract=analyzer.describe_contract()
        supported=set(contract['supported_controller_versions'])
        self.assertTrue({'17.1.3','18.0.0','18.0.1'}.issubset(supported))
        self.assertEqual(contract['expected_controller_version'],'17.1.3')
        self.assertIn('EXPECTED_VERSION in (payload.get("supported_controller_versions") or [])',
                      (ROOT/'tools/v18_field_acceptance.py').read_text())

    def test_installer_hold_or_released_state_consistent_with_build_evidence(self):
        """A released installer must never coexist with BLOCKED build evidence."""
        script=ROOT/'tools/install_zendure_controller.sh'
        head=script.read_text().split('SCRIPT_DIR=',1)[0]
        evidence=json.loads((ROOT/'validation/V18_0_1_BUILD_EVIDENCE.json').read_text())
        if evidence.get('status') == 'BLOCKED':
            self.assertIn('RELEASE_HOLD',head)
            self.assertIn('exit 78',head)
            for args in (['v18_0_1','--preflight-only'], ['v18_0_1','--help'], ['v18_0_1','--fresh-install']):
                q=subprocess.run(['bash',str(script),*args],capture_output=True,text=True,timeout=3)
                self.assertEqual(q.returncode,78,q.stderr)
        elif evidence.get('status') == 'PASS':
            self.assertNotIn('exit 78',head)
            self.assertNotIn('RELEASE_HOLD',head)
            q=subprocess.run(['bash',str(script),'v18_0_1','--help'],capture_output=True,text=True,timeout=3)
            self.assertEqual(q.returncode,0,q.stderr)
            self.assertIn('preflight-only',q.stdout)
        else:
            self.fail('INVALID_BUILD_EVIDENCE_STATUS')

    def test_syntax_recovery_and_backup_contract_present(self):
        script=ROOT/'tools/install_zendure_controller.sh'
        proc=subprocess.run(['bash','-n',str(script)],capture_output=True,text=True)
        self.assertEqual(proc.returncode,0,proc.stderr)
        body=script.read_text()
        for token in ('verify_build_evidence_at "$STAGED_ROOT"', 'verify_manifest_at "$STAGED_ROOT"',
                      'rollback_update()', 'rollback_fresh()', 'zec_backup_root_artifacts',
                      "--exclude 'config.json'", "--exclude 'logs/'",'SUPPORTED_UPDATE','CLEAN_FRESH_INSTALL'):
            self.assertIn(token,body,token)

    def test_datasheet_versioned_assets_integrity(self):
        self.assertEqual(validate(ROOT)['status'],'PASS')

    def test_uml_technical_and_source_review_complete(self):
        tech=uml_check(ROOT,require_manual=False,verify_dot=False)
        self.assertEqual(tech['technical_gate'],'PASS',tech['errors'])
        self.assertEqual(tech['diagrams'],22)
        self.assertEqual(tech['manual_gate'],'PASS')
        self.assertTrue((ROOT/'docs/architecture/uml/SOURCE_REVIEW_V18_0_1_20261102.md').is_file())
        review=(ROOT/'docs/architecture/uml/SOURCE_REVIEW_V18_0_1_20261102.md').read_text()
        for n in range(1,23):
            self.assertIn(f'| {n:02} |',review)

    def test_release_manifest_excludes_generated_runtime_databases(self):
        manifest = (ROOT/'V18_0_1_SOURCE_MANIFEST.sha256').read_text().splitlines()
        prohibited=[]
        for line in manifest:
            rel=line.split('  ',1)[-1].removeprefix('./').replace('\\','/')
            if rel.endswith(('.sqlite','.sqlite3','.db','.db-wal','.db-shm')):
                prohibited.append(rel)
        self.assertEqual(prohibited,[],f'Runtime DB must not be released: {prohibited}')

    def test_build_evidence_is_true_to_release_state(self):
        doc=json.loads((ROOT/'validation/V18_0_1_BUILD_EVIDENCE.json').read_text())
        if doc.get('status') == 'BLOCKED':
            self.assertEqual(doc['full_regression']['status'],'NOT_RUN_ON_FINAL_TREE')
        elif doc.get('status') == 'PASS':
            from tools.deployment_contract import verify_build_evidence
            check=verify_build_evidence(root=ROOT,evidence_name='validation/V18_0_1_BUILD_EVIDENCE.json',
                expected_version='18.0.1',expected_label='V18.0.1',expected_build='v18.0.1-20261102')
            self.assertTrue(check['ok'],check['errors'])
        else:
            self.fail('BUILD_EVIDENCE_STATUS_UNKNOWN')

if __name__=='__main__':unittest.main()
