#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Create a separate, non-installable V18 identity staging tree from CP29.

This tool NEVER prepares a released installer. All device-affecting installer
paths are guarded by a non-overridable early exit 78. No input file is edited.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from deployment_contract import build_source_manifest, verify_source_manifest, release_tree_hygiene
from verify_release_identity_readiness import check as identity_check, python_identity
from verify_v18_draft_provenance import check as draft_check
from verify_v18_datasheet_draft import check as datasheet_source_check, METADATA as DATASHEET_METADATA

VERSION = '18.0.0'
BUILD = 'v18.0.0-20261027'  # provisional, never a final release identifier
SOURCE_VERSION = '17.1.3'
SOURCE_BUILD = 'v17.1.3-20261022'
OUTPUT_ROOT = 'zendure_controller_v18_0_0_STAGING_NOT_INSTALLABLE'
MANIFEST = 'V18_0_0_SOURCE_MANIFEST.sha256'
EVIDENCE = 'validation/V18_0_0_BUILD_EVIDENCE.json'
DATASHEET_BINDING = 'validation/V18_0_0_STAGING_DATASHEET_BINDING.json'


def _replace_once(source: str, pattern: str, replacement: str) -> str:
    out, n = re.subn(pattern, replacement, source, flags=re.M)
    if n != 1:
        raise ValueError('RELEASE_STAGING_SOURCE_IDENTITY_UNEXPECTED:' + pattern)
    return out


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()



def _verify_staged_datasheet(root: Path) -> list[str]:
    """Independently verify the CP33 draft after the two intentional V18 identity substitutions.

    Draft validity is not release approval. A staged source hash is NEVER passed
    off as the original CP33 source digest, and no product DOCX/PDF is promoted.
    """
    errors: list[str] = []
    try:
        source = json.loads((root / DATASHEET_METADATA).read_text(encoding='utf8'))
        binding = json.loads((root / DATASHEET_BINDING).read_text(encoding='utf8'))
    except (OSError, ValueError, AttributeError):
        return ['STAGED_DATASHEET_PROVENANCE_MISSING_OR_INVALID']
    guards = {'schema': 'ZEC_V18_STAGING_DATASHEET_BINDING_V1',
              'status': 'DEVELOPMENT_NOT_INSTALLABLE', 'release_gate': 'FAIL',
              'datasheet_status': 'DRAFT_ONLY', 'hardware_effect': 'NOT_VERIFIED'}
    if any(binding.get(k) != v for k, v in guards.items()):
        errors.append('STAGED_DATASHEET_RELEASE_HOLD_MISMATCH')
    if source.get('schema') != 'ZEC_V18_DATASHEET_DRAFT_PROVENANCE_V1' or any(
        source.get(k) != v for k, v in {
            'status': 'DEVELOPMENT_NOT_INSTALLABLE', 'release_gate': 'FAIL',
            'hardware_effect': 'NOT_VERIFIED', 'manual_uml': 'PENDING',
            'build_identity_status': 'PROVISIONAL_NOT_FROZEN',
            'target_version': VERSION, 'target_build_id': BUILD,
        }.items()
    ):
        errors.append('STAGED_DATASHEET_SOURCE_GUARD_INVALID')
    if binding.get('source_metadata_sha256') != _digest(root / DATASHEET_METADATA):
        errors.append('STAGED_DATASHEET_METADATA_HASH_MISMATCH')
    allowed_replacements = {'version.py', 'tools/install_zendure_controller.sh'}
    previous_hashes = source.get('source_sha256', {})
    if not isinstance(previous_hashes, dict) or not allowed_replacements.issubset(previous_hashes):
        errors.append('STAGED_DATASHEET_SOURCE_COVERAGE_MISSING')
    else:
        if set(binding.get('intentional_source_replacements', {})) != allowed_replacements:
            errors.append('STAGED_DATASHEET_REPLACEMENT_SET_INVALID')
        for relative, original_digest in previous_hashes.items():
            if not isinstance(relative, str) or relative.startswith('/') or '..' in Path(relative).parts:
                errors.append('STAGED_DATASHEET_UNSAFE_PATH'); continue
            path = root / relative
            if not path.is_file():
                errors.append('STAGED_DATASHEET_SOURCE_MISSING:' + relative);continue
            if relative in allowed_replacements:
                pair = binding.get('intentional_source_replacements', {}).get(relative, {})
                if not isinstance(pair, dict) or pair.get('cp33_source_sha256') != original_digest or pair.get('staged_sha256') != _digest(path):
                    errors.append('STAGED_DATASHEET_REPLACEMENT_HASH_MISMATCH:' + relative)
                if _digest(path) == original_digest:
                    errors.append('STAGED_DATASHEET_EXPECTED_REPLACEMENT_MISSING:' + relative)
            elif _digest(path) != original_digest:
                errors.append('STAGED_DATASHEET_UNAUTHORIZED_SOURCE_CHANGE:' + relative)
    for category in ('canonical_previous_datasheet_sha256',):
        values = source.get(category, {})
        if not isinstance(values, dict) or len(values) != 3:
            errors.append('STAGED_DATASHEET_LEGACY_COVERAGE_MISSING');continue
        for relative, expected in values.items():
            if not isinstance(relative, str) or relative.startswith('/') or '..' in Path(relative).parts or not (root/relative).is_file() or _digest(root/relative) != expected:
                errors.append('STAGED_DATASHEET_PREVIOUS_RELEASE_MISMATCH:' + str(relative))
    for kind in ('docx', 'pdf'):
        info = source.get('files', {}).get(kind, {})
        relative = info.get('path', '')
        if not isinstance(relative, str) or not relative.startswith('docs/releases/v18.0.0/') or not relative.endswith('.'+kind) or '..' in Path(relative).parts:
            errors.append('STAGED_DATASHEET_INVALID_ASSET_PATH:' + kind);continue
        path = root / relative
        if not path.is_file() or _digest(path) != info.get('sha256') or binding.get('assets_sha256', {}).get(kind) != info.get('sha256'):
            errors.append('STAGED_DATASHEET_ASSET_HASH_MISMATCH:' + kind)
    return errors


