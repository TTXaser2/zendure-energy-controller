# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from settings_codecs import ParseIssue, parse_value
from settings_registry import SETTINGS_BY_KEY, ApplyClass


class ValidationSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    RESTART = "restart"
    CONFIRM = "confirm"
    ACTION = "action"


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    severity: ValidationSeverity
    keys: Tuple[str, ...]
    message_id: str
    params: Mapping[str, Any] = field(default_factory=dict)
    source: str = "validation"
    blocking: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "params", MappingProxyType(dict(self.params)))


@dataclass(frozen=True)
class ParsedCandidate:
    known: Mapping[str, Any]
    unknown: Mapping[str, Any]
    issues: Tuple[ValidationIssue, ...]

    @property
    def valid(self) -> bool:
        return not any(issue.blocking for issue in self.issues)


@dataclass(frozen=True)
class ValidationContext:
    previous: Optional[Mapping[str, Any]] = None
    grid_source_candidate_ready: Optional[bool] = None
    sma_multiple_devices_detected: Optional[bool] = None
    irreversible_v4_gap_confirmed: bool = False
    sqlite_retention_enforce_confirmed: bool = False
    v4_catalog_ready: bool = False
    simulation_coverage_ready: bool = False
    forensic_coverage_ready: bool = False
    restore_verified: bool = False
    protection_period_clear: bool = False
    protected_storage_migration: bool = False
    restart_action_requested: bool = False
    restart_allowlist_helper: bool = False
    restart_single_flight: bool = False
    restart_cooldown_clear: bool = False
    restart_ready_after: bool = False
    secret_contract_ok: bool = True
    unknown_keys_preserved: bool = True


def _issue(code: str, severity: ValidationSeverity, keys: Sequence[str], blocking: bool = True, **params: Any) -> ValidationIssue:
    return ValidationIssue(code=code, severity=severity, keys=tuple(keys), message_id=code, params=params, blocking=blocking)


def parse_candidate(raw: Mapping[str, Any]) -> ParsedCandidate:
    known: Dict[str, Any] = {}
    unknown: Dict[str, Any] = {}
    issues = []
    for key, value in raw.items():
        spec = SETTINGS_BY_KEY.get(key)
        if spec is None:
            unknown[key] = value
            continue
        result = parse_value(spec, value)
        if result.issue is not None:
            issues.append(_issue(result.issue.code, ValidationSeverity.ERROR, (key,)))
        else:
            known[key] = result.value
    return ParsedCandidate(MappingProxyType(known), MappingProxyType(unknown), tuple(issues))


def _changed(key: str, values: Mapping[str, Any], previous: Optional[Mapping[str, Any]]) -> bool:
    return previous is not None and key in values and values.get(key) != previous.get(key)


def _minutes(value: str) -> int:
    hour, minute = value.split(":", 1)
    return int(hour) * 60 + int(minute)


def _mmdd(value: str) -> int:
    month, day = value.split("-", 1)
    return int(month) * 100 + int(day)


