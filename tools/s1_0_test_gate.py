#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""S1.0 test collection and runner gate for the RC19 source tree.

This tool has no product runtime role. It inventories unittest and pytest
collections, normalises their IDs, runs the agreed gates, and writes reports.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import unittest
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]


def _walk_suite(suite: unittest.TestSuite) -> Iterable[unittest.TestCase]:
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _walk_suite(item)
        else:
            yield item


def _unittest_id_to_pytest(test_id: str) -> str:
    parts = test_id.split(".")
    if parts and parts[0] == "tests":
        parts = parts[1:]
    module = parts[0]
    rest = parts[1:]
    module_path = ROOT / "tests" / f"{module}.py"
    if not module_path.exists():
        raise RuntimeError(f"Cannot map unittest module to file: {test_id}")
    return "::".join([module_path.relative_to(ROOT).as_posix(), *rest])


def collect_unittest_ids() -> list[str]:
    suite = unittest.defaultTestLoader.discover(
        str(ROOT / "tests"), top_level_dir=str(ROOT)
    )
    return sorted(_unittest_id_to_pytest(test.id()) for test in _walk_suite(suite))


def collect_pytest_ids() -> tuple[list[str], str, int]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    ids = sorted(
        line.strip()
        for line in proc.stdout.splitlines()
        if line.startswith("tests/") and "::" in line
    )
    return ids, proc.stdout, proc.returncode


def run_command(
    name: str,
    command: list[str],
    out_dir: Path,
    *,
    resource_warning_gate: bool = False,
) -> dict:
    started = time.monotonic()
    log_path = out_dir / f"{name}.log"
    # Write directly to a regular file. Some legacy tests spawn short-lived
    # descendants that inherit stdout; PIPE-based capture can wait forever for
    # EOF even after the tested Python process has exited.
    with log_path.open("w", encoding="utf-8") as log_file:
        proc = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            check=False,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
    output = log_path.read_text(encoding="utf-8", errors="replace")
    warning_count = len(re.findall(r"ResourceWarning", output))
    passed = proc.returncode == 0 and (
        not resource_warning_gate or warning_count == 0
    )
    return {
        "name": name,
        "command": command,
        "returncode": proc.returncode,
        "resource_warning_count": warning_count,
        "duration_s": round(time.monotonic() - started, 3),
        "passed": passed,
        "log_file": log_path.name,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(ROOT / "s1_0_test_results"))
    parser.add_argument("--collect-only", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    unittest_ids = collect_unittest_ids()
    pytest_ids, pytest_collect_output, pytest_collect_rc = collect_pytest_ids()
    only_unittest = sorted(set(unittest_ids) - set(pytest_ids))
    only_pytest = sorted(set(pytest_ids) - set(unittest_ids))

    collection = {
        "schema_version": 1,
        "root": str(ROOT),
        "unittest_count": len(unittest_ids),
        "pytest_count": len(pytest_ids),
        "unittest_ids": unittest_ids,
        "pytest_ids": pytest_ids,
        "only_unittest": only_unittest,
        "only_pytest": only_pytest,
        "pytest_collect_returncode": pytest_collect_rc,
    }
    (out_dir / "TEST_COLLECTION_BASELINE.json").write_text(
        json.dumps(collection, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "pytest_collect.txt").write_text(
        pytest_collect_output, encoding="utf-8"
    )

    summary = [
        "# Test Collection Baseline",
        "",
        f"- unittest: {len(unittest_ids)}",
        f"- pytest: {len(pytest_ids)}",
        f"- only unittest: {len(only_unittest)}",
        f"- only pytest: {len(only_pytest)}",
        "",
        "## Only unittest",
        *(f"- `{item}`" for item in only_unittest),
        "",
        "## Only pytest",
        *(f"- `{item}`" for item in only_pytest),
        "",
    ]
    (out_dir / "TEST_COLLECTION_BASELINE.md").write_text(
        "\n".join(summary), encoding="utf-8"
    )

    if args.collect_only:
        return 0 if pytest_collect_rc == 0 and not only_unittest and not only_pytest else 1

    runs = [
        run_command(
            "unittest",
            [
                sys.executable,
                "-W",
                "always::ResourceWarning",
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-v",
            ],
            out_dir,
            resource_warning_gate=True,
        ),
        run_command("pytest", [sys.executable, "-m", "pytest", "-q"], out_dir),
    ]
    result = {
        "schema_version": 1,
        "collection_parity": (
            not only_unittest and not only_pytest and pytest_collect_rc == 0
        ),
        "runs": runs,
        "passed": (
            not only_unittest
            and not only_pytest
            and pytest_collect_rc == 0
            and all(run["passed"] for run in runs)
        ),
    }
    (out_dir / "TEST_GATE_RESULTS.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
