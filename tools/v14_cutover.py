#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Transactional V14 Graph-Core V3 cutover helper.

The production contract is intentionally maintenance-window oriented:
- Measurement V4 remains the primary historical source.
- The existing graph DB is never migrated in place.
- A new V3 candidate is rebuilt and validated next to the target DB.
- Activation is an atomic os.replace() only after validation.
- Existing DB/WAL/SHM artifacts are backed up exactly and can be restored.
- Controller readiness is not evaluated here; graph-history readiness remains
  a separate diagnostic/runtime contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from graph_core_v3 import validate_graph_core  # noqa: E402
from graph_history_runtime import graph_history_runtime_status  # noqa: E402
from measurement_db import detect_measurement_db_backend, resolve_measurement_db_path  # noqa: E402
from tools.rebuild_graph_core_v3 import (  # noqa: E402
    _load_json,
    candidate_dirs,
    find_v4_files,
    rebuild,
)

STATE_FILE = "cutover_state.json"
ARTIFACTS = ("db", "wal", "shm")
MIN_FREE_MARGIN_BYTES = 512 * 1024 * 1024


@contextmanager
def _runtime_root_context(runtime_root: Optional[Path]):
    """Resolve relative runtime paths exactly as the installed service would.

    Installer/diagnostic tools execute package code from a staging directory.
    Relative settings such as MEASUREMENT_LOG_DIR="logs" are runtime-root
    relative, not package-root relative.  This explicit context prevents a
    staging CWD from redirecting verification to a non-existent shadow DB.
    """
    if runtime_root is None:
        yield None
        return
    root = runtime_root.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"RUNTIME_ROOT_MISSING:{root}")
    previous = Path.cwd()
    os.chdir(root)
    try:
        yield root
    finally:
        os.chdir(previous)


