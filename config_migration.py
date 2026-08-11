# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>

"""Pure, shared configuration migration authority for ZEC.

The live runtime, installer/CLI migration and V13 bundle/legacy import paths use
this module so schema transforms cannot drift between entry points.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Dict, Mapping, Tuple


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

    # V12.13: Measurement runtime is V4-only. Keep the marker for rollback
    # compatibility, but migrate every historical selector value to the fixed 4.
    schema_marker = str(result.get("MEASUREMENT_SCHEMA_VERSION", "") or "").strip().lower()
    legacy_schema_marker = str(result.get("MEASUREMENT_LOG_SCHEMA", "") or "").strip().lower()
    if schema_marker in {"3", "v3", "zec3", "zec-measurement-v3"} or (not schema_marker and legacy_schema_marker in {"3", "v3", "zec3", "zec-measurement-v3"}):
        result["MEASUREMENT_SCHEMA_VERSION"] = "4"
        steps.append("MIG-V12.13-MEASUREMENT-SCHEMA-3-TO-4")
    elif schema_marker and schema_marker not in {"4", "v4", "zec4", "zec-measurement-v4"}:
        raise ValueError("MEASUREMENT_SCHEMA_VERSION_INVALID")
    elif schema_marker in {"v4", "zec4", "zec-measurement-v4"}:
        result["MEASUREMENT_SCHEMA_VERSION"] = "4"
        steps.append("MIG-V12.13-NORMALIZE-MEASUREMENT-SCHEMA-4")

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



@dataclass(frozen=True)
class MigrationResult:
    configured: Mapping[str, Any]
    steps: Tuple[str, ...]
    scope_keys: Tuple[str, ...]
    consumed_keys: Tuple[str, ...]
    removed_keys: Tuple[str, ...]


def migrate_scope_keys(keys) -> Tuple[Tuple[str, ...], Tuple[str, ...], Tuple[str, ...]]:
    """Migrate bundle scope names with the same key authority as config migration.

    Returns ``(current_keys, consumed_legacy_keys, removed_obsolete_keys)``.
    Values are not interpreted here; value transforms remain exclusively in
    ``migrate_rc19_to_rc20``.
    """
    migrated = []
    consumed = []
    removed = []
    for raw_key in keys:
        key = str(raw_key)
        if key == "ZENDURE_BATTERY_CAPACITY_KWH":
            migrated.append("ZENDURE_BATTERY_CAPACITY_WH")
            consumed.append(key)
        elif key == "SMA_DISCHARGE_BLOCK_W":
            migrated.append("CROSS_CHARGE_SIGNIFICANT_W")
            consumed.append(key)
        elif key == "SERVICE_RESTART_COMMAND" or key in LEGACY_REMOVE_NO_EFFECT_KEYS:
            removed.append(key)
        else:
            migrated.append(key)
    return tuple(sorted(dict.fromkeys(migrated))), tuple(sorted(dict.fromkeys(consumed))), tuple(sorted(dict.fromkeys(removed)))


def migrate_to_current(raw: Mapping[str, Any], scope_keys=()) -> MigrationResult:
    migrated, steps = migrate_rc19_to_rc20(raw)
    current_scope, consumed, removed = migrate_scope_keys(scope_keys or tuple(raw.keys()))
    return MigrationResult(
        configured=MappingProxyType(dict(migrated)),
        steps=tuple(steps),
        scope_keys=current_scope,
        consumed_keys=consumed,
        removed_keys=removed,
    )
