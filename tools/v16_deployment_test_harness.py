#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Non-destructive engineering harness for the V16 deployment contract.

The harness never installs or removes ZEC.  It creates isolated temporary roots,
exercises the shared state/bootstrap/dependency/port contracts and statically
verifies the real installer failure-order contract.  Real systemd/fresh-install
field acceptance remains a separate release gate on Raspberry Pi OS.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import socket
import tempfile
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import deployment_contract as dc  # noqa:E402


def _artifact(root: Path, absolute: str, content: str = "x") -> Path:
    p = root / absolute.lstrip("/")
    p.parent.mkdir(parents=True, exist_ok=True)
    if absolute.endswith("/zendure-controller"):
        p.mkdir(parents=True, exist_ok=True)
    else:
        p.write_text(content, encoding="utf-8")
    return p


def _supported_update_root(root: Path) -> None:
    target = _artifact(root, dc.TARGET)
    (target / "version.py").write_text(
        'APP_VERSION="15.0.3"\nAPP_BUILD_ID="v15.0.3-20260911"\n', encoding="utf-8"
    )
    (target / "config.json").write_text('{"WEB_PORT":8123}\n', encoding="utf-8")
    _artifact(root, "/etc/systemd/system/zendure-controller.service")
    _artifact(root, "/usr/local/sbin/zendure-controller-restart")
    _artifact(root, "/etc/sudoers.d/zendure-controller")


def run_harness() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def record(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        before = sorted(str(p.relative_to(root)) for p in root.rglob("*"))
        clean = dc.classify_installation(root=str(root), check_active_units=False)
        after = sorted(str(p.relative_to(root)) for p in root.rglob("*"))
        record("clean_fresh_install", clean["state"] == dc.STATE_CLEAN_FRESH_INSTALL, clean["state"])
        record("classifier_read_only", before == after, "temporary root unchanged")

        _supported_update_root(root)
        supported = dc.classify_installation(
            root=str(root), expected_update_version="15.0.3",
            expected_update_build="v15.0.3-20260911", check_active_units=False,
        )
        record("supported_update", supported["state"] == dc.STATE_SUPPORTED_UPDATE, supported["state"])

        (root / dc.TARGET.lstrip("/") / "config.json").unlink()
        partial = dc.classify_installation(
            root=str(root), expected_update_version="15.0.3",
            expected_update_build="v15.0.3-20260911", check_active_units=False,
        )
        record("partial_fail_closed", partial["state"] == dc.STATE_AMBIGUOUS, partial["state"])

    with tempfile.TemporaryDirectory() as td:
        b = Path(td) / dc.BOOTSTRAP_NAME
        dc.write_bootstrap(b, 8123)
        record("bootstrap_roundtrip", dc.load_bootstrap(b) == {"WEB_PORT": 8123})
        try:
            dc.validate_web_port(80)
        except ValueError:
            record("privileged_port_blocked", True)
        else:
            record("privileged_port_blocked", False)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0)); sock.listen(1)
    port = int(sock.getsockname()[1])
    try:
        record("port_conflict_detected", not dc.is_tcp_port_available(port, "127.0.0.1"), str(port))
    finally:
        sock.close()

    deps = dc.dependency_matrix(
        tool_lookup=lambda name: name != "rsync",
        module_lookup=lambda label, module: True,
    )
    record(
        "missing_dependency_has_install_hint",
        (not deps["ok"] and deps["missing_tools"] == ["rsync"] and "rsync" in deps["install_hint"]),
        deps["install_hint"],
    )
    dep_names = set(dc.REQUIRED_TOOLS) | {label for label, _ in dc.PYTHON_IMPORTS}
    record("broker_neutral_dependencies", "mosquitto" not in dep_names and "mosquitto.service" not in dep_names)

    installer = (ROOT / "tools/install_zendure_controller.sh").read_text(encoding="utf-8")
    error_start = installer.index("on_error()")
    error_end = installer.index("trap 'on_error", error_start)
    error_body = installer[error_start:error_end]
    pre = error_body.index('start_support_capture "pre_rollback"')
    rollback = min(i for i in (error_body.find("rollback_update", pre), error_body.find("rollback_fresh", pre)) if i >= 0)
    finalize = error_body.index("finalize_support_capture", rollback)
    record("failure_capture_before_rollback", pre < rollback < finalize)
    record("no_production_fault_injection_flag", "--fault-inject" not in installer and "--fail-phase" not in installer)

    failed = [c for c in checks if c["status"] != "PASS"]
    return {
        "format": "ZEC_V16_DEPLOYMENT_TEST_HARNESS_V1",
        "status": "PASS" if not failed else "FAIL",
        "check_count": len(checks),
        "failure_count": len(failed),
        "checks": checks,
        "limitations": [
            "No productive filesystem/systemd mutation is performed by this harness.",
            "Real Raspberry Pi OS fresh-install and update field tests remain mandatory before PRODUCTIVE-PASS.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="")
    args = ap.parse_args()
    report = run_harness()
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
