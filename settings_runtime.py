# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>

"""RC20 runtime contract for configured/effective settings and Last-Good recovery.

This module deliberately has no MQTT, controller, HTTP or database dependency.  It owns
only configuration parsing, revisions, atomic persistence, reload state and the bounded
A/B Last-Good store.
"""
from __future__ import annotations

import grp
import hashlib
import json
import math
import os
import pwd
import secrets
import stat
import tempfile
import threading
import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from settings_apply_policy import ApplyPlan, build_apply_plan
from settings_registry import (
    SETTINGS,
    SETTINGS_BY_KEY,
    ApplyClass,
    Editability,
    SettingSpec,
)
from settings_validation import (
    ParsedCandidate,
    ValidationContext,
    ValidationIssue,
    ValidationSeverity,
    parse_candidate,
    validate_candidate,
)

CONFIG_RUNTIME_SCHEMA_VERSION = "1"
LAST_GOOD_POINTER_VERSION = 1
LAST_GOOD_MANIFEST_VERSION = 1
STABLE_READY_SECONDS = 300.0

STARTUP_NORMAL = "NORMAL"
STARTUP_RECOVERY_WAITING = "RECOVERY_LAST_GOOD_WAITING_PREFLIGHT"
STARTUP_RECOVERY_ACTIVE = "RECOVERY_LAST_GOOD_ACTIVE"
STARTUP_CONFIG_ERROR = "CONFIG_ERROR_DIAGNOSTIC_ONLY"
STARTUP_FIRST_INSTALL = "FIRST_INSTALL_SETUP"

CONFIG_HEALTH_VALID = "valid"
CONFIG_HEALTH_INVALID_RUNTIME = "invalid_runtime"
CONFIG_HEALTH_INVALID_STARTUP = "invalid_startup"
CONFIG_HEALTH_MISSING = "missing"


@dataclass(frozen=True)
class FileFingerprint:
    device: int
    inode: int
    size: int
    mtime_ns: int

    @classmethod
    def from_stat(cls, value: os.stat_result) -> "FileFingerprint":
        return cls(value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)

    def as_dict(self) -> Dict[str, int]:
        return {
            "st_dev": self.device,
            "st_ino": self.inode,
            "st_size": self.size,
            "st_mtime_ns": self.mtime_ns,
        }


@dataclass(frozen=True)
class RuntimeIssue:
    code: str
    severity: str
    keys: Tuple[str, ...] = ()
    message_id: str = ""
    params: Mapping[str, Any] = field(default_factory=dict)
    source: str = "runtime"
    blocking: bool = True

    def as_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "keys": list(self.keys),
            "message_id": self.message_id or self.code,
            "params": dict(self.params),
            "source": self.source,
            "blocking": self.blocking,
        }


@dataclass(frozen=True)
class CandidateResult:
    # Full typed configured view, including inherited in-memory defaults.
    configured: Mapping[str, Any]
    # Exact typed object eligible for persistence. Missing optional/defaulted
    # keys stay absent so GET/preview/commit never materialise defaults silently.
    persisted: Mapping[str, Any]
    known: Mapping[str, Any]
    unknown: Mapping[str, Any]
    inherited_defaults: Tuple[str, ...]
    issues: Tuple[ValidationIssue, ...]
    typed_revision: str

    @property
    def valid(self) -> bool:
        return not any(issue.blocking for issue in self.issues)


@dataclass(frozen=True)
class StableReadResult:
    status: str
    data: Optional[bytes]
    fingerprint: Optional[FileFingerprint]
    revision: Optional[str]
    issue: Optional[RuntimeIssue] = None


@dataclass(frozen=True)
class LastGoodSlot:
    slot: str
    valid: bool
    eligible: bool
    generation_id: int = 0
    typed_revision: str = ""
    config_hash: str = ""
    config: Mapping[str, Any] = field(default_factory=dict)
    manifest: Mapping[str, Any] = field(default_factory=dict)
    issues: Tuple[RuntimeIssue, ...] = ()

    def as_status(self) -> Dict[str, Any]:
        return {
            "slot": self.slot,
            "valid": self.valid,
            "eligible": self.eligible,
            "generation_id": self.generation_id,
            "typed_revision": self.typed_revision,
            "config_hash": self.config_hash,
            "issues": [issue.as_dict() for issue in self.issues],
        }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def pretty_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(dict(value), ensure_ascii=False, indent=4) + "\n").encode("utf-8")


def typed_revision(value: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(value))



# S1.7 legacy authority matrix. Keys marked ``remove_*`` in the generated
# registry are not silently retained as active runtime settings. Four values
# still consumed by RC19 production code remain explicit compatibility inputs
# for RC20 and are scheduled for a later, separately tested removal.
LEGACY_RUNTIME_COMPAT_KEYS = frozenset({
    "HARVEST_CAPACITY_WEIGHTING_MODE",
    "MEASUREMENT_LOG_BACKUP_COUNT",
    "MEASUREMENT_LOG_ESTIMATED_ROW_BYTES",
    "MEASUREMENT_LOG_FALLBACK_BACKUP_COUNT",
})
LEGACY_REMOVE_NO_EFFECT_KEYS = frozenset({
    "HARVEST_IMPORT_EXIT_CONFIRM_SECONDS",
    "HARVEST_IMPORT_REDUCE_CONFIRM_SECONDS",
    "HARVEST_PRIMARY_BELOW_FLOOR_CONFIRM_SECONDS",
    "HARVEST_PRIMARY_RESTART_CONFIRM_SECONDS",
    "CROSS_CHARGE_RESERVE_W",
    "MEASUREMENT_DB_MAX_QUEUE_ROWS",
})
LEGACY_MIGRATION_MATRIX = {
    "ZENDURE_BATTERY_CAPACITY_KWH": "transform_to_ZENDURE_BATTERY_CAPACITY_WH_then_remove",
    "SMA_DISCHARGE_BLOCK_W": "transform_to_CROSS_CHARGE_SIGNIFICANT_W_then_remove",
    **{key: "remove_no_runtime_effect" for key in LEGACY_REMOVE_NO_EFFECT_KEYS},
    **{key: "preserve_runtime_compatibility_until_S2" for key in LEGACY_RUNTIME_COMPAT_KEYS},
}


def _active_registry_specs():
    for spec in SETTINGS:
        if spec.lifecycle.startswith("remove_") and spec.key not in LEGACY_RUNTIME_COMPAT_KEYS:
            continue
        yield spec

