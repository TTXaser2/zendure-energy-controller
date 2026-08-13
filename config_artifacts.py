# SPDX-License-Identifier: AGPL-3.0-or-later
"""Coordinator for named-state loading and configuration import previews.

All paths end in SettingsService.preview_candidate; this module never persists the
primary config directly.
"""
from __future__ import annotations

import hashlib
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from config_bundle import (
    BUNDLE_MAX_BYTES,
    BundleError,
    ParsedBundle,
    parse_bundle,
    strict_json_object,
)
from config_migration import migrate_to_current
from config_states import ConfigStateError, ConfigStateStore
from settings_registry import SETTINGS_BY_KEY, managed_settings, PortabilityClass
from settings_service import SettingsService

IMPORT_TOKEN_TTL_SECONDS = 300.0
MAX_IMPORT_TOKENS = 32


def _issue(code: str, *, blocking: bool, keys: Sequence[str] = (), message: str = "", severity: str = "") -> Dict[str, Any]:
    return {
        "code": code,
        "severity": severity or ("error" if blocking else "warning"),
        "keys": list(keys),
        "message_id": code,
        "message": message or code,
        "params": {},
        "source": "config_import",
        "blocking": blocking,
    }


@dataclass(frozen=True)
class ImportArtifact:
    token: str
    created_monotonic: float
    expires_monotonic: float
    artifact_sha256: str
    parsed: ParsedBundle
    session_token: str
    legacy_raw: bool = False


class ImportTokenStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._items: Dict[str, ImportArtifact] = {}

    def _cleanup(self) -> None:
        now = time.monotonic()
        for key, item in list(self._items.items()):
            if item.expires_monotonic <= now:
                self._items.pop(key, None)
        if len(self._items) > MAX_IMPORT_TOKENS:
            ordered = sorted(self._items.values(), key=lambda x: x.created_monotonic)
            for item in ordered[: len(self._items) - MAX_IMPORT_TOKENS]:
                self._items.pop(item.token, None)

    def put(self, parsed: ParsedBundle, artifact_sha256: str, *, session_token: str, legacy_raw: bool = False) -> ImportArtifact:
        with self._lock:
            self._cleanup()
            token = secrets.token_urlsafe(24)
            now = time.monotonic()
            item = ImportArtifact(token, now, now + IMPORT_TOKEN_TTL_SECONDS, artifact_sha256, parsed, str(session_token or ""), legacy_raw)
            self._items[token] = item
            return item

    def get(self, token: str, session_token: str) -> ImportArtifact:
        with self._lock:
            self._cleanup()
            item = self._items.get(str(token or ""))
            if item is None:
                raise KeyError("CONFIG_IMPORT_TOKEN_EXPIRED_OR_UNKNOWN")
            if not item.session_token or item.session_token != str(session_token or ""):
                raise PermissionError("CONFIG_IMPORT_TOKEN_SESSION_MISMATCH")
            return item


