"""Dual-root tests: preserve V17 assertions, validate actual blocked V18 staging.

These checks must not be used as production release acceptance. Historical V17
assertions remain unmodified on the source root. On V18, the *same* test name
validates the corresponding staged safety contract, without silent exclusions.
"""
from __future__ import annotations

from pathlib import Path
import os
import re
import subprocess
import sys


def is_v18_stage(root: Path) -> bool:
    from tools.verify_release_identity_readiness import python_identity
    identity = python_identity(root)
    if identity.get('APP_VERSION') == '18.0.0':
        assert root.name == 'zendure_controller_v18_0_0_STAGING_NOT_INSTALLABLE', root
        return True
    assert identity.get('APP_VERSION') == '17.1.3', identity
    return False


def assert_stage_runtime(test, root: Path):
    from tools.verify_release_identity_readiness import python_identity
    from version import APP_VERSION, APP_VERSION_LABEL, APP_BUILD_ID
    expected = {'APP_VERSION': '18.0.0', 'APP_VERSION_LABEL': 'V18.0.0',
                'APP_BUILD_ID': 'v18.0.0-20261027'}
    test.assertEqual(expected, python_identity(root))
    test.assertEqual((APP_VERSION, APP_VERSION_LABEL, APP_BUILD_ID),
                     (expected['APP_VERSION'], expected['APP_VERSION_LABEL'], expected['APP_BUILD_ID']))
    test.assertIn('RELEASE_HOLD', (root/'tools/install_zendure_controller.sh').read_text().split('SCRIPT_DIR=',1)[0])


def assert_stage_installer(test, root: Path):
    from tools.verify_release_identity_readiness import shell_installer_identity
    assert_stage_runtime(test, root)
    installer = root/'tools/install_zendure_controller.sh'
    text = installer.read_text(encoding='utf8')
    test.assertEqual('17.1.3', shell_installer_identity(root)['EXPECTED_SOURCE_VERSION'])
    for token in ('EXPECTED_TARGET_VERSION="18.0.0"',
                  'EXPECTED_TARGET_BUILD_ID="v18.0.0-20261027"',
                  'EXPECTED_SOURCE_BUILD_ID="v17.1.3-20261022"',
                  'SOURCE_MANIFEST="V18_0_0_SOURCE_MANIFEST.sha256"',
                  'verify_build_evidence_at "$STAGED_ROOT"',
                  'rollback_update()', 'rollback_fresh()', 'PRODUCTIVE_CHANGES=NONE'):
        test.assertIn(token,text)
    test.assertFalse(installer.stat().st_mode & 0o111)
    test.assertRegex(text.split('SCRIPT_DIR=',1)[0],r'(?m)^exit 78\s*$')
    # The early hold is enforced by bash itself, not only source inspection.
    ret = subprocess.run(['bash',str(installer),'v18_0_0','--preflight-only'],
                         capture_output=True,text=True,timeout=5,cwd=root)
    test.assertEqual(ret.returncode,78,(ret.stdout,ret.stderr))
    test.assertIn('RELEASE_HOLD',ret.stderr)


def assert_stage_drafts(test, root: Path):
    from tools.prepare_v18_staging_tree import _verify_staged_datasheet
    from tools.verify_v18_draft_provenance import check as draft_check
    assert_stage_runtime(test,root)
    test.assertEqual([], _verify_staged_datasheet(root))
    draft = draft_check(root)
    # CP29 draft references PRE-staging V17 version/installer hashes.
    # They are not valid to reassert as current V18 source hashes.
    test.assertEqual('FAIL',draft['gate'])
    test.assertIn('SOURCE_CHANGED:version.py',draft['errors'])
    test.assertIn('SOURCE_CHANGED:tools/install_zendure_controller.sh',draft['errors'])
    test.assertFalse(draft['installable'])
