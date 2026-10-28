#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Isolated, bounded V18 staging regression; NEVER produces release build evidence.

Checks staging provenance and a known V17-only test-fixture contradiction first.
When the fixture contract is clean, executes two full suites from disposable copies,
with separate machine-readable results and strict ResourceWarning policy. A failed
suite, incomplete output or timeout never becomes a PASS.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest

from prepare_v18_staging_tree import OUTPUT_ROOT, verify_staging

SCHEMA = 'ZEC_V18_STAGING_REGRESSION_READINESS_V1'
# These are exact contradictory contracts on the *same test source* when the root
# is V18. Do not silently exclude the affected tests from the release suite.
V17_ONLY_FIXTURES = {
    'tests/test_batcare_v18_staging_freeze.py': (
        'cls.created = prepare(ROOT, cls.parent)',
    ),
    'tests/test_batcare_v18_candidate_contract.py': (
        "self.assertEqual('17.1.3', python_identity(ROOT)['APP_VERSION'])",
    ),
    'tests/test_batcare_release_identity_readiness.py': (
        "self.assertEqual('17.1.3',python_identity(ROOT)['APP_VERSION'])",
    ),
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()



def _guarded_dual_root_staging_fixture(source: str) -> bool:
    """AST-prove V18 copy/verify and V17-only builder in opposing branches.

    Whitespace, comments and wrapped source calls must not affect this gate.
    A comment mentioning a guard is not a guard. Bad syntax fails closed.
    """
    try:
        parsed = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(parsed):
        if not isinstance(node, ast.If) or ast.unparse(node.test) != 'cls.from_staging':
            continue
        true_calls = [n for part in node.body for n in ast.walk(part) if isinstance(n, ast.Call)]
        false_calls = [n for part in node.orelse for n in ast.walk(part) if isinstance(n, ast.Call)]
        has_guarded_copy = any(
            ast.unparse(c.func) == 'shutil.copytree' and
            any(k.arg == 'ignore' and isinstance(k.value, ast.Call) and
                ast.unparse(k.value.func) == 'shutil.ignore_patterns' for k in c.keywords)
            for c in true_calls)
        has_stage_verify = any(ast.unparse(c.func) == 'verify_staging' for c in true_calls)
        has_v17_prepare = any(ast.unparse(c.func) == 'prepare' and len(c.args) >= 1 and
                              ast.unparse(c.args[0]) == 'ROOT' for c in false_calls)
        if has_guarded_copy and has_stage_verify and has_v17_prepare:
            return True
    return False

def find_fixture_blockers(root: Path) -> list[str]:
    """Known, demonstrable unmodified V17 test preconditions, not speculative failures."""
    errors: list[str] = []
    for rel, patterns in V17_ONLY_FIXTURES.items():
        try:
            content = (root / rel).read_text(encoding='utf-8')
        except OSError:
            errors.append('TEST_SOURCE_MISSING:' + rel)
            continue
        for pattern in patterns:
            if pattern in content:
                # A V17-only builder call is permissible *only* in the explicit
                # dual-root fixture where V18 first clones the already-staged
                # source and performs staging verification rather than prepare().
                dual_root = (rel == 'tests/test_batcare_v18_staging_freeze.py' and
                             _guarded_dual_root_staging_fixture(content))
                if not dual_root:
                    errors.append('V17_SOURCE_ONLY_FIXTURE_ON_V18_STAGE:' + rel)
                break
    return errors


def suite_result(*, process_exit: int | None, worker: dict | None,
                 timed_out: bool, strict: bool) -> dict:
    """Conservative validation of independently captured unittest completion."""
    w = worker if isinstance(worker, dict) else {}
    tests = w.get('tests')
    subtests = w.get('subtests')
    errors = w.get('errors')
    failures = w.get('failures')
    valid = all(type(x) is int and x >= 0 for x in (tests, subtests, errors, failures))
    passed = (not timed_out and process_exit == 0 and valid and tests > 0 and
              errors == 0 and failures == 0 and w.get('completed') is True and
              (not strict or w.get('warnings_mode') == 'error::ResourceWarning'))
    return {'status': 'PASS' if passed else 'FAIL', 'tests': tests if valid else None,
            'subtests': subtests if valid else None, 'errors': errors if valid else None,
            'failures': failures if valid else None, 'exit_code': process_exit,
            'timed_out': timed_out, 'warnings_mode': 'error::ResourceWarning' if strict else 'default',
            'complete': w.get('completed') is True}


def worker_run(root: Path, output: Path, strict: bool) -> int:
    """Private worker; writes objective counts but never a release certificate."""
    root = root.resolve()
    os.chdir(root)
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / 'tools'))
    # Unittest discovery with top_level_dir=root does not automatically add
    # sibling fixture imports from tests/ (e.g. sma_packet_fixtures).
    sys.path.insert(0, str(root / 'tests'))
    class CountSubtests(unittest.TextTestResult):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            self.subtest_count = 0
        def addSubTest(self, test, subtest, err):
            self.subtest_count += 1
            return super().addSubTest(test, subtest, err)
    result = None
    try:
        suite = unittest.defaultTestLoader.discover(str(root / 'tests'), pattern='test_*.py', top_level_dir=str(root))
        result = unittest.TextTestRunner(verbosity=1, resultclass=CountSubtests).run(suite)
        payload = {'completed': True, 'tests': result.testsRun,
                   'subtests': result.subtest_count, 'errors': len(result.errors),
                   'failures': len(result.failures),
                   'warnings_mode': 'error::ResourceWarning' if strict else 'default'}
        output.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
        return 0 if result.wasSuccessful() else 1
    except BaseException as exc:
        output.write_text(json.dumps({'completed': False, 'reason': type(exc).__name__}) + '\n', encoding='utf-8')
        raise