class ConfigArtifactCoordinator:
    def __init__(self, manager: Any, settings_service: SettingsService, state_store: ConfigStateStore) -> None:
        self.manager = manager
        self.settings_service = settings_service
        self.state_store = state_store
        self.imports = ImportTokenStore()

    @staticmethod
    def _inspect_response(item: ImportArtifact) -> Dict[str, Any]:
        p = item.parsed
        secret_items = p.secrets.get("items", {}) if isinstance(p.secrets, Mapping) else {}
        return {
            "status": "inspected",
            "import_token": item.token,
            "expires_at_epoch": time.time() + max(0.0, item.expires_monotonic - time.monotonic()),
            "artifact_sha256": item.artifact_sha256,
            "artifact_kind": p.payload.get("artifact_kind"),
            "name": p.payload.get("name", ""),
            "description": p.payload.get("description", ""),
            "source": dict(p.source_metadata),
            "compatibility": dict(p.compatibility),
            "migration_steps": list(p.migration_steps),
            "scope": dict(p.scope),
            "unknown_source_keys": list(p.scope.get("unknown_keys") or []),
            "secrets": {
                "available": [key for key, meta in secret_items.items() if isinstance(meta, Mapping) and meta.get("included")],
                "default_operation": "keep",
                "plaintext_returned": False,
            },
            "legacy_raw": item.legacy_raw,
        }

    def inspect_bundle(self, data: bytes, *, session_token: str) -> Dict[str, Any]:
        parsed = parse_bundle(data)
        item = self.imports.put(parsed, hashlib.sha256(data).hexdigest(), session_token=session_token, legacy_raw=False)
        return self._inspect_response(item)

    def inspect_legacy_raw(self, data: bytes, *, expert: bool, session_token: str) -> Dict[str, Any]:
        if not expert:
            raise PermissionError("EXPERT_MODE_REQUIRED")
        raw = strict_json_object(data, max_bytes=BUNDLE_MAX_BYTES)
        migrated = migrate_to_current(raw, scope_keys=tuple(raw.keys()))
        managed = {spec.key for spec in managed_settings()}
        unknown = tuple(sorted(set(migrated.configured) - set(SETTINGS_BY_KEY)))
        explicit: Dict[str, Any] = {}
        resolved: Dict[str, Any] = {}
        secret_items: Dict[str, Any] = {}
        for key, value in migrated.configured.items():
            spec = SETTINGS_BY_KEY.get(key)
            if spec is None:
                continue
            if spec.is_secret:
                secret_items[key] = {"source_state": "set" if bool(value) else "empty", "included": True, "value": str(value or "")}
            elif key in managed:
                explicit[key] = value
                resolved[key] = value
        scope_keys = tuple(sorted(managed))
        from config_bundle import ParsedBundle  # local to keep raw path explicit
        parsed = ParsedBundle(
            document={},
            payload={"artifact_kind": "export", "name": "Legacy config.json", "description": ""},
            payload_sha256=hashlib.sha256(data).hexdigest(),
            source_metadata={
                "app_version": "legacy/unknown",
                "app_build_id": "legacy/unknown",
                "settings_registry_schema_version": "legacy/unknown",
                "settings_registry_sha256": "legacy/unknown",
                "config_runtime_schema_version": "1",
            },
            scope={"mode": "full_managed", "categories": [], "keys": list(scope_keys), "unknown_keys": list(unknown)},
            explicit_values=explicit,
            resolved_values=resolved,
            secrets={"included": bool(secret_items), "items": secret_items},
            compatibility={"status": "migration_required", "warnings": ["LEGACY_RAW_CONFIG_NO_BUNDLE_INTEGRITY"]},
            migrated_scope_keys=scope_keys,
            migration_steps=tuple(migrated.steps),
        )
        item = self.imports.put(parsed, hashlib.sha256(data).hexdigest(), session_token=session_token, legacy_raw=True)
        response = self._inspect_response(item)
        response["warnings"] = ["LEGACY_RAW_CONFIG_NO_BUNDLE_INTEGRITY"]
        return response

    def _materialize_candidate(
        self,
        parsed: ParsedBundle,
        *,
        expert: bool,
        skip_unknown: bool,
        secret_operations: Optional[Mapping[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], Tuple[Dict[str, Any], ...], Dict[str, str], Dict[str, Any]]:
        current_raw = dict(self.manager.candidate_base_config())
        candidate = dict(current_raw)
        issues = []
        origin: Dict[str, str] = {}
        unknown = tuple(sorted(set(parsed.scope.get("unknown_keys") or [])))
        if unknown:
            if not skip_unknown:
                issues.append(_issue(
                    "IMPORT_UNKNOWN_KEYS_REQUIRE_SKIP", blocking=True, keys=unknown,
                    message="Unbekannte Quellschlüssel werden nicht übernommen; das Überspringen muss ausdrücklich bestätigt werden.",
                ))
            elif not expert:
                issues.append(_issue("EXPERT_MODE_REQUIRED", blocking=True, keys=unknown))
            else:
                issues.append(_issue(
                    "IMPORT_UNKNOWN_KEYS_SKIPPED", blocking=False, keys=unknown,
                    message="Unbekannte Quellschlüssel werden übersprungen; vorhandene unbekannte Zielschlüssel bleiben erhalten.",
                ))

        known_scope = []
        for key in parsed.migrated_scope_keys:
            spec = SETTINGS_BY_KEY.get(key)
            if spec is None:
                continue
            if spec.editability.value != "editable" or spec.apply_class.value not in ("live_next_cycle", "restart_required"):
                continue
            known_scope.append(key)
            if spec.is_secret:
                continue
            # Source inheritance is represented by absence from explicit_values.
            candidate.pop(key, None)
            if key in parsed.explicit_values:
                candidate[key] = parsed.explicit_values[key]
                origin[key] = "explicit"
            else:
                origin[key] = "inherited"

        secret_ops = dict(secret_operations or {})
        secret_items = parsed.secrets.get("items", {}) if isinstance(parsed.secrets, Mapping) else {}
        for key in known_scope:
            spec = SETTINGS_BY_KEY.get(key)
            if spec is None or not spec.is_secret:
                continue
            op = secret_ops.get(key, "keep")
            if isinstance(op, Mapping):
                op = op.get("op", "keep")
            op = str(op)
            if op == "keep":
                origin[key] = "keep"
                continue
            if not expert:
                issues.append(_issue("EXPERT_MODE_REQUIRED", blocking=True, keys=(key,)))
                continue
            if op == "clear":
                candidate[key] = ""
                origin[key] = "clear"
                issues.append(_issue(
                    "IMPORT_SECRET_CLEAR_CONFIRMATION", blocking=False, keys=(key,), severity="confirm",
                    message="Das Secret wird ausdrücklich geleert. Diese irreversible Zieländerung muss im Commit bestätigt werden.",
                ))
                continue
            if op == "replace":
                meta = secret_items.get(key)
                if not isinstance(meta, Mapping) or not meta.get("included") or not isinstance(meta.get("value"), str):
                    issues.append(_issue("IMPORT_SECRET_REPLACEMENT_UNAVAILABLE", blocking=True, keys=(key,)))
                else:
                    candidate[key] = meta.get("value")
                    origin[key] = "replace"
                continue
            issues.append(_issue("SECRET_OPERATION_INVALID", blocking=True, keys=(key,)))

        # Resolve inherited values through the same canonical candidate parser as
        # SettingsRuntime/SettingsManager. This includes compatibility-derived
        # values such as SECOND_BATTERY_INTEGRATION_ENABLED and prevents a
        # parallel, simplified default interpretation in the artifact path.
        target_result = self.manager.validate_candidate(candidate, previous=self.manager.get_configured())
        target_view = dict(target_result.configured)
        default_drift = []
        for key in known_scope:
            if key in parsed.explicit_values or key not in parsed.resolved_values:
                continue
            spec = SETTINGS_BY_KEY.get(key)
            if spec is not None and spec.is_secret:
                continue
            source_value = parsed.resolved_values.get(key)
            target_value = target_view.get(key)
            if source_value != target_value:
                default_drift.append({"key": key, "source_resolved": source_value, "target_inherited": target_value})
                issues.append(_issue(
                    "INHERITED_DEFAULT_CHANGED", blocking=False, keys=(key,),
                    message="Der geerbte Default der Quelle unterscheidet sich vom aktuellen Zieldefault; der Zieldefault bleibt geerbt.",
                ))

        for warning in parsed.compatibility.get("warnings", []) if isinstance(parsed.compatibility, Mapping) else []:
            issues.append(_issue(str(warning), blocking=False))
        if parsed.migration_steps:
            issues.append(_issue("CONFIG_IMPORT_MIGRATED", blocking=False))

        meta = {
            "source_metadata": dict(parsed.source_metadata),
            "compatibility": dict(parsed.compatibility),
            "migration_steps": list(parsed.migration_steps),
            "scope": {"mode": parsed.scope.get("mode"), "keys": list(known_scope)},
            "skipped_keys": list(unknown) if skip_unknown else [],
            "unknown_source_keys": list(unknown),
            "default_drift": default_drift,
        }
        return candidate, tuple(issues), origin, meta

    def preview_import(
        self,
        token: str,
        *,
        base_revision: str,
        session_token: str,
        state_snapshot: Optional[Mapping[str, Any]] = None,
        expert: bool = False,
        skip_unknown: bool = False,
        secret_operations: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        item = self.imports.get(token, session_token)
        candidate, issues, origin, meta = self._materialize_candidate(
            item.parsed, expert=expert, skip_unknown=skip_unknown, secret_operations=secret_operations,
        )
        meta.update({"operation": "config_import", "artifact_id": item.token, "artifact_sha256": item.artifact_sha256, "legacy_raw": item.legacy_raw})
        return self.settings_service.preview_candidate(
            candidate,
            base_revision=base_revision,
            session_token=session_token,
            state_snapshot=state_snapshot,
            patch_issues=issues,
            metadata=meta,
            explicit_keys=tuple(candidate.keys()),
            origin_by_key=origin,
        )

    def preview_state(
        self,
        state_id: str,
        *,
        state_revision: str,
        base_revision: str,
        session_token: str,
        state_snapshot: Optional[Mapping[str, Any]] = None,
        expert: bool = False,
        secret_operations: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        read = self.state_store.get(state_id)
        if read.revision != str(state_revision or ""):
            raise ConfigStateError("CONFIG_STATE_REVISION_CONFLICT")
        candidate, issues, origin, meta = self._materialize_candidate(
            read.bundle, expert=expert, skip_unknown=True, secret_operations=secret_operations,
        )
        meta.update({"operation": "config_state_load", "artifact_id": state_id, "artifact_sha256": read.bundle.payload_sha256, "state_revision": read.revision})

        def revalidate() -> None:
            latest = self.state_store.get(state_id)
            if latest.revision != read.revision:
                raise RuntimeError("CONFIG_STATE_REVISION_CONFLICT")

        return self.settings_service.preview_candidate(
            candidate,
            base_revision=base_revision,
            session_token=session_token,
            state_snapshot=state_snapshot,
            patch_issues=issues,
            metadata=meta,
            source_revalidator=revalidate,
            explicit_keys=tuple(candidate.keys()),
            origin_by_key=origin,
        )
