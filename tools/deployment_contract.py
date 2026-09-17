#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared deployment-state, endpoint and preflight helpers for ZEC V16.

This module is intentionally stdlib-only.  Installer, uninstaller, diagnostics and
server-side WEB_PORT validation share these semantics so CLEAN_FRESH_INSTALL is a
single contract instead of several slightly different shell interpretations.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

STATE_SUPPORTED_UPDATE = "SUPPORTED_UPDATE"
STATE_CLEAN_FRESH_INSTALL = "CLEAN_FRESH_INSTALL"
STATE_AMBIGUOUS = "AMBIGUOUS_OR_PARTIAL_INSTALL"

TARGET = "/opt/zendure-controller"
BOOTSTRAP_NAME = ".zec_first_install_bootstrap.json"
BOOTSTRAP_FORMAT = "ZEC_FIRST_INSTALL_BOOTSTRAP_V1"
DEFAULT_WEB_PORT = 8080
MIN_WEB_PORT = 1024
MAX_WEB_PORT = 65535

ACTIVE_ARTIFACTS: Tuple[str, ...] = (
    TARGET,
    "/etc/systemd/system/zendure-controller.service",
    "/etc/systemd/system/zendure-replay.service",
    "/etc/systemd/system/zendure-status-preview.service",
    "/usr/local/sbin/zendure-controller-restart",
    "/etc/sudoers.d/zendure-controller",
)
ACTIVE_UNITS: Tuple[str, ...] = (
    "zendure-controller.service",
    "zendure-replay.service",
    "zendure-status-preview.service",
)
REQUIRED_TOOLS: Tuple[str, ...] = (
    "python3", "sudo", "systemctl", "unzip", "rsync", "tar", "curl",
    "sha256sum", "install", "find", "visudo",
)
PYTHON_IMPORTS: Tuple[Tuple[str, str], ...] = (
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("requests", "requests"),
    ("paho-mqtt", "paho.mqtt.client"),
    ("python-multipart", "multipart"),
)
APT_TOOL_PACKAGES = {
    "unzip": "unzip", "rsync": "rsync", "tar": "tar", "curl": "curl",
    "sha256sum": "coreutils", "install": "coreutils", "find": "findutils",
    "visudo": "sudo", "sudo": "sudo", "systemctl": "systemd", "python3": "python3",
}
APT_PYTHON_PACKAGES = {
    "fastapi": "python3-fastapi",
    "uvicorn": "python3-uvicorn",
    "requests": "python3-requests",
    "paho-mqtt": "python3-paho-mqtt",
    "python-multipart": "python3-multipart",
}


def rooted(root: str | os.PathLike[str], absolute_path: str) -> Path:
    r = Path(root)
    if str(r) == "/":
        return Path(absolute_path)
    return r / absolute_path.lstrip("/")


def _version_value(text: str, name: str) -> str:
    match = re.search(rf'^{re.escape(name)}\s*=\s*["\']([^"\']*)["\']', text, flags=re.M)
    return match.group(1) if match else ""


def read_identity(version_py: Path) -> Dict[str, str]:
    if not version_py.is_file():
        return {"version": "", "build_id": "", "label": ""}
    try:
        text = version_py.read_text(encoding="utf-8")
    except OSError:
        return {"version": "", "build_id": "", "label": ""}
    return {
        "version": _version_value(text, "APP_VERSION"),
        "build_id": _version_value(text, "APP_BUILD_ID"),
        "label": _version_value(text, "APP_VERSION_LABEL"),
    }


def verify_release_identity(
    version_py: Path, *, expected_version: str, expected_build: str,
) -> Dict[str, Any]:
    identity = read_identity(version_py)
    ok = bool(
        expected_version
        and expected_build
        and identity["version"] == expected_version
        and identity["build_id"] == expected_build
    )
    return {
        "ok": ok,
        "version_file": str(version_py),
        "expected_version": expected_version,
        "expected_build_id": expected_build,
        "identity": identity,
    }


def _unit_active(unit: str) -> bool:
    if not shutil.which("systemctl"):
        return False
    try:
        return subprocess.run(
            ["systemctl", "is-active", "--quiet", unit],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3,
        ).returncode == 0
    except Exception:
        return False


