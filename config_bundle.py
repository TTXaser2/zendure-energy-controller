# SPDX-License-Identifier: AGPL-3.0-or-later
"""Portable V13 configuration bundle contract.

The module is deliberately side-effect free: parsing/building bundles never writes the
primary config, Last-Good store, device state or measurement storage.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from config_migration import migrate_scope_keys, migrate_to_current
from settings_registry import (
    SETTINGS_BY_KEY,
    ApplyClass,
    Editability,
    PortabilityClass,
    managed_settings,
    portable_profile_settings,
    registry_contract_sha256,
    SCHEMA_VERSION as SETTINGS_REGISTRY_SCHEMA_VERSION,
)
from settings_runtime import CONFIG_RUNTIME_SCHEMA_VERSION
from version import APP_BUILD_ID, APP_VERSION

BUNDLE_FORMAT = "ZEC-CONFIG-BUNDLE"
BUNDLE_FORMAT_VERSION = 1
CANONICALIZATION = "ZEC-CANONICAL-JSON-V1"
BUNDLE_MAX_BYTES = 1024 * 1024
ARTIFACT_KINDS = frozenset(("named_state", "export", "portable_profile"))
SCOPE_MODES = frozenset(("full_managed", "categories", "keys", "portable_profile"))

# V13.0.2 changes only public display/help metadata in the registry contract.
# Exact prior V13.0.1 bundles remain safely interpretable because setting keys,
# types, codecs, portability, apply semantics and defaults are unchanged.
_DISPLAY_ONLY_REGISTRY_COMPATIBILITY = {
    ("1.24-v13.0", "c1e13a7a1fd2968545bcf49073dc7b1d9e9dd7c71e0d002a45f50610d0780440"): "REGISTRY_DISPLAY_METADATA_V13_0_2",
}


class BundleError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code if not detail else f"{code}:{detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class ParsedBundle:
    document: Mapping[str, Any]
    payload: Mapping[str, Any]
    payload_sha256: str
    source_metadata: Mapping[str, Any]
    scope: Mapping[str, Any]
    explicit_values: Mapping[str, Any]
    resolved_values: Mapping[str, Any]
    secrets: Mapping[str, Any]
    compatibility: Mapping[str, Any]
    migrated_scope_keys: Tuple[str, ...]
    migration_steps: Tuple[str, ...]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def payload_sha256(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _reject_constant(value: str) -> None:
    raise BundleError("BUNDLE_NON_FINITE_NUMBER", value)


def _pairs_object(pairs: Sequence[Tuple[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise BundleError("BUNDLE_DUPLICATE_KEY", key)
        out[key] = value
    return out


def strict_json_object(data: bytes, *, max_bytes: int = BUNDLE_MAX_BYTES) -> Dict[str, Any]:
    if len(data) > max_bytes:
        raise BundleError("BUNDLE_TOO_LARGE")
    try:
        text = data.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise BundleError("BUNDLE_UTF8_INVALID") from exc
    try:
        value = json.loads(text, object_pairs_hook=_pairs_object, parse_constant=_reject_constant)
    except BundleError:
        raise
    except Exception as exc:
        raise BundleError("BUNDLE_JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise BundleError("BUNDLE_ROOT_NOT_OBJECT")
    return value


def _validate_tree_finite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise BundleError("BUNDLE_NON_FINITE_NUMBER")
    if isinstance(value, Mapping):
        for child in value.values():
            _validate_tree_finite(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _validate_tree_finite(child)


def _managed_by_key() -> Dict[str, Any]:
    return {spec.key: spec for spec in managed_settings()}


def materialize_scope(
    mode: str,
    *,
    categories: Optional[Iterable[str]] = None,
    keys: Optional[Iterable[str]] = None,
) -> Tuple[str, Tuple[str, ...], Tuple[str, ...]]:
    """Return normalized mode/categories/concrete sorted scope keys."""
    mode = str(mode or "full_managed")
    if mode not in SCOPE_MODES:
        raise BundleError("SCOPE_MODE_INVALID", mode)
    managed = _managed_by_key()
    cats = tuple(sorted({str(x) for x in (categories or ()) if str(x)}))
    requested = tuple(str(x) for x in (keys or ()))
    if len(set(requested)) != len(requested):
        raise BundleError("SCOPE_DUPLICATE_KEY")
    if mode == "full_managed":
        concrete = tuple(sorted(managed))
        cats = tuple()
    elif mode == "portable_profile":
        concrete = tuple(sorted(spec.key for spec in portable_profile_settings()))
        cats = tuple()
    elif mode == "categories":
        known_categories = {spec.category for spec in managed.values()}
        unknown_cats = tuple(sorted(set(cats) - known_categories))
        if unknown_cats:
            raise BundleError("SCOPE_UNKNOWN_CATEGORY", ",".join(unknown_cats))
        concrete = tuple(sorted(key for key, spec in managed.items() if spec.category in set(cats)))
        if not concrete:
            raise BundleError("SCOPE_EMPTY")
    else:
        unknown = tuple(sorted(set(requested) - set(managed)))
        if unknown:
            raise BundleError("SCOPE_UNKNOWN_KEY", ",".join(unknown))
        concrete = tuple(sorted(requested))
        cats = tuple()
        if not concrete:
            raise BundleError("SCOPE_EMPTY")
    return mode, cats, concrete


def _validate_portable_scope(keys: Iterable[str]) -> None:
    invalid = []
    for key in keys:
        spec = SETTINGS_BY_KEY.get(key)
        if spec is None or spec.portability_class is not PortabilityClass.PORTABLE_PROFILE:
            invalid.append(key)
    if invalid:
        raise BundleError("PORTABLE_PROFILE_SCOPE_VIOLATION", ",".join(sorted(invalid)))


def build_bundle_payload(
    manager: Any,
    *,
    artifact_kind: str,
    scope_mode: str = "full_managed",
    categories: Optional[Iterable[str]] = None,
    keys: Optional[Iterable[str]] = None,
    name: str = "",
    description: str = "",
    include_secrets: bool = False,
) -> Dict[str, Any]:
    if artifact_kind not in ARTIFACT_KINDS:
        raise BundleError("ARTIFACT_KIND_INVALID", artifact_kind)
    mode, cats, concrete = materialize_scope(scope_mode, categories=categories, keys=keys)
    if artifact_kind == "portable_profile":
        mode, cats, concrete = materialize_scope("portable_profile")
        _validate_portable_scope(concrete)
        include_secrets = False
    elif mode == "portable_profile":
        # Scope and artifact type are independent dimensions. A local named
        # state may intentionally contain only portable settings without
        # becoming an exchange artifact itself.
        mode, cats, concrete = materialize_scope("portable_profile")
        _validate_portable_scope(concrete)
        include_secrets = False

    persisted = dict(manager.candidate_base_config())
    configured = dict(manager.get_configured())
    explicit_values: Dict[str, Any] = {}
    resolved_values: Dict[str, Any] = {}
    secret_items: Dict[str, Any] = {}
    for key in concrete:
        spec = SETTINGS_BY_KEY[key]
        if spec.is_secret:
            secret_items[key] = {
                "source_state": "set" if bool(configured.get(key)) else "empty",
                "included": bool(include_secrets),
            }
            if include_secrets:
                secret_items[key]["value"] = configured.get(key, "")
            continue
        if key in persisted:
            explicit_values[key] = persisted[key]
        if key in configured:
            resolved_values[key] = configured[key]

    status = manager.status() if callable(getattr(manager, "status", None)) else {}
    payload: Dict[str, Any] = {
        "artifact_kind": artifact_kind,
        "created_at": _utc_now_iso(),
        "name": str(name),
        "description": str(description),
        "source": {
            "app_version": APP_VERSION,
            "app_build_id": APP_BUILD_ID,
            "settings_registry_schema_version": SETTINGS_REGISTRY_SCHEMA_VERSION,
            "settings_registry_sha256": registry_contract_sha256(),
            "config_runtime_schema_version": CONFIG_RUNTIME_SCHEMA_VERSION,
            "typed_config_revision": str(status.get("typed_config_revision") or manager.typed_config_revision()),
            "config_file_revision": str(status.get("config_file_revision") or manager.cas_revision()),
        },
        "scope": {"mode": mode, "categories": list(cats), "keys": list(concrete)},
        "explicit_values": explicit_values,
        "resolved_values": resolved_values,
        "secrets": {
            "included": bool(include_secrets and secret_items),
            "items": secret_items,
        },
    }
    return payload


def encode_bundle(payload: Mapping[str, Any]) -> bytes:
    _validate_tree_finite(payload)
    digest = payload_sha256(payload)
    doc = {
        "format": BUNDLE_FORMAT,
        "format_version": BUNDLE_FORMAT_VERSION,
        "payload": dict(payload),
        "integrity": {
            "canonicalization": CANONICALIZATION,
            "payload_sha256": digest,
        },
    }
    data = canonical_json_bytes(doc)
    if len(data) > BUNDLE_MAX_BYTES:
        raise BundleError("BUNDLE_TOO_LARGE")
    return data


def build_bundle(manager: Any, **kwargs: Any) -> bytes:
    return encode_bundle(build_bundle_payload(manager, **kwargs))


def _required_mapping(container: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = container.get(key)
    if not isinstance(value, Mapping):
        raise BundleError("BUNDLE_REQUIRED_OBJECT_MISSING", key)
    return value


def _compatibility(source: Mapping[str, Any]) -> Dict[str, Any]:
    runtime_schema = str(source.get("config_runtime_schema_version") or "")
    registry_schema = str(source.get("settings_registry_schema_version") or "")
    registry_hash = str(source.get("settings_registry_sha256") or "")
    source_app = str(source.get("app_version") or "")
    if not runtime_schema or not registry_schema or not registry_hash:
        raise BundleError("BUNDLE_SOURCE_METADATA_INCOMPLETE")
    if runtime_schema != CONFIG_RUNTIME_SCHEMA_VERSION:
        return {
            "status": "incompatible",
            "code": "CONFIG_RUNTIME_SCHEMA_INCOMPATIBLE",
            "source": runtime_schema,
            "target": CONFIG_RUNTIME_SCHEMA_VERSION,
        }
    current_hash = registry_contract_sha256()
    compatibility_step = ""
    if registry_hash == current_hash and registry_schema == SETTINGS_REGISTRY_SCHEMA_VERSION:
        status = "direct"
    elif (registry_schema, registry_hash) in _DISPLAY_ONLY_REGISTRY_COMPATIBILITY:
        status = "compatible"
        compatibility_step = _DISPLAY_ONLY_REGISTRY_COMPATIBILITY[(registry_schema, registry_hash)]
    else:
        # Arbitrary Registry drift remains fail closed. Only exact, explicitly
        # reviewed compatibility transitions may pass this boundary.
        return {
            "status": "incompatible",
            "code": "SETTINGS_REGISTRY_COMPATIBILITY_UNSUPPORTED",
            "source_registry_schema_version": registry_schema,
            "target_registry_schema_version": SETTINGS_REGISTRY_SCHEMA_VERSION,
            "source_registry_sha256": registry_hash,
            "target_registry_sha256": current_hash,
        }
    warnings = []
    try:
        # Numeric comparison is intentionally conservative; non-numeric versions are
        # not guessed and therefore create no warning.
        src = tuple(int(x) for x in source_app.split("."))
        cur = tuple(int(x) for x in APP_VERSION.split("."))
        if src > cur and runtime_schema == CONFIG_RUNTIME_SCHEMA_VERSION:
            warnings.append("SOURCE_APP_NEWER_SAME_CONFIG_SCHEMA")
    except Exception:
        pass
    if compatibility_step:
        warnings.append(compatibility_step)
    return {
        "status": status,
        "source_registry_schema_version": registry_schema,
        "target_registry_schema_version": SETTINGS_REGISTRY_SCHEMA_VERSION,
        "source_registry_sha256": registry_hash,
        "target_registry_sha256": current_hash,
        "warnings": warnings,
        "migration_steps": [compatibility_step] if compatibility_step else [],
    }


def parse_bundle(data: bytes) -> ParsedBundle:
    doc = strict_json_object(data)
    if doc.get("format") != BUNDLE_FORMAT:
        raise BundleError("BUNDLE_FORMAT_INVALID")
    if doc.get("format_version") != BUNDLE_FORMAT_VERSION:
        raise BundleError("BUNDLE_FORMAT_VERSION_UNSUPPORTED")
    payload = _required_mapping(doc, "payload")
    integrity = _required_mapping(doc, "integrity")
    if integrity.get("canonicalization") != CANONICALIZATION:
        raise BundleError("BUNDLE_CANONICALIZATION_UNSUPPORTED")
    actual = payload_sha256(payload)
    expected = str(integrity.get("payload_sha256") or "")
    if not expected or actual != expected:
        raise BundleError("BUNDLE_INTEGRITY_MISMATCH")
    _validate_tree_finite(payload)
    artifact_kind = str(payload.get("artifact_kind") or "")
    if artifact_kind not in ARTIFACT_KINDS:
        raise BundleError("ARTIFACT_KIND_INVALID")
    source = _required_mapping(payload, "source")
    scope = _required_mapping(payload, "scope")
    explicit = _required_mapping(payload, "explicit_values")
    resolved = _required_mapping(payload, "resolved_values")
    secrets_doc = _required_mapping(payload, "secrets")
    secret_items = secrets_doc.get("items", {})
    if not isinstance(secret_items, Mapping) or not isinstance(secrets_doc.get("included"), bool):
        raise BundleError("BUNDLE_SECRET_STRUCTURE_INVALID")

    raw_mode = str(scope.get("mode") or "")
    raw_keys = scope.get("keys")
    raw_categories = scope.get("categories") or []
    if not isinstance(raw_keys, list) or not all(isinstance(x, str) for x in raw_keys):
        raise BundleError("BUNDLE_SCOPE_INVALID")
    if len(set(raw_keys)) != len(raw_keys):
        raise BundleError("SCOPE_DUPLICATE_KEY")
    if not isinstance(raw_categories, list) or not all(isinstance(x, str) for x in raw_categories):
        raise BundleError("BUNDLE_SCOPE_INVALID")

    compatibility = _compatibility(source)
    if compatibility["status"] == "incompatible":
        raise BundleError(str(compatibility["code"]))

    migrated_explicit = migrate_to_current(explicit, scope_keys=raw_keys)
    migrated_resolved = migrate_to_current(resolved, scope_keys=raw_keys)
    migrated_keys, scope_consumed, scope_removed = migrate_scope_keys(raw_keys)
    scope_steps = tuple(["MIG-SCOPE-CONSUME-" + key for key in scope_consumed] + ["MIG-SCOPE-REMOVE-" + key for key in scope_removed])
    compatibility_steps = tuple(str(x) for x in (compatibility.get("migration_steps") or ()) if str(x))
    migration_steps = tuple(dict.fromkeys(
        compatibility_steps + tuple(migrated_explicit.steps) + tuple(migrated_resolved.steps) + tuple(scope_steps)
    ))
    if raw_mode == "portable_profile" or artifact_kind == "portable_profile":
        _validate_portable_scope(migrated_keys)
        raw_mode = "portable_profile"

    # Every migrated scope key must now be a current managed setting; imported
    # unknowns are reported by the coordinator but cannot silently enter a bundle scope.
    managed = _managed_by_key()
    unknown_scope = tuple(sorted(set(migrated_keys) - set(managed)))
    if unknown_scope and (raw_mode == "portable_profile" or artifact_kind == "portable_profile"):
        raise BundleError("PORTABLE_PROFILE_UNKNOWN_KEY", ",".join(unknown_scope))

    source_value_keys = set(migrated_explicit.configured) | set(migrated_resolved.configured)
    outside_scope = tuple(sorted(source_value_keys - set(migrated_keys)))
    if outside_scope:
        raise BundleError("BUNDLE_VALUE_OUTSIDE_SCOPE", ",".join(outside_scope))

    # Secrets may only appear in the dedicated contract, never in value maps.
    secret_keys = {key for key, spec in SETTINGS_BY_KEY.items() if spec.is_secret}
    leaked = sorted((set(migrated_explicit.configured) | set(migrated_resolved.configured)) & secret_keys)
    if leaked:
        raise BundleError("BUNDLE_SECRET_IN_VALUE_MAP", ",".join(leaked))
    included_secret_keys = []
    migrated_scope_set = set(migrated_keys)
    for key, item in secret_items.items():
        key = str(key)
        spec = SETTINGS_BY_KEY.get(key)
        if spec is None or not spec.is_secret or not isinstance(item, Mapping):
            raise BundleError("BUNDLE_SECRET_STRUCTURE_INVALID", key)
        if key not in migrated_scope_set:
            raise BundleError("BUNDLE_SECRET_OUTSIDE_SCOPE", key)
        if not isinstance(item.get("included"), bool):
            raise BundleError("BUNDLE_SECRET_STRUCTURE_INVALID", key)
        included = item.get("included")
        if included:
            included_secret_keys.append(key)
            if not isinstance(item.get("value"), str):
                raise BundleError("BUNDLE_SECRET_VALUE_INVALID", key)
        elif "value" in item:
            raise BundleError("BUNDLE_SECRET_VALUE_WITHOUT_INCLUDE", key)
        if artifact_kind == "portable_profile" and included:
            raise BundleError("PORTABLE_PROFILE_SECRET_FORBIDDEN")
    if bool(secrets_doc.get("included")) != bool(included_secret_keys):
        raise BundleError("BUNDLE_SECRET_INCLUDE_MISMATCH")

    # A direct v1 bundle must carry the resolved source value for every current,
    # non-secret managed setting in scope. This is needed to detect inherited-default
    # drift without silently pinning the old default as an explicit target value.
    if compatibility.get("status") in ("direct", "compatible"):
        missing_resolved = sorted(
            key for key in migrated_keys
            if key in managed and not managed[key].is_secret and key not in migrated_resolved.configured
        )
        if missing_resolved:
            raise BundleError("BUNDLE_RESOLVED_VALUE_MISSING", ",".join(missing_resolved))

    return ParsedBundle(
        document=doc,
        payload=payload,
        payload_sha256=actual,
        source_metadata=source,
        scope={"mode": raw_mode, "categories": list(raw_categories), "keys": list(migrated_keys), "unknown_keys": list(unknown_scope)},
        explicit_values=dict(migrated_explicit.configured),
        resolved_values=dict(migrated_resolved.configured),
        secrets=secrets_doc,
        compatibility=compatibility,
        migrated_scope_keys=tuple(migrated_keys),
        migration_steps=migration_steps,
    )
