#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only CP29 source-to-document traceability audit; never an install gate.

PASS only means that the *development drafts* are backed by unchanged bytes
and all product/release holds remain in force.  A release-ready tree must
replace these documents and re-run the real release gates, not reuse this PASS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

TRACE = 'docs/releases/v18.0.0/CP29_SOURCE_TRACEABILITY_20261027.json'
DOCS = (
    'docs/architecture/ZEC_V18_0_0_As_Built.md',
    'docs/releases/v18.0.0/RELEASE_INFO_V18_0_0.md',
    'docs/releases/v18.0.0/TECHNICAL_NOTES_V18_0_0.md',
    'docs/releases/v18.0.0/BUILD_VALIDATION_V18_0_0.md',
    'docs/releases/v18.0.0/DATASHEET_V18_0_0_SOURCE_MATRIX_DRAFT.md',
    'README_INSTALLATION_V18_0_0.md',
)
REQUIRED_SOURCES = frozenset((
    'controller_logic.py', 'battery_care_policy.py', 'battery_care_pv_allocation.py',
    'battery_care_grid_observation.py', 'battery_care_episode_store.py',
    'battery_care_graph_history.py', 'battery_care_stage_events.py',
    'operational_events.py', 'status_page_v2.py', 'web_ui.py',
    'static/status_v2.js', 'version.py',
    'tools/install_zendure_controller.sh',
    'tools/install_zendure_controller_v18_candidate.sh',
    'tools/v18_field_acceptance.py',
))
HOLD = ('DEVELOPMENT_NOT_INSTALLABLE', 'MANUAL_UML_REVIEW_PENDING',
        'PHYSICAL_EFFECT_NOT_VERIFIED')


def check(root: Path) -> dict:
    root = root.resolve()
    errors: list[str] = []
    try:
        data = json.loads((root / TRACE).read_text(encoding='utf-8'))
    except (OSError, ValueError, UnicodeError):
        return {'gate': 'FAIL', 'installable': False, 'errors': ['TRACEABILITY_UNREADABLE']}
    if not isinstance(data, dict) or data.get('schema') != 'ZEC_V18_DRAFT_SOURCE_TRACEABILITY_V1':
        errors.append('SCHEMA_INVALID')
    if (data.get('document_status') != 'DEVELOPMENT_NOT_INSTALLABLE' or
            data.get('candidate_build_status') != 'PROVISIONAL_NOT_FROZEN' or
            data.get('manual_uml_review') != 'PENDING' or
            data.get('controller_effect') != 'UNVERIFIED_REAL_HARDWARE'):
        errors.append('DRAFT_HOLDS_MISSING')
    if (data.get('productive_version'), data.get('productive_build'), data.get('candidate_version')) != (
            '17.1.3', 'v17.1.3-20261022', '18.0.0'):
        errors.append('VERSION_PROVENANCE_MISMATCH')
    files = data.get('files')
    if not isinstance(files, dict) or set(files) != REQUIRED_SOURCES:
        errors.append('SOURCE_SET_MISMATCH')
        files = files if isinstance(files, dict) else {}
    for name in sorted(REQUIRED_SOURCES):
        entry = files.get(name)
        if (not isinstance(entry, dict) or
                not re.fullmatch(r'[0-9a-f]{64}', str(entry.get('sha256', '')))
                or not isinstance(entry.get('scope'), str) or not entry['scope'].strip()):
            errors.append('SOURCE_EVIDENCE_INVALID:' + name)
            continue
        path = root / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            errors.append('SOURCE_CHANGED:' + name)
    for rel in DOCS:
        try:
            content = (root / rel).read_text(encoding='utf-8')
        except (OSError, UnicodeError):
            errors.append('DRAFT_MISSING:' + rel)
            continue
        if any(token not in content for token in HOLD):
            errors.append('DRAFT_WARNING_MISSING:' + rel)
        if 'V18.0.0' not in content:
            errors.append('DRAFT_IDENTITY_MISSING:' + rel)
    try:
        version = (root / 'version.py').read_text(encoding='utf-8')
        if ('APP_VERSION = "17.1.3"' not in version or
                'APP_BUILD_ID = "v17.1.3-20261022"' not in version):
            errors.append('CURRENT_RUNTIME_RELEASE_HOLD_MISSING')
        installer = (root / 'tools/install_zendure_controller_v18_candidate.sh').read_text(encoding='utf-8')
        header = installer.split('SCRIPT_DIR=', 1)[0]
        if not re.search(r'^exit 78\s*$', header, re.M) or 'RELEASE_HOLD' not in header:
            errors.append('V18_INSTALLER_HARD_HOLD_MISSING')
    except (OSError, UnicodeError):
        errors.append('INSTALLER_OR_RUNTIME_UNREADABLE')
    if (root / 'V18_0_0_SOURCE_MANIFEST.sha256').exists() or (root / 'validation/V18_0_0_BUILD_EVIDENCE.json').exists():
        errors.append('FINAL_BUILD_EVIDENCE_UNEXPECTED_IN_DRAFT')
    # This deliberately never asserts release/field success and never mutates.
    return {'gate': 'PASS' if not errors else 'FAIL', 'installable': False,
            'scope': 'CP29_DEVELOPMENT_DRAFT_TRACEABILITY_ONLY',
            'files_checked': len(REQUIRED_SOURCES),
            'documents_checked': len(DOCS), 'errors': errors}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', default='.')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    result = check(Path(args.root))
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else
          'V18_DRAFT_PROVENANCE_GATE=' + result['gate'] + ' ' + repr(result['errors']))
    return int(result['gate'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())
