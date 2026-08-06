# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from settings_apply_policy import ApplyPlan, build_apply_plan
from settings_registry import SETTINGS_BY_KEY, ApplyClass, Editability
from settings_runtime import CandidateResult, SettingsRuntimeManager
from settings_validation import ValidationContext, ValidationIssue, ValidationSeverity

PREVIEW_TTL_SECONDS = 300.0
MAX_PREVIEWS = 64


ISSUE_MESSAGES = {
    "CONFIG_ROOT_NOT_OBJECT": "Die Konfigurationsdatei muss ein JSON-Objekt enthalten.",
    "CONFIG_JSON_INVALID": "Die Konfigurationsdatei enthält ungültiges JSON.",
    "CONFIG_UTF8_INVALID": "Die Konfigurationsdatei ist nicht gültig UTF-8-codiert.",
    "PARSE_INT_REQUIRED": "Ein ganzzahliger Wert ist erforderlich.",
    "PARSE_INT_INVALID": "Der Wert muss eine ganze Zahl sein.",
    "PARSE_INT_BOOL_NOT_ALLOWED": "Ein Wahrheitswert ist hier keine gültige Zahl.",
    "PARSE_FLOAT_INVALID": "Der Wert muss eine gültige Dezimalzahl sein.",
    "PARSE_FLOAT_BOOL_NOT_ALLOWED": "Ein Wahrheitswert ist hier keine gültige Zahl.",
    "PARSE_FLOAT_NON_FINITE": "Unendliche Werte und NaN sind nicht zulässig.",
    "PARSE_VALUE_BELOW_MINIMUM": "Der Wert unterschreitet den zulässigen Mindestwert.",
    "PARSE_VALUE_ABOVE_MAXIMUM": "Der Wert überschreitet den zulässigen Höchstwert.",
    "PARSE_BOOL_INVALID": "Der Wert muss true oder false sein.",
    "PARSE_STRING_INVALID": "Der Wert muss Text sein.",
    "PARSE_ENUM_UNKNOWN_VALUE": "Der Wert ist keine zulässige Auswahl.",
    "PARSE_ENUM_INVALID_TYPE": "Die Auswahl muss als Text übertragen werden.",
    "PARSE_TIME_INVALID": "Die Uhrzeit muss im Format HH:MM angegeben werden.",
    "PARSE_TIME_INVALID_TYPE": "Die Uhrzeit muss als Text angegeben werden.",
    "PARSE_MM_DD_INVALID": "Das Datum muss im Format MM-TT angegeben werden.",
    "PARSE_MM_DD_INVALID_CALENDAR_DAY": "Der Kalendertag ist für den Monat ungültig.",
    "VAL-001": "MIN_SOC_PERCENT muss kleiner als MAX_SOC_PERCENT sein.",
    "VAL-002": "Die feste Entladung verletzt Leistung oder SOC-Schutzfenster.",
    "VAL-003": "Die feste Beladung verletzt Leistung oder SOC-Schutzfenster.",
    "VAL-004": "Beginn und Ende des Nachtfensters dürfen nicht identisch sein.",
    "VAL-005": "Der Nachtreserve-SOC muss innerhalb des globalen SOC-Schutzfensters liegen.",
    "VAL-006": "Cross-Charge oder Harvest erfordern die aktivierte Primärspeicher-Integration.",
    "VAL-007": "Restüberschuss-Harvest erfordert Primärspeicher-Integration und Cross-Charge-Schutz.",
    "VAL-008": "Für die gewählte Primärspeicherfunktion fehlt ein erforderlicher MQTT-Topic.",
    "VAL-009": "Für Harvest ist eine plausible maximale Primärspeicher-Ladeleistung erforderlich.",
    "VAL-010": "Die High-SOC-Hysterese muss Exit < Enter <= Full-SOC erfüllen.",
    "VAL-011": "Floor, Restart und Near-Limit müssen monoton bis zur Primärspeicher-Maximalleistung ansteigen.",
    "VAL-012": "Der absolute Watt-Override hat Vorrang vor der Verhältnisangabe.",
    "VAL-013": "Die Harvest-Zeitprofile müssen streng aufsteigend sein.",
    "VAL-014": "Der saisonale Parallelzeitraum ist unvollständig oder widersprüchlich.",
    "VAL-015": "Die neue Netzleistungsquelle benötigt vor Aktivierung einen erfolgreichen Preflight.",
    "VAL-016": "Bei mehreren SMA-Zählern muss eine eindeutige Seriennummer gewählt werden.",
    "VAL-017": "Mindestens eine Änderung wird erst nach Dienstneustart wirksam.",
    "VAL-018": "Das Abschalten des Messdaten-Loggings erzeugt eine irreversible Datenlücke.",
    "VAL-019": "SQLite-Enforce benötigt eine gesonderte geschützte Bestätigung.",
    "VAL-020": "V4-Enforce ist erst nach Katalog-, Coverage-, Restore- und Schutzprüfung zulässig.",
    "VAL-021": "Der SQLite-Pfad darf nur durch die geschützte Datenmigration geändert werden.",
    "VAL-022": "Der Dienstneustart erfüllt nicht alle Schutzbedingungen.",
    "VAL-023": "Der Secret-Vertrag wurde verletzt.",
    "VAL-024": "Unbekannte Konfigurationsschlüssel würden verloren gehen.",
    "MQTT_BROKER_MISSING": "Die MQTT-Broker-Adresse darf nicht leer sein.",
    "DEVICE_ID_INVALID": "Die Zendure-Geräte-ID ist leer oder enthält unzulässige MQTT-Zeichen.",
    "PATCH_UNKNOWN_KEY": "Der Schlüssel ist nicht als editierbare Einstellung registriert.",
    "PATCH_OPERATION_INVALID": "Die angeforderte Änderungsoperation ist nicht zulässig.",
    "PATCH_KEY_NOT_EDITABLE": "Die Einstellung ist in diesem Release nicht direkt editierbar.",
    "SECRET_OPERATION_INVALID": "Die Secretoperation ist nicht zulässig.",
    "SECRET_REPLACE_REQUIRES_VALUE": "Zum Ersetzen des Secrets ist ein neuer Wert erforderlich.",
    "PROTECTED_ACTION_REQUIRED": "Diese Änderung benötigt eine separate geschützte Aktion.",
}