def run_suite(root: Path, *, strict: bool, timeout_seconds: int,
              report_dir: Path, label: str) -> dict:
    log = report_dir / f'{label}.log'
    sidecar = report_dir / f'{label}.worker.json'
    cmd = [sys.executable]
    if strict:
        cmd += ['-W', 'error::ResourceWarning']
    cmd += [str(Path(__file__).resolve()), '--worker-root', str(root),
            '--worker-result', str(sidecar), '--worker-strict' if strict else '--worker-normal']
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=f'{root}:{root / "tools"}:{root / "tests"}')
    exit_code = None
    timeout = False
    with log.open('wb') as outfile:
        proc = subprocess.Popen(cmd, cwd=root, env=env, stdout=outfile,
                                stderr=subprocess.STDOUT, start_new_session=True)
        try:
            exit_code = proc.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timeout = True
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
    try:
        captured = json.loads(sidecar.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        captured = None
    result = suite_result(process_exit=exit_code, worker=captured,
                          timed_out=timeout, strict=strict)
    result['log'] = str(log)
    return result


def check(root: Path, *, report_dir: Path | None = None,
          timeout_seconds: int = 90, run_tests: bool = False) -> dict:
    """Root untouched; all executed suites run from separate temporary source copies."""
    root = root.resolve()
    result = {'schema': SCHEMA, 'gate': 'FAIL', 'release_approved': False,
              'build_evidence_generated': False, 'staging_root': str(root),
              'errors': [], 'suites': []}
    if not root.is_dir() or root.name != OUTPUT_ROOT:
        result['errors'].append('STAGING_ROOT_INVALID')
        return result
    check_stage = verify_staging(root)
    result['staging_provenance_gate'] = check_stage['gate']
    if check_stage['gate'] != 'PASS':
        result['errors'].append('STAGING_PROVENANCE_INVALID')
        result['stage_errors'] = check_stage['errors']
        return result
    result['source_manifest_sha256'] = digest(root / 'V18_0_0_SOURCE_MANIFEST.sha256')
    blockers = find_fixture_blockers(root)
    result['errors'].extend(blockers)
    result['test_compatibility_gate'] = 'FAIL' if blockers else 'PASS'
    if not run_tests or blockers:
        result['test_execution'] = 'BLOCKED_BY_INCOMPATIBLE_TEST_CONTRACT' if blockers else 'NOT_REQUESTED'
        return result
    if timeout_seconds < 1 or report_dir is None:
        result['errors'].append('REPORT_DIRECTORY_OR_TIMEOUT_INVALID')
        return result
    report_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='zec_v18_qa_isolated_') as tmp:
        for i, strict in enumerate((False, True)):
            temp_root = Path(tmp)/f'run{i}'/OUTPUT_ROOT
            shutil.copytree(root, temp_root)
            suite = run_suite(temp_root, strict=strict, timeout_seconds=timeout_seconds,
                              report_dir=report_dir, label='strict' if strict else 'regular')
            result['suites'].append(suite)
            # No second run after failure; never fabricate the missing result.
            if suite['status'] != 'PASS':
                result['errors'].append('STAGING_SUITE_NOT_PASS:' + ('strict' if strict else 'regular'))
                break
    if len(result['suites']) == 2 and all(s['status'] == 'PASS' for s in result['suites']):
        a, b = result['suites']
        if a['tests'] != b['tests'] or a['subtests'] != b['subtests']:
            result['errors'].append('DUAL_SUITE_COUNT_MISMATCH')
    result['gate'] = 'PASS' if not result['errors'] and len(result['suites']) == 2 else 'FAIL'
    # PASS is *regression readiness only*, never release, deployment or build evidence approval.
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--staging-root')
    p.add_argument('--report-json')
    p.add_argument('--report-dir')
    p.add_argument('--run-tests', action='store_true')
    p.add_argument('--timeout-seconds', type=int, default=90)
    p.add_argument('--worker-root')
    p.add_argument('--worker-result')
    w = p.add_mutually_exclusive_group()
    w.add_argument('--worker-strict', action='store_true')
    w.add_argument('--worker-normal', action='store_true')
    args = p.parse_args()
    if args.worker_root:
        if not args.worker_result:
            p.error('worker result missing')
        return worker_run(Path(args.worker_root), Path(args.worker_result), args.worker_strict)
    if not args.staging_root:
        p.error('staging root missing')
    response = check(Path(args.staging_root), report_dir=Path(args.report_dir) if args.report_dir else None,
                     timeout_seconds=args.timeout_seconds, run_tests=args.run_tests)
    serialized = json.dumps(response, ensure_ascii=False, indent=2) + '\n'
    if args.report_json:
        Path(args.report_json).write_text(serialized, encoding='utf-8')
    print(serialized)
    return int(response['gate'] != 'PASS')

if __name__ == '__main__':
    raise SystemExit(main())