def registry_defaults(*, new_install: bool = False) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for spec in _active_registry_specs():
        if new_install:
            value = spec.bootstrap_value
        else:
            value = spec.default_rc19
            if value is None and spec.origin != "RC19":
                value = spec.default_new_install
        result[spec.key] = value
    return result


def configured_view_from_raw(raw: Mapping[str, Any], *, new_install: bool = False) -> Tuple[Dict[str, Any], Tuple[str, ...]]:
    """Build the UI-facing configured view without coercing invalid values.

    The exact bytes/object from the primary file remain authoritative for CAS and
    repair. Missing known keys are represented by inherited defaults, while every
    explicitly present value -- including an invalid one -- remains visible.
    """
    defaults = registry_defaults(new_install=new_install)
    view: Dict[str, Any] = {}
    inherited = []
    for spec in _active_registry_specs():
        if spec.key in raw:
            view[spec.key] = raw[spec.key]
        else:
            view[spec.key] = defaults.get(spec.key)
            inherited.append(spec.key)
    view.update({key: value for key, value in raw.items() if key not in SETTINGS_BY_KEY})
    return view, tuple(inherited)


def _expected_pi_owner() -> Tuple[int, int]:
    """Resolve the production owner, with a test/development-safe fallback."""
    try:
        uid = int(pwd.getpwnam("pi").pw_uid)
    except KeyError:
        uid = int(os.geteuid())
    try:
        gid = int(grp.getgrnam("pi").gr_gid)
    except KeyError:
        gid = int(os.getegid())
    return uid, gid


def migrate_rc19_to_rc20(raw: Mapping[str, Any]) -> Tuple[Dict[str, Any], Tuple[str, ...]]:
    """Exact and idempotent RC19 -> RC20 config migration.

    RC20 keeps all productive RC19 values and unknown extension keys. It does
    not materialise defaults and does not introduce target-only settings from
    later release stages. The unsafe free-form restart command is removed, two
    legacy authorities are transformed only when valid and conflict-free, and
    keys proven to have no runtime effect are removed explicitly.
    """
    if not isinstance(raw, Mapping):
        raise ValueError("RC19 config root must be a JSON object")
    result = dict(raw)
    steps = []

    if "SERVICE_RESTART_COMMAND" in result:
        result.pop("SERVICE_RESTART_COMMAND", None)
        steps.append("MIG-RC20-REMOVE-FREE-RESTART-COMMAND")

    # WH is the canonical capacity key. Transform-and-remove is performed only
    # when the legacy value is valid and non-conflicting. A conflict remains
    # visible to strict validation and is never silently repaired.
    if "ZENDURE_BATTERY_CAPACITY_KWH" in result:
        kwh = result.get("ZENDURE_BATTERY_CAPACITY_KWH")

        # RC19 carried this compatibility key in normal configs even when it
        # was unset (JSON null) and its runtime float codec also accepted
        # numeric strings. Preserve that exact source contract: null and blank
        # mean "unset", while finite positive JSON numbers and numeric strings
        # are transformed. Other values remain a fail-closed migration error.
        legacy_unset = kwh is None or (isinstance(kwh, str) and kwh.strip() == "")
        if not legacy_unset:
            if isinstance(kwh, bool):
                raise ValueError("ZENDURE_BATTERY_CAPACITY_KWH_INVALID")
            try:
                parsed_kwh = float(kwh)
            except (TypeError, ValueError, OverflowError):
                raise ValueError("ZENDURE_BATTERY_CAPACITY_KWH_INVALID") from None
            if not math.isfinite(parsed_kwh) or parsed_kwh <= 0:
                raise ValueError("ZENDURE_BATTERY_CAPACITY_KWH_INVALID")

            derived_wh = int(round(parsed_kwh * 1000.0))
            current_wh = result.get("ZENDURE_BATTERY_CAPACITY_WH")
            if current_wh in (None, ""):
                result["ZENDURE_BATTERY_CAPACITY_WH"] = derived_wh
                steps.append("MIG-RC20-CAPACITY-KWH-TO-WH")
            else:
                try:
                    parsed_wh = float(current_wh)
                    agrees = math.isfinite(parsed_wh) and int(round(parsed_wh)) == derived_wh
                except (TypeError, ValueError, OverflowError):
                    agrees = False
                if not agrees:
                    raise ValueError("ZENDURE_BATTERY_CAPACITY_CONFLICT")

        result.pop("ZENDURE_BATTERY_CAPACITY_KWH", None)
        steps.append("MIG-RC20-REMOVE-CAPACITY-KWH")

    if "SMA_DISCHARGE_BLOCK_W" in result:
        legacy_threshold = result.get("SMA_DISCHARGE_BLOCK_W")
        canonical_threshold = result.get("CROSS_CHARGE_SIGNIFICANT_W")
        if canonical_threshold in (None, ""):
            result["CROSS_CHARGE_SIGNIFICANT_W"] = legacy_threshold
            steps.append("MIG-RC20-CROSS-CHARGE-ALIAS")
        else:
            try:
                agrees = int(float(canonical_threshold)) == int(float(legacy_threshold))
            except Exception:
                agrees = False
            if not agrees:
                raise ValueError("CROSS_CHARGE_SIGNIFICANT_W_CONFLICT")
        result.pop("SMA_DISCHARGE_BLOCK_W", None)
        steps.append("MIG-RC20-REMOVE-SMA-DISCHARGE-BLOCK")

    for key in sorted(LEGACY_REMOVE_NO_EFFECT_KEYS):
        if key in result:
            result.pop(key, None)
            steps.append("MIG-RC20-REMOVE-" + key)

    return result, tuple(steps)