@dataclass
class PreviewRecord:
    preview_id: str
    created_monotonic: float
    expires_monotonic: float
    base_revision: str
    candidate: Dict[str, Any]
    candidate_typed_revision: str
    diff: Tuple[Dict[str, Any], ...]
    issues: Tuple[Dict[str, Any], ...]
    apply_plan: ApplyPlan
    confirmations: Tuple[str, ...]
    session_token: str
    consumed: bool = False


class SettingsPreviewStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._items: Dict[str, PreviewRecord] = {}

    def _cleanup(self, now: float) -> None:
        expired = [key for key, item in self._items.items() if item.expires_monotonic <= now or item.consumed]
        for key in expired:
            self._items.pop(key, None)
        if len(self._items) > MAX_PREVIEWS:
            ordered = sorted(self._items.values(), key=lambda item: item.created_monotonic)
            for item in ordered[: len(self._items) - MAX_PREVIEWS]:
                self._items.pop(item.preview_id, None)

    def put(self, item: PreviewRecord) -> None:
        with self._lock:
            self._cleanup(time.monotonic())
            self._items[item.preview_id] = item

    def consume(self, preview_id: str, session_token: str) -> PreviewRecord:
        with self._lock:
            now = time.monotonic()
            self._cleanup(now)
            item = self._items.get(preview_id)
            if item is None or item.expires_monotonic <= now:
                raise KeyError("PREVIEW_EXPIRED_OR_UNKNOWN")
            if item.session_token != session_token:
                raise PermissionError("PREVIEW_SESSION_MISMATCH")
            if item.consumed:
                raise KeyError("PREVIEW_ALREADY_USED")
            item.consumed = True
            self._items.pop(preview_id, None)
            return item


