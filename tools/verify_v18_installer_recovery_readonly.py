#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fail-closed, nonmutating V18 installer/rollback *source contract* audit.

NO deployment, backup creation, host probing, service calls, or rollback execution.
PASS means only a demonstrable structural contract + the actual early release hold.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

SCOPE = 'STATIC_INSTALLER_AND_RECOVERY_CONTRACT_NOT_EXECUTED'
REQUIRED_EXCLUDES = (
    "--exclude 'config.json'", "--exclude 'config.json.last-good*'",
    "--exclude 'logs/'", "--exclude 'config-states/'",
    "--exclude '*.sqlite3'", "--exclude 'zec_config_snapshots.json'",
    "--exclude 'zec_runtime_events.jsonl*'",
)


def _noncomment_lines(content: str) -> list[str]:
    return [line.strip() for line in content.splitlines()
            if line.strip() and not line.lstrip().startswith('#')]


def _function(content: str, name: str) -> str:
    """Extract the exact top-level bash function using balanced literal braces.

    The inspected installer uses no dynamic brace construction in function bodies.
    This is a structural audit, NOT a complete Bash parser.
    """
    match = re.search(r'^' + re.escape(name) + r'\(\)\s*\{\s*$', content, re.M)
    if not match:
        return ''
    # Top-level Bash functions end with a closing brace in column zero.
    # Inner error blocks contain indented closing braces and must be retained.
    text = content[match.end():]
    closing = re.search(r'^}\s*$', text, re.M)
    return text[:closing.start()] if closing else ''


