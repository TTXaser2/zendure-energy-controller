# SPDX-License-Identifier: AGPL-3.0-or-later
"""Presentation contract for the V14 graph workspace.

WP7/WP8 deliberately keep machine/persistence ids owned by GraphQueryService and
adds only presentation/grouping metadata.  The browser may translate or restyle
these labels later without changing the V3 storage/query contract.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping

WORKSPACE_CONTRACT_VERSION = 2
WORKSPACE_MAX_WINDOW_MS = 48 * 60 * 60 * 1000
WORKSPACE_DEFAULT_WINDOW_MS = 24 * 60 * 60 * 1000
WORKSPACE_DEFAULT_PRESET = "24h"
WORKSPACE_MAX_SELECTED_SERIES = 18
INSPECTOR_DEFAULT_TOLERANCE_MS = 10_000
COMMAND_FOLLOW_DEFAULT_BEFORE_MS = 15_000
COMMAND_FOLLOW_DEFAULT_AFTER_MS = 180_000
COMMAND_FOLLOW_MAX_SIDE_MS = 10 * 60_000
EPISODE_COMPARE_DEFAULT_BEFORE_MS = 15 * 60_000
EPISODE_COMPARE_DEFAULT_AFTER_MS = 45 * 60_000
EPISODE_COMPARE_TRIGGER_LIMIT = 500

TERMS_DE: Dict[str, str] = {
    "graph.workspace.title": "Graph / Live-Verlauf",
    "graph.workspace.subtitle": "Zeitliche Zusammenhänge aus Graph Core V3 – geführt oder frei kombinierbar.",
    "graph.view.energy_balance": "Energiefluss",
    "graph.view.energy_balance.description": "Netz, PV, Haus und Speicherleistungen gemeinsam betrachten.",
    "graph.view.storage": "Speicher",
    "graph.view.storage.description": "SOC und Leistung der logischen Speicher sowie vorhandener Einzelgeräte.",
    "graph.view.control": "Regelung",
    "graph.view.control.description": "Mess- und Zielwertpipeline bis zum finalen Reglerziel nachvollziehen.",
    "graph.view.free": "Freie Auswahl",
    "graph.view.free.description": "Beliebige verfügbare System- und Geräteserien kombinieren.",
    "graph.group.grid": "Netz & Bilanz",
    "graph.group.storage": "Speicher",
    "graph.group.control": "Regelung",
    "graph.group.command": "Command",
    "graph.group.entity": "Geräte / Topologie",
    "graph.series.grid_power_w": "Netzleistung",
    "graph.series.raw_grid_power_w": "Netz Rohwert",
    "graph.series.control_grid_power_w": "Netz Regelwert",
    "graph.series.control_grid_power_smoothed_w": "Netz Regelwert geglättet",
    "graph.series.pv_power_w": "PV-Leistung",
    "graph.series.house_power_w": "Hausverbrauch",
    "graph.series.zendure_actual_power_w": "Zendure Istleistung",
    "graph.series.zendure_soc_percent": "Zendure SOC",
    "graph.series.primary_power_w": "Primärspeicher Leistung",
    "graph.series.primary_soc_percent": "Primärspeicher SOC",
    "graph.series.target_raw_w": "Ziel Rohwert",
    "graph.series.target_limited_w": "Ziel nach Limits",
    "graph.series.target_filtered_w": "Ziel gefiltert",
    "graph.series.target_step_limited_w": "Ziel nach Schrittbegrenzung",
    "graph.series.target_final_w": "Reglerziel final",
    "graph.series.command_desired_target_w": "Command Sollwert",
    "graph.series.command_readback_target_w": "Command Readback",
    "graph.entity_series.power_w": "Leistung",
    "graph.entity_series.soc_percent": "SOC",
    "graph.entity_series.target_w": "Sollwert",
    "graph.entity_series.readback_target_w": "Readback Sollwert",
    "graph.inspector.title": "Regler-Inspector",
    "graph.inspector.description": "Cursorpunkt mit Messwerten, Zielwertpipeline, Zuständen, Config, Topologie und Evidence.",
    "graph.command_follow.title": "Command-Follow / Ursache-Wirkung",
    "graph.command_follow.description": "Publish, beobachtete Reaktion, Readback, Tracking und Systemwirkung getrennt bewerten.",
    "graph.episode_comparison.title": "Episodenvergleich",
    "graph.episode_comparison.description": "Zwei persistiert verankerte Episoden relativ zu t=0 nebeneinander oder überlagert vergleichen.",
}

SERIES_GROUP: Dict[str, str] = {
    "grid_power_w": "grid",
    "raw_grid_power_w": "grid",
    "control_grid_power_w": "control",
    "control_grid_power_smoothed_w": "control",
    "pv_power_w": "grid",
    "house_power_w": "grid",
    "zendure_actual_power_w": "storage",
    "zendure_soc_percent": "storage",
    "primary_power_w": "storage",
    "primary_soc_percent": "storage",
    "target_raw_w": "control",
    "target_limited_w": "control",
    "target_filtered_w": "control",
    "target_step_limited_w": "control",
    "target_final_w": "control",
    "command_desired_target_w": "command",
    "command_readback_target_w": "command",
}

GUIDED_VIEWS: List[Dict[str, Any]] = [
    {
        "view_id": "energy_balance",
        "label_key": "graph.view.energy_balance",
        "description_key": "graph.view.energy_balance.description",
        "system_series": [
            "grid_power_w", "pv_power_w", "house_power_w",
            "zendure_actual_power_w", "primary_power_w",
        ],
        "entity_policy": "none",
        "entity_series": [],
        "default_window_ms": WORKSPACE_DEFAULT_WINDOW_MS,
    },
    {
        "view_id": "storage",
        "label_key": "graph.view.storage",
        "description_key": "graph.view.storage.description",
        "system_series": [
            "zendure_actual_power_w", "primary_power_w",
            "zendure_soc_percent", "primary_soc_percent",
        ],
        # Physical unit rows only exist after real per-unit telemetry.  Logical
        # storage rows remain available through the system-bound entities.
        "entity_policy": "physical_storage_units_if_present",
        "entity_series": ["power_w", "soc_percent"],
        "default_window_ms": WORKSPACE_DEFAULT_WINDOW_MS,
    },
    {
        "view_id": "control",
        "label_key": "graph.view.control",
        "description_key": "graph.view.control.description",
        "system_series": [
            "control_grid_power_w", "control_grid_power_smoothed_w",
            "target_raw_w", "target_limited_w", "target_filtered_w",
            "target_step_limited_w", "target_final_w",
        ],
        "entity_policy": "none",
        "entity_series": [],
        "default_window_ms": WORKSPACE_DEFAULT_WINDOW_MS,
    },
    {
        "view_id": "free",
        "label_key": "graph.view.free",
        "description_key": "graph.view.free.description",
        "system_series": ["grid_power_w", "zendure_actual_power_w", "zendure_soc_percent"],
        "entity_policy": "user_selected",
        "entity_series": [],
        "default_window_ms": WORKSPACE_DEFAULT_WINDOW_MS,
    },
]

TIME_PRESETS = [
    {"preset_id": "2h", "label": "2 Stunden", "window_ms": 2 * 60 * 60 * 1000},
    {"preset_id": "6h", "label": "6 Stunden", "window_ms": 6 * 60 * 60 * 1000},
    {"preset_id": "24h", "label": "24 Stunden", "window_ms": 24 * 60 * 60 * 1000},
    {"preset_id": "48h", "label": "48 Stunden", "window_ms": 48 * 60 * 60 * 1000},
]

CALENDAR_PRESETS = [
    {"preset_id": "today", "label": "Heute", "semantics": "LOCAL_TODAY_TO_NOW"},
    {"preset_id": "yesterday", "label": "Gestern", "semantics": "LOCAL_COMPLETE_PREVIOUS_DAY"},
    {"preset_id": "today_yesterday", "label": "Heute & Gestern", "semantics": "LOCAL_YESTERDAY_TO_NOW"},
    {"preset_id": "last_two_complete_days", "label": "Letzte 2 Kalendertage", "semantics": "LOCAL_TWO_COMPLETE_DAYS_BEFORE_TODAY"},
]


def _decorate_catalog(items: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for raw in items:
        item = dict(raw)
        item["label"] = TERMS_DE.get(str(item.get("label_key") or ""), str(item.get("series_id") or ""))
        item["group"] = SERIES_GROUP.get(str(item.get("series_id") or ""), "other")
        result.append(item)
    return result


def resolve_guided_views(views: Iterable[Mapping[str, Any]], entities: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Resolve topology-dependent guided selections from real entity catalog rows.

    Only persisted physical ``ZENDURE_UNIT`` rows may become automatic unit
    series. Logical storage roles stay represented by the system series and are
    therefore not duplicated. The product topology currently supports at most
    two controlled physical units in a guided storage view; additional historic
    identities remain available in Free Selection.
    """
    physical = [dict(item) for item in entities if str(item.get("entity_type") or "").upper() == "ZENDURE_UNIT"]
    physical.sort(key=lambda item: (-(int(item.get("last_seen_ms") or 0)), str(item.get("source_identity") or ""), str(item.get("stable_id") or "")))
    physical = physical[:2]
    result: List[Dict[str, Any]] = []
    for raw in views:
        view = dict(raw)
        resolved: List[Dict[str, str]] = []
        if str(view.get("entity_policy") or "") == "physical_storage_units_if_present":
            for entity in physical:
                stable_id = str(entity.get("stable_id") or "")
                available = set(str(x) for x in (entity.get("available_series") or []))
                if not stable_id:
                    continue
                for series_id in view.get("entity_series") or []:
                    sid = str(series_id)
                    if sid in available:
                        resolved.append({"stable_id": stable_id, "series_id": sid})
        view["resolved_entity_series"] = resolved
        result.append(view)
    return result