def classify_installation(
    *, root: str = "/", expected_update_version: str = "", expected_update_build: str = "",
    check_active_units: bool = True,
) -> Dict[str, Any]:
    artifact_state = {path: rooted(root, path).exists() for path in ACTIVE_ARTIFACTS}
    target = rooted(root, TARGET)
    identity = read_identity(target / "version.py")
    config_exists = (target / "config.json").is_file()
    unit_active = {
        unit: (_unit_active(unit) if check_active_units and root == "/" else False)
        for unit in ACTIVE_UNITS
    }
    any_artifact = any(artifact_state.values()) or any(unit_active.values())
    if not any_artifact:
        state = STATE_CLEAN_FRESH_INSTALL
        reason = "NO_ACTIVE_ZEC_ARTIFACTS"
    else:
        required_update_artifacts = (
            artifact_state[TARGET]
            and artifact_state["/etc/systemd/system/zendure-controller.service"]
            and artifact_state["/usr/local/sbin/zendure-controller-restart"]
            and artifact_state["/etc/sudoers.d/zendure-controller"]
        )
        identity_ok = bool(
            expected_update_version
            and expected_update_build
            and identity["version"] == expected_update_version
            and identity["build_id"] == expected_update_build
        )
        if required_update_artifacts and config_exists and identity_ok:
            state = STATE_SUPPORTED_UPDATE
            reason = "EXACT_SUPPORTED_SOURCE"
        else:
            state = STATE_AMBIGUOUS
            reason = "PARTIAL_OR_UNSUPPORTED_ZEC_STATE"
    found = [path for path, present in artifact_state.items() if present]
    found += [f"unit-active:{unit}" for unit, active in unit_active.items() if active]
    return {
        "state": state,
        "reason": reason,
        "root": str(root),
        "identity": identity,
        "config_exists": config_exists,
        "artifacts": artifact_state,
        "active_units": unit_active,
        "found": found,
    }


def validate_web_port(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("WEB_PORT_BOOL_INVALID")
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("WEB_PORT_NOT_INTEGER") from exc
    if not MIN_WEB_PORT <= port <= MAX_WEB_PORT:
        raise ValueError(f"WEB_PORT_OUT_OF_RANGE:{MIN_WEB_PORT}..{MAX_WEB_PORT}")
    return port


def is_tcp_port_available(port: int, host: str = "0.0.0.0") -> bool:
    port = validate_web_port(port)
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        sock.settimeout(1.0)
        sock.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def load_bootstrap(path: str | os.PathLike[str]) -> Dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError("FIRST_INSTALL_BOOTSTRAP_INVALID_JSON") from exc
    if not isinstance(data, dict) or set(data) != {"format", "values"}:
        raise ValueError("FIRST_INSTALL_BOOTSTRAP_INVALID_ROOT")
    if data.get("format") != BOOTSTRAP_FORMAT or not isinstance(data.get("values"), dict):
        raise ValueError("FIRST_INSTALL_BOOTSTRAP_INVALID_FORMAT")
    values = dict(data["values"])
    if set(values) - {"WEB_PORT"}:
        raise ValueError("FIRST_INSTALL_BOOTSTRAP_KEY_NOT_ALLOWED")
    if "WEB_PORT" in values:
        values["WEB_PORT"] = validate_web_port(values["WEB_PORT"])
    return values


def write_bootstrap(path: str | os.PathLike[str], web_port: int) -> None:
    port = validate_web_port(web_port)
    p = Path(path)
    payload = {"format": BOOTSTRAP_FORMAT, "values": {"WEB_PORT": port}}
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)


def _read_config_port(config_path: Path) -> Optional[int]:
    if not config_path.is_file():
        return None
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return validate_web_port(data.get("WEB_PORT", DEFAULT_WEB_PORT))
    except Exception:
        return None


def effective_local_web_endpoint(
    *, target: str = TARGET, config_path: Optional[str] = None, bootstrap_path: Optional[str] = None,
) -> Dict[str, Any]:
    target_path = Path(target)
    cfg = Path(config_path) if config_path else target_path / "config.json"
    bootstrap = Path(bootstrap_path) if bootstrap_path else target_path / BOOTSTRAP_NAME
    port = _read_config_port(cfg)
    source = "config"
    if port is None:
        try:
            values = load_bootstrap(bootstrap)
            port = values.get("WEB_PORT")
        except ValueError:
            port = None
        source = "first_install_bootstrap" if port is not None else "default"
    if port is None:
        port = DEFAULT_WEB_PORT
    return {"host": "127.0.0.1", "port": int(port), "base_url": f"http://127.0.0.1:{int(port)}", "source": source}