def _create_datasheet_binding(source_root: Path, stage: Path) -> None:
    source_record = json.loads((source_root / DATASHEET_METADATA).read_text(encoding='utf8'))
    record = {
        'schema': 'ZEC_V18_STAGING_DATASHEET_BINDING_V1',
        'status': 'DEVELOPMENT_NOT_INSTALLABLE', 'release_gate': 'FAIL',
        'datasheet_status': 'DRAFT_ONLY', 'hardware_effect': 'NOT_VERIFIED',
        'source_metadata_sha256': _digest(source_root / DATASHEET_METADATA),
        'assets_sha256': {kind: source_record['files'][kind]['sha256'] for kind in ('docx', 'pdf')},
        'intentional_source_replacements': {
            relative: {
                'cp33_source_sha256': source_record['source_sha256'][relative],
                'staged_sha256': _digest(stage / relative),
            }
            for relative in ('version.py', 'tools/install_zendure_controller.sh')
        },
    }
    (stage / DATASHEET_BINDING).write_text(json.dumps(record, indent=2, ensure_ascii=False)+'\n', encoding='utf8')


def verify_staging(root: Path) -> dict:
    """Fail-closed check of staging hold, consistency, provenance and CRC-independent file hashes."""
    errors = []
    if not root.is_dir() or root.name != OUTPUT_ROOT:
        return {'gate': 'FAIL', 'installable': False, 'errors': ['STAGING_ROOT_INVALID']}
    version = python_identity(root)
    expected = {'APP_VERSION': VERSION, 'APP_VERSION_LABEL': 'V'+VERSION, 'APP_BUILD_ID': BUILD}
    if version != expected:
        errors.append('STAGED_RUNTIME_IDENTITY_MISMATCH')
    installer = root / 'tools/install_zendure_controller.sh'
    try:
        script = installer.read_text(encoding='utf-8')
        header = script.split('SCRIPT_DIR=', 1)[0]
        if not re.search(r'^exit 78\s*$', header, flags=re.M) or 'RELEASE_HOLD' not in header:
            errors.append('STANDARD_INSTALLER_EARLY_HOLD_MISSING')
        if installer.stat().st_mode & 0o111:
            errors.append('STANDARD_INSTALLER_EXECUTABLE')
        for value in ('EXPECTED_VERSION_ARG="v18_0_0"',
                      'EXPECTED_SOURCE_VERSION="17.1.3"',
                      'EXPECTED_SOURCE_BUILD_ID="v17.1.3-20261022"',
                      'EXPECTED_TARGET_VERSION="18.0.0"',
                      'EXPECTED_TARGET_BUILD_ID="v18.0.0-20261027"'):
            if value not in script:
                errors.append('STANDARD_INSTALLER_IDENTITY_MISMATCH:'+value)
    except OSError:
        errors.append('STANDARD_INSTALLER_MISSING')
    try:
        evidence = json.loads((root / EVIDENCE).read_text(encoding='utf-8'))
        if (evidence.get('format') != 'ZEC_BUILD_EVIDENCE_V1' or
                evidence.get('status') != 'BLOCKED' or
                evidence.get('release', {}).get('build_id') != BUILD or
                evidence.get('full_regression', {}).get('status') != 'NOT_RUN_ON_FINAL_TREE' or
                evidence.get('resourcewarning_regression', {}).get('status') != 'NOT_RUN_ON_FINAL_TREE'):
            errors.append('BUILD_EVIDENCE_NOT_EXPLICITLY_BLOCKED')
    except (OSError, ValueError, AttributeError):
        errors.append('BUILD_EVIDENCE_MISSING_OR_INVALID')
    errors.extend(_verify_staged_datasheet(root))
    if (root/'docs/ZEC_Master_Backlog.md').read_bytes() != (root/'05_ZEC_BACKLOG_AND_ROADMAP.md').read_bytes():
        errors.append('MASTER_LEDGER_SNAPSHOT_NOT_IDENTICAL')
    manifest_result = verify_source_manifest(root=root, manifest_name=MANIFEST)
    if not manifest_result['ok']:
        errors.append('STAGING_SOURCE_MANIFEST_INVALID')
    hygiene = release_tree_hygiene(root=root, manifest_name=MANIFEST)
    if not hygiene['ok']:
        errors.append('STAGING_HYGIENE_FAILED')
    identity = identity_check(root,version=VERSION,build_id=BUILD,
                              source_version=SOURCE_VERSION,source_build_id=SOURCE_BUILD)
    if identity['gate'] != 'FAIL':
        errors.append('RELEASE_IDENTITY_MUST_REMAIN_BLOCKED')
    return {'gate': 'PASS' if not errors else 'FAIL', 'installable': False,
            'scope': 'V18_STAGING_IDENTITY_AND_SOURCE_MANIFEST_ONLY',
            'version': VERSION, 'build_id': BUILD,
            'source_manifest_entries': manifest_result.get('entry_count', 0),
            'release_identity_gate': identity['gate'],
            'release_identity_errors': identity['errors'],
            'errors': errors}