def parse_full_candidate(
    raw: Mapping[str, Any],
    *,
    previous: Optional[Mapping[str, Any]] = None,
    context: Optional[ValidationContext] = None,
    new_install: bool = False,
) -> CandidateResult:
    if not isinstance(raw, Mapping):
        issue = ValidationIssue(
            code="CONFIG_ROOT_NOT_OBJECT",
            severity=ValidationSeverity.ERROR,
            keys=tuple(),
            message_id="CONFIG_ROOT_NOT_OBJECT",
            source="config",
            blocking=True,
        )
        return CandidateResult(
            MappingProxyType({}), MappingProxyType({}), MappingProxyType({}),
            MappingProxyType({}), tuple(), (issue,), ""
        )

    defaults = registry_defaults(new_install=new_install)
    merged: Dict[str, Any] = {}
    inherited = []
    for spec in _active_registry_specs():
        if spec.key in raw:
            merged[spec.key] = raw[spec.key]
        else:
            merged[spec.key] = defaults.get(spec.key)
            inherited.append(spec.key)

    # RC19 has no explicit primary/second-battery integration switch.  Until
    # its later release stage becomes operational, derive the inherited value
    # from the two existing productive features without persisting a new key.
    if "SECOND_BATTERY_INTEGRATION_ENABLED" not in raw:
        merged["SECOND_BATTERY_INTEGRATION_ENABLED"] = bool(
            merged.get("CROSS_CHARGE_ENABLED") or merged.get("REST_SURPLUS_HARVEST_ENABLED")
        )

    unknown = {key: value for key, value in raw.items() if key not in SETTINGS_BY_KEY}
    parsed: ParsedCandidate = parse_candidate(merged)
    known = dict(parsed.known)
    retired_keys = tuple(sorted(
        key for key in raw
        if key in SETTINGS_BY_KEY
        and SETTINGS_BY_KEY[key].lifecycle.startswith("remove_")
        and key not in LEGACY_RUNTIME_COMPAT_KEYS
    ))
    issues = [
        ValidationIssue(
            code="LEGACY_KEYS_REQUIRE_RC20_MIGRATION",
            severity=ValidationSeverity.ERROR,
            keys=retired_keys,
            message_id="LEGACY_KEYS_REQUIRE_RC20_MIGRATION",
            params={"count": len(retired_keys)},
            source="config",
            blocking=True,
        )
    ] if retired_keys else []
    issues.extend(parsed.issues)
    if not issues:
        validation_context = context or ValidationContext(previous=previous)
        if validation_context.previous is None and previous is not None:
            validation_context = ValidationContext(previous=previous)
        issues.extend(validate_candidate(known, validation_context))

    configured = dict(known)
    configured.update(unknown)
    if new_install:
        # A first installation is a canonical bootstrap transaction, not a
        # sparse migration patch. Persist the complete currently operational
        # Settings surface so a later NORMAL restart cannot fall back to
        # historical RC19 migration defaults. Target-only future settings stay
        # absent; the protected fixed SQLite path is persisted explicitly.
        persisted = {
            spec.key: known[spec.key]
            for spec in _active_registry_specs()
            if spec.key in known
            and (
                (spec.lifecycle == "active" and (spec.release_stage == "S1" or spec.origin == "RC19")
                 and spec.apply_class not in (ApplyClass.MIGRATION_ONLY, ApplyClass.READ_ONLY, ApplyClass.PROTECTED_ACTION))
                or spec.key == "MEASUREMENT_DB_PATH"
            )
        }
    else:
        persisted = {
            key: known[key]
            for key in raw
            if key in SETTINGS_BY_KEY and key in known
        }
    persisted.update(unknown)
    revision = typed_revision(configured) if not any(issue.blocking for issue in issues) else ""
    return CandidateResult(
        configured=MappingProxyType(configured),
        persisted=MappingProxyType(persisted),
        known=MappingProxyType(known),
        unknown=MappingProxyType(unknown),
        inherited_defaults=tuple(inherited),
        issues=tuple(issues),
        typed_revision=revision,
    )


def validation_issues_to_runtime(issues: Iterable[ValidationIssue], source: str = "validation") -> Tuple[RuntimeIssue, ...]:
    return tuple(
        RuntimeIssue(
            code=issue.code,
            severity=issue.severity.value,
            keys=issue.keys,
            message_id=issue.message_id,
            params=issue.params,
            source=source,
            blocking=issue.blocking,
        )
        for issue in issues
    )


def stable_read(path: str) -> StableReadResult:
    try:
        before_stat = os.stat(path)
    except FileNotFoundError:
        return StableReadResult(
            status="missing",
            data=None,
            fingerprint=None,
            revision=None,
            issue=RuntimeIssue("CONFIG_FILE_MISSING", "error", source="file"),
        )
    except OSError as exc:
        return StableReadResult(
            status="error",
            data=None,
            fingerprint=None,
            revision=None,
            issue=RuntimeIssue("CONFIG_FILE_STAT_FAILED", "error", params={"error": type(exc).__name__}, source="file"),
        )

    before = FileFingerprint.from_stat(before_stat)
    try:
        with open(path, "rb") as handle:
            data = handle.read()
        after = FileFingerprint.from_stat(os.stat(path))
    except OSError as exc:
        return StableReadResult(
            status="error",
            data=None,
            fingerprint=before,
            revision=None,
            issue=RuntimeIssue("CONFIG_FILE_READ_FAILED", "error", params={"error": type(exc).__name__}, source="file"),
        )
    if before != after:
        return StableReadResult(
            status="unstable_read",
            data=None,
            fingerprint=after,
            revision=None,
            issue=RuntimeIssue("CONFIG_FILE_UNSTABLE_READ", "info", source="file", blocking=False),
        )
    return StableReadResult("ok", data, after, sha256_bytes(data), None)


def decode_json_object(data: bytes) -> Tuple[Optional[Dict[str, Any]], Tuple[RuntimeIssue, ...]]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None, (RuntimeIssue("CONFIG_UTF8_INVALID", "error", source="file"),)
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, (
            RuntimeIssue(
                "CONFIG_JSON_INVALID",
                "error",
                params={"line": exc.lineno, "column": exc.colno},
                source="file",
            ),
        )
    if not isinstance(value, dict):
        return None, (RuntimeIssue("CONFIG_ROOT_NOT_OBJECT", "error", source="file"),)
    return value, tuple()


def atomic_write(path: str, data: bytes, *, mode: int = 0o600) -> None:
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=os.path.basename(path) + ".", suffix=".tmp", dir=directory)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        os.chmod(path, mode)
        dir_fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


