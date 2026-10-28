"""CP41: nonmutating installer/rollback contract audit; no host path is exercised."""
from __future__ import annotations

from pathlib import Path
from tools.verify_release_identity_readiness import python_identity
import shutil
import tempfile
import unittest

from tools.verify_v18_installer_recovery_readonly import check

ROOT = Path(__file__).resolve().parents[1]


def _fixture(dst: Path, *, staged: bool | None = None) -> Path:
    # Preserve the actual root's identity: V17 fixtures retain the V17 installer;
    # V18 fixtures retain the hard-held V18 standard installer.
    if staged is None:
        staged = python_identity(ROOT)['APP_VERSION'] == '18.0.0'
    tools = dst/'tools'
    tools.mkdir()
    for src in ('install_zendure_controller.sh',
                'install_zendure_controller_v18_candidate.sh',
                'root_artifact_transaction.sh'):
        shutil.copy2(ROOT/'tools'/src, tools/src)
    shutil.copy2(ROOT/'version.py',dst/'version.py')
    if staged:
        shutil.copy2(tools/'install_zendure_controller_v18_candidate.sh',
                     tools/'install_zendure_controller.sh')
        (tools/'install_zendure_controller.sh').chmod(0o644)
        (dst/'version.py').write_text("APP_VERSION = '18.0.0'\n")
    else:
        (dst/'version.py').write_text("APP_VERSION = '17.1.3'\n")
    return dst


class TestV18InstallerRecoveryReadonly(unittest.TestCase):
    def test_current_development_or_staging_sources_pass_structural_not_release_gate(self):
        p=check(ROOT)
        self.assertEqual([],p['errors'],p)
        self.assertEqual('PASS',p['gate'])
        self.assertTrue(p['early_hold_execution_tested'])
        for field in ('installer_executed_past_hold','host_mutation_performed',
                      'rollback_executed','archive_restore_integrity_tested',
                      'real_pi_tested','release_approved'):
            self.assertFalse(p[field],field)

    def test_fixture_inherits_actual_test_root_identity_without_downgrade(self):
        with tempfile.TemporaryDirectory() as td:
            root=_fixture(Path(td))
            expected=python_identity(ROOT)['APP_VERSION']
            self.assertEqual(expected, python_identity(root)['APP_VERSION'])
            self.assertEqual('PASS', check(root,execute_hold=False)['gate'])

    def test_staged_standard_installer_is_also_non_executable_and_exit78(self):
        with tempfile.TemporaryDirectory() as td:
            root=_fixture(Path(td),staged=True)
            p=check(root)
            self.assertEqual('PASS',p['gate'],p)
            self.assertTrue(p['early_hold_execution_tested'])

    def _tamper(self, needle: str, replacement: str, expected: str, *, file='install_zendure_controller_v18_candidate.sh'):
        with tempfile.TemporaryDirectory() as td:
            root=_fixture(Path(td))
            path=root/'tools'/file
            text=path.read_text()
            self.assertIn(needle,text)
            path.write_text(text.replace(needle,replacement,1))
            result=check(root,execute_hold=False)
            self.assertEqual('FAIL',result['gate'],result)
            self.assertTrue(any(expected in e for e in result['errors']),result)
            self.assertFalse(result['rollback_executed'])

    def test_rejects_added_mutation_before_release_hold(self):
        self._tamper('exit 78\n','touch /tmp/zec_insecure_marker\nexit 78\n',
                     'IMMEDIATE_NONOVERRIDABLE_HOLD_INVALID')

    def test_rejects_removed_predeploy_build_proof(self):
        self._tamper('verify_build_evidence_at "$STAGED_ROOT"',
                     'echo "fake evidence"',
                     'PACKAGE_PREDEPLOY_VERIFICATION_INCOMPLETE')

    def test_rejects_preflight_invocation_order_swap(self):
        self._tamper('package_preflight\nsystem_dependency_preflight\nclassify_mode\nmode_specific_preflight\n',
                     'classify_mode\nsystem_dependency_preflight\npackage_preflight\nmode_specific_preflight\n',
                     'PREFLIGHT_ENTRYPOINT_ORDER_INVALID')

    def test_rejects_update_missing_measurement_retention_exclusion(self):
        self._tamper("--exclude 'logs/'", "--exclude 'unimportant/'",
                     'USER_DATA_PRESERVATION_EXCLUDE_MISSING')

    def test_rejects_update_missing_full_backup(self):
        self._tamper('sudo tar -czf "$BACKUP" zendure-controller',
                     'sudo true', 'PREFLIGHT_BACKUP_DEPLOY_ORDER_INVALID')

    def test_rejects_missing_restore_of_privileged_services(self):
        self._tamper('zec_restore_root_artifacts "$ROOT_ARTIFACT_BACKUP" "${ROOT_ARTIFACTS[@]}" || true',
                     'echo no-restore', 'UPDATE_ROLLBACK_RESTORE_CONTRACT_MISSING')

    def test_rejects_diagnostics_after_rollback_removed(self):
        self._tamper('start_support_capture "pre_rollback" "RC_${code}_LINE_${line}"',
                     'echo no-diagnostics', 'SINGLE_OWNER_FAILURE_DIAGNOSTIC_OR_ROLLBACK_MISSING')

    def test_rejects_missing_clean_fresh_guard(self):
        self._tamper('if [ "$INSTALL_MODE" = "CLEAN_FRESH_INSTALL" ] && [ "$FRESH_ASSERT" -ne 1 ]; then',
                     'if false; then', 'MODE_CLASSIFICATION_FAIL_CLOSED_CONTRACT_MISSING')

    def test_rejects_unsupported_source_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root=_fixture(Path(td))
            (root/'version.py').write_text("APP_VERSION = '99.0.0'\n")
            p=check(root,execute_hold=False)
            self.assertEqual('FAIL',p['gate'])
            self.assertIn('UNSUPPORTED_ROOT_IDENTITY',p['errors'])

    def test_rejects_symlinked_script_before_executing_hold(self):
        with tempfile.TemporaryDirectory() as td:
            root=_fixture(Path(td))
            p=root/'tools/install_zendure_controller_v18_candidate.sh'
            other=root/'safe-script'
            shutil.copy2(p,other)
            p.unlink()
            p.symlink_to(other)
            report=check(root)
            self.assertEqual('FAIL',report['gate'])
            self.assertFalse(report['early_hold_execution_tested'])

if __name__ == '__main__':
    unittest.main()
