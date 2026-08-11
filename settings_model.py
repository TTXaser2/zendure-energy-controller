# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from settings_registry import SETTINGS, SETTINGS_BY_KEY, Visibility, ApplyClass, Editability, DefaultClass, ResetPolicy
from settings_help import (CATEGORY_GROUPS, CATEGORY_DESCRIPTIONS, SECTION_ORDER_OVERRIDES, SETTING_ORDER_OVERRIDES, LABEL_OVERRIDES, DEPENDENCY_RULES, HANDBOOK_GLOSSARY, build_category_specs, build_section_specs)
from settings_runtime import SettingsRuntimeManager
from settings_service import ISSUE_MESSAGES

CATEGORY_SPECS = build_category_specs()
def _operational_specs():
    return tuple(
        spec for spec in SETTINGS
        if spec.visibility not in (Visibility.HIDDEN_MIGRATION, Visibility.HIDDEN_TRANSITION)
        and (spec.release_stage == "S1" or spec.origin == "RC19")
        and not spec.lifecycle.startswith("remove_")
        and spec.lifecycle not in ("reserved_inactive", "deployment_constant_not_config")
    )


SECTION_SPECS = build_section_specs(tuple(dict.fromkeys((spec.category, spec.section) for spec in _operational_specs())))


def _format_default_value(value: Any, unit: Optional[str]) -> str:
    if value is None:
        return "nicht gesetzt"
    if isinstance(value, bool):
        text = "Ein" if value else "Aus"
    else:
        text = str(value)
    return f"{text}{f' {unit}' if unit else ''}"


def _default_ui_policy(spec: Any) -> Dict[str, Any]:
    if spec.is_secret or spec.editability is not Editability.EDITABLE:
        return {"kind": "none", "meta": spec.default_help if not spec.is_secret else "", "action": None}
    kind = spec.default_class
    if kind is DefaultClass.INSTALLATION:
        return {"kind": "installation", "meta": spec.default_help, "action": None}
    if kind is DefaultClass.LEGACY_INTERNAL:
        return {"kind": "none", "meta": spec.default_help, "action": None}
    if kind is DefaultClass.AUTO_OR_UNSET:
        return {"kind": "auto" if spec.reset_policy is ResetPolicy.AUTO else "clear", "meta": spec.default_help, "action": spec.reset_label, "value": spec.reset_value}
    if kind is DefaultClass.PROFILE_PRESET:
        profile = {"EVCC_STANDARD":"EVCC Standard", "HARVEST_ZEC_STANDARD":"ZEC Standardstrategie", "MANUAL_PROFILE":"Manuelles Profil", "NIGHT_PROFILE":"ZEC Nachtprofil"}.get(spec.profile_id, spec.profile_id or "Profil")
        return {"kind": "profile", "meta": f"Profilwert ({profile}): {_format_default_value(spec.reset_value, spec.unit)} · kein universeller Einzeldefault", "action": spec.reset_label, "value": spec.reset_value}
    if kind is DefaultClass.SAFE_SENTINEL:
        return {"kind": "sentinel", "meta": f"Sicherer Ausgangszustand: {_format_default_value(spec.bootstrap_value, spec.unit)} · kein empfohlener Betriebswert", "action": spec.reset_label, "value": spec.reset_value}
    return {"kind": "default", "meta": f"Produktdefault: {_format_default_value(spec.product_default, spec.unit)}", "action": spec.reset_label, "value": spec.reset_value}


def _safe_value(key: str, value: Any) -> Any:
    spec = SETTINGS_BY_KEY.get(key)
    if spec is not None and spec.is_secret:
        return None
    return value


def _description(key: str, spec: Any) -> str:
    return spec.help.short_help


def _handbook_payload(ref: Any) -> Optional[Dict[str, Any]]:
    if ref is None:
        return None
    return {"section_id": ref.section_id, "section_title": ref.section_title, "page": ref.page, "url": f"/manual.pdf#page={ref.page}"}


