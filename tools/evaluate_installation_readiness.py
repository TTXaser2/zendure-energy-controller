#!/usr/bin/env python3
"""Classify post-install /ready payloads without weakening runtime readiness."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

EXPECTED_VERSION = "12.12.1"
EXPECTED_BUILD_ID = "v12.12.1-20260810"

_REQUIRED_HEALTHY_CHECKS = (
    "mqtt",
    "grid_measurement",
    "zendure_soc",
    "cross_charge_second_battery",
    "command_path",
    "command_state",
    "zendure_power_telemetry",
    "controller",
)
_ALLOWED_TRANSITIONAL_FAILURES = {"command_readback", "command_guards"}
_ALLOWED_LIMIT_MISMATCHES = {"INPUT_LIMIT", "OUTPUT_LIMIT"}
_ALLOWED_TRANSITIONAL_LIFECYCLES = {
    "IDLE",
    "COMMAND_STATE_VERIFYING",
    "ACTIVE_OBSERVING",
    "ACTIVE_BELOW_DIAGNOSTIC_THRESHOLD",
    "ACTIVE_EFFECTIVE",
    "ACTIVE_ACCEPTANCE_VERIFYING",
    "ACTIVE_ACCEPTANCE_LIMITED",
    "NEUTRALIZATION_OBSERVING",
    "NEUTRALIZATION_CONFIRMED",
    "RECOVERED",
}


def classify(payload: Mapping[str, Any]) -> tuple[str, str]:
    """Return READY, TRANSITIONAL, or REJECT plus a stable reason code."""
    if payload.get("version") != EXPECTED_VERSION or payload.get("build_id") != EXPECTED_BUILD_ID:
        return "REJECT", "IDENTITY"
    if payload.get("ready") is True:
        return "READY", "FULL_READY"

    checks = payload.get("checks")
    if not isinstance(checks, Mapping):
        return "REJECT", "CHECKS_MISSING"
    for name in _REQUIRED_HEALTHY_CHECKS:
        check = checks.get(name)
        if not isinstance(check, Mapping) or check.get("ok") is not True:
            return "REJECT", f"CRITICAL_CHECK_{name.upper()}"

    controller = checks["controller"]
    if controller.get("mode") == "SAFE_STATE":
        return "REJECT", "CONTROLLER_SAFE_STATE"
    if int(controller.get("consecutive_errors") or 0) != 0:
        return "REJECT", "CONTROLLER_ERRORS"

    command_state = checks["command_state"]
    if command_state.get("complete") is not True or command_state.get("static_invariant_ok") is not True:
        return "REJECT", "COMMAND_STATE_INCOMPLETE"

    failed_checks = set(payload.get("failed_checks") or [])
    if not failed_checks.issubset(_ALLOWED_TRANSITIONAL_FAILURES):
        return "REJECT", "UNSAFE_FAILED_CHECKS"

    readback = checks.get("command_readback") or {}
    mismatch_fields = {
        item.strip()
        for item in str(readback.get("mismatch_fields") or "").split(",")
        if item.strip() and item.strip() != "NONE"
    }
    if not mismatch_fields.issubset(_ALLOWED_LIMIT_MISMATCHES):
        return "REJECT", "NON_LIMIT_COMMAND_MISMATCH"

    guards = checks.get("command_guards") or {}
    if guards.get("not_effective_active") is True:
        return "REJECT", "COMMAND_NOT_EFFECTIVE"
    if guards.get("late_effect_guard_active") is True:
        return "REJECT", "LATE_EFFECT_GUARD"
    lifecycle = str(guards.get("lifecycle_state") or "")
    if lifecycle not in _ALLOWED_TRANSITIONAL_LIFECYCLES:
        return "REJECT", "UNSAFE_COMMAND_LIFECYCLE"

    return "TRANSITIONAL", "LIMIT_READBACK_CONVERGENCE"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: evaluate_installation_readiness.py READY_JSON", file=sys.stderr)
        return 2
    try:
        payload = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        classification, reason = classify(payload)
    except (OSError, ValueError, TypeError) as exc:
        print(f"REJECT:PAYLOAD_ERROR:{type(exc).__name__}")
        return 0
    print(f"{classification}:{reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