class LastGoodStore:
    def __init__(
        self,
        config_path: str,
        app_version: str,
        *,
        expected_uid: Optional[int] = None,
        expected_gid: Optional[int] = None,
    ):
        self.config_path = os.path.abspath(config_path)
        self.app_version = app_version
        self.base = self.config_path + ".last-good"
        self.pointer_path = self.base + ".current"
        default_uid, default_gid = _expected_pi_owner()
        self.expected_uid = default_uid if expected_uid is None else int(expected_uid)
        self.expected_gid = default_gid if expected_gid is None else int(expected_gid)
        self._lock = threading.RLock()

    def _secure_file_issues(self, path: str, code_prefix: str, subject: str) -> Tuple[RuntimeIssue, ...]:
        try:
            value = os.lstat(path)
        except FileNotFoundError:
            return tuple()
        except OSError as exc:
            return (RuntimeIssue(
                code_prefix + "_LSTAT_FAILED", "error", (subject,),
                params={"error": type(exc).__name__}, source="last_good",
            ),)
        issues = []
        if not stat.S_ISREG(value.st_mode):
            issues.append(RuntimeIssue(code_prefix + "_NOT_REGULAR", "error", (subject,), source="last_good"))
            return tuple(issues)
        mode = stat.S_IMODE(value.st_mode)
        if mode != 0o600:
            issues.append(RuntimeIssue(
                code_prefix + "_MODE_INVALID", "error", (subject,),
                params={"expected": "0600", "actual": format(mode, "04o")}, source="last_good",
            ))
        if int(value.st_uid) != self.expected_uid or int(value.st_gid) != self.expected_gid:
            issues.append(RuntimeIssue(
                code_prefix + "_OWNER_INVALID", "error", (subject,),
                params={
                    "expected_uid": self.expected_uid,
                    "expected_gid": self.expected_gid,
                    "actual_uid": int(value.st_uid),
                    "actual_gid": int(value.st_gid),
                },
                source="last_good",
            ))
        return tuple(issues)

    def config_path_for(self, slot: str) -> str:
        return self.base + "." + slot

    def manifest_path_for(self, slot: str) -> str:
        return self.base + "." + slot + ".manifest.json"

    def _pointer(self) -> Tuple[Optional[Dict[str, Any]], Tuple[RuntimeIssue, ...]]:
        result = stable_read(self.pointer_path)
        if result.status == "missing":
            return None, (RuntimeIssue("LAST_GOOD_POINTER_MISSING", "warning", source="last_good", blocking=False),)
        security_issues = self._secure_file_issues(self.pointer_path, "LAST_GOOD_POINTER", "current")
        if security_issues:
            return None, security_issues
        if result.status != "ok" or result.data is None:
            return None, (result.issue or RuntimeIssue("LAST_GOOD_POINTER_INVALID", "error", source="last_good"),)
        value, issues = decode_json_object(result.data)
        if issues or value is None:
            return None, (RuntimeIssue("LAST_GOOD_POINTER_INVALID", "error", source="last_good"),)
        slot = value.get("slot")
        generation = value.get("generation_id")
        if value.get("pointer_version") != LAST_GOOD_POINTER_VERSION or slot not in ("A", "B") or not isinstance(generation, int) or isinstance(generation, bool) or generation <= 0:
            return None, (RuntimeIssue("LAST_GOOD_POINTER_INVALID", "error", source="last_good"),)
        return value, tuple()

    def validate_slot(self, slot: str) -> LastGoodSlot:
        issues = []
        config_path = self.config_path_for(slot)
        manifest_path = self.manifest_path_for(slot)
        issues.extend(self._secure_file_issues(config_path, "LAST_GOOD_CONFIG", slot))
        issues.extend(self._secure_file_issues(manifest_path, "LAST_GOOD_MANIFEST", slot))
        if issues:
            return LastGoodSlot(slot, False, False, issues=tuple(issues))
        config_result = stable_read(config_path)
        manifest_result = stable_read(manifest_path)
        if config_result.status != "ok" or config_result.data is None:
            issues.append(RuntimeIssue("LAST_GOOD_CONFIG_MISSING_OR_UNREADABLE", "error", (slot,), source="last_good"))
        if manifest_result.status != "ok" or manifest_result.data is None:
            issues.append(RuntimeIssue("LAST_GOOD_MANIFEST_MISSING_OR_UNREADABLE", "error", (slot,), source="last_good"))
        if issues:
            return LastGoodSlot(slot, False, False, issues=tuple(issues))

        manifest, manifest_issues = decode_json_object(manifest_result.data)
        config_raw, config_decode_issues = decode_json_object(config_result.data)
        if manifest_issues or manifest is None:
            issues.append(RuntimeIssue("LAST_GOOD_MANIFEST_INVALID", "error", (slot,), source="last_good"))
        if config_decode_issues or config_raw is None:
            issues.append(RuntimeIssue("LAST_GOOD_CONFIG_INVALID", "error", (slot,), source="last_good"))
        if issues:
            return LastGoodSlot(slot, False, False, issues=tuple(issues))

        config_hash = sha256_bytes(config_result.data)
        if manifest.get("manifest_version") != LAST_GOOD_MANIFEST_VERSION:
            issues.append(RuntimeIssue("LAST_GOOD_MANIFEST_VERSION_INVALID", "error", (slot,), source="last_good"))
        if manifest.get("controller_version") != self.app_version:
            issues.append(RuntimeIssue("LAST_GOOD_CONTROLLER_VERSION_MISMATCH", "error", (slot,), source="last_good"))
        if manifest.get("config_runtime_schema_version") != CONFIG_RUNTIME_SCHEMA_VERSION:
            issues.append(RuntimeIssue("LAST_GOOD_CONFIG_SCHEMA_MISMATCH", "error", (slot,), source="last_good"))
        if manifest.get("config_sha256") != config_hash:
            issues.append(RuntimeIssue("LAST_GOOD_HASH_MISMATCH", "error", (slot,), source="last_good"))
        generation = manifest.get("generation_id")
        if not isinstance(generation, int) or isinstance(generation, bool) or generation <= 0:
            issues.append(RuntimeIssue("LAST_GOOD_GENERATION_INVALID", "error", (slot,), source="last_good"))
            generation = 0
        if manifest.get("ready_proven") is not True or manifest.get("pending_restart") is not False:
            issues.append(RuntimeIssue("LAST_GOOD_NOT_ELIGIBLE", "error", (slot,), source="last_good"))
        candidate = parse_full_candidate(config_raw)
        if not candidate.valid:
            issues.extend(validation_issues_to_runtime(candidate.issues, "last_good"))
        if manifest.get("typed_revision") != candidate.typed_revision:
            issues.append(RuntimeIssue("LAST_GOOD_TYPED_REVISION_MISMATCH", "error", (slot,), source="last_good"))

        valid = not any(issue.blocking for issue in issues)
        return LastGoodSlot(
            slot=slot,
            valid=valid,
            eligible=valid,
            generation_id=int(generation or 0),
            typed_revision=candidate.typed_revision,
            config_hash=config_hash,
            config=candidate.configured if valid else MappingProxyType({}),
            manifest=MappingProxyType(dict(manifest)),
            issues=tuple(issues),
        )

    def select_recovery(self) -> Tuple[Optional[LastGoodSlot], Dict[str, Any]]:
        with self._lock:
            pointer, pointer_issues = self._pointer()
            slots = {slot: self.validate_slot(slot) for slot in ("A", "B")}
            status: Dict[str, Any] = {
                "pointer": pointer,
                "pointer_issues": [issue.as_dict() for issue in pointer_issues],
                "slots": {slot: value.as_status() for slot, value in slots.items()},
                "selection_reason": "unavailable",
                "repair_required": False,
            }
            valid_slots = [value for value in slots.values() if value.valid and value.eligible]

            if pointer is not None:
                current_name = pointer["slot"]
                current = slots[current_name]
                if current.valid and current.generation_id == pointer.get("generation_id") and current.typed_revision == pointer.get("typed_revision"):
                    status["selection_reason"] = "pointer_current"
                    return current, status
                other = slots["B" if current_name == "A" else "A"]
                if other.valid and other.generation_id < int(pointer.get("generation_id") or 0):
                    status["selection_reason"] = "current_invalid_previous_valid"
                    status["repair_required"] = True
                    return other, status
                status["selection_reason"] = "pointer_current_invalid"
                status["repair_required"] = True
                return None, status

            # Pointer missing/invalid: deterministic bounded disaster-recovery selection.
            status["repair_required"] = bool(valid_slots)
            if len(valid_slots) == 1:
                status["selection_reason"] = "single_valid"
                return valid_slots[0], status
            if len(valid_slots) == 2:
                a, b = slots["A"], slots["B"]
                if a.generation_id > b.generation_id:
                    status["selection_reason"] = "higher_generation_A"
                    return a, status
                if b.generation_id > a.generation_id:
                    status["selection_reason"] = "higher_generation_B"
                    return b, status
                status["selection_reason"] = "ambiguous"
                return None, status
            return None, status

    def current_status(self) -> Dict[str, Any]:
        selected, status = self.select_recovery()
        status["selected_slot"] = selected.slot if selected else None
        return status

    def promote(self, config: Mapping[str, Any], typed_config_revision: str, stable_ready_seconds: float) -> Dict[str, Any]:
        with self._lock:
            pointer, _pointer_issues = self._pointer()
            slots = {slot: self.validate_slot(slot) for slot in ("A", "B")}
            current_slot = pointer.get("slot") if pointer else None
            current_valid = slots.get(current_slot) if current_slot in slots else None
            if current_valid and current_valid.valid and current_valid.typed_revision == typed_config_revision:
                return {"status": "no_op", "slot": current_slot, "generation_id": current_valid.generation_id}

            generation = max((slot.generation_id for slot in slots.values() if slot.generation_id > 0), default=0) + 1
            target_slot = "B" if current_slot == "A" else "A"
            config_bytes = pretty_json_bytes(config)
            config_hash = sha256_bytes(config_bytes)
            manifest = {
                "manifest_version": LAST_GOOD_MANIFEST_VERSION,
                "controller_version": self.app_version,
                "config_runtime_schema_version": CONFIG_RUNTIME_SCHEMA_VERSION,
                "slot": target_slot,
                "generation_id": generation,
                "typed_revision": typed_config_revision,
                "config_sha256": config_hash,
                "promoted_at": _utc_now_iso(),
                "stable_ready_seconds": float(stable_ready_seconds),
                "ready_proven": True,
                "pending_restart": False,
                "effective_source": "primary",
            }
            atomic_write(self.config_path_for(target_slot), config_bytes, mode=0o600)
            atomic_write(self.manifest_path_for(target_slot), pretty_json_bytes(manifest), mode=0o600)
            reread = self.validate_slot(target_slot)
            if not reread.valid or reread.generation_id != generation or reread.typed_revision != typed_config_revision:
                raise RuntimeError("Last-Good target slot verification failed")
            pointer_value = {
                "pointer_version": LAST_GOOD_POINTER_VERSION,
                "slot": target_slot,
                "generation_id": generation,
                "typed_revision": typed_config_revision,
            }
            atomic_write(self.pointer_path, pretty_json_bytes(pointer_value), mode=0o600)
            pointer_after, issues_after = self._pointer()
            if issues_after or pointer_after != pointer_value:
                raise RuntimeError("Last-Good pointer verification failed")
            return {"status": "promoted", "slot": target_slot, "generation_id": generation, "typed_revision": typed_config_revision}

    def repair_pointer(self, expected_store_revision: str, target_slot: str) -> Dict[str, Any]:
        """Pointer-only protected repair primitive used by the S1.6 admin API."""
        with self._lock:
            before = self.store_revision()
            if before != expected_store_revision:
                raise RuntimeError("STORE_REVISION_CONFLICT")
            selected, status = self.select_recovery()
            if selected is None or selected.slot != target_slot or not status.get("repair_required"):
                raise RuntimeError("REPAIR_TARGET_NOT_ELIGIBLE")
            # Full revalidation directly before commit.
            target = self.validate_slot(target_slot)
            if not target.valid or target.typed_revision != selected.typed_revision or target.generation_id != selected.generation_id:
                raise RuntimeError("REPAIR_TARGET_CHANGED")

            old_exists = os.path.exists(self.pointer_path)
            old_bytes = stable_read(self.pointer_path).data if old_exists else None
            new_pointer = {
                "pointer_version": LAST_GOOD_POINTER_VERSION,
                "slot": target.slot,
                "generation_id": target.generation_id,
                "typed_revision": target.typed_revision,
            }
            try:
                atomic_write(self.pointer_path, pretty_json_bytes(new_pointer), mode=0o600)
                pointer_after, issues_after = self._pointer()
                target_after = self.validate_slot(target_slot)
                if issues_after or pointer_after != new_pointer or not target_after.valid:
                    raise RuntimeError("REPAIR_POST_VERIFY_FAILED")
            except Exception:
                if old_exists and old_bytes is not None:
                    atomic_write(self.pointer_path, old_bytes, mode=0o600)
                elif os.path.exists(self.pointer_path):
                    os.remove(self.pointer_path)
                    directory = os.path.dirname(self.pointer_path) or "."
                    dir_fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
                    try:
                        os.fsync(dir_fd)
                    finally:
                        os.close(dir_fd)
                raise
            return {"status": "repaired", "slot": target.slot, "generation_id": target.generation_id, "store_revision": self.store_revision()}

    def store_revision(self) -> str:
        digest = hashlib.sha256()
        for path in (
            self.pointer_path,
            self.config_path_for("A"),
            self.manifest_path_for("A"),
            self.config_path_for("B"),
            self.manifest_path_for("B"),
        ):
            digest.update(os.path.basename(path).encode("utf-8"))
            result = stable_read(path)
            if result.status == "ok" and result.data is not None:
                digest.update(result.data)
            else:
                digest.update(("<" + result.status + ">").encode("utf-8"))
        return digest.hexdigest()