def prepare(source_root: Path, output_parent: Path) -> dict:
    """Create a staged tree without altering source or any existing output path."""
    source_root = source_root.resolve()
    output_parent = output_parent.resolve()
    if not source_root.is_dir() or not output_parent.is_dir():
        raise ValueError('SOURCE_OR_OUTPUT_PARENT_NOT_DIRECTORY')
    if output_parent == source_root or source_root in output_parent.parents or output_parent in source_root.parents:
        raise ValueError('SOURCE_AND_OUTPUT_ARE_NOT_DISJOINT')
    output = output_parent / OUTPUT_ROOT
    if output.exists() or output.is_symlink():
        raise FileExistsError('STAGING_OUTPUT_ALREADY_EXISTS')
    if python_identity(source_root) != {
            'APP_VERSION': SOURCE_VERSION, 'APP_VERSION_LABEL': 'V'+SOURCE_VERSION,
            'APP_BUILD_ID': SOURCE_BUILD}:
        raise ValueError('SOURCE_IS_NOT_EXPECTED_V17_1_3_DEVELOPMENT_TREE')
    datasheet_provenance = datasheet_source_check(source_root)
    if datasheet_provenance['gate'] != 'PASS':
        raise ValueError('CP33_DATASHEET_DRAFT_PROVENANCE_NOT_PASS:'+repr(datasheet_provenance['errors']))
    provenance = draft_check(source_root)
    if provenance['gate'] != 'PASS':
        raise ValueError('CP29_DRAFT_PROVENANCE_NOT_PASS:'+repr(provenance['errors']))
    tmp = Path(tempfile.mkdtemp(prefix='.zec_v18_staging_', dir=output_parent))
    stage = tmp / OUTPUT_ROOT
    try:
        shutil.copytree(source_root, stage,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.pytest_cache', '*.pyo',
                                                       'logs', '*.sqlite3', '*.sqlite3-*',
                                                       '*.sqlite', '*.db', '*.db-*', '*.log'))
        version = stage / 'version.py'
        old = version.read_text(encoding='utf-8')
        updated = _replace_once(old, r'^APP_VERSION = "17\.1\.3"$', 'APP_VERSION = "18.0.0"')
        updated = _replace_once(updated, r'^APP_VERSION_LABEL = "V17\.1\.3"$', 'APP_VERSION_LABEL = "V18.0.0"')
        updated = _replace_once(updated, r'^APP_BUILD_ID = "v17\.1\.3-20261022"$', 'APP_BUILD_ID = "'+BUILD+'"')
        version.write_text(updated, encoding='utf-8')
        installer = stage/'tools/install_zendure_controller.sh'
        guarded = (stage/'tools/install_zendure_controller_v18_candidate.sh').read_bytes()
        # Do not install: retain the hard hold and remove the direct execute bit.
        installer.write_bytes(guarded)
        installer.chmod(installer.stat().st_mode & ~0o111)
        (stage/'README_INSTALLATION.md').write_bytes((stage/'README_INSTALLATION_V18_0_0.md').read_bytes())
        for rel in ('README.md', 'docs/INDEX.md'):
            path = stage/rel
            content = path.read_text(encoding='utf-8')
            path.write_text('**V18.0.0 / '+BUILD+' – STAGING · RELEASE_HOLD · DEVELOPMENT_NOT_INSTALLABLE**\n\n'+content,
                            encoding='utf-8')
        (stage/'docs/ZEC_Master_Backlog.md').write_bytes((stage/'05_ZEC_BACKLOG_AND_ROADMAP.md').read_bytes())
        build_evidence = {
            'format': 'ZEC_BUILD_EVIDENCE_V1',
            'release': {'version': VERSION, 'label': 'V'+VERSION, 'build_id': BUILD},
            'status': 'BLOCKED', 'reason': 'FINAL_TREE_REGRESSION_AND_MANUAL_RELEASE_GATES_PENDING',
            'test_file_count': 0,
            'full_regression': {'status': 'NOT_RUN_ON_FINAL_TREE', 'tests': 0, 'subtests': 0},
            'resourcewarning_regression': {'status': 'NOT_RUN_ON_FINAL_TREE', 'tests': 0,
                                           'subtests': 0, 'warnings_mode': 'error::ResourceWarning'},
        }
        (stage/EVIDENCE).write_text(json.dumps(build_evidence, indent=2, ensure_ascii=False)+'\n',encoding='utf-8')
        _create_datasheet_binding(source_root, stage)
        manifest = build_source_manifest(root=stage,manifest_name=MANIFEST)
        if not manifest['ok']:
            raise ValueError('STAGING_MANIFEST_GATE_FAILED:'+repr(manifest['errors']))
        gate = verify_staging(stage)
        if gate['gate'] != 'PASS':
            raise ValueError('STAGING_VERIFICATION_FAILED:'+repr(gate['errors']))
        # Atomic publication of a complete, still-noninstallable directory.
        if output.exists():
            raise FileExistsError('STAGING_OUTPUT_RACE')
        os.rename(stage, output)
        gate['output_root'] = str(output)
        gate['source_cp29_version_sha256'] = _digest(source_root/'version.py')
        return gate
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-root', required=True)
    ap.add_argument('--output-parent', required=True)
    ap.add_argument('--verify-only', action='store_true')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    if args.verify_only:
        result = verify_staging(Path(args.output_parent)/OUTPUT_ROOT)
    else:
        try:
            result = prepare(Path(args.source_root), Path(args.output_parent))
        except (OSError, ValueError) as exc:
            result = {'gate': 'FAIL', 'installable': False, 'errors': [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else repr(result))
    return int(result['gate'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())
