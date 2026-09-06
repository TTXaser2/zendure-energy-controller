# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared pure controller-state projection for persistence consumers.

V14.1.3 moves the small operating-mode/control-intent projection out of the
Measurement-V4 writer so Graph Core V3 can persist the same semantics even when
Measurement V4 logging is disabled.  The functions are intentionally pure and
perform no I/O or controller mutation.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _bool01(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "ja"}


def _csv_list(value: Any) -> List[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, Iterable):
        return [str(part).strip() for part in value if str(part).strip()]
    return [str(value).strip()]


def map_target_reason(
    reason: str,
    operating_mode: str,
    target_final: Optional[float],
    active_limiters: List[str],
    row: Mapping[str, Any],
) -> str:
    """Return the canonical V4/Graph target-reason code.

    This is the existing V4 mapping moved verbatim into a shared pure module.
    """
    raw = str(reason or "").upper()
    upper_limiters = {str(item).upper() for item in active_limiters}
    cross_charge_active = (
        _bool01(row.get("cross_charge_guard_active"))
        or _bool01(row.get("cross_charge_guard_limited"))
        or "CROSS_CHARGE" in upper_limiters
        or "SMA_DISCHARGE" in upper_limiters
        or "CROSS_CHARGE" in raw
        or "BLOCKED_BY_SMA" in raw
    )
    if operating_mode == "NIGHT_DISCHARGE":
        return "NIGHT_BASE_DISCHARGE"
    stop_reason = str(row.get("night_discharge_stop_reason", "") or "").upper()
    if "RESERVE" in stop_reason:
        return "NIGHT_RESERVE_STOP"
    if "WINDOW" in stop_reason or "ENDED" in stop_reason:
        return "NIGHT_WINDOW_ENDED_NEUTRALIZED"
    if operating_mode == "FIXED_CHARGE":
        return "FIXED_CHARGE"
    if operating_mode == "FIXED_DISCHARGE":
        return "FIXED_DISCHARGE"
    if operating_mode == "STOP_HOLD":
        return "MANUAL_STOP"
    if "MIN_SOC" in raw or "SOC ZU NIEDRIG" in raw or "MIN_SOC" in upper_limiters:
        return "MIN_SOC_LIMIT"
    if "MAX_SOC" in raw or "SOC ZU HOCH" in raw or "MAX_SOC" in upper_limiters:
        return "MAX_SOC_LIMIT"
    if str(operating_mode or "").upper() == "SAFE_STATE":
        return "SAFE_STATE"
    if cross_charge_active:
        return "CROSS_CHARGE_BLOCKED" if target_final == 0 else "CROSS_CHARGE_REDUCED"
    if "REST_SURPLUS" in raw or "HARVEST" in raw or "RESTÜBERSCHUSS" in raw or "RESTUEBERSCHUSS" in raw or "ERNTE" in raw:
        return "REST_SURPLUS_HARVEST"
    if "DEADBAND" in raw:
        return "DEADBAND"
    if "DISCONNECT" in raw or "MQTT" in raw:
        return "MQTT_DISCONNECTED" if "DISCONNECT" in raw else "ZENDURE_MQTT_STALE"
    if "GRID" in raw and "STALE" in raw:
        return "GRID_STALE"
    if "SOC" in raw and "STALE" in raw:
        return "SOC_STALE"
    if "RAMP" in raw or "STEP" in raw:
        return "STEP_LIMIT"
    if "SMOOTH" in raw:
        return "SMOOTHING"
    if target_final is not None:
        if target_final > 0:
            return "AUTO_GRID_EXPORT"
        if target_final < 0:
            return "AUTO_GRID_IMPORT"
        return "DEADBAND"
    return "UNKNOWN"


def map_operating_mode(mode: str, *, target_reason: str = "", row: Optional[Mapping[str, Any]] = None) -> str:
    raw = str(mode or "").upper()
    reason = str((row or {}).get("control_reason", (row or {}).get("target_final_reason", "")) or "").upper()
    # The legacy controller internally uses SAFE_STATE also as a neutralizing
    # helper for SOC limits.  In persisted analysis semantics these are normal
    # target limiters, not fault modes.
    if raw == "SAFE_STATE" and target_reason in {"MAX_SOC_LIMIT", "MIN_SOC_LIMIT"}:
        return "AUTO"
    if raw == "SAFE_STATE" and ("SOC ZU HOCH" in reason or "SOC ZU NIEDRIG" in reason):
        return "AUTO"
    if raw in {"AUTO", "HOLD", "HOLD_DEADBAND", "NIGHT_DISCHARGE", "STOP_HOLD", "SAFE_STATE"}:
        return raw
    if raw in {"MANUAL_FIXED_CHARGE", "FIXED_CHARGE"}:
        return "FIXED_CHARGE"
    if raw in {"MANUAL_FIXED_DISCHARGE", "FIXED_DISCHARGE"}:
        return "FIXED_DISCHARGE"
    if raw in {"CHARGE", "DISCHARGE", "CHARGE_RAMP_DOWN", "DISCHARGE_RAMP_DOWN", "BLOCKED_BY_SMA"}:
        return "AUTO"
    return "UNKNOWN"


def control_intent(operating_mode: str, target_final: Optional[float]) -> str:
    if operating_mode == "SAFE_STATE":
        return "SAFE"
    if operating_mode in {"HOLD", "HOLD_DEADBAND", "STOP_HOLD"}:
        return "HOLD"
    if target_final is None:
        return "UNKNOWN"
    if target_final > 0:
        return "CHARGE"
    if target_final < 0:
        return "DISCHARGE"
    return "NEUTRAL"


def derive_control_state(row: Mapping[str, Any]) -> Dict[str, Any]:
    """Project a controller graph row to canonical sparse state fields."""
    mode_raw = str(row.get("mode", "UNKNOWN") or "UNKNOWN")
    target_final = _safe_float(row.get("target_final_w", row.get("zendure_target_power_w")))
    active_limiters = _csv_list(row.get("technical_limiters", row.get("target_limiters_summary")))
    control_reason = str(row.get("control_reason", row.get("target_final_reason", "UNKNOWN")) or "UNKNOWN")
    target_reason = map_target_reason(control_reason, mode_raw, target_final, active_limiters, row)
    operating_mode = map_operating_mode(mode_raw, target_reason=target_reason, row=row)
    intent = control_intent(operating_mode, target_final)
    return {
        "target_final_w": target_final,
        "active_limiters": active_limiters,
        "control_reason": control_reason,
        "target_reason": target_reason,
        "operating_mode": operating_mode,
        "control_intent": intent,
    }


def project_graph_state_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a shallow copy enriched for Graph-Core sparse-state persistence."""
    projected = dict(row)
    derived = derive_control_state(projected)
    projected["operating_mode"] = derived["operating_mode"]
    projected["control_intent"] = derived["control_intent"]
    # Keep the existing human-readable target_final_reason/CONTROL_REASON
    # untouched. Graph Core intentionally stores it as the descriptive reason.
    return projected
