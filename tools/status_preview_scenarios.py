#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Synthetic, read-only payloads for the RC10 status UI preview.

This module has deliberately no imports from controller, MQTT, state, logging or
measurement code.  It only produces dictionaries consumed by the common status
page renderer and its JSON endpoints.
"""

from __future__ import annotations

import math
import time
from datetime import date as date_cls, datetime, timedelta
from typing import Any, Dict, List

SCENARIOS = (
    {
        "key": "zendure_only",
        "label": "1× Zendure · ohne Primärspeicher",
        "primary_storage_present": False,
        "zendure_unit_count": 1,
    },
    {
        "key": "dual_zendure_primary",
        "label": "2× Zendure · mit Primärspeicher",
        "primary_storage_present": True,
        "zendure_unit_count": 2,
    },
)
DEFAULT_SCENARIO = SCENARIOS[0]["key"]


def normalize_scenario(value: Any) -> str:
    key = str(value or "").strip().lower()
    return key if any(item["key"] == key for item in SCENARIOS) else DEFAULT_SCENARIO


def scenario_definition(value: Any) -> Dict[str, Any]:
    key = normalize_scenario(value)
    return next(dict(item) for item in SCENARIOS if item["key"] == key)


def _de_number(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


def _power_phrase(value: float) -> str:
    if abs(value) < 0.5:
        return "0 W neutral"
    action = "Laden" if value > 0 else "Entladen"
    amount = abs(value)
    if amount >= 1000:
        shown = f"{_de_number(amount / 1000.0, 2)} kW"
    else:
        shown = f"{round(amount)} W"
    return f"{shown} {action}"


def _grid_value(value: float) -> str:
    sign = "+" if value > 0 else ("−" if value < 0 else "")
    amount = abs(value)
    if amount >= 1000:
        return f"{sign}{_de_number(amount / 1000.0, 2)} kW"
    return f"{sign}{round(amount)} W"


def _unit(name: str, unit_id: str, soc: float, actual_w: float, target_w: float, capacity_kwh: float) -> Dict[str, Any]:
    energy = capacity_kwh * soc / 100.0
    state = "lädt" if actual_w > 50 else ("entlädt" if actual_w < -50 else "neutral")
    detail = f"{round(soc)} % · {_de_number(energy, 2)} kWh von {_de_number(capacity_kwh, 2)} kWh · {_power_phrase(actual_w)}"
    return {
        "id": unit_id,
        "name": name,
        "soc": soc,
        "actual_w": actual_w,
        "target_w": target_w,
        "state_text": state,
        "detail": detail,
        "tone": "ok",
        "capacity_kwh": capacity_kwh,
        "energy_kwh": energy,
    }


def build_preview_status_payload(scenario: Any, *, now_epoch: float | None = None) -> Dict[str, Any]:
    definition = scenario_definition(scenario)
    now_epoch = float(now_epoch if now_epoch is not None else time.time())
    now = datetime.fromtimestamp(now_epoch)
    wave = math.sin(now_epoch / 18.0)
    grid_w = -850.0 - 520.0 * wave
    target_w = max(0.0, min(1800.0, -grid_w * 0.92))
    actual_w = target_w * (0.92 + 0.03 * math.sin(now_epoch / 7.0))
    mode = "AUTO_CHARGE" if grid_w < -50 else "AUTO_HOLD"

    if definition["zendure_unit_count"] == 1:
        soc_1 = 63.0 + 0.8 * math.sin(now_epoch / 150.0)
        units = [_unit("Zendure", "unit-1", soc_1, actual_w, target_w, 5.28)]
        system_soc = soc_1
        remaining = 5.28 * max(0.0, 99.0 - system_soc) / 100.0
        primary: Dict[str, Any] = {
            "present": False,
            "soc": None,
            "actual": "nicht konfiguriert",
            "actual_raw": None,
            "status": "nicht konfiguriert",
            "line": "",
            "source": "",
            "freshness_text": "",
            "tone": "unknown",
        }
    else:
        soc_1 = 74.0 + 0.9 * math.sin(now_epoch / 170.0)
        soc_2 = 58.0 + 1.1 * math.sin(now_epoch / 190.0 + 0.8)
        p1 = actual_w * 0.64
        p2 = actual_w - p1
        units = [
            _unit("Zendure 1 · SolarFlow 2400 AC+", "unit-1", soc_1, p1, target_w * 0.64, 5.28),
            _unit("Zendure 2 · SolarFlow 2400 AC+", "unit-2", soc_2, p2, target_w * 0.36, 2.88),
        ]
        total_capacity = sum(float(unit["capacity_kwh"]) for unit in units)
        system_soc = sum(float(unit["capacity_kwh"]) * float(unit["soc"]) for unit in units) / total_capacity
        remaining = total_capacity * max(0.0, 99.0 - system_soc) / 100.0
        primary_power = 1120.0 + 120.0 * math.sin(now_epoch / 22.0)
        primary_soc = 82.0 + 0.5 * math.sin(now_epoch / 240.0)
        primary = {
            "present": True,
            "soc": primary_soc,
            "actual": _power_phrase(primary_power),
            "actual_raw": primary_power,
            "status": "lädt",
            "line": "Harvest: Parallel-Ernte aktiv · Primärspeicher bleibt priorisiert",
            "source": "SMA Sunny Island",
            "freshness_text": "aktuell",
            "tone": "ok",
        }

    grid_status = "Einspeisung / Export" if grid_w < -50 else ("Bezug aus Netz" if grid_w > 50 else "ausgeglichen")
    grid_tone = "ok" if grid_w <= 50 else "warn"
    timing = [
        ("config", "Konfigurationsprüfung", 1.5),
        ("local_api", "Zendure Local API", None),
        ("energy_data", "SMA- und Netzdaten", 0.7),
        ("diagnostics", "Status- und Diagnoseaufbereitung", 2.8),
        ("control", "Regelentscheidung", 0.3),
        ("mqtt", "MQTT-Kommandopfad", 5.5),
        ("effect", "Kommandowirkungsprüfung", 0.2),
        ("logging", "Logging im Hauptthread", 8.4),
        ("other", "Sonstige, nicht einzeln erfasste Verarbeitung", 1.9),
    ]
    loop_ms = sum(v for _, _, v in timing if v is not None)
    phases: List[Dict[str, Any]] = []
    for key, label, value in timing:
        phases.append({
            "key": key,
            "label": label,
            "ms": value,
            "percent": (100.0 * value / loop_ms) if value is not None else None,
            "executed": value is not None,
        })

    return {
        "version": "V12.11.2-RC11",
        "snapshot_epoch_ms": int(now_epoch * 1000),
        "server_time": now.strftime("%H:%M:%S"),
        "snapshot_time": now.isoformat(timespec="seconds"),
        "preview": {
            "active": True,
            "scenario": definition["key"],
            "scenarios": [{"key": item["key"], "label": item["label"]} for item in SCENARIOS],
        },
        "topology": {
            "primary_storage_present": bool(definition["primary_storage_present"]),
            "zendure_unit_count": int(definition["zendure_unit_count"]),
        },
        "system": {
            "kind": "ok",
            "label": "Vorschau aktiv",
            "warnings": ["Simulierte Daten · keine Steuerwirkung"],
            "critical_text": "",
        },
        "grid": {
            "value": _grid_value(grid_w),
            "value_raw": grid_w,
            "status": grid_status,
            "valid": True,
            "tone": grid_tone,
            "source": "Synthetischer Vorschauzähler",
            "freshness_text": "live simuliert",
            "age": 0,
        },
        "mode": {
            "mode": mode,
            "text": "Restüberschuss wird gespeichert",
            "target": _power_phrase(target_w),
            "target_raw": target_w,
            "reason": "Vorschau-Szenario · AUTO_GRID_EXPORT",
            "last_change": now.strftime("%H:%M:%S"),
            "projection": "Gemeinsamer Operating Mode · ausschließlich visualisiert",
            "tone": "ok",
            "status_text": "UI-Vorschau · keine Regelung aktiv",
        },
        "zendure": {
            "soc": system_soc,
            "system_soc_text": f"{_de_number(system_soc, 1)} % gewichtet" if len(units) > 1 else f"{round(system_soc)} %",
            "actual": _power_phrase(actual_w),
            "actual_raw": actual_w,
            "remaining": remaining,
            "remaining_text": f"{_de_number(remaining, 2)} kWh",
            "max_soc_text": "99 %",
            "source": "synthetische Unit-Telemetrie",
            "unit_count": len(units),
            "units": units,
            "command_warning": "",
            "tone": "ok",
        },
        "primary": primary,
        "source": {
            "name": "Synthetische Netzleistungsquelle",
            "device_line": "Vorschau-Datenstrom · keine reale Hardware",
            "age": 0,
            "age_text": "gerade eben",
            "packets_min": 20,
            "packets_text": "20/min",
            "auto_text": "Simulierter Messwert für UI-Validierung",
            "rejected_text": "",
            "rejected_count_text": "",
            "tone": "ok",
        },
        "logging": {
            "status": "Vorschau · kein Schreiben",
            "db": "Vorschau · deaktiviert",
            "target": "Kein Speicherziel",
            "db_name": "—",
            "db_size_bytes": 0,
            "queue_depth": 0,
            "last_write": "kein Schreibzugriff",
            "last_write_epoch_s": None,
            "fallback_active": False,
            "fallback_count": 0,
            "fallback_reason": "",
            "free_bytes": 201 * 1024**3,
            "used_bytes": 18 * 1024**3,
            "total_bytes": 219 * 1024**3,
            "disk_used_percent": 18 / 219 * 100,
            "tone": "ok",
        },
        "resources": {
            "cpu_percent": 4.8,
            "ram_used_percent": 61.0,
            "ram_available_bytes": 355 * 1024**2,
            "ram_total_bytes": 909 * 1024**2,
            "swap_used_bytes": 74 * 1024**2,
            "swap_total_bytes": 256 * 1024**2,
            "swap_in_bytes_per_s": 0,
            "swap_out_bytes_per_s": 0,
            "temperature_c": 45.2,
            "load": [0.15, 0.12, 0.10],
            "system_uptime_s": 8 * 86400 + 4 * 3600,
            "throttling": {"available": True, "current": [], "historic": []},
            "tone": "ok",
            "status": "Vorschauwerte · Raspberry Pi unauffällig",
        },
        "diag": {
            "rule": "Simuliert",
            "rule_tone": "ok",
            "broker": "Nicht verbunden (Vorschau)",
            "broker_tone": "unknown",
            "mqtt": "Synthetische Telemetrie",
            "mqtt_tone": "ok",
            "api": "Nicht verwendet",
            "api_tone": "unknown",
            "effect": "Nur Darstellung",
            "effect_tone": "ok",
            "loop_ms": loop_ms,
            "loop_text": f"{_de_number(loop_ms, 1)} ms",
            "cycle_meta_text": "Zyklusabstand ca. 3,02 s · aktive Arbeit 0,7 %",
            "cycle_slow_warning": False,
            "slow_cycle_warn_ms": 5000,
            "timing_phases": phases,
            "timing_stats": {},
            "sqlite_ms": None,
            "slowest_step": "Logging im Hauptthread",
            "slowest_ms": 8.4,
            "controller_uptime_s": 3600,
            "resync_text": "Keiner seit Vorschau-Start",
            "resync_suppressed_text": "Keiner seit Vorschau-Start",
            "analysis": "Nicht verwendet",
        },
        "events": {
            "items": [],
            "open_count": 0,
            "open_severity": "info",
            "technical_restrictions": [],
        },
    }


def build_preview_grid_payload(scenario: Any, *, now_epoch: float | None = None) -> Dict[str, Any]:
    normalize_scenario(scenario)
    now_epoch = float(now_epoch if now_epoch is not None else time.time())
    points = []
    for index in range(48):
        epoch = now_epoch - (47 - index) * 3.0
        value = -850.0 - 520.0 * math.sin(epoch / 18.0)
        dt = datetime.fromtimestamp(epoch)
        points.append({
            "time": dt.strftime("%H:%M:%S"),
            "epoch": epoch,
            "value": value,
            "status": "Einspeisung / Export" if value < -50 else ("Bezug aus Netz" if value > 50 else "ausgeglichen"),
        })
    return {"points": points, "source": "synthetische Vorschau", "snapshot_epoch_ms": int(now_epoch * 1000)}


def _parse_date(value: Any) -> date_cls:
    try:
        return datetime.strptime(str(value or "")[:10], "%Y-%m-%d").date()
    except Exception:
        return datetime.now().date()


def build_preview_soc_payload(scenario: Any, *, date: Any = None, now_epoch: float | None = None) -> Dict[str, Any]:
    definition = scenario_definition(scenario)
    now_epoch = float(now_epoch if now_epoch is not None else time.time())
    selected = min(_parse_date(date), datetime.now().date())
    today = datetime.now().date()
    is_today = selected == today
    max_minute = datetime.now().hour * 60 + datetime.now().minute if is_today else 1440
    points: List[Dict[str, Any]] = []
    for minute in range(0, max_minute + 1, 5):
        day_fraction = minute / 1440.0
        solar_shape = max(0.0, math.sin((day_fraction - 0.25) * math.pi))
        zendure_1 = 42.0 + 46.0 * solar_shape + 1.2 * math.sin(minute / 80.0)
        unit_2 = 34.0 + 40.0 * solar_shape + 1.0 * math.sin(minute / 95.0 + 0.5)
        primary = 55.0 + 42.0 * solar_shape + 0.8 * math.sin(minute / 110.0)
        power = 1700.0 * solar_shape - 420.0 * (1.0 - solar_shape)
        hour, minute_part = divmod(minute, 60)
        points.append({
            "minute": minute,
            "time": f"{hour:02d}:{minute_part:02d}",
            "zendure_soc": max(0.0, min(100.0, zendure_1)),
            "zendure_unit_1_soc": max(0.0, min(100.0, zendure_1)),
            "zendure_unit_2_soc": max(0.0, min(100.0, unit_2)) if definition["zendure_unit_count"] > 1 else None,
            "primary_soc": max(0.0, min(100.0, primary)) if definition["primary_storage_present"] else None,
            "zendure_power_w": power,
            "primary_power_w": (1150.0 * solar_shape - 250.0 * (1.0 - solar_shape)) if definition["primary_storage_present"] else None,
            "mode": "AUTO_CHARGE" if power > 50 else "NIGHT_DISCHARGE",
            "reason": "AUTO_GRID_EXPORT" if power > 50 else "NIGHT_DISCHARGE",
        })
    return {
        "date": selected.isoformat(),
        "is_today": is_today,
        "complete": not is_today,
        "zendure_unit_count": int(definition["zendure_unit_count"]),
        "primary_storage_present": bool(definition["primary_storage_present"]),
        "unit_labels": ["Zendure 1", "Zendure 2"][: int(definition["zendure_unit_count"])],
        "axis_minute_start": 0,
        "axis_minute_end": 1440,
        "points": points,
        "source": "synthetische UI-Vorschau",
        "cache_status": "live",
        "cache_age_s": 0,
        "error": "",
        "last_point_at": points[-1]["time"] if points else "",
        "available_from": (today - timedelta(days=30)).isoformat(),
        "available_to": today.isoformat(),
        "thresholds": {"min_soc": 10, "max_soc": 99, "reserve_soc": 35},
        "night_window": {"start": "21:30", "end": "05:30"},
    }
