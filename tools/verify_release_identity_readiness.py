#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Mutation-free, fail-closed version/installer/document consistency readiness audit.

This is a PRE-RELEASE identity gate, not an installer or a field acceptance.
It intentionally does not write to the source tree, touch runtime services,
import the controller, connect to a network, or assert hardware efficacy.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

try:
    from .deployment_contract import verify_build_evidence
except ImportError:  # direct CLI execution from tools/
    from deployment_contract import verify_build_evidence

_IDENTITY = ('APP_VERSION', 'APP_VERSION_LABEL', 'APP_BUILD_ID')
_INSTALLER = (
    'EXPECTED_VERSION_ARG', 'EXPECTED_SOURCE_VERSION', 'EXPECTED_SOURCE_BUILD_ID',
    'EXPECTED_TARGET_VERSION', 'EXPECTED_TARGET_BUILD_ID', 'SOURCE_MANIFEST',
)


def python_identity(root: Path) -> dict[str, str]:
    tree = ast.parse((root / 'version.py').read_text(encoding='utf-8'))
    values: dict[str, str] = {}
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id in _IDENTITY
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)):
            values[node.targets[0].id] = node.value.value
    return values


def shell_installer_identity(root: Path) -> dict[str, str]:
    text = (root / 'tools/install_zendure_controller.sh').read_text(encoding='utf-8')
    values: dict[str, str] = {}
    for key in _INSTALLER:
        m = re.search(r'^' + re.escape(key) + r'="([^"\n]*)"\s*$', text, re.M)
        if m:
            values[key] = m.group(1)
    return values


