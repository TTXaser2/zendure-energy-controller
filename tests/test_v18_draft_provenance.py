# SPDX-License-Identifier: AGPL-3.0-or-later
"""CP29 negative and positive tests: draft gate != release gate."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.verify_v18_draft_provenance import DOCS, REQUIRED_SOURCES, TRACE, check

ROOT = Path(__file__).resolve().parents[1]


class V18DraftProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in (*DOCS, TRACE, *REQUIRED_SOURCES):
            src = ROOT / name
            dest = self.root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)

    def test_intact_draft_passes_without_becoming_installable(self):
        from tests.v18_staging_test_contract import is_v18_stage, assert_stage_drafts
        if is_v18_stage(Path(__file__).resolve().parents[1]):
            assert_stage_drafts(self, Path(__file__).resolve().parents[1])
            return
        result = check(self.root)
        self.assertEqual(result['gate'], 'PASS', result['errors'])
        self.assertIs(result['installable'], False)
        self.assertEqual(result['files_checked'], 15)

    def test_actual_worktree_still_pending_release_identity(self):
        from tests.v18_staging_test_contract import is_v18_stage, assert_stage_drafts
        if is_v18_stage(Path(__file__).resolve().parents[1]):
            assert_stage_drafts(self, Path(__file__).resolve().parents[1])
            return
        result = check(ROOT)
        self.assertEqual(result['gate'], 'PASS', result['errors'])
        self.assertFalse(result['installable'])

    def test_tampering_controller_invalidates_source_hash(self):
        with (self.root / 'controller_logic.py').open('ab') as handle:
            handle.write(b'\n# unauthorized change\n')
        self.assertIn('SOURCE_CHANGED:controller_logic.py', check(self.root)['errors'])

    def test_tampering_runtime_is_detected(self):
        path = self.root / 'version.py'
        path.write_text(path.read_text().replace('17.1.3', '18.0.0'), encoding='utf-8')
        result = check(self.root)
        self.assertIn('CURRENT_RUNTIME_RELEASE_HOLD_MISSING', result['errors'])

    def test_removed_install_hold_is_detected(self):
        path = self.root / 'tools/install_zendure_controller_v18_candidate.sh'
        path.write_text(path.read_text().replace('exit 78', 'exit 0', 1), encoding='utf-8')
        self.assertIn('V18_INSTALLER_HARD_HOLD_MISSING', check(self.root)['errors'])

    def test_document_missing_warning_cannot_pass(self):
        path = self.root / DOCS[0]
        path.write_text(path.read_text().replace('PHYSICAL_EFFECT_NOT_VERIFIED', 'COMPLETE'), encoding='utf-8')
        self.assertTrue(any(s.startswith('DRAFT_WARNING_MISSING:') for s in check(self.root)['errors']))

    def test_absent_original_document_cannot_pass(self):
        (self.root / DOCS[-1]).unlink()
        self.assertTrue(any(s.startswith('DRAFT_MISSING:') for s in check(self.root)['errors']))

    def test_forged_final_manifest_is_not_accepted_as_draft(self):
        (self.root / 'V18_0_0_SOURCE_MANIFEST.sha256').write_text('not verified', encoding='utf-8')
        self.assertIn('FINAL_BUILD_EVIDENCE_UNEXPECTED_IN_DRAFT', check(self.root)['errors'])

    def test_changed_traceability_release_hold_cannot_pass(self):
        path = self.root / TRACE
        data = json.loads(path.read_text())
        data['manual_uml_review'] = 'PASS'
        path.write_text(json.dumps(data))
        self.assertIn('DRAFT_HOLDS_MISSING', check(self.root)['errors'])


if __name__ == '__main__':
    unittest.main()