class SettingsService:
    def __init__(self, manager: SettingsRuntimeManager):
        self.manager = manager
        self.previews = SettingsPreviewStore()

    @staticmethod
    def _issue_dict(issue: ValidationIssue) -> Dict[str, Any]:
        return {
            "code": issue.code,
            "severity": issue.severity.value,
            "keys": list(issue.keys),
            "message_id": issue.message_id,
            "message": ISSUE_MESSAGES.get(issue.message_id, ISSUE_MESSAGES.get(issue.code, issue.code)),
            "params": dict(issue.params),
            "source": issue.source,
            "blocking": issue.blocking,
        }

    @staticmethod
    def _synthetic_issue(code: str, key: str = "", *, blocking: bool = True) -> Dict[str, Any]:
        return {
            "code": code,
            "severity": "error" if blocking else "warning",
            "keys": [key] if key else [],
            "message_id": code,
            "message": ISSUE_MESSAGES.get(code, code),
            "params": {},
            "source": "patch",
            "blocking": blocking,
        }

    @staticmethod
    def _safe_value(key: str, value: Any) -> Any:
        spec = SETTINGS_BY_KEY.get(key)
        if spec is not None and spec.is_secret:
            return {"secret_set": bool(value)}
        return value

    def _base_config(self) -> Dict[str, Any]:
        method = getattr(self.manager, "candidate_base_config", None)
        if callable(method):
            return dict(method())
        return self.manager.get_configured()

    def _base_revision(self) -> str:
        method = getattr(self.manager, "cas_revision", None)
        if callable(method):
            return str(method())
        return self.manager.configured_revision()

    def preview(self, payload: Mapping[str, Any], session_token: str, state_snapshot: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        base_revision = str(payload.get("base_revision") or "")
        current_revision = self._base_revision()
        if base_revision != current_revision:
            raise RuntimeError("CONFIG_REVISION_CONFLICT")

        changes = payload.get("changes") or {}
        secrets_payload = payload.get("secrets") or {}
        if not isinstance(changes, Mapping) or not isinstance(secrets_payload, Mapping):
            raise ValueError("PATCH_INVALID")

        current_persisted = self._base_config()
        current = self.manager.get_configured()
        candidate = dict(current_persisted)
        patch_issues = []

        for key, operation in changes.items():
            spec = SETTINGS_BY_KEY.get(str(key))
            if spec is None:
                patch_issues.append(self._synthetic_issue("PATCH_UNKNOWN_KEY", str(key)))
                continue
            if spec.editability is not Editability.EDITABLE or spec.apply_class in (ApplyClass.PROTECTED_ACTION, ApplyClass.READ_ONLY, ApplyClass.MIGRATION_ONLY):
                patch_issues.append(self._synthetic_issue("PATCH_KEY_NOT_EDITABLE", spec.key))
                continue
            if spec.is_secret:
                # Secrets must use the explicit keep/replace/clear contract.
                # The generic patch channel is deliberately rejected even for
                # an otherwise authenticated and CSRF-valid caller.
                patch_issues.append(self._synthetic_issue("SECRET_OPERATION_INVALID", spec.key))
                continue
            if not isinstance(operation, Mapping):
                patch_issues.append(self._synthetic_issue("PATCH_OPERATION_INVALID", spec.key))
                continue
            op = operation.get("op")
            if op == "set":
                candidate[spec.key] = operation.get("value")
            elif op == "reset_default":
                candidate[spec.key] = spec.default_new_install
            else:
                patch_issues.append(self._synthetic_issue("PATCH_OPERATION_INVALID", spec.key))

        for key, operation in secrets_payload.items():
            spec = SETTINGS_BY_KEY.get(str(key))
            if spec is None or not spec.is_secret or spec.editability is not Editability.EDITABLE:
                patch_issues.append(self._synthetic_issue("PATCH_KEY_NOT_EDITABLE", str(key)))
                continue
            if not isinstance(operation, Mapping):
                patch_issues.append(self._synthetic_issue("SECRET_OPERATION_INVALID", spec.key))
                continue
            op = operation.get("op")
            if op == "keep":
                continue
            if op == "clear":
                candidate[spec.key] = ""
                continue
            if op == "replace":
                value = operation.get("value")
                if not isinstance(value, str) or value == "":
                    patch_issues.append(self._synthetic_issue("SECRET_REPLACE_REQUIRES_VALUE", spec.key))
                else:
                    candidate[spec.key] = value
                continue
            patch_issues.append(self._synthetic_issue("SECRET_OPERATION_INVALID", spec.key))

        # Read-only capability context. A changed grid source is accepted only if
        # its required static parameters are complete; live source preflight remains
        # visible in the restart/apply phase.
        grid_changed = candidate.get("GRID_METER_SOURCE") != current.get("GRID_METER_SOURCE")
        grid_ready = True
        if grid_changed:
            source = candidate.get("GRID_METER_SOURCE")
            if source == "sma_energy_meter_udp":
                grid_ready = bool(candidate.get("SMA_ENERGY_METER_GROUP") and candidate.get("SMA_ENERGY_METER_PORT"))
            elif source == "shelly_http":
                grid_ready = bool(candidate.get("SHELLY_IP"))
            else:
                grid_ready = False
        context = ValidationContext(
            previous=current,
            grid_source_candidate_ready=grid_ready,
            sma_multiple_devices_detected=bool((state_snapshot or {}).get("sma_energy_meter_multiple_devices_detected")),
            secret_contract_ok=True,
            unknown_keys_preserved=all(key in candidate for key in current_persisted if key not in SETTINGS_BY_KEY),
        )
        result: CandidateResult = self.manager.validate_candidate(candidate, previous=current, context=context)
        issues = list(patch_issues) + [self._issue_dict(issue) for issue in result.issues]

        blocking = any(bool(issue.get("blocking")) for issue in issues)
        if not result.valid:
            blocking = True
        apply_plan = build_apply_plan(result.configured if result.valid else candidate, self.manager.get())
        if apply_plan.blocking_keys:
            for key in apply_plan.blocking_keys:
                issues.append(self._synthetic_issue("PROTECTED_ACTION_REQUIRED", key))
            blocking = True

        diff = []
        if result.valid:
            keys = sorted(set(current) | set(result.configured))
            for key in keys:
                before = current.get(key)
                after = result.configured.get(key)
                if before == after:
                    continue
                spec = SETTINGS_BY_KEY.get(key)
                diff.append({
                    "key": key,
                    "label": spec.label if spec else key,
                    "old": self._safe_value(key, before),
                    "new": self._safe_value(key, after),
                    "apply_class": spec.apply_class.value if spec else "unknown",
                    "apply_text": spec.apply_text if spec else "Unknown key preserved",
                    "risk": spec.risk if spec else None,
                    "secret": bool(spec and spec.is_secret),
                })

        confirmations = tuple(sorted({
            issue["code"] for issue in issues
            if issue.get("severity") in ("confirm", "warning") and not issue.get("blocking")
        }))
        now = time.monotonic()
        preview_id = ""
        expires_at_epoch = None
        if not blocking and result.valid:
            preview_id = secrets.token_urlsafe(24)
            record = PreviewRecord(
                preview_id=preview_id,
                created_monotonic=now,
                expires_monotonic=now + PREVIEW_TTL_SECONDS,
                base_revision=base_revision,
                candidate=dict(result.persisted),
                candidate_typed_revision=result.typed_revision,
                diff=tuple(diff),
                issues=tuple(issues),
                apply_plan=apply_plan,
                confirmations=confirmations,
                session_token=session_token,
            )
            self.previews.put(record)
            expires_at_epoch = time.time() + PREVIEW_TTL_SECONDS

        return {
            "status": "blocked" if blocking else "ready",
            "preview_id": preview_id or None,
            "expires_at_epoch": expires_at_epoch,
            "base_revision": base_revision,
            "candidate_typed_revision": result.typed_revision or None,
            "diff": diff,
            "issues": issues,
            "confirmations_required": list(confirmations),
            "apply_plan": {
                "live_next_cycle": list(apply_plan.live_keys),
                "restart_required": list(apply_plan.restart_keys),
                "protected_actions": list(apply_plan.protected_action_keys),
                "read_only": list(apply_plan.read_only_keys),
                "migration_only": list(apply_plan.migration_only_keys),
            },
            "pending_restart_after_commit": bool(apply_plan.restart_keys or self.manager.pending_restart()),
        }

    def commit(self, payload: Mapping[str, Any], session_token: str) -> Dict[str, Any]:
        preview_id = str(payload.get("preview_id") or "")
        confirmations = set(str(value) for value in (payload.get("confirmations") or []))
        record = self.previews.consume(preview_id, session_token)
        if self._base_revision() != record.base_revision:
            raise RuntimeError("CONFIG_REVISION_CONFLICT")
        missing = set(record.confirmations) - confirmations
        if missing:
            raise PermissionError("CONFIRMATIONS_MISSING:" + ",".join(sorted(missing)))
        result = self.manager.commit_candidate(record.candidate, record.base_revision)
        plan: ApplyPlan = result["apply_plan"]
        return {
            "status": "committed",
            "configured_revision": result["configured_revision"],
            "typed_revision": result["typed_revision"],
            "effective_revision": result["effective_revision"],
            "changed_keys": list(plan.changed_keys),
            "live_applied_keys": list(plan.live_keys),
            "restart_required_keys": list(result["pending_restart_keys"]),
            "pending_restart": bool(result["pending_restart_keys"]),
        }