def _readonly_graph_connection(path: Path) -> sqlite3.Connection:
    """Open an existing graph store without schema/WAL mutation."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30.0)
    conn.execute("PRAGMA query_only=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def _artifact_paths(db_path: Path) -> Dict[str, Path]:
    return {
        "db": db_path,
        "wal": Path(str(db_path) + "-wal"),
        "shm": Path(str(db_path) + "-shm"),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _nearest_existing_parent(path: Path) -> Path:
    current = path
    while not current.exists() and current.parent != current:
        current = current.parent
    return current if current.exists() else Path("/")


def _quick_check(path: Path) -> str:
    if not path.exists() or path.stat().st_size == 0:
        return "missing"
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30.0)
        row = conn.execute("PRAGMA quick_check").fetchone()
        return str(row[0]) if row else "no_result"
    finally:
        if conn is not None:
            conn.close()


def _checkpoint_existing(path: Path) -> Dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {"attempted": False, "result": "missing"}
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = sqlite3.connect(str(path), timeout=30.0)
        row = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        return {"attempted": True, "result": list(row) if row else []}
    except Exception as exc:
        return {"attempted": True, "result": "error", "error": f"{type(exc).__name__}: {exc}"}
    finally:
        if conn is not None:
            conn.close()


def _fsync_file(path: Path) -> None:
    with path.open("rb") as fh:
        os.fsync(fh.fileno())


def _fsync_dir(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def preflight(config_path: Path, runtime_root: Optional[Path] = None) -> Dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    if not config_path.is_file():
        return {"status": "error", "reason": "CONFIG_MISSING", "config": str(config_path)}
    with _runtime_root_context(runtime_root) as active_root:
        config = _load_json(config_path)
        db_path = Path(resolve_measurement_db_path(dict(config))).expanduser().resolve()
        dirs = candidate_dirs(config, config_path, [])
        result = _preflight_resolved(config_path, config, db_path, dirs)
        result["runtime_root"] = str(active_root) if active_root is not None else str(Path.cwd())
        return result


def _preflight_resolved(config_path: Path, config: Dict[str, Any], db_path: Path, dirs) -> Dict[str, Any]:
    files = find_v4_files(dirs, [])
    source_bytes = sum(p.stat().st_size for p in files)
    artifacts = _artifact_paths(db_path)
    existing_bytes = sum(p.stat().st_size for p in artifacts.values() if p.exists())
    parent = _nearest_existing_parent(db_path.parent)
    disk = shutil.disk_usage(parent)
    # This is a fail-closed floor, not a prediction of the final V3 size.  It
    # ensures room for at least one source-sized/replacement candidate plus the
    # existing DB footprint and a fixed operational margin.  ENOSPC during the
    # rebuild still leaves the old DB untouched because activation is atomic.
    rebuild_floor = max(source_bytes, existing_bytes)
    required_free = rebuild_floor + existing_bytes + MIN_FREE_MARGIN_BYTES
    detection = detect_measurement_db_backend(str(db_path))
    quick = _quick_check(db_path)
    writable_parent = os.access(parent, os.W_OK)
    reasons = []
    if not files:
        reasons.append("NO_V4_FILES")
    if not writable_parent:
        reasons.append("DB_PARENT_NOT_WRITABLE")
    if disk.free < required_free:
        reasons.append("INSUFFICIENT_FREE_SPACE_FLOOR")
    if detection.get("backend") == "unknown":
        reasons.append("EXISTING_DB_UNKNOWN_SCHEMA")
    if quick not in {"ok", "missing"}:
        reasons.append("EXISTING_DB_QUICK_CHECK_FAILED")
    return {
        "status": "ok" if not reasons else "error",
        "reason": "READY" if not reasons else reasons[0],
        "reasons": reasons,
        "config": str(config_path),
        "db_path": str(db_path),
        "db_backend": detection.get("backend"),
        "db_schema_version": detection.get("schema_version"),
        "db_quick_check": quick,
        "existing_db_artifact_bytes": existing_bytes,
        "v4_file_count": len(files),
        "v4_source_bytes": source_bytes,
        "v4_directories": [str(p) for p in dirs],
        "free_bytes": disk.free,
        "required_free_floor_bytes": required_free,
        "free_space_formula": "max(v4_source_bytes,existing_db_artifact_bytes)+existing_db_artifact_bytes+512MiB",
        "db_parent": str(db_path.parent),
        "writable_existing_parent": str(parent),
        "db_parent_writable": writable_parent,
        "controller_readiness_impact": "NONE",
        "measurement_v4_role": "PRIMARY_REBUILD_SOURCE",
    }


def _write_state(backup_dir: Path, state: Mapping[str, Any]) -> None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    tmp = backup_dir / (STATE_FILE + ".tmp")
    tmp.write_text(json.dumps(dict(state), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, backup_dir / STATE_FILE)
    _fsync_dir(backup_dir)


def _backup_existing(db_path: Path, backup_dir: Path) -> Dict[str, Any]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = _checkpoint_existing(db_path)
    artifacts_state: Dict[str, Any] = {}
    for key, src in _artifact_paths(db_path).items():
        dst = backup_dir / src.name
        if src.exists():
            source_size = src.stat().st_size
            source_sha256 = _sha256(src)
            shutil.copy2(src, dst)
            backup_size = dst.stat().st_size
            backup_sha256 = _sha256(dst)
            if backup_size != source_size or backup_sha256 != source_sha256:
                raise IOError(f"CUTOVER_BACKUP_VERIFY_FAILED:{key}")
            artifacts_state[key] = {
                "present": True,
                "source": str(src),
                "backup": str(dst),
                "size": source_size,
                "sha256": source_sha256,
                "backup_verified": True,
            }
        else:
            artifacts_state[key] = {
                "present": False, "source": str(src), "backup": str(dst),
                "size": 0, "sha256": "", "backup_verified": True,
            }
    state = {
        "format": "ZEC_V14_GRAPH_CUTOVER_STATE_V1",
        "created_epoch_s": time.time(),
        "target_db": str(db_path),
        "checkpoint": checkpoint,
        "artifacts": artifacts_state,
        "activation": "NOT_STARTED",
    }
    _write_state(backup_dir, state)
    return state


def restore(backup_dir: Path) -> Dict[str, Any]:
    backup_dir = backup_dir.expanduser().resolve()
    state_path = backup_dir / STATE_FILE
    if not state_path.is_file():
        return {"status": "error", "reason": "CUTOVER_STATE_MISSING", "backup_dir": str(backup_dir)}
    state = json.loads(state_path.read_text(encoding="utf-8"))
    db_path = Path(state["target_db"])
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Phase 1: validate every required backup before touching the active DB
    # generation. A corrupt/missing rollback artifact must fail closed while
    # leaving the currently active store untouched.
    plan = []
    for key in ARTIFACTS:
        info = dict(state.get("artifacts", {}).get(key) or {})
        target = Path(str(info.get("source") or _artifact_paths(db_path)[key]))
        backup = Path(str(info.get("backup") or backup_dir / target.name))
        expected_size = int(info.get("size") or 0)
        expected_sha256 = str(info.get("sha256") or "")
        present = bool(info.get("present"))
        if present:
            if not backup.is_file():
                return {"status": "error", "reason": "BACKUP_ARTIFACT_MISSING", "artifact": key, "path": str(backup)}
            if backup.stat().st_size != expected_size or not expected_sha256 or _sha256(backup) != expected_sha256:
                return {"status": "error", "reason": "BACKUP_ARTIFACT_VERIFY_FAILED", "artifact": key, "path": str(backup)}
        plan.append((key, target, backup, present, expected_size, expected_sha256))

    # Phase 2: prepare and verify all replacement bytes next to their targets.
    # No active artifact is changed while this preparation is in progress.
    prepared: Dict[str, Path] = {}
    try:
        for key, target, backup, present, expected_size, expected_sha256 in plan:
            if not present:
                continue
            tmp = target.parent / f".{target.name}.zec-v14-restore-{os.getpid()}-{key}.tmp"
            try:
                tmp.unlink()
            except FileNotFoundError:
                pass
            shutil.copy2(backup, tmp)
            if tmp.stat().st_size != expected_size or _sha256(tmp) != expected_sha256:
                raise IOError(f"RESTORE_PREPARE_VERIFY_FAILED:{key}")
            _fsync_file(tmp)
            prepared[key] = tmp

        # Phase 3: service is expected to be stopped by the installer. Switch
        # the complete DB generation only after all restore bytes are proven.
        for _key, target, _backup, _present, _size, _sha in plan:
            try:
                target.unlink()
            except FileNotFoundError:
                pass
        restored = []
        for key, target, _backup, present, expected_size, expected_sha256 in plan:
            if not present:
                continue
            os.replace(prepared[key], target)
            prepared.pop(key, None)
            if target.stat().st_size != expected_size or _sha256(target) != expected_sha256:
                return {"status": "error", "reason": "RESTORED_ARTIFACT_VERIFY_FAILED", "artifact": key, "path": str(target)}
            restored.append(str(target))
        _fsync_dir(db_path.parent)
    except Exception as exc:
        return {"status": "error", "reason": type(exc).__name__, "error": str(exc), "target_db": str(db_path)}
    finally:
        for tmp in prepared.values():
            try:
                tmp.unlink()
            except FileNotFoundError:
                pass

    state["activation"] = "ROLLED_BACK"
    state["rolled_back_epoch_s"] = time.time()
    _write_state(backup_dir, state)
    return {"status": "ok", "reason": "RESTORED", "target_db": str(db_path), "restored": restored}


def verify(config_path: Path, runtime_root: Optional[Path] = None) -> Dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    with _runtime_root_context(runtime_root) as active_root:
        config = _load_json(config_path)
        db_path = Path(resolve_measurement_db_path(dict(config))).expanduser().resolve()
        detection = detect_measurement_db_backend(str(db_path))
        result: Dict[str, Any] = {
            "status": "error",
            "db_path": str(db_path),
            "db_backend": detection.get("backend"),
            "db_schema_version": detection.get("schema_version"),
            "quick_check": _quick_check(db_path),
            "controller_readiness_impact": "NONE",
            "runtime_root": str(active_root) if active_root is not None else str(Path.cwd()),
            "verification_mode": "READ_ONLY",
        }
        if detection.get("backend") != "v3":
            result["reason"] = "NOT_V3"
            return result
        conn = _readonly_graph_connection(db_path)
        try:
            validation = validate_graph_core(conn)
        finally:
            conn.close()
        runtime = graph_history_runtime_status(config)
        result.update({"validation": validation, "runtime": runtime})
        if validation.get("integrity_check") != "ok":
            result["reason"] = "V3_INTEGRITY_FAILED"
            return result
        if runtime.get("read_mode") != "V3_NATIVE" or not runtime.get("workspace_ready"):
            result["reason"] = "V3_RUNTIME_NOT_READY"
            return result
        result.update({"status": "ok", "reason": "V3_NATIVE_READY"})
        return result


def rebuild_and_cutover(config_path: Path, backup_dir: Path, *, report_path: Optional[Path] = None) -> Dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    backup_dir = backup_dir.expanduser().resolve()
    pf = preflight(config_path)
    if pf.get("status") != "ok":
        return {"status": "error", "reason": "PREFLIGHT_FAILED", "preflight": pf}
    config = _load_json(config_path)
    db_path = Path(pf["db_path"])
    files = find_v4_files(candidate_dirs(config, config_path, []), [])
    state = _backup_existing(db_path, backup_dir)
    legacy = db_path if db_path.exists() and detect_measurement_db_backend(str(db_path)).get("backend") in {"v2", "v3"} else None
    candidate = db_path.parent / f".{db_path.name}.v14-rebuild-{os.getpid()}-{int(time.time())}.tmp"
    for suffix in ("", "-wal", "-shm"):
        try:
            Path(str(candidate) + suffix).unlink()
        except FileNotFoundError:
            pass
    result: Dict[str, Any]
    activated = False
    try:
        rebuilt = rebuild(
            files,
            candidate,
            legacy_db=legacy,
            reset=True,
            batch_size=5000,
            progress_every=100000,
            include_source_sha256=False,
            entity_config=config,
        )
        if rebuilt.get("status") != "ok" or (rebuilt.get("validation") or {}).get("integrity_check") != "ok":
            raise RuntimeError("REBUILD_VALIDATION_FAILED")
        if rebuilt.get("source_errors"):
            raise RuntimeError("REBUILD_SOURCE_ERRORS")
        if int(rebuilt.get("files_ok") or 0) != int(rebuilt.get("files") or 0):
            raise RuntimeError("REBUILD_INCOMPLETE_SOURCE_SET")
        if int(rebuilt.get("rows_imported") or 0) <= 0:
            raise RuntimeError("REBUILD_NO_ROWS_IMPORTED")
        candidate_detection = detect_measurement_db_backend(str(candidate))
        if candidate_detection.get("backend") != "v3":
            raise RuntimeError("REBUILD_NOT_V3")
        _fsync_file(candidate)
        # Sidecars belong to the old DB generation and must never survive the
        # atomic replacement. They are already represented in the rollback backup.
        for sidecar in (Path(str(db_path) + "-wal"), Path(str(db_path) + "-shm")):
            try:
                sidecar.unlink()
            except FileNotFoundError:
                pass
        os.replace(candidate, db_path)
        _fsync_dir(db_path.parent)
        activated = True
        state["activation"] = "ACTIVATED_PENDING_VERIFY"
        state["activated_epoch_s"] = time.time()
        _write_state(backup_dir, state)
        checked = verify(config_path)
        if checked.get("status") != "ok":
            raise RuntimeError(f"POST_ACTIVATION_VERIFY_FAILED:{checked.get('reason')}")
        state["activation"] = "VERIFIED"
        state["verified_epoch_s"] = time.time()
        _write_state(backup_dir, state)
        result = {
            "status": "ok",
            "reason": "CUTOVER_VERIFIED",
            "db_path": str(db_path),
            "backup_dir": str(backup_dir),
            "source_v4_files": len(files),
            "source_v4_bytes": sum(p.stat().st_size for p in files),
            "previous_backend": pf.get("db_backend"),
            "previous_schema_version": pf.get("db_schema_version"),
            "rebuild": rebuilt,
            "verify": checked,
            "controller_readiness_impact": "NONE",
        }
    except Exception as exc:
        rollback_result = restore(backup_dir) if activated else {"status": "not_needed", "reason": "TARGET_NOT_ACTIVATED"}
        result = {
            "status": "error",
            "reason": type(exc).__name__,
            "error": str(exc),
            "db_path": str(db_path),
            "backup_dir": str(backup_dir),
            "activated_before_error": activated,
            "rollback": rollback_result,
        }
    finally:
        for suffix in ("", "-wal", "-shm"):
            try:
                Path(str(candidate) + suffix).unlink()
            except FileNotFoundError:
                pass
    if report_path is not None:
        report_path = report_path.expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def _emit(result: Mapping[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(dict(result), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{result.get('status')}:{result.get('reason')}")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ZEC V14 transactional Graph-Core cutover")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("preflight", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--config", required=True)
        p.add_argument("--runtime-root", default="")
        p.add_argument("--json", action="store_true")
    p = sub.add_parser("rebuild")
    p.add_argument("--config", required=True)
    p.add_argument("--backup-dir", required=True)
    p.add_argument("--report", default="")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("restore")
    p.add_argument("--backup-dir", required=True)
    p.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if args.command == "preflight":
        result = preflight(Path(args.config), Path(args.runtime_root) if args.runtime_root else None)
    elif args.command == "verify":
        result = verify(Path(args.config), Path(args.runtime_root) if args.runtime_root else None)
    elif args.command == "rebuild":
        result = rebuild_and_cutover(
            Path(args.config), Path(args.backup_dir),
            report_path=Path(args.report) if args.report else None,
        )
    else:
        result = restore(Path(args.backup_dir))
    _emit(result, bool(args.json))
    return 0 if result.get("status") == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