def dependency_matrix(*, tool_lookup=None, module_lookup=None) -> Dict[str, Any]:
    tool_lookup = tool_lookup or (lambda name: bool(shutil.which(name)))
    def default_module_lookup(label: str, module: str) -> bool:
        try:
            return importlib.util.find_spec(module) is not None
        except (ImportError, AttributeError, ValueError):
            return False
    module_lookup = module_lookup or default_module_lookup
    tools = {name: bool(tool_lookup(name)) for name in REQUIRED_TOOLS}
    python = {}
    for label, module in PYTHON_IMPORTS:
        try:
            ok = bool(module_lookup(label, module))
        except Exception:
            ok = False
        python[label] = ok
    missing_tools = [k for k, ok in tools.items() if not ok]
    missing_python = [k for k, ok in python.items() if not ok]
    packages = []
    for name in missing_tools:
        pkg = APT_TOOL_PACKAGES.get(name)
        if pkg and pkg not in packages:
            packages.append(pkg)
    for name in missing_python:
        pkg = APT_PYTHON_PACKAGES.get(name)
        if pkg and pkg not in packages:
            packages.append(pkg)
    command = ""
    if packages:
        command = "sudo apt update && sudo apt install -y " + " ".join(packages)
    return {
        "tools": tools,
        "python_imports": python,
        "missing_tools": missing_tools,
        "missing_python": missing_python,
        "install_hint": command,
        "ok": not missing_tools and not missing_python,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p_class = sub.add_parser("classify")
    p_class.add_argument("--root", default="/")
    p_class.add_argument("--expected-version", default="")
    p_class.add_argument("--expected-build", default="")
    p_class.add_argument("--no-active-unit-check", action="store_true")
    p_class.add_argument("--json", action="store_true")
    p_ep = sub.add_parser("endpoint")
    p_ep.add_argument("--target", default=TARGET)
    p_ep.add_argument("--json", action="store_true")
    p_dep = sub.add_parser("dependencies")
    p_dep.add_argument("--json", action="store_true")
    p_identity = sub.add_parser("identity")
    p_identity.add_argument("--version-file", required=True)
    p_identity.add_argument("--expected-version", required=True)
    p_identity.add_argument("--expected-build", required=True)
    p_identity.add_argument("--json", action="store_true")
    p_port = sub.add_parser("port-check")
    p_port.add_argument("port", type=int)
    p_port.add_argument("--host", default="0.0.0.0")
    p_port.add_argument("--json", action="store_true")
    p_bw = sub.add_parser("bootstrap-write")
    p_bw.add_argument("--path", required=True)
    p_bw.add_argument("--web-port", type=int, required=True)
    p_bw.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "classify":
        result = classify_installation(
            root=args.root, expected_update_version=args.expected_version,
            expected_update_build=args.expected_build,
            check_active_units=not args.no_active_unit_check,
        )
    elif args.command == "endpoint":
        result = effective_local_web_endpoint(target=args.target)
    elif args.command == "dependencies":
        result = dependency_matrix()
    elif args.command == "identity":
        result = verify_release_identity(
            Path(args.version_file), expected_version=args.expected_version,
            expected_build=args.expected_build,
        )
    elif args.command == "bootstrap-write":
        try:
            write_bootstrap(args.path, args.web_port)
            result = {"ok": True, "path": args.path, "WEB_PORT": validate_web_port(args.web_port)}
        except (OSError, ValueError) as exc:
            result = {"ok": False, "path": args.path, "error": str(exc)}
    else:
        try:
            port = validate_web_port(args.port)
            available = is_tcp_port_available(port, args.host)
            result = {"port": port, "host": args.host, "available": available, "ok": available}
        except ValueError as exc:
            result = {"port": args.port, "host": args.host, "available": False, "ok": False, "error": str(exc)}

    if getattr(args, "json", False):
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for key, value in result.items():
            print(f"{key}={value}")
    return 0 if result.get("ok", True) is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())