def _after(content: str, before: str, after: str) -> bool:
    a = content.find(before)
    b = content.find(after)
    return a >= 0 and b >= 0 and a < b


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as file:
        for block in iter(lambda: file.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def check(root: Path, *, execute_hold: bool = True) -> dict:
    root = Path(root).resolve()
    candidate = root / 'tools/install_zendure_controller_v18_candidate.sh'
    standard = root / 'tools/install_zendure_controller.sh'
    root_helper = root / 'tools/root_artifact_transaction.sh'
    version = root / 'version.py'
    errors: list[str] = []
    inspected: dict[str, str] = {}
    for name, path in [('candidate', candidate), ('standard', standard),
                       ('root_helper', root_helper), ('version', version)]:
        if not path.is_file() or path.is_symlink():
            errors.append('MISSING_OR_SYMLINK_SOURCE:' + name)
        else:
            inspected[name] = _sha(path)
    if errors:
        return _report(errors, inspected, hold_executed=False)

    source = candidate.read_text(encoding='utf-8')
    std = standard.read_text(encoding='utf-8')
    helper = root_helper.read_text(encoding='utf-8')
    ident = version.read_text(encoding='utf-8')
    staged = bool(re.search(r'^APP_VERSION\s*=\s*[\'\"]18\.0\.0[\'\"]', ident, re.M))
    legacy = bool(re.search(r'^APP_VERSION\s*=\s*[\'\"]17\.1\.3[\'\"]', ident, re.M))
    if not (staged or legacy):
        errors.append('UNSUPPORTED_ROOT_IDENTITY')

    for name, code in [('candidate', source)] + ([('standard', std)] if staged else []):
        # Verify first *executable* statements, no unguarded shell evaluation.
        commands = _noncomment_lines(code)
        if (len(commands) < 3 or commands[0] != 'set -Eeuo pipefail'
                or not re.fullmatch(r"printf '%s\\n' '[^']*RELEASE_HOLD[^']*' >&2", commands[1])
                or commands[2] != 'exit 78'):
            errors.append('IMMEDIATE_NONOVERRIDABLE_HOLD_INVALID:' + name)
        if name == 'standard' and (standard.stat().st_mode & 0o111):
            errors.append('STAGED_STANDARD_INSTALLER_MUST_NOT_BE_EXECUTABLE')
    if legacy and 'EXPECTED_TARGET_VERSION="17.1.3"' not in std:
        errors.append('HISTORIC_V17_STANDARD_CONTRACT_CHANGED')
    if staged and 'EXPECTED_TARGET_VERSION="18.0.0"' not in std:
        errors.append('STAGED_STANDARD_IDENTITY_CHANGED')

    for item in (
        'EXPECTED_VERSION_ARG="v18_0_0"', 'EXPECTED_SOURCE_VERSION="17.1.3"',
        'EXPECTED_SOURCE_BUILD_ID="v17.1.3-20261022"',
        'EXPECTED_TARGET_VERSION="18.0.0"',
        'EXPECTED_TARGET_BUILD_ID="v18.0.0-20261027"',
        'SOURCE_MANIFEST="V18_0_0_SOURCE_MANIFEST.sha256"',
    ):
        if item not in _noncomment_lines(source):
            errors.append('CANDIDATE_IDENTITY_MISMATCH:' + item)
    required_functions = ('package_preflight','system_dependency_preflight','classify_mode',
                          'mode_specific_preflight','rollback_update','rollback_fresh',
                          'on_error','verify_build_evidence_at','start_support_capture',
                          'finalize_support_capture','require_basic_contract')
    extracted = {f: _function(source, f) for f in required_functions}
    for f, body in extracted.items():
        if not body:
            errors.append('MISSING_INSTALLER_FUNCTION:' + f)
    if not errors:
        # Below main marker after all functions, executable invocation order.
        invocation = '\npackage_preflight\nsystem_dependency_preflight\nclassify_mode\nmode_specific_preflight\n'
        if invocation not in source:
            errors.append('PREFLIGHT_ENTRYPOINT_ORDER_INVALID')
            entry = ''
        else:
            entry = source[source.index(invocation):]
        steps = (
            'package_preflight\n', 'system_dependency_preflight\n',
            'classify_mode\n', 'mode_specific_preflight\n',
            'PREFLIGHT_RESULT=PASS', 'if [ "$PREFLIGHT_ONLY" -eq 1 ]; then',
            'INSTALLATION_STARTED=1', 'zec_backup_root_artifacts "$ROOT_ARTIFACT_BACKUP"',
            'if [ "$INSTALL_MODE" = "SUPPORTED_UPDATE" ]; then',
            'sudo tar -czf "$BACKUP" zendure-controller', 'BACKUP_CREATED=1',
            'rsync -a --delete',
        )
        for a, b in zip(steps, steps[1:]):
            if not _after(entry, a, b):
                errors.append('PREFLIGHT_BACKUP_DEPLOY_ORDER_INVALID:' + a + '->' + b)
        if ('verify_manifest_at "$STAGED_ROOT"' not in extracted['package_preflight']
                or 'verify_build_evidence_at "$STAGED_ROOT"' not in extracted['package_preflight']
                or 'verify_runtime_readiness_smoke "$STAGED_ROOT"' not in extracted['package_preflight']):
            errors.append('PACKAGE_PREDEPLOY_VERIFICATION_INCOMPLETE')
        if ('--expected-version "$EXPECTED_SOURCE_VERSION"' not in extracted['classify_mode']
                or '--expected-build "$EXPECTED_SOURCE_BUILD_ID"' not in extracted['classify_mode']
                or 'AMBIGUOUS_OR_PARTIAL_INSTALL' not in extracted['classify_mode']
                or 'CLEAN_FRESH_INSTALL' not in extracted['classify_mode']
                or '--fresh-install' not in extracted['classify_mode']
                or 'if [ "$INSTALL_MODE" = "CLEAN_FRESH_INSTALL" ] && [ "$FRESH_ASSERT" -ne 1 ]; then' not in extracted['classify_mode']
                or 'if [ "$FRESH_ASSERT" -eq 1 ] && [ "$INSTALL_MODE" != "CLEAN_FRESH_INSTALL" ]; then' not in extracted['classify_mode']
                or 'if [ "$WEB_PORT_EXPLICIT" -eq 1 ] && [ "$INSTALL_MODE" != "CLEAN_FRESH_INSTALL" ]; then' not in extracted['classify_mode']):
            errors.append('MODE_CLASSIFICATION_FAIL_CLOSED_CONTRACT_MISSING')
        if ('port-check' not in extracted['mode_specific_preflight']
                or '--check-only' not in extracted['mode_specific_preflight']):
            errors.append('MODE_PREDEPLOY_PORT_OR_MIGRATION_CHECK_MISSING')
        if ('BACKUP_CREATED=1' not in entry or 'BACKUP_SHA256=' not in entry
                or 'CONFIG_BACKUP=' not in source or 'cp "$TARGET/config.json" "$CONFIG_BACKUP"' not in entry):
            errors.append('UPDATE_BACKUP_CONTRACT_MISSING')
        for item in REQUIRED_EXCLUDES:
            if item not in entry:
                errors.append('USER_DATA_PRESERVATION_EXCLUDE_MISSING:' + item)
        if ('sudo tar -xzf "$BACKUP" -C /opt' not in extracted['rollback_update']
                or 'zec_restore_root_artifacts' not in extracted['rollback_update']
                or 'restore_previous_services' not in extracted['rollback_update']):
            errors.append('UPDATE_ROLLBACK_RESTORE_CONTRACT_MISSING')
        if ('sudo rm -rf "$TARGET"' not in extracted['rollback_fresh']
                or 'zec_restore_root_artifacts' not in extracted['rollback_fresh']
                or 'sudo systemctl disable --now zendure-controller.service' not in extracted['rollback_fresh']):
            errors.append('FRESH_ROLLBACK_CONTRACT_MISSING')
        if ('start_support_capture "pre_rollback"' not in extracted['on_error']
                or 'finalize_support_capture' not in extracted['on_error']
                or 'ROLLBACK_STARTED=1' not in extracted['on_error']
                or '"$BASHPID" != "$MAIN_BASHPID"' not in extracted['on_error']):
            errors.append('SINGLE_OWNER_FAILURE_DIAGNOSTIC_OR_ROLLBACK_MISSING')
        if ('trap \'on_error $? $LINENO\' ERR' not in source
                or 'trap \'on_error $? $LINENO\' EXIT' not in source):
            errors.append('FAILURE_TRAPS_MISSING')
        for item in ('zec_backup_root_artifacts()', 'zec_restore_root_artifacts()',
                     'state="$(', 'present', 'absent'):
            if item not in helper:
                errors.append('ROOT_ARTIFACT_EXACT_RESTORE_CONTRACT_MISSING:' + item)

    for name, path in [('candidate', candidate), ('standard', standard)]:
        if subprocess.run(['bash', '-n', str(path)], capture_output=True, timeout=5).returncode:
            errors.append('SHELL_SYNTAX_INVALID:' + name)

    # No execution of a tampered installer: only run the original once the
    # immediate, unconditional hold has passed the structural audit.
    hold_executed = False
    if execute_hold and not errors:
        with tempfile.TemporaryDirectory(prefix='zec_hold_audit_') as td:
            for args in ([], ['v18_0_0'], ['v18_0_0','--preflight-only'],
                         ['v18_0_0','--fresh-install'], ['v18_0_0','--web-port','18888'],
                         ['v18_0_0','--unknown-option']):
                for name, path in [('candidate', candidate)] + ([('standard', standard)] if staged else []):
                    proc = subprocess.run(['bash',str(path),*args], cwd=td,
                                          capture_output=True, text=True, timeout=5)
                    if proc.returncode != 78 or 'RELEASE_HOLD' not in proc.stderr:
                        errors.append('HOLD_EXECUTION_FAILURE:' + name + ':' + str(args))
                    if list(Path(td).iterdir()):
                        errors.append('HOLD_CREATED_LOCAL_FILES')
            hold_executed = True
    return _report(errors, inspected, hold_executed=hold_executed)


def _report(errors: list[str], hashes: dict[str, str], *, hold_executed: bool) -> dict:
    return {
        'schema': 'ZEC_V18_INSTALLER_RECOVERY_READONLY_AUDIT_V1',
        'gate': 'PASS' if not errors else 'FAIL',
        'scope': SCOPE,
        'source_sha256': hashes,
        'early_hold_execution_tested': hold_executed,
        'installer_executed_past_hold': False,
        'host_mutation_performed': False,
        'rollback_executed': False,
        'archive_restore_integrity_tested': False,
        'real_pi_tested': False,
        'release_approved': False,
        'errors': errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--no-execute-hold', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    result = check(args.root, execute_hold=not args.no_execute_hold)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result['gate'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