class SettingsRuntimeManager:
    """Thread-safe configured/effective config authority for RC20."""

    def __init__(self, path: str, app_version: str):
        self.path = os.path.abspath(path)
        self.app_version = app_version
        self.last_good_store = LastGoodStore(self.path, app_version)
        self._lock = threading.RLock()
        self._configured: Dict[str, Any] = registry_defaults(new_install=False)
        self._persisted: Dict[str, Any] = {}
        self._effective: Dict[str, Any] = dict(self._configured)
        self._startup_effective: Dict[str, Any] = dict(self._effective)
        self._configured_revision = ""
        self._typed_revision = typed_revision(self._configured)
        self._effective_revision = self._typed_revision
        self._file_fingerprint: Optional[FileFingerprint] = None
        self._config_health = CONFIG_HEALTH_MISSING
        self._startup_mode = STARTUP_FIRST_INSTALL
        self._effective_source = "defaults_first_install"
        self._primary_valid = False
        self._invalid_file_revision: Optional[str] = None
        self._issues: Tuple[RuntimeIssue, ...] = tuple()
        self._inherited_defaults: Tuple[str, ...] = tuple()
        self._last_valid_configured_at: Optional[str] = None
        self._last_external_reload_at: Optional[str] = None
        self._last_commit_at: Optional[str] = None
        self._last_good_status: Dict[str, Any] = {}
        self._stable_ready_started_monotonic: Optional[float] = None
        self._stable_ready_elapsed_s = 0.0
        self._last_promoted_typed_revision = ""
        self._last_promotion: Dict[str, Any] = {}
        self._revision_nonce = secrets.token_hex(8)
        self._last_stat_fingerprint: Optional[FileFingerprint] = None
        self._invalid_raw: Optional[Dict[str, Any]] = None
        self._runtime_change_pending = False
        self._stable_ready_proof_revision = ""
        self._promotion_in_flight = False
        self._promotion_thread: Optional[threading.Thread] = None
        self._promotion_done = threading.Event()
        self._promotion_done.set()

    def get(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._effective)

    def get_configured(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._configured)

    def get_value(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._effective.get(key, default)

    def configured_revision(self) -> str:
        with self._lock:
            return self._configured_revision

    def typed_config_revision(self) -> str:
        with self._lock:
            return self._typed_revision

    def effective_revision(self) -> str:
        with self._lock:
            return self._effective_revision

    def control_allowed(self) -> bool:
        with self._lock:
            return self._startup_mode in (STARTUP_NORMAL, STARTUP_RECOVERY_ACTIVE)

    def startup_mode(self) -> str:
        with self._lock:
            return self._startup_mode

    def pending_restart_keys(self) -> Tuple[str, ...]:
        with self._lock:
            if not self._primary_valid:
                return tuple()
            return tuple(
                sorted(
                    spec.key
                    for spec in _active_registry_specs()
                    if spec.apply_class is ApplyClass.RESTART_REQUIRED
                    and self._configured.get(spec.key) != self._effective.get(spec.key)
                )
            )

    def pending_restart(self) -> bool:
        return bool(self.pending_restart_keys())

    def _set_valid_primary(self, result: CandidateResult, file_result: StableReadResult, *, startup: bool, source: str) -> None:
        previous_effective = dict(self._effective)
        previous_typed_revision = self._typed_revision
        self._configured = dict(result.configured)
        self._persisted = dict(result.persisted)
        if startup:
            self._effective = dict(result.configured)
            self._startup_effective = dict(self._effective)
        else:
            # Live settings follow configured immediately. Restart settings keep
            # their startup-effective values. Migration/read-only keys are not
            # runtime-applied by the settings layer.
            # Unknown extension keys are opaque to the controller but still
            # belong to the current config snapshot and Last-Good proof.  Drop
            # stale unknown keys from the previous snapshot and copy the exact
            # newly configured unknown set.  Known restart-required keys retain
            # their startup-effective values until a successful process restart.
            new_effective = {
                key: value for key, value in previous_effective.items()
                if key in SETTINGS_BY_KEY
            }
            for key, value in result.known.items():
                spec = SETTINGS_BY_KEY[key]
                if spec.apply_class is ApplyClass.LIVE_NEXT_CYCLE:
                    new_effective[key] = value
                elif key not in new_effective:
                    new_effective[key] = value
            new_effective.update(result.unknown)
            self._effective = new_effective
        self._configured_revision = file_result.revision or sha256_bytes(pretty_json_bytes(result.configured))
        self._typed_revision = result.typed_revision
        self._effective_revision = typed_revision(self._effective)
        if previous_typed_revision != self._typed_revision:
            self._stable_ready_started_monotonic = None
            self._stable_ready_elapsed_s = 0.0
        self._file_fingerprint = file_result.fingerprint
        self._last_stat_fingerprint = file_result.fingerprint
        self._config_health = CONFIG_HEALTH_VALID
        self._primary_valid = True
        self._invalid_file_revision = None
        self._invalid_raw = None
        self._issues = tuple()
        self._inherited_defaults = result.inherited_defaults
        self._effective_source = "primary"
        self._startup_mode = STARTUP_NORMAL
        self._stable_ready_proof_revision = ""
        self._last_valid_configured_at = _utc_now_iso()
        if source == "external_reload":
            self._last_external_reload_at = _utc_now_iso()

    def load(self) -> Dict[str, Any]:
        with self._lock:
            file_result = stable_read(self.path)
            if file_result.status == "ok" and file_result.data is not None:
                raw, decode_issues = decode_json_object(file_result.data)
                if raw is not None and not decode_issues:
                    candidate = parse_full_candidate(raw)
                    if candidate.valid:
                        self._set_valid_primary(candidate, file_result, startup=True, source="startup")
                        return dict(self._effective)
                    primary_issues = validation_issues_to_runtime(candidate.issues, "primary_config")
                else:
                    primary_issues = decode_issues
            else:
                primary_issues = (file_result.issue,) if file_result.issue else tuple()

            self._primary_valid = False
            self._configured_revision = file_result.revision or ""
            self._file_fingerprint = file_result.fingerprint
            self._last_stat_fingerprint = file_result.fingerprint
            self._invalid_file_revision = file_result.revision
            self._invalid_raw = dict(raw) if 'raw' in locals() and isinstance(raw, dict) else None
            self._issues = tuple(issue for issue in primary_issues if issue is not None)
            self._config_health = CONFIG_HEALTH_MISSING if file_result.status == "missing" else CONFIG_HEALTH_INVALID_STARTUP
            if self._invalid_raw is not None:
                self._configured, self._inherited_defaults = configured_view_from_raw(self._invalid_raw)
                self._persisted = dict(self._invalid_raw)
            else:
                self._configured = registry_defaults(new_install=file_result.status == "missing")
                self._persisted = {}
                self._inherited_defaults = tuple(spec.key for spec in _active_registry_specs())
            self._typed_revision = ""

            recovery, status = self.last_good_store.select_recovery()
            self._last_good_status = status
            if recovery is not None:
                self._effective = dict(recovery.config)
                self._startup_effective = dict(recovery.config)
                self._effective_revision = recovery.typed_revision
                self._effective_source = "last_good_" + recovery.slot.lower()
                self._startup_mode = STARTUP_RECOVERY_WAITING
                return dict(self._effective)

            self._effective = registry_defaults(new_install=True)
            self._startup_effective = dict(self._effective)
            self._effective_revision = typed_revision(self._effective)
            self._effective_source = "defaults_diagnostic_only"
            if file_result.status == "missing" and not any(os.path.exists(self.last_good_store.config_path_for(slot)) for slot in ("A", "B")):
                self._startup_mode = STARTUP_FIRST_INSTALL
            else:
                self._startup_mode = STARTUP_CONFIG_ERROR
            return dict(self._effective)

    def _current_stat_fingerprint(self) -> Optional[FileFingerprint]:
        try:
            return FileFingerprint.from_stat(os.stat(self.path))
        except FileNotFoundError:
            return None
        except OSError:
            return None

    def reload_if_needed(self) -> Tuple[Dict[str, Any], bool]:
        with self._lock:
            current = self._current_stat_fingerprint()
            # An actual external byte/file change always has priority over the
            # synthetic change edge emitted by a prior API commit.  This keeps
            # manual HEADLESS recovery and concurrent SSH edits responsive even
            # if they race the next controller cycle after a web save.
            if current == self._last_stat_fingerprint:
                if self._runtime_change_pending:
                    self._runtime_change_pending = False
                    return dict(self._effective), True
                return dict(self._effective), False

            # The external change supersedes the pending notification; its
            # successful reload will itself return the correct change edge.
            self._runtime_change_pending = False
            file_result = stable_read(self.path)
            if file_result.status == "unstable_read":
                return dict(self._effective), False
            self._last_stat_fingerprint = file_result.fingerprint
            if file_result.status != "ok" or file_result.data is None:
                if self._startup_mode == STARTUP_NORMAL:
                    self._config_health = CONFIG_HEALTH_INVALID_RUNTIME
                    self._primary_valid = False
                    self._invalid_file_revision = file_result.revision
                    self._invalid_raw = None
                    self._configured_revision = file_result.revision or ""
                    self._issues = (file_result.issue,) if file_result.issue else tuple()
                    self._effective_source = "last_valid_runtime"
                return dict(self._effective), False

            raw, decode_issues = decode_json_object(file_result.data)
            if raw is None or decode_issues:
                if self._startup_mode == STARTUP_NORMAL:
                    self._config_health = CONFIG_HEALTH_INVALID_RUNTIME
                    self._primary_valid = False
                    self._invalid_file_revision = file_result.revision
                    self._invalid_raw = None
                    self._configured_revision = file_result.revision or ""
                    self._issues = decode_issues
                    self._effective_source = "last_valid_runtime"
                return dict(self._effective), False

            candidate = parse_full_candidate(raw, previous=self._effective)
            if not candidate.valid:
                if self._startup_mode == STARTUP_NORMAL:
                    self._config_health = CONFIG_HEALTH_INVALID_RUNTIME
                    self._primary_valid = False
                    self._invalid_file_revision = file_result.revision
                    self._invalid_raw = dict(raw)
                    self._configured, self._inherited_defaults = configured_view_from_raw(raw)
                    self._persisted = dict(raw)
                    self._configured_revision = file_result.revision or ""
                    self._typed_revision = ""
                    self._issues = validation_issues_to_runtime(candidate.issues, "external_config")
                    self._effective_source = "last_valid_runtime"
                return dict(self._effective), False

            before = dict(self._effective)
            self._set_valid_primary(candidate, file_result, startup=False, source="external_reload")
            return dict(self._effective), before != self._effective

    def is_first_install(self) -> bool:
        with self._lock:
            return self._startup_mode == STARTUP_FIRST_INSTALL and not self._primary_valid

    def validate_candidate(
        self,
        candidate: Mapping[str, Any],
        *,
        previous: Optional[Mapping[str, Any]] = None,
        context: Optional[ValidationContext] = None,
    ) -> CandidateResult:
        first_install = self.is_first_install()
        if context is None:
            context = ValidationContext(previous=previous or self.get_configured(), first_install=first_install, explicit_keys=tuple(candidate.keys()))
        elif first_install and not context.first_install:
            context = replace(context, first_install=True, explicit_keys=tuple(candidate.keys()))
        return parse_full_candidate(candidate, previous=previous or self.get_configured(), context=context, new_install=first_install)

    def commit_candidate(
        self,
        candidate: Mapping[str, Any],
        expected_file_revision: str,
        *,
        context: Optional[ValidationContext] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            # Re-read the exact file bytes directly before persistence.
            current_file = stable_read(self.path)
            current_revision = current_file.revision or ""
            if current_revision != expected_file_revision:
                raise RuntimeError("CONFIG_REVISION_CONFLICT")
            first_install = self._startup_mode == STARTUP_FIRST_INSTALL and not self._primary_valid
            if context is None:
                context = ValidationContext(
                    previous=self._effective if not self._primary_valid else self._configured,
                    first_install=first_install,
                    explicit_keys=tuple(candidate.keys()),
                )
            elif first_install:
                # Preserve the exact explicit-key set that was validated during
                # preview. The persisted first-install candidate is canonical and
                # therefore contains many bootstrap keys that the user did not
                # explicitly set; treating those as explicit at commit would
                # weaken the First-Install contract.
                context = replace(context, first_install=True)
            result = parse_full_candidate(
                candidate,
                previous=self._effective if not self._primary_valid else self._configured,
                context=context,
                new_install=first_install,
            )
            if not result.valid:
                raise ValueError("CONFIG_CANDIDATE_INVALID")
            data = pretty_json_bytes(result.persisted)
            atomic_write(self.path, data, mode=0o600)
            reread = stable_read(self.path)
            if reread.status != "ok" or reread.data != data:
                raise RuntimeError("CONFIG_POST_WRITE_VERIFY_FAILED")
            before_effective = dict(self._effective)
            self._set_valid_primary(result, reread, startup=False, source="commit")
            self._runtime_change_pending = True
            self._last_commit_at = _utc_now_iso()
            apply_plan = build_apply_plan(result.configured, before_effective)
            return {
                "configured": dict(self._configured),
                "effective": dict(self._effective),
                "configured_revision": self._configured_revision,
                "typed_revision": self._typed_revision,
                "effective_revision": self._effective_revision,
                "apply_plan": apply_plan,
                "pending_restart_keys": self.pending_restart_keys(),
            }

    def _promotion_worker(self, config: Dict[str, Any], revision: str, elapsed_s: float) -> None:
        try:
            result = self.last_good_store.promote(config, revision, elapsed_s)
        except Exception as exc:
            result = {"status": "failed", "error": type(exc).__name__, "at": _utc_now_iso()}
        with self._lock:
            self._last_promotion = dict(result)
            if result.get("status") in ("promoted", "no_op"):
                self._last_promoted_typed_revision = revision
            self._promotion_in_flight = False
            self._promotion_done.set()

    def _schedule_promotion_locked(self) -> bool:
        if self._promotion_in_flight or self._last_promoted_typed_revision == self._typed_revision:
            return False
        config = dict(self._configured)
        revision = str(self._typed_revision)
        elapsed_s = float(self._stable_ready_elapsed_s)
        self._promotion_in_flight = True
        self._promotion_done.clear()
        self._last_promotion = {"status": "scheduled", "typed_revision": revision, "at": _utc_now_iso()}
        thread = threading.Thread(
            target=self._promotion_worker,
            args=(config, revision, elapsed_s),
            name="zec-last-good-promotion",
            daemon=True,
        )
        self._promotion_thread = thread
        thread.start()
        return True

    def wait_for_promotion(self, timeout: float = 5.0) -> bool:
        """Test/diagnostic helper; never used by the controller cycle."""
        return self._promotion_done.wait(max(0.0, float(timeout)))

    def observe_ready(
        self,
        base_ready: bool,
        now_monotonic: Optional[float] = None,
        proof_revision: str = "",
    ) -> Dict[str, Any]:
        now_mono = time.monotonic() if now_monotonic is None else float(now_monotonic)
        proof = str(proof_revision or "")
        with self._lock:
            if self._startup_mode == STARTUP_RECOVERY_WAITING:
                if base_ready:
                    self._startup_mode = STARTUP_RECOVERY_ACTIVE
                return {"startup_mode": self._startup_mode, "promoted": False, "promotion_scheduled": False}

            eligible = bool(
                self._startup_mode == STARTUP_NORMAL
                and self._primary_valid
                and self._config_health == CONFIG_HEALTH_VALID
                and self._effective_source == "primary"
                and not self.pending_restart()
                and base_ready
            )
            if not eligible:
                self._stable_ready_started_monotonic = None
                self._stable_ready_elapsed_s = 0.0
                self._stable_ready_proof_revision = proof
                return {"startup_mode": self._startup_mode, "promoted": False, "promotion_scheduled": False}

            if proof != self._stable_ready_proof_revision:
                self._stable_ready_proof_revision = proof
                self._stable_ready_started_monotonic = now_mono
                self._stable_ready_elapsed_s = 0.0
                return {"startup_mode": self._startup_mode, "promoted": False, "promotion_scheduled": False}

            if self._stable_ready_started_monotonic is None:
                self._stable_ready_started_monotonic = now_mono
            self._stable_ready_elapsed_s = max(0.0, now_mono - self._stable_ready_started_monotonic)
            if self._stable_ready_elapsed_s < STABLE_READY_SECONDS:
                return {"startup_mode": self._startup_mode, "promoted": False, "promotion_scheduled": False}
            scheduled = self._schedule_promotion_locked()
            return {
                "startup_mode": self._startup_mode,
                "promoted": False,
                "promotion_scheduled": scheduled,
                "promotion_in_flight": self._promotion_in_flight,
                "last_good": dict(self._last_promotion),
            }

    def candidate_base_config(self) -> Dict[str, Any]:
        """Base object for a repair preview.

        A syntactically valid but semantically invalid external file remains the
        configured source visible to the UI, so an explicit patch can repair it.
        """
        with self._lock:
            return dict(self._invalid_raw) if self._invalid_raw is not None else dict(self._persisted)

    def cas_revision(self) -> str:
        with self._lock:
            return self._invalid_file_revision or self._configured_revision

    def redacted_config(self, *, configured: bool = True) -> Dict[str, Any]:
        source = self.get_configured() if configured else self.get()
        result = {}
        for key, value in source.items():
            spec = SETTINGS_BY_KEY.get(key)
            if spec is not None and spec.lifecycle == "deployment_constant_not_config":
                continue
            if spec is not None and spec.is_secret:
                result[key] = {"secret_set": bool(value)}
            else:
                result[key] = value
        return result

    def status(self) -> Dict[str, Any]:
        with self._lock:
            pending = self.pending_restart_keys()
            last_good_status = self.last_good_store.current_status()
            self._last_good_status = last_good_status
            return {
                "config_health": self._config_health,
                "primary_config_valid": self._primary_valid,
                "configured_file_valid": self._config_health == CONFIG_HEALTH_VALID,
                "effective_config_valid": bool(self._effective),
                "startup_mode": self._startup_mode,
                "control_allowed": self._startup_mode in (STARTUP_NORMAL, STARTUP_RECOVERY_ACTIVE),
                "recovery_mode": self._startup_mode in (STARTUP_RECOVERY_WAITING, STARTUP_RECOVERY_ACTIVE),
                "effective_source": self._effective_source,
                "configured_revision": self._configured_revision,
                "config_file_revision": self._configured_revision,
                "typed_config_revision": self._typed_revision,
                "effective_config_revision": self._effective_revision,
                "invalid_file_revision": self._invalid_file_revision,
                "pending_restart": bool(pending),
                "pending_restart_keys": list(pending),
                "inherited_default_keys": list(self._inherited_defaults),
                "issues": [issue.as_dict() for issue in self._issues],
                "last_valid_configured_at": self._last_valid_configured_at,
                "last_external_reload_at": self._last_external_reload_at,
                "last_commit_at": self._last_commit_at,
                "stable_ready_elapsed_s": self._stable_ready_elapsed_s,
                "stable_ready_required_s": STABLE_READY_SECONDS,
                "stable_ready_proof_revision": self._stable_ready_proof_revision,
                "promotion_in_flight": self._promotion_in_flight,
                "last_promotion": dict(self._last_promotion),
                "last_good_store": last_good_status,
                "last_good_store_revision": self.last_good_store.store_revision(),
                "last_good_store_repair_required": bool(last_good_status.get("repair_required")),
            }
