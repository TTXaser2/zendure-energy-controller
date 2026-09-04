# SPDX-License-Identifier: AGPL-3.0-or-later
"""Runtime/cutover boundary between existing history consumers and Graph Core V3.

WP6 contract:
- V3 consumers use GraphQueryService as the canonical historical API;
- existing V2 databases remain explicitly readable as legacy compatibility;
- Measurement V4 may enrich/fallback elsewhere but is never required here;
- graph/history readiness is diagnostic and must never gate controller readiness.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from graph_config_timeline import (
    build_day_segments,
    build_segments_from_rows,
    overlay_legend_transitions,
)
from graph_query_service import GRAPH_QUERY_SERVICE, GraphQueryError
from measurement_db import (
    detect_measurement_db_backend,
    query_graph_points,
    query_measurement_date_range,
    resolve_measurement_db_path,
)

SYSTEM_STORAGE_SERIES: Tuple[str, ...] = (
    "zendure_soc_percent",
    "zendure_actual_power_w",
    "primary_soc_percent",
    "primary_power_w",
)
ENTITY_STORAGE_SERIES: Tuple[str, ...] = ("soc_percent", "power_w")


def _date_from_ms(value: Any) -> str:
    try:
        return datetime.fromtimestamp(int(value) / 1000.0).date().isoformat()
    except Exception:
        return ""


def graph_history_runtime_status(config: Mapping[str, Any]) -> Dict[str, Any]:
    """Classify the current historical read path without mutating storage."""
    enabled = bool(config.get("MEASUREMENT_DB_ENABLED", True))
    path = resolve_measurement_db_path(dict(config))
    base: Dict[str, Any] = {
        "enabled": enabled,
        "db_path": path,
        "control_readiness_impact": "NONE",
        "measurement_v4_required": False,
        "legacy_history_readable": False,
        "workspace_ready": False,
        "history_data_available": False,
        "evidence_supported": False,
        "read_mode": "DISABLED" if not enabled else "UNAVAILABLE",
        "reason": "MEASUREMENT_DB_DISABLED" if not enabled else "GRAPH_DB_MISSING",
    }
    if not enabled:
        return base

    detection = detect_measurement_db_backend(path)
    backend = str(detection.get("backend") or "unknown")
    base.update({
        "backend": backend,
        "schema_version": detection.get("schema_version"),
    })
    if backend == "v3":
        try:
            native = GRAPH_QUERY_SERVICE.runtime_status(path)
        except GraphQueryError as exc:
            base.update({"read_mode": "V3_INVALID", "reason": str(exc)})
            return base
        base.update(native)
        capabilities = dict(native.get("capabilities") or {})
        persisted_evidence = bool(capabilities.get("evidence"))
        base.update({
            "read_mode": "V3_NATIVE",
            "reason": "READY" if native.get("workspace_ready") else "V3_REQUIRED_TABLES_MISSING",
            "legacy_history_readable": True,
            # Even pre-WP5 V3 stores can derive bounded evidence from core
            # persisted spans. WP5 tables upgrade this to persisted evidence.
            "evidence_supported": bool(capabilities.get("coverage")),
            "persisted_evidence_supported": persisted_evidence,
            "evidence_mode": "PERSISTED_WP5" if persisted_evidence else "DERIVED_V3_FALLBACK",
            "available_from": _date_from_ms(native.get("available_from_ms")),
            "available_to": _date_from_ms(native.get("available_to_ms")),
        })
        return base

    if backend == "v2":
        date_range = query_measurement_date_range(dict(config))
        base.update({
            "read_mode": "LEGACY_V2_COMPAT",
            "reason": "LEGACY_V2_READ_COMPATIBLE",
            "legacy_history_readable": True,
            "workspace_ready": False,
            "history_data_available": bool(date_range.get("available_from") or date_range.get("available_to")),
            "evidence_supported": False,
            "available_from": date_range.get("available_from") or "",
            "available_to": date_range.get("available_to") or "",
            "capabilities": {
                "overview": False,
                "inspector": False,
                "entities": False,
                "config_timeline": True,
                "coverage": False,
                "evidence": False,
                "retention_evidence": False,
            },
        })
        return base

    if backend == "missing":
        return base

    base.update({
        "read_mode": "INVALID",
        "reason": str(detection.get("error") or "UNKNOWN_DB_SCHEMA"),
        "db_error": str(detection.get("error") or ""),
    })
    return base


def _minute_index(ts_ms: int, day_start: datetime) -> Optional[int]:
    minute = int((datetime.fromtimestamp(int(ts_ms) / 1000.0) - day_start).total_seconds() // 60)
    return minute if 0 <= minute <= 1440 else None


def _entity_minute_maps(entity_payload: Mapping[str, Any], day_start: datetime) -> Dict[int, Dict[str, Any]]:
    timestamps = list(entity_payload.get("timestamps_ms") or [])
    series = dict(entity_payload.get("series") or {})
    soc_values = list(series.get("soc_percent") or [])
    power_values = list(series.get("power_w") or [])
    result: Dict[int, Dict[str, Any]] = {}
    for index, ts in enumerate(timestamps):
        minute = _minute_index(int(ts), day_start)
        if minute is None:
            continue
        result[minute] = {
            "soc": soc_values[index] if index < len(soc_values) else None,
            "power_w": power_values[index] if index < len(power_values) else None,
        }
    return result


def _v3_storage_day(
    config: Mapping[str, Any],
    day_start: datetime,
    day_end: datetime,
    *,
    current_effective_config: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    path = resolve_measurement_db_path(dict(config))
    start_ms = int(day_start.timestamp() * 1000)
    end_ms = int(day_end.timestamp() * 1000)

    points, compat_meta = GRAPH_QUERY_SERVICE.compatibility_points(path, start_ms, end_ms, limit=2000)
    overview_meta = dict(compat_meta.get("overview_meta") or {})

    config_payload = GRAPH_QUERY_SERVICE.config_timeline(path, start_ms, end_ms)
    config_rows = list(config_payload.get("items") or [])
    segments, timeline_meta = build_segments_from_rows(
        config_rows,
        day_start,
        day_end,
        current_effective_config=current_effective_config,
        meta={
            "timeline_status": "hit" if config_rows else "empty",
            "db_path": path,
            "query_source": "graph_query_service_v1",
            "query_meta": dict(config_payload.get("meta") or {}),
        },
    )

    entities_payload: Dict[str, Any] = {"entities": {}, "meta": {}}
    try:
        entities_payload = GRAPH_QUERY_SERVICE.entity_overview(
            path,
            start_ms,
            end_ms,
            series_ids=ENTITY_STORAGE_SERIES,
            resolution="1min",
        )
    except Exception as exc:
        entities_payload = {"entities": {}, "meta": {"error": str(exc), "status": "UNAVAILABLE"}}

    all_entities = dict(entities_payload.get("entities") or {})
    physical = [
        item for item in all_entities.values()
        if str((item.get("entity") or {}).get("entity_type") or "") == "ZENDURE_UNIT"
    ]
    physical.sort(key=lambda item: (
        str((item.get("entity") or {}).get("source_identity") or ""),
        str((item.get("entity") or {}).get("stable_id") or ""),
    ))
    physical = physical[:2]
    physical_maps = [_entity_minute_maps(item, day_start) for item in physical]
    unit_labels = [
        str((item.get("entity") or {}).get("display_name") or (item.get("entity") or {}).get("stable_id") or f"Zendure {index + 1}")
        for index, item in enumerate(physical)
    ]

    controlled = all_entities.get("storage:controlled") or {}
    primary = all_entities.get("storage:primary") or {}
    controlled_entity = dict(controlled.get("entity") or {})
    primary_entity = dict(primary.get("entity") or {})

    result_points: List[Dict[str, Any]] = []
    for point in points:
        minute = _minute_index(int(point.get("epoch_ms") or 0), day_start)
        if minute is None:
            continue
        item: Dict[str, Any] = {
            "minute": minute,
            "time": datetime.fromtimestamp(int(point["epoch_ms"]) / 1000.0).strftime("%H:%M"),
            "zendure_soc": point.get("soc"),
            "zendure_power_w": point.get("zendure_actual_power_w"),
            "primary_soc": point.get("primary_soc"),
            "primary_power_w": point.get("primary_power_w"),
            "mode": point.get("mode"),
            "reason": point.get("control_reason") or point.get("limit_reason") or "",
            "safe_state": bool(point.get("safe_state_active")),
            "night_window": bool(point.get("night_window_active")),
        }
        if physical_maps:
            unit_one = physical_maps[0].get(minute) or {}
            item["zendure_unit_1_soc"] = unit_one.get("soc")
            item["zendure_unit_1_power_w"] = unit_one.get("power_w")
            if len(physical_maps) > 1:
                unit_two = physical_maps[1].get(minute) or {}
                item["zendure_unit_2_soc"] = unit_two.get("soc")
                item["zendure_unit_2_power_w"] = unit_two.get("power_w")
        else:
            item["zendure_unit_1_soc"] = point.get("soc")
            item["zendure_unit_1_power_w"] = point.get("zendure_actual_power_w")
            item["zendure_unit_2_soc"] = None
            item["zendure_unit_2_power_w"] = None
        result_points.append(item)

    coverage: Dict[str, Any]
    try:
        coverage = GRAPH_QUERY_SERVICE.coverage(path, series_ids=SYSTEM_STORAGE_SERIES)
    except Exception as exc:
        coverage = {"series": {}, "meta": {"error": str(exc), "status": "UNAVAILABLE"}}

    evidence: Dict[str, Any]
    try:
        evidence = GRAPH_QUERY_SERVICE.evidence(
            path,
            start_ms,
            end_ms,
            series_ids=SYSTEM_STORAGE_SERIES,
            resolution="1min",
        )
    except Exception as exc:
        evidence = {
            "series": {},
            "meta": {"error": str(exc), "status": "NOT_SUPPORTED_OR_UNAVAILABLE"},
            "resolution": "1min",
        }

    runtime = graph_history_runtime_status(config)
    return {
        "points": result_points,
        "source": "graph_core_v3_1min",
        "read_mode": "V3_NATIVE",
        "runtime": runtime,
        "config_segments": segments,
        "config_timeline": timeline_meta,
        "config_legend": overlay_legend_transitions(segments),
        "coverage": coverage,
        "evidence": evidence,
        "entities": all_entities,
        "zendure_unit_count": len(physical) if physical else 1,
        "unit_labels": unit_labels or [str(controlled_entity.get("display_name") or "Zendure")],
        "primary_storage_present": bool(primary_entity),
        "primary_display_name": str(primary_entity.get("display_name") or ""),
        "controlled_display_name": str(controlled_entity.get("display_name") or "Zendure"),
        "available_from": runtime.get("available_from") or "",
        "available_to": runtime.get("available_to") or "",
        "meta": {
            "compatibility": compat_meta,
            "overview": overview_meta,
            "config_timeline": dict(config_payload.get("meta") or {}),
            "entities": dict(entities_payload.get("meta") or {}),
        },
    }


def _legacy_storage_day(
    config: Mapping[str, Any],
    day_start: datetime,
    day_end: datetime,
    *,
    current_effective_config: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    points, meta = query_graph_points(dict(config), day_start, day_end, limit=2000)
    result_points: List[Dict[str, Any]] = []
    for point in points:
        minute = _minute_index(int(point.get("epoch_ms") or 0), day_start)
        if minute is None:
            continue
        result_points.append({
            "minute": minute,
            "time": datetime.fromtimestamp(int(point["epoch_ms"]) / 1000.0).strftime("%H:%M"),
            "zendure_soc": point.get("soc"),
            "zendure_unit_1_soc": point.get("soc"),
            "zendure_unit_2_soc": None,
            "primary_soc": point.get("primary_soc"),
            "zendure_power_w": point.get("zendure_actual_power_w"),
            "primary_power_w": point.get("primary_power_w"),
            "mode": point.get("mode"),
            "reason": point.get("control_reason") or point.get("limit_reason") or "",
            "safe_state": bool(point.get("safe_state_active")),
            "night_window": bool(point.get("night_window_active")),
        })
    segments, timeline_meta = build_day_segments(
        config,
        day_start,
        day_end,
        current_effective_config=current_effective_config,
    )
    date_range = query_measurement_date_range(dict(config))
    return {
        "points": result_points,
        "source": "measurement_db_v2_compat",
        "read_mode": "LEGACY_V2_COMPAT",
        "runtime": graph_history_runtime_status(config),
        "config_segments": segments,
        "config_timeline": timeline_meta,
        "config_legend": overlay_legend_transitions(segments),
        "coverage": {"series": {}, "meta": {"status": "NOT_SUPPORTED_ON_V2"}},
        "evidence": {"series": {}, "meta": {"status": "NOT_SUPPORTED_ON_V2"}},
        "entities": {},
        "zendure_unit_count": 1,
        "unit_labels": ["Zendure"],
        "primary_storage_present": True,
        "primary_display_name": "",
        "controlled_display_name": "Zendure",
        "available_from": date_range.get("available_from") or "",
        "available_to": date_range.get("available_to") or "",
        "meta": {"compatibility": meta},
    }


def query_storage_day_history(
    config: Mapping[str, Any],
    day_start: datetime,
    day_end: datetime,
    *,
    current_effective_config: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Return one coherent status-day history payload across V3/V2 cutover."""
    status = graph_history_runtime_status(config)
    mode = str(status.get("read_mode") or "")
    if mode == "V3_NATIVE":
        try:
            return _v3_storage_day(
                config,
                day_start,
                day_end,
                current_effective_config=current_effective_config,
            )
        except Exception as exc:
            return {
                "points": [],
                "source": "graph_core_v3_error",
                "read_mode": "V3_NATIVE",
                "runtime": dict(status, reason="V3_QUERY_ERROR", query_error=str(exc)),
                "config_segments": [],
                "config_timeline": {"timeline_status": "error", "timeline_error": str(exc)},
                "config_legend": {"max_soc": [], "reserve_soc": [], "min_soc": [], "night_window": []},
                "coverage": {"series": {}, "meta": {"error": str(exc)}},
                "evidence": {"series": {}, "meta": {"error": str(exc)}},
                "entities": {},
                "zendure_unit_count": 1,
                "unit_labels": ["Zendure"],
                "primary_storage_present": True,
                "primary_display_name": "",
                "controlled_display_name": "Zendure",
                "available_from": status.get("available_from") or "",
                "available_to": status.get("available_to") or "",
                "meta": {"error": str(exc)},
            }
    if mode == "LEGACY_V2_COMPAT":
        return _legacy_storage_day(
            config,
            day_start,
            day_end,
            current_effective_config=current_effective_config,
        )
    return {
        "points": [],
        "source": "history_unavailable",
        "read_mode": mode or "UNAVAILABLE",
        "runtime": status,
        "config_segments": [],
        "config_timeline": {"timeline_status": "unavailable"},
        "config_legend": {"max_soc": [], "reserve_soc": [], "min_soc": [], "night_window": []},
        "coverage": {"series": {}, "meta": {"status": "UNAVAILABLE"}},
        "evidence": {"series": {}, "meta": {"status": "UNAVAILABLE"}},
        "entities": {},
        "zendure_unit_count": 1,
        "unit_labels": ["Zendure"],
        "primary_storage_present": True,
        "primary_display_name": "",
        "controlled_display_name": "Zendure",
        "available_from": status.get("available_from") or "",
        "available_to": status.get("available_to") or "",
        "meta": {},
    }