def _help_payload(spec: Any) -> Dict[str, Any]:
    help_spec = spec.help
    example = None
    if help_spec.example is not None:
        example = {
            "title": help_spec.example.title,
            "inputs": list(help_spec.example.inputs),
            "calculation": help_spec.example.calculation,
            "result": help_spec.example.result,
            "interpretation": help_spec.example.interpretation,
        }
    return {
        "level": help_spec.help_level,
        "short": help_spec.short_help,
        "extended": help_spec.extended_help,
        "when": help_spec.when_help,
        "effect_increase": help_spec.effect_increase,
        "effect_decrease": help_spec.effect_decrease,
        "effect_enable": help_spec.effect_enable,
        "effect_disable": help_spec.effect_disable,
        "option_help": [{"value": value, "text": text} for value, text in help_spec.option_help],
        "dependencies": [{"relation": dep.relation, "key": dep.key, "text": dep.text} for dep in help_spec.dependencies],
        "dependency_help": help_spec.dependency_help,
        "override": help_spec.override_help,
        "risk": help_spec.risk_help,
        "example": example,
        "formula": help_spec.formula_text,
        "search_terms": list(help_spec.search_terms),
        "guidance_rule_ids": list(help_spec.guidance_rule_ids),
        "evidence_refs": list(help_spec.evidence_refs),
        "handbook": _handbook_payload(help_spec.handbook_ref),
    }