def check(root: Path, *, version: str, build_id: str,
          source_version: str, source_build_id: str) -> dict:
    """Return all independent missing/mismatched release obligations; never mutate."""
    root = root.resolve()
    errors: list[str] = []
    checked: dict[str, object] = {}
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        errors.append('CANDIDATE_VERSION_INVALID')
    if not re.fullmatch(r'v\d+\.\d+\.\d+-\d{8}', build_id) or not build_id.startswith('v'+version+'-'):
        errors.append('CANDIDATE_BUILD_INVALID')
    if not re.fullmatch(r'\d+\.\d+\.\d+', source_version):
        errors.append('SOURCE_VERSION_INVALID')
    if not re.fullmatch(r'v\d+\.\d+\.\d+-\d{8}', source_build_id) or not source_build_id.startswith('v'+source_version+'-'):
        errors.append('SOURCE_BUILD_INVALID')
    if version == source_version or build_id == source_build_id:
        errors.append('RELEASE_IDENTITY_NOT_NEW')
    label = 'V'+version
    slug = 'V'+version.replace('.', '_')
    arg = 'v'+version.replace('.', '_')
    expected = {'APP_VERSION': version, 'APP_VERSION_LABEL': label, 'APP_BUILD_ID': build_id}
    try:
        runtime = python_identity(root)
    except (OSError, SyntaxError, UnicodeError, ValueError) as ex:
        runtime = {}
        errors.append('RUNTIME_IDENTITY_UNREADABLE:'+type(ex).__name__)
    checked['runtime_identity'] = runtime
    for key, value in expected.items():
        if runtime.get(key) != value:
            errors.append('RUNTIME_IDENTITY_MISMATCH:'+key)
    try:
        installer = shell_installer_identity(root)
    except (OSError, UnicodeError) as ex:
        installer = {}
        errors.append('INSTALLER_IDENTITY_UNREADABLE:'+type(ex).__name__)
    checked['installer_identity'] = installer
    required_installer = {
        'EXPECTED_VERSION_ARG':arg,
        'EXPECTED_SOURCE_VERSION':source_version,
        'EXPECTED_SOURCE_BUILD_ID':source_build_id,
        'EXPECTED_TARGET_VERSION':version,
        'EXPECTED_TARGET_BUILD_ID':build_id,
        'SOURCE_MANIFEST':slug+'_SOURCE_MANIFEST.sha256',
    }
    for key, value in required_installer.items():
        if installer.get(key) != value:
            errors.append('INSTALLER_IDENTITY_MISMATCH:'+key)

    manifest = root / required_installer['SOURCE_MANIFEST']
    if not manifest.is_file() or not manifest.stat().st_size:
        errors.append('SOURCE_MANIFEST_MISSING')
    release_evidence = root / ('validation/'+slug+'_BUILD_EVIDENCE.json')
    if not release_evidence.is_file():
        errors.append('BUILD_EVIDENCE_MISSING')
    else:
        evidence_gate = verify_build_evidence(
            root=root, evidence_name='validation/'+slug+'_BUILD_EVIDENCE.json',
            expected_version=version, expected_label=label, expected_build=build_id,
        )
        checked['build_evidence_validation'] = {
            'ok': evidence_gate.get('ok', False),
            'errors': evidence_gate.get('errors', []),
        }
        if not evidence_gate.get('ok'):
            for problem in evidence_gate.get('errors', []):
                errors.append('BUILD_EVIDENCE_CONTRACT_FAIL:'+str(problem.get('reason', 'UNKNOWN')))

    release_docs = [
        f'README_INSTALLATION_{slug}.md',
        f'docs/releases/v{version}/RELEASE_INFO_{slug}.md',
        f'docs/releases/v{version}/TECHNICAL_NOTES_{slug}.md',
        f'docs/releases/v{version}/BUILD_VALIDATION_{slug}.md',
        f'docs/architecture/ZEC_{slug}_As_Built.md',
    ]
    for name in release_docs:
        path = root / name
        if not path.is_file() or path.stat().st_size == 0:
            errors.append('RELEASE_DOCUMENT_MISSING:'+name)
    for name in ('README.md', 'docs/INDEX.md'):
        path = root/name
        if not path.is_file() or label not in path.read_text(encoding='utf-8') or build_id not in path.read_text(encoding='utf-8'):
            errors.append('RELEASE_ENTRYPOINT_MISMATCH:'+name)
    install_guide = root/'README_INSTALLATION.md'
    version_guide = root/f'README_INSTALLATION_{slug}.md'
    if not install_guide.is_file() or not version_guide.is_file() or install_guide.read_bytes() != version_guide.read_bytes():
        errors.append('INSTALLATION_GUIDE_ENTRYPOINT_MISMATCH')

    meta = root/'docs/ZEC_Technisches_Datenblatt.release.json'
    if not meta.is_file():
        errors.append('DATASHEET_RELEASE_METADATA_MISSING')
    else:
        try:
            obj = json.loads(meta.read_text(encoding='utf-8'))
            if any(obj.get(k) != v for k,v in [('release_version',version),('release_label',label),('build_id',build_id)]):
                errors.append('DATASHEET_RELEASE_IDENTITY_MISMATCH')
            for name, key in [('ZEC_Technisches_Datenblatt.docx','docx_sha256'),('ZEC_Technisches_Datenblatt.pdf','pdf_sha256')]:
                p=root/'docs'/name
                if not p.is_file() or not p.stat().st_size or not isinstance(obj.get(key),str):
                    errors.append('DATASHEET_ASSET_MISSING_OR_UNHASHED:'+name)
                else:
                    import hashlib
                    if hashlib.sha256(p.read_bytes()).hexdigest() != obj[key]:
                        errors.append('DATASHEET_HASH_MISMATCH:'+name)
        except (ValueError, TypeError, OSError):
            errors.append('DATASHEET_RELEASE_METADATA_INVALID')

    uml_manifest = root/'docs/architecture/uml/manifest.json'
    if not uml_manifest.is_file():
        errors.append('UML_MANIFEST_MISSING')
    else:
        try:
            data = json.loads(uml_manifest.read_text(encoding='utf-8'))
            if data.get('release') != label or data.get('build_id') != build_id:
                errors.append('UML_RELEASE_IDENTITY_MISMATCH')
            if data.get('review_gate') != 'MANUAL_SOURCE_REVIEW_PASS' or data.get('status') != 'AS_BUILT_RELEASE_APPROVED':
                errors.append('UML_MANUAL_REVIEW_PENDING')
        except (OSError, ValueError, AttributeError):
            errors.append('UML_MANIFEST_INVALID')

    field_path = root/'tools'/('v'+version.split('.')[0]+'_field_acceptance.py')
    if not field_path.is_file():
        errors.append('VERSIONED_FIELD_ACCEPTANCE_TOOL_MISSING')
    checked['candidate'] = {'version': version,'label':label,'build_id':build_id}
    checked['source'] = {'version':source_version,'build_id':source_build_id}
    return {'gate':'PASS' if not errors else 'FAIL', 'installable':False,
            'scope':'RELEASE_IDENTITY_CONSISTENCY_ONLY',
            'errors':errors,'checked':checked}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',default='.')
    ap.add_argument('--candidate-version',required=True)
    ap.add_argument('--candidate-build',required=True)
    ap.add_argument('--source-version',required=True)
    ap.add_argument('--source-build',required=True)
    ap.add_argument('--json',action='store_true')
    a=ap.parse_args()
    result = check(Path(a.root),version=a.candidate_version,build_id=a.candidate_build,
                   source_version=a.source_version,source_build_id=a.source_build)
    print(json.dumps(result,indent=2,ensure_ascii=False) if a.json else 'RELEASE_IDENTITY_GATE='+result['gate']+' errors='+repr(result['errors']))
    return 0 if result['gate']=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())