def workspace_manifest(catalog: Mapping[str, Any]) -> Dict[str, Any]:
    """Return the DB-independent browser contract for WP7/WP8.

    The manifest does not invent availability.  It only decorates the canonical
    GraphQueryService catalog; actual data, entities, coverage and evidence are
    still read through the V3 endpoints.
    """
    return {
        "workspace_contract_version": WORKSPACE_CONTRACT_VERSION,
        "query_contract": "graph_query_service_v1",
        "locale": "de",
        "default_view_id": "energy_balance",
        "default_time_preset": WORKSPACE_DEFAULT_PRESET,
        "default_window_ms": WORKSPACE_DEFAULT_WINDOW_MS,
        "max_window_ms": WORKSPACE_MAX_WINDOW_MS,
        "max_selected_series": WORKSPACE_MAX_SELECTED_SERIES,
        "inspector": {
            "contract_version": 2,
            "default_tolerance_ms": INSPECTOR_DEFAULT_TOLERANCE_MS,
            "click_to_inspect": True,
            "historical_config_scope": "SOC_AND_NIGHT_OVERLAY",
            "historical_entity_context": True,
            "historical_topology_context": True,
        },
        "command_follow": {
            "contract_version": 1,
            "default_before_ms": COMMAND_FOLLOW_DEFAULT_BEFORE_MS,
            "default_after_ms": COMMAND_FOLLOW_DEFAULT_AFTER_MS,
            "max_side_ms": COMMAND_FOLLOW_MAX_SIDE_MS,
            "publish_is_effectiveness_proof": False,
            "direction_is_effectiveness_proof": False,
            "system_effect_without_branch_target": "NOT_EVALUABLE",
        },
        "episode_comparison": {
            "contract_version": 1,
            "default_before_ms": EPISODE_COMPARE_DEFAULT_BEFORE_MS,
            "default_after_ms": EPISODE_COMPARE_DEFAULT_AFTER_MS,
            "max_window_ms": WORKSPACE_MAX_WINDOW_MS,
            "trigger_limit": EPISODE_COMPARE_TRIGGER_LIMIT,
            "allowed_trigger_sources": ["PUBLISHED_EVENT", "INTERVAL_START"],
            "allowed_interval_kinds": ["OPERATING_MODE", "CONTROL_INTENT", "CONTROL_REASON"],
            "max_episode_count": 2,
            "relative_axis": "t0_ms",
            "absolute_time_retained": True,
            "visual_similarity_is_causality_proof": False,
        },
        "time_presets": [dict(item) for item in TIME_PRESETS],
        "calendar_presets": [dict(item) for item in CALENDAR_PRESETS],
        "guided_views": resolve_guided_views(GUIDED_VIEWS, []),
        "terms": dict(TERMS_DE),
        "catalog": {
            "catalog_version": catalog.get("catalog_version"),
            "series": _decorate_catalog(catalog.get("series") or []),
            "entity_series": _decorate_catalog(catalog.get("entity_series") or []),
        },
        "capabilities": {
            "guided_views": True,
            "free_selection": True,
            "custom_time_range": True,
            "coverage_badges": True,
            "evidence_badges": True,
            "entity_series": True,
            "inspector": "available_wp8",
            "command_follow": "available_wp8",
            "episode_comparison": "available_wp9",
            "side_by_side": True,
            "overlay_pair_only": True,
            "synchronized_cursor": True,
        },
    }