def build_settings_model(
    manager: SettingsRuntimeManager,
    state_snapshot: Optional[Mapping[str, Any]] = None,
    *,
    csrf_token: str = "",
) -> Dict[str, Any]:
    configured = manager.get_configured()
    effective = manager.get()
    status = manager.status()
    inherited = set(status.get("inherited_default_keys") or [])
    pending = set(status.get("pending_restart_keys") or [])
    issue_by_key: Dict[str, List[Dict[str, Any]]] = {}
    for issue in status.get("issues") or []:
        issue = dict(issue)
        issue["message"] = ISSUE_MESSAGES.get(issue.get("message_id") or issue.get("code"), issue.get("code"))
        for key in issue.get("keys") or ["__global__"]:
            issue_by_key.setdefault(key, []).append(issue)

    categories: Dict[str, Dict[str, Any]] = {}
    for spec in SETTINGS:
        # S1 shows the active RC19/S1 surface. Later-release target-only fields
        # remain in the registry but are not presented as operational settings.
        if spec.visibility in (
            Visibility.HIDDEN_MIGRATION,
            Visibility.HIDDEN_TRANSITION,
        ):
            continue
        if spec.release_stage != "S1" and spec.origin != "RC19":
            continue
        if spec.lifecycle.startswith("remove_") or spec.lifecycle in ("reserved_inactive", "deployment_constant_not_config"):
            continue

        category_spec = CATEGORY_SPECS.get(spec.category)
        category = categories.setdefault(spec.category, {
            "name": spec.category,
            "group": CATEGORY_GROUPS.get(spec.category, "D. Daten, System & Diagnose"),
            "description": CATEGORY_DESCRIPTIONS.get(spec.category, ""),
            "help": category_spec.help_text if category_spec else CATEGORY_DESCRIPTIONS.get(spec.category, ""),
            "handbook": _handbook_payload(category_spec.handbook_ref) if category_spec else None,
            "sections": {},
            "setting_count": 0,
        })
        section_spec = SECTION_SPECS.get((spec.category, spec.section))
        section = category["sections"].setdefault(spec.section, {
            "name": spec.section,
            "help": section_spec.help_text if section_spec else "",
            "handbook": _handbook_payload(section_spec.handbook_ref) if section_spec else None,
            "settings": [],
        })
        configured_value = configured.get(spec.key, spec.default_new_install)
        effective_value = effective.get(spec.key, spec.default_new_install)
        available = spec.release_stage == "S1" or spec.origin == "RC19"
        editable = bool(
            available
            and spec.editability is Editability.EDITABLE
            and spec.apply_class not in (ApplyClass.PROTECTED_ACTION, ApplyClass.READ_ONLY, ApplyClass.MIGRATION_ONLY)
        )
        entry = {
            "key": spec.key,
            "label": LABEL_OVERRIDES.get(spec.key, spec.label),
            "description": _description(spec.key, spec),
            "help": _help_payload(spec),
            "value_type": spec.value_type.value,
            "codec_id": spec.codec_id,
            "configured": _safe_value(spec.key, configured_value),
            "effective": _safe_value(spec.key, effective_value),
            "configured_state": "secret_set" if spec.is_secret and bool(configured_value) else ("secret_not_set" if spec.is_secret else "configured"),
            "secret_set": bool(configured_value) if spec.is_secret else False,
            "default": None if spec.is_secret or spec.reset_policy is ResetPolicy.NONE else spec.reset_value,
            "bootstrap_value": None if spec.is_secret else spec.bootstrap_value,
            "product_default": None if spec.is_secret else spec.product_default,
            "default_class": spec.default_class.value,
            "reset_policy": spec.reset_policy.value,
            "required_first_install": spec.required_first_install,
            "profile_id": spec.profile_id,
            "default_ui": _default_ui_policy(spec),
            "default_state": "set" if spec.is_secret and bool(spec.default_new_install) else ("not_set" if spec.is_secret else None),
            "minimum": spec.minimum,
            "maximum": spec.maximum,
            "unit": spec.unit,
            "options": [{"value": value, "label": label} for value, label in spec.options],
            "visibility": spec.visibility.value,
            "expert": spec.visibility is not Visibility.STANDARD,
            "protected": spec.visibility is Visibility.PROTECTED_EXPERT,
            "editable": editable,
            "available": available,
            "apply_class": spec.apply_class.value,
            "apply_text": spec.apply_text,
            "risk": spec.risk,
            "dependency_keys": list(spec.dependency_keys),
            "dependency_rule": DEPENDENCY_RULES.get(spec.key),
            "validation_text": spec.validation_text,
            "validator_ids": list(spec.validator_ids),
            "inherited_default": spec.key in inherited,
            "pending_restart": spec.key in pending,
            "configured_differs_effective": configured_value != effective_value,
            "issues": issue_by_key.get(spec.key, []),
            "config_key_visible": spec.visibility is not Visibility.STANDARD,
            "release_stage": spec.release_stage,
            "ui_order": SETTING_ORDER_OVERRIDES.get(spec.key, 10000 + spec.order),
            "lifecycle": spec.lifecycle,
            "portability_class": spec.portability_class.value,
            "portable_profile": spec.portability_class.value == "portable_profile",
        }
        section["settings"].append(entry)
        category["setting_count"] += 1

    category_list = []
    for category in categories.values():
        section_order = {name: idx for idx, name in enumerate(SECTION_ORDER_OVERRIDES.get(category["name"], ()), start=1)}
        sections = list(category["sections"].values())
        for section in sections:
            section["settings"].sort(key=lambda item: (item.get("ui_order", 10000), item.get("key", "")))
        sections.sort(key=lambda section: (section_order.get(section["name"], 10000), section["name"]))
        for section in sections:
            for item in section["settings"]:
                item.pop("ui_order", None)
        category["sections"] = sections
        category_list.append(category)

    return {
        "schema": "ZEC-SETTINGS-MODEL-V1",
        "controller_version": manager.app_version,
        "csrf_token": csrf_token,
        "base_revision": getattr(manager, "cas_revision", manager.configured_revision)(),
        "configured_revision": manager.configured_revision(),
        "typed_revision": manager.typed_config_revision(),
        "effective_revision": manager.effective_revision(),
        "status": status,
        "categories": category_list,
        "glossary": _handbook_payload(HANDBOOK_GLOSSARY),
        "global_issues": issue_by_key.get("__global__", []),
        "unknown_keys": sorted(key for key in configured if key not in SETTINGS_BY_KEY),
        "capabilities": {
            "preview_commit": True,
            "restart_action": bool(effective.get("WEB_SERVICE_RESTART_ENABLED", False)),
            "storage_probe": True,
            "last_good_pointer_repair": bool(status.get("last_good_store_repair_required")),
            "config_states": True,
            "config_import_export": True,
            "portable_profiles": True,
        },
        "runtime": {
            "current_mode": (state_snapshot or {}).get("current_mode"),
            "ready": (state_snapshot or {}).get("ready"),
            "battery_soc": (state_snapshot or {}).get("battery_soc"),
            "interval_seconds": effective.get("INTERVAL_SECONDS"),
        },
    }