def _positive_override(value: Any) -> Optional[int]:
    if value is None or value == "" or value == 0 or value == "0":
        return None
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def validate_candidate(values: Mapping[str, Any], context: Optional[ValidationContext] = None) -> Tuple[ValidationIssue, ...]:
    context = context or ValidationContext()
    issues = []
    get = values.get

    min_soc, max_soc = get("MIN_SOC_PERCENT"), get("MAX_SOC_PERCENT")
    if min_soc is not None and max_soc is not None and not min_soc < max_soc:
        issues.append(_issue("VAL-001", ValidationSeverity.ERROR, ("MIN_SOC_PERCENT", "MAX_SOC_PERCENT")))

    if get("MANUAL_MODE") == "FIXED_DISCHARGE":
        target, power = get("MANUAL_FIXED_DISCHARGE_TARGET_SOC"), get("MANUAL_FIXED_DISCHARGE_POWER_W")
        if None not in (min_soc, target, max_soc, power) and not (min_soc <= target < max_soc and power > 0):
            issues.append(_issue("VAL-002", ValidationSeverity.ERROR, ("MIN_SOC_PERCENT", "MANUAL_FIXED_DISCHARGE_TARGET_SOC", "MAX_SOC_PERCENT", "MANUAL_FIXED_DISCHARGE_POWER_W")))
    if get("MANUAL_MODE") == "FIXED_CHARGE":
        target, power = get("MANUAL_FIXED_CHARGE_TARGET_SOC"), get("MANUAL_FIXED_CHARGE_POWER_W")
        if None not in (min_soc, target, max_soc, power) and not (min_soc < target <= max_soc and power > 0):
            issues.append(_issue("VAL-003", ValidationSeverity.ERROR, ("MIN_SOC_PERCENT", "MANUAL_FIXED_CHARGE_TARGET_SOC", "MAX_SOC_PERCENT", "MANUAL_FIXED_CHARGE_POWER_W")))

    night = (get("NIGHT_START_HOUR"), get("NIGHT_START_MINUTE"), get("NIGHT_END_HOUR"), get("NIGHT_END_MINUTE"))
    if all(value is not None for value in night) and night[:2] == night[2:]:
        issues.append(_issue("VAL-004", ValidationSeverity.ERROR, ("NIGHT_START_HOUR", "NIGHT_START_MINUTE", "NIGHT_END_HOUR", "NIGHT_END_MINUTE")))
    reserve = get("NIGHT_DISCHARGE_STOP_SOC_PERCENT")
    if reserve is not None and None not in (min_soc, max_soc) and not min_soc <= reserve <= max_soc:
        issues.append(_issue("VAL-005", ValidationSeverity.ERROR, ("MIN_SOC_PERCENT", "NIGHT_DISCHARGE_STOP_SOC_PERCENT", "MAX_SOC_PERCENT")))

    integration = get("SECOND_BATTERY_INTEGRATION_ENABLED")
    cross = bool(get("CROSS_CHARGE_ENABLED"))
    harvest = bool(get("REST_SURPLUS_HARVEST_ENABLED"))
    if (cross or harvest) and integration is not True:
        issues.append(_issue("VAL-006", ValidationSeverity.ERROR, ("SECOND_BATTERY_INTEGRATION_ENABLED", "CROSS_CHARGE_ENABLED", "REST_SURPLUS_HARVEST_ENABLED")))
    if harvest and not (integration is True and cross):
        issues.append(_issue("VAL-007", ValidationSeverity.ERROR, ("REST_SURPLUS_HARVEST_ENABLED", "SECOND_BATTERY_INTEGRATION_ENABLED", "CROSS_CHARGE_ENABLED")))

    if get("SECOND_BATTERY_SOURCE_PROFILE") == "custom" and not get("SECOND_BATTERY_POWER_TOPIC"):
        issues.append(_issue("VAL-008", ValidationSeverity.ERROR, ("SECOND_BATTERY_SOURCE_PROFILE", "SECOND_BATTERY_POWER_TOPIC")))
    if bool(get("HARVEST_HIGH_SMA_SOC_ENABLED")) and not get("SECOND_BATTERY_SOC_TOPIC"):
        issues.append(_issue("VAL-008", ValidationSeverity.ERROR, ("HARVEST_HIGH_SMA_SOC_ENABLED", "SECOND_BATTERY_SOC_TOPIC")))

    maximum = get("SECOND_BATTERY_MAX_CHARGE_POWER_W")
    if harvest and not (isinstance(maximum, int) and not isinstance(maximum, bool) and 300 <= maximum <= 10000):
        issues.append(_issue("VAL-009", ValidationSeverity.ERROR, ("REST_SURPLUS_HARVEST_ENABLED", "SECOND_BATTERY_MAX_CHARGE_POWER_W")))

    exit_soc, enter_soc, full_soc = get("HARVEST_HIGH_SMA_SOC_EXIT_PERCENT"), get("HARVEST_HIGH_SMA_SOC_ENTER_PERCENT"), get("HARVEST_SMA_FULL_SOC_PERCENT")
    if None not in (exit_soc, enter_soc, full_soc) and not (0 <= exit_soc < enter_soc <= full_soc <= 100):
        issues.append(_issue("VAL-010", ValidationSeverity.ERROR, ("HARVEST_HIGH_SMA_SOC_EXIT_PERCENT", "HARVEST_HIGH_SMA_SOC_ENTER_PERCENT", "HARVEST_SMA_FULL_SOC_PERCENT")))

    if isinstance(maximum, int) and maximum > 0:
        floor = _positive_override(get("HARVEST_PRIMARY_CHARGE_FLOOR_W"))
        restart = _positive_override(get("HARVEST_PRIMARY_CHARGE_RESTART_W"))
        near = _positive_override(get("HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_W"))
        floor = floor if floor is not None else float(get("HARVEST_PRIMARY_CHARGE_FLOOR_RATIO", 0)) * maximum
        restart = restart if restart is not None else float(get("HARVEST_PRIMARY_CHARGE_RESTART_RATIO", 0)) * maximum
        near = near if near is not None else float(get("HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_RATIO", 0)) * maximum
        if not (0 <= floor <= restart <= near <= maximum):
            issues.append(_issue("VAL-011", ValidationSeverity.ERROR, ("SECOND_BATTERY_MAX_CHARGE_POWER_W", "HARVEST_PRIMARY_CHARGE_FLOOR_W", "HARVEST_PRIMARY_CHARGE_RESTART_W", "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_W")))
        for key in ("HARVEST_PRIMARY_CHARGE_FLOOR_W", "HARVEST_PRIMARY_CHARGE_RESTART_W", "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_W"):
            if _positive_override(get(key)) is not None:
                issues.append(_issue("VAL-012", ValidationSeverity.INFO, (key,), blocking=False, effective_source="absolute_w"))

    time_keys = ("HARVEST_HIGH_SMA_SOC_PROFILE_START_TIME", "HARVEST_HIGH_SMA_SOC_PROFILE_MIDDAY_START_TIME", "HARVEST_HIGH_SMA_SOC_PROFILE_AFTERNOON_START_TIME", "HARVEST_HIGH_SMA_SOC_PROFILE_END_TIME")
    times = tuple(get(key) for key in time_keys)
    if all(isinstance(value, str) for value in times) and not (_minutes(times[0]) < _minutes(times[1]) < _minutes(times[2]) < _minutes(times[3])):
        issues.append(_issue("VAL-013", ValidationSeverity.ERROR, time_keys))

    if get("HARVEST_SEASON_MODE") == "calendar":
        start, end = get("HARVEST_SEASON_PARALLEL_START_MM_DD"), get("HARVEST_SEASON_PARALLEL_END_MM_DD")
        if not (isinstance(start, str) and isinstance(end, str) and _mmdd(start) <= _mmdd(end)):
            issues.append(_issue("VAL-014", ValidationSeverity.ERROR, ("HARVEST_SEASON_MODE", "HARVEST_SEASON_PARALLEL_START_MM_DD", "HARVEST_SEASON_PARALLEL_END_MM_DD")))

    if _changed("GRID_METER_SOURCE", values, context.previous) and context.grid_source_candidate_ready is not True:
        issues.append(_issue("VAL-015", ValidationSeverity.ERROR, ("GRID_METER_SOURCE",)))
    if context.sma_multiple_devices_detected is True and get("GRID_METER_SOURCE") == "sma_energy_meter_udp" and not get("SMA_ENERGY_METER_SERIAL"):
        issues.append(_issue("VAL-016", ValidationSeverity.ERROR, ("GRID_METER_SOURCE", "SMA_ENERGY_METER_SERIAL")))

    restart_keys = tuple(key for key, spec in SETTINGS_BY_KEY.items() if spec.apply_class is ApplyClass.RESTART_REQUIRED)
    changed_restart = tuple(key for key in restart_keys if _changed(key, values, context.previous))
    if changed_restart:
        issues.append(_issue("VAL-017", ValidationSeverity.RESTART, changed_restart, blocking=False))

    if context.previous is not None and context.previous.get("MEASUREMENT_LOG_MODE") in ("standard", "extended") and get("MEASUREMENT_LOG_MODE") == "off" and not context.irreversible_v4_gap_confirmed:
        issues.append(_issue("VAL-018", ValidationSeverity.CONFIRM, ("MEASUREMENT_LOG_MODE",)))

    if get("MEASUREMENT_DB_MAINTENANCE_MODE") == "enforce" and not context.sqlite_retention_enforce_confirmed:
        issues.append(_issue("VAL-019", ValidationSeverity.CONFIRM, ("MEASUREMENT_DB_MAINTENANCE_MODE",)))

    if get("MEASUREMENT_LOG_MAINTENANCE_MODE") == "enforce" and get("MEASUREMENT_LOG_RETENTION_MODE") == "bounded":
        technical_gates = (context.v4_catalog_ready, context.simulation_coverage_ready, context.forensic_coverage_ready, context.restore_verified, context.protection_period_clear)
        if not all(technical_gates):
            issues.append(_issue("VAL-020", ValidationSeverity.ERROR, ("MEASUREMENT_LOG_MAINTENANCE_MODE", "MEASUREMENT_LOG_RETENTION_MODE")))

    if _changed("MEASUREMENT_DB_PATH", values, context.previous) and not context.protected_storage_migration:
        issues.append(_issue("VAL-021", ValidationSeverity.ACTION, ("MEASUREMENT_DB_PATH",)))

    if context.restart_action_requested and not all((context.restart_allowlist_helper, context.restart_single_flight, context.restart_cooldown_clear, context.restart_ready_after)):
        issues.append(_issue("VAL-022", ValidationSeverity.ACTION, tuple()))
    if not context.secret_contract_ok:
        issues.append(_issue("VAL-023", ValidationSeverity.ERROR, ("MQTT_PASSWORD",)))
    if not context.unknown_keys_preserved:
        issues.append(_issue("VAL-024", ValidationSeverity.ERROR, tuple()))

    if get("MQTT_BROKER") == "":
        issues.append(_issue("MQTT_BROKER_MISSING", ValidationSeverity.ERROR, ("MQTT_BROKER",)))
    device_id = get("DEVICE_ID")
    if device_id is not None and (device_id == "" or any(char in device_id for char in "/+#")):
        issues.append(_issue("DEVICE_ID_INVALID", ValidationSeverity.ERROR, ("DEVICE_ID",)))
    return tuple(issues)
