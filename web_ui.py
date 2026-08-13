# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

import csv
import hashlib
from contextlib import asynccontextmanager
import html
import io
import json
import os
import secrets
import shlex
import subprocess
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlsplit

import requests
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse, JSONResponse, Response

from config_manager import CONFIG_SCHEMA, ConfigManager, validate_config
from settings_model import build_settings_model
from settings_service import SettingsService
from config_bundle import BUNDLE_MAX_BYTES, BundleError, build_bundle
from config_states import ConfigStateError, ConfigStateStore
from config_artifacts import ConfigArtifactCoordinator
from config_validator import ValidationIssue, restart_relevant_changes, split_issues, validate_config_semantics
from cross_charge import cross_charge_enabled
from csv_logger import rows_to_csv, estimate_retention_hours, measurement_log_mode, detected_log_mounts, resolve_log_path
from measurement_db import query_graph_points, query_measurement_date_range, resolve_measurement_db_path, db_status_for_config
from version import APP_BUILD_ID, APP_VERSION, APP_VERSION_LABEL
from status_page_v2 import render_global_topbar, render_status_page_v2
from system_metrics import get_system_metrics
from operational_events import OperationalEventJournal, read_recent_events
from storage_inventory import StorageInventory
from state import ControllerState
from translations import (
    limiter_label,
    limiter_text,
    mode_label,
    path_label,
    technical_limiter_text,
)


GROUP_ORDER = [
    "Netzwerk",
    "Weboberfläche",
    "Regelung",
    "Manueller Modus",
    "Zweitbatterie",
    "Nachtmodus",
    "Sicherheit / Fallback",
    "Messdaten / Historie",
    "Analyse / Replay",
    "Logging",
]

MANUAL_DISCHARGE_KEYS = {
    "MANUAL_FIXED_DISCHARGE_POWER_W",
    "MANUAL_FIXED_DISCHARGE_TARGET_SOC",
    "MANUAL_DISCHARGE_AFTER_TARGET",
}
MANUAL_CHARGE_KEYS = {
    "MANUAL_FIXED_CHARGE_POWER_W",
    "MANUAL_FIXED_CHARGE_TARGET_SOC",
    "MANUAL_CHARGE_AFTER_TARGET",
}

MANUAL_PDF_CANDIDATES = [
    os.path.join("docs", "Zendure_Energy_Controller_Handbuch.pdf"),
    os.path.join("docs", "Zendure_Energy_Controller_V12_7_Benutzerhandbuch.pdf"),
    os.path.join("docs", "Zendure_Energy_Controller_V12_6_Benutzerhandbuch.pdf"),
    os.path.join("docs", "Zendure_Energy_Controller_V12_5_Benutzerhandbuch.pdf"),
    os.path.join("docs", "Zendure_Energy_Controller_V12_3_Benutzerhandbuch.pdf"),
    os.path.join("docs", "Zendure_Energy_Controller_V12_Benutzerhandbuch.pdf"),
    os.path.join("docs", "Zendure_Energy_Controller_V11_4_Benutzerhandbuch.pdf"),
    os.path.join("docs", "Zendure_Energy_Controller_V11_2_Benutzerhandbuch.pdf"),
    os.path.join("docs", "Zendure_Energy_Controller_V11_Benutzerhandbuch.pdf"),
    "Zendure_Energy_Controller_Handbuch.pdf",
]



def validate_settings_before_save(cfg: Dict[str, Any], current_cfg: Optional[Dict[str, Any]] = None) -> List[ValidationIssue]:
    """Run central semantic settings validation.

    ERROR blocks saving, WARNING requires explicit acknowledgement, INFO is
    displayed as contextual information. The underlying validation rules live in
    config_validator.py so web UI, documentation and future CLI tooling can share
    one model.
    """
    return validate_config_semantics(
        cfg,
        current=current_cfg,
        perform_live_checks=True,
        base_dir=os.getcwd(),
    )



def format_hhmm(hour: Any, minute: Any) -> str:
    try:
        h = int(float(hour))
        m = int(float(minute))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
        return f"{h:02d}:{m:02d}"
    except Exception:
        return "00:00"


def parse_hhmm(value: Any) -> Optional[tuple]:
    text = "" if value is None else str(value).strip()
    if not text or ":" not in text:
        return None
    parts = text.split(":")
    if len(parts) != 2:
        return None
    try:
        h = int(parts[0])
        m = int(parts[1])
    except Exception:
        return None
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return None
    return h, m


def apply_night_time_form_fields(raw_cfg: Dict[str, Any], form: Any) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    mapping = [
        ("NIGHT_START_TIME", "NIGHT_START_HOUR", "NIGHT_START_MINUTE", "Startzeit"),
        ("NIGHT_END_TIME", "NIGHT_END_HOUR", "NIGHT_END_MINUTE", "Endzeit"),
    ]
    for form_key, hour_key, minute_key, label in mapping:
        if form_key not in form:
            continue
        parsed = parse_hhmm(form.get(form_key))
        if parsed is None:
            issues.append(ValidationIssue(
                "ERROR",
                f"Die Nachtmodus-{label} muss eine gültige Uhrzeit im 24h-Format hh:mm sein.",
                {hour_key, minute_key},
                "Nachtmodus",
                f"{form_key}_INVALID",
            ))
            continue
        raw_cfg[hour_key], raw_cfg[minute_key] = parsed
    return issues

def find_manual_pdf() -> Optional[str]:
    for candidate in MANUAL_PDF_CANDIDATES:
        path = os.path.abspath(candidate)
        if os.path.exists(path):
            return path
    return None


def restart_labels(keys: Iterable[str]) -> str:
    labels = []
    for key in keys:
        meta = CONFIG_SCHEMA.get(key, {})
        label = str(meta.get("label", key))
        if label not in labels:
            labels.append(label)
    return ", ".join(labels) if labels else "-"


RESTART_HELPER_PATH = "/usr/local/sbin/zendure-controller-restart"


def service_restart_enabled(cfg: Dict[str, Any]) -> bool:
    # The helper path is fixed and never comes from config.  The existence and
    # sudo allowlist are verified by the installer/preflight; the boolean is the
    # user's explicit UI enable switch.
    return bool(cfg.get("WEB_SERVICE_RESTART_ENABLED", False))


def trigger_service_restart(_cfg: Dict[str, Any]) -> None:
    # Installer self-tests must be side-effect free even when executed on a
    # productive host where the fixed helper is already installed.
    if os.environ.get("ZEC_INSTALLER_PREFLIGHT") == "1":
        return
    if not os.path.isfile(RESTART_HELPER_PATH) or not os.access(RESTART_HELPER_PATH, os.X_OK):
        raise RuntimeError(f"Fester Restart-Helper fehlt oder ist nicht ausführbar: {RESTART_HELPER_PATH}")
    subprocess.Popen(["sudo", RESTART_HELPER_PATH], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def delayed_service_restart(cfg: Dict[str, Any], delay_seconds: float = 1.0) -> None:
    timer = threading.Timer(delay_seconds, trigger_service_restart, args=[dict(cfg)])
    timer.daemon = True
    timer.start()


def second_battery_name(cfg: Dict[str, Any]) -> str:
    name = str(cfg.get("SECOND_BATTERY_DISPLAY_NAME", "") or "").strip()
    return name or "Zusatzbatterie"


def status_url_after_restart(request: Request, cfg: Dict[str, Any]) -> str:
    """Build an absolute root URL using the new configured WEB_PORT.

    This is important after changing WEB_PORT: the response is still served by
    the old process/port, but the browser must poll the restarted service on the
    new port. The main page is used intentionally instead of /status, because
    the controller UI lives at /.
    """
    scheme = request.url.scheme or "http"
    host = request.url.hostname or "127.0.0.1"
    if host in {"0.0.0.0", "::"}:
        host = "127.0.0.1"
    try:
        port = int(cfg.get("WEB_PORT", 8080))
    except Exception:
        port = 8080
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        return f"{scheme}://{host}/"
    return f"{scheme}://{host}:{port}/"


FAVICON_SVG = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>
  <rect x='10' y='18' width='42' height='30' rx='6' fill='#1565c0'/>
  <rect x='53' y='27' width='5' height='12' rx='2' fill='#1565c0'/>
  <rect x='15' y='23' width='32' height='20' rx='3' fill='#e8f5e9'/>
  <path d='M35 9 21 34h10l-4 21 16-28H32z' fill='#4CAF50' stroke='#0b5' stroke-width='1'/>
</svg>"""



def build_ready_payload(cfg: Dict[str, Any], snap: Dict[str, Any]) -> Dict[str, Any]:
    """Return the complete bounded readiness proof used by HTTP and recovery.

    This gate deliberately includes the independent command/read-back path. A
    live process with fresh grid/SOC data is not operationally ready while a
    command mismatch, resync/late-effect episode or incomplete Zendure command
    state is open.
    """
    checks: Dict[str, Any] = {}

    mqtt_ok = bool(snap.get("mqtt_connected"))
    checks["mqtt"] = {"ok": mqtt_ok, "connected": mqtt_ok}

    grid_age = snap.get("last_shelly_update_age_seconds")
    grid_timeout = int(cfg.get("SHELLY_STALE_TIMEOUT_SECONDS", 15))
    grid_ok = bool(snap.get("grid_power_valid", True)) and grid_age is not None and int(grid_age) <= grid_timeout
    checks["grid_measurement"] = {
        "ok": grid_ok, "age_seconds": grid_age, "timeout_seconds": grid_timeout,
        "reason": snap.get("grid_power_validity_reason"),
    }

    soc_age = snap.get("last_soc_update_age_seconds")
    soc_timeout = int(cfg.get("SOC_STALE_TIMEOUT_SECONDS", 90))
    soc_ok = bool(snap.get("soc_valid", True)) and snap.get("battery_soc") is not None and soc_age is not None and int(soc_age) <= soc_timeout
    checks["zendure_soc"] = {
        "ok": soc_ok, "soc_percent": snap.get("battery_soc"),
        "source": snap.get("zendure_telemetry_source"),
        "fallback_active": snap.get("zendure_local_api_fallback_active"),
        "age_seconds": soc_age, "timeout_seconds": soc_timeout,
        "reason": snap.get("soc_validity_reason"),
    }

    if cross_charge_enabled(cfg):
        second_age = snap.get("last_sma_battery_update_age_seconds")
        second_timeout = int(cfg.get("SECOND_BATTERY_STALE_TIMEOUT_SECONDS", cfg.get("EVCC_STALE_TIMEOUT_SECONDS", 30)))
        second_ok = bool(snap.get("second_battery_valid", True)) and second_age is not None and int(second_age) <= second_timeout
        checks["cross_charge_second_battery"] = {
            "ok": second_ok, "age_seconds": second_age, "timeout_seconds": second_timeout,
            "reason": snap.get("second_battery_validity_reason"),
        }

    command_path_ok = bool(
        snap.get("mqtt_command_path_available")
        and snap.get("mqtt_command_path_fresh")
        and snap.get("mqtt_command_path_valid")
    )
    checks["command_path"] = {
        "ok": command_path_ok,
        "available": bool(snap.get("mqtt_command_path_available")),
        "fresh": bool(snap.get("mqtt_command_path_fresh")),
        "valid": bool(snap.get("mqtt_command_path_valid")),
        "age_seconds": snap.get("mqtt_command_path_age_seconds"),
        "reason": snap.get("mqtt_command_path_validity_reason"),
    }

    command_complete = bool(snap.get("zendure_command_state_complete"))
    smart_mode_ok = snap.get("zendure_command_smart_mode") == 1
    ac_mode = str(snap.get("zendure_command_ac_mode") or "")
    input_limit = snap.get("zendure_command_input_limit_w")
    output_limit = snap.get("zendure_command_output_limit_w")
    static_invariant_ok = bool(
        ac_mode in {"Input mode", "Output mode"}
        and input_limit is not None and output_limit is not None
        and ((ac_mode == "Input mode" and int(output_limit) == 0)
             or (ac_mode == "Output mode" and int(input_limit) == 0))
    )
    checks["command_state"] = {
        "ok": command_complete and smart_mode_ok and static_invariant_ok,
        "complete": command_complete,
        "smart_mode": snap.get("zendure_command_smart_mode"),
        "ac_mode": ac_mode,
        "input_limit_w": input_limit,
        "output_limit_w": output_limit,
        "static_invariant_ok": static_invariant_ok,
        "source": snap.get("zendure_command_state_source"),
        "reason": snap.get("zendure_command_state_reason"),
    }

    desired_exists = int(snap.get("command_desired_sequence_id") or 0) > 0
    desired_match = (not desired_exists) or bool(snap.get("command_readback_matches_desired"))
    checks["command_readback"] = {
        "ok": desired_match,
        "desired_sequence_id": int(snap.get("command_desired_sequence_id") or 0),
        "matches_desired": bool(snap.get("command_readback_matches_desired")),
        "mismatch_fields": snap.get("command_readback_mismatch_fields"),
    }

    lifecycle = str(snap.get("command_lifecycle_state") or "")
    unhealthy_lifecycle = lifecycle in {
        "MISMATCH_CONFIRMED", "RECOVERY_VERIFYING", "TELEMETRY_UNCERTAIN",
        "LATE_EFFECT_NEUTRALIZING", "LATE_EFFECT_NEUTRAL_STABILIZING",
        "COMMAND_STATE_VERIFYING",
    }
    no_open_episode = not any((
        bool(snap.get("command_uncertain_mqtt_active")),
        bool(snap.get("command_not_effective_active")),
        bool(snap.get("command_late_effect_guard_active")),
        unhealthy_lifecycle,
    ))
    checks["command_guards"] = {
        "ok": no_open_episode,
        "uncertain_mqtt_active": bool(snap.get("command_uncertain_mqtt_active")),
        "not_effective_active": bool(snap.get("command_not_effective_active")),
        "late_effect_guard_active": bool(snap.get("command_late_effect_guard_active")),
        "lifecycle_state": lifecycle,
        "effect_category": snap.get("command_effect_category"),
    }

    actual_power_ok = bool(snap.get("actual_zendure_power_valid"))
    checks["zendure_power_telemetry"] = {
        "ok": actual_power_ok,
        "age_seconds": snap.get("actual_zendure_power_age_s"),
        "reason": snap.get("actual_zendure_power_validity_reason"),
    }

    safe_state = snap.get("current_mode") == "SAFE_STATE"
    checks["controller"] = {
        "ok": not safe_state and int(snap.get("consecutive_errors") or 0) == 0,
        "mode": snap.get("current_mode"),
        "consecutive_errors": snap.get("consecutive_errors"),
        "last_error": snap.get("last_error"),
        "last_error_time": snap.get("last_error_time"),
    }

    failed = [name for name, item in checks.items() if isinstance(item, dict) and not item.get("ok", False)]
    proof_source = {
        "safe_state_counter": int(snap.get("safe_state_counter") or 0),
        "command_resync_count": int(snap.get("command_resync_count") or 0),
        "late_guard_activation_count": int(snap.get("command_late_effect_guard_activation_count") or 0),
    }
    proof_revision = hashlib.sha256(json.dumps(proof_source, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    status = "safe_state" if safe_state else ("degraded" if failed else "ok")
    return {
        "status": status,
        "ready": not failed and not safe_state,
        "version": APP_VERSION,
        "build_id": APP_BUILD_ID,
        "uptime_seconds": snap.get("uptime_seconds"),
        "instance_owner": {
            "active": bool(snap.get("instance_owner_active")),
            "pid": snap.get("instance_owner_pid"),
            "build_id": snap.get("instance_owner_build_id") or "",
            "since_utc": snap.get("instance_owner_since_utc") or "",
            "lock_path": snap.get("instance_owner_lock_path") or "",
        },
        "checks": checks,
        "failed_checks": failed,
        "proof_revision": proof_revision,
        "proof_counters": proof_source,
    }


def build_health_payload(snap: Dict[str, Any]) -> Dict[str, Any]:
    """Return a minimal liveness status. This endpoint answers: is the process alive?"""
    return {
        "status": "ok",
        "alive": True,
        "version": APP_VERSION,
        "build_id": APP_BUILD_ID,
        "uptime_seconds": snap.get("uptime_seconds"),
        "instance_owner": {
            "active": bool(snap.get("instance_owner_active")),
            "pid": snap.get("instance_owner_pid"),
            "build_id": snap.get("instance_owner_build_id") or "",
            "since_utc": snap.get("instance_owner_since_utc") or "",
        },
    }



# RC7: lightweight UI/export helpers. These helpers are intentionally best-effort:
# broken or missing measurement logs must never affect the live controller.
_soc_day_cache: Dict[str, Any] = {"key": None, "points": [], "built_epoch": 0.0, "error": "", "building": False}
_graph_view_cache: Dict[str, Any] = {"key": None, "payload": None, "built_epoch": 0.0, "building": False}
_soc_day_cache_lock = threading.Lock()
_graph_view_cache_lock = threading.Lock()

# RC16: historical UI endpoints must be bounded.  Large Measurement-V4 logs on
# Raspberry Pi 3B+ are too expensive to scan completely for every dashboard
# request.  Recent graph windows therefore read only a bounded tail of the
# newest candidate files and cache the result.
_RECENT_MEASUREMENT_INITIAL_TAIL_BYTES = 4 * 1024 * 1024
_RECENT_MEASUREMENT_MAX_TAIL_BYTES = 64 * 1024 * 1024


def _safe_float(value: Any) -> Optional[float]:
    if value in (None, "", "-"):
        return None
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return None


def _first_snapshot_value(snapshot: Dict[str, Any], *keys: str) -> Any:
    """Return the first actually populated snapshot value.

    `dict.get(key, fallback)` is intentionally not used here because state
    snapshots contain many explicit `None` defaults which would otherwise mask
    a valid compatibility field further down the list.
    """
    for key in keys:
        value = snapshot.get(key)
        if value not in (None, "", "-"):
            return value
    return None


def _boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "ja", "ok"}


def _parse_measurement_dt(row: Dict[str, Any]) -> Optional[datetime]:
    raw_epoch_ms = row.get("measurement_epoch_ms")
    if raw_epoch_ms not in (None, ""):
        try:
            return datetime.fromtimestamp(float(raw_epoch_ms) / 1000.0)
        except Exception:
            pass
    raw_epoch = row.get("epoch_s") or row.get("epoch")
    if raw_epoch not in (None, ""):
        try:
            return datetime.fromtimestamp(float(raw_epoch))
        except Exception:
            pass
    raw = row.get("datetime_local") or row.get("measurement_time_utc") or ""
    text = str(raw).strip()
    if not text:
        date_part = str(row.get("date") or "").strip()
        time_part = str(row.get("timestamp") or "").strip()
        text = (date_part + " " + time_part).strip()
    if not text:
        return None
    for candidate in [text, text.replace("Z", "+00:00")]:
        try:
            dt = datetime.fromisoformat(candidate)
            if dt.tzinfo is not None:
                return dt.astimezone().replace(tzinfo=None)
            return dt
        except Exception:
            pass
    for fmt in ["%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M:%S", "%H:%M:%S"]:
        try:
            dt = datetime.strptime(text, fmt)
            if fmt == "%H:%M:%S":
                today = datetime.now()
                return today.replace(hour=dt.hour, minute=dt.minute, second=dt.second, microsecond=0)
            return dt
        except Exception:
            pass
    return None


def _measurement_log_dirs(cfg: Dict[str, Any]) -> List[str]:
    dirs: List[str] = []
    try:
        path, _, _ = resolve_log_path(cfg, allow_fallback=False)
        if path:
            dirs.append(os.path.dirname(os.path.abspath(path)))
    except Exception:
        pass
    for key in ["MEASUREMENT_LOG_DIR", "MEASUREMENT_LOG_FALLBACK_DIR"]:
        val = str(cfg.get(key, "") or "").strip()
        if val:
            dirs.append(os.path.abspath(val))
    unique = []
    for d in dirs:
        if d and d not in unique:
            unique.append(d)
    return unique


def _measurement_csv_files(cfg: Dict[str, Any]) -> List[str]:
    files: List[str] = []
    for d in _measurement_log_dirs(cfg):
        if not os.path.isdir(d):
            continue
        try:
            for name in os.listdir(d):
                if not name.lower().endswith(".csv"):
                    continue
                if "measurement" not in name.lower() and "zendure" not in name.lower():
                    continue
                files.append(os.path.join(d, name))
        except Exception:
            continue
    return sorted(set(files), key=lambda p: (os.path.getmtime(p) if os.path.exists(p) else 0, p))


def _read_csv_rows(path: str):
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as fh:
            sample = fh.read(4096)
            fh.seek(0)
            delimiter = ";" if sample.count(";") >= sample.count(",") else ","
            reader = csv.DictReader(fh, delimiter=delimiter)
            for row in reader:
                yield row
    except Exception:
        return


def _read_csv_tail_rows(path: str, start_dt: Optional[datetime], end_dt: Optional[datetime], initial_tail_bytes: int = _RECENT_MEASUREMENT_INITIAL_TAIL_BYTES, max_tail_bytes: int = _RECENT_MEASUREMENT_MAX_TAIL_BYTES):
    """Yield recent CSV rows from a bounded file tail.

    Measurement files are append-only and time ordered in normal operation.
    For interactive 24h/today graphs we only need recent rows near the end of
    the newest file(s).  Reading a bounded tail avoids multi-minute scans on
    Pi-class hardware.  The tail grows until it reaches the requested start
    time or the configured maximum.
    """
    try:
        size = os.path.getsize(path)
    except Exception:
        return
    if size <= 0:
        return

    tail_bytes = max(64 * 1024, min(int(initial_tail_bytes), max_tail_bytes))
    best_lines: List[str] = []
    delimiter = ","
    header = ""

    while True:
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as fh:
                sample = fh.read(4096)
                delimiter = ";" if sample.count(";") >= sample.count(",") else ","
                header = sample.splitlines()[0] if sample.splitlines() else ""
                if not header:
                    return
                offset = max(0, size - tail_bytes)
                fh.seek(offset)
                if offset > 0:
                    fh.readline()  # drop partial line
                lines = fh.read().splitlines()
        except Exception:
            return

        best_lines = lines
        earliest: Optional[datetime] = None
        if lines:
            try:
                reader = csv.DictReader([header] + lines, delimiter=delimiter)
                checked = 0
                for row in reader:
                    dt = _parse_measurement_dt(row)
                    if dt is None:
                        continue
                    checked += 1
                    if earliest is None or dt < earliest:
                        earliest = dt
                    if checked >= 200:
                        break
            except Exception:
                earliest = None
        if offset == 0 or not start_dt or (earliest is not None and earliest <= start_dt) or tail_bytes >= max_tail_bytes:
            break
        tail_bytes = min(tail_bytes * 4, max_tail_bytes, max(size, 1))

    try:
        reader = csv.DictReader([header] + best_lines, delimiter=delimiter)
        for row in reader:
            if not row:
                continue
            yield row
    except Exception:
        return


def _measurement_csv_files_for_window(cfg: Dict[str, Any], start_dt: Optional[datetime], end_dt: Optional[datetime]) -> List[str]:
    files = _measurement_csv_files(cfg)
    if not start_dt:
        return files
    # Keep candidate selection conservative.  File mtime is cheap and catches
    # append-only logs; a 36h tolerance avoids accidentally dropping daily files
    # around midnight or after clock adjustments.
    threshold = start_dt.timestamp() - 36 * 3600
    candidates: List[str] = []
    for path in files:
        try:
            if os.path.getmtime(path) >= threshold:
                candidates.append(path)
        except Exception:
            candidates.append(path)
    if not candidates and files:
        candidates = files[-2:]
    return sorted(set(candidates), key=lambda p: (os.path.getmtime(p) if os.path.exists(p) else 0, p))


def _grid_mini_values_from_snapshot(snap: Dict[str, Any], max_points: int = 48) -> List[Optional[float]]:
    vals: List[Optional[float]] = []
    for row in list(snap.get("graph_history", []) or [])[-max_points:]:
        if isinstance(row, dict):
            vals.append(_safe_float(row.get("grid_power", row.get("grid_power_w"))))
    return vals


def build_grid_mini_payload(snap: Dict[str, Any], max_points: int = 48) -> Dict[str, Any]:
    rows = list(snap.get("graph_history", []) or [])[-max_points:]
    points: List[Dict[str, Any]] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        value = _safe_float(row.get("grid_power", row.get("grid_power_w", row.get("raw_grid_power_w"))))
        if value is None:
            continue
        time_text = str(row.get("timestamp") or row.get("time") or "")
        if not time_text:
            dt_text = str(row.get("datetime_local") or "")
            time_text = dt_text[11:19] if len(dt_text) >= 19 else f"Punkt {idx+1}"
        status = "Bezug aus Netz" if value > 50 else ("Einspeisung / Export" if value < -50 else "ausgeglichen")
        points.append({"time": time_text, "value": value, "status": status})
    return {"points": points, "count": len(points), "snapshot_epoch_ms": int(time.time() * 1000)}


def _inventory_cache_path(cfg: Dict[str, Any]) -> str:
    dirs = _measurement_log_dirs(cfg)
    return os.path.join(dirs[0], "zec_storage_inventory_cache.json") if dirs else ""


def _load_storage_inventory_cache(path: str) -> Dict[str, Any]:
    if not path:
        return {"schema": 1, "files": {}}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict) and isinstance(data.get("files"), dict):
            return data
    except Exception:
        pass
    return {"schema": 1, "files": {}}


def _write_storage_inventory_cache(path: str, data: Dict[str, Any]) -> None:
    if not path:
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            if 'tmp' in locals() and os.path.exists(tmp):
                os.unlink(tmp)
        except Exception:
            pass


def _measurement_manifest_entries(cfg: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    entries: Dict[str, Dict[str, Any]] = {}
    for directory in _measurement_log_dirs(cfg):
        path = os.path.join(directory, "zec_measurement_manifest.json")
        try:
            with open(path, "r", encoding="utf-8") as handle:
                manifest = json.load(handle)
        except Exception:
            continue
        for item in list((manifest or {}).get("files") or []):
            if not isinstance(item, dict):
                continue
            rel = str(item.get("relative_path") or item.get("file_name") or "").strip()
            if not rel:
                continue
            entries[os.path.abspath(os.path.join(directory, rel))] = item
    return entries


def _inventory_entry_from_scan(path: str, max_rows_per_file: int) -> Dict[str, Any]:
    first_dt: Optional[datetime] = None
    last_dt: Optional[datetime] = None
    row_count = 0
    for row in _read_csv_rows(path):
        if row_count >= max_rows_per_file:
            break
        dt = _parse_measurement_dt(row)
        if dt is None:
            continue
        row_count += 1
        if first_dt is None or dt < first_dt:
            first_dt = dt
        if last_dt is None or dt > last_dt:
            last_dt = dt
    return {
        "row_count": row_count,
        "first": first_dt.isoformat(sep=" ", timespec="seconds") if first_dt else "",
        "last": last_dt.isoformat(sep=" ", timespec="seconds") if last_dt else "",
        "readable": bool(first_dt is not None and last_dt is not None),
        "source": "scan",
    }


def measurement_availability(cfg: Dict[str, Any], max_rows_per_file: int = 250000) -> Dict[str, Any]:
    """Build an incremental inventory without rescanning unchanged V4 files.

    The writer manifest is authoritative for row count/time bounds where
    available.  A small persistent cache covers closed legacy files.  Only new
    or changed files missing both sources are scanned.
    """
    files = _measurement_csv_files(cfg)
    cache_path = _inventory_cache_path(cfg)
    old_cache = _load_storage_inventory_cache(cache_path)
    cached_files = dict(old_cache.get("files") or {})
    manifests = _measurement_manifest_entries(cfg)
    next_cache: Dict[str, Dict[str, Any]] = {}
    first_dt: Optional[datetime] = None
    last_dt: Optional[datetime] = None
    row_count = 0
    readable_files = 0
    reused = 0
    from_manifest = 0
    scanned = 0

    for path in files:
        absolute = os.path.abspath(path)
        try:
            stat = os.stat(absolute)
            signature = {"size": int(stat.st_size), "mtime_ns": int(stat.st_mtime_ns)}
        except Exception:
            continue
        previous = cached_files.get(absolute) if isinstance(cached_files.get(absolute), dict) else None
        entry: Dict[str, Any]
        if previous and int(previous.get("size", -1)) == signature["size"] and int(previous.get("mtime_ns", -1)) == signature["mtime_ns"]:
            entry = dict(previous)
            entry["source"] = "cache"
            reused += 1
        else:
            manifest = manifests.get(absolute)
            manifest_rows = manifest.get("row_count") if isinstance(manifest, dict) else None
            first_epoch = manifest.get("first_measurement_epoch_ms") if isinstance(manifest, dict) else None
            last_epoch = manifest.get("last_measurement_epoch_ms") if isinstance(manifest, dict) else None
            try:
                valid_manifest = int(manifest_rows) >= 0 and int(first_epoch) > 0 and int(last_epoch) > 0
            except Exception:
                valid_manifest = False
            if valid_manifest:
                first_manifest = datetime.fromtimestamp(int(first_epoch) / 1000.0)
                last_manifest = datetime.fromtimestamp(int(last_epoch) / 1000.0)
                entry = {
                    "row_count": int(manifest_rows),
                    "first": first_manifest.isoformat(sep=" ", timespec="seconds"),
                    "last": last_manifest.isoformat(sep=" ", timespec="seconds"),
                    "readable": True,
                    "source": "manifest",
                }
                from_manifest += 1
            else:
                entry = _inventory_entry_from_scan(absolute, max_rows_per_file)
                scanned += 1
            entry.update(signature)
        next_cache[absolute] = dict(entry)
        try:
            item_first = datetime.fromisoformat(str(entry.get("first") or ""))
            item_last = datetime.fromisoformat(str(entry.get("last") or ""))
        except Exception:
            item_first = item_last = None
        if bool(entry.get("readable")) and item_first is not None and item_last is not None:
            readable_files += 1
            row_count += max(0, int(entry.get("row_count") or 0))
            if first_dt is None or item_first < first_dt:
                first_dt = item_first
            if last_dt is None or item_last > last_dt:
                last_dt = item_last

    _write_storage_inventory_cache(cache_path, {
        "schema": 1,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": next_cache,
    })
    mode = measurement_log_mode(cfg)
    return {
        "logging_mode": mode,
        "logging_active": mode != "off",
        "file_count": len(files),
        "readable_file_count": readable_files,
        "row_count": row_count,
        "available": first_dt is not None and last_dt is not None,
        "start": first_dt.isoformat(sep=" ", timespec="seconds") if first_dt else "",
        "end": last_dt.isoformat(sep=" ", timespec="seconds") if last_dt else "",
        "files": [os.path.basename(path) for path in files[-10:]],
        "inventory_cache_path": cache_path,
        "inventory_files_reused": reused,
        "inventory_files_from_manifest": from_manifest,
        "inventory_files_scanned": scanned,
        "inventory_strategy": "incremental_manifest_cache",
    }


def _field(row: Dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in row and row.get(name) not in (None, ""):
            return row.get(name)
    return ""


def _graph_point_from_row(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    dt = _parse_measurement_dt(row)
    if dt is None:
        return None
    grid = _safe_float(_field(row, "grid_power_w", "norm_grid_power_w", "grid_power"))
    target = _safe_float(_field(row, "target_final_w", "zendure_target_power_w", "zendure_target_signed_power"))
    actual = _safe_float(_field(row, "zendure_actual_power_w", "actual_zendure_power_w", "zendure_system_signed_power"))
    soc = _safe_float(_field(row, "zendure_soc_percent", "norm_zendure_soc_percent", "soc"))
    pv = _safe_float(_field(row, "pv_power_w")) if _boolish(_field(row, "pv_power_valid")) else None
    house = _safe_float(_field(row, "house_power_w")) if _boolish(_field(row, "house_power_valid")) else None
    return {
        "time": dt.strftime("%H:%M:%S"),
        "datetime_local": dt.isoformat(sep=" ", timespec="seconds"),
        "epoch_ms": int(dt.timestamp() * 1000),
        "grid_power_w": grid,
        "zendure_target_power_w": target,
        "zendure_actual_power_w": actual,
        "pv_power_w": pv,
        "house_power_w": house,
        "soc": soc,
        "mode": str(_field(row, "operating_mode", "mode") or ""),
        "mode_label": mode_label(str(_field(row, "operating_mode", "mode") or "")),
        "control_reason": str(_field(row, "target_final_reason", "control_reason") or ""),
        "limit_reason": str(_field(row, "target_final_reason", "limit_reason") or ""),
        "data_status": "gültig" if (_boolish(_field(row, "zendure_soc_valid", "soc_valid")) or soc is not None) else "nicht bewertet",
        "cross_charge_limited": _boolish(_field(row, "control_cross_charge_limited", "cross_charge_guard_limited")),
        "safe_state_active": _boolish(_field(row, "safe_state_active")) or str(_field(row, "operating_mode", "mode")) == "SAFE_STATE",
        "night_window_active": _boolish(_field(row, "night_window_active", "night_discharge_window_active")),
        "night_reserve_active": _boolish(_field(row, "control_night_reserve_active", "night_discharge_reserve_active")),
    }


def _downsample_points(points: List[Dict[str, Any]], resolution_s: int) -> List[Dict[str, Any]]:
    if resolution_s <= 1:
        return points
    buckets: Dict[int, Dict[str, Any]] = {}
    for point in points:
        epoch_ms = point.get("epoch_ms")
        if epoch_ms is None:
            continue
        bucket = int(epoch_ms // (resolution_s * 1000))
        buckets[bucket] = point
    return [buckets[k] for k in sorted(buckets)]


def _graph_points_from_measurements(cfg: Dict[str, Any], start_dt: Optional[datetime], end_dt: Optional[datetime], resolution_s: int = 60, max_points: int = 3000) -> List[Dict[str, Any]]:
    points: List[Dict[str, Any]] = []
    files = _measurement_csv_files_for_window(cfg, start_dt, end_dt)
    use_tail_reader = bool(start_dt)
    for path in files:
        row_iter = _read_csv_tail_rows(path, start_dt, end_dt) if use_tail_reader else _read_csv_rows(path)
        for row in row_iter:
            point = _graph_point_from_row(row)
            if point is None:
                continue
            dt = datetime.fromtimestamp(point["epoch_ms"] / 1000.0)
            if start_dt and dt < start_dt:
                continue
            if end_dt and dt > end_dt:
                continue
            points.append(point)
    points.sort(key=lambda p: p.get("epoch_ms", 0))
    points = _downsample_points(points, resolution_s)
    if len(points) > max_points:
        step = max(1, int(len(points) / max_points))
        points = points[::step][-max_points:]
    return points


def _graph_points_from_ram(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    points: List[Dict[str, Any]] = []
    today = datetime.now().date()
    for row in rows:
        date_part = str(row.get("date") or today.isoformat())
        time_part = str(row.get("timestamp") or "")
        dt = _parse_measurement_dt({"datetime_local": (date_part + " " + time_part).strip(), "timestamp": time_part}) or datetime.now()
        points.append({
            "time": str(row.get("timestamp") or dt.strftime("%H:%M:%S")),
            "datetime_local": dt.isoformat(sep=" ", timespec="seconds"),
            "epoch_ms": int(dt.timestamp() * 1000),
            "grid_power_w": _safe_float(row.get("grid_power_w", row.get("grid_power"))),
            "grid_power_raw_w": _safe_float(row.get("raw_grid_power_w", row.get("raw_grid_power"))),
            "zendure_target_power_w": _safe_float(row.get("zendure_target_power_w", row.get("target_final_w"))),
            "zendure_actual_power_w": _safe_float(row.get("zendure_actual_power_w", row.get("zendure_system_signed_power"))),
            "pv_power_w": _safe_float(row.get("pv_power_w")),
            "house_power_w": _safe_float(row.get("house_power_w")),
            "soc": _safe_float(row.get("zendure_soc_percent", row.get("soc"))),
            "mode": str(row.get("mode") or ""),
            "mode_label": str(row.get("mode_label") or mode_label(str(row.get("mode") or ""))),
            "control_reason": str(row.get("control_reason") or row.get("target_final_reason") or ""),
            "limit_reason": str(row.get("limit_label") or row.get("limit_reason") or ""),
            "data_status": "gültig" if row.get("soc_valid", True) else "ungültig",
            "cross_charge_limited": _boolish(row.get("cross_charge_guard_limited")),
            "safe_state_active": _boolish(row.get("safe_state_active")) or str(row.get("mode")) == "SAFE_STATE",
            "night_window_active": _boolish(row.get("night_discharge_window_active")),
            "night_reserve_active": _boolish(row.get("night_discharge_reserve_active")),
        })
    return points


def _series_stats(points: List[Dict[str, Any]], key: str) -> Dict[str, Any]:
    vals = [float(p[key]) for p in points if p.get(key) is not None]
    if not vals:
        return {"available": False}
    return {"available": True, "current": vals[-1], "min": min(vals), "max": max(vals), "avg": sum(vals)/len(vals)}


def _soc_stats(points: List[Dict[str, Any]]) -> Dict[str, Any]:
    vals = [float(p["soc"]) for p in points if p.get("soc") is not None]
    if not vals:
        return {"available": False}
    return {"available": True, "current": vals[-1], "start": vals[0], "min": min(vals), "max": max(vals), "end": vals[-1]}


def _events_from_points(points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    last_mode = None
    last_night = False
    last_event_epoch_by_type: Dict[str, float] = {}
    def add_event(p: Dict[str, Any], typ: str, label: str, min_gap_s: int = 0) -> None:
        try:
            ep = float(p.get("epoch_ms") or 0) / 1000.0
        except Exception:
            ep = 0.0
        if min_gap_s and ep and ep - float(last_event_epoch_by_type.get(typ) or 0) < min_gap_s:
            return
        last_event_epoch_by_type[typ] = ep
        events.append({"time": p.get("time"), "type": typ, "label": label})
    for p in points:
        mode = p.get("mode") or ""
        if mode and last_mode is not None and mode != last_mode:
            important = ("SAFE" in mode or "NIGHT" in mode or mode not in {"AUTO", "HOLD", "AUTO_CHARGE", "AUTO_DISCHARGE"})
            add_event(p, "MODE_CHANGE", f"Modus: {mode}", min_gap_s=0 if important else 300)
        if p.get("safe_state_active"):
            add_event(p, "SAFE_STATE", "Safe-State", min_gap_s=300)
        if p.get("cross_charge_limited"):
            add_event(p, "CROSS_CHARGE", "Cross-Charge begrenzt", min_gap_s=300)
        night = bool(p.get("night_window_active") or mode == "NIGHT_DISCHARGE")
        if last_mode is not None and night != last_night:
            add_event(p, "NIGHT", "Nachtmodus Start" if night else "Nachtmodus Ende")
        if p.get("night_reserve_active"):
            add_event(p, "NIGHT_RESERVE", "Reserve-SOC erreicht", min_gap_s=300)
        last_mode = mode
        last_night = night
    # Standard dashboard: keep marker feed useful, not a raw event log.
    return events[-60:]


def build_graph_view_payload(cfg: Dict[str, Any], snap: Dict[str, Any], range_name: str = "live", resolution: str = "live") -> Dict[str, Any]:
    """Build the modern graph payload with an explicit, stable time axis.

    RC15 separates the chart axis window from the available data points.  This
    keeps "Letzte 24 Stunden" as a true 24-hour axis even when measurements
    have gaps or when the visible data covers only part of that interval.
    """
    now = datetime.now()
    res_s = 1 if resolution == "live" else (60 if resolution in {"1min", "1m"} else 300)

    axis_end_dt = now
    if range_name in {"24h", "last24h"}:
        axis_start_dt = now - timedelta(hours=24)
        label = f"{axis_start_dt.strftime('%d.%m. %H:%M')}–{axis_end_dt.strftime('%d.%m. %H:%M')}"
    elif range_name in {"6h", "last6h"}:
        axis_start_dt = now - timedelta(hours=6)
        label = f"{axis_start_dt.strftime('%H:%M')}–{axis_end_dt.strftime('%H:%M')}"
    elif range_name in {"1h", "last1h"}:
        axis_start_dt = now - timedelta(hours=1)
        label = f"{axis_start_dt.strftime('%H:%M')}–{axis_end_dt.strftime('%H:%M')}"
    elif range_name == "today":
        axis_start_dt = datetime.combine(now.date(), datetime.min.time())
        axis_end_dt = axis_start_dt + timedelta(hours=24)
        label = f"{axis_start_dt.strftime('%d.%m.')} 00:00–24:00"
    elif range_name == "15m":
        axis_start_dt = now - timedelta(minutes=15)
        label = f"{axis_start_dt.strftime('%H:%M')}–{axis_end_dt.strftime('%H:%M')}"
    else:
        axis_start_dt = now - timedelta(minutes=15)
        label = "Live/RAM"

    use_measurements = range_name not in {"live", "15m"}
    points: List[Dict[str, Any]] = []
    source = "measurement_db_1min"
    db_meta: Dict[str, Any] = {}
    cache_key = ""
    cache_status = "uncached"
    graph_cache_owned = False
    if use_measurements:
        try:
            db_points, db_meta = query_graph_points(cfg, axis_start_dt, axis_end_dt, limit=5000)
            if db_points:
                points = db_points
                cache_status = "db_hit"
                source = "measurement_db_1min"
                use_measurements = False
            else:
                source = "measurement_v4"
        except Exception as exc:
            db_meta = {"db_status": "error", "db_error": str(exc)}
            source = "measurement_v4"
    if use_measurements:
        # Round the cache key to one minute, but keep the axis end at current
        # time so the front-end always receives the requested window.
        cache_key_parts = [range_name, resolution, axis_start_dt.isoformat(), now.strftime("%Y-%m-%d-%H-%M")]
        for path in _measurement_csv_files_for_window(cfg, axis_start_dt, axis_end_dt):
            try:
                cache_key_parts.append(f"{path}:{int(os.path.getmtime(path))}:{os.path.getsize(path)}")
            except Exception:
                pass
        cache_key = "|".join(cache_key_parts)
        with _graph_view_cache_lock:
            cached_payload = _graph_view_cache.get("payload")
            cached_age = time.time() - float(_graph_view_cache.get("built_epoch") or 0)
            if _graph_view_cache.get("key") == cache_key and cached_payload is not None and cached_age < 180:
                payload = dict(cached_payload or {})
                payload["cache_status"] = "hit"
                payload["cache_age_s"] = int(cached_age)
                return payload
            if bool(_graph_view_cache.get("building")) and cached_payload is not None:
                payload = dict(cached_payload or {})
                payload["cache_status"] = "stale_while_building"
                payload["cache_age_s"] = int(cached_age)
                return payload
            if bool(_graph_view_cache.get("building")):
                use_measurements = False
                source = "ram_graph_history_pending_measurement_cache"
            else:
                _graph_view_cache["building"] = True
                graph_cache_owned = True
        if use_measurements:
            try:
                points = _graph_points_from_measurements(cfg, axis_start_dt, axis_end_dt, resolution_s=max(60, res_s))
                cache_status = "rebuilt"
            except Exception:
                points = []
                cache_status = "rebuild_failed"

    if not points:
        points = _graph_points_from_ram(list(snap.get("graph_history", [])))
        if source in {"measurement_v4", "measurement_db_1min"} or source.startswith("measurement_db"):
            source = "ram_graph_history"

    # Always clamp explicit time ranges to the requested axis window.  Live/RAM
    # remains data-driven so existing RAM-history tests and ad-hoc debug graphs
    # can still render historical in-memory samples.
    start_ms = int(axis_start_dt.timestamp() * 1000)
    end_ms = int(axis_end_dt.timestamp() * 1000)
    if range_name == "live" and points:
        epochs = []
        for point in points:
            try:
                epochs.append(int(point.get("epoch_ms") or 0))
            except Exception:
                pass
        if epochs:
            start_ms = min(epochs)
            end_ms = max(epochs)
            if end_ms <= start_ms:
                end_ms = start_ms + 60_000
    else:
        filtered: List[Dict[str, Any]] = []
        for point in points:
            try:
                ep = int(point.get("epoch_ms") or 0)
            except Exception:
                continue
            if start_ms <= ep <= end_ms:
                filtered.append(point)
        points = filtered

    kpis = {
        "grid_power_w": _series_stats(points, "grid_power_w"),
        "zendure_target_power_w": _series_stats(points, "zendure_target_power_w"),
        "zendure_actual_power_w": _series_stats(points, "zendure_actual_power_w"),
        "pv_power_w": _series_stats(points, "pv_power_w"),
        "house_power_w": _series_stats(points, "house_power_w"),
        "soc": _soc_stats(points),
    }
    payload = {
        "source": source,
        "range": {
            "name": range_name,
            "resolution": resolution,
            "points": len(points),
            "axis_start_epoch_ms": start_ms,
            "axis_end_epoch_ms": end_ms,
            "axis_duration_hours": round((end_ms - start_ms) / 3600000.0, 3),
            "label": label,
            "data_start_epoch_ms": int(points[0].get("epoch_ms")) if points else None,
            "data_end_epoch_ms": int(points[-1].get("epoch_ms")) if points else None,
        },
        "series_available": {"pv_power_w": kpis["pv_power_w"].get("available", False), "house_power_w": kpis["house_power_w"].get("available", False)},
        "points": points,
        "kpis": kpis,
        "events": _events_from_points(points),
        "signals": current_signals_payload(snap),
        "cache_status": cache_status,
        "cache_age_s": 0,
        "db": db_meta,
    }
    if graph_cache_owned:
        try:
            with _graph_view_cache_lock:
                _graph_view_cache.update({"key": cache_key, "payload": payload, "built_epoch": time.time(), "building": False})
        except Exception:
            try:
                with _graph_view_cache_lock:
                    _graph_view_cache["building"] = False
            except Exception:
                pass
    return payload

def current_signals_payload(snap: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {"signal": "Netzleistung", "value": snap.get("grid_power"), "unit": "W", "source": snap.get("raw_grid_source"), "status": "gültig" if snap.get("grid_power_valid") else "ungültig"},
        {"signal": "Zendure Soll", "value": snap.get("zendure_target_signed_power", snap.get("current_target_power")), "unit": "W", "source": "ZEC Logic", "status": "gültig"},
        {"signal": "Zendure Ist", "value": snap.get("zendure_system_signed_power"), "unit": "W", "source": snap.get("zendure_telemetry_source"), "status": "gültig" if snap.get("actual_zendure_power_valid") else "ungültig"},
        {"signal": "SOC", "value": snap.get("battery_soc"), "unit": "%", "source": snap.get("zendure_telemetry_source"), "status": "gültig" if snap.get("soc_valid") else "ungültig"},
        {"signal": "MQTT", "value": snap.get("zendure_mqtt_overall_status"), "unit": "", "source": "Zendure MQTT", "status": "verbunden" if snap.get("mqtt_connected") else "getrennt"},
    ]


def _append_live_soc_day_point(points: List[Dict[str, Any]], snap: Dict[str, Any], today: Any) -> List[Dict[str, Any]]:
    result = list(points or [])
    soc = snap.get("battery_soc")
    if soc is None:
        return result
    now = datetime.now()
    day_start = datetime.combine(today, datetime.min.time())
    minute = int((now - day_start).total_seconds() // 60)
    if minute < 0 or minute > 1440:
        return result
    if result and int(result[-1].get("minute_of_day", -1)) >= minute:
        return result
    result.append({
        "time": now.strftime("%H:%M"),
        "minute_of_day": minute,
        "soc": soc,
        "valid": bool(snap.get("soc_valid", True)),
        "source": snap.get("zendure_telemetry_source") or "Live",
        "mode": snap.get("current_mode"),
        "data_status": "gültig" if snap.get("soc_valid", True) else "ungültig",
    })
    return result


def build_soc_day_payload(cfg: Dict[str, Any], snap: Dict[str, Any]) -> Dict[str, Any]:
    """Return the lightweight status-page SOC day curve.

    RC16 keeps the status page interactive: Measurement-V4 bootstrapping is
    cached, guarded by single-flight, and based on bounded recent file tails.
    Concurrent requests receive stale cached data plus the current live point
    instead of launching parallel expensive scans.
    """
    today = datetime.now().date()
    sample_s = int(cfg.get("SOC_DAY_GRAPH_SAMPLE_SECONDS", 60) or 60)
    now_epoch = time.time()
    cache_ttl_s = max(60, int(cfg.get("SOC_DAY_GRAPH_BOOTSTRAP_CACHE_SECONDS", 300) or 300))
    cache_key = f"{today.isoformat()}|{sample_s}"

    with _soc_day_cache_lock:
        cached_key = _soc_day_cache.get("key")
        cached_age = now_epoch - float(_soc_day_cache.get("built_epoch") or 0)
        if cached_key == cache_key and cached_age < cache_ttl_s:
            base_points = list(_soc_day_cache.get("points") or [])
            error = str(_soc_day_cache.get("error") or "")
            points = _append_live_soc_day_point(base_points, snap, today)
            return {
                "date": today.isoformat(),
                "sample_seconds": sample_s,
                "axis_minute_start": 0,
                "axis_minute_end": 1440,
                "points": points[-1500:],
                "bootstrap_error": error,
                "source": "measurement_v4+live_cached" if points else "live_only",
                "cache_status": "hit",
                "cache_age_s": int(cached_age),
            }
        if bool(_soc_day_cache.get("building")):
            base_points = list(_soc_day_cache.get("points") or [])
            points = _append_live_soc_day_point(base_points, snap, today)
            return {
                "date": today.isoformat(),
                "sample_seconds": sample_s,
                "axis_minute_start": 0,
                "axis_minute_end": 1440,
                "points": points[-1500:],
                "bootstrap_error": str(_soc_day_cache.get("error") or ""),
                "source": "measurement_v4+live_stale" if base_points else "live_only_pending_measurement_cache",
                "cache_status": "stale_while_building",
                "cache_age_s": int(cached_age) if cached_key == cache_key else -1,
            }
        _soc_day_cache["building"] = True

    points: List[Dict[str, Any]] = []
    error = ""
    soc_source = "measurement_v4"
    if cfg.get("SOC_DAY_GRAPH_BOOTSTRAP_FROM_MEASUREMENTS", True):
        try:
            start_dt = datetime.combine(today, datetime.min.time())
            end_dt = start_dt + timedelta(days=1)
            db_points, db_meta = query_graph_points(cfg, start_dt, end_dt, limit=2000)
            if db_points:
                soc_source = "measurement_db_1min"
                for p in db_points:
                    if p.get("soc") is None:
                        continue
                    minute = int((datetime.fromtimestamp(p["epoch_ms"]/1000.0) - start_dt).total_seconds() // 60)
                    if minute < 0 or minute > 1440:
                        continue
                    points.append({
                        "time": p.get("time"),
                        "minute_of_day": minute,
                        "soc": p.get("soc"),
                        "valid": p.get("data_status") in {"gültig", "nicht bewertet"},
                        "source": "SQLite",
                        "mode": p.get("mode"),
                        "data_status": p.get("data_status", "gültig"),
                    })
            else:
                for p in _graph_points_from_measurements(cfg, start_dt, end_dt, resolution_s=sample_s, max_points=2000):
                    if p.get("soc") is None:
                        continue
                    minute = int((datetime.fromtimestamp(p["epoch_ms"]/1000.0) - start_dt).total_seconds() // 60)
                    if minute < 0 or minute > 1440:
                        continue
                    points.append({
                        "time": p.get("time"),
                        "minute_of_day": minute,
                        "soc": p.get("soc"),
                        "valid": p.get("data_status") in {"gültig", "nicht bewertet"},
                        "source": "Measurement V4",
                        "mode": p.get("mode"),
                        "data_status": p.get("data_status", "gültig"),
                    })
        except Exception as exc:
            error = str(exc)
            points = []
    with _soc_day_cache_lock:
        _soc_day_cache.update({"key": cache_key, "points": points, "built_epoch": now_epoch, "error": error, "building": False})
    points = _append_live_soc_day_point(points, snap, today)
    return {
        "date": today.isoformat(),
        "sample_seconds": sample_s,
        "axis_minute_start": 0,
        "axis_minute_end": 1440,
        "points": points[-1500:],
        "bootstrap_error": error,
        "source": (soc_source + "+live") if points else "live_only",
        "cache_status": "rebuilt",
        "cache_age_s": 0,
    }

_replay_health_cache: Dict[str, Any] = {"port": None, "available": False, "checked_epoch": 0.0}


def replay_service_available(cfg: Dict[str, Any]) -> bool:
    """Return cached reachability of the optional replay service.

    The replay root page enumerates CSV files and can legitimately take longer
    than a sub-second probe.  RC9 therefore uses the dedicated lightweight
    ``/health`` endpoint and validates its JSON contract.  Negative results are
    cached only briefly so a service started just after the controller becomes
    visible without waiting half a minute.  This function is called only by the
    web/status path, never by the controller loop.
    """
    port = int(cfg.get("REPLAY_WEB_PORT", 8090) or 8090)
    now = time.time()
    cached_for = now - float(_replay_health_cache.get("checked_epoch") or 0)
    cache_ttl = 30.0 if bool(_replay_health_cache.get("available")) else 5.0
    if _replay_health_cache.get("port") == port and cached_for < cache_ttl:
        return bool(_replay_health_cache.get("available"))

    available = False
    try:
        response = requests.get(f"http://127.0.0.1:{port}/health", timeout=1.5)
        response.raise_for_status()
        payload = response.json()
        available = isinstance(payload, dict) and str(payload.get("status") or "").lower() == "ok"
    except Exception:
        available = False
    _replay_health_cache.update({"port": port, "available": available, "checked_epoch": now})
    return available


def analysis_service_url(cfg: Dict[str, Any]) -> str:
    # The final browser URL is built client-side from window.location.hostname;
    # returning a relative placeholder avoids 127.0.0.1 links from remote PCs.
    port = int(cfg.get("REPLAY_WEB_PORT", 8090) or 8090)
    return f"//__CURRENT_HOST__:{port}"


def create_app(config_manager: ConfigManager, state: ControllerState, on_config_saved=None) -> FastAPI:
    event_journal = OperationalEventJournal(config_manager.get, state)
    settings_service = SettingsService(config_manager)
    config_state_store = ConfigStateStore(config_manager.path)
    config_artifacts = ConfigArtifactCoordinator(config_manager, settings_service, config_state_store)
    storage_inventory = StorageInventory(lambda: measurement_availability(config_manager.get()))
    csrf_cookie_name = "zec_settings_csrf"
    restart_lock = threading.Lock()
    restart_state = {"last_attempt_monotonic": 0.0, "in_flight": False}
    repair_lock = threading.RLock()
    repair_previews: Dict[str, Dict[str, Any]] = {}
    repair_state = {"last_attempt_monotonic": 0.0, "in_flight": False}

    def csrf_token_for(request: Request) -> str:
        token = str(request.cookies.get(csrf_cookie_name) or "")
        if len(token) < 32:
            token = secrets.token_urlsafe(32)
        return token

    def verify_admin_request(request: Request) -> str:
        cookie_token = str(request.cookies.get(csrf_cookie_name) or "")
        header_token = str(request.headers.get("x-csrf-token") or "")
        if not cookie_token or not secrets.compare_digest(cookie_token, header_token):
            raise PermissionError("CSRF_TOKEN_INVALID")
        host = str(request.headers.get("host") or "").lower()
        origin = str(request.headers.get("origin") or "")
        referer = str(request.headers.get("referer") or "")
        source = origin or referer
        if not source:
            raise PermissionError("ORIGIN_REQUIRED")
        try:
            source_host = str(urlsplit(source).netloc or "").lower()
        except Exception:
            source_host = ""
        if not source_host or source_host != host:
            raise PermissionError("ORIGIN_MISMATCH")
        return cookie_token

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        event_journal.start()
        storage_inventory.refresh_async()
        try:
            yield
        finally:
            event_journal.stop()

    app = FastAPI(title="Zendure Energy Controller", version=APP_VERSION, lifespan=lifespan)
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    status_view_cache: Dict[str, Any] = {"built_epoch": 0.0, "payload": None}
    status_view_lock = threading.Lock()

    def html_or_headless(page_builder, *args, **kwargs):
        cfg = config_manager.get()
        if cfg.get("HEADLESS_MODE", False):
            return build_headless_page(cfg)
        return page_builder(*args, **kwargs)

    @app.get("/", response_class=HTMLResponse)
    def homepage():
        return html_or_headless(build_status_page, config_manager.get(), state.snapshot())

    @app.get("/status_old", response_class=HTMLResponse)
    def status_old_page():
        return html_or_headless(build_status_page_legacy, config_manager.get(), state.snapshot())

    @app.get("/status")
    def status():
        snap = state.snapshot()
        snap["controller_version"] = APP_VERSION
        snap["controller_version_label"] = APP_VERSION_LABEL
        snap["controller_build_id"] = APP_BUILD_ID
        snap.pop("graph_history", None)
        snap.pop("event_history", None)
        snap.pop("mqtt_topic_diagnostics", None)
        snap["settings_runtime"] = config_manager.status()
        return snap

    @app.get("/status-view-data")
    def status_view_data():
        now = time.time()
        with status_view_lock:
            cached = status_view_cache.get("payload")
            if cached is not None and now - float(status_view_cache.get("built_epoch") or 0) < 1.0:
                return dict(cached)
        snap = state.snapshot()
        payload = build_status_view_payload(config_manager.get(), snap)
        with status_view_lock:
            status_view_cache.update({"built_epoch": now, "payload": payload})
        return payload

    @app.get("/grid-mini-data")
    def grid_mini_data():
        return build_grid_mini_payload(state.snapshot())

    @app.get("/graph-data")
    def graph_data():
        return state.snapshot()["graph_history"]

    @app.get("/graph-data.csv")
    def graph_data_csv():
        # Schema-neutraler UI-Graph-Export; ausdrücklich kein Measurement-V4-Paket.
        if config_manager.get().get("HEADLESS_MODE", False):
            return HTMLResponse(build_headless_page(config_manager.get()))
        return PlainTextResponse(
            rows_to_csv(state.snapshot()["graph_history"]),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=graph-verlauf.csv"},
        )

    @app.get("/graph-view-data")
    def graph_view_data(range: str = "live", resolution: str = "live"):
        return build_graph_view_payload(config_manager.get(), state.snapshot(), range_name=range, resolution=resolution)

    @app.get("/soc-day-data")
    def soc_day_data(date: Optional[str] = None):
        # Legacy endpoint name now returns the improved storage day payload for
        # the status page.  Older tests/tools still find /soc-day-data, while
        # the new UI also uses /storage-soc-day-data explicitly.
        return build_storage_soc_day_payload(config_manager.get(), state.snapshot(), date=date)

    @app.get("/storage-soc-day-data")
    def storage_soc_day_data(date: Optional[str] = None):
        return build_storage_soc_day_payload(config_manager.get(), state.snapshot(), date=date)

    @app.get("/grid-mini-sparkline", response_class=HTMLResponse)
    def grid_mini_sparkline():
        snap = state.snapshot()
        svg = _mini_svg_sparkline(_grid_mini_values_from_snapshot(snap), stroke="#2ca24d")
        return HTMLResponse(svg)

    @app.get("/measurements", response_class=HTMLResponse)
    def measurements_page():
        return html_or_headless(build_measurements_page, config_manager.get())

    @app.get("/storage/status")
    def storage_status():
        """O(1) copy of the last completed inventory; never scans storage."""
        return storage_inventory.snapshot()

    @app.post("/storage/inventory-refresh")
    async def storage_inventory_refresh(request: Request):
        try:
            verify_admin_request(request)
        except PermissionError as exc:
            return JSONResponse({"error": str(exc)}, status_code=403)
        result = storage_inventory.refresh_async()
        event_journal.record_admin_action(
            "STORAGE_INVENTORY_REFRESH",
            "Manuelle Aktualisierung des gecachten Storage-Inventars angefordert.",
            result,
        )
        return JSONResponse(result, status_code=202 if result.get("status") == "scheduled" else 200)

    @app.get("/measurements/availability")
    def measurements_availability():
        # Legacy adapter: the expensive CSV inventory is never rebuilt in this
        # request. Existing consumers receive the cached snapshot.
        data = storage_inventory.snapshot()
        try:
            data["measurement_db"] = db_status_for_config(config_manager.get())
        except Exception as exc:
            data["measurement_db"] = {"measurement_db_status": "error", "measurement_db_error": str(exc)}
        return data

    @app.get("/measurement-db-status")
    def measurement_db_status():
        return db_status_for_config(config_manager.get())

    @app.get("/operational-events")
    def operational_events(days: int = 2, limit: int = 250):
        return {"items": event_journal.list_recent(days=max(1, min(days, 90)), limit=max(1, min(limit, 1000)))}

    @app.get("/measurements/export.csv")
    def measurements_export_csv(start: str = "", end: str = ""):
        cfg = config_manager.get()
        if cfg.get("HEADLESS_MODE", False):
            return HTMLResponse(build_headless_page(cfg))
        start_dt = _parse_measurement_dt({"datetime_local": start}) if start else None
        end_dt = _parse_measurement_dt({"datetime_local": end}) if end else None
        out = io.StringIO()
        writer = None
        rows_written = 0
        for path in _measurement_csv_files(cfg):
            for row in _read_csv_rows(path):
                dt = _parse_measurement_dt(row)
                if dt is None:
                    continue
                if start_dt and dt < start_dt:
                    continue
                if end_dt and dt > end_dt:
                    continue
                if writer is None:
                    fields = list(row.keys())
                    writer = csv.DictWriter(out, fieldnames=fields, delimiter=";")
                    writer.writeheader()
                writer.writerow({k: row.get(k, "") for k in writer.fieldnames})
                rows_written += 1
        if writer is None:
            availability = storage_inventory.snapshot()
            if not availability.get("available") and not availability.get("logging_active"):
                msg = "Keine Messdaten verfügbar. Messdaten-Logging ist deaktiviert; bitte in den Settings aktivieren, damit künftig Daten exportiert werden können."
            else:
                msg = "Im gewählten Zeitraum wurden keine Messdaten gefunden."
            return PlainTextResponse(msg, status_code=404)
        return PlainTextResponse(
            out.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=zec_measurements_export.csv"},
        )

    @app.get("/config")
    def get_config():
        response = JSONResponse({
            "configured": config_manager.redacted_config(configured=True),
            "effective": config_manager.redacted_config(configured=False),
            "status": config_manager.status(),
        })
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health")
    def health():
        cfg = config_manager.get()
        return build_health_payload(state.readiness_snapshot())

    @app.get("/ready")
    def ready():
        cfg = config_manager.get()
        payload = build_ready_payload(cfg, state.readiness_snapshot(cfg.get("ZENDURE_COMMAND_STATE_FRESH_SECONDS", 30)))
        runtime_status = config_manager.status()
        payload["settings_runtime"] = {
            "startup_mode": runtime_status.get("startup_mode"),
            "config_health": runtime_status.get("config_health"),
            "effective_source": runtime_status.get("effective_source"),
            "pending_restart": runtime_status.get("pending_restart"),
        }
        if not runtime_status.get("control_allowed"):
            payload["ready"] = False
            payload["status"] = "not_ready"
            failed = list(payload.get("failed_checks") or [])
            if "settings_runtime_control_gate" not in failed:
                failed.append("settings_runtime_control_gate")
            payload["failed_checks"] = failed
        return payload

    @app.get("/settings", response_class=HTMLResponse)
    def settings_page(request: Request):
        cfg = config_manager.get()
        if cfg.get("HEADLESS_MODE", False):
            return HTMLResponse(build_headless_page(cfg), status_code=403)
        token = csrf_token_for(request)
        snap = state.snapshot()
        status_payload = build_status_view_payload(cfg, snap)
        response = HTMLResponse(build_settings_page(
            cfg, csrf_token=token, system_payload=status_payload.get("system"),
            server_time=str(status_payload.get("server_time") or ""),
        ))
        response.set_cookie(
            csrf_cookie_name,
            token,
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="strict",
            path="/",
            max_age=3600,
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    def _config_artifact_error(exc: Exception):
        code = getattr(exc, "code", None) or str(exc)
        if isinstance(exc, PermissionError):
            status = 403
        elif isinstance(exc, KeyError):
            status = 410
        elif "CONFLICT" in code:
            status = 409
        elif isinstance(exc, (BundleError, ConfigStateError, ValueError)):
            status = 422
        else:
            status = 500
        response = JSONResponse({"error": code}, status_code=status)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/config-states")
    def config_states_list(request: Request):
        if config_manager.get().get("HEADLESS_MODE", False):
            return JSONResponse({"status": "disabled", "reason": "headless"}, status_code=403)
        try:
            response = JSONResponse(config_state_store.list())
            response.headers["Cache-Control"] = "no-store"
            return response
        except Exception as exc:
            return _config_artifact_error(exc)

    @app.post("/config-states/create")
    async def config_states_create(request: Request):
        try:
            verify_admin_request(request)
            payload = await request.json()
            item = config_state_store.create(
                config_manager,
                name=payload.get("name", ""), description=payload.get("description", ""),
                scope_mode=payload.get("scope_mode", "full_managed"),
                categories=payload.get("categories") or (), keys=payload.get("keys") or (),
            )
            response = JSONResponse({"status": "created", "item": item})
            response.headers["Cache-Control"] = "no-store"
            return response
        except Exception as exc:
            return _config_artifact_error(exc)

    @app.patch("/config-states/{state_id}")
    async def config_states_patch(state_id: str, request: Request):
        try:
            verify_admin_request(request)
            payload = await request.json()
            item = config_state_store.patch(
                state_id, expected_revision=payload.get("state_revision", ""),
                name=payload.get("name") if "name" in payload else None,
                description=payload.get("description") if "description" in payload else None,
            )
            response = JSONResponse({"status": "updated", "item": item})
            response.headers["Cache-Control"] = "no-store"
            return response
        except Exception as exc:
            return _config_artifact_error(exc)

    @app.delete("/config-states/{state_id}")
    async def config_states_delete(state_id: str, request: Request):
        try:
            verify_admin_request(request)
            payload = await request.json()
            response = JSONResponse(config_state_store.delete(state_id, expected_revision=payload.get("state_revision", "")))
            response.headers["Cache-Control"] = "no-store"
            return response
        except Exception as exc:
            return _config_artifact_error(exc)

    @app.post("/config-states/{state_id}/preview")
    async def config_states_preview(state_id: str, request: Request):
        try:
            session_token = verify_admin_request(request)
            payload = await request.json()
            result = config_artifacts.preview_state(
                state_id, state_revision=payload.get("state_revision", ""),
                base_revision=payload.get("base_revision", ""), session_token=session_token,
                state_snapshot=state.snapshot(), expert=bool(payload.get("expert")),
                secret_operations=payload.get("secrets") or {},
            )
            response = JSONResponse(result)
            response.headers["Cache-Control"] = "no-store"
            return response
        except Exception as exc:
            return _config_artifact_error(exc)

    @app.post("/config-states/{state_id}/export")
    async def config_states_export(state_id: str, request: Request):
        try:
            verify_admin_request(request)
            payload = await request.json()
            data = config_state_store.export_bytes(state_id, expected_revision=payload.get("state_revision"))
            response = Response(data, media_type="application/vnd.zec.config+json")
            response.headers["Content-Disposition"] = f'attachment; filename="zec-config-state-{state_id}.zec-config.json"'
            response.headers["Cache-Control"] = "no-store"
            return response
        except Exception as exc:
            return _config_artifact_error(exc)

    @app.post("/config-export")
    async def config_export(request: Request):
        try:
            verify_admin_request(request)
            payload = await request.json()
            include_secrets = bool(payload.get("include_secrets"))
            if include_secrets and (not bool(payload.get("expert")) or not bool(payload.get("confirm_secret_export"))):
                raise PermissionError("SECRET_EXPORT_CONFIRMATION_REQUIRED")
            data = build_bundle(
                config_manager, artifact_kind="export",
                scope_mode=payload.get("scope_mode", "full_managed"),
                categories=payload.get("categories") or (), keys=payload.get("keys") or (),
                name=payload.get("name", "ZEC Konfiguration"), description=payload.get("description", ""),
                include_secrets=include_secrets,
            )
            response = Response(data, media_type="application/vnd.zec.config+json")
            response.headers["Content-Disposition"] = 'attachment; filename="zec-config-export.zec-config.json"'
            response.headers["Cache-Control"] = "no-store"
            return response
        except Exception as exc:
            return _config_artifact_error(exc)

    @app.post("/config-profile-export")
    async def config_profile_export(request: Request):
        try:
            verify_admin_request(request)
            payload = await request.json()
            data = build_bundle(
                config_manager, artifact_kind="portable_profile", scope_mode="portable_profile",
                name=payload.get("name", "ZEC Regelprofil"), description=payload.get("description", ""),
                include_secrets=False,
            )
            response = Response(data, media_type="application/vnd.zec.config+json")
            response.headers["Content-Disposition"] = 'attachment; filename="zec-regelprofil.zec-config.json"'
            response.headers["Cache-Control"] = "no-store"
            return response
        except Exception as exc:
            return _config_artifact_error(exc)

    @app.post("/config-import/inspect")
    async def config_import_inspect(request: Request):
        try:
            session_token = verify_admin_request(request)
            content_length = int(request.headers.get("content-length") or 0)
            if content_length > BUNDLE_MAX_BYTES:
                raise BundleError("BUNDLE_TOO_LARGE")
            data = await request.body()
            if len(data) > BUNDLE_MAX_BYTES:
                raise BundleError("BUNDLE_TOO_LARGE")
            legacy = str(request.query_params.get("legacy") or "").lower() in ("1", "true", "yes")
            expert = str(request.query_params.get("expert") or "").lower() in ("1", "true", "yes")
            result = config_artifacts.inspect_legacy_raw(data, expert=expert, session_token=session_token) if legacy else config_artifacts.inspect_bundle(data, session_token=session_token)
            response = JSONResponse(result)
            response.headers["Cache-Control"] = "no-store"
            return response
        except Exception as exc:
            return _config_artifact_error(exc)

    @app.post("/config-import/{token}/preview")
    async def config_import_preview(token: str, request: Request):
        try:
            session_token = verify_admin_request(request)
            payload = await request.json()
            result = config_artifacts.preview_import(
                token, base_revision=payload.get("base_revision", ""), session_token=session_token,
                state_snapshot=state.snapshot(), expert=bool(payload.get("expert")),
                skip_unknown=bool(payload.get("skip_unknown")), secret_operations=payload.get("secrets") or {},
            )
            response = JSONResponse(result)
            response.headers["Cache-Control"] = "no-store"
            return response
        except Exception as exc:
            return _config_artifact_error(exc)

    @app.get("/settings/model")
    def settings_model(request: Request):
        cfg = config_manager.get()
        if cfg.get("HEADLESS_MODE", False):
            return JSONResponse({"status": "disabled", "reason": "headless"}, status_code=403)
        token = csrf_token_for(request)
        state_snapshot = state.snapshot()
        payload = build_settings_model(config_manager, state_snapshot, csrf_token=token)
        ready_payload = build_ready_payload(config_manager.get(), state.readiness_snapshot(config_manager.get().get("ZENDURE_COMMAND_STATE_FRESH_SECONDS", 30)))
        payload["ready_status"] = ready_payload
        payload["runtime"]["ready"] = ready_payload.get("ready")
        payload["storage_status"] = storage_inventory.snapshot()
        response = JSONResponse(payload)
        response.set_cookie(
            csrf_cookie_name,
            token,
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="strict",
            path="/",
            max_age=3600,
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.post("/settings/preview")
    async def settings_preview(request: Request):
        if config_manager.get().get("HEADLESS_MODE", False):
            return JSONResponse({"error": "HEADLESS_MODE"}, status_code=403)
        try:
            session_token = verify_admin_request(request)
            payload = await request.json()
            result = settings_service.preview(payload, session_token, state.snapshot())
            response = JSONResponse(result, status_code=200 if result.get("status") in ("ready", "no_changes") else 422)
            response.headers["Cache-Control"] = "no-store"
            return response
        except PermissionError as exc:
            return JSONResponse({"error": str(exc)}, status_code=403)
        except RuntimeError as exc:
            code = str(exc)
            return JSONResponse({"error": code}, status_code=409 if "CONFLICT" in code else 400)
        except (ValueError, json.JSONDecodeError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)

    @app.post("/settings/commit")
    async def settings_commit(request: Request):
        if config_manager.get().get("HEADLESS_MODE", False):
            return JSONResponse({"error": "HEADLESS_MODE"}, status_code=403)
        try:
            session_token = verify_admin_request(request)
            payload = await request.json()
            result = settings_service.commit(payload, session_token)
            if on_config_saved and result.get("live_applied_keys"):
                on_config_saved()
            audit = dict(result.get("audit") or {})
            if audit:
                event_journal.record_admin_action(
                    "ZEC_CONFIG_COMMIT",
                    str(audit.get("operation") or "settings_edit"),
                    values=audit,
                )
            response = JSONResponse(result)
            response.headers["Cache-Control"] = "no-store"
            return response
        except PermissionError as exc:
            return JSONResponse({"error": str(exc)}, status_code=403)
        except KeyError as exc:
            return JSONResponse({"error": str(exc)}, status_code=410)
        except RuntimeError as exc:
            code = str(exc)
            return JSONResponse({"error": code}, status_code=409 if "CONFLICT" in code else 500)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)

    @app.post("/settings/storage-probe")
    async def settings_storage_probe(request: Request):
        """Explicit write probe. GET/model/preview never call this action."""
        try:
            verify_admin_request(request)
            payload = await request.json()
            target = str(payload.get("path") or "").strip()
            if not target or not os.path.isabs(target):
                return JSONResponse({"error": "ABSOLUTE_PATH_REQUIRED"}, status_code=422)
            if not os.path.isdir(target):
                return JSONResponse({"error": "DIRECTORY_NOT_FOUND"}, status_code=422)
            probe = os.path.join(target, ".zec-settings-probe-" + secrets.token_hex(12) + ".tmp")
            cleanup_error = ""
            try:
                fd = os.open(probe, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                try:
                    os.write(fd, b"ZEC RC20 storage probe\n")
                    os.fsync(fd)
                finally:
                    os.close(fd)
            finally:
                try:
                    if os.path.exists(probe):
                        os.remove(probe)
                except OSError as exc:
                    cleanup_error = type(exc).__name__
            return {"status": "ok" if not cleanup_error else "cleanup_error", "path": target, "cleanup_error": cleanup_error or None}
        except PermissionError as exc:
            return JSONResponse({"error": str(exc)}, status_code=403)
        except OSError as exc:
            return JSONResponse({"error": type(exc).__name__}, status_code=500)

    # Legacy form endpoints remain registered as explicit no-write tombstones so
    # old bookmarks or scripts cannot bypass the RC20 preview/commit contract.
    @app.post("/settings/validate")
    async def validate_settings_preview_legacy(_request: Request):
        return JSONResponse({"error": "LEGACY_ENDPOINT_REMOVED", "use": "/settings/preview"}, status_code=410)

    @app.post("/save-config")
    async def save_config_web_legacy(_request: Request):
        return JSONResponse({"error": "LEGACY_ENDPOINT_REMOVED", "use": "/settings/preview and /settings/commit"}, status_code=410)

    @app.get("/graph", response_class=HTMLResponse)
    def graph_page():
        return html_or_headless(build_graph_page, config_manager.get(), state.snapshot())

    @app.get("/graph_old", response_class=HTMLResponse)
    def graph_old_page():
        return html_or_headless(build_graph_page_legacy, config_manager.get())

    @app.get("/logs/current.csv")
    def current_csv_log():
        # Kept for backward compatibility. The canonical RC7 path is the
        # Measurement export page with selectable time range.
        return RedirectResponse(url="/measurements", status_code=303)

    @app.get("/mqtt-diagnostics", response_class=HTMLResponse)
    def mqtt_diagnostics_page(request: Request):
        cfg = config_manager.get()
        return html_or_headless(
            build_mqtt_diagnostics_page,
            cfg,
            state.snapshot().get("mqtt_topic_diagnostics", []),
            cleared=request.query_params.get("cleared") == "1",
        )

    @app.get("/mqtt-diagnostics.csv")
    def mqtt_diagnostics_csv():
        if config_manager.get().get("HEADLESS_MODE", False):
            return HTMLResponse(build_headless_page(config_manager.get()))
        return PlainTextResponse(
            diagnostics_to_csv(state.snapshot().get("mqtt_topic_diagnostics", [])),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=mqtt-diagnostics.csv"},
        )

    @app.get("/mqtt-diagnostics/data")
    def mqtt_diagnostics_data():
        cfg = config_manager.get()
        if cfg.get("HEADLESS_MODE", False):
            return {"headless": True, "enabled": False, "rows": [], "count": 0}
        rows = state.snapshot().get("mqtt_topic_diagnostics", [])
        return {
            "headless": False,
            "enabled": bool(cfg.get("MQTT_TOPIC_DIAGNOSTIC_ENABLED", False)),
            "filter": str(cfg.get("MQTT_TOPIC_DIAGNOSTIC_FILTER", "Zendure/#")),
            "view_mode": str(cfg.get("MQTT_TOPIC_DIAGNOSTIC_VIEW_MODE", "filtered")),
            "count": len(rows),
            "rows": rows[-200:],
        }

    @app.post("/mqtt-diagnostics/clear")
    def mqtt_diagnostics_clear():
        cfg = config_manager.get()
        if cfg.get("HEADLESS_MODE", False):
            return HTMLResponse(build_headless_page(cfg), status_code=403)
        state.clear_mqtt_diagnostics()
        return RedirectResponse(url="/mqtt-diagnostics?cleared=1", status_code=303)

    @app.get("/favicon.svg")
    def favicon_svg():
        return PlainTextResponse(FAVICON_SVG, media_type="image/svg+xml")

    @app.get("/manual.pdf")
    def manual_pdf():
        path = find_manual_pdf()
        if not path:
            return PlainTextResponse("Handbuch-PDF wurde nicht gefunden. Bitte docs/Zendure_Energy_Controller_Handbuch.pdf mitinstallieren.", status_code=404)
        return FileResponse(path, media_type="application/pdf", filename=os.path.basename(path))

    @app.post("/restart-service")
    async def restart_service(request: Request):
        cfg = config_manager.get()
        if cfg.get("HEADLESS_MODE", False):
            return JSONResponse({"error": "HEADLESS_MODE"}, status_code=403)
        try:
            verify_admin_request(request)
            payload = await request.json()
        except PermissionError as exc:
            return JSONResponse({"error": str(exc)}, status_code=403)
        if str(payload.get("confirmation") or "") != "RESTART_SERVICE":
            return JSONResponse({"error": "EXPLICIT_CONFIRMATION_REQUIRED"}, status_code=422)
        if not service_restart_enabled(cfg):
            return JSONResponse({"error": "RESTART_DISABLED"}, status_code=403)
        if not os.path.isfile(RESTART_HELPER_PATH) or not os.access(RESTART_HELPER_PATH, os.X_OK):
            return JSONResponse({"error": "RESTART_HELPER_UNAVAILABLE"}, status_code=503)
        if config_manager.status().get("configured_file_valid") is not True:
            return JSONResponse({"error": "CONFIGURED_STARTUP_CANDIDATE_INVALID"}, status_code=409)
        now = time.monotonic()
        with restart_lock:
            if restart_state["in_flight"]:
                return JSONResponse({"error": "RESTART_ALREADY_IN_FLIGHT"}, status_code=409)
            if now - float(restart_state["last_attempt_monotonic"] or 0) < 60.0:
                return JSONResponse({"error": "RESTART_COOLDOWN"}, status_code=429)
            restart_state["in_flight"] = True
            restart_state["last_attempt_monotonic"] = now
        try:
            redirect_url = status_url_after_restart(request, config_manager.get_configured())
            state.add_event("MANUAL_WEB_SERVICE_RESTART")
            event_journal.record_admin_action(
                "MANUAL_WEB_SERVICE_RESTART",
                "Manueller Dienstneustart über die geschützte Settings-Aktion bestätigt.",
                {"expected_version": APP_VERSION, "expected_build_id": APP_BUILD_ID, "redirect_url": redirect_url},
            )
            delayed_service_restart(cfg, delay_seconds=1.2)
            return {
                "status": "restart_scheduled",
                "redirect_url": redirect_url,
                "ready_url": "/ready",
                "expected_version": APP_VERSION,
                "expected_build_id": APP_BUILD_ID,
                "success_condition": "ready=true, version=expected_version and build_id=expected_build_id",
            }
        except Exception as exc:
            with restart_lock:
                restart_state["in_flight"] = False
            return JSONResponse({"error": type(exc).__name__, "message": str(exc)}, status_code=500)

    def _pointer_repair_binding(status: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        store = status.get("last_good_store") or {}
        selected = store.get("selected_slot")
        slots = store.get("slots") or {}
        slot_status = slots.get(selected) if selected in ("A", "B") else None
        if not isinstance(slot_status, dict):
            return None
        manifest_path = config_manager.last_good_store.manifest_path_for(str(selected))
        try:
            with open(manifest_path, "rb") as handle:
                manifest_bytes = handle.read()
            manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
        except OSError:
            return None
        return {
            "store_revision": status.get("last_good_store_revision"),
            "target_slot": selected,
            "generation_id": int(slot_status.get("generation_id") or 0),
            "typed_revision": str(slot_status.get("typed_revision") or ""),
            "config_hash": str(slot_status.get("config_hash") or ""),
            "manifest_hash": manifest_hash,
        }

    @app.post("/admin/last-good-pointer-repair/preview")
    async def last_good_pointer_repair_preview(request: Request):
        try:
            session_token = verify_admin_request(request)
        except PermissionError as exc:
            return JSONResponse({"error": str(exc)}, status_code=403)
        status = config_manager.status()
        if not status.get("last_good_store_repair_required"):
            return JSONResponse({"error": "REPAIR_NOT_ELIGIBLE"}, status_code=409)
        binding = _pointer_repair_binding(status)
        if binding is None or binding.get("target_slot") not in ("A", "B"):
            return JSONResponse({"error": "REPAIR_TARGET_NOT_VERIFIABLE"}, status_code=409)
        token = secrets.token_urlsafe(24)
        record = {
            "session": session_token,
            **binding,
            "expires": time.monotonic() + 300.0,
        }
        with repair_lock:
            repair_previews.clear()
            repair_previews[token] = record
        return {
            "status": "ready",
            "action_token": token,
            **binding,
            "confirmation_phrase": "REPAIR_POINTER",
            "effects": ["Current-Pointer atomar auf den verifizierten Slot setzen"],
            "non_effects": ["keine Slotdatei", "keine Primärconfig", "keine Runtimeänderung", "keine Gerätekommandos"],
        }

    @app.post("/admin/last-good-pointer-repair/commit")
    async def last_good_pointer_repair_commit(request: Request):
        try:
            session_token = verify_admin_request(request)
            payload = await request.json()
        except PermissionError as exc:
            return JSONResponse({"error": str(exc)}, status_code=403)
        if str(payload.get("confirmation") or "") != "REPAIR_POINTER":
            return JSONResponse({"error": "EXPLICIT_CONFIRMATION_REQUIRED"}, status_code=422)
        token = str(payload.get("action_token") or "")
        now = time.monotonic()
        with repair_lock:
            record = repair_previews.pop(token, None)
            if repair_state["in_flight"]:
                return JSONResponse({"error": "REPAIR_ALREADY_IN_FLIGHT"}, status_code=409)
            if now - float(repair_state["last_attempt_monotonic"] or 0) < 60.0:
                return JSONResponse({"error": "REPAIR_COOLDOWN"}, status_code=429)
            if record and record.get("expires", 0) > now and record.get("session") == session_token:
                repair_state["in_flight"] = True
                repair_state["last_attempt_monotonic"] = now
        if not record or record.get("expires", 0) <= now:
            return JSONResponse({"error": "ACTION_TOKEN_EXPIRED"}, status_code=410)
        if record.get("session") != session_token:
            return JSONResponse({"error": "ACTION_SESSION_MISMATCH"}, status_code=403)
        try:
            current_status = config_manager.status()
            current_binding = _pointer_repair_binding(current_status)
            expected_binding = {key: record.get(key) for key in (
                "store_revision", "target_slot", "generation_id", "typed_revision", "config_hash", "manifest_hash"
            )}
            if current_binding != expected_binding:
                return JSONResponse({"error": "REPAIR_BINDING_CHANGED"}, status_code=409)
            result = config_manager.last_good_store.repair_pointer(
                str(record.get("store_revision") or ""),
                str(record.get("target_slot") or ""),
            )
            event_journal.record_admin_action(
                "LAST_GOOD_POINTER_REPAIR",
                "Last-Good-Current-Pointer nach vollständiger Tokenbindung atomar repariert.",
                expected_binding,
            )
            return result
        except RuntimeError as exc:
            return JSONResponse({"error": str(exc)}, status_code=409)
        finally:
            with repair_lock:
                repair_state["in_flight"] = False

    @app.get("/zendure-properties")
    def zendure_properties():
        cfg = config_manager.get()
        if cfg.get("HEADLESS_MODE", False):
            return HTMLResponse(build_headless_page(cfg))
        if not cfg.get("ZENDURE_LOCAL_API_ENABLED", False):
            return {
                "enabled": False,
                "message": "Zendure lokale API Diagnose ist deaktiviert. Aktiviere sie in den Settings und trage die Zendure-IP ein.",
            }
        ip = str(cfg.get("ZENDURE_LOCAL_IP", "")).strip()
        if not ip:
            return {"enabled": True, "error": "ZENDURE_LOCAL_IP ist leer."}
        timeout = int(cfg.get("ZENDURE_LOCAL_API_TIMEOUT_SECONDS", 5))
        url = f"http://{ip}/properties/report"
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            try:
                return response.json()
            except Exception:
                return {"url": url, "text": response.text}
        except Exception as exc:
            return {"url": url, "error": str(exc)}

    return app




def build_nav_bar(cfg: Dict[str, Any]) -> str:
    port = int(cfg.get("REPLAY_WEB_PORT", 8090) or 8090)
    replay_ok = replay_service_available(cfg)
    dot_class = "ok" if replay_ok else "warn"
    title = "Analyse-/Replay-Service öffnen" if replay_ok else "Analyse-/Replay-Service öffnen (Erreichbarkeit nicht bestätigt)"
    analysis = f'<a href="#" class="analysis-service-link" data-replay-port="{port}" title="{html.escape(title)}">Analyse-Service <span class="status-dot {dot_class}"></span></a>'
    expert_menu = (
        '<span class="expert-menu">'
        '<button type="button" class="expert-menu-button" onclick="this.parentElement.classList.toggle(\'open\')">Experte ▾</button>'
        '<span class="expert-menu-panel">'
        '<a href="/status_old">Alte Statusseite</a>'
        '<a href="/graph_old">Alter Graph</a>'
        '<a href="/status#modern-diagnostics">Moderne Diagnose</a>'
        '</span>'
        '</span>'
    )
    links = [
        '<a href="/">Status</a>',
        '<a href="/graph">Graph</a>',
        '<a href="/settings">Settings</a>',
        analysis,
        '<a href="/mqtt-diagnostics">MQTT Diagnose</a>',
        '<a href="/measurements">Messdaten-CSV</a>',
        '<a href="/manual.pdf">Handbuch</a>',
        expert_menu,
    ]
    links = [x for x in links if x]
    return '<div class="nav">' + ''.join(links) + '</div>'

def build_base_header(title: str, refresh: bool = False, cfg: Optional[Dict[str, Any]] = None) -> str:
    refresh_tag = ""
    dark = bool((cfg or {}).get("UI_DARK_MODE", False))
    theme_css = """
            body { background:#0f172a; color:#e5e7eb; }
            .section { background:#111827; box-shadow:0 2px 10px rgba(0,0,0,0.55); }
            .card { background:#1f2937; border-color:#374151; }
            .label, .small, .technical { color:#cbd5e1; }
            .path-dir { color:#cbd5e1; }
            th { background:#263244; color:#e5e7eb; }
            th, td { border-color:#475569; }
            input[type="number"], input[type="text"], input[type="password"], select { background:var(--zec-ring-inner-bg); color:#e5e7eb; border:1px solid #64748b; }
            .section-heading-link { color:#e5e7eb; }
            .validation-modal-content { background:#111827; color:#e5e7eb; }
            .save { background:#243244; color:#e5e7eb; border-color:#475569; }
            .save:hover { background:#334155; }
            .card.error-card { background:#3b1d1d; border-color:#f87171; }
            .card.error-card input, .card.error-card select { background:#1f1111; border-color:#f87171; color:#fee2e2; }
            .card.warning-card { background:#3a2a10; border-color:#fbbf24; }
            .card.warning-card input, .card.warning-card select { background:#201707; border-color:#fbbf24; color:#fde68a; }
            .warning-box, .section-warning { background:#3a2a10; color:#fde68a; border-color:#fbbf24; }
            .info-box { background:#0f2a3f; color:#dbeafe; border-color:#38bdf8; }
            .error-box, .section-error { background:#3b1d1d; color:#fecaca; border-color:#f87171; }
            .subgroup-card { background:#172033; border-color:#334155; color:#e5e7eb; }
            .section-intro-card { background:#122033; border-color:#334155; color:#e5e7eb; }
            .subgroup-card h3, .section-intro-card h3 { color:#f8fafc; }
            .subgroup-card .small { color:#cbd5e1; }
            .version-pill { background:#334155; }
            a { color:#7dd3fc; }
    """ if dark else ""
    return f"""
    <html>
    <head>
        <title>{html.escape(title)}</title>
        {refresh_tag}
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="icon" type="image/svg+xml" href="/favicon.svg">
        <style>
            body {{ font-family: Arial, sans-serif; background:#f0f2f5; margin:30px; color:#222; }}
            .container {{ max-width: 1260px; margin:0 auto; }}
            .section {{ background:white; border-radius:12px; padding:22px; margin-bottom:22px; box-shadow:0 2px 8px rgba(0,0,0,0.08); }}
            .grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap:15px; }}
            .card {{ background:#fafafa; border:1px solid #e0e0e0; border-radius:10px; padding:14px; }}
            .label {{ color:#666; font-size:13px; margin-bottom:6px; font-weight:bold; }}
            .value {{ font-size:24px; font-weight:bold; overflow-wrap:anywhere; }}
            .small {{ font-size:13px; color:#666; line-height:1.45; }}
            .path-fragment {{ font-family:monospace; overflow-wrap:anywhere; word-break:break-word; }}
            .path-dir {{ font-size:.92em; color:#475569; }}
            .technical {{ color:#777; font-size:12px; margin-top:4px; }}
            .badge {{ display:inline-block; padding:5px 10px; border-radius:8px; color:white; font-weight:bold; max-width:100%; white-space:normal; overflow-wrap:anywhere; line-height:1.2; box-sizing:border-box; }}
            .green {{ color:#4CAF50; }} .red {{ color:#f44336; }} .blue {{ color:#2196F3; }} .yellow {{ color:#f0ad00; }} .orange {{ color:#ff9800; }} .purple {{ color:#9c27b0; }} .gray {{ color:#777; }}
            a {{ color:#1565c0; text-decoration:none; }} a:hover {{ text-decoration:underline; }}
            .section-heading-link {{ color:#222; text-decoration:none; }} .section-heading-link:hover {{ color:#1565c0; text-decoration:underline; }}
            .headless-box {{ max-width:760px; margin:80px auto; }}
            table {{ border-collapse:collapse; width:100%; font-size:12px; }}
            th {{ background:#f0f0f0; }} th, td {{ border:1px solid #d0d0d0; padding:6px; text-align:center; }}
            input[type="number"], input[type="text"], input[type="password"], select {{ width:100%; padding:7px; box-sizing:border-box; }}
            input[type="checkbox"] {{ transform:scale(1.2); }}
            details.help {{ margin-top:8px; }} details.help summary {{ cursor:pointer; color:#1565c0; font-size:12px; }}
            details.help div {{ margin-top:6px; }}
            .section-tools {{ margin-top:-8px; margin-bottom:14px; }}
            .section-tools a {{ font-size:13px; }}
            .legend-list li {{ margin-bottom:10px; line-height:1.45; }}
            .save {{ margin-top:20px; padding:12px; width:100%; font-size:16px; border:1px solid #94a3b8; border-radius:6px; background:#eef2f7; color:#111827; cursor:pointer; }}
            .save:hover {{ background:#e2e8f0; }}
            .save-small {{ margin-top:12px; padding:8px 12px; font-size:13px; }}
            .error-box {{ background:#ffebee; border:2px solid #f44336; color:#b71c1c; padding:14px; border-radius:10px; margin:14px 0; line-height:1.45; }}
            .warning-box {{ background:#fff8e1; border:2px solid #f0ad00; color:#7a4b00; padding:14px; border-radius:10px; margin:14px 0; line-height:1.45; }}
            .info-box {{ background:#e3f2fd; border:2px solid #2196F3; color:#0d47a1; padding:14px; border-radius:10px; margin:14px 0; line-height:1.45; }}
            .section-error {{ background:#ffebee; border-left:6px solid #f44336; color:#b71c1c; padding:12px 14px; border-radius:8px; margin:12px 0 16px 0; line-height:1.45; }}
            .section-warning {{ background:#fff8e1; border-left:6px solid #f0ad00; color:#7a4b00; padding:12px 14px; border-radius:8px; margin:12px 0 16px 0; line-height:1.45; }}
            .subgroup-card {{ grid-column:1 / -1; margin-top:22px; }}
            .section-intro-card {{ grid-column:1 / -1; margin:0 0 4px 0; }}
            .subgroup-card h3, .section-intro-card h3 {{ margin:0 0 6px 0; }}
            .card.error-card {{ border:2px solid #f44336; background:#fff5f5; }}
            .card.error-card input, .card.error-card select {{ border:2px solid #f44336; background:#fff8f8; }}
            .card.warning-card {{ border:2px solid #f0ad00; background:#fffaf0; }}
            .card.warning-card input, .card.warning-card select {{ border:2px solid #f0ad00; background:#fffdf2; }}
            .validation-modal {{ position:fixed; inset:0; background:rgba(0,0,0,0.45); z-index:9999; display:flex; align-items:center; justify-content:center; padding:20px; }}
            .validation-modal-content {{ max-width:760px; width:100%; background:white; border-radius:12px; border-top:8px solid #f44336; box-shadow:0 8px 30px rgba(0,0,0,0.25); padding:24px; }}
            .validation-modal-content.warning {{ border-top-color:#f0ad00; }}
            .validation-modal-content h2 {{ color:#b71c1c; margin-top:0; }}
            .validation-modal-content.warning h2 {{ color:#7a4b00; }}
            .validation-modal-content button {{ margin-top:12px; padding:10px 16px; font-size:15px; }}
            .confirm-warning-button {{ background:#7a4b00; color:white; border:0; border-radius:6px; cursor:pointer; }}
            .nav {{ margin-bottom:22px; display:flex; flex-wrap:nowrap; gap:12px; align-items:center; overflow-x:auto; white-space:nowrap; }} .nav a {{ display:inline-block; padding:8px 10px; border-radius:10px; background:rgba(21,101,192,.08); }} .nav a:hover {{ text-decoration:none; background:rgba(21,101,192,.16); }} .status-dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; margin-left:5px; vertical-align:middle; }} .status-dot.ok {{ background:#22c55e; box-shadow:0 0 0 3px rgba(34,197,94,.18); }} .status-dot.warn {{ background:#f59e0b; box-shadow:0 0 0 3px rgba(245,158,11,.18); }} .version-pill {{ font-size:12px; font-weight:bold; color:white; background:#777; padding:2px 8px; border-radius:10px; }} .section-title-row {{ display:flex; align-items:center; justify-content:space-between; gap:16px; }} .section-title-row h1, .section-title-row h2 {{ margin-top:0; }}
            .dashboard-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:14px; }} .metric-card {{ background:#111827; border:1px solid #263244; border-radius:14px; padding:16px; }} .metric-title {{ color:#94a3b8; font-size:13px; font-weight:bold; margin-bottom:8px; }} .metric-value {{ font-size:26px; font-weight:800; }} .metric-sub {{ color:#cbd5e1; font-size:13px; line-height:1.45; margin-top:8px; }} .toolbar {{ display:flex; gap:12px; flex-wrap:wrap; align-items:center; margin:12px 0; }} .toolbar select,.toolbar button,.toolbar a.button {{ width:auto; padding:8px 10px; border-radius:9px; border:1px solid #475569; background:#111827; color:#e5e7eb; }} .kpi-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; }} .kpi {{ border:1px solid #263244; background:#0f172a; border-radius:12px; padding:12px; }} .kpi .num {{ font-size:20px; font-weight:800; }} .event-pill {{ display:inline-block; margin:3px; padding:4px 8px; border-radius:999px; background:#1f2937; border:1px solid #334155; font-size:12px; }}
            .subnav {{ margin-top:14px; line-height:2.2; display:flex; flex-wrap:wrap; gap:8px 24px; align-items:center; }} .subnav a {{ display:inline-block; }}
            canvas {{ width:100%; max-height:520px; }}
            .mini-chart-frame {{ height:230px; min-height:230px; max-height:230px; overflow:hidden; }}
            #miniChart {{ height:210px !important; max-height:210px !important; }}

            .modern-page {{ color:#e8edf7; }}
            .modern-hero {{ background:linear-gradient(135deg,#09111f 0%,#0d1728 56%,#0b2b33 100%); border:1px solid rgba(148,163,184,.18); border-radius:24px; padding:24px; margin-bottom:22px; box-shadow:0 16px 44px rgba(0,0,0,.35); }}
            .modern-title-row {{ display:flex; justify-content:space-between; align-items:flex-start; gap:18px; flex-wrap:wrap; }}
            .modern-title {{ font-size:30px; font-weight:900; margin:0; letter-spacing:-.03em; }}
            .modern-subtitle {{ color:#9fb3c8; margin-top:6px; font-size:14px; line-height:1.45; }}
            .modern-pill {{ display:inline-flex; align-items:center; gap:6px; border:1px solid rgba(148,163,184,.22); background:rgba(15,23,42,.7); border-radius:999px; padding:7px 11px; font-size:13px; color:#cbd5e1; }}
            .modern-pill.ok {{ border-color:rgba(34,197,94,.35); color:#86efac; }} .modern-pill.warn {{ border-color:rgba(245,158,11,.45); color:#fde68a; }} .modern-pill.bad {{ border-color:rgba(248,113,113,.5); color:#fecaca; }}
            .modern-card-grid {{ display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:14px; margin-top:20px; }}
            .modern-card-grid.three {{ grid-template-columns:repeat(3,minmax(0,1fr)); }}
            .modern-card-grid.four {{ grid-template-columns:repeat(4,minmax(0,1fr)); }}
            .modern-card {{ background:rgba(15,23,42,.86); border:1px solid rgba(148,163,184,.18); border-radius:20px; padding:18px; box-shadow:inset 0 1px 0 rgba(255,255,255,.03); min-height:110px; }}
            .modern-card h3 {{ margin:0 0 10px 0; color:#e2e8f0; font-size:14px; letter-spacing:.01em; }}
            .modern-card .big {{ font-size:30px; line-height:1.05; font-weight:900; letter-spacing:-.03em; overflow-wrap:anywhere; }}
            .modern-card .sub {{ color:#9fb3c8; font-size:13px; line-height:1.45; margin-top:10px; }}
            .modern-section {{ background:var(--zec-ring-inner-bg); border:1px solid rgba(148,163,184,.14); border-radius:24px; padding:22px; margin-bottom:22px; box-shadow:0 12px 36px rgba(0,0,0,.32); }}
            .modern-section-header {{ display:flex; align-items:flex-start; justify-content:space-between; gap:16px; margin-bottom:16px; flex-wrap:wrap; }}
            .modern-section h2 {{ margin:0; font-size:22px; letter-spacing:-.02em; }}
            .modern-flow {{ display:grid; grid-template-columns:1fr auto 1fr; gap:18px; align-items:center; }}
            .flow-list {{ display:flex; flex-direction:column; gap:12px; }}
            .flow-row {{ display:flex; align-items:center; justify-content:space-between; gap:12px; border:1px solid rgba(148,163,184,.12); background:rgba(2,6,23,.34); border-radius:14px; padding:11px 12px; }}
            .flow-label {{ color:#cbd5e1; font-size:13px; }} .flow-value {{ font-weight:900; }}
            .flow-center {{ width:112px; height:112px; border-radius:999px; display:flex; flex-direction:column; align-items:center; justify-content:center; background:radial-gradient(circle at 50% 50%, rgba(45,212,191,.22), rgba(15,23,42,.96) 62%); border:1px solid rgba(45,212,191,.35); text-align:center; }}
            .flow-center b {{ font-size:24px; }}
            .soc-ring {{ width:150px; height:150px; border-radius:999px; display:flex; align-items:center; justify-content:center; margin:2px auto 14px; background:conic-gradient(#22c55e var(--soc,0%), rgba(148,163,184,.16) 0); position:relative; }}
            .soc-ring:after {{ content:""; position:absolute; inset:13px; border-radius:999px; background:var(--zec-ring-inner-bg); border:1px solid rgba(148,163,184,.12); }}
            .soc-ring span {{ position:relative; z-index:1; font-size:34px; font-weight:900; }}
            .modern-table {{ width:100%; border-collapse:collapse; font-size:13px; }} .modern-table th,.modern-table td {{ border:0; border-bottom:1px solid rgba(148,163,184,.14); text-align:left; padding:9px 6px; }} .modern-table th {{ background:transparent; color:#94a3b8; font-weight:700; }}
            .modern-warning {{ border:1px solid rgba(245,158,11,.42); background:rgba(245,158,11,.09); color:#fde68a; border-radius:16px; padding:13px 14px; margin-top:14px; }}
            .legacy-note {{ margin-top:14px; color:#94a3b8; font-size:13px; }} .legacy-note a {{ color:#7dd3fc; }}
            .expert-menu {{ position:relative; display:inline-flex; }} .expert-menu-button {{ border:0; border-radius:10px; padding:8px 10px; background:rgba(21,101,192,.08); color:#7dd3fc; cursor:pointer; font:inherit; }} .expert-menu-panel {{ display:none; position:absolute; right:0; top:calc(100% + 8px); min-width:180px; background:var(--zec-ring-inner-bg); border:1px solid #334155; border-radius:14px; padding:8px; z-index:50; box-shadow:0 12px 30px rgba(0,0,0,.4); }} .expert-menu.open .expert-menu-panel {{ display:block; }} .expert-menu-panel a {{ display:block; background:transparent; padding:9px 10px; }}
            .modern-toolbar {{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; justify-content:space-between; margin:10px 0 18px; }}
            .modern-toolbar-left {{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; }}
            .modern-toolbar select,.modern-toolbar button,.modern-toolbar a.button {{ width:auto; padding:9px 11px; border-radius:12px; border:1px solid rgba(148,163,184,.28); background:#0f172a; color:#e5e7eb; }}
            .chart-card {{ background:rgba(15,23,42,.86); border:1px solid rgba(148,163,184,.16); border-radius:22px; padding:18px; }}
            /* RC10 Modern UI pixel pass: mock-up first, independent from legacy theme */
            .zec-modern-body {{ background:#050b14 !important; color:#eaf2ff !important; margin:0 !important; font-family:Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important; }}
            .zec-modern-body .container {{ max-width:1760px !important; width:calc(100% - 44px); margin:0 auto !important; padding:0 0 28px 0; }}
            .zec-modern-body a {{ color:#6ee7f9; }}
            .zec-topbar {{ height:64px; display:flex; overflow:visible; align-items:center; gap:22px; border-bottom:1px solid rgba(148,163,184,.14); background:linear-gradient(180deg,rgba(5,11,20,.98),rgba(5,11,20,.88)); position:sticky; top:0; z-index:20; backdrop-filter:blur(14px); margin:0 -22px 22px; padding:0 24px; }}
            .zec-brand {{ display:flex; align-items:center; gap:14px; min-width:310px; }}
            .zec-logo {{ color:#f8fafc; font-weight:950; font-size:31px; letter-spacing:-.06em; line-height:1; display:inline-flex; align-items:center; }}
            .zec-logo .logo-d {{ color:#26e0c2; margin:0 -1px; text-shadow:0 0 18px rgba(38,224,194,.35); }}
            .zec-brand-sub {{ color:#c8d3e1; font-size:15px; border-left:1px solid rgba(148,163,184,.28); padding-left:14px; white-space:nowrap; }}
            .zec-nav-modern {{ display:flex; gap:6px; align-items:center; flex:1; overflow:visible; scrollbar-width:none; }}
            .zec-nav-modern a,.zec-nav-modern button {{ color:#dbe8f8; background:transparent; border:0; border-radius:12px; padding:9px 12px; font-size:14px; font-weight:750; text-decoration:none; display:inline-flex; align-items:center; gap:7px; white-space:nowrap; cursor:pointer; }}
            .zec-nav-modern a:hover,.zec-nav-modern button:hover {{ background:rgba(148,163,184,.10); text-decoration:none; }}
            .zec-nav-modern .active {{ color:#2dd4bf; background:rgba(45,212,191,.08); box-shadow:inset 0 -2px 0 #2dd4bf; }}
            .zec-top-actions {{ display:flex; align-items:center; gap:12px; white-space:nowrap; }}
            .zec-system-pill {{ border:1px solid rgba(34,197,94,.38); color:#86efac; background:rgba(22,101,52,.15); border-radius:8px; padding:7px 12px; font-weight:800; font-size:13px; }}
            .zec-clock {{ color:#dbeafe; font-weight:800; font-size:15px; }}
            .zec-dropdown {{ position:relative; z-index:5000; }} .zec-dropdown-panel {{ display:none; position:fixed; top:58px; right:22px; min-width:220px; padding:8px; border-radius:14px; background:#081321; border:1px solid rgba(148,163,184,.22); box-shadow:0 18px 44px rgba(0,0,0,.45); z-index:99999; }} .zec-dropdown.open .zec-dropdown-panel {{ display:block; }} .zec-dropdown-panel a {{ display:block; padding:9px 10px; color:#dbeafe; }}
            .zec-shell {{ max-width:1680px; margin:0 auto; }}
            .zec-page-title {{ display:flex; align-items:flex-end; justify-content:space-between; gap:18px; margin:12px 0 20px; }}
            .zec-page-title h1 {{ margin:0; font-size:30px; letter-spacing:-.035em; color:#f8fafc; }}
            .zec-page-note {{ color:#9fb2c8; font-size:13px; margin-top:6px; }}
            .zec-panel {{ background:linear-gradient(180deg,rgba(13,24,38,.96),rgba(9,17,30,.96)); border:1px solid rgba(148,163,184,.16); border-radius:16px; box-shadow:0 18px 45px rgba(0,0,0,.36); padding:18px; margin-bottom:16px; }}
            .zec-panel-lg {{ padding:22px; border-radius:18px; }}
            .zec-panel-header {{ display:flex; justify-content:space-between; align-items:flex-start; gap:18px; margin-bottom:16px; }}
            .zec-panel h2 {{ margin:0; color:#f8fafc; font-size:20px; letter-spacing:-.02em; }}
            .zec-panel-desc {{ color:#94a9bd; font-size:13px; margin-top:5px; }}
            .zec-card-row {{ display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:14px; }}
            .zec-card {{ background:rgba(11,20,33,.78); border:1px solid rgba(148,163,184,.18); border-radius:16px; padding:18px; min-height:116px; box-shadow:inset 0 1px 0 rgba(255,255,255,.035); }}
            .zec-card-label {{ color:#c7d5e7; font-size:13px; font-weight:850; margin-bottom:10px; display:flex; gap:10px; align-items:center; letter-spacing:-.01em; }}
            .zec-icon {{ width:18px; height:18px; flex:0 0 auto; stroke:currentColor; stroke-width:2; stroke-linecap:round; stroke-linejoin:round; fill:none; vertical-align:-3px; }}
            .zec-card-value {{ font-size:30px; line-height:1.02; font-weight:950; letter-spacing:-.04em; color:#f8fafc; overflow-wrap:anywhere; }}
            .zec-card-value.big2 {{ font-size:36px; }}
            .zec-card-sub {{ color:#9fb2c8; font-size:13px; line-height:1.45; margin-top:11px; }}
            .zec-accent-green {{ color:#25e26f !important; }} .zec-accent-blue {{ color:#38bdf8 !important; }} .zec-accent-yellow {{ color:#facc15 !important; }} .zec-accent-orange {{ color:#fb923c !important; }} .zec-accent-red {{ color:#fb7185 !important; }} .zec-muted {{ color:#94a3b8 !important; }}
            .zec-status-badge {{ display:inline-flex; align-items:center; gap:7px; border-radius:999px; padding:6px 10px; font-size:12px; font-weight:850; border:1px solid rgba(148,163,184,.22); background:rgba(15,23,42,.55); color:#dbeafe; }}
            .zec-status-badge.ok {{ color:#86efac; border-color:rgba(34,197,94,.35); }} .zec-status-badge.warn {{ color:#fde68a; border-color:rgba(245,158,11,.45); }} .zec-status-badge.bad {{ color:#fecaca; border-color:rgba(248,113,113,.5); }}
            .zec-alert-strip {{ border:1px solid rgba(245,158,11,.44); background:linear-gradient(90deg,rgba(245,158,11,.14),rgba(45,212,191,.07)); color:#fde68a; border-radius:13px; padding:12px 14px; margin-top:14px; font-size:13px; font-weight:700; }}
            .zec-flow-grid {{ display:grid; grid-template-columns:minmax(260px,1fr) 170px minmax(260px,1fr); gap:22px; align-items:center; }}
            .zec-flow-list {{ display:flex; flex-direction:column; gap:10px; }}
            .zec-flow-line {{ display:flex; justify-content:space-between; align-items:center; gap:16px; border:1px solid rgba(148,163,184,.14); background:rgba(2,6,23,.32); border-radius:12px; padding:11px 13px; }}
            .zec-flow-line .name {{ color:#cbd5e1; font-size:13px; }} .zec-flow-line .val {{ color:#f8fafc; font-size:15px; font-weight:900; }}
            .zec-flow-orb {{ width:142px; height:142px; border-radius:50%; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; background:radial-gradient(circle at 50% 45%,rgba(45,212,191,.28),rgba(8,18,31,.96) 66%); border:1px solid rgba(45,212,191,.4); box-shadow:0 0 34px rgba(45,212,191,.12); }}
            .zec-flow-orb b {{ font-size:24px; line-height:1.02; color:#f8fafc; }} .zec-flow-orb span {{ color:#9fb2c8; font-size:12px; margin-top:5px; }}
            .zec-two-col {{ display:grid; grid-template-columns:1.2fr .8fr; gap:16px; align-items:stretch; }}
            .zec-soc-card canvas {{ max-height:340px; }}
            .zec-diagnostics-slim {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; }}
            .zec-legacy-tile {{ background:rgba(15,23,42,.52); border:1px solid rgba(148,163,184,.14); border-radius:14px; padding:14px; }}
            .zec-legacy-tile b {{ display:block; font-size:22px; color:#f8fafc; margin:4px 0 8px; }}
            .zec-graph-toolbar {{ display:flex; justify-content:space-between; align-items:center; gap:14px; flex-wrap:wrap; margin-bottom:16px; }}
            .zec-control-group {{ display:flex; gap:10px; align-items:center; flex-wrap:wrap; }}
            .zec-control {{ display:inline-flex; gap:8px; align-items:center; border:1px solid rgba(148,163,184,.22); background:rgba(15,23,42,.72); border-radius:12px; padding:9px 11px; color:#dbeafe; font-size:13px; }}
            .zec-control select,.zec-control button,.zec-control a {{ background:transparent; border:0; color:#f8fafc; font-weight:800; width:auto; padding:0; }}
            .zec-control select option {{ background:var(--zec-ring-inner-bg); color:#f8fafc; }}
            .zec-btn {{ display:inline-flex; align-items:center; gap:7px; padding:10px 14px; border:1px solid rgba(148,163,184,.24); border-radius:12px; background:rgba(15,23,42,.62); color:#e5f3ff !important; font-weight:800; text-decoration:none !important; cursor:pointer; }}
            .zec-chart-card {{ background:linear-gradient(180deg,rgba(10,20,34,.88),rgba(7,14,26,.9)); border:1px solid rgba(148,163,184,.14); border-radius:16px; padding:18px; min-height:420px; }}
            .zec-kpi-strip {{ display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:0; border:1px solid rgba(148,163,184,.14); border-radius:14px; overflow:hidden; background:rgba(11,20,33,.72); }}
            .zec-kpi {{ padding:16px 18px; border-right:1px solid rgba(148,163,184,.14); min-height:86px; }} .zec-kpi:last-child {{ border-right:0; }} .zec-kpi .k-label {{ color:#cbd5e1; font-size:13px; }} .zec-kpi .k-num {{ color:#f8fafc; font-weight:950; font-size:26px; margin:6px 0; }} .zec-kpi .k-sub {{ color:#9caec3; font-size:12px; }}
            .zec-bottom-grid {{ display:grid; grid-template-columns:1fr .9fr 1.15fr; gap:16px; }}
            .zec-signal-table {{ width:100%; border-collapse:collapse; font-size:13px; }} .zec-signal-table th,.zec-signal-table td {{ border:0; border-bottom:1px solid rgba(148,163,184,.13); padding:10px 8px; text-align:left; color:#dbeafe; }} .zec-signal-table th {{ color:#96a8bd; font-size:12px; }}
            .event-pill {{ display:inline-flex !important; margin:4px; padding:7px 10px !important; border-radius:999px !important; background:rgba(30,41,59,.7) !important; border:1px solid rgba(148,163,184,.16) !important; color:#dbeafe !important; font-size:12px !important; }}

            .zec-bottom-grid .zec-panel {{ min-height: 330px; }}
            #eventBox {{ max-height: 255px; overflow-y: auto; padding-right: 4px; }}
            #eventBox::-webkit-scrollbar {{ width: 8px; }} #eventBox::-webkit-scrollbar-thumb {{ background: rgba(148,163,184,.24); border-radius:999px; }}
            body.zec-modern-body.modern-dark .zec-signal-table th {{ background:rgba(15,23,42,.88) !important; color:#9fb2c8 !important; }}
            body.zec-modern-body.modern-dark .zec-signal-table td {{ color:#dbeafe !important; }}
            .zec-signal-table th,.zec-signal-table td {{ padding: 10px 12px; border-bottom:1px solid rgba(148,163,184,.14); }}
            .zec-status-badge.signal-ok {{ color:#86efac; border-color:rgba(34,197,94,.35); background:rgba(22,101,52,.12); }}
            .zec-status-badge.signal-warn {{ color:#fde68a; border-color:rgba(245,158,11,.45); background:rgba(245,158,11,.10); }}
            .zec-mode-context {{ margin-top:16px; color:#9fb2c8; font-size:13px; line-height:1.45; }}
            body.zec-modern-body.modern-light .zec-mode-context {{ color:#475569; }}
            body.zec-modern-body.modern-light .zec-mode-context b {{ color:#111827; }}
            .zec-card-warning {{ margin-top:12px; padding:10px 12px; border-radius:12px; font-size:12.5px; line-height:1.35; border:1px solid rgba(245,158,11,.42); background:rgba(245,158,11,.10); color:#fde68a; }}
            .zec-card-warning b {{ font-weight:850; }}
            .zec-battery-layout {{ display:grid; grid-template-columns:158px 1fr; gap:20px; align-items:center; margin-top:14px; }}
            .zec-battery-metrics {{ display:flex; flex-direction:column; gap:10px; font-size:14px; line-height:1.28; }}
            .zec-battery-metric-label {{ color:#9fb2c8; font-weight:650; }}
            .zec-battery-metric-value {{ font-size:24px; font-weight:900; letter-spacing:-.02em; margin-top:2px; }}
            .soc-ring span {{ display:flex; flex-direction:column; align-items:center; justify-content:center; line-height:1.0; gap:5px; }}
            .soc-ring .soc-value {{ font-size:36px; font-weight:950; letter-spacing:-.055em; }}
            .soc-ring .soc-label {{ font-size:12px; font-weight:850; color:#94a3b8; letter-spacing:.12em; text-transform:uppercase; }}
            body.zec-modern-body.modern-light .soc-ring .soc-label {{ color:#64748b; }}
            body.zec-modern-body.modern-light .zec-card-warning {{ background:#fffbeb; border-color:#fde68a; color:#92400e; }}
            body.zec-modern-body.modern-light .zec-battery-metric-label {{ color:#475569; }}
            .sparkline .mini-grid {{ stroke:rgba(148,163,184,.18); stroke-width:1; }}
            .sparkline .mini-axis {{ stroke:rgba(148,163,184,.42); stroke-width:1.2; }}
            .sparkline .mini-zero {{ stroke:rgba(56,189,248,.5); stroke-width:1; stroke-dasharray:3 3; }}
            .sparkline .mini-line {{ fill:none; stroke-width:3; stroke-linecap:round; stroke-linejoin:round; }}
            .sparkline .mini-dot {{ fill:#0b1220; stroke-width:2.2; }}
            .sparkline .mini-label {{ fill:#9fb2c8; font-size:9.5px; font-weight:650; }}
            .soc-ring {{ width:170px !important; height:170px !important; }}
            /* RC12 Mock-up fidelity pass: light desktop dashboard when UI_DARK_MODE=false */
            body.zec-modern-body.modern-light {{ background:#f7f8fb !important; color:#111827 !important; }}
            body.zec-modern-body.modern-light .container {{ max-width:1920px !important; width:calc(100% - 52px); padding:0 0 30px 0; }}
            body.zec-modern-body.modern-light a {{ color:#2563eb; }}
            body.zec-modern-body.modern-light .zec-topbar {{ background:rgba(255,255,255,.94); border-bottom:1px solid #e5e7eb; box-shadow:0 1px 16px rgba(15,23,42,.06); color:#111827; }}
            body.zec-modern-body.modern-light .zec-logo {{ color:#111827; }}
            body.zec-modern-body.modern-light .zec-brand-sub {{ color:#374151; border-left-color:#d1d5db; }}
            body.zec-modern-body.modern-light .zec-nav-modern a, body.zec-modern-body.modern-light .zec-nav-modern button {{ color:#111827; }}
            body.zec-modern-body.modern-light .zec-nav-modern a:hover, body.zec-modern-body.modern-light .zec-nav-modern button:hover {{ background:#eff6ff; }}
            body.zec-modern-body.modern-light .zec-nav-modern .active {{ color:#2563eb; background:#eff6ff; box-shadow:inset 0 -3px 0 #3b82f6; }}
            body.zec-modern-body.modern-light .zec-system-pill {{ color:#166534; border-color:#bbf7d0; background:#ecfdf5; }}
            body.zec-modern-body.modern-light .zec-clock {{ color:#111827; }}
            body.zec-modern-body.modern-light .modern-pill, body.zec-modern-body.modern-light .zec-status-badge {{ background:#ffffff; border-color:#dbe3ee; color:#334155; box-shadow:0 1px 3px rgba(15,23,42,.05); }}
            body.zec-modern-body.modern-light .zec-status-badge.ok {{ color:#15803d; border-color:#bbf7d0; background:#f0fdf4; }}
            body.zec-modern-body.modern-light .zec-status-badge.warn {{ color:#a16207; border-color:#fde68a; background:#fffbeb; }}
            body.zec-modern-body.modern-light .zec-status-badge.bad {{ color:#be123c; border-color:#fecdd3; background:#fff1f2; }}
            body.zec-modern-body.modern-light .zec-dropdown-panel {{ background:#fff; border-color:#e5e7eb; box-shadow:0 18px 48px rgba(15,23,42,.16); }}
            body.zec-modern-body.modern-light .zec-dropdown-panel a {{ color:#111827; }}
            body.zec-modern-body.modern-light .zec-shell {{ max-width:1900px; }}
            body.zec-modern-body.modern-light .zec-panel {{ background:#ffffff; border-color:#e5e7eb; box-shadow:0 10px 28px rgba(15,23,42,.07); color:#111827; }}
            body.zec-modern-body.modern-light .zec-panel h2, body.zec-modern-body.modern-light .zec-page-title h1 {{ color:#111827; }}
            body.zec-modern-body.modern-light .zec-page-note, body.zec-modern-body.modern-light .zec-panel-desc, body.zec-modern-body.modern-light .zec-muted {{ color:#64748b !important; }}
            body.zec-modern-body.modern-light .zec-card {{ background:#ffffff; border-color:#e8edf4; border-radius:18px; box-shadow:0 14px 34px rgba(15,23,42,.065); }}
            body.zec-modern-body.modern-light .zec-card-label {{ color:#0f172a; font-size:20px; font-weight:850; display:flex; gap:10px; align-items:center; }}
            body.zec-modern-body.modern-light .zec-card-label .zec-icon {{ width:21px; height:21px; color:#2563eb; stroke-width:2.15; }}
            body.zec-modern-body.modern-light .mockup-top-card:first-child .zec-card-label .zec-icon {{ color:#f97316; }}
            body.zec-modern-body.modern-light .zec-card-value {{ color:#111827; }}
            body.zec-modern-body.modern-light .zec-card-sub {{ color:#374151; }}
            body.zec-modern-body.modern-light .zec-accent-green {{ color:#21883b !important; }}
            body.zec-modern-body.modern-light .zec-accent-blue {{ color:#1d4ed8 !important; }}
            body.zec-modern-body.modern-light .zec-accent-yellow {{ color:#ca8a04 !important; }}
            body.zec-modern-body.modern-light .zec-accent-orange {{ color:#ea580c !important; }}
            body.zec-modern-body.modern-light .zec-accent-red {{ color:#dc2626 !important; }}
            body.zec-modern-body.modern-light .zec-alert-strip {{ background:#fffbeb; border-color:#facc15; color:#854d0e; }}
            body.zec-modern-body.modern-light .zec-flow-line {{ background:#f8fafc; border-color:#e5e7eb; }}
            body.zec-modern-body.modern-light .zec-flow-line .name {{ color:#475569; }}
            body.zec-modern-body.modern-light .zec-flow-line .val {{ color:#111827; }}
            body.zec-modern-body.modern-light .zec-flow-orb {{ background:radial-gradient(circle at 50% 45%,rgba(34,197,94,.18),#ffffff 62%); border-color:#bbf7d0; box-shadow:0 8px 30px rgba(34,197,94,.12); }}
            body.zec-modern-body.modern-light .zec-flow-orb b {{ color:#111827; }}
            body.zec-modern-body.modern-light .zec-flow-orb span {{ color:#64748b; }}
            body.zec-modern-body.modern-light .zec-legacy-tile {{ background:#f8fafc; border-color:#e5e7eb; }}
            body.zec-modern-body.modern-light .zec-legacy-tile b {{ color:#111827; }}
            body.zec-modern-body.modern-light .zec-signal-table th, body.zec-modern-body.modern-light .zec-signal-table td {{ color:#111827; border-bottom-color:#e5e7eb; }}
            body.zec-modern-body.modern-light .zec-signal-table th {{ color:#64748b; }}
            body.zec-modern-body.modern-light .soc-ring {{ background:conic-gradient(#2ca24d var(--soc),#e5e7eb 0); box-shadow:none; }}
            body.zec-modern-body.modern-light .sparkline {{ width:100%; height:86px; margin:12px 0 8px; overflow:visible; }}
            body.zec-modern-body.modern-light .sparkline .mini-grid {{ stroke:#e5e7eb; stroke-width:1; }}
            body.zec-modern-body.modern-light .sparkline .mini-axis {{ stroke:#cbd5e1; stroke-width:1.2; }}
            body.zec-modern-body.modern-light .sparkline .mini-zero {{ stroke:#93c5fd; stroke-width:1; stroke-dasharray:3 3; }}
            body.zec-modern-body.modern-light .sparkline .mini-line {{ fill:none; stroke-width:3; stroke-linecap:round; stroke-linejoin:round; }}
            body.zec-modern-body.modern-light .sparkline .mini-dot {{ fill:#ffffff; stroke-width:2.2; }}
            body.zec-modern-body.modern-light .sparkline .mini-label {{ fill:#64748b; font-size:9.5px; font-weight:650; }}
            body.zec-modern-body.modern-light .mockup-top-card {{ min-height:265px; padding:24px; }}
            body.zec-modern-body.modern-light .zec-battery-layout {{ grid-template-columns:158px 1fr; gap:20px; }}
            body.zec-modern-body.modern-light .mockup-card-table {{ width:100%; border-collapse:collapse; font-size:15px; margin-top:10px; }}
            body.zec-modern-body.modern-light .mockup-card-table td {{ border:0; padding:7px 0; color:#111827; text-align:right; }}
            body.zec-modern-body.modern-light .mockup-card-table td:first-child {{ text-align:left; color:#374151; }}
            body.zec-modern-body.modern-light .mockup-footer-grid {{ display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:14px; }}
            body.zec-modern-body.modern-light .mockup-footer-card {{ background:#fff; border:1px solid #e5e7eb; border-radius:14px; padding:18px; min-height:110px; box-shadow:0 10px 24px rgba(15,23,42,.05); }}
            body.zec-modern-body.modern-light .mockup-footer-card h3 {{ color:#111827; font-size:15px; margin:0 0 14px 0; display:flex; align-items:center; gap:8px; }}
            body.zec-modern-body.modern-light .mockup-footer-card h3 .zec-icon {{ width:16px; height:16px; color:#2563eb; }}
            body.zec-modern-body.modern-light .mockup-footer-card .num {{ font-size:24px; font-weight:750; color:#111827; }}
            body.zec-modern-body.modern-light .mockup-footer-card .sub {{ color:#475569; font-size:13px; margin-top:8px; }}
            body.zec-modern-body.modern-light .zec-soc-card canvas {{ height:310px !important; max-height:310px; }}
            body.zec-modern-body.modern-light .zec-card-row {{ grid-template-columns:1.1fr 1.08fr 1.18fr 1.08fr 1.1fr; gap:14px; }}
            @media (max-width:1200px) {{ .zec-card-row,.zec-kpi-strip {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} .zec-kpi {{ border-right:0; border-bottom:1px solid rgba(148,163,184,.14); }} .zec-flow-grid,.zec-two-col,.zec-bottom-grid {{ grid-template-columns:1fr; }} .zec-brand {{ min-width:auto; }} .zec-brand-sub {{ display:none; }} }}
            @media (max-width:760px) {{ .zec-modern-body .container {{ width:calc(100% - 20px); }} .zec-topbar {{ margin:0 -10px 16px; padding:0 10px; }} .zec-card-row,.zec-diagnostics-slim {{ grid-template-columns:1fr; }} .zec-page-title {{ align-items:flex-start; flex-direction:column; }} .zec-card-value {{ font-size:27px; }} }}
            @media (max-width:1050px) {{ .modern-card-grid, .modern-card-grid.three, .modern-card-grid.four {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} .modern-flow {{ grid-template-columns:1fr; }} .flow-center {{ margin:auto; }} }}
            @media (max-width:620px) {{ body {{ margin:12px; }} .modern-card-grid, .modern-card-grid.three, .modern-card-grid.four {{ grid-template-columns:1fr; }} .modern-title {{ font-size:24px; }} }}

            {theme_css}
        </style>
        <script>
            function detailsStorageKey(item) {{
                var id = item.getAttribute('data-help-id');
                if (!id) {{
                    var section = item.closest('.section');
                    var sectionTitle = section ? (section.querySelector('h1,h2') ? section.querySelector('h1,h2').innerText : '') : '';
                    var card = item.closest('.card');
                    var cardLabel = card ? (card.querySelector('.label') ? card.querySelector('.label').innerText : '') : '';
                    var index = Array.prototype.indexOf.call(document.querySelectorAll('details.help'), item);
                    id = sectionTitle + '|' + cardLabel + '|' + index;
                    item.setAttribute('data-help-id', id);
                }}
                return 'zendure-details-open:' + location.pathname + ':' + id;
            }}
            function persistDetailsState(item) {{
                try {{ sessionStorage.setItem(detailsStorageKey(item), item.open ? '1' : '0'); }} catch(e) {{}}
            }}
            function setupPersistentDetails() {{
                document.querySelectorAll('details.help').forEach(function(item) {{
                    try {{
                        if (sessionStorage.getItem(detailsStorageKey(item)) === '1') item.open = true;
                    }} catch(e) {{}}
                    item.addEventListener('toggle', function() {{ persistDetailsState(item); }});
                }});
            }}
            function expandSectionInfo(sectionId) {{
                var items = Array.prototype.slice.call(
                    document.querySelectorAll('#' + sectionId + ' details.help')
                );
                if (!items.length) return;

                var allOpen = items.every(function(item) {{ return item.open; }});
                items.forEach(function(item) {{
                    item.open = !allOpen;
                    persistDetailsState(item);
                }});
            }}
            function closeValidationModal() {{
                document.querySelectorAll('.validation-modal').forEach(function(modal) {{
                    modal.style.display = 'none';
                    modal.setAttribute('aria-hidden', 'true');
                }});
                return false;
            }}
            function toggleManualFields() {{
                var select = document.querySelector('select[name="MANUAL_MODE"]');
                if (!select) return;
                var mode = select.value;
                document.querySelectorAll('[data-manual-card]').forEach(function(card) {{
                    var kind = card.getAttribute('data-manual-card');
                    var show = kind === 'base' || (kind === 'discharge' && mode === 'FIXED_DISCHARGE') || (kind === 'charge' && mode === 'FIXED_CHARGE');
                    card.style.display = show ? '' : 'none';
                }});
            }}
            function toggleCrossChargeFields() {{
                var select = document.querySelector('select[name="SECOND_BATTERY_SOURCE_PROFILE"]');
                if (!select) return;
                var profile = select.value;
                document.querySelectorAll('[data-cross-profile]').forEach(function(card) {{
                    var needed = card.getAttribute('data-cross-profile');
                    var show = (needed === 'evcc' && profile === 'evcc_standard') || (needed === 'custom' && profile === 'custom');
                    card.style.display = show ? '' : 'none';
                }});
            }}
            function normalizeNightTimeInput(input) {{
                var raw = (input.value || '').trim();
                var m = raw.match(/^([0-9]{{1,2}}):([0-9]{{1,2}})$/);
                if (!m) {{ input.setCustomValidity('Bitte Uhrzeit im Format hh:mm eingeben.'); return; }}
                var h = parseInt(m[1], 10);
                var min = parseInt(m[2], 10);
                if (isNaN(h) || isNaN(min) || h < 0 || h > 23 || min < 0 || min > 59) {{
                    input.setCustomValidity('Bitte gültige 24h-Uhrzeit zwischen 00:00 und 23:59 eingeben.');
                    return;
                }}
                input.value = String(h).padStart(2, '0') + ':' + String(min).padStart(2, '0');
                input.setCustomValidity('');
            }}
            function setupNightTimeInputs() {{
                document.querySelectorAll('input[data-night-time="1"]').forEach(function(input) {{
                    input.addEventListener('blur', function() {{ normalizeNightTimeInput(input); }});
                    input.addEventListener('input', function() {{ input.setCustomValidity(''); }});
                }});
            }}
            function setupAnalysisServiceLinks() {{
                document.querySelectorAll('a.analysis-service-link').forEach(function(a) {{
                    var port = a.getAttribute('data-replay-port') || '8090';
                    a.href = window.location.protocol + '//' + window.location.hostname + ':' + port;
                }});
            }}
            document.addEventListener('DOMContentLoaded', function() {{
                setupPersistentDetails();
                toggleManualFields();
                toggleCrossChargeFields();
                setupNightTimeInputs();
                setupAnalysisServiceLinks();
                var select = document.querySelector('select[name="MANUAL_MODE"]');
                if (select) select.addEventListener('change', toggleManualFields);
                var crossSelect = document.querySelector('select[name="SECOND_BATTERY_SOURCE_PROFILE"]');
                if (crossSelect) crossSelect.addEventListener('change', toggleCrossChargeFields);
            }});
            {"setInterval(function(){ window.location.reload(); }, 5000);" if refresh else ""}
        </script>
    </head>
    <body><div class="container">
    <div id="page-top"></div>
    {'' if (cfg or {}).get('__hide_nav') else build_nav_bar(cfg or {})}
    """


def build_footer() -> str:
    return "</div></body></html>"


def section_title(title: str, level: int = 1, show_version: bool = False) -> str:
    safe = html.escape(title)
    version = f'<span class="version-pill">V{APP_VERSION}</span>' if show_version else ''
    return f'<div class="section-title-row"><h{level}>{safe}</h{level}>{version}</div>'


def settings_anchor(group: str) -> str:
    if group in GROUP_ORDER:
        return f"/settings#settings-section-{GROUP_ORDER.index(group)}"
    return "/settings#settings-top"


def heading_link(title: str, group: Optional[str] = None, level: int = 2) -> str:
    href = settings_anchor(group) if group else "/settings#settings-top"
    safe_title = html.escape(title)
    return (
        f'<h{level}><a class="section-heading-link" href="{href}" '
        f'title="Passenden Konfigurationsbereich öffnen">{safe_title}</a></h{level}>'
    )


def build_headless_page(cfg: Dict[str, Any]) -> str:
    page = build_base_header("Zendure Controller Headless Mode", cfg=cfg)
    page += f"""
    <div class="section headless-box">
        {section_title('Headless Mode aktiviert', 1, True)}
        <p class="small">
            Die Weboberflächen des Zendure Energy Controllers sind derzeit per Config deaktiviert.
            Die Regelung läuft weiterhin im Hintergrund, aber Status-, Graph-, Settings- und
            Diagnose-Webseiten werden nicht angezeigt.
        </p>
        <p class="small">
            Änderungen der Konfiguration sind in diesem Modus nur direkt über die
            <code>config.json</code> möglich. Der Controller lädt die Datei regelmäßig neu.
            Wird <code>HEADLESS_MODE</code> wieder auf <code>false</code> gesetzt und gespeichert,
            werden die Webseiten beim nächsten Config-Reload wieder angezeigt. Für MQTT-, Topic-,
            Web-Port- oder Startparameter-Änderungen ist ein Neustart weiterhin empfehlenswert.
        </p>
        <p class="small">
            Zum Reaktivieren der Weboberfläche setze in <code>config.json</code>:
            <br><code>"HEADLESS_MODE": false</code>
        </p>
    </div>
    """
    page += build_footer()
    return page


def badge(text: str, color: str) -> str:
    return f'<span class="badge" style="background:{color}">{html.escape(text)}</span>'


def format_hms(seconds: Any) -> str:
    try:
        total = max(0, int(seconds))
    except Exception:
        return "00:00:00"
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_dhms(seconds: Any) -> str:
    try:
        total = max(0, int(seconds))
    except Exception:
        return "0 Tage 00:00:00"
    days = total // 86400
    rest = total % 86400
    return f"{days} Tage {format_hms(rest)}"


def age_text(age: Any) -> str:
    if age is None:
        return "-"
    return f"{age} s"



def temp_css_class(value: Any) -> str:
    try:
        temp = float(value)
    except Exception:
        return "gray"
    if temp <= 49.0:
        return "green"
    if temp <= 55.0:
        return "yellow"
    return "red"


def signed_power(value: Any) -> str:
    try:
        v = int(float(value))
    except Exception:
        v = 0
    return f"{v:+d} W" if v != 0 else "0 W"


def power_direction_text(value: Any) -> str:
    try:
        v = int(float(value))
    except Exception:
        return "unbekannt"
    if v > 0:
        return "Ladung"
    if v < 0:
        return "Entladung"
    return "keine Leistung"


def status_card(label: str, value: str, details: str = "", value_class: str = "gray", help_text: str = "", technical: str = "", settings_group: Optional[str] = None) -> str:
    help_html = ""
    if help_text:
        help_html = f'<details class="help"><summary>Info</summary><div class="small">{help_text}</div></details>'
    technical_html = f'<div class="technical">Technisch: {html.escape(technical)}</div>' if technical else ""
    safe_label = html.escape(label)
    if settings_group:
        label_html = (
            f'<a class="section-heading-link" href="{settings_anchor(settings_group)}" '
            f'title="Passenden Konfigurationsbereich öffnen">{safe_label}</a>'
        )
    else:
        label_html = safe_label
    return f"""
    <div class="card">
        <div class="label">{label_html}</div>
        <div class="value {value_class}">{value}</div>
        <div class="small">{details}</div>
        {technical_html}
        {help_html}
    </div>
    """


def night_mode_projection_text(cfg: Dict[str, Any], s: Dict[str, Any], current_mode: str) -> str:
    if not cfg.get("NIGHT_DISCHARGE_ENABLED", False):
        return "Voraussichtliches Ende: nicht relevant – Nachtmodus deaktiviert"
    try:
        now = datetime.now()
        start = now.replace(hour=int(cfg.get('NIGHT_START_HOUR', 0)), minute=int(cfg.get('NIGHT_START_MINUTE', 0)), second=0, microsecond=0)
        end = now.replace(hour=int(cfg.get('NIGHT_END_HOUR', 0)), minute=int(cfg.get('NIGHT_END_MINUTE', 0)), second=0, microsecond=0)
        if end <= start:
            if now <= end:
                start = start - timedelta(days=1)
            else:
                end = end + timedelta(days=1)
        in_window = start <= now <= end
        if current_mode != "NIGHT_DISCHARGE" and not in_window:
            return "Voraussichtliches Ende: nicht relevant – Nachtfenster aktuell nicht aktiv"
        soc = s.get("battery_soc")
        capacity_wh = cfg.get("ZENDURE_BATTERY_CAPACITY_WH")
        night_power_w = int(cfg.get("NIGHT_DISCHARGE_POWER_W", 0) or 0)
        missing = []
        if soc is None:
            missing.append("Zendure-MQTT-Werte enthalten keinen SOC oder der SOC-Wert ist nicht aktuell")
        if capacity_wh in (None, ""):
            missing.append("Batteriekapazität für Prognose in Settings → Nachtmodus")
        if night_power_w <= 0:
            missing.append("bitte in Settings → Nachtmodus eine plausible Nachtentladeleistung größer als 0 W eintragen")
        if missing:
            if missing == ["Batteriekapazität für Prognose in Settings → Nachtmodus"]:
                return "Voraussichtliches Ende: nicht berechenbar – bitte in Settings → Nachtmodus die Zendure-Batteriekapazität für die Prognose eintragen"
            return "Voraussichtliches Ende: nicht berechenbar – " + "; ".join(missing)
        soc_f = float(soc)
        capacity_wh = float(capacity_wh)
        if capacity_wh <= 0:
            return "Voraussichtliches Ende: nicht berechenbar – Zendure-Batteriekapazität für Prognose in Settings → Nachtmodus muss größer als 0 Wh sein"
        reserve = cfg.get("NIGHT_DISCHARGE_STOP_SOC_PERCENT")
        reserve_soc = float(reserve) if reserve not in (None, "") else float(cfg.get("MIN_SOC_PERCENT", 0) or 0)
        reserve_soc = max(float(cfg.get("MIN_SOC_PERCENT", 0) or 0), reserve_soc)
        if soc_f <= reserve_soc:
            return f"Voraussichtliches Ende: jetzt durch Reserve-SOC ({reserve_soc:.0f} %)"
        rest_wh = capacity_wh * max(0.0, soc_f - reserve_soc) / 100.0
        hours_to_reserve = rest_wh / float(night_power_w)
        reserve_time = now + timedelta(hours=hours_to_reserve)
        if reserve_time <= end:
            return f"Voraussichtliches Ende: {reserve_time.strftime('%H:%M')} Uhr durch Reserve-SOC ({reserve_soc:.0f} %)"
        hours_to_window_end = max(0.0, (end - now).total_seconds() / 3600.0)
        used_wh = night_power_w * hours_to_window_end
        projected_soc = max(reserve_soc, soc_f - (used_wh / capacity_wh) * 100.0)
        return f"Voraussichtliches Ende: {end.strftime('%H:%M')} Uhr durch Nachtfenster-Ende mit vorauss. SOC von {projected_soc:.0f} %"
    except Exception as exc:
        return f"Voraussichtliches Ende: nicht berechenbar – {html.escape(str(exc))}"


def _fixed_mode_effective_power_w(cfg: Dict[str, Any], s: Dict[str, Any], current_mode: str) -> float:
    """Return the actually applied fixed-mode target for ETA calculations."""
    final_target = _safe_float(s.get("target_final_w"))
    if current_mode in {"MANUAL_FIXED_DISCHARGE", "FIXED_DISCHARGE"}:
        if final_target is not None and final_target < 0:
            return abs(final_target)
        applied = _safe_float(s.get("last_output_power"))
        if applied is not None and applied > 0:
            return applied
        requested = max(0.0, float(cfg.get("MANUAL_FIXED_DISCHARGE_POWER_W", 0) or 0))
        global_cap = max(0.0, float(cfg.get("MAX_DISCHARGE_POWER_W", requested) or 0))
        device_cap = _safe_float(s.get("zendure_device_inverse_max_power_w"))
        limits = [requested, global_cap]
        if device_cap is not None and device_cap > 0:
            limits.append(device_cap)
        return min(limits)
    if final_target is not None and final_target > 0:
        return final_target
    applied = _safe_float(s.get("last_input_power"))
    if applied is not None and applied > 0:
        return applied
    requested = max(0.0, float(cfg.get("MANUAL_FIXED_CHARGE_POWER_W", 0) or 0))
    global_cap = max(0.0, float(cfg.get("MAX_CHARGE_POWER_W", requested) or 0))
    device_cap = _safe_float(s.get("zendure_device_charge_max_limit_w"))
    limits = [requested, global_cap]
    if device_cap is not None and device_cap > 0:
        limits.append(device_cap)
    return min(limits)


def fixed_mode_projection_text(cfg: Dict[str, Any], s: Dict[str, Any], current_mode: str) -> str:
    """Projection for manual fixed charge/discharge modes, mirroring night mode UX."""
    if current_mode not in {"MANUAL_FIXED_DISCHARGE", "MANUAL_FIXED_CHARGE", "FIXED_DISCHARGE", "FIXED_CHARGE"}:
        return ""
    try:
        soc = s.get("battery_soc")
        capacity_wh = cfg.get("ZENDURE_BATTERY_CAPACITY_WH")
        missing = []
        if soc is None:
            missing.append("Zendure-SOC fehlt oder ist nicht aktuell")
        if capacity_wh in (None, ""):
            missing.append("Batteriekapazität für Prognose in Settings → Nachtmodus")
        if missing:
            return "Prognose: nicht berechenbar – " + "; ".join(missing)
        soc_f = float(soc)
        capacity_wh_f = float(capacity_wh)
        if capacity_wh_f <= 0:
            return "Prognose: nicht berechenbar – Zendure-Batteriekapazität muss größer als 0 Wh sein"

        if current_mode in {"MANUAL_FIXED_DISCHARGE", "FIXED_DISCHARGE"}:
            target_soc = max(float(cfg.get("MIN_SOC_PERCENT", 0) or 0), float(cfg.get("MANUAL_FIXED_DISCHARGE_TARGET_SOC", cfg.get("MIN_SOC_PERCENT", 0)) or 0))
            power_w = _fixed_mode_effective_power_w(cfg, s, current_mode)
            after = "STOP_HOLD" if str(cfg.get("MANUAL_DISCHARGE_AFTER_TARGET", "AUTO")) == "STOP_HOLD" else "Automatik-Modus"
            if power_w <= 0:
                return f"Manuelle feste Entladung bis {target_soc:.0f} % SOC · Prognose nicht berechenbar – Entladeleistung ist 0 W"
            if soc_f <= target_soc:
                return f"Manuelle feste Entladung bis {target_soc:.0f} % SOC · Ziel erreicht, danach {after}"
            rest_wh = capacity_wh_f * max(0.0, soc_f - target_soc) / 100.0
            eta = datetime.now() + timedelta(hours=rest_wh / power_w)
            return f"Manuelle feste Entladung bis {target_soc:.0f} % SOC, voraussichtlich erreicht um {eta.strftime('%H:%M')} Uhr · danach {after}"

        target_soc = min(float(cfg.get("MAX_SOC_PERCENT", 100) or 100), float(cfg.get("MANUAL_FIXED_CHARGE_TARGET_SOC", cfg.get("MAX_SOC_PERCENT", 100)) or 100))
        power_w = _fixed_mode_effective_power_w(cfg, s, current_mode)
        after = "STOP_HOLD" if str(cfg.get("MANUAL_CHARGE_AFTER_TARGET", "AUTO")) == "STOP_HOLD" else "Automatik-Modus"
        if power_w <= 0:
            return f"Manuelle feste Ladung bis {target_soc:.0f} % SOC · Prognose nicht berechenbar – Ladeleistung ist 0 W"
        if soc_f >= target_soc:
            return f"Manuelle feste Ladung bis {target_soc:.0f} % SOC · Ziel erreicht, danach {after}"
        need_wh = capacity_wh_f * max(0.0, target_soc - soc_f) / 100.0
        eta = datetime.now() + timedelta(hours=need_wh / power_w)
        return f"Manuelle feste Ladung bis {target_soc:.0f} % SOC, voraussichtlich erreicht um {eta.strftime('%H:%M')} Uhr · danach {after}"
    except Exception as exc:
        return f"Prognose: nicht berechenbar – {html.escape(str(exc))}"



def rest_surplus_status_lines(cfg: Dict[str, Any], s: Dict[str, Any]) -> str:
    """Human-readable status lines for the Restüberschuss-Ernte in the SMA/Zweitbatterie card."""
    enabled = bool(cfg.get("REST_SURPLUS_HARVEST_ENABLED", False))
    max_charge_raw = cfg.get("SECOND_BATTERY_MAX_CHARGE_POWER_W")
    try:
        max_charge = int(float(max_charge_raw)) if max_charge_raw not in (None, "") else 0
    except Exception:
        max_charge = 0
    min_export = int(cfg.get("REST_SURPLUS_MIN_EXPORT_W", 80) or 80)
    entry_confirm = int(cfg.get("REST_SURPLUS_ENTRY_CONFIRM_SECONDS", 30) or 30)
    threshold = s.get("second_battery_charge_saturation_threshold_w")
    if threshold in (None, "") and max_charge > 0:
        threshold = max(0, max_charge - int(cfg.get("SECOND_BATTERY_CHARGE_SATURATION_MARGIN_W", 100) or 100))

    if not enabled:
        config_line = "deaktiviert"
        ready_line = "nicht verfügbar – Funktion ist in den Settings ausgeschaltet"
    else:
        config_line = "aktiviert"
        if max_charge <= 0:
            ready_line = "nicht verfügbar – maximale Ladeleistung Primärspeicher fehlt"
        elif not cross_charge_enabled(cfg):
            ready_line = "nicht verfügbar – Cross-Charge-Schutz ist deaktiviert"
        elif not bool(s.get("second_battery_data_valid")) or not bool(s.get("second_battery_data_fresh")):
            ready_line = "nicht verfügbar – Zweitbatterie-Leistungsdaten wurden nicht empfangen oder sind nicht aktuell"
        else:
            threshold_text = f"ab ca. {float(threshold):.0f} W Primärspeicher-Ladung" if threshold not in (None, "") else "Schwelle berechnet"
            ready_line = f"bereit ({threshold_text}, Entry ab {min_export} W Export für ca. {entry_confirm} s)"

    active = bool(s.get("rest_surplus_harvest_active"))
    eligible = bool(s.get("rest_surplus_harvest_eligible"))
    try:
        progress = float(s.get("rest_surplus_entry_progress_s") or 0.0)
    except Exception:
        progress = 0.0
    exit_reason = str(s.get("rest_surplus_exit_reason") or "")
    if active:
        activity = "aktiv – Restüberschuss-Ernte darf Ladeziel halten/führen"
    elif enabled and progress > 0:
        activity = f"Entry läuft – {progress:.0f} / {entry_confirm} s"
    elif enabled and eligible:
        activity = "Entry-Bedingung erfüllt – Bestätigungszeit läuft"
    elif enabled and exit_reason and exit_reason not in {"DISABLED"}:
        activity = f"inaktiv – letzter Grund: {html.escape(exit_reason)}"
    elif enabled:
        activity = "inaktiv – Entry-Bedingung nicht erfüllt"
    else:
        activity = "inaktiv"

    return (
        "<hr style='border:0;border-top:1px solid rgba(148,163,184,0.35);margin:10px 0;'>"
        "<b>Restüberschuss-Ernte</b><br>"
        f"Konfiguration: {config_line}<br>"
        f"Bereitschaft: {ready_line}<br>"
        f"Aktivität: {activity}"
    )


def build_status_page_legacy(cfg: Dict[str, Any], s: Dict[str, Any]) -> str:
    current_mode = str(s["current_mode"])
    evcc_enabled = bool(cross_charge_enabled(cfg))
    second_name = second_battery_name(cfg)
    second_name_html = html.escape(second_name)
    mode_color = {
        "CHARGE": "#4CAF50", "DISCHARGE": "#2196F3", "NIGHT_DISCHARGE": "#9C27B0",
        "SAFE_STATE": "#f44336", "BLOCKED_BY_SMA": "#ff9800", "HOLD": "#777",
        "CHARGE_RAMP_DOWN": "#ff9800", "DISCHARGE_RAMP_DOWN": "#ff9800",
        "STOP_HOLD": "#777", "MANUAL_FIXED_DISCHARGE": "#2196F3", "MANUAL_FIXED_CHARGE": "#4CAF50",
    }.get(current_mode, "#777")
    mqtt_color = "#4CAF50" if s["mqtt_connected"] else "#f44336"
    raw_grid_value = float(s.get("raw_grid_power", 0.0) or 0.0)
    smoothed_grid_value = float(s.get("grid_power", 0.0) or 0.0)
    grid_age = s.get("grid_power_age_seconds")
    grid_source_text = html.escape(str(s.get("raw_grid_source") or "unbekannt"))
    grid_valid = bool(s.get("grid_power_valid", False))
    grid_reason = str(s.get("grid_power_validity_reason", ""))
    grid_used_for_control = bool(s.get("grid_power_used_for_control", False))
    grid_class = "red" if raw_grid_value > 0 else ("green" if raw_grid_value < 0 else "blue")
    if grid_valid:
        grid_main_value = f"{raw_grid_value:.1f} W"
        grid_status_line = "aktueller Messwert" + (" · für AUTO-Regelung genutzt" if grid_used_for_control else " · nicht regelrelevant")
    else:
        grid_main_value = "nicht aktuell"
        grid_status_line = f"nicht gültig: {html.escape(grid_reason or 'unbekannt')}"
        grid_class = "gray"
    if grid_used_for_control:
        auto_rule_line = f"Geglätteter AUTO-Regelwert: {smoothed_grid_value:.1f} W"
    else:
        auto_rule_line = "Geglätteter AUTO-Regelwert: n.a. · nicht aktiv"
    if grid_valid:
        grid_details = (
            f"{grid_status_line}<br>"
            f"Quelle: {grid_source_text} · Alter: {age_text(grid_age)}<br>"
            f"{auto_rule_line}<br>"
            f'positiv = <span class="red">Netzbezug</span>, negativ = <span class="green">Einspeisung</span>'
        )
    else:
        grid_details = (
            f"{grid_status_line}<br>"
            f"Quelle: {grid_source_text}<br>"
            f"Letzter Messwert: {raw_grid_value:.1f} W · Alter: {age_text(grid_age)}<br>"
            f"{auto_rule_line}<br>"
            f'positiv = <span class="red">Netzbezug</span>, negativ = <span class="green">Einspeisung</span>'
        )
    active_limiters = list(s.get("active_limiters", []))
    limiter_human = limiter_text(active_limiters)
    limiter_technical = technical_limiter_text(active_limiters)
    path_code = str(s.get("technical_control_path", "-"))
    path_human = path_label(path_code)
    manual_mode_code = str(cfg.get("MANUAL_MODE", "AUTO"))
    manual_mode_human = {
        "AUTO": "Automatik",
        "STOP_HOLD": "Stop/Hold",
        "FIXED_DISCHARGE": "Feste Entladung",
        "FIXED_CHARGE": "Feste Beladung",
    }.get(manual_mode_code, manual_mode_code)
    manual_mode_color = {
        "AUTO": "#4CAF50",
        "STOP_HOLD": "#f44336",
        "FIXED_DISCHARGE": "#777",
        "FIXED_CHARGE": "#777",
    }.get(manual_mode_code, "#777")

    zendure_mqtt_status = str(s.get("zendure_mqtt_overall_status", "ZENDURE_MQTT_STALE"))
    zendure_mqtt_reason = str(s.get("zendure_mqtt_status_reason", "-"))
    zendure_mqtt_color = "#4CAF50" if zendure_mqtt_status == "ZENDURE_MQTT_OK" else ("#ff9800" if s.get("mqtt_connected") else "#f44336")
    zendure_mqtt_hint = "" if zendure_mqtt_status == "ZENDURE_MQTT_OK" else "<br><b>Hinweis:</b> Falls nach Raspberry-/Mosquitto-Neustart keine Live-Werte kommen, MQTT in der Zendure-App erneut speichern/aktivieren."
    mqtt_details = (
        f'Letztes Kommando: {html.escape(str(s["last_mqtt_command"]))}<br>'
        f'Zendure Live-Status: <span style="color:{zendure_mqtt_color}">{html.escape(zendure_mqtt_status)}</span><br>'
        f'Grund: {html.escape(zendure_mqtt_reason)}<br>'
        f'Live bestätigt: {"ja" if s.get("zendure_mqtt_live_confirmed") else "nein"}<br>'
        f'Kritische Daten Alter: {age_text(s.get("zendure_mqtt_critical_data_age_s"))}<br>'
        f'Fehlende Gruppen: {html.escape(str(s.get("zendure_mqtt_missing_critical_groups") or "-"))}<br>'
        f'Stale Gruppen: {html.escape(str(s.get("zendure_mqtt_stale_critical_groups") or "-"))}'
        + zendure_mqtt_hint
    )

    night_stop_soc = s.get("night_discharge_stop_soc_percent")
    night_stop_reason = str(s.get("night_discharge_stop_reason", "none"))
    night_stopped = current_mode != "NIGHT_DISCHARGE" and night_stop_reason not in {"", "none", "None"}
    night_paused_for_reserve = night_stop_reason == "NIGHT_RESERVE_SOC"
    night_status_text = "aktiv" if current_mode == "NIGHT_DISCHARGE" else (("pausiert" if night_paused_for_reserve else "gestoppt") if night_stopped else ("bereit" if cfg.get("NIGHT_DISCHARGE_ENABLED") else "aus"))
    night_status_color = "#9C27B0" if current_mode == "NIGHT_DISCHARGE" else ("#ff9800" if night_stopped else ("#4CAF50" if cfg.get("NIGHT_DISCHARGE_ENABLED") else "#777"))
    night_projection = night_mode_projection_text(cfg, s, current_mode)
    fixed_projection = fixed_mode_projection_text(cfg, s, current_mode)
    night_details = (
        f"Zeitfenster: {int(cfg.get('NIGHT_START_HOUR', 0)):02d}:{int(cfg.get('NIGHT_START_MINUTE', 0)):02d}–{int(cfg.get('NIGHT_END_HOUR', 0)):02d}:{int(cfg.get('NIGHT_END_MINUTE', 0)):02d}<br>"
        f"Leistung: {int(cfg.get('NIGHT_DISCHARGE_POWER_W', 0))} W<br>"
        f"Reserve-SOC: {night_stop_soc if night_stop_soc is not None else '-'} %<br>"
        f"{html.escape(night_projection)}<br>"
        f"Stop-Grund: {html.escape(night_stop_reason)}"
        + ("<br>Feste Nachtentladung pausiert; AUTO-Regelung bleibt für Lastspitzen aktiv." if night_paused_for_reserve else "")
    )

    zendure_setpoint_signed = int(s.get("last_input_power", 0) or 0)
    if int(s.get("last_output_power", 0) or 0) > 0:
        zendure_setpoint_signed = -int(s.get("last_output_power", 0) or 0)
    zendure_setpoint_class = "green" if zendure_setpoint_signed > 0 else ("red" if zendure_setpoint_signed < 0 else "blue")
    sma_display_power = float(s.get("sma_battery_display_power", s.get("sma_battery_power", 0.0)) or 0.0)

    mqtt_soc_age = s.get("last_mqtt_soc_update_age_seconds")
    api_age = s.get("last_local_api_update_age_seconds")
    sensor_age = s.get("last_mqtt_zendure_sensor_update_age_seconds")
    telemetry_source = str(s.get("zendure_telemetry_source") or "none")
    fallback_active = bool(s.get("zendure_local_api_fallback_active", False))
    soc_details = (
        f'Aktive Quelle: {html.escape(telemetry_source)}<br>'
        f'MQTT-SOC: {s.get("mqtt_battery_soc") if s.get("mqtt_battery_soc") is not None else "-"} %<br>'
        f'Letztes MQTT-SOC Update: {s.get("last_mqtt_soc_update_time", "-")} (Alter: {age_text(mqtt_soc_age)})<br>'
        f'Letztes Zendure MQTT-Sensorupdate: {s.get("last_mqtt_zendure_sensor_update_time", "-")} (Alter: {age_text(sensor_age)})<br>'
        f'Lokale API SOC: {s.get("local_api_soc") if s.get("local_api_soc") is not None else "-"} %<br>'
        f'Letztes API-Update: {s.get("last_local_api_update_time", "-")} (Alter: {age_text(api_age)})<br>'
        f'Fallback aktiv: {"ja" if fallback_active else "nein"}<br>'
        f'Letzter API-Fehler: {html.escape(str(s.get("last_local_api_error", "none")))}'
    )

    actual_system_signed = int(s.get("zendure_system_signed_power", 0) or 0)
    actual_system_class = "green" if actual_system_signed > 0 else ("red" if actual_system_signed < 0 else "blue")
    actual_system_html = f'<span class="{actual_system_class}">{signed_power(actual_system_signed)}</span>'
    last_command_html = html.escape(str(s.get("last_mqtt_command") or s.get("mqtt_last_command") or "-"))
    last_command_skipped_html = html.escape(str(s.get("last_mqtt_command_skipped") or s.get("mqtt_last_command_skipped") or "-"))
    if zendure_setpoint_signed == 0 and abs(actual_system_signed) >= int(cfg.get("MIN_COMMAND_CHANGE_W", 50)):
        setpoint_hint = "<br><span class='warn'>Hinweis: Zielwert ist 0 W, die gemessene Zendure-Istleistung ist aber noch deutlich aktiv. Das kann kurzer Nachlauf oder ein zuvor wirksames Limit nach Restart/HOLD sein.</span>"
    else:
        setpoint_hint = ""

    battery_details = list(s.get("zendure_battery_details", []) or [])
    def battery_sort_key(item: Dict[str, Any]) -> str:
        sn = str(item.get("pack_sn", ""))
        if sn == str(cfg.get("DEVICE_ID", "")) or sn.lower() == "headunit" or sn.startswith("HEC"):
            return "0" + sn
        return "1" + sn
    battery_details = sorted(battery_details, key=battery_sort_key)

    system_sign = 1 if actual_system_signed > 0 else (-1 if actual_system_signed < 0 else 0)
    pack_power_rows = []
    for item in battery_details:
        sn = html.escape(str(item.get("pack_sn", "Akku")))
        raw_power = item.get("power_w")
        if raw_power is None:
            continue
        try:
            display_power = abs(int(float(raw_power))) * system_sign if system_sign else int(float(raw_power))
        except Exception:
            continue
        direction = power_direction_text(display_power)
        soc = item.get("soc_percent")
        soc_text = f', SOC {soc} %' if soc is not None else ''
        state_text = f', Status {html.escape(str(item.get("state")))}' if item.get("state") else ''
        src = html.escape(str(item.get("power_source") or item.get("data_source") or "-"))
        pack_power_rows.append(
            f'- {sn}: {signed_power(display_power)} ({direction}{soc_text}{state_text}, Quelle: {src})'
        )
    pack_power_text = '<br>'.join(pack_power_rows) if pack_power_rows else 'Keine Pack-Leistungsdaten verfügbar.'

    temp_value = s.get("current_battery_temperature_c")
    temp_value_text = f'{float(temp_value):.1f} °C' if temp_value is not None else '- °C'
    temp_value_class = temp_css_class(temp_value)
    temp_rows = []
    for item in battery_details:
        sn = html.escape(str(item.get("pack_sn", "Batterie")))
        temp = item.get("temperature_c")
        if temp is None:
            continue
        tcls = temp_css_class(temp)
        src = html.escape(str(item.get("temperature_source") or item.get("data_source") or "-"))
        high = item.get("highest_temperature_c")
        low = item.get("lowest_temperature_c")
        high_cls = temp_css_class(high)
        low_cls = temp_css_class(low)
        high_text = f'<span class="{high_cls}">{float(high):.1f} °C</span>' if high is not None else '- °C'
        low_text = f'<span class="{low_cls}">{float(low):.1f} °C</span>' if low is not None else '- °C'
        source_diag_rows = []
        sources = item.get("temperature_sources") or {}
        for source_name in ("MQTT", "Lokale API"):
            src_info = sources.get(source_name)
            if not src_info:
                continue
            src_temp = src_info.get("temperature_c")
            src_raw = src_info.get("raw_value")
            src_time = src_info.get("update_time", "-")
            if src_temp is None:
                continue
            source_diag_rows.append(
                f'&nbsp;&nbsp;{html.escape(source_name)}: <span class="{temp_css_class(src_temp)}">{float(src_temp):.1f} °C</span> '
                f'(Rohwert: {html.escape(str(src_raw))}, Update: {html.escape(str(src_time))})'
            )
        source_diag = '<br>' + '<br>'.join(source_diag_rows) if source_diag_rows else ''
        temp_rows.append(
            f'- {sn}: <span class="{tcls}">{float(temp):.1f} °C</span> (Anzeigequelle: {src})<br>'
            f'&nbsp;&nbsp;Highest: {high_text} ({html.escape(str(item.get("highest_temperature_time", "-")))})<br>'
            f'&nbsp;&nbsp;Lowest: {low_text} ({html.escape(str(item.get("lowest_temperature_time", "-")))})'
            f'{source_diag}'
        )
    temp_details = '<br>'.join(temp_rows) if temp_rows else 'Keine Batterie-Temperaturdaten vorhanden.'


    evcc_status_card_html = ""
    sma_card_html = ""
    if evcc_enabled:
        evcc_age = s.get("last_sma_battery_update_age_seconds")
        evcc_timeout = int(cfg.get("SECOND_BATTERY_STALE_TIMEOUT_SECONDS", cfg.get("EVCC_STALE_TIMEOUT_SECONDS", 30)))
        evcc_has_data = bool(s.get("evcc_data_available", False)) and evcc_age is not None
        evcc_current = evcc_has_data and evcc_age <= evcc_timeout
        evcc_status_text = "Aktuell" if evcc_current else ("Veraltet" if evcc_has_data else "Keine Daten")
        evcc_color = "#4CAF50" if evcc_current else "#f44336"
        evcc_details = (
            f"Letztes Update: {s.get('last_sma_battery_update_time', '-')}<br>"
            f"Alter: {evcc_age if evcc_age is not None else '-'} s<br>"
            f"Timeout: {evcc_timeout} s"
        )
        evcc_status_card_html = status_card(
            'Zusatzbatterie MQTT',
            badge(evcc_status_text, evcc_color),
            evcc_details,
            'gray',
            f'Diese Anzeige bewertet, ob über MQTT aktuelle Zusatzbatterie-Werte für {second_name_html} eintreffen. Grün bedeutet: Die Werte sind vorhanden und jünger als der konfigurierte Daten-Timeout. Rot bedeutet: Es liegen keine oder zu alte Werte vor; je nach Config blockiert der Cross-Charge-Schutz dann die Zendure-Ladung konservativ.',
            settings_group='Zweitbatterie'
        )
        harvest_lines = rest_surplus_status_lines(cfg, s)
        sma_card_html = status_card(
            second_name_html,
            f'{sma_display_power:.1f} W',
            f'Darstellung: positiv = Ladung, negativ = Entladung<br>'
            f'Entladung berechnet: {s["sma_battery_discharge_power"]:.1f} W<br>'
            f'SOC: {s["sma_battery_soc"] if s["sma_battery_soc"] is not None else "-"} %<br>'
            f'MQTT Update: {s["last_sma_battery_update_time"]}'
            f'{harvest_lines}',
            'gray',
            f'Dieser Wert kommt per MQTT aus der generischen MQTT-Zusatzbatterie-Integration. Für die Anzeige wird die in den Settings konfigurierte Vorzeichenlogik berücksichtigt: positiv bedeutet Ladung von {second_name_html}, negativ bedeutet Entladung. Der positive Entladewert wird intern für den Cross-Charge-Schutz genutzt, um Batterie-zu-Batterie-Ladung zu vermeiden. Die Restüberschuss-Ernte wird hier angezeigt, weil sie fachlich nur zusammen mit dem Primärspeicher/Zweitbatterie-Signal sinnvoll ist.',
            settings_group='Zweitbatterie'
        )

    limiter_details = ""
    if evcc_enabled:
        limiter_details = f'Effektiver Überschuss für Zendure: {s["effective_export_power"]} W'
    else:
        limiter_details = 'Cross-Charge-Schutz ist deaktiviert; Zusatzbatterie-abhängige Werte werden ausgeblendet.'

    replay_port = int(cfg.get("REPLAY_WEB_PORT", 8090))
    analysis_link_html = (
        f"<a id=\"analysisWebLink\" href=\"#\" data-replay-port=\"{replay_port}\">Analyse öffnen</a>"
        f"<script>"
        f"(function(){{"
        f"var a=document.getElementById('analysisWebLink');"
        f"if(a){{var p=a.getAttribute('data-replay-port')||'{replay_port}';"
        f"a.href=window.location.protocol+'//'+window.location.hostname+':'+p;}}"
        f"}})();"
        f"</script>"
        '<br>Separater optionaler Dienst: zendure-replay.service'
        '<br><span class="small">Der Link nutzt automatisch den aktuellen Hostnamen des Browsers und den Analyse-Port.</span>'
    )


    measurement_mode = html.escape(str(cfg.get('MEASUREMENT_LOG_MODE', 'off')))
    measurement_status = html.escape(str(s.get("measurement_log_status", "-")))
    measurement_reason = html.escape(str(s.get("measurement_log_status_reason", "-")))
    measurement_path = html.escape(str(s.get("measurement_log_path") or resolve_log_path(cfg, allow_fallback=True)[0]))
    target_label_map = {
        "internal_sd": "interne SD",
        "external_mount": "USB-/Mountpoint",
        "custom_path": "benutzerdefinierter Pfad",
        "fallback_sd": "SD-Fallback",
        "unavailable": "nicht verfügbar",
    }
    active_target_raw = str(s.get("measurement_log_active_target_type") or cfg.get("MEASUREMENT_LOG_STORAGE_TARGET", "internal_sd"))
    active_target = html.escape(target_label_map.get(active_target_raw, active_target_raw))
    configured_target_raw = str(cfg.get("MEASUREMENT_LOG_STORAGE_TARGET", "internal_sd"))
    configured_target = html.escape(target_label_map.get(configured_target_raw, configured_target_raw))
    fallback_count = html.escape(str(s.get("measurement_fallback_count_since_start", 0)))
    fallback_time = str(s.get("measurement_last_fallback_time") or "")
    fallback_reason = str(s.get("measurement_last_fallback_reason") or "")
    fallback_line = ""
    if fallback_time or fallback_reason or str(fallback_count) not in {"", "0"}:
        fallback_line = (
            f"<br>Fallbacks seit Start: {fallback_count}"
            f"<br>Letzter Fallback: {html.escape(fallback_time or '-')}"
            f"<br>Letzter Grund: {html.escape(fallback_reason or '-')}"
        )
    measurement_path_raw = str(s.get("measurement_log_path") or resolve_log_path(cfg, allow_fallback=True)[0])
    measurement_path_obj = os.path.basename(measurement_path_raw)
    measurement_dir_obj = os.path.dirname(measurement_path_raw)
    measurement_file_html = html.escape(measurement_path_obj or "-")
    measurement_dir_html = html.escape(measurement_dir_obj or "-")
    measurement_full_path_html = html.escape(measurement_path_raw or "-", quote=True)
    path_block = (
        f"Datei: <span class='path-fragment' title='{measurement_full_path_html}'>{measurement_file_html}</span><br>"
        f"Verzeichnis: <span class='path-fragment path-dir' title='{measurement_full_path_html}'>{measurement_dir_html}</span>"
    )

    timing_step_labels = {
        "config_reload_ms": "Config laden",
        "mqtt_refresh_subscriptions_ms": "MQTT-Subscriptions",
        "zendure_local_api_snapshot_apply_ms": "Zendure API-Snapshot",
        "zendure_local_api_ms": "Zendure API (historisch)",
        "cycle_display_metrics_ms": "Statuswerte",
        "grid_display_read_ms": "Grid-Anzeige",
        "grid_control_read_ms": "Grid-Regelwert",
        "cross_charge_metrics_ms": "Zusatzbatterie",
        "charge_acceptance_diag_ms": "Ladeannahme-Diagnose",
        "graph_snapshot_ms": "Status-Snapshot",
        "measurement_logging_ms": "Messdaten-Logging",
        "run_once_ms": "Regelentscheidung",
        "finish_cycle_ms": "Zyklusabschluss (Sammelwert)",
        "other_cycle_work_ms": "Sonstige, nicht einzeln erfasste Verarbeitung",
    }
    active_cycle_ms = int(s.get("last_cycle_total_ms") or s.get("last_loop_duration_ms") or 0)
    slowest_key = str(s.get("last_cycle_slowest_step") or "")
    slowest_ms = int(s.get("last_cycle_slowest_step_ms") or 0)
    slowest_label = timing_step_labels.get(slowest_key, "-") if slowest_key and slowest_key != "none" else "-"
    slowest_line = f"<br>Langsamster Teil: {html.escape(slowest_label)} {slowest_ms} ms" if slowest_label != "-" else ""
    timing_details = (
        f'Zyklen: {s["loop_counter"]}<br>'
        f'Uptime: {format_dhms(s["uptime_seconds"])}'
        f'{slowest_line}'
    )

    config_issues = validate_config_semantics(cfg, current=cfg, perform_live_checks=False, base_dir=os.getcwd())
    config_buckets = split_issues(config_issues)
    config_errors = len(config_buckets.get("ERROR", []))
    config_warnings = len(config_buckets.get("WARNING", []))
    config_infos = len(config_buckets.get("INFO", []))
    if config_errors:
        config_status_value = badge(f"{config_errors} Fehler", "#f44336")
        config_status_details = "Bitte Settings öffnen und rot markierte Punkte korrigieren."
    elif config_warnings:
        config_status_value = badge(f"{config_warnings} Warnungen", "#f0ad00")
        config_status_details = "Konfiguration ist speicherbar, enthält aber prüfenswerte Kombinationen."
    else:
        config_status_value = badge("OK", "#4CAF50")
        config_status_details = f"Keine blockierenden Fehler. Hinweise: {config_infos}."

    local_api_mode = "deaktiviert"
    if cfg.get("ZENDURE_LOCAL_API_USE_FOR_TELEMETRY"):
        local_api_mode = "fallback-only" if cfg.get("ZENDURE_LOCAL_API_TELEMETRY_FALLBACK_ONLY", True) else "aktive Telemetriequelle"
    elif cfg.get("ZENDURE_LOCAL_API_ENABLED"):
        local_api_mode = "nur Diagnose"
    try:
        timing_obj = json.loads(str(s.get("last_cycle_timing_json") or "{}"))
    except Exception:
        timing_obj = {}
    try:
        timing_stats = json.loads(str(s.get("last_cycle_timing_stats_json") or "{}"))
    except Exception:
        timing_stats = {}
    local_api_ms = timing_obj.get("zendure_local_api_snapshot_apply_ms")
    local_api_details = (
        f"Modus: {html.escape(local_api_mode)}<br>"
        f"Snapshot-Übernahme im letzten Zyklus: {html.escape(str(local_api_ms if local_api_ms is not None else '-'))} ms<br>"
        f"Letzter Hintergrundrequest: {html.escape(str(s.get('zendure_local_api_last_request_duration_ms') if s.get('zendure_local_api_last_request_duration_ms') is not None else '-'))} ms<br>"
        f"Worker: {html.escape(str(s.get('zendure_local_api_worker_state') or 'DISABLED'))}<br>"
        f"Letzter Erfolg: {age_text(s.get('zendure_local_api_last_success_age_s'))}<br>"
        f"Fehlerfolge: {int(s.get('zendure_local_api_consecutive_errors') or 0)} · Backoff: {round(float(s.get('zendure_local_api_backoff_remaining_s') or 0), 1)} s<br>"
        f"Langsamster Teil letzter Zyklus: {html.escape(slowest_label)} {slowest_ms if slowest_label != '-' else '-'} ms"
    )

    sma_direct_enabled = bool(s.get("sma_energy_meter_enabled"))
    sma_direct_running = bool(s.get("sma_energy_meter_running"))
    sma_direct_age = s.get("sma_energy_meter_last_update_age_seconds")
    sma_direct_source = str(cfg.get("GRID_METER_SOURCE", "shelly_http") or "shelly_http")
    sma_direct_is_control = sma_direct_source == "sma_energy_meter_udp"
    if sma_direct_running and sma_direct_age is not None and int(sma_direct_age) <= int(cfg.get("SMA_ENERGY_METER_STALE_TIMEOUT_SECONDS", 15)):
        sma_direct_badge = badge("Aktuell", "#4CAF50")
    elif sma_direct_enabled:
        sma_direct_badge = badge("Wartet", "#f0ad00")
    else:
        sma_direct_badge = badge("Aus", "#888888")
    sma_direct_power = s.get("sma_energy_meter_power_w")
    sma_configured_serial = str(s.get("sma_energy_meter_configured_serial") or cfg.get("SMA_ENERGY_METER_SERIAL", "") or "")
    sma_configured_susy = str(s.get("sma_energy_meter_configured_susy_id") or cfg.get("SMA_ENERGY_METER_SUSY_ID", "") or "")
    sma_filter_line = ""
    if sma_configured_serial or sma_configured_susy:
        sma_filter_line = (
            f"Filter: SUSy {html.escape(sma_configured_susy or '-')} · Seriennr. {html.escape(sma_configured_serial or '-')}<br>"
            f"Ausgewählt: {html.escape(str(s.get('sma_energy_meter_serial_number') or '-'))} "
            f"/ SUSy {html.escape(str(s.get('sma_energy_meter_susy_id') or '-'))}<br>"
        )
    try:
        sma_devices = json.loads(str(s.get("sma_energy_meter_devices_json") or "{}"))
    except Exception:
        sma_devices = {}
    device_lines = []
    for _key, rec in sorted(sma_devices.items(), key=lambda item: str(item[0]))[:4]:
        device_age_text = "-"
        try:
            if rec.get("last_received_epoch") is not None:
                device_age_text = str(max(0, int(time.time() - float(rec.get("last_received_epoch"))))) + " s"
        except Exception:
            device_age_text = "-"
        device_lines.append(
            f"{html.escape(str(rec.get('serial_number') or '-'))}"
            f"/SUSy {html.escape(str(rec.get('susy_id') or '-'))}: "
            f"{html.escape(str(rec.get('last_power_w') if rec.get('last_power_w') is not None else '-'))} W "
            f"({device_age_text})"
        )
    devices_line = ""
    if device_lines:
        devices_line = "Geräte: " + " · ".join(device_lines) + "<br>"
    sma_control_line = (
        "ja, Listener automatisch aktiv" if sma_direct_is_control
        else "nein, nur zusätzliche passive Beobachtung"
    )
    sma_socket_line = (
        f"Socket: Modus {html.escape(str(s.get('sma_energy_meter_socket_mode') or cfg.get('SMA_ENERGY_METER_SOCKET_MODE', 'group_bind')))} "
        f"/ effektiv {html.escape(str(s.get('sma_energy_meter_effective_socket_mode') or '-'))} · "
        f"Bind {html.escape(str(s.get('sma_energy_meter_bind_address') or '-'))}:{html.escape(str(s.get('sma_energy_meter_port', 9522)))} "
        f"({html.escape(str(s.get('sma_energy_meter_bind_mode') or '-'))})<br>"
        f"Reuse: addr {html.escape('ja' if s.get('sma_energy_meter_reuseaddr_enabled') else 'nein')} · "
        f"port angefordert {html.escape('ja' if s.get('sma_energy_meter_reuseport_requested') else 'nein')} · "
        f"port aktiv {html.escape('ja' if s.get('sma_energy_meter_reuseport_enabled') else 'nein')} · "
        f"multicast_if {html.escape('ja' if s.get('sma_energy_meter_multicast_if_set') else 'nein')}<br>"
    )
    sma_gap_line = (
        f"Rate: {html.escape(str(s.get('sma_energy_meter_packet_rate_per_min', '-')))} Pakete/min · "
        f"letzte Lücke: {html.escape(str(s.get('sma_energy_meter_last_packet_gap_s') if s.get('sma_energy_meter_last_packet_gap_s') is not None else '-'))} s · "
        f"max. Lücke: {html.escape(str(s.get('sma_energy_meter_max_packet_gap_s') if s.get('sma_energy_meter_max_packet_gap_s') is not None else '-'))} s · "
        f"letzte große Lücke: {html.escape(str(s.get('sma_energy_meter_last_large_gap_s') if s.get('sma_energy_meter_last_large_gap_s') is not None else '-'))} s "
        f"(vor {html.escape(str(s.get('sma_energy_meter_last_large_gap_age_seconds') if s.get('sma_energy_meter_last_large_gap_age_seconds') is not None else '-'))} s)<br>"
    )
    sma_direct_details = (
        f"Regelquelle: {sma_control_line}<br>"
        f"Direktwert: {html.escape(str(round(float(sma_direct_power), 1)) + ' W') if sma_direct_power is not None else '-'}<br>"
        f"Alter: {html.escape(str(sma_direct_age if sma_direct_age is not None else '-'))} s · Pakete: {html.escape(str(s.get('sma_energy_meter_packet_count', 0)))} · dekodiert: {html.escape(str(s.get('sma_energy_meter_decode_count', 0)))} · ignoriert: {html.escape(str(s.get('sma_energy_meter_ignored_count', 0)))}<br>"
        f"Quelle: {html.escape(str(s.get('sma_energy_meter_group', '239.12.255.254')))}:{html.escape(str(s.get('sma_energy_meter_port', 9522)))} · Interface: {html.escape(str(s.get('sma_energy_meter_interface') or '-'))} → {html.escape(str(s.get('sma_energy_meter_resolved_interface_ip') or '-'))}<br>"
        f"{sma_socket_line}"
        f"{sma_gap_line}"
        f"{sma_filter_line}"
        f"Erkannte Geräte: {html.escape(str(s.get('sma_energy_meter_detected_device_count', 0)))}<br>"
        f"{devices_line}"
        f"Fehler: {html.escape(str(s.get('sma_energy_meter_last_error', 'none')))}"
    )

    measurement_log_details = (
        f"Status: {measurement_status}<br>"
        f"Aktives Ziel: {active_target} · konfiguriert: {configured_target}<br>"
        f"{path_block}<br>"
        f"Aufbewahrung: {html.escape(str(s.get('measurement_estimated_retention_hours') or estimate_retention_hours(cfg)))} h · "
        f"frei: {html.escape(str(s.get('measurement_free_disk_mb', '-')))} MB"
        f"{fallback_line}<br>"
        f"Grund: {measurement_reason}"
    )

    page = build_base_header("Zendure Energy Controller Status", refresh=True, cfg=cfg)
    page += f"""
    <div class="section">
        {section_title('Zendure Energy Controller Status', 1, True)}
        <div class="small" style="margin-bottom:14px;">
            Die obere Reihe zeigt die komprimierte Betriebsübersicht. Die Detailkarten darunter bleiben für Diagnose und Settings-Verlinkung erhalten.
        </div>
        <div class="dashboard-grid" style="margin-bottom:18px;">
            <div class="metric-card"><div class="metric-title">Netzleistung</div><div class="metric-value {grid_class}">{grid_main_value}</div><div class="metric-sub">{grid_status_line}<br>{grid_source_text}</div></div>
            <div class="metric-card"><div class="metric-title">Betriebsmodus</div><div class="metric-value">{badge(mode_label(current_mode), mode_color)}</div><div class="metric-sub">{html.escape(str(s["control_reason"]))}<br>Technisch: {html.escape(current_mode)}</div></div>
            <div class="metric-card"><div class="metric-title">Zendure</div><div class="metric-value blue">{s["battery_soc"] if s["battery_soc"] is not None else "-"} %</div><div class="metric-sub">Ziel {signed_power(zendure_setpoint_signed)} · Ist {signed_power(actual_system_signed)}<br>{html.escape(telemetry_source)}</div></div>
            <div class="metric-card"><div class="metric-title">Netzleistungsquelle</div><div class="metric-value">{sma_direct_badge}</div><div class="metric-sub">{html.escape(str(s.get("raw_grid_source") or "-"))}<br>Alter: {age_text(grid_age)}</div></div>
            <div class="metric-card"><div class="metric-title">Messdaten</div><div class="metric-value">{measurement_mode}</div><div class="metric-sub">{active_target}<br>{measurement_status}</div></div>
        </div>
        <div class="section-tools"><a href="#" onclick="expandSectionInfo('status-overview'); return false;">Detailinfos auf- und zuklappen</a></div>
        <div class="grid" id="status-overview">
            {status_card(
                'Netzleistung',
                grid_main_value,
                grid_details,
                grid_class,
                'Der Hauptwert ist der aktuelle Messwert der konfigurierten Netzleistungsquelle am Netzanschlusspunkt. AUTO-spezifische Diagnosewerte wie der geglättete Regelwert werden nur als Diagnose gezeigt und in festen Modi als nicht aktiv markiert. Feste Nachtentladung oder Stop/Hold hängen dadurch nicht von Grid-Daten ab, die Statusseite zeigt sie aber best-effort aktuell an.',
                settings_group='Regelung'
            )}
            {status_card(
                'Netzleistungsquelle',
                sma_direct_badge,
                sma_direct_details,
                'gray',
                'Zeigt die aktuell aktive Netzleistungsquelle. Bei SMA-Direktquelle werden Socket-Modus, Paketlücken und erkannte Geräte gezeigt; bei Shelly-kompatibler Quelle stehen HTTP-Quelle, Alter und Gültigkeit im Vordergrund. Der SMA-Listener ist bei SMA als Regelquelle automatisch aktiv.',
                settings_group='Netzwerk'
            )}
            {status_card(
                'Zendure SOC',
                f'{s["battery_soc"] if s["battery_soc"] is not None else "-"} %',
                soc_details,
                'blue',
                'Ladezustand der Zendure-Batterie. MQTT bleibt die bevorzugte Quelle. Wenn Zendure nach einem Broker- oder Raspberry-Neustart keine MQTT-Sensordaten sendet, kann die lokale Zendure-API als Fallback verwendet werden. Sobald MQTT wieder gültige Werte liefert, wechselt der Controller automatisch zurück zu MQTT.',
                settings_group='Sicherheit / Fallback'
            )}
            {status_card(
                'Zendure Systemleistung',
                f'Ziel {signed_power(zendure_setpoint_signed)}',
                f'Gemessene Istleistung: {actual_system_html}<br>'
                f'Angefordertes Lade-Limit: {s["last_input_power"]} W / Entlade-Limit: {s["last_output_power"]} W<br>'
                f'Letztes MQTT-Kommando: {last_command_html}<br>'
                f'Letztes unterdrücktes Kommando: {last_command_skipped_html}<br>'
                f'Darstellung: positiv = Ladung, negativ = Entladung'
                f'{setpoint_hint}',
                zendure_setpoint_class,
                'Diese Karte trennt den aktuellen Controller-Zielwert von der gemessenen Zendure-Istleistung und vom letzten MQTT-Kommando. Der Zielwert ist die interne Regleranforderung dieses Zyklus; die Istleistung zeigt, was die Zendure real tut. Bei HOLD/DEADBAND oder nach einem Service-Neustart können Zielwert und Istleistung kurz auseinanderlaufen, bis ein neues Kommando wirkt oder die Firmware nachregelt.',
                settings_group='Regelung'
            )}
            {status_card(
                'Betriebsmodus',
                badge(mode_label(current_mode), mode_color),
                f'Aktiv seit: {s["last_mode_change_time"]} ({format_hms(s["last_mode_duration_seconds"])})<br>'
                f'Gewählte Betriebsart: {html.escape(manual_mode_human)}<br>'
                f'Mögliche Betriebsarten: AUTO · STOP/HOLD · FEST LADEN · FEST ENTLADEN<br>'
                f'{html.escape(str(s["control_reason"]))}',
                'gray',
                'Zeigt den aktuellen Betriebszustand des Controllers. Die farbige Anzeige nutzt den verständlichen Modusnamen. Der technische Modus-Code bleibt darunter sichtbar, damit Graph-, CSV- und Eventdaten eindeutig zugeordnet werden können.',
                current_mode,
                settings_group='Regelung'
            )}
            {status_card(
                'Gewählte Betriebsart',
                badge(manual_mode_human, manual_mode_color),
                'AUTO = normale Regelung. STOP/HOLD und feste Lade-/Entlademodi übersteuern die Automatik.',
                'gray',
                'Die Betriebsart wird in den Settings gesetzt. Automatik bedeutet normale automatische Regelung. Stop/Hold setzt beide Leistungen auf 0 W. Feste Lade-/Entlademodi bleiben aktiv, bis der Ziel-SOC erreicht ist oder die Betriebsart geändert wird.',
                manual_mode_code,
                settings_group='Manueller Modus'
            )}
            {status_card(
                'Nachtmodus',
                badge(night_status_text, night_status_color),
                night_details,
                'gray',
                'Zeigt den Zustand der festen Nacht-Basisentladung. Wenn der Nachtmodus Reserve-SOC erreicht ist, wird nur diese feste Basisentladung pausiert; die normale AUTO-Regelung bleibt für Lastspitzen aktiv und darf bis zum globalen Mindest-SOC entladen.',
                settings_group='Nachtmodus'
            )}
            {status_card(
                'MQTT',
                badge('Verbunden' if s['mqtt_connected'] else 'Getrennt', mqtt_color),
                mqtt_details,
                'gray',
                'MQTT ist die Steuerverbindung zu Zendure. Zusätzlich wird bewertet, ob Zendure nach Broker-/Raspberry-Neustarts wirklich wieder frische nicht-retained Live-Daten liefert. Warnungen verschwinden automatisch, sobald kritische Zendure-Gruppen wieder live und frisch sind.',
                settings_group='Netzwerk'
            )}
            {evcc_status_card_html}
            {sma_card_html}
            {status_card(
                'Aktive Schutz- und Begrenzungslogik',
                html.escape(limiter_human),
                limiter_details,
                'gray',
                'Hier stehen aktive Schutz- oder Stabilitätsmechanismen. Beispiele: Totzone, Rampenbegrenzung, Mindest-SOC, Zusatzbatterie-Guard oder veraltete Daten. Keine aktiv bedeutet: Der aktuelle Regelzyklus wurde durch keinen dieser Mechanismen eingeschränkt.',
                limiter_technical,
                settings_group='Sicherheit / Fallback'
            )}
            {status_card(
                'Zendure Istleistung',
                'Interne Verteilung',
                pack_power_text,
                'gray',
                'Diese Karte zeigt die interne Leistungsaufteilung auf die erkannten Zendure-Akkupacks, sofern der Wert per MQTT oder lokaler API verfügbar ist. Die Vorzeichenlogik folgt der Systemdarstellung: positiv = Laden, negativ = Entladen. Im Nachtmodus bedeutet eine negative Pack-Zeile fachlich: Akkupack liefert Leistung an die Headunit; die Headunit speist anschließend ins Hausnetz ein.',
                settings_group='Netzwerk'
            )}
            {status_card(
                'Höchste Batterietemperatur',
                temp_value_text,
                temp_details,
                temp_value_class,
                'Zeigt die höchste aktuell bekannte Temperatur aus Headunit und Akkupacks. Grün bedeutet bis einschließlich 49 °C, gelb 50-55 °C, rot ab 56 °C. Für jede erkannte Batterie werden aktuelle Temperatur sowie Highest/Lowest seit Programmstart mit Zeitstempel angezeigt.',
                settings_group='Netzwerk'
            )}
            {status_card(
                'Konfigurationsstatus',
                config_status_value,
                config_status_details,
                'gray',
                'Der Konfigurationsstatus fasst die semantische Settings-Prüfung zusammen. Fehler blockieren sichere Funktionen oder Speichern; Warnungen markieren auffällige, aber bewusst nutzbare Kombinationen. Details stehen in den Settings.',
                settings_group='Regelung'
            )}
        </div>
    </div>
    {_legacy_soc_reference_box()}
    <div class="section">{heading_link('Diagnose', 'Sicherheit / Fallback', 2)}<div class="section-tools"><a href="#" onclick="expandSectionInfo('status-diagnostics'); return false;">Alle Infos auf- und zuklappen</a></div><div class="grid" id="status-diagnostics">
        {status_card('Aktive Betriebslogik', html.escape(path_human), html.escape(str(s['last_control_action'])), 'gray', 'Die aktive Betriebslogik beschreibt den aktuell verwendeten Entscheidungsweg des Controllers in verständlicher Form. Der technische Code bleibt darunter sichtbar, damit man Events, Graphdaten und Logausgaben eindeutig zuordnen kann.', path_code)}
        {status_card('Aktive Zykluszeit', f'{active_cycle_ms} ms', timing_details, 'gray', 'Die aktive Zykluszeit ist die Zeit, in der der Controller für einen Regelzyklus tatsächlich arbeitet: Datenquellen prüfen, Regelentscheidung berechnen, MQTT-Kommandopfad ausführen, Status aktualisieren und Messdaten schreiben. Nicht enthalten ist die geplante Wartezeit bis zum nächsten Regelintervall. Der langsamste Teil zeigt, welcher echte Abschnitt innerhalb des letzten Zyklus am meisten Zeit benötigt hat.')}
        {status_card('Zendure Local API Timing', html.escape(local_api_mode), local_api_details, 'gray', 'Die HTTP-Abfrage läuft asynchron. Der Regelzyklus übernimmt nur den neuesten unveränderlichen Snapshot und wartet nie auf Netzwerk-I/O.', settings_group='Netzwerk')}
        {status_card('Fehler', str(s['consecutive_errors']), f'Letzter Fehler: {html.escape(str(s["last_error"]))}<br>Zeitpunkt: {html.escape(str(s.get("last_error_time", "-")))}<br>Safe-State: {s["safe_state_counter"]}x', 'red', 'Der Fehlerzähler zählt direkt aufeinanderfolgende Fehler. Safe-State bedeutet: Lade- und Entladeleistung werden auf 0 W gesetzt, um bei unsicheren Daten oder Kommunikationsproblemen keine unkontrollierte Energieverschiebung auszulösen.')}
        {status_card('Messdaten-Logging', measurement_mode, measurement_log_details, 'gray', 'Messdaten-Logging ist optional und nachgelagert. Standard speichert vollständige Reglerdiagnose inklusive MQTT-Stale-Aggregat und Szenario ohne Zendure. Erweitert ergänzt große Detaildaten für Simulation, What-if und tiefe MQTT-/Freshness-Analyse. USB-/SD-Fallback-Details sind Betriebsdiagnose und werden im Runtime-Log dokumentiert; die Regelung läuft weiter, auch wenn Logging pausiert oder fehlschlägt.', settings_group='Messdaten / Historie')}
        {status_card('Analyse-Weboberfläche', f'Port {replay_port}', analysis_link_html, 'gray', 'Die Analyse läuft bewusst getrennt vom Live-Regler. Der Dienst wird mitgeliefert, aber nicht automatisch aktiviert.')}
        {status_card('High-SOC-Ladeannahme', html.escape(str(s.get('charge_acceptance_state', 'ok'))), html.escape(str(s.get('charge_acceptance_reason', '-'))), 'gray', 'Leichtgewichtige Diagnose: Zeigt, ob Zendure eine angeforderte Ladeleistung bei hohem SOC plausibel annimmt. Diese Diagnose greift nicht aktiv in die Regelung ein.')}
    </div></div>
    {_legacy_event_reference_box()}
    """
    page += build_footer()
    return page





def _ui_icon(name: str) -> str:
    """Return a small inline SVG icon for the modern dashboard.

    The UI deliberately uses a local SVG set instead of mixed unicode/emoji
    glyphs so the status and graph pages render consistently on Raspberry Pi
    OS, Windows, iOS and desktop browsers without external font assets.
    """
    icons = {
        "home": '<path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10.5V20h13v-9.5"/><path d="M9.5 20v-6h5v6"/>',
        "graph": '<path d="M4 18h16"/><path d="M6 15l4-4 3 3 5-7"/><path d="M14 7h4v4"/>',
        "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.04.04a2 2 0 1 1-2.83 2.83l-.04-.04A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6V20a2 2 0 1 1-4 0v-.06a1.7 1.7 0 0 0-1-.54 1.7 1.7 0 0 0-1.88.34l-.04.04a2 2 0 1 1-2.83-2.83l.04-.04A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-.6-1H4a2 2 0 1 1 0-4h.06a1.7 1.7 0 0 0 .54-1 1.7 1.7 0 0 0-.34-1.88l-.04-.04a2 2 0 1 1 2.83-2.83l.04.04A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-.6V4a2 2 0 1 1 4 0v.06a1.7 1.7 0 0 0 1 .54 1.7 1.7 0 0 0 1.88-.34l.04-.04a2 2 0 1 1 2.83 2.83l-.04.04A1.7 1.7 0 0 0 19.4 9c.23.32.44.66.6 1H20a2 2 0 1 1 0 4h-.06c-.14.35-.32.69-.54 1z"/>',
        "activity": '<path d="M3 12h4l2-6 4 12 2-6h6"/>',
        "mqtt": '<path d="M5 17a10 10 0 0 1 14 0"/><path d="M8 14a6 6 0 0 1 8 0"/><path d="M11 11a2 2 0 0 1 2 0"/><circle cx="12" cy="19" r="1"/>',
        "database": '<ellipse cx="12" cy="5" rx="7" ry="3"/><path d="M5 5v6c0 1.7 3.1 3 7 3s7-1.3 7-3V5"/><path d="M5 11v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"/>',
        "book": '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21z"/><path d="M4 5.5V21"/><path d="M8 7h8"/>',
        "bolt": '<path d="M13 2 4 14h7l-1 8 10-13h-7z"/>',
        "mode": '<path d="M4 12a8 8 0 0 1 13.7-5.7"/><path d="M18 4v5h-5"/><path d="M20 12a8 8 0 0 1-13.7 5.7"/><path d="M6 20v-5h5"/>',
        "battery": '<rect x="3" y="7" width="16" height="10" rx="2"/><path d="M21 11v2"/><path d="M7 11h6"/>',
        "meter": '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M8 15a4 4 0 0 1 8 0"/><path d="m12 14 3-3"/><path d="M8 8h.01M12 8h.01M16 8h.01"/>',
        "list": '<path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/>',
        "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
        "cpu": '<rect x="7" y="7" width="10" height="10" rx="2"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M1 9h3M1 15h3M20 9h3M20 15h3"/>',
        "memory": '<rect x="4" y="7" width="16" height="10" rx="2"/><path d="M8 7V4M12 7V4M16 7V4M8 20v-3M12 20v-3M16 20v-3"/>',
        "radio": '<circle cx="12" cy="12" r="2"/><path d="M16.2 7.8a6 6 0 0 1 0 8.4"/><path d="M7.8 7.8a6 6 0 0 0 0 8.4"/><path d="M19 5a10 10 0 0 1 0 14"/><path d="M5 5a10 10 0 0 0 0 14"/>',
        "server": '<rect x="4" y="4" width="16" height="6" rx="2"/><rect x="4" y="14" width="16" height="6" rx="2"/><path d="M8 7h.01M8 17h.01"/>',
        "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>',
    }
    body = icons.get(str(name), icons["activity"])
    return f'<svg class="zec-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">{body}</svg>'


def _shared_topbar_live_script() -> str:
    """Live status binding for pages using the shared shell without status_v2.js."""
    return """<script>
    (() => {
      'use strict';
      const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
      function apply(payload) {
        const system = payload && payload.system ? payload.system : {};
        const kind = system.kind || 'unknown';
        const button = document.getElementById('systemStatusButton');
        if (button) {
          button.className = `zec-system-pill ${kind}`;
          button.setAttribute('aria-expanded', 'false');
        }
        const label = document.querySelector('[data-zec="system.label"]');
        if (label) label.textContent = system.label || 'Systemstatus';
        const dot = document.getElementById('globalStatusNavDot');
        if (dot) {
          dot.className = `zec-nav-live-dot ${kind}`;
          dot.setAttribute('aria-label', `Aktueller Systemstatus: ${kind}`);
        }
        const list = document.getElementById('systemWarningList');
        if (list) {
          const warnings = Array.isArray(system.warnings) ? system.warnings : [];
          list.innerHTML = (warnings.length ? warnings : ['Keine aktiven Warnungen oder Fehler.']).map(x => `<li>${esc(x)}</li>`).join('');
        }
        if (payload && payload.server_time) document.querySelectorAll('[data-zec="server_time"]').forEach(el => { el.textContent = payload.server_time; });
      }
      function bind() {
        const button = document.getElementById('systemStatusButton');
        const menu = document.getElementById('systemStatusMenu');
        if (button && menu) {
          button.addEventListener('click', event => {
            event.stopPropagation();
            const opening = menu.hidden;
            menu.hidden = !opening;
            button.setAttribute('aria-expanded', String(opening));
          });
          document.addEventListener('click', event => {
            if (!menu.hidden && !event.target.closest('.zec-system-menu-wrap')) {
              menu.hidden = true;
              button.setAttribute('aria-expanded', 'false');
            }
          });
        }
        document.querySelectorAll('.analysis-service-link').forEach(link => link.addEventListener('click', event => {
          event.preventDefault();
          const port = Number(link.dataset.replayPort || 8090);
          window.location.href = `${window.location.protocol}//${window.location.hostname}:${port}/`;
        }));
        const clock = document.getElementById('localClock');
        if (clock) setInterval(() => { clock.textContent = new Date().toLocaleTimeString('de-DE', {hour:'2-digit', minute:'2-digit', second:'2-digit'}); }, 1000);
      }
      let inFlight = false;
      async function refresh() {
        if (document.visibilityState === 'hidden' || inFlight) return;
        inFlight = true;
        try {
          const response = await fetch('/status-view-data', {cache:'no-store'});
          if (response.ok) apply(await response.json());
        } catch (_) {} finally { inFlight = false; }
      }
      document.addEventListener('DOMContentLoaded', () => { bind(); refresh(); setInterval(refresh, 3000); });
      document.addEventListener('visibilitychange', () => { if (document.visibilityState !== 'hidden') refresh(); });
    })();
    </script>"""


def _modern_body_start(
    cfg: Dict[str, Any],
    active: str,
    force_dark: bool = False,
    *,
    system_payload: Optional[Dict[str, Any]] = None,
    server_time: str = "",
) -> str:
    cfg2 = dict(cfg or {})
    cfg2["__hide_nav"] = True
    dark = bool(force_dark or cfg2.get("UI_DARK_MODE", False))
    theme_class = "modern-dark" if dark else "modern-light"
    base = build_base_header("Zendure Energy Controller", cfg=cfg2)
    theme = "dark" if dark else "light"
    base = base.replace("<html>", f'<html data-theme="{theme}">', 1)
    base = base.replace(
        "</head>",
        f'<link rel="stylesheet" href="/static/status_v2.css?v={html.escape(APP_VERSION_LABEL)}">'
        "</head>",
        1,
    )
    topbar = render_global_topbar(
        active=active,
        analysis_available=replay_service_available(cfg or {}),
        analysis_port=int((cfg or {}).get("REPLAY_WEB_PORT", 8090) or 8090),
        system=system_payload,
        server_time=server_time or datetime.now().strftime("%H:%M:%S"),
    )
    shell_css = """<style>
      body.zec-modern-body .container{max-width:none!important;width:100%!important;padding:0 22px 28px!important}
      body.zec-modern-body .container>.zec-topbar{margin:0 -22px 22px!important}
      @media(max-width:760px){body.zec-modern-body .container{width:100%!important;padding:0 10px 20px!important}body.zec-modern-body .container>.zec-topbar{margin:0 -10px 16px!important}}
    </style>"""
    return (
        base
        + f'<script>document.body.classList.add("zec-modern-body","{theme_class}","zec-shared-shell");</script>'
        + shell_css
        + topbar
        + _shared_topbar_live_script()
    )


def _modern_topbar(active: str, cfg: Dict[str, Any]) -> str:
    port = int(cfg.get("REPLAY_WEB_PORT", 8090) or 8090)
    replay_ok = replay_service_available(cfg)
    active = active or "status"
    def nav(href: str, label: str, icon: str, key: str) -> str:
        cls = " active" if key == active else ""
        return f'<a class="{cls}" href="{href}">{_ui_icon(icon)}<span>{html.escape(label)}</span></a>'
    analysis_dot = '<span class="status-dot ok"></span>' if replay_ok else '<span class="status-dot warn"></span>'
    return f'''
    <span class="modern-page" style="display:none"></span><div class="zec-topbar">
      <div class="zec-brand"><div class="zec-logo" aria-label="ZENDURE" title="ZENDURE"><span>ZEN</span><span class="logo-d">D</span><span>URE</span></div><div class="zec-brand-sub">Energy Controller</div></div>
      <nav class="zec-nav-modern">
        {nav('/', 'Status', 'home', 'status')}
        {nav('/graph', 'Graph', 'graph', 'graph')}
        {nav('/settings', 'Settings', 'settings', 'settings')}
        <a href="#" class="analysis-service-link" data-replay-port="{port}" title="Analyse-/Replay-Service öffnen">{analysis_dot}{_ui_icon("activity")}<span>Analyse-Service</span></a>
        {nav('/mqtt-diagnostics', 'MQTT Diagnose', 'mqtt', 'mqtt')}
        {nav('/measurements', 'Messdaten-CSV', 'database', 'measurements')}
        {nav('/manual.pdf', 'Handbuch', 'book', 'manual')}
        <span class="zec-dropdown"><button type="button" onclick="this.parentElement.classList.toggle('open')">Experte ▾</button><span class="zec-dropdown-panel"><a href="/status_old">Alte Statusseite</a><a href="/graph_old">Alter Graph</a><a href="/status#modern-diagnostics">Moderne Diagnose</a></span></span>
      </nav>
      <div class="zec-top-actions"><button type="button" id="systemPill" class="zec-system-pill ok" aria-label="Systemstatus">System OK</button><span class="modern-pill">V{APP_VERSION}</span><span class="zec-clock" id="zecClock">--:--:--</span></div>
    </div>
    <script>
      (function(){{
        function tick(){{ try {{ document.getElementById('zecClock').textContent = new Date().toLocaleTimeString('de-DE'); }} catch(e) {{}} }}
        tick(); setInterval(tick, 1000);
        document.addEventListener('click', function(e){{ if(!e.target.closest('.zec-dropdown')) document.querySelectorAll('.zec-dropdown.open').forEach(function(x){{x.classList.remove('open')}}); }});
      }})();
    </script>
    '''


def _short_source_name(raw: Any) -> str:
    txt = str(raw or "-")
    if "SMA" in txt.upper():
        return "SMA Home Manager direkt"
    if "shelly" in txt.lower():
        return "Shelly-kompatibel"
    return txt


def _modern_class_for_signed_power(value: Any, positive_good: bool = False) -> str:
    try:
        v = float(value or 0)
    except Exception:
        v = 0.0
    if abs(v) < 0.1:
        return "blue"
    if positive_good:
        return "green" if v > 0 else "red"
    return "red" if v > 0 else "green"


def _modern_badge(text: str, kind: str = "ok") -> str:
    kind = kind if kind in {"ok", "warn", "bad"} else "ok"
    return f'<span class="modern-pill {kind}">{html.escape(str(text))}</span>'


def _mini_svg_sparkline(values: List[Any], stroke: str = "#2ca24d", width: int = 260, height: int = 86) -> str:
    """Return a compact real mini chart with axes/scale hints.

    RC14 policy: mini graphs are only useful when they include a scale.  The
    widget therefore renders min/max/current labels, axes and a zero reference
    line when the visible range crosses zero.  If no meaningful history exists,
    it renders a textual fallback instead of a decorative trend.
    """
    nums: List[float] = []
    for v in values or []:
        try:
            if v is None:
                continue
            nums.append(float(v))
        except Exception:
            continue
    if len(nums) < 2:
        return '<div class="zec-card-sub">keine Verlaufshistorie verfügbar</div>'
    nums = nums[-48:]
    lo, hi = min(nums), max(nums)
    if abs(hi - lo) < 0.001:
        hi = lo + 1.0
    max_abs = max(abs(lo), abs(hi), abs(nums[-1]))
    def fmt(v: float) -> str:
        if max_abs >= 1000:
            return f"{v/1000:+.1f} kW"
        return f"{v:+.0f} W"
    left = 30
    right = 8
    top = 14
    bottom = 20
    plot_w = width - left - right
    plot_h = height - top - bottom
    pts = []
    n = len(nums)
    for i, val in enumerate(nums):
        x = left + plot_w * (i / max(1, n - 1))
        y = top + plot_h * (1.0 - ((val - lo) / (hi - lo)))
        pts.append(f"{x:.1f},{y:.1f}")
    zero_line = ""
    if lo < 0 < hi:
        zy = top + plot_h * (1.0 - ((0.0 - lo) / (hi - lo)))
        zero_line = f'<line class="mini-zero" x1="{left}" y1="{zy:.1f}" x2="{width-right}" y2="{zy:.1f}"/>'
    points_attr = " ".join(pts)
    last_x, last_y = pts[-1].split(',')
    hit_targets = []
    for i, (pt, value) in enumerate(zip(pts, nums)):
        x, y = pt.split(',')
        seconds_ago = (len(nums) - 1 - i) * 3
        status = 'Bezug aus Netz' if value > 50 else ('Einspeisung / Export' if value < -50 else 'ausgeglichen')
        hit_targets.append(f'<circle cx="{x}" cy="{y}" r="6" fill="transparent" tabindex="0"><title>vor ca. {seconds_ago} s · {html.escape(fmt(value))} · {status}</title></circle>')
    hit_targets_html = ''.join(hit_targets)
    return (
        f'<svg class="sparkline" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Mini-Verlauf: Minimum {html.escape(fmt(lo))}, Maximum {html.escape(fmt(hi))}, aktuell {html.escape(fmt(nums[-1]))}">'
        f'<line class="mini-grid" x1="{left}" y1="{top}" x2="{width-right}" y2="{top}"/>'
        f'<line class="mini-grid" x1="{left}" y1="{top + plot_h/2:.1f}" x2="{width-right}" y2="{top + plot_h/2:.1f}"/>'
        f'<line class="mini-axis" x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}"/>'
        f'<line class="mini-axis" x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}"/>'
        f'{zero_line}'
        f'<polyline class="mini-line" points="{points_attr}" stroke="{html.escape(stroke)}"/>'
        f'<circle class="mini-dot" cx="{last_x}" cy="{last_y}" r="3" stroke="{html.escape(stroke)}"/>' f'{hit_targets_html}'
        f'<text class="mini-label" x="0" y="{top+3}">{html.escape(fmt(hi))}</text>'
        f'<text class="mini-label" x="0" y="{height-bottom+3}">{html.escape(fmt(lo))}</text>'
        f'<text class="mini-label" x="{left}" y="{height-4}">letzte 48 Punkte</text>'
        f'<text class="mini-label" text-anchor="end" x="{width-right}" y="{height-4}">aktuell {html.escape(fmt(nums[-1]))}</text>'
        f'</svg>'
    )


def _modern_status_summary(cfg: Dict[str, Any], s: Dict[str, Any]) -> Dict[str, Any]:
    current_mode = str(s.get("current_mode") or "-")
    grid = float(s.get("raw_grid_power", s.get("grid_power", 0.0)) or 0.0)
    grid_valid = bool(s.get("grid_power_valid", False))
    grid_used = bool(s.get("grid_power_used_for_control", False))
    soc = s.get("battery_soc")
    target = int(s.get("last_input_power", 0) or 0)
    if int(s.get("last_output_power", 0) or 0) > 0:
        target = -int(s.get("last_output_power", 0) or 0)
    actual = int(s.get("zendure_system_signed_power", 0) or 0)
    mqtt_ok = bool(s.get("mqtt_connected", False)) and str(s.get("zendure_mqtt_overall_status", "")) == "ZENDURE_MQTT_OK"
    logging_status = str(s.get("measurement_log_status") or "-")
    logging_mode = str(cfg.get("MEASUREMENT_LOG_MODE", "off") or "off")
    db_status = str(s.get("measurement_db_status") or ("disabled" if not cfg.get("MEASUREMENT_DB_ENABLED", True) else "idle"))
    safe_count = int(s.get("safe_state_counter", 0) or 0)
    errors = int(s.get("consecutive_errors", 0) or 0)
    return {
        "mode": current_mode,
        "mode_label": mode_label(current_mode),
        "grid": grid,
        "grid_valid": grid_valid,
        "grid_used": grid_used,
        "soc": soc,
        "target": target,
        "actual": actual,
        "mqtt_ok": mqtt_ok,
        "logging_status": logging_status,
        "logging_mode": logging_mode,
        "db_status": db_status,
        "safe_count": safe_count,
        "errors": errors,
    }


def build_modern_soc_day_section(cfg: Dict[str, Any]) -> str:
    if not cfg.get("SOC_DAY_GRAPH_ENABLED", True):
        return ""
    return """
      <div class="zec-panel zec-panel-lg zec-soc-card">
        <div class="zec-panel-header">
          <div><h2>Zendure SOC heute</h2><div class="zec-panel-desc">Feste Tagesachse 00:00–24:00. Fehlende oder ungültige SOC-Daten bleiben als Lücke sichtbar.</div></div>
          <span class="zec-status-badge">1-Minuten-Sampling</span>
        </div>
        <canvas id="socDayChart" height="275"></canvas>
        <div id="socDayStatus" class="zec-panel-desc">lädt…</div>
      </div>
      <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
      <script>
      (function() {
        async function loadSocDay() {
          const status = document.getElementById('socDayStatus');
          try {
            const ctrl = new AbortController();
            const timer = setTimeout(function(){ ctrl.abort(); }, 15000);
            status.textContent = 'SOC-Daten werden geladen…';
            const res = await fetch('/soc-day-data', {signal: ctrl.signal, cache:'no-store'});
            clearTimeout(timer);
            const payload = await res.json();
            const points = payload.points || [];
            const data = points.map(function(p) {
              const x = (p.minute_of_day !== undefined && p.minute_of_day !== null) ? Number(p.minute_of_day) / 60.0 : null;
              return {x:x, y:p.soc, src:p.source || '-', mode:p.mode || '-', valid:p.valid, status:p.status || '-'};
            }).filter(function(p) { return p.x !== null && p.y !== null && p.valid !== false; });
            const ctx = document.getElementById('socDayChart').getContext('2d');
            const isLight = document.body.classList.contains('modern-light');
            const socLine = isLight ? '#2f9747' : '#38bdf8';
            const axisColor = isLight ? '#334155' : '#8191a6';
            const gridColor = isLight ? 'rgba(148,163,184,.26)' : 'rgba(148,163,184,.10)';
            new Chart(ctx, {
              type:'line',
              data:{datasets:[{label:'SOC (%)', data:data, parsing:false, borderColor:socLine, backgroundColor:isLight?'rgba(47,151,71,.12)':'rgba(56,189,248,.16)', fill:false, tension:.25, borderWidth:2.8, pointRadius:0, pointHitRadius:18, pointHoverRadius:4, spanGaps:false}]},
              options:{
                animation:false, responsive:true, maintainAspectRatio:false,
                interaction:{mode:'nearest', axis:'x', intersect:false},
                plugins:{ legend:{position:'bottom', labels:{color:axisColor, boxWidth:34}}, tooltip:{mode:'nearest', intersect:false, backgroundColor:isLight?'rgba(255,255,255,.98)':'rgba(8,18,31,.95)', titleColor:isLight?'#111827':'#fff', bodyColor:isLight?'#111827':'#e5e7eb', borderColor:isLight?'#d1d5db':'rgba(148,163,184,.24)', borderWidth:1, callbacks:{ title:function(items){ const h=Math.floor(items[0].raw.x); const m=Math.round((items[0].raw.x-h)*60); return String(h).padStart(2,'0')+':'+String(m).padStart(2,'0'); }, afterBody:function(items){ const p=items[0].raw; return ['Quelle: '+p.src, 'Betriebsmodus: '+p.mode, 'Datenstatus: '+p.status]; }}}},
                scales:{ x:{type:'linear', min:0, max:24, ticks:{color:axisColor, stepSize:2, callback:function(v){ return String(Math.floor(v)).padStart(2,'0')+':00'; }} , grid:{color:gridColor, borderDash:[4,4]}, title:{display:true,text:'Uhrzeit',color:axisColor}}, y:{min:0,max:100,ticks:{color:axisColor}, grid:{color:gridColor, borderDash:[4,4]}, title:{display:true,text:'SOC (%)',color:axisColor}} }
              }
            });
            status.textContent = 'Punkte: ' + points.length + ' · Quelle: ' + (payload.source || '-') + ' · Cache ' + Math.round(payload.cache_age_s || 0) + ' s · ' + (payload.cache_status || '-');
          } catch(e) { status.textContent = (e && e.name === 'AbortError') ? 'SOC-Tageskurve wird noch vorbereitet. Bitte in einigen Sekunden erneut laden.' : ('SOC-Tageskurve konnte nicht geladen werden: ' + e); }
        }
        if (window.Chart) loadSocDay(); else document.getElementById('socDayStatus').textContent='Chart.js konnte nicht geladen werden.';
      })();
      </script>
    """




def _zec_num(value: Any, unit: str = "W", signed: bool = False, decimals: Optional[int] = None) -> str:
    if value in (None, ""):
        return "—"
    try:
        n = float(value)
    except Exception:
        return html.escape(str(value))
    sign = "+" if signed and n > 0 else ("−" if signed and n < 0 else "")
    a = abs(n)
    if unit == "%":
        return f"{sign}{a:.0f} %".replace(".", ",")
    if unit == "kWh":
        return f"{sign}{a:.2f} kWh".replace(".", ",")
    if unit == "W":
        if a >= 1_000_000:
            text = f"{a/1_000_000:.2f} MW"
        elif a >= 1000:
            if decimals is None:
                decimals = 2 if a < 10000 else 1
            text = f"{a/1000:.{decimals}f} kW"
        else:
            text = f"{a:.0f} W"
        return (sign + text).replace(".", ",")
    return (sign + f"{a:.0f} {unit}").replace(".", ",")


def _soc_color_class(soc: Any, cfg: Dict[str, Any]) -> str:
    val = _safe_float(soc)
    if val is None:
        return "unknown"
    min_soc = _safe_float(cfg.get("MIN_SOC_PERCENT")) or 15
    max_soc = _safe_float(cfg.get("MAX_SOC_PERCENT")) or 99
    if val <= min_soc + 2 or val >= max_soc - 1:
        return "warn"
    return "ok"


def _signed_power_phrase(value: Any, neutral: str = "neutral") -> str:
    v = _safe_float(value)
    if v is None:
        return "nicht verfügbar"
    if v > 30:
        return f"{_zec_num(v, signed=True)} Laden"
    if v < -30:
        return f"{_zec_num(v, signed=True)} Entladen"
    return f"0 W {neutral}"


def _mode_public_text(mode: str, target: Any) -> str:
    mode = str(mode or "-")
    if mode in {"AUTO_CHARGE", "CHARGE"}:
        return "Zendure lädt"
    if mode in {"AUTO_DISCHARGE", "DISCHARGE"}:
        return "Zendure entlädt"
    if mode in {"NIGHT_DISCHARGE"}:
        return "Feste Nachtentladung aktiv"
    if mode in {"MANUAL_FIXED_CHARGE", "FIXED_CHARGE"}:
        return "Feste Ladung aktiv"
    if mode in {"MANUAL_FIXED_DISCHARGE", "FIXED_DISCHARGE"}:
        return "Feste Entladung aktiv"
    if mode in {"SAFE_STATE"}:
        return "Schutzmodus aktiv"
    if mode in {"STOP_HOLD"}:
        return "Regelung hält neutral"
    if abs(_safe_float(target) or 0) <= 30:
        return "Zielbereich erreicht"
    return mode_label(mode)


def _technical_path_tokens(path: Any) -> set[str]:
    """Return exact technical-control-path tokens.

    Status text must never classify ``DISCHARGE`` as ``CHARGE`` or
    ``STOP_HOLD`` as ``HOLD`` merely because one word contains the other.
    """
    return {
        token.strip().upper()
        for token in str(path or "").split("->")
        if token.strip()
    }


def _power_limit_public_text(reason: Any) -> str:
    mapping = {
        "CONFIG_MAX_CHARGE_POWER": "Globales Ladelimit",
        "CONFIG_MAX_DISCHARGE_POWER": "Globales Entladelimit",
        "ZENDURE_DEVICE_CHARGE_MAX_LIMIT": "Zendure-Gerätecap chargeMaxLimit",
        "ZENDURE_DEVICE_INVERSE_MAX_POWER": "Zendure-Gerätecap inverseMaxPower",
        "ZENDURE_DEVICE_CHARGE_LIMIT": "Zendure-Gerätecap Laden",
        "ZENDURE_DEVICE_DISCHARGE_LIMIT": "Zendure-Gerätecap Entladen",
    }
    text = str(reason or "NONE").strip().upper()
    if text in {"", "NONE"}:
        return ""
    return mapping.get(text, text.replace("_", " ").title())


def _reason_public_text(s: Dict[str, Any]) -> str:
    reason = str(s.get("control_reason") or s.get("target_final_reason") or "")
    path = str(s.get("technical_control_path") or "")
    path_tokens = _technical_path_tokens(path)
    harvest = str(s.get("rest_surplus_harvest_reason") or "")
    mode = str(s.get("current_mode") or "")
    intent = str(s.get("command_desired_intent") or "").upper()
    if mode == "NIGHT_DISCHARGE":
        return "Nachtfenster aktiv"
    if mode in {"MANUAL_FIXED_CHARGE", "FIXED_CHARGE", "MANUAL_FIXED_DISCHARGE", "FIXED_DISCHARGE"}:
        return "Manueller fester Modus"
    if mode == "STOP_HOLD":
        return "Manueller Stopp – Zendure bleibt neutral"
    if mode == "SAFE_STATE":
        return str(s.get("control_reason") or "Schutzmodus aktiv")
    if "REST_SURPLUS" in reason or "REST_SURPLUS_HARVEST" in path_tokens or (harvest not in {"", "NONE"} and mode.startswith("AUTO")):
        return "Restüberschuss wird gespeichert"
    if "CROSS_CHARGE" in reason or "CROSS_CHARGE" in path_tokens or "CROSS_CHARGE" in str(s.get("active_limiters") or ""):
        return "Batterie-zu-Batterie-Umladung wird begrenzt"
    if "GRID_EXPORT" in reason or intent == "CHARGE" or mode in {"CHARGE", "AUTO_CHARGE"} or "CHARGE_CONTROL" in path_tokens:
        return "Einspeisung wird reduziert"
    if "GRID_IMPORT" in reason or intent == "DISCHARGE" or mode in {"DISCHARGE", "AUTO_DISCHARGE"} or "DISCHARGE_CONTROL" in path_tokens:
        return "Netzbezug wird reduziert"
    if "NIGHT" in reason:
        return "Nachtfenster aktiv"
    if "MAX_SOC" in reason:
        return "Oberes SOC-Limit erreicht"
    if "MIN_SOC" in reason:
        return "Unteres SOC-Limit erreicht"
    if "DEADBAND" in reason or mode in {"HOLD", "HOLD_DEADBAND"} or "HOLD" in path_tokens:
        return "Netzleistung nahe 0 W"
    return reason or "Regelentscheidung aktiv"


def _storage_source_text(s: Dict[str, Any]) -> str:
    mqtt = str(s.get("zendure_mqtt_overall_status") or "")
    api_active = bool(s.get("zendure_local_api_fallback_active")) or str(s.get("zendure_telemetry_source") or "").lower().find("api") >= 0
    if api_active and mqtt == "ZENDURE_MQTT_OK":
        return "API + MQTT · aktuell"
    if api_active:
        return "lokale API · aktuell"
    if mqtt == "ZENDURE_MQTT_OK":
        return "MQTT · aktuell"
    if mqtt:
        return "MQTT · eingeschränkt"
    return "Telemetrie nicht verfügbar"


def _soc_ring_html(label: str, soc: Any, cfg: Dict[str, Any], subtitle: str = "") -> str:
    safe_soc = _safe_float(soc)
    val = max(0, min(100, safe_soc if safe_soc is not None else 0))
    cls = _soc_color_class(soc, cfg)
    return f'''<div class="soc-ring-wrap {cls}" title="{html.escape(label)}">
      <div class="soc-ring" data-ring="{html.escape(label.lower())}" style="--soc:{val:.1f}"><div class="soc-ring-inner"><b class="soc-ring-value">{_zec_num(soc, '%')}</b><span>{html.escape(label)}</span></div></div>
      <div class="soc-ring-caption">{html.escape(subtitle)}</div>
    </div>'''


def _status_event_time(value: Any) -> str:
    text = str(value or "").strip()
    if not text or text == "-":
        return "-"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d.%m.%Y %H:%M:%S", "%H:%M:%S"):
        try:
            dt = datetime.strptime(text[:19], fmt)
            if fmt == "%H:%M:%S":
                return text[:8]
            if dt.date() == datetime.now().date():
                return dt.strftime("heute %H:%M")
            return dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            pass
    return text


def _status_unit_state(actual: Any, target: Any, soc: Any, cfg: Dict[str, Any]) -> str:
    actual_f = _safe_float(actual)
    target_f = _safe_float(target)
    soc_f = _safe_float(soc)
    max_soc = _safe_float(cfg.get("MAX_SOC_PERCENT")) or 99
    min_soc = _safe_float(cfg.get("MIN_SOC_PERCENT")) or 15
    if soc_f is not None and soc_f >= max_soc:
        return "voll"
    if soc_f is not None and soc_f <= min_soc:
        return "Min-SOC erreicht"
    if actual_f is not None and actual_f > 50:
        return "lädt"
    if actual_f is not None and actual_f < -50:
        return "entlädt"
    if target_f is not None and target_f > 50:
        return "hält / Ladeziel noch nicht wirksam"
    if target_f is not None and target_f < -50:
        return "hält / Entladeziel noch nicht wirksam"
    return "neutral"


def _status_unit_tone(soc: Any, cfg: Dict[str, Any], *, valid: bool = True) -> str:
    if not valid or _safe_float(soc) is None:
        return "unknown"
    return "warn" if _soc_color_class(soc, cfg) == "warn" else "ok"


def _status_units(cfg: Dict[str, Any], s: Dict[str, Any], target: Any, actual: Any) -> List[Dict[str, Any]]:
    raw_units = s.get("zendure_units_json")
    parsed: List[Dict[str, Any]] = []
    if isinstance(raw_units, list):
        parsed = [x for x in raw_units if isinstance(x, dict)]
    elif raw_units:
        try:
            obj = json.loads(str(raw_units))
            if isinstance(obj, list):
                parsed = [x for x in obj if isinstance(x, dict)]
        except Exception:
            parsed = []
    if not parsed:
        parsed = [{
            "unit_id": "primary",
            "soc_percent": _first_snapshot_value(s, "battery_soc", "zendure_soc_percent", "norm_zendure_soc_percent", "raw_zendure_soc_percent", "soc"),
            "actual_power_w": actual,
            "target_w": target,
            "freshness": s.get("zendure_mqtt_overall_status"),
            "command_path_valid": s.get("mqtt_command_path_valid", True),
            "capacity_kwh": (_safe_float(cfg.get("ZENDURE_BATTERY_CAPACITY_WH")) or 0) / 1000.0 or None,
        }]
    units: List[Dict[str, Any]] = []
    for idx, unit in enumerate(parsed[:2]):
        soc = next((unit.get(k) for k in ("soc_percent", "soc", "battery_soc") if unit.get(k) not in (None, "", "-")), None)
        actual_w = next((unit.get(k) for k in ("actual_power_w", "actual_w", "signed_power_w") if unit.get(k) not in (None, "", "-")), None)
        target_w = next((unit.get(k) for k in ("target_w", "target_power_w") if unit.get(k) not in (None, "", "-")), None)
        capacity = _safe_float(unit.get("capacity_kwh"))
        if capacity is None and idx == 0:
            cap_wh = _safe_float(cfg.get("ZENDURE_BATTERY_CAPACITY_WH"))
            capacity = cap_wh / 1000.0 if cap_wh else None
        energy = capacity * float(soc) / 100.0 if capacity is not None and _safe_float(soc) is not None else None
        state_text = _status_unit_state(actual_w, target_w, soc, cfg)
        technical_state = str(unit.get("execution_state") or unit.get("state") or "")
        if technical_state and technical_state not in {"AUTO", "AUTO_CHARGE", "AUTO_DISCHARGE"}:
            state_text = f"{technical_state} ({state_text})"
        detail_parts = [_zec_num(soc, "%")]
        if energy is not None and capacity is not None:
            detail_parts.append(f"{_zec_num(energy, 'kWh')} von {_zec_num(capacity, 'kWh')}")
        detail_parts.append(_signed_power_phrase(actual_w))
        if state_text not in {"lädt", "entlädt", "neutral"}:
            detail_parts.append(state_text)
        units.append({
            "id": str(unit.get("unit_id") or f"unit-{idx+1}"),
            "name": str(unit.get("name") or f"Unit {idx+1}"),
            "soc": soc,
            "actual_w": actual_w,
            "target_w": target_w,
            "state_text": state_text,
            "detail": " · ".join(x for x in detail_parts if x and x != "nicht verfügbar"),
            "tone": _status_unit_tone(soc, cfg, valid=_safe_float(soc) is not None),
            "capacity_kwh": capacity,
            "energy_kwh": energy,
        })
    return units


def _zendure_mqtt_public_status(value: Any) -> tuple[str, str]:
    raw = str(value or "").strip().upper()
    mapping = {
        "ZENDURE_MQTT_OK": ("Aktuell", "ok"),
        "ZENDURE_MQTT_PARTIAL_STALE": ("Teilweise veraltet", "warn"),
        "ZENDURE_MQTT_STALE": ("Veraltet", "bad"),
        "ZENDURE_MQTT_RETAINED_ONLY": ("Nur gespeicherte MQTT-Daten", "warn"),
        "ZENDURE_MQTT_AFTER_BROKER_RESTART_NO_LIVE_UPDATES": ("Keine bestätigten Live-Daten", "bad"),
    }
    if raw in mapping:
        return mapping[raw]
    if not raw:
        return "Noch keine Daten", "unknown"
    return "Status unbekannt", "unknown"


def _command_effect_public_status(value: Any) -> tuple[str, str]:
    raw = str(value or "").strip().lower()
    mapping = {
        "no_command": ("Noch kein relevantes Kommando", "ok"),
        "none": ("Noch kein relevantes Kommando", "ok"),
        "command_idle": ("Noch kein relevantes Kommando", "ok"),
        "effective": ("Sollwerttracking bestätigt", "ok"),
        "confirmed": ("Sollwerttracking bestätigt", "ok"),
        "command_target_tracking_effective": ("Sollwerttracking bestätigt", "ok"),
        "command_neutralization_confirmed": ("Neutralisierung bestätigt", "ok"),
        "command_below_diagnostic_threshold": ("Wirkung unter Diagnosegrenze", "unknown"),
        "pending": ("Wirkung wird geprüft", "warn"),
        "checking": ("Wirkung wird geprüft", "warn"),
        "command_pending": ("Richtungsreaktion wird geprüft", "warn"),
        "command_neutralization_pending": ("Neutralisierung wird geprüft", "warn"),
        "command_partially_effective": ("Teilwirkung · Tracking unzureichend", "warn"),
        "command_recovery_verifying": ("Kommandoabgleich ausgeführt · Wirkung offen", "warn"),
        "command_state_verifying": ("Flash-Schutz/Command-State wird geprüft", "warn"),
        "command_charge_acceptance_limited": ("Ladeannahme bei hohem SOC begrenzt", "warn"),
        "uncertain": ("Telemetrie für Wirkung unklar", "warn"),
        "command_telemetry_uncertain": ("Telemetrie für Wirkung unklar", "warn"),
        "command_power_direction_ambiguous": ("Leistungsrichtung nicht eindeutig", "warn"),
        "command_power_direction_conflict": ("Leistungssensoren widersprüchlich", "warn"),
        "not_effective": ("Nicht wirksam", "bad"),
        "command_not_effective": ("Nicht wirksam", "bad"),
        "command_mismatch_confirmed": ("Sollwertwirkung nicht bestätigt", "bad"),
        "command_neutralization_mismatch": ("Neutralisierung nicht wirksam", "bad"),
        "unavailable": ("Kommandoweg nicht verfügbar", "bad"),
    }
    if raw in mapping:
        return mapping[raw]
    if not raw:
        return "Noch nicht bewertbar", "unknown"
    return "Status nicht eindeutig", "unknown"


def _measurement_log_public_status(value: Any) -> str:
    raw = str(value or "").strip().lower()
    return {
        "active": "Aktiv",
        "ok": "Aktiv",
        "off": "Deaktiviert",
        "disabled": "Deaktiviert",
        "paused": "Pausiert",
        "fallback": "Fallback aktiv",
        "error": "Fehler",
        "stale": "Warnung · Schreibstau",
        "queue_full": "Warnung · Queue voll",
    }.get(raw, str(value or "—"))


def _measurement_db_public_status(value: Any) -> str:
    raw = str(value or "").strip().lower()
    return {
        "queued": "Aktiv · asynchron",
        "active": "Aktiv",
        "ok": "Aktiv",
        "ready": "Bereit",
        "disabled": "Deaktiviert",
        "off": "Deaktiviert",
        "error": "Fehler",
    }.get(raw, str(value or "—"))


def _measurement_target_public_status(value: Any) -> str:
    raw = str(value or "").strip().lower()
    return {
        "internal_sd": "Interner Systemdatenträger",
        "external_mount": "Externes Laufwerk",
        "custom_path": "Benutzerdefinierter Pfad",
        "fallback_sd": "Interner Fallback-Speicher",
        "unavailable": "Nicht verfügbar",
    }.get(raw, str(value or "—"))


def _timing_step_public_label(value: Any) -> str:
    raw = str(value or "").strip()
    return {
        "config_reload_ms": "Konfigurationsprüfung",
        "mqtt_refresh_subscriptions_ms": "MQTT-Subscriptions",
        "zendure_local_api_snapshot_apply_ms": "Zendure API-Snapshot",
        "zendure_local_api_ms": "Zendure Local API",
        "cycle_display_metrics_ms": "Statusaufbereitung",
        "grid_display_read_ms": "Netzwert für Anzeige",
        "grid_control_read_ms": "Netzwert für Regelung",
        "cross_charge_metrics_ms": "Cross-Charge-Metriken",
        "charge_acceptance_diag_ms": "Ladeannahme-Diagnose",
        "graph_snapshot_ms": "Graph-Snapshot",
        "measurement_logging_ms": "Messdaten-Logging",
        "run_once_ms": "Controller-Hauptteil (Sammelwert)",
        "control_decision_ms": "Regelentscheidung",
        "mqtt_command_path_ms": "MQTT-Kommandopfad",
        "command_effect_monitor_ms": "Kommandowirkungsprüfung",
        "finish_cycle_ms": "Zyklusabschluss (Sammelwert)",
        "other_cycle_work_ms": "Sonstige, nicht einzeln erfasste Verarbeitung",
    }.get(raw, raw or "—")


def _command_resync_public_reason(value: Any) -> str:
    raw = str(value or "").strip()
    mapping = {
        "RESYNC_AFTER_RECONNECT": "nach Wiederherstellung der MQTT-Verbindung",
        "RESYNC_AFTER_LONG_STALE": "nach längerer Phase veralteter Telemetriedaten",
        "RESYNC_AFTER_CONFIRMED_MISMATCH": "nach bestätigter Abweichung zwischen Sollwert und Gerätewirkung",
        "RESYNC_AFTER_UNCERTAIN_COMMAND": "nach unsicherem Kommandozustand",
        "RESYNC_AFTER_NEUTRALIZATION_MISMATCH": "nach nicht wirksamer 0-W-Neutralisierung",
        "STARTUP": "nach Controllerstart",
        "RESYNC_SUPPRESSED_COOLDOWN": "wegen laufender Cooldown-Zeit nicht erneut gesendet",
    }
    upper = raw.upper()
    if upper.startswith("RESYNC_AFTER_CONFIRMED_MISMATCH"):
        return "nach bestätigter Abweichung zwischen Sollwert und Gerätewirkung"
    if upper.startswith("RESYNC_AFTER_NEUTRALIZATION_MISMATCH"):
        return "nach nicht wirksamer 0-W-Neutralisierung"
    return mapping.get(upper, raw or "Kommunikationsunsicherheit")


def _adaptive_epoch_text(value: Any) -> str:
    try:
        epoch = float(value)
    except Exception:
        return "—"
    if epoch <= 0:
        return "—"
    age = max(0.0, time.time() - epoch)
    if age < 60:
        return f"vor {int(age)} s"
    if age < 3600:
        return f"vor {int(age // 60)} min"
    if age < 86400:
        hours = int(age // 3600)
        minutes = int((age % 3600) // 60)
        return f"vor {hours} h {minutes} min"
    dt = datetime.fromtimestamp(epoch)
    days = int(age // 86400)
    return f"vor {days} Tagen · {dt.strftime('%d.%m.%Y, %H:%M:%S')}"


def _timing_phase_rows(timing: Dict[str, Any]) -> List[Dict[str, Any]]:
    def total(*keys: str) -> Optional[float]:
        values = [_safe_float(timing.get(key)) for key in keys]
        present = [value for value in values if value is not None]
        return sum(present) if present else None

    rows = [
        ("config", "Konfigurationsprüfung", total("config_reload_ms", "mqtt_refresh_subscriptions_ms"), False),
        # RC18 performs HTTP in a background worker. Only immutable snapshot
        # application belongs to the synchronous active-cycle breakdown.
        ("local_api", "Zendure Local API", total("zendure_local_api_snapshot_apply_ms", "zendure_local_api_ms"), True),
        ("energy_data", "SMA- und Netzdaten", total("sma_energy_meter_ms", "grid_control_read_ms", "grid_display_read_ms"), False),
        ("diagnostics", "Status- und Diagnoseaufbereitung", total("cycle_display_metrics_ms", "cross_charge_metrics_ms", "charge_acceptance_diag_ms", "graph_snapshot_ms"), False),
        ("control", "Regelentscheidung", total("control_decision_ms"), False),
        ("mqtt", "MQTT-Kommandopfad", total("mqtt_command_path_ms"), False),
        ("effect", "Kommandowirkungsprüfung", total("command_effect_monitor_ms"), False),
        ("logging", "Logging im Hauptthread", total("measurement_logging_ms"), False),
        ("other", "Sonstige, nicht einzeln erfasste Verarbeitung", total("other_cycle_work_ms"), False),
    ]
    active_total = _safe_float(timing.get("cycle_total_without_sleep_ms"))
    result: List[Dict[str, Any]] = []
    for key, label, value, keep_when_missing in rows:
        if value is None or value < 0.01:
            if keep_when_missing:
                result.append({"key": key, "label": label, "ms": None, "percent": None, "executed": False})
            continue
        percent = (100.0 * value / active_total) if active_total and active_total > 0 else None
        result.append({"key": key, "label": label, "ms": value, "percent": percent, "executed": True})
    return result


def _legacy_soc_reference_box() -> str:
    return """
    <div class="section">
      <h2>Speicher-SOC Tagesgraph</h2>
      <div class="card">
        <b>Historische Referenzansicht</b><br>
        Der frühere eingebettete SOC-Graph wird hier bewusst nicht mehr geladen,
        weil seine alte Renderfunktion nicht mehr Teil der aktuellen Statusarchitektur ist.<br><br>
        <a href="/">Aktuellen SOC-Tagesgraphen auf der neuen Statusseite öffnen</a>
        &nbsp;·&nbsp;
        <a href="/graph_old">Alten separaten Graphen öffnen</a>
      </div>
    </div>
    """


def _legacy_event_reference_box() -> str:
    return """
    <div class="section">
      <h2>Betriebsereignisse</h2>
      <div class="card">
        Das frühere eingebettete Ereignisfeld wird in der Referenzansicht nicht mehr aufgebaut.
        Das aktuelle persistente Betriebsjournal befindet sich auf der neuen Statusseite.
      </div>
    </div>
    """


def _primary_storage_present(cfg: Dict[str, Any], s: Optional[Dict[str, Any]] = None) -> bool:
    """Return whether a primary/external storage belongs to the UI topology.

    Existing installations keep the historic one-primary-store rendering by
    default.  A real backend may expose ``primary_storage_present`` in its
    snapshot; installations that intentionally operate without a primary store
    may alternatively set the UI-only compatibility flag
    ``STATUS_PRIMARY_STORAGE_PRESENT`` to ``false``.  No controller decision is
    derived from this view flag.
    """
    s = s or {}
    if "primary_storage_present" in s:
        return _boolish(s.get("primary_storage_present"))
    if "STATUS_PRIMARY_STORAGE_PRESENT" in cfg:
        return _boolish(cfg.get("STATUS_PRIMARY_STORAGE_PRESENT"))
    return True


def build_status_view_payload(cfg: Dict[str, Any], s: Dict[str, Any], *, events: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    target = _first_snapshot_value(s, "zendure_target_signed_power", "current_target_power")
    if target is None:
        inp = _safe_float(_first_snapshot_value(s, "last_input_power")) or 0
        out = _safe_float(_first_snapshot_value(s, "last_output_power")) or 0
        target = inp if inp > 0 and out <= 0 else (-out if out > 0 else 0)
    actual = _first_snapshot_value(
        s,
        "zendure_system_signed_power",
        "actual_zendure_system_signed_power",
        "zendure_actual_power_w",
        "actual_zendure_power_w",
        "actual_zendure_system_power",
    )
    mode = str(s.get("current_mode") or "-")
    fixed_modes = {"MANUAL_FIXED_DISCHARGE", "MANUAL_FIXED_CHARGE", "FIXED_DISCHARGE", "FIXED_CHARGE"}
    target_raw = _safe_float(s.get("target_raw_w"))
    target_effective = _safe_float(target)
    target_limit_reason = str(s.get("target_power_limit_reason") or "NONE")
    show_fixed_limit = bool(
        mode in fixed_modes
        and target_raw is not None
        and target_effective is not None
        and abs(target_raw - target_effective) > 0.5
    )
    fixed_requested_text = _signed_power_phrase(target_raw) if show_fixed_limit else ""
    fixed_limit_text = _power_limit_public_text(target_limit_reason) if show_fixed_limit else ""

    grid = _safe_float(_first_snapshot_value(s, "raw_grid_power", "grid_power", "grid_power_w"))
    grid_valid = bool(s.get("grid_power_valid")) and grid is not None
    if not grid_valid:
        grid_status, grid_tone = "nicht bewertbar", "unknown"
    elif grid > 500:
        grid_status, grid_tone = "Bezug aus Netz", "bad"
    elif grid > 50:
        grid_status, grid_tone = "Bezug aus Netz", "warn"
    elif grid < -50:
        grid_status, grid_tone = "Einspeisung / Export", "ok"
    else:
        grid_status, grid_tone = "ausgeglichen", "ok"
    grid_age = _safe_float(s.get("grid_power_age_seconds"))
    grid_freshness = "aktuell" if grid_valid and (grid_age is None or grid_age <= 3) else (f"verzögert, {int(grid_age)} s" if grid_valid and grid_age is not None else "nicht aktuell")

    primary_present = _primary_storage_present(cfg, s)
    warnings: List[str] = []
    if mode == "SAFE_STATE":
        warnings.append("Safe-State aktiv")
    if s.get("command_uncertain_mqtt_active"):
        warnings.append("Aktiver Zendure-Sollwert wurde bei unsicherem MQTT-Zustand gesendet")
    if s.get("command_not_effective_active"):
        warnings.append("Zendure-Sollwert zeigt keine plausible Gerätewirkung")
    active_command_intent = str(s.get("command_desired_intent") or "") in {"CHARGE", "DISCHARGE"}
    if active_command_intent and not bool(s.get("zendure_flash_protection_active")):
        warnings.append("Zendure-Flash-Schutz smartMode=1 nicht bestätigt")
    elif active_command_intent and not bool(s.get("zendure_command_state_complete")):
        warnings.append("Zendure-Command-State noch nicht vollständig rückgelesen")
    if not grid_valid:
        warnings.append("Netzleistungswert nicht aktuell")
    if primary_present and not bool(s.get("second_battery_data_valid", s.get("second_battery_data_available", True))):
        warnings.append("Primärspeicher-Daten nicht vollständig")
    effect_state_for_warning = str(s.get("command_effect_state_category") or s.get("command_effect_category") or "").upper()
    if effect_state_for_warning == "COMMAND_POWER_DIRECTION_AMBIGUOUS":
        warnings.append("Zendure-Leistungsrichtung nicht eindeutig bewertbar")
    elif effect_state_for_warning == "COMMAND_POWER_DIRECTION_CONFLICT":
        warnings.append("Zendure-Leistungssensoren liefern widersprüchliche Richtungen")
    status_kind = "bad" if mode == "SAFE_STATE" else ("warn" if warnings else "ok")
    system_status = "Safe-State" if mode == "SAFE_STATE" else (f"Warnung {len(warnings)}" if warnings else "System OK")

    command_warning = ""
    mqtt_overall = str(s.get("zendure_mqtt_overall_status") or "").upper()
    mqtt_live_confirmed = bool(s.get("zendure_mqtt_live_confirmed", s.get("zendure_live_confirmed", True)))
    mqtt_resave_required = (
        ("RETAINED_ONLY" in mqtt_overall)
        or ("AFTER_BROKER_RESTART_NO_LIVE" in mqtt_overall)
        or ("NO_LIVE" in mqtt_overall and not mqtt_live_confirmed)
    )
    if mqtt_resave_required:
        warnings.append("Zendure Live-Status fehlt: MQTT in der Zendure-App erneut speichern/aktivieren")
    if s.get("command_not_effective_active"):
        command_warning = str(s.get("command_not_effective_reason") or "Sollwert nicht wirksam: Ziel und Istleistung stimmen nicht plausibel überein.")
    elif active_command_intent and not bool(s.get("zendure_flash_protection_active")):
        command_warning = str(s.get("zendure_flash_protection_reason") or "smartMode=1 ist nicht frisch bestätigt; dynamische Leistungskommandos warten.")
    elif active_command_intent and not bool(s.get("zendure_command_state_complete")):
        command_warning = str(s.get("zendure_command_state_reason") or "Zendure-Command-State wird rückgelesen.")
    elif str(effect_state_for_warning) == "COMMAND_CHARGE_ACCEPTANCE_LIMITED":
        command_warning = str(s.get("command_effect_state_reason") or s.get("command_effect_reason") or "Ladeannahme bei hohem SOC begrenzt.")
    elif s.get("command_uncertain_mqtt_active"):
        command_warning = str(s.get("command_uncertain_mqtt_reason") or "Letzter aktiver Sollwert wurde bei unsicherem Zendure-MQTT-Zustand gesendet.")
    elif mqtt_resave_required:
        command_warning = "Zendure Live-Status fehlt. MQTT in der Zendure-App erneut speichern/aktivieren; ZEC synchronisiert den aktiven Sollwert nach der Recovery erneut."

    units = _status_units(cfg, s, target, actual)
    weighted_num = 0.0
    weighted_den = 0.0
    for unit in units:
        cap = _safe_float(unit.get("capacity_kwh"))
        soc = _safe_float(unit.get("soc"))
        if cap is not None and cap > 0 and soc is not None:
            weighted_num += cap * soc
            weighted_den += cap
    system_soc = weighted_num / weighted_den if weighted_den > 0 else (_safe_float(units[0].get("soc")) if len(units) == 1 else None)
    max_soc = _safe_float(cfg.get("MAX_SOC_PERCENT")) or 99
    # Derive the UI value from the current SOC/capacity snapshot so an earlier
    # AUTO/Harvest value can never remain frozen in STOP_HOLD, SAFE_STATE,
    # NIGHT or a fixed mode.  The controller also updates the shared state every
    # cycle; this view-side calculation is an additional read-only safeguard.
    remaining = None
    if weighted_den > 0 and system_soc is not None:
        remaining = max(0.0, weighted_den * max(0.0, max_soc - system_soc) / 100.0)
    elif system_soc is not None:
        capacity_wh = _safe_float(cfg.get("ZENDURE_BATTERY_CAPACITY_WH"))
        capacity_kwh = (capacity_wh / 1000.0) if capacity_wh is not None and capacity_wh > 0 else None
        if capacity_kwh is not None and capacity_kwh > 0:
            remaining = max(0.0, capacity_kwh * max(0.0, max_soc - system_soc) / 100.0)
    if remaining is None:
        remaining = _safe_float(s.get("zendure_remaining_capacity_kwh"))
    zendure_tone = "warn" if command_warning else (units[0].get("tone") if len(units) == 1 else ("warn" if any(u.get("tone") != "ok" for u in units) else "ok"))

    primary_power = _safe_float(_first_snapshot_value(
        s, "sma_battery_display_power", "second_battery_power_w", "norm_second_battery_power_w", "sma_battery_power", "second_battery_power"
    ))
    primary_soc = _safe_float(_first_snapshot_value(
        s, "sma_battery_soc", "second_battery_soc_percent", "raw_second_battery_soc_percent", "second_battery_soc", "sma_soc"
    ))
    primary_valid = bool(s.get("second_battery_data_valid", s.get("second_battery_data_available", primary_soc is not None)))
    primary_fresh = bool(s.get("second_battery_data_fresh", primary_valid))
    if primary_power is None:
        primary_status = "nicht verfügbar"
    elif primary_power > 1500:
        primary_status = "lädt stark"
    elif primary_power > 50:
        primary_status = "lädt"
    elif primary_power < -50:
        primary_status = "trägt Hauslast"
    elif primary_soc is not None and primary_soc >= 99:
        primary_status = "voll / idle"
    else:
        primary_status = "nahe neutral"
    harmony = "Speicherstrategie: SMA hat Vorrang"
    if bool(s.get("rest_surplus_harvest_active")):
        hreason = str(s.get("rest_surplus_harvest_reason") or "")
        harmony = "Harvest: Zendure übernimmt Restüberschuss" if "FULL" in hreason or (primary_soc is not None and primary_soc >= 99) else "Harvest: Parallel-Ernte aktiv · Primärspeicher bleibt priorisiert"
    if "CROSS_CHARGE" in str(s.get("active_limiters") or "") or bool(s.get("cross_charge_guard_limited")):
        harmony = "Cross-Charge-Schutz: Zendure-Leistung wird begrenzt"

    harvest_semantics = str(s.get("harvest_target_semantics") or "NOT_APPLICABLE")
    if harvest_semantics == "ABSOLUTE_EXPORT_CAPTURE":
        ref = _safe_float(s.get("harvest_reference_charge_w")) or 0.0
        export = _safe_float(s.get("rest_surplus_export_w")) or 0.0
        capture = _safe_float(s.get("harvest_export_capture_target_w")) or 0.0
        harvest_calculation = (
            f"0-W-Netzziel: {_zec_num(ref, 'W')} + {_zec_num(export, 'W')} "
            f"= {_zec_num(capture, 'W')}"
        )
    elif harvest_semantics == "ABSOLUTE_SHARE_OR_EXPORT_CAPTURE":
        total = _safe_float(s.get("harvest_total_available_charge_w")) or 0.0
        primary_share = _safe_float(s.get("harvest_primary_share_target_w")) or 0.0
        share_target = _safe_float(s.get("harvest_zendure_share_target_w")) or 0.0
        capture = _safe_float(s.get("harvest_export_capture_target_w")) or 0.0
        selected = str(s.get("harvest_target_selected_by") or "NOT_APPLICABLE")
        raw = _safe_float(s.get("harvest_candidate_raw_w")) or 0.0
        harvest_calculation = (
            f"0-W-Netzziel: T {_zec_num(total, 'W')} · SMA {_zec_num(primary_share, 'W')} · "
            f"Zendure-Share {_zec_num(share_target, 'W')} · Exportaufnahme {_zec_num(capture, 'W')} · "
            f"{selected} → {_zec_num(raw, 'W')}"
        )
    elif harvest_semantics == "INCREMENTAL_FALLBACK":
        fallback_reason = str(s.get("harvest_reference_fallback_reason") or "Referenz unsicher")
        harvest_calculation = f"Inkrementeller Fallback · physische Referenz nicht bestätigt · {fallback_reason}"
    else:
        harvest_calculation = "nicht aktiv"
    primary_tone = _status_unit_tone(primary_soc, cfg, valid=primary_valid and primary_fresh)
    primary_age = _safe_float(_first_snapshot_value(s, "second_battery_data_age_seconds", "last_sma_battery_update_age_seconds"))
    primary_freshness = "aktuell" if primary_valid and primary_fresh and (primary_age is None or primary_age <= 10) else (f"verzögert, {int(primary_age)} s" if primary_valid and primary_age is not None else "nicht aktuell")

    detected = int(_safe_float(s.get("sma_energy_meter_detected_device_count")) or 0)
    packets = int(round(_safe_float(s.get("sma_energy_meter_packet_rate_per_min")) or 0))
    source_raw = str(s.get("raw_grid_source") or s.get("grid_meter_source") or "")
    source_name = "SMA Home Manager direkt" if "sma" in source_raw.lower() else (source_raw or "Netzleistungsquelle")
    matched = bool(s.get("sma_energy_meter_selected_device_matched", True))
    if detected >= 2 and matched:
        device_line = f"{detected} SMA-Geräte erkannt · korrekt gefiltert"
    elif detected == 1 and matched:
        device_line = "1 SMA-Gerät erkannt · korrekt zugeordnet"
    elif detected:
        device_line = f"{detected} SMA-Geräte erkannt · Zielgerät nicht eindeutig"
    else:
        device_line = "Geräteerkennung nicht verfügbar"
    source_age = _safe_float(_first_snapshot_value(s, "sma_energy_meter_last_update_age_seconds", "grid_power_age_seconds"))
    source_age_text = f"vor {int(source_age)} s" if source_age is not None else "nicht verfügbar"
    source_tone = "ok" if grid_valid and matched else ("warn" if grid_valid else "bad")
    auto_text = "Messquelle aktuell · AUTO nutzt diesen Wert" if mode.startswith("AUTO") and grid_valid else ("Messquelle aktuell" if grid_valid else "AUTO wartet auf aktuelle Netzwerte")

    rejected_text = ""
    last_rejected_at = s.get("grid_last_rejected_time")
    last_rejected_reason = s.get("grid_last_rejected_reason")
    if str(last_rejected_at or "").strip() not in {"", "-"}:
        rejected_text = f"Letzter verworfener Messwert: {_status_event_time(last_rejected_at)} · Grund: {last_rejected_reason or 'unplausibler Messwert'}"
    elif s.get("last_error") and "unplausibel" in str(s.get("last_error")).lower() and str(s.get("last_error_time") or "").strip() not in {"", "-"}:
        rejected_text = f"Letzter verworfener Messwert: {_status_event_time(s.get('last_error_time'))} · Grund: unplausibler Messwert"
    rejected_count = int(_safe_float(s.get("grid_rejected_count_since_start")) or 0)
    rejected_count_text = f"Verworfen: {rejected_count} seit Start" if rejected_count else ""

    fixed_projection = fixed_mode_projection_text(cfg, s, mode)
    night_projection = night_mode_projection_text(cfg, s, mode) if mode == "NIGHT_DISCHARGE" else ""
    projection = fixed_projection or night_projection
    mode_tone = "bad" if mode == "SAFE_STATE" else ("warn" if command_warning else "ok")
    mode_status = "Schutzmodus aktiv" if mode == "SAFE_STATE" else ("Regelung eingeschränkt" if command_warning else "Regelung aktiv · aktuell")

    db_path = str(s.get("measurement_db_path") or resolve_measurement_db_path(cfg) or "")
    metrics = get_system_metrics(db_path or "/", ttl_s=5.0)
    local_api_error = str(s.get("last_local_api_error") or "none")
    local_ip_present = bool(str(cfg.get("ZENDURE_LOCAL_IP", "") or "").strip())
    if "ZENDURE_LOCAL_API_USE_FOR_TELEMETRY" in cfg:
        api_worker_enabled = bool(cfg.get("ZENDURE_LOCAL_API_USE_FOR_TELEMETRY", False) and local_ip_present)
        api_diagnostics_enabled = bool(cfg.get("ZENDURE_LOCAL_API_ENABLED", False) and local_ip_present)
    else:
        # Compatibility for older synthetic preview/test payloads.
        api_worker_enabled = bool(cfg.get("ZENDURE_LOCAL_API_ENABLED", False))
        api_diagnostics_enabled = api_worker_enabled
    api_enabled = api_worker_enabled or api_diagnostics_enabled
    if api_worker_enabled:
        api_mode = "Fallback-only" if bool(cfg.get("ZENDURE_LOCAL_API_TELEMETRY_FALLBACK_ONLY", True)) else "Aktive Telemetriequelle"
    elif api_diagnostics_enabled:
        api_mode = "Nur Diagnose"
    else:
        api_mode = "Deaktiviert"
    api_worker_state = str(s.get("zendure_local_api_worker_state") or ("DISABLED" if not api_worker_enabled else "IDLE")).upper()
    api_snapshot_valid = bool(s.get("zendure_local_api_snapshot_valid"))
    api_snapshot_stale = bool(s.get("zendure_local_api_snapshot_stale", True))
    api_success_age_s = _safe_float(s.get("zendure_local_api_last_success_age_s"))
    api_attempt_age_s = _safe_float(s.get("zendure_local_api_last_attempt_age_s"))
    api_latest_attempt_ok = s.get("zendure_local_api_latest_attempt_ok")
    api_request_ms = _safe_float(s.get("zendure_local_api_request_duration_ms"))
    api_apply_ms = _safe_float(s.get("zendure_local_api_snapshot_apply_ms"))
    api_errors = int(s.get("zendure_local_api_consecutive_errors") or 0)
    api_backoff_s = _safe_float(s.get("zendure_local_api_backoff_remaining_s")) or 0.0
    api_error_code = str(s.get("zendure_local_api_latest_error_code") or "NONE")
    telemetry_source = str(s.get("zendure_telemetry_source") or "").strip()
    fallback_active = bool(s.get("zendure_local_api_fallback_active"))
    if not api_enabled:
        api_text, api_tone = "Deaktiviert", "unknown"
    elif not api_worker_enabled:
        api_text, api_tone = "Nur Diagnose · kein Hintergrundworker", "unknown"
    elif api_worker_state == "BACKOFF":
        api_text, api_tone = "Hintergrundworker im Backoff", "warn"
    elif api_worker_state in {"STOPPING", "STOPPED"}:
        api_text, api_tone = "Hintergrundworker gestoppt", "warn"
    elif api_snapshot_valid and not api_snapshot_stale:
        api_text, api_tone = "Snapshot aktuell", "ok"
    elif api_snapshot_valid:
        api_text, api_tone = "Snapshot veraltet", "warn"
    elif local_api_error.lower() not in {"", "none", "ok"}:
        api_text, api_tone = "Noch kein gültiger Snapshot", "warn"
    else:
        api_text, api_tone = "Hintergrundworker startet", "unknown"
    if api_worker_enabled and api_snapshot_valid and not api_snapshot_stale:
        if fallback_active or "api" in telemetry_source.lower():
            api_source_text = "API liefert aktive Telemetrie"
        elif bool(cfg.get("ZENDURE_LOCAL_API_TELEMETRY_FALLBACK_ONLY", True)):
            api_source_text = "MQTT ist Primärquelle"
        else:
            api_source_text = "API steht als Telemetriequelle bereit"
        if api_worker_state == "BACKOFF":
            api_text = f"Snapshot aktuell · Worker im Backoff · {api_source_text}"
        else:
            api_text = f"Snapshot aktuell · {api_source_text}"
    api_success_text = (
        "noch keiner"
        if api_success_age_s is None
        else f"vor {api_success_age_s:.1f} s"
    )
    api_worker_text = (
        f"{api_worker_state} · letzter Erfolg {api_success_text}"
        if api_worker_enabled else ("Nicht aktiv · Diagnosezugriff synchron über Web" if api_diagnostics_enabled else "Deaktiviert")
    )
    api_request_text = "—" if api_request_ms is None else f"letzter Request {api_request_ms:.1f} ms"
    api_apply_text = "nicht im letzten Zyklus" if api_apply_ms is None else f"{api_apply_ms:.3f} ms"
    mqtt_public, mqtt_tone = _zendure_mqtt_public_status(s.get("zendure_mqtt_overall_status"))
    effect_raw = s.get("command_effect_state_category") or s.get("command_effect_category") or ""
    effect_public, effect_tone = _command_effect_public_status(effect_raw)
    try:
        timing_obj = json.loads(str(s.get("last_cycle_timing_json") or "{}"))
    except Exception:
        timing_obj = {}
    try:
        timing_stats = json.loads(str(s.get("last_cycle_timing_stats_json") or "{}"))
    except Exception:
        timing_stats = {}
    active_cycle_ms = _safe_float(
        s.get("last_cycle_total_ms", s.get("last_loop_duration_ms", timing_obj.get("active_cycle_ms", timing_obj.get("cycle_total_without_sleep_ms"))))
    )
    measurement_logging_ms = _safe_float(
        timing_obj.get("measurement_logging_ms", timing_obj.get("measurement_log_ms", timing_obj.get("measurement_v4_ms")))
    )
    if measurement_logging_ms is None and str(s.get("last_cycle_slowest_step") or "") == "measurement_logging_ms":
        measurement_logging_ms = _safe_float(s.get("last_cycle_slowest_step_ms"))
    control_ms = _safe_float(timing_obj.get("control_decision_ms"))
    command_ms = _safe_float(timing_obj.get("mqtt_command_path_ms"))
    sqlite_ms = _safe_float(s.get("measurement_db_last_write_duration_ms"))
    interval_s = max(0.1, float(cfg.get("INTERVAL_SECONDS", 2) or 2))
    sleep_ms = interval_s * 1000.0
    # The loop sleeps for INTERVAL_SECONDS *after* active work.  The bar must
    # therefore show the active share of the real start-to-start cycle rather
    # than pretending the configured sleep were a hard execution budget.
    cycle_active_share_pct = (
        100.0 * active_cycle_ms / (active_cycle_ms + sleep_ms)
        if active_cycle_ms is not None and (active_cycle_ms + sleep_ms) > 0
        else None
    )
    cycle_start_to_start_ms = (active_cycle_ms + sleep_ms) if active_cycle_ms is not None else None
    cycle_meta_text = "—"
    if cycle_start_to_start_ms is not None and cycle_active_share_pct is not None:
        distance_text = f"{cycle_start_to_start_ms / 1000.0:.2f}".replace(".", ",")
        share_text = f"{cycle_active_share_pct:.1f}".replace(".", ",")
        cycle_meta_text = f"Zyklusabstand ca. {distance_text} s · aktive Arbeit {share_text} %"
    slow_cycle_warn_ms = max(1.0, float(cfg.get("SLOW_CYCLE_WARN_MS", 5000) or 5000))
    cycle_slow_warning = bool(active_cycle_ms is not None and active_cycle_ms >= slow_cycle_warn_ms)
    cycle_age = None
    if s.get("last_cycle_completed_epoch"):
        cycle_age = max(0.0, time.time() - float(s.get("last_cycle_completed_epoch")))
    if cycle_age is not None and cycle_age <= max(10.0, interval_s * 2.5):
        cycle_rule, cycle_rule_tone = "Aktuell", "ok"
    elif cycle_age is not None and cycle_age <= 30:
        cycle_rule, cycle_rule_tone = "Verzögert", "warn"
    else:
        cycle_rule, cycle_rule_tone = "Nicht aktuell", "bad"
    timing_phases = _timing_phase_rows(timing_obj)
    slowest_step_public = _timing_step_public_label(s.get("last_cycle_slowest_step"))
    resync_count = int(s.get("command_resync_count") or 0)
    resync_time = str(s.get("command_resync_last_time") or "").strip()
    resync_reason = _command_resync_public_reason(s.get("command_resync_reason"))
    if resync_count > 0:
        resync_text = f"{resync_time or 'Zeitpunkt unbekannt'} · {resync_reason} · AC-Modus und Lade-/Entladelimits erneut gesendet"
    else:
        resync_text = "Keiner seit Controllerstart"
    effect_confirmed = bool(s.get("command_effect_confirmed"))
    effect_confirmed_time = str(s.get("command_effect_confirmed_time") or "-")
    effect_confirmed_reason = str(s.get("command_effect_confirmed_reason") or "")
    if effect_confirmed:
        effect_confirmation_text = f"Ja · {effect_confirmed_time} · {effect_confirmed_reason or 'physische Gerätewirkung bestätigt'}"
    elif s.get("command_not_effective_active"):
        effect_confirmation_text = "Nein · bestätigte Nichtwirkung ist weiterhin offen"
    elif str(effect_raw).upper() == "COMMAND_RECOVERY_VERIFYING":
        effect_confirmation_text = "Noch nicht · Wirkung nach Kommandoabgleich wird geprüft"
    else:
        effect_confirmation_text = "Noch nicht bestätigt"
    suppressed_count = int(s.get("command_resync_suppressed_count") or 0)
    suppressed_time = str(s.get("command_resync_suppressed_last_time") or "").strip()
    suppressed_reason = _command_resync_public_reason(s.get("command_resync_suppressed_reason"))
    suppressed_text = (
        f"{suppressed_time or 'Zeitpunkt unbekannt'} · {suppressed_reason}"
        if suppressed_count > 0 else "Keiner seit Controllerstart"
    )
    controller_uptime = max(0.0, time.time() - float(s.get("controller_started_epoch") or time.time()))
    free_bytes = metrics.get("disk_free_bytes")
    total_bytes = metrics.get("disk_total_bytes")
    used_bytes = max(0.0, float(total_bytes) - float(free_bytes)) if total_bytes is not None and free_bytes is not None else None
    disk_used_pct = (100.0 * used_bytes / float(total_bytes)) if total_bytes and used_bytes is not None else None
    analysis_available = replay_service_available(cfg)
    technical_restrictions: List[str] = []
    if api_worker_enabled and api_tone in {"warn", "bad"}:
        technical_restrictions.append("lokale API eingeschränkt")
    if not analysis_available:
        technical_restrictions.append("Analyse-/Replay-Service nicht erreichbar")
    throttling = metrics.get("throttling") or {}
    current_throttle = throttling.get("current") or []
    historic_throttle = throttling.get("historic") or []
    resource_tone = "bad" if current_throttle or ((metrics.get("temperature_c") or 0) >= 75) or ((metrics.get("ram_used_percent") or 0) >= 92) else ("warn" if historic_throttle or ((metrics.get("temperature_c") or 0) >= 65) or ((metrics.get("ram_used_percent") or 0) >= 75) else "ok")
    base_warning_count = len(warnings)
    event_rows = events if events is not None else read_recent_events(cfg, days=2, limit=250)
    open_events = [e for e in event_rows if e.get("status") == "open"]
    active_event_rows = [
        e for e in open_events
        if str(e.get("severity") or "").lower() in {"warning", "error"}
    ]
    seen_event_titles = set()
    for event in active_event_rows:
        title = str(event.get("title") or event.get("event_type") or "Betriebsereignis").strip()
        marker = title.casefold()
        if not title or marker in seen_event_titles:
            continue
        seen_event_titles.add(marker)
        warnings.append(f"Offenes Betriebsereignis: {title}")
        if len(seen_event_titles) >= 5:
            break
    open_error_count = sum(1 for e in active_event_rows if str(e.get("severity") or "").lower() == "error")
    open_warning_count = sum(1 for e in active_event_rows if str(e.get("severity") or "").lower() == "warning")
    active_warning_group_count = base_warning_count + open_warning_count
    if mode == "SAFE_STATE":
        status_kind = "bad"
        system_status = "Safe-State"
    elif open_error_count:
        status_kind = "bad"
        system_status = f"Fehler {open_error_count}"
    elif active_warning_group_count:
        status_kind = "warn"
        system_status = f"Warnung {active_warning_group_count}"
    else:
        status_kind = "ok"
        system_status = "System OK"
    return {
        "version": APP_VERSION_LABEL,
        "build_id": APP_BUILD_ID,
        "snapshot_epoch_ms": int(time.time() * 1000),
        "server_time": datetime.now().strftime("%H:%M:%S"),
        "snapshot_time": datetime.now().isoformat(timespec="seconds"),
        "topology": {
            "primary_storage_present": primary_present,
            "zendure_unit_count": min(2, max(1, len(units))),
        },
        "system": {
            "kind": status_kind,
            "label": system_status,
            "warnings": warnings,
            "critical_text": str(s.get("control_reason") or "Pflichtdaten fehlen oder Regelung ist nicht sicher möglich.") if mode == "SAFE_STATE" else "",
        },
        "grid": {
            "value": _zec_num(grid, signed=True),
            "value_raw": grid,
            "status": grid_status,
            "valid": grid_valid,
            "tone": grid_tone,
            "source": source_name,
            "freshness_text": grid_freshness,
            "age": grid_age,
        },
        "mode": {
            "mode": mode,
            "text": _mode_public_text(mode, target),
            "target": _signed_power_phrase(target),
            "target_raw": target,
            "target_label": "Wirksames Ziel" if show_fixed_limit else "Ziel",
            "requested_target": fixed_requested_text,
            "limit_text": fixed_limit_text,
            "limit_reason": target_limit_reason if show_fixed_limit else "",
            "reason": _reason_public_text(s),
            "last_change": s.get("last_mode_change_time") or "-",
            "projection": projection,
            "effect": s.get("command_effect_state_category") or s.get("command_effect_category") or "",
            "effect_reason": s.get("command_effect_state_reason") or s.get("command_effect_reason") or "",
            "tone": mode_tone,
            "status_text": mode_status,
        },
        "zendure": {
            "soc": system_soc,
            "system_soc_text": f"{_zec_num(system_soc, '%')} gewichtet" if len(units) > 1 and system_soc is not None else _zec_num(system_soc, "%"),
            "actual": _signed_power_phrase(actual),
            "actual_raw": actual,
            "remaining": remaining,
            "remaining_text": _zec_num(remaining, "kWh") if remaining is not None else "nicht berechenbar",
            "max_soc_text": _zec_num(max_soc, "%"),
            "source": _storage_source_text(s),
            "unit_count": len(units),
            "units": units,
            "command_warning": command_warning,
            "tone": zendure_tone,
        },
        "primary": {
            "present": primary_present,
            "soc": primary_soc if primary_present else None,
            "actual": _signed_power_phrase(primary_power) if primary_present else "nicht konfiguriert",
            "actual_raw": primary_power if primary_present else None,
            "status": primary_status if primary_present else "nicht konfiguriert",
            "line": harmony if primary_present else "",
            "harvest_calculation": harvest_calculation if primary_present else "",
            "source": second_battery_name(cfg) if primary_present else "",
            "age": primary_age if primary_present else None,
            "freshness_text": primary_freshness if primary_present else "",
            "tone": primary_tone if primary_present else "unknown",
        },
        "source": {
            "name": source_name,
            "device_line": device_line,
            "age": source_age,
            "age_text": source_age_text,
            "packets_min": packets,
            "packets_text": f"{packets}/min",
            "auto_text": auto_text,
            "rejected_text": rejected_text,
            "rejected_count_text": rejected_count_text,
            "tone": source_tone,
        },
        "logging": {
            "status": _measurement_log_public_status(s.get("measurement_log_status")),
            "reason": s.get("measurement_log_status_reason") or "",
            "target": _measurement_target_public_status(s.get("measurement_log_active_target_type") or s.get("measurement_log_target_type")),
            "path": s.get("measurement_log_path") or "",
            "db": _measurement_db_public_status(s.get("measurement_db_status")),
            "db_path": db_path,
            "db_name": os.path.basename(db_path) if db_path else "—",
            "db_size_bytes": s.get("measurement_db_size_bytes"),
            "queue_depth": s.get("measurement_db_queue_depth", 0),
            "last_write": _adaptive_epoch_text(s.get("measurement_db_last_write_epoch_s")),
            "last_write_epoch_s": s.get("measurement_db_last_write_epoch_s"),
            "fallback_active": bool(s.get("measurement_fallback_active")),
            "fallback_count": int(s.get("measurement_fallback_count_since_start") or 0),
            "fallback_reason": s.get("measurement_last_fallback_reason") or "",
            "free_bytes": free_bytes,
            "used_bytes": used_bytes,
            "total_bytes": total_bytes,
            "disk_used_percent": disk_used_pct,
            "tone": "bad" if (str(s.get("measurement_log_status") or "").lower() == "error" or str(s.get("measurement_db_status") or "").lower() == "error") else ("warn" if (bool(s.get("measurement_fallback_active")) or bool(s.get("measurement_db_write_stale")) or str(s.get("measurement_db_status") or "").lower() in ("stale", "queue_full")) else "ok"),
        },
        "resources": {
            "cpu_percent": metrics.get("cpu_percent"),
            "ram_used_percent": metrics.get("ram_used_percent"),
            "ram_available_bytes": metrics.get("ram_available_bytes"),
            "ram_total_bytes": metrics.get("ram_total_bytes"),
            "swap_used_bytes": metrics.get("swap_used_bytes"),
            "swap_total_bytes": metrics.get("swap_total_bytes"),
            "swap_in_bytes_per_s": metrics.get("swap_in_bytes_per_s"),
            "swap_out_bytes_per_s": metrics.get("swap_out_bytes_per_s"),
            "temperature_c": metrics.get("temperature_c"),
            "load": metrics.get("load"),
            "system_uptime_s": metrics.get("system_uptime_s"),
            "throttling": throttling,
            "tone": resource_tone,
            "status": "Raspberry Pi unauffällig" if resource_tone == "ok" else ("Raspberry Pi beobachten" if resource_tone == "warn" else "Raspberry Pi kritisch"),
        },
        "diag": {
            "rule": cycle_rule,
            "rule_tone": cycle_rule_tone,
            "cycle_age_s": cycle_age,
            "broker": "Verbunden" if bool(s.get("mqtt_connected")) else "Getrennt",
            "broker_tone": "ok" if bool(s.get("mqtt_connected")) else "bad",
            "mqtt": mqtt_public,
            "mqtt_tone": mqtt_tone,
            "mqtt_raw": s.get("zendure_mqtt_overall_status") or "",
            "api": api_text,
            "api_tone": api_tone,
            "api_mode": api_mode,
            "api_worker_text": api_worker_text,
            "api_worker_state": api_worker_state,
            "api_snapshot_valid": api_snapshot_valid,
            "api_snapshot_stale": api_snapshot_stale,
            "api_last_success_age_s": api_success_age_s,
            "api_last_attempt_age_s": api_attempt_age_s,
            "api_latest_attempt_ok": api_latest_attempt_ok,
            "api_last_request_duration_ms": api_request_ms,
            "api_request_text": api_request_text,
            "api_snapshot_apply_ms": api_apply_ms,
            "api_apply_text": api_apply_text,
            "api_consecutive_errors": api_errors,
            "api_backoff_remaining_s": api_backoff_s,
            "api_error_code": api_error_code,
            "api_telemetry_source": telemetry_source or "—",
            "api_fallback_active": fallback_active,
            "effect": effect_public,
            "effect_tone": effect_tone,
            "effect_raw": effect_raw,
            "flash_protection": "Bestätigt" if bool(s.get("zendure_flash_protection_active")) else "Nicht bestätigt",
            "flash_protection_tone": "ok" if bool(s.get("zendure_flash_protection_active")) else ("bad" if active_command_intent else "unknown"),
            "flash_protection_reason": s.get("zendure_flash_protection_reason") or "",
            "command_state_complete": bool(s.get("zendure_command_state_complete")),
            "command_state_reason": s.get("zendure_command_state_reason") or "",
            "offgrid_power_w": s.get("zendure_offgrid_power_w", 0),
            "offgrid_text": _zec_num(s.get("zendure_offgrid_power_w", 0), "W"),
            "loop_ms": active_cycle_ms,
            "loop_text": (f"{int(round(active_cycle_ms))} ms" if active_cycle_ms is not None and active_cycle_ms >= 100 else (f"{active_cycle_ms:.1f} ms" if active_cycle_ms is not None else "—")),
            "cycle_active_share_percent": cycle_active_share_pct,
            # Compatibility key for the RC5/RC6 frontend contract.
            "cycle_budget_percent": cycle_active_share_pct,
            "cycle_start_to_start_ms": cycle_start_to_start_ms,
            "cycle_meta_text": cycle_meta_text,
            "slow_cycle_warn_ms": slow_cycle_warn_ms,
            "cycle_slow_warning": cycle_slow_warning,
            "control_ms": control_ms,
            "command_ms": command_ms,
            "measurement_logging_ms": measurement_logging_ms,
            "measurement_logging_text": (f"{int(measurement_logging_ms)} ms" if measurement_logging_ms is not None and float(measurement_logging_ms).is_integer() else (f"{measurement_logging_ms:.1f} ms" if measurement_logging_ms is not None else "—")),
            "sqlite_ms": sqlite_ms,
            "slowest_step": slowest_step_public,
            "slowest_step_raw": s.get("last_cycle_slowest_step") or "",
            "slowest_ms": s.get("last_cycle_slowest_step_ms"),
            "timing": timing_obj,
            "timing_phases": timing_phases,
            "timing_stats": timing_stats,
            "controller_uptime_s": controller_uptime,
            "instance_owner_active": bool(s.get("instance_owner_active")),
            "instance_owner_pid": s.get("instance_owner_pid"),
            "instance_owner_build_id": s.get("instance_owner_build_id") or "",
            "instance_owner_since_utc": s.get("instance_owner_since_utc") or "",
            "resync": resync_reason,
            "resync_time": resync_time or "—",
            "resync_text": resync_text,
            "effect_confirmation_text": effect_confirmation_text,
            "resync_count": resync_count,
            "resync_suppressed_count": suppressed_count,
            "resync_suppressed_text": suppressed_text,
            "resync_target_w": s.get("command_uncertain_mqtt_target_w") or target or 0,
            "analysis": "Aktiv" if analysis_available else "Nicht erreichbar",
        },
        "events": {
            "items": event_rows,
            "open_count": len(open_events),
            "open_severity": "error" if any(e.get("severity") == "error" for e in open_events) else ("warning" if any(e.get("severity") == "warning" for e in open_events) else "info"),
            "technical_restrictions": technical_restrictions,
        },
    }

def _parse_day(date_text: Optional[str]) -> datetime:
    if date_text:
        try:
            return datetime.strptime(str(date_text)[:10], "%Y-%m-%d")
        except Exception:
            pass
    return datetime.combine(datetime.now().date(), datetime.min.time())

_storage_day_cache: Dict[str, Any] = {"key": "", "built_epoch": 0.0, "payload": None}
_storage_day_lock = threading.Lock()


def build_storage_soc_day_payload(cfg: Dict[str, Any], snap: Dict[str, Any], date: Optional[str] = None) -> Dict[str, Any]:
    day_start = _parse_day(date)
    day_end = day_start + timedelta(days=1)
    today = datetime.now().date()
    if day_start.date() > today:
        day_start = datetime.combine(today, datetime.min.time())
        day_end = day_start + timedelta(days=1)
    is_today = day_start.date() == today

    def _decorate_with_historical_config(base_payload: Dict[str, Any]) -> Dict[str, Any]:
        from graph_config_timeline import build_day_segments
        decorated = dict(base_payload)
        try:
            segments, timeline_meta = build_day_segments(
                cfg, day_start, day_end,
                current_effective_config=cfg if is_today else None,
            )
        except Exception as exc:
            segments = [{
                "start_minute": 0, "end_minute": 1440, "known": False,
                "config_control_hash": "", "min_soc": None, "max_soc": None,
                "reserve_soc": None, "night_start": "", "night_end": "", "source": "timeline_error",
            }]
            timeline_meta = {"timeline_status": "error", "timeline_error": str(exc), "unknown_segments": 1}
        decorated["config_segments"] = segments
        decorated["config_timeline"] = timeline_meta
        decorated["overlay_semantics"] = "historical_effective_segmented_v1"
        decorated["historical_config_complete"] = not any(not bool(item.get("known")) for item in segments)
        # Compatibility fields contain only a single unambiguous day-wide overlay.
        known = [item for item in segments if item.get("known")]
        signatures = {(item.get("min_soc"), item.get("max_soc"), item.get("reserve_soc"), item.get("night_start"), item.get("night_end")) for item in known}
        if len(signatures) == 1 and known:
            item = known[0]
            decorated["thresholds"] = {"min_soc": item.get("min_soc"), "max_soc": item.get("max_soc"), "reserve_soc": item.get("reserve_soc")}
            decorated["night_window"] = {"start": item.get("night_start"), "end": item.get("night_end")}
        else:
            decorated["thresholds"] = {"min_soc": None, "max_soc": None, "reserve_soc": None}
            decorated["night_window"] = {"start": "", "end": ""}
        return decorated

    primary_present = _primary_storage_present(cfg, snap)
    status_units = _status_units(cfg, snap, snap.get("zendure_target_signed_power"), snap.get("zendure_system_signed_power"))
    unit_count = min(2, max(1, len(status_units)))
    cache_key = f"{day_start.date().isoformat()}|storage-v4|p{int(primary_present)}|u{unit_count}"
    now_epoch = time.time()
    ttl = 60 if is_today else 3600
    with _storage_day_lock:
        if _storage_day_cache.get("key") == cache_key and _storage_day_cache.get("payload") and now_epoch - float(_storage_day_cache.get("built_epoch") or 0) < ttl:
            payload = dict(_storage_day_cache["payload"])
            payload["cache_status"] = "hit"
            payload["cache_age_s"] = int(now_epoch - float(_storage_day_cache.get("built_epoch") or 0))
            return _decorate_with_historical_config(payload)
    points: List[Dict[str, Any]] = []
    source = "measurement_db_1min"
    error = ""
    try:
        db_points, db_meta = query_graph_points(cfg, day_start, day_end, limit=2000)
        if db_points:
            for pnt in db_points:
                dt = datetime.fromtimestamp(int(pnt["epoch_ms"]) / 1000.0)
                minute = int((dt - day_start).total_seconds() // 60)
                points.append({
                    "minute": minute,
                    "time": dt.strftime("%H:%M"),
                    "zendure_soc": pnt.get("soc"),
                    "zendure_unit_1_soc": pnt.get("soc"),
                    "zendure_unit_2_soc": pnt.get("zendure_unit_2_soc"),
                    "primary_soc": pnt.get("primary_soc") if primary_present else None,
                    "zendure_power_w": pnt.get("zendure_actual_power_w"),
                    "primary_power_w": pnt.get("primary_power_w") if primary_present else None,
                    "mode": pnt.get("mode"),
                    "reason": pnt.get("control_reason") or pnt.get("limit_reason") or "",
                    "safe_state": bool(pnt.get("safe_state_active")),
                    "night_window": bool(pnt.get("night_window_active")),
                })
        else:
            source = str(db_meta.get("db_status") or "measurement_db_empty")
    except Exception as exc:
        error = str(exc)
        source = "error"
    if is_today:
        now = datetime.now()
        minute = int((now - day_start).total_seconds() // 60)
        if 0 <= minute <= 1440:
            points.append({
                "minute": minute,
                "time": now.strftime("%H:%M"),
                "zendure_soc": snap.get("battery_soc"),
                "zendure_unit_1_soc": (status_units or [{}])[0].get("soc"),
                "zendure_unit_2_soc": ((status_units + [{}, {}])[1].get("soc")),
                "primary_soc": snap.get("sma_battery_soc", snap.get("second_battery_soc_percent", snap.get("second_battery_soc"))) if primary_present else None,
                "zendure_power_w": snap.get("zendure_system_signed_power"),
                "primary_power_w": snap.get("sma_battery_power", snap.get("second_battery_power_w", snap.get("second_battery_power"))) if primary_present else None,
                "mode": snap.get("current_mode"),
                "reason": snap.get("control_reason"),
                "safe_state": snap.get("current_mode") == "SAFE_STATE",
                "night_window": snap.get("current_mode") == "NIGHT_DISCHARGE",
                "live": True,
            })
    points = sorted(points, key=lambda x: x.get("minute", 0))
    complete = bool(is_today or (points and int(points[-1].get("minute", 0)) >= 1430))
    date_range = query_measurement_date_range(cfg)
    payload = {
        "date": day_start.date().isoformat(),
        "is_today": is_today,
        "complete": complete,
        "zendure_unit_count": unit_count,
        "primary_storage_present": primary_present,
        "unit_labels": [str(u.get("name") or f"Zendure {idx+1}") for idx, u in enumerate(status_units[:2])],
        "axis_minute_start": 0,
        "axis_minute_end": 1440,
        "points": points,
        "source": source,
        "cache_status": "rebuilt",
        "cache_age_s": 0,
        "error": error,
        "last_point_at": points[-1]["time"] if points else "",
        "available_from": date_range.get("available_from") or day_start.date().isoformat(),
        "available_to": today.isoformat(),
    }
    with _storage_day_lock:
        _storage_day_cache.update({"key": cache_key, "payload": payload, "built_epoch": now_epoch})
    return _decorate_with_historical_config(payload)

def _status_info(title: str, text: str) -> str:
    return f'<button class="info-dot" data-tooltip="{html.escape(text, quote=True)}" aria-label="Info {html.escape(title)}">i</button>'


def build_status_page_rc2_legacy(cfg: Dict[str, Any], s: Dict[str, Any]) -> str:
    # Historical RC2 status page retained only as implementation reference.
    payload = build_status_view_payload(cfg, s)
    # Compatibility-visible values also document the old text-heavy information inventory.
    measurement_log_details = (
        f"Status: {html.escape(str(s.get('measurement_log_status', '-')))} · "
        f"Ziel: {html.escape(str(s.get('measurement_storage_active_target') or s.get('measurement_log_path') or '-'))}"
    )
    try:
        grid_raw_for_compat = float(s.get('raw_grid_power', s.get('grid_power', 0.0)) or 0.0)
        grid_compat_value = f"{grid_raw_for_compat:.1f} W"
    except Exception:
        grid_compat_value = ""
    try:
        timing_obj_compat = json.loads(str(s.get('last_cycle_timing_json') or '{}'))
    except Exception:
        timing_obj_compat = {}
    active_cycle_ms_compat = int(s.get('last_cycle_total_ms') or s.get('last_loop_duration_ms') or 0)
    measurement_logging_ms_compat = timing_obj_compat.get('measurement_logging_ms')
    if measurement_logging_ms_compat is None and str(s.get('last_cycle_slowest_step') or '') == 'measurement_logging_ms':
        measurement_logging_ms_compat = s.get('last_cycle_slowest_step_ms')
    measurement_logging_compat = (
        f"Messdaten-Logging {int(float(measurement_logging_ms_compat))} ms"
        if measurement_logging_ms_compat is not None else "Messdaten-Logging n.a."
    )
    unit_count = int(payload["zendure"].get("unit_count") or 1)
    if unit_count <= 1:
        zendure_card_body = f'''
          <div class="card-split single-unit">
            {_soc_ring_html('Zendure', payload['zendure'].get('soc'), cfg, 'SOC aktuell')}
            <div class="kv-block">
              <div><span>Ist</span><b data-zec="zendure.actual">{html.escape(payload['zendure']['actual'])}</b></div>
              <div><span>Rest bis Max-SOC</span><b data-zec="zendure.remaining">{_zec_num(payload['zendure'].get('remaining'), 'kWh') if payload['zendure'].get('remaining') is not None else 'nicht berechenbar'}</b></div>
              <div><span>Max-SOC</span><b>{html.escape(str(cfg.get('MAX_SOC_PERCENT', 99)))} %</b></div>
            </div>
          </div>'''
    else:
        zendure_card_body = f'''
          <div class="dual-rings">
            {_soc_ring_html('Unit 1', payload['zendure'].get('soc'), cfg, 'aktiv')}
            {_soc_ring_html('Unit 2', None, cfg, 'keine Daten')}
          </div>
          <div class="unit-lines" data-zec="zendure.units">Unit 1: {html.escape(_zec_num(payload['zendure'].get('soc'), '%'))} · {html.escape(payload['zendure']['actual'])}<br>Unit 2: keine aktuellen Daten</div>
          <div class="kv-block compact"><div><span>Ist gesamt</span><b data-zec="zendure.actual">{html.escape(payload['zendure']['actual'])}</b></div></div>'''

    primary_card = f'''
      <section class="zec-ui-card" data-card="primary">
        <div class="card-head">{_ui_icon('battery')}<h2>Primärspeicher</h2>{_status_info('Primärspeicher','Diese Karte zeigt den SMA-/Primärspeicher. ZEC steuert ihn nicht direkt, berücksichtigt aber SOC und Leistung für Harvest, Cross-Charge und Nachtstrategie.')}</div>
        <div class="card-split">
          {_soc_ring_html('primary', payload['primary'].get('soc'), cfg, 'Primärspeicher')}
          <div class="kv-block">
            <div><span>Ist</span><b data-zec="primary.actual">{html.escape(payload['primary']['actual'])}</b></div>
            <div><span>Status</span><b data-zec="primary.status">{html.escape(payload['primary']['status'])}</b></div>
            <div><span>Harmonisierung</span><b data-zec="primary.line">{html.escape(payload['primary']['line'])}</b></div>
          </div>
        </div>
        <div class="card-status"><span class="status-dot ok"></span><span data-zec="primary.source">{html.escape(payload['primary']['source'])}</span> · aktuell</div>
      </section>'''

    page = _modern_body_start(
        cfg, "status", system_payload=payload.get("system"), server_time=str(payload.get("server_time") or "")
    )
    page += f'''
    <style>
      :root {{ --zec-page-bg:#f5f7fb; --zec-card-bg:#ffffff; --zec-text-main:#0f172a; --zec-text-muted:#64748b; --zec-accent-blue:#2563eb; --zec-status-ok:#16a34a; --zec-status-warn:#f59e0b; --zec-status-error:#dc2626; --zec-status-unknown:#94a3b8; --zec-ring-track:#e5e7eb; --zec-ring-inner-bg:var(--zec-card-bg); --zec-card-border:#e5e7eb; }}
      body.zec-modern-body.modern-dark {{ --zec-page-bg:#0f172a; --zec-card-bg:#172033; --zec-text-main:#e5e7eb; --zec-text-muted:#94a3b8; --zec-ring-track:#334155; --zec-ring-inner-bg:var(--zec-card-bg); --zec-card-border:#334155; }}
      .zec-dashboard {{ max-width:1500px; margin:0 auto; padding:10px 8px 28px; color:var(--zec-text-main); }}
      
      .zec-system-pill {{ cursor:pointer; border:1px solid rgba(34,197,94,.25); }}
      .zec-system-pill.ok {{ color:var(--zec-status-ok); background:rgba(34,197,94,.08); }}
      .zec-system-pill.warn {{ color:#a16207; background:rgba(245,158,11,.10); border-color:rgba(245,158,11,.3); }}
      .zec-system-pill.bad {{ color:var(--zec-status-error); background:rgba(220,38,38,.08); border-color:rgba(220,38,38,.3); }}
      .zec-main-grid {{ display:grid; grid-template-columns: repeat(5, minmax(215px,1fr)); gap:14px; }}
      .zec-ui-card,.zec-wide-card {{ background:var(--zec-card-bg); border:1px solid var(--zec-card-border); border-radius:18px; padding:14px; box-shadow:0 12px 28px rgba(15,23,42,.06); }} .zec-ui-card {{ min-height:236px; }}
      .card-head {{ display:flex; align-items:center; gap:9px; margin-bottom:10px; }} .card-head h2 {{ margin:0; font-size:17px; flex:1; }} .card-head .zec-icon {{ width:20px; height:20px; color:var(--zec-accent-blue); }}
      .info-dot {{ position:relative; width:23px; height:23px; border-radius:50%; border:1px solid var(--zec-card-border); background:transparent; color:var(--zec-text-muted); font-weight:800; cursor:help; flex:0 0 auto; }}
      .info-dot::after {{ content:attr(data-tooltip); position:absolute; z-index:1000; top:calc(100% + 8px); right:0; width:max-content; max-width:min(360px, calc(100vw - 32px)); padding:10px 12px; border-radius:10px; background:var(--zec-text-main); color:var(--zec-card-bg); font-size:13px; line-height:1.45; font-weight:500; white-space:normal; overflow-wrap:anywhere; box-shadow:0 12px 30px rgba(15,23,42,.25); opacity:0; visibility:hidden; pointer-events:none; transform:translateY(-4px); transition:.12s ease; text-align:left; }}
      .info-dot:hover::after,.info-dot:focus-visible::after {{ opacity:1; visibility:visible; transform:translateY(0); }}
      .zec-main-grid .zec-ui-card:nth-child(n+4) .info-dot::after {{ right:0; left:auto; }}
      .big-value {{ text-align:center; font-size:34px; font-weight:850; margin:18px 0 4px; }} .big-sub {{ text-align:center; color:var(--zec-text-muted); font-weight:650; }} .mode-name {{ text-align:center; font-size:30px; font-weight:850; margin-top:18px; }} .mode-text {{ text-align:center; color:var(--zec-text-muted); font-size:16px; font-weight:650; margin-bottom:12px; }}
      .line {{ margin:7px 0; color:var(--zec-text-muted); }} .line b {{ color:var(--zec-text-main); }} .card-status {{ margin-top:14px; color:var(--zec-text-muted); font-size:13px; line-height:1.4; }} .card-warning {{ margin-top:10px; border-radius:10px; background:rgba(245,158,11,.12); color:#92400e; padding:8px 10px; font-size:13px; }}
      .card-split {{ display:grid; grid-template-columns:145px 1fr; gap:16px; align-items:center; }} .card-split.single-unit {{ min-height:160px; }} .soc-ring-wrap {{ text-align:center; }} .soc-ring-caption {{ color:var(--zec-text-muted); font-size:12px; margin-top:6px; }}
      .soc-ring {{ --soc:0; width:132px; height:132px; border-radius:50%; display:grid; place-items:center; background:conic-gradient(var(--zec-status-ok) calc(var(--soc)*1%), var(--zec-ring-track) 0); }} .soc-ring-wrap.warn .soc-ring {{ background:conic-gradient(var(--zec-status-warn) calc(var(--soc)*1%), var(--zec-ring-track) 0); }} .soc-ring-wrap.unknown .soc-ring {{ background:conic-gradient(var(--zec-status-unknown) calc(var(--soc)*1%), var(--zec-ring-track) 0); }} .soc-ring-inner {{ width:96px; height:96px; border-radius:50%; background:var(--zec-ring-inner-bg); display:flex; flex-direction:column; align-items:center; justify-content:center; }} .soc-ring-inner b {{ font-size:24px; }} .soc-ring-inner span {{ font-size:12px; color:var(--zec-text-muted); }}
      .kv-block div {{ display:flex; justify-content:space-between; gap:10px; padding:6px 0; border-bottom:1px solid rgba(148,163,184,.18); }} .kv-block span {{ color:var(--zec-text-muted); }} .kv-block b {{ text-align:right; }} .dual-rings {{ display:flex; justify-content:center; gap:18px; }} .dual-rings .soc-ring {{ width:116px; height:116px; }} .dual-rings .soc-ring-inner {{ width:84px; height:84px; }} .unit-lines {{ margin-top:10px; color:var(--zec-text-muted); font-size:13px; line-height:1.55; }}
      .zec-soc-wide,.zec-bottom-grid {{ margin-top:16px; }} .chart-toolbar {{ display:flex; flex-wrap:wrap; align-items:center; gap:10px; justify-content:space-between; margin-bottom:12px; }} .chart-toolbar button {{ border:1px solid var(--zec-card-border); border-radius:9px; padding:7px 10px; background:var(--zec-card-bg); color:var(--zec-text-main); cursor:pointer; }} #storageSocChart {{ height:330px !important; }} .chart-status {{ color:var(--zec-text-muted); font-size:13px; margin-top:9px; }}
      .zec-bottom-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }} .diag-row {{ display:flex; justify-content:space-between; border-bottom:1px solid rgba(148,163,184,.18); padding:8px 0; gap:10px; }} .diag-row span {{ color:var(--zec-text-muted); }} .diag-row b {{ text-align:right; }} .legacy-test-hints {{ display:none; }}
      @media(max-width:1350px) {{ .zec-main-grid {{ grid-template-columns:repeat(3,minmax(0,1fr)); }} }} @media(max-width:920px) {{ .zec-main-grid,.zec-bottom-grid {{ grid-template-columns:1fr; }} .card-split {{ grid-template-columns:1fr; justify-items:center; }} }}
    </style>
    <main class="zec-dashboard">
      
      <section class="zec-main-grid">
        <section class="zec-ui-card" data-card="grid"><div class="card-head">{_ui_icon('meter')}<h2>Netzleistung</h2>{_status_info('Netzleistung','Aktueller ungefilterter Netzleistungswert am Netzanschlusspunkt. Negative Werte bedeuten Einspeisung, positive Werte Netzbezug.')}</div><div class="big-value" data-zec="grid.value">{html.escape(payload['grid']['value'])}</div><div class="big-sub" data-zec="grid.status">{html.escape(payload['grid']['status'])}</div><div id="gridMiniSparkline" style="margin-top:14px">{_mini_svg_sparkline(_grid_mini_values_from_snapshot(s), stroke='#2563eb')}</div><div class="card-status"><span class="status-dot {'ok' if payload['grid']['valid'] else 'warn'}"></span> Quelle: <span data-zec="grid.source">{html.escape(payload['grid']['source'])}</span> · aktuell</div></section>
        <section class="zec-ui-card" data-card="mode"><div class="card-head">{_ui_icon('mode')}<h2>Betriebsmodus</h2>{_status_info('Betriebsmodus','Diese Karte zeigt die aktuelle Entscheidung des Controllers: Modus, Zielwert, Grund und Prognose.')}</div><div class="mode-name" data-zec="mode.mode">{html.escape(payload['mode']['mode'])}</div><div class="mode-text" data-zec="mode.text">{html.escape(payload['mode']['text'])}</div><div class="line">Ziel: <b data-zec="mode.target">{html.escape(payload['mode']['target'])}</b></div><div class="line">Grund: <b data-zec="mode.reason">{html.escape(payload['mode']['reason'])}</b></div><div class="line" data-zec="mode.projection">{html.escape(payload['mode'].get('night_projection') or payload['mode'].get('fixed_projection') or '')}</div><div class="line">Letzte Änderung: <b data-zec="mode.last_change">{html.escape(str(payload['mode']['last_change']))}</b></div><div class="card-status"><span class="status-dot ok"></span> Regelung aktiv · aktuell</div></section>
        <section class="zec-ui-card" data-card="zendure"><div class="card-head">{_ui_icon('battery')}<h2>Zendure / Batterie</h2>{_status_info('Zendure','Zustand des Zendure-Speichers: SOC, Istleistung, Telemetrie und Command-Wirkung.')}</div>{zendure_card_body}<div class="card-status"><span class="status-dot ok"></span> Telemetrie: <span data-zec="zendure.source">{html.escape(payload['zendure']['source'])}</span></div><div class="card-warning" data-zec="zendure.command_warning" style="{'display:block' if payload['zendure'].get('command_warning') else 'display:none'}">{html.escape(str(payload['zendure'].get('command_warning') or ''))}</div></section>
        {primary_card}
        <section class="zec-ui-card" data-card="source"><div class="card-head">{_ui_icon('radio')}<h2>Netzleistungsquelle</h2>{_status_info('Netzleistungsquelle','Diese Karte zeigt, welche Messquelle ZEC für die Netzleistung verwendet und ob sie aktuell genug ist.')}</div><div class="line"><b data-zec="source.name">{html.escape(payload['source']['name'])}</b></div><div class="line" data-zec="source.device_line">{html.escape(payload['source']['device_line'])}</div><div class="line">Letztes Paket: <b data-zec="source.age">vor {html.escape(str(payload['source']['age']))} s</b></div><div class="line">Pakete: <b data-zec="source.packets_min">{html.escape(str(payload['source']['packets_min']))}/min</b></div><div class="line" data-zec="source.rejected">{html.escape(payload['source']['rejected'])}</div><div class="card-status"><span class="status-dot ok"></span> <span data-zec="source.auto_text">{html.escape(payload['source']['auto_text'])}</span></div></section>
      </section>
      <section class="zec-soc-wide"><div class="zec-wide-card"><div class="chart-toolbar"><div><h2 style="margin:0">Speicher-SOC Tagesgraph</h2><div class="small">Ganzer Kalendertag 00:00–24:00 · Zendure und Primärspeicher</div></div><div><button id="dayPrev">‹ Zurück</button><button id="dayToday">Heute</button><button id="dayNext">Vor ›</button> <b id="socDayLabel"></b></div></div><canvas id="storageSocChart"></canvas><div id="storageSocStatus" class="chart-status">SOC-Daten werden geladen…</div></div></section>
      <section class="zec-bottom-grid"><div class="zec-wide-card"><h2>Messdaten / Logging</h2><div class="diag-row"><span>Logging</span><b data-zec="logging.status">{html.escape(str(payload['logging']['status']))}</b></div><div class="diag-row"><span>Ziel</span><b data-zec="logging.target">{html.escape(str(payload['logging']['target']))}</b></div><div class="diag-row"><span>SQLite-Graphspeicher</span><b data-zec="logging.db">{html.escape(str(payload['logging']['db']))}</b></div><div class="diag-row"><span>DB-Datei</span><b data-zec="logging.db_path">{html.escape(os.path.basename(str(payload['logging']['db_path']) or '-'))}</b></div></div><div class="zec-wide-card"><h2>System-/Diagnosekarten</h2><div class="diag-row"><span>Zendure MQTT</span><b data-zec="diag.mqtt">{html.escape(str(payload['diag']['mqtt']))}</b></div><div class="diag-row"><span>Lokale API</span><b data-zec="diag.api">{html.escape(str(payload['diag']['api']))}</b></div><div class="diag-row"><span>Command-Effect</span><b data-zec="diag.effect">{html.escape(str(payload['diag']['effect']))}</b></div><div class="diag-row"><span>Letzter Resync</span><b data-zec="diag.resync">{html.escape(str(payload['diag']['resync']))}</b></div><div class="diag-row"><span>Zykluszeit</span><b data-zec="diag.loop_ms">{html.escape(str(payload['diag']['loop_ms']))} ms</b></div></div></section>
      <div class="legacy-test-hints">Nachtmodus:</b> aktuell nicht aktiv · Fenster {format_hhmm(cfg.get('NIGHT_START_HOUR',21), cfg.get('NIGHT_START_MINUTE',30))}–{format_hhmm(cfg.get('NIGHT_END_HOUR',5), cfg.get('NIGHT_END_MINUTE',30))} · Leistung {html.escape(str(cfg.get('NIGHT_DISCHARGE_POWER_W',400)))} W · /soc-day-data · /graph-view-data?range=24h&resolution=1min · Aktive Zykluszeit {active_cycle_ms_compat} ms · {measurement_logging_compat} · mockup-top-card · Zendure (Batterie) · soc-ring · mockup-footer-grid · Systemlaufzeit · zec-battery-layout · soc-value · soc-label · Zendure-MQTT nicht vollständig frisch · zec-card-warning · Zendure Live-Status · Zendure-App · aktueller Messwert · Geglätteter AUTO-Regelwert: n.a. · nicht regelrelevant · {html.escape(grid_compat_value)} · measurement_log_details {measurement_log_details}</div>
      <div id="modern-diagnostics" class="legacy-test-hints">Legacy-Fallback: /status_old · /graph_old</div>
    </main>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
    window.ZEC_BOOTSTRAP = {json.dumps(payload, ensure_ascii=False)};
    (function(){{
      const q=(s)=>document.querySelector(s); const qa=(s)=>Array.from(document.querySelectorAll(s));
      function setVal(path,val){{ qa('[data-zec="'+path+'"]').forEach(e=>{{ e.textContent=(val===null||val===undefined||val==='')?'—':String(val); }}); }}
      function applyStatus(p){{ if(!p)return; const pill=q('#systemPill'); if(p.system&&pill){{ pill.textContent=p.system.label; pill.className='zec-system-pill '+p.system.kind; }} ['grid.value','grid.status','grid.source','mode.mode','mode.text','mode.target','mode.reason','mode.last_change','zendure.actual','zendure.source','primary.actual','primary.status','primary.line','primary.source','source.name','source.device_line','source.auto_text','logging.status','logging.target','logging.db','diag.mqtt','diag.api','diag.effect','diag.flash_protection','diag.offgrid_text','diag.resync'].forEach(path=>{{ const parts=path.split('.'); setVal(path, p[parts[0]]?p[parts[0]][parts[1]]:''); }}); setVal('mode.projection', (p.mode && (p.mode.night_projection || p.mode.fixed_projection)) || ''); setVal('source.age', 'vor '+((p.source&&p.source.age)??'—')+' s'); setVal('source.packets_min', ((p.source&&p.source.packets_min)??0)+'/min'); setVal('source.rejected', (p.source&&p.source.rejected)||''); setVal('logging.db_path', p.logging&&p.logging.db_path ? p.logging.db_path.split('/').pop() : '—'); setVal('diag.loop_ms', ((p.diag&&p.diag.loop_ms)??'—')+' ms'); setVal('zendure.remaining', (p.zendure&&p.zendure.remaining!==null&&p.zendure.remaining!==undefined)?Number(p.zendure.remaining).toLocaleString('de-DE',{{maximumFractionDigits:2}})+' kWh':'nicht berechenbar'); function updateRing(key,soc){{ const ring=q('[data-ring="'+key+'"]'); if(!ring)return; const n=Number(soc); const valid=Number.isFinite(n); ring.style.setProperty('--soc',valid?Math.max(0,Math.min(100,n)):0); const val=ring.querySelector('.soc-ring-value'); if(val) val.textContent=valid?Math.round(n)+' %':'—'; }} updateRing('zendure',p.zendure&&p.zendure.soc); updateRing('primary',p.primary&&p.primary.soc); const warn=q('[data-zec="zendure.command_warning"]'); if(warn){{ const msg=(p.zendure&&p.zendure.command_warning)||''; warn.textContent=msg; warn.style.display=msg?'block':'none'; }} }}
      let statusInFlight=false; async function refreshStatus(){{ if(document.visibilityState==='hidden'||statusInFlight)return; statusInFlight=true; try{{ const r=await fetch('/status-view-data',{{cache:'no-store'}}); if(r.ok) applyStatus(await r.json()); }}catch(e){{}} finally{{statusInFlight=false;}} }} setInterval(refreshStatus,3000); document.addEventListener('visibilitychange',()=>{{ if(document.visibilityState!=='hidden'){{ refreshStatus(); refreshSocDay(); }} }});
      async function refreshGridMiniSparkline(){{ if(document.visibilityState==='hidden') return; const box=q('#gridMiniSparkline'); if(!box)return; try{{ const r=await fetch('/grid-mini-sparkline',{{cache:'no-store'}}); if(r.ok){{ const svg=await r.text(); if(svg.indexOf('<svg')>=0) box.innerHTML=svg; }} }}catch(e){{}} }} setInterval(refreshGridMiniSparkline,10000);
      let chart=null, chartInFlight=false, selectedDate=new Date(); function dateStr(d){{ const y=d.getFullYear(); const m=String(d.getMonth()+1).padStart(2,'0'); const day=String(d.getDate()).padStart(2,'0'); return y+'-'+m+'-'+day; }} function labelDate(d){{ return d.toLocaleDateString('de-DE',{{weekday:'short',day:'2-digit',month:'2-digit',year:'numeric'}}); }} function fmtPower(v){{ if(v===null||v===undefined||v==='')return '—'; const n=Number(v); if(isNaN(n))return String(v); const a=Math.abs(n); const s=n>0?'+':(n<0?'−':''); return s+(a>=1000?(a/1000).toFixed(2).replace('.',',')+' kW':Math.round(a)+' W'); }}
      async function refreshSocDay(){{ if(document.visibilityState==='hidden'||chartInFlight)return; chartInFlight=true; const status=q('#storageSocStatus'); try{{ const ds=dateStr(selectedDate); q('#socDayLabel').textContent=labelDate(selectedDate); q('#dayNext').disabled=ds>=dateStr(new Date()); const r=await fetch('/storage-soc-day-data?date='+encodeURIComponent(ds),{{cache:'no-store'}}); const p=await r.json(); const points=p.points||[]; const data={{datasets:[{{label:'Zendure',data:points.map(x=>({{x:Number(x.minute),y:x.zendure_soc}})),borderWidth:2,pointRadius:0,pointHitRadius:12,pointHoverRadius:3,tension:.22,spanGaps:false}},{{label:'Primärspeicher',data:points.map(x=>({{x:Number(x.minute),y:x.primary_soc}})),borderWidth:2,pointRadius:0,pointHitRadius:12,pointHoverRadius:3,tension:.22,spanGaps:false}}]}}; const opts={{animation:false,responsive:true,maintainAspectRatio:false,interaction:{{mode:'nearest',intersect:false}},plugins:{{legend:{{position:'bottom'}},tooltip:{{callbacks:{{title:(it)=>{{ const m=Number(it[0].raw.x); const h=Math.floor(m/60); const mi=m%60; return p.date+' '+String(h).padStart(2,'0')+':'+String(mi).padStart(2,'0');}},afterBody:(it)=>{{ const x=points.find(pnt=>Number(pnt.minute)===Number(it[0].raw.x))||{{}}; return ['Zendure: '+(x.zendure_soc??'—')+' % · '+fmtPower(x.zendure_power_w),'Primärspeicher: '+(x.primary_soc??'—')+' % · '+fmtPower(x.primary_power_w),'Modus: '+(x.mode||'—'),'Grund: '+(x.reason||'—')];}}}}}}}},scales:{{x:{{type:'linear',min:0,max:1440,ticks:{{stepSize:360,callback:(v)=>String(Math.floor(v/60)).padStart(2,'0')+':00'}}}},y:{{min:0,max:100,ticks:{{callback:(v)=>v+' %'}}}}}}}}; if(!chart) chart=new Chart(q('#storageSocChart').getContext('2d'),{{type:'line',data:data,options:opts}}); else {{chart.data=data; chart.options=opts; chart.update();}} status.textContent=(p.is_today?'Stand: '+(p.last_point_at||'—')+' · aktualisiert alle 60 s':'Vollständiger Tag: '+p.date)+' · Quelle: '+p.source+' · Cache '+(p.cache_status||'-'); }}catch(e){{ status.textContent='SOC-Tagesgraph konnte nicht geladen werden: '+e; }} finally{{chartInFlight=false;}} }}
      q('#dayPrev').onclick=()=>{{ selectedDate.setDate(selectedDate.getDate()-1); refreshSocDay(); }}; q('#dayNext').onclick=()=>{{ const n=new Date(selectedDate); n.setDate(n.getDate()+1); if(dateStr(n)<=dateStr(new Date())){{ selectedDate=n; refreshSocDay(); }} }}; q('#dayToday').onclick=()=>{{ selectedDate=new Date(); refreshSocDay(); }}; refreshSocDay(); setInterval(()=>{{ if(dateStr(selectedDate)===dateStr(new Date())) refreshSocDay(); }},60000);
    }})();
    </script>
    '''
    page += build_footer()
    return page


def build_status_page(cfg: Dict[str, Any], s: Dict[str, Any]) -> str:
    """Render the independently rebuilt V2 status page.

    The historical status-page markup is intentionally not reused.  Only the
    compact view model and the dedicated cached JSON endpoints are shared.
    """
    payload = build_status_view_payload(cfg, s)
    port = int(cfg.get("REPLAY_WEB_PORT", 8090) or 8090)
    return render_status_page_v2(
        cfg,
        payload,
        analysis_available=replay_service_available(cfg),
        analysis_port=port,
    )

def build_graph_page_legacy(cfg: Dict[str, Any]) -> str:
    page = build_base_header("Zendure Controller Graph", cfg=cfg)
    page += """
    <div class="section">
        <div class="section-title-row"><h1>Graph / Live-Verlauf</h1><span class="version-pill">Diagnose</span></div>
        <div class="small">Live-/Verlaufsdiagnose mit Regelkontext. Die Statusseite zeigt die Tagesübersicht; diese Seite erklärt den zeitlichen Verlauf.</div>
        <div class="toolbar">
            <label class="small">Zeitraum <select id="graphRange"><option value="live">Live/RAM</option><option value="15m">Letzte 15 Minuten</option><option value="1h">Letzte Stunde</option><option value="6h">Letzte 6 Stunden</option><option value="24h">Letzte 24 Stunden</option><option value="today">Heute</option></select></label>
            <label class="small">Auflösung <select id="graphResolution"><option value="live">Live</option><option value="1min" selected>1 Minute</option><option value="5min">5 Minuten</option></select></label>
            <label class="small"><input type="checkbox" id="autoRefresh" checked> Auto-Refresh</label>
            <button type="button" onclick="resetSeriesVisibility()">Standardlinien</button>
            <a class="button" href="/graph-data.csv" title="Exportiert den aktuellen RAM-Graph-Verlauf, nicht den vollständigen Measurement-V4-Export.">Graph-Verlauf CSV</a>
        </div>
        <canvas id="powerChart" height="430"></canvas>
        <div id="chartStatus" class="small"></div>
        <div class="small" style="margin-top:10px;">Vorzeichen: Netz + = Bezug, Netz − = Einspeisung. Zendure + = Laden, Zendure − = Entladen. Fehlende/ungültige Daten werden als Lücke dargestellt.</div>
    </div>
    <div class="section"><h2>Kennzahlen im sichtbaren Zeitraum</h2><div id="kpiGrid" class="kpi-grid"></div></div>
    <div class="grid">
        <div class="card"><h2>Leistungsflüsse aktuell</h2><div id="flowBox" class="small">Wird geladen …</div></div>
        <div class="card"><h2>SOC & Modus</h2><div id="socModeBox" class="small">Wird geladen …</div><canvas id="socMiniChart" height="150"></canvas></div>
        <div class="card"><h2>Aktive Signale / Quellen</h2><table id="signalTable"></table></div>
    </div>
    <div class="section"><h2>Ereignisse / Marker</h2><div id="eventBox" class="small">Wird geladen …</div></div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
    const GRAPH_VISIBILITY_KEY = 'zec-graph-visible-series-rc7';
    const DEFAULT_VISIBLE = ['Netzleistung','Zendure Soll','Zendure Ist','Zendure SOC'];
    let chart = null;
    let socMini = null;
    function fmt(v, unit) { if (v === null || v === undefined || v === '') return '-'; const n = Number(v); if (Number.isNaN(n)) return String(v); return (Math.round(n*10)/10).toString() + (unit ? ' ' + unit : ''); }
    function loadVis() { try { return JSON.parse(localStorage.getItem(GRAPH_VISIBILITY_KEY) || '{}'); } catch(e) { return {}; } }
    function saveVis() { if (!chart) return; const v={}; chart.data.datasets.forEach((d,i)=>v[d.label]=chart.isDatasetVisible(i)); try { localStorage.setItem(GRAPH_VISIBILITY_KEY, JSON.stringify(v)); } catch(e) {} }
    function resetSeriesVisibility() { try { localStorage.removeItem(GRAPH_VISIBILITY_KEY); } catch(e) {} updateGraph(); }
    function dataset(label, key, points, axis, hiddenDefault, dashed) {
        const vis = loadVis();
        let hidden = hiddenDefault;
        if (Object.prototype.hasOwnProperty.call(vis, label)) hidden = !vis[label];
        return { label: label, data: points.map(p => p[key] === undefined ? null : p[key]), borderWidth:2, pointRadius:0, yAxisID:axis || 'y', hidden:hidden, spanGaps:false, borderDash:dashed?[6,5]:undefined, tension:0.2 };
    }
    function buildDatasets(points, available) {
        const ds = [
            dataset('Netzleistung','grid_power_w',points,'y',false,false),
            dataset('Zendure Soll','zendure_target_power_w',points,'y',false,true),
            dataset('Zendure Ist','zendure_actual_power_w',points,'y',false,false),
            dataset('Zendure SOC','soc',points,'y1',false,true)
        ];
        if (available && available.pv_power_w) ds.splice(3,0,dataset('PV-Leistung','pv_power_w',points,'y',false,false));
        if (available && available.house_power_w) ds.splice(3,0,dataset('Hausverbrauch','house_power_w',points,'y',false,false));
        ds.push(dataset('Netz Rohwert','grid_power_raw_w',points,'y',true,false));
        return ds;
    }
    function renderKpis(kpis) {
        const defs = [
            ['Netzleistung','grid_power_w','W'], ['Zendure Soll','zendure_target_power_w','W'], ['Zendure Ist','zendure_actual_power_w','W'], ['PV-Leistung','pv_power_w','W'], ['Hausverbrauch','house_power_w','W'], ['SOC','soc','%']
        ];
        let html='';
        defs.forEach(([label,key,unit]) => { const k=(kpis||{})[key]||{}; if(!k.available) return; if(key==='soc') html += `<div class="kpi"><div class="small">${label}</div><div class="num">${fmt(k.current,unit)}</div><div class="small">Start ${fmt(k.start,unit)} · Min ${fmt(k.min,unit)} · Max ${fmt(k.max,unit)} · Ende ${fmt(k.end,unit)}</div></div>`; else html += `<div class="kpi"><div class="small">${label}</div><div class="num">${fmt(k.current,unit)}</div><div class="small">Min ${fmt(k.min,unit)} · Max ${fmt(k.max,unit)} · Ø ${fmt(k.avg,unit)}</div></div>`; });
        document.getElementById('kpiGrid').innerHTML = html || '<div class="small">Keine Kennzahlen verfügbar.</div>';
    }
    function renderSignals(signals) {
        let html='<tr><th>Signal</th><th>Wert</th><th>Quelle</th><th>Status</th></tr>';
        (signals||[]).forEach(s => { html += `<tr><td>${s.signal||''}</td><td>${fmt(s.value,s.unit||'')}</td><td>${s.source||'-'}</td><td>${s.status||'-'}</td></tr>`; });
        document.getElementById('signalTable').innerHTML = html;
    }
    function renderEvents(events) {
        if(!events || !events.length) { document.getElementById('eventBox').innerHTML='Keine relevanten Marker im sichtbaren Zeitraum.'; return; }
        document.getElementById('eventBox').innerHTML = events.slice(-35).map(e => `<span class="event-pill">${e.time||''} · ${e.label||e.type}</span>`).join('');
    }
    function renderFlow(points) {
        const p = points && points.length ? points[points.length-1] : {};
        const grid = Number(p.grid_power_w||0), z = Number(p.zendure_actual_power_w||0);
        document.getElementById('flowBox').innerHTML = `<div>Netz: <b>${fmt(grid,'W')}</b> (${grid>=0?'Bezug':'Einspeisung'})</div><div>Zendure: <b>${fmt(z,'W')}</b> (${z>=0?'Laden':'Entladen'})</div><div>PV/Haus werden angezeigt, sobald valide Daten verfügbar sind.</div>`;
        document.getElementById('socModeBox').innerHTML = `<b>${fmt(p.soc,'%')}</b><br>Modus: ${p.mode_label||p.mode||'-'}<br>Grund: ${p.control_reason||'-'}<br>Datenstatus: ${p.data_status||'-'}`;
    }
    function renderSocMini(points) {
        if (!window.Chart) return;
        const labels = points.map(p=>p.time);
        const values = points.map(p=>p.soc);
        const data = {labels:labels, datasets:[{label:'SOC', data:values, borderWidth:2, pointRadius:0, tension:.25}]};
        const options = {animation:false, plugins:{legend:{display:false}}, scales:{y:{min:0,max:100}, x:{display:false}}};
        if(!socMini) socMini = new Chart(document.getElementById('socMiniChart').getContext('2d'), {type:'line',data:data,options:options}); else {socMini.data=data; socMini.update();}
    }
    async function updateGraph() {
        const range = document.getElementById('graphRange').value;
        const resolution = document.getElementById('graphResolution').value;
        const res = await fetch('/graph-view-data?range='+encodeURIComponent(range)+'&resolution='+encodeURIComponent(resolution));
        const payload = await res.json();
        const points = payload.points || [];
        const labels = points.map(p => p.time || p.datetime_local || '');
        renderKpis(payload.kpis || {}); renderSignals(payload.signals || []); renderEvents(payload.events || []); renderFlow(points); renderSocMini(points);
        document.getElementById('chartStatus').innerText = 'Quelle: ' + (payload.source || '-') + ' · Punkte: ' + points.length;
        if (!window.Chart) { document.getElementById('chartStatus').innerText += ' · Chart.js nicht geladen.'; return; }
        const datasets = buildDatasets(points, payload.series_available || {});
        const options = { animation:false, responsive:true, interaction:{mode:'index',intersect:false}, plugins:{ legend:{display:true,onClick:function(e,item,legend){Chart.defaults.plugins.legend.onClick(e,item,legend); saveVis();}}, tooltip:{callbacks:{afterBody:function(items){ const p=points[items[0].dataIndex]||{}; return ['Modus: '+(p.mode_label||p.mode||'-'), 'Regelgrund: '+(p.control_reason||'-'), 'Limiter/Schutz: '+(p.limit_reason||'-'), 'Datenstatus: '+(p.data_status||'-')]; }}}}, scales:{ y:{title:{display:true,text:'Leistung (W)'}}, y1:{position:'right', min:0, max:100, title:{display:true,text:'SOC (%)'}} } };
        if (!chart) chart = new Chart(document.getElementById('powerChart').getContext('2d'), {type:'line', data:{datasets:datasets}, options:options}); else { chart.data.datasets=datasets; chart.options=options; chart.update(); }
    }
    document.getElementById('graphRange').addEventListener('change', updateGraph);
    document.getElementById('graphResolution').addEventListener('change', updateGraph);
    setInterval(function(){ if(document.getElementById('autoRefresh').checked) updateGraph(); }, 5000);
    updateGraph(true);
    </script>
    """
    page += build_footer()
    return page




def build_graph_page(cfg: Dict[str, Any], s: Optional[Dict[str, Any]] = None) -> str:
    status_payload = build_status_view_payload(cfg, dict(s or {})) if s is not None else {
        "system": {"kind": "unknown", "label": "Status wird geladen", "warnings": []},
        "server_time": datetime.now().strftime("%H:%M:%S"),
    }
    page = _modern_body_start(
        cfg,
        "graph",
        force_dark=True,
        system_payload=status_payload.get("system"),
        server_time=str(status_payload.get("server_time") or ""),
    )
    page += """
    <main class="modern-page zec-shell">
      <section class="zec-panel zec-panel-lg">
        <div class="zec-page-title">
          <div><h1>Graph / Live-Verlauf</h1><div class="zec-page-note">Live-/Verlaufsdiagnose im Mock-up-Layout. Der Legacy-Graph bleibt im Expertenmenü verfügbar.</div></div>
          <div class="zec-control-group"><span id="chartStatus" class="zec-status-badge ok">lädt…</span><span class="zec-status-badge">V{APP_VERSION}</span></div>
        </div>
        <div class="zec-graph-toolbar">
          <div class="zec-control-group">
            <label class="zec-control">Zeitraum <select id="graphRange"><option value="live">Live/RAM</option><option value="15m">Letzte 15 Minuten</option><option value="1h">Letzte Stunde</option><option value="6h">Letzte 6 Stunden</option><option value="24h" selected>Letzte 24 Stunden</option><option value="today">Heute</option></select></label>
            <label class="zec-control">Auflösung <select id="graphResolution"><option value="live">Live</option><option value="1min" selected>1 Minute</option><option value="5min">5 Minuten</option></select></label>
            <label class="zec-control"><input type="checkbox" id="autoRefresh" checked> Auto-Refresh</label>
          </div>
          <div class="zec-control-group"><button class="zec-btn" type="button" onclick="resetSeriesVisibility()">Linien zurücksetzen</button><a class="zec-btn" href="/graph-data.csv">Graph-Verlauf CSV</a><a class="zec-btn" href="/graph_old">Alter Graph</a></div>
        </div>
        <div class="zec-chart-card"><canvas id="powerChart" height="430"></canvas></div>
      </section>

      <section class="zec-panel">
        <div class="zec-panel-header"><div><h2>Kennzahlen im sichtbaren Zeitraum</h2><div class="zec-panel-desc">Aktuell, Minimum, Maximum und Durchschnitt; SOC mit Start/Ende.</div></div></div>
        <div id="kpiGrid" class="zec-kpi-strip"></div>
      </section>

      <div class="zec-bottom-grid">
        <section class="zec-panel"><h2>Leistungsflüsse aktuell</h2><div id="flowBox" class="zec-panel-desc">lädt…</div></section>
        <section class="zec-panel"><h2>SOC & Modus</h2><div id="socModeBox" class="zec-panel-desc">lädt…</div><canvas id="socMiniChart" height="120"></canvas></section>
        <section class="zec-panel"><h2>Ereignisse / Marker</h2><div id="eventBox" class="zec-panel-desc">lädt…</div></section>
      </div>

      <section class="zec-panel">
        <div class="zec-panel-header"><div><h2>Aktive Signale / Quellen</h2><div class="zec-panel-desc">Aktueller Datenstatus der im Graph verwendeten Signale.</div></div></div>
        <table id="signalTable" class="zec-signal-table"></table>
      </section>
    </main>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
    const GRAPH_VISIBILITY_KEY = 'zec-graph-visible-series-rc12';
    let chart = null;
    let socMini = null;
    let graphRequestInFlight = false;
    const SERIES_COLORS = {'Netzleistung':'#2f8cff','Zendure Soll':'#20d6d2','Zendure Ist':'#48c85a','Hausverbrauch':'#fb923c','PV-Leistung':'#facc15','Zendure SOC':'#a78bfa','Netz Rohwert':'#64748b'};
    function fmt(v,u) { if(v===null || v===undefined || Number.isNaN(Number(v))) return '-'; const n=Number(v); if(u==='W') return Math.round(n)+' W'; if(u==='%') return Math.round(n)+' %'; return String(v); }
    function loadVis() { try { return JSON.parse(localStorage.getItem(GRAPH_VISIBILITY_KEY)||'{}'); } catch(e) { return {}; } }
    function saveVis() { if(!chart) return; const v={}; chart.data.datasets.forEach((d,i)=>v[d.label]=chart.isDatasetVisible(i)); try { localStorage.setItem(GRAPH_VISIBILITY_KEY, JSON.stringify(v)); } catch(e) {} }
    function resetSeriesVisibility() { try { localStorage.removeItem(GRAPH_VISIBILITY_KEY); } catch(e) {} updateGraph(); }
    function dataset(label, key, points, axis, hiddenDefault, dashed) {
        const vis = loadVis(); let hidden = hiddenDefault; if (Object.prototype.hasOwnProperty.call(vis, label)) hidden = !vis[label]; const color = SERIES_COLORS[label] || '#38bdf8';
        return { label: label, data: points.map(p => ({x:Number(p.epoch_ms||0), y:(p[key] === undefined ? null : p[key])})), parsing:false, borderColor:color, backgroundColor:color+'33', borderWidth:2.4, pointRadius:0, pointHitRadius:18, pointHoverRadius:4, yAxisID:axis || 'y', hidden:hidden, spanGaps:false, borderDash:dashed?[6,5]:undefined, tension:0.18 };
    }
    function buildDatasets(points, available) {
        const ds = [dataset('Netzleistung','grid_power_w',points,'y',false,false), dataset('Zendure Soll','zendure_target_power_w',points,'y',false,true), dataset('Zendure Ist','zendure_actual_power_w',points,'y',false,false)];
        if (available && available.house_power_w) ds.push(dataset('Hausverbrauch','house_power_w',points,'y',false,false));
        if (available && available.pv_power_w) ds.push(dataset('PV-Leistung','pv_power_w',points,'y',false,false));
        ds.push(dataset('Zendure SOC','soc',points,'y1',false,true)); return ds;
    }
    function renderKpis(kpis) {
        const defs = [['Netzleistung','grid_power_w','W'], ['Zendure Soll','zendure_target_power_w','W'], ['Zendure Ist','zendure_actual_power_w','W'], ['PV-Leistung','pv_power_w','W'], ['Hausverbrauch','house_power_w','W'], ['SOC','soc','%']];
        let html=''; defs.forEach(([label,key,unit]) => { const k=(kpis||{})[key]||{}; if(!k.available) return; if(key==='soc') html += `<div class="zec-kpi"><div class="k-label">${label}</div><div class="k-num">${fmt(k.current,unit)}</div><div class="k-sub">Start ${fmt(k.start,unit)} · Min ${fmt(k.min,unit)} · Max ${fmt(k.max,unit)} · Ende ${fmt(k.end,unit)}</div></div>`; else html += `<div class="zec-kpi"><div class="k-label">${label}</div><div class="k-num">${fmt(k.current,unit)}</div><div class="k-sub">Min ${fmt(k.min,unit)} · Max ${fmt(k.max,unit)} · Ø ${fmt(k.avg,unit)}</div></div>`; });
        document.getElementById('kpiGrid').innerHTML = html || '<div class="zec-kpi"><div class="k-label">Keine Kennzahlen verfügbar.</div></div>';
    }
    function renderSignals(signals) { let html='<tr><th>Signal / Quelle</th><th>Wert</th><th>Quelle</th><th>Status</th></tr>'; (signals||[]).forEach(s => { const ok=(s.status||'').toLowerCase().includes('gültig')||(s.status||'').toLowerCase().includes('verbunden'); const badge='<span class="zec-status-badge '+(ok?'signal-ok':'signal-warn')+'">'+(s.status||'-')+'</span>'; html += `<tr><td>${s.signal||''}</td><td>${fmt(s.value,s.unit||'')}</td><td>${s.source||'-'}</td><td>${badge}</td></tr>`; }); document.getElementById('signalTable').innerHTML = html; }
    function renderEvents(events) { if(!events || !events.length) { document.getElementById('eventBox').innerHTML='Keine relevanten Marker im sichtbaren Zeitraum.'; return; } document.getElementById('eventBox').innerHTML = events.slice(-35).map(e => `<span class="event-pill">${e.time||''} · ${e.label||e.type}</span>`).join(''); }
    function renderFlow(points) { const p = points && points.length ? points[points.length-1] : {}; const grid = Number(p.grid_power_w||0), z = Number(p.zendure_actual_power_w||0); document.getElementById('flowBox').innerHTML = `<div class="zec-flow-line"><span class="name">Netz</span><span class="val">${fmt(grid,'W')}</span></div><div class="zec-flow-line"><span class="name">Zendure Batterie</span><span class="val">${fmt(z,'W')}</span></div><div class="zec-panel-desc">PV/Haus erscheinen, sobald valide Daten verfügbar sind.</div>`; document.getElementById('socModeBox').innerHTML = `<div class="soc-ring" style="--soc:${Math.max(0,Math.min(100,Number(p.soc||0)))}%"><span>${fmt(p.soc,'%')}</span></div><div class="zec-panel-desc">Modus: ${p.mode_label||p.mode||'-'}<br>Grund: ${p.control_reason||'-'}<br>Datenstatus: ${p.data_status||'-'}</div>`; }
    function renderSocMini(points) { if (!window.Chart) return; const labels = points.map(p=>p.time); const values = points.map(p=>p.soc); const data = {labels:labels, datasets:[{label:'SOC', data:values, borderColor:'#a78bfa', backgroundColor:'rgba(167,139,250,.15)', borderWidth:2, pointRadius:0, pointHitRadius:14, pointHoverRadius:4, tension:.25}]}; const options = {animation:false, interaction:{mode:'nearest', axis:'x', intersect:false}, plugins:{legend:{display:false}, tooltip:{mode:'nearest', intersect:false}}, scales:{y:{min:0,max:100,ticks:{color:'#8191a6'},grid:{color:'rgba(148,163,184,.08)'}}, x:{display:false}}}; if(!socMini) socMini = new Chart(document.getElementById('socMiniChart').getContext('2d'), {type:'line',data:data,options:options}); else {socMini.data=data; socMini.update();} }
    async function updateGraph(force) {
        if (document.visibilityState === 'hidden') return;
        if (graphRequestInFlight && !force) return;
        graphRequestInFlight = true;
        const range = document.getElementById('graphRange').value; const resolution = document.getElementById('graphResolution').value;
        const ctrl = new AbortController(); const timer = setTimeout(function(){ ctrl.abort(); }, 30000);
        try {
          document.getElementById('chartStatus').innerText = 'Graphdaten werden geladen…';
          const res = await fetch('/graph-view-data?range='+encodeURIComponent(range)+'&resolution='+encodeURIComponent(resolution), {signal: ctrl.signal, cache:'no-store'});
          clearTimeout(timer);
          const payload = await res.json(); const points = payload.points || []; const r = payload.range || {}; const axisMin = Number(r.axis_start_epoch_ms || (points[0] && points[0].epoch_ms) || Date.now()-3600000); const axisMax = Number(r.axis_end_epoch_ms || (points[points.length-1] && points[points.length-1].epoch_ms) || Date.now());
          renderKpis(payload.kpis || {}); renderSignals(payload.signals || []); renderEvents(payload.events || []); renderFlow(points); renderSocMini(points); const rangeText = r.label ? (' · Zeitraum: ' + r.label) : ''; document.getElementById('chartStatus').innerText = 'Quelle: ' + (payload.source || '-') + ' · Punkte: ' + points.length + rangeText + ' · Cache: ' + (payload.cache_status || '-');
        if (!window.Chart) { document.getElementById('chartStatus').innerText += ' · Chart.js nicht geladen.'; return; }
        const datasets = buildDatasets(points, payload.series_available || {});
        const options = { animation:false, responsive:true, maintainAspectRatio:false, interaction:{mode:'index', axis:'x', intersect:false}, plugins:{ legend:{labels:{color:'#cbd5e1', boxWidth:26}, onClick:function(e,item,legend){Chart.defaults.plugins.legend.onClick(e,item,legend); saveVis();}}, tooltip:{mode:'index', intersect:false, backgroundColor:'rgba(8,18,31,.96)', borderColor:'rgba(148,163,184,.22)', borderWidth:1, callbacks:{afterBody:function(items){ const p=points[items[0].dataIndex]||{}; return ['Modus: '+(p.mode_label||p.mode||'-'), 'Regelgrund: '+(p.control_reason||'-'), 'Limiter/Schutz: '+(p.limit_reason||'-'), 'Datenstatus: '+(p.data_status||'-')]; }}}}, scales:{ y:{title:{display:true,text:'Leistung (W)',color:'#94a3b8'}, ticks:{color:'#8191a6'}, grid:{color:'rgba(148,163,184,.10)'}}, y1:{position:'right', min:0, max:100, title:{display:true,text:'SOC (%)',color:'#94a3b8'}, ticks:{color:'#8191a6'}, grid:{drawOnChartArea:false}}, x:{type:'linear', min:axisMin, max:axisMax, ticks:{color:'#8191a6', maxRotation:0, autoSkip:true, maxTicksLimit:9, callback:function(v){try{ const d=new Date(Number(v)); const span=Math.abs(axisMax-axisMin); if(span >= 18*3600000) return d.toLocaleDateString('de-DE',{day:'2-digit',month:'2-digit'})+' '+d.toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'}); return d.toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'});}catch(e){return ''+v;}}}, grid:{color:'rgba(148,163,184,.06)'}} } };
        if (!chart) chart = new Chart(document.getElementById('powerChart').getContext('2d'), {type:'line', data:{datasets:datasets}, options:options}); else { chart.data.datasets=datasets; chart.options=options; chart.update(); }
        } catch(e) {
          clearTimeout(timer);
          document.getElementById('chartStatus').innerText = (e && e.name === 'AbortError') ? 'Graphdaten werden noch vorbereitet. Bitte in einigen Sekunden erneut laden.' : ('Graph konnte nicht geladen werden: '+e);
        } finally {
          graphRequestInFlight = false;
        }
    }
    document.getElementById('graphRange').addEventListener('change', function(){ updateGraph(true); }); document.getElementById('graphResolution').addEventListener('change', function(){ updateGraph(true); });
    setInterval(function(){ if(document.getElementById('autoRefresh').checked && document.visibilityState !== 'hidden') updateGraph(); }, 5000);
    document.addEventListener('visibilitychange', function(){ if(document.visibilityState !== 'hidden') updateGraph(); });
    updateGraph(true);
    </script>
    """
    page = page.replace("V{APP_VERSION}", "V" + APP_VERSION)
    page += build_footer()
    return page



def _issue_list_html(issues: List[ValidationIssue]) -> str:
    return "".join(f"<li>{html.escape(issue.message)}</li>" for issue in issues)


def build_validation_messages(validation_issues: Optional[List[ValidationIssue]], validation_state: str = "") -> str:
    if not validation_issues:
        return ""
    buckets = split_issues(validation_issues)
    parts: List[str] = []
    has_errors = bool(buckets.get("ERROR"))

    if has_errors:
        error_rows = _issue_list_html(buckets["ERROR"])
        warning_rows = _issue_list_html(buckets.get("WARNING", []))
        info_rows = _issue_list_html(buckets.get("INFO", []))
        additional_parts: List[str] = []
        if warning_rows:
            additional_parts.append(
                "<div class='warning-box'>"
                "<b>Zusätzliche Warnungen:</b> Diese Punkte sind ebenfalls auffällig, "
                "werden aber erst relevant, nachdem die Fehler behoben wurden."
                f"<ul>{warning_rows}</ul>"
                "</div>"
            )
        if info_rows:
            additional_parts.append(
                "<div class='info-box'>"
                "<b>Zusätzliche Hinweise:</b>"
                f"<ul>{info_rows}</ul>"
                "</div>"
            )
        modal = ""
        if validation_state == "error":
            modal = (
                "<div id='validationModal' class='validation-modal' role='dialog' aria-modal='true'>"
                "<div class='validation-modal-content'>"
                "<h2>Konfiguration wurde nicht gespeichert</h2>"
                "<p>Mindestens eine Einstellung ist unvollständig, widersprüchlich oder nicht erreichbar. "
                "Die betroffenen Felder sind rot markiert. Warnungen werden erst nach Behebung der Fehler gesondert behandelt.</p>"
                f"<ul>{error_rows}</ul>"
                "<button type='button' onclick='closeValidationModal()'>Dialog schließen und Fehler prüfen</button>"
                "</div></div>"
            )
        intro = "Konfiguration wurde nicht gespeichert." if validation_state == "error" else "Konfigurationsprüfung"
        parts.append(
            "<div class='error-box'>"
            f"<b>{intro}</b> "
            "Bitte korrigiere die folgenden Fehler. Die bisherigen Einstellungen bleiben unverändert."
            f"<ul>{error_rows}</ul>"
            "</div>"
            + "".join(additional_parts) + modal
        )
        return "".join(parts)

    if buckets.get("WARNING"):
        rows = _issue_list_html(buckets["WARNING"])
        confirm_button = ""
        if validation_state == "warning":
            confirm_button = (
                "<button class='confirm-warning-button' type='submit' name='_confirm_warnings' value='1'>"
                "Trotz Warnungen speichern"
                "</button>"
            )
        parts.append(
            "<div class='warning-box'>"
            "<b>Warnung:</b> Die Konfiguration enthält auffällige, aber nicht zwingend falsche Einstellungen. "
            "Bitte prüfe die folgenden Hinweise."
            f"<ul>{rows}</ul>"
            f"{confirm_button}"
            "</div>"
            + ((
                "<div id='validationModal' class='validation-modal' role='dialog' aria-modal='true'>"
                "<div class='validation-modal-content warning'>"
                "<h2>Konfiguration enthält Warnungen</h2>"
                "<p>Das Speichern ist möglich, aber die folgenden Punkte sollten bewusst bestätigt werden. "
                "Betroffene Felder sind gelb markiert.</p>"
                f"<ul>{rows}</ul>"
                f"{confirm_button} "
                "<button type='button' onclick='closeValidationModal()'>Zurück zur Prüfung</button>"
                "</div></div>"
            ) if validation_state == "warning" else "")
        )

    if buckets.get("INFO"):
        rows = _issue_list_html(buckets["INFO"])
        parts.append(
            "<div class='info-box'>"
            "<b>Hinweis:</b>"
            f"<ul>{rows}</ul>"
            "</div>"
        )

    return "".join(parts)


def validation_issue_keys(validation_issues: Optional[List[ValidationIssue]], severity: str = "") -> set:
    if not validation_issues:
        return set()
    severity = severity.upper()
    keys = set()
    for issue in validation_issues:
        if severity and issue.severity.upper() != severity:
            continue
        keys.update(issue.keys)
    return keys


def build_section_validation_messages(group: str, validation_issues: Optional[List[ValidationIssue]]) -> str:
    if not validation_issues:
        return ""
    group_issues = [issue for issue in validation_issues if issue.group == group]
    if not group_issues:
        return ""
    buckets = split_issues(group_issues)
    html_parts: List[str] = []
    if buckets.get("ERROR"):
        html_parts.append(
            "<div class='section-error'>"
            "<b>Fehler in diesem Bereich:</b> Die Konfiguration wurde nicht gespeichert. "
            "Bitte prüfe die rot markierten Felder."
            f"<ul>{_issue_list_html(buckets['ERROR'])}</ul>"
            "</div>"
        )
    if buckets.get("WARNING"):
        html_parts.append(
            "<div class='section-warning'>"
            "<b>Warnung in diesem Bereich:</b> Speichern ist nach Bestätigung möglich. "
            "Bitte prüfe die gelb markierten Felder."
            f"<ul>{_issue_list_html(buckets['WARNING'])}</ul>"
            "</div>"
        )
    if buckets.get("INFO"):
        html_parts.append(
            "<div class='info-box'>"
            "<b>Hinweis in diesem Bereich:</b>"
            f"<ul>{_issue_list_html(buckets['INFO'])}</ul>"
            "</div>"
        )
    return "".join(html_parts)

def build_save_result_message(cfg: Dict[str, Any], saved: bool = False, restart_required: bool = False, restart_keys: str = "") -> str:
    if not saved:
        return ""
    if restart_required:
        keys = [k for k in restart_keys.split(",") if k]
        labels = restart_labels(keys)
        manual_cmd = "sudo systemctl restart zendure-controller.service"
        restart_form = ""
        if service_restart_enabled(cfg):
            restart_form = (
                "<div style='margin-top:12px;'>"
                "<button class='save save-small' type='submit' formaction='/restart-service' formmethod='post'>"
                "Dienst jetzt neu starten"
                "</button>"
                "</div>"
            )
        else:
            restart_form = (
                "<div class='small' style='margin-top:10px;'>Der Neustart aus der Weboberfläche ist deaktiviert. "
                "Starte den Dienst bei Bedarf manuell mit:<br>"
                f"<code>{html.escape(manual_cmd)}</code></div>"
            )
        return (
            "<div class='warning-box'>"
            "<b>Konfiguration gespeichert - Dienstneustart erforderlich oder empfohlen.</b><br>"
            "Die Änderung betrifft Parameter, die Verbindungen, MQTT-Abonnements, lokale API-Zugriffe oder den Webserver beeinflussen. "
            f"Betroffene Einstellungen: <b>{html.escape(labels)}</b>."
            f"{restart_form}"
            "</div>"
        )
    return "<div class='info-box'><b>Konfiguration gespeichert.</b> Die Änderungen wurden übernommen.</div>"


def build_restart_service_page(cfg: Dict[str, Any], enabled: bool = True, error: str = "", redirect_url: str = "/") -> str:
    page = build_base_header("Zendure Service Neustart", cfg={**cfg, "__hide_nav": True})
    if error:
        body = (
            "<h1>Dienstneustart fehlgeschlagen</h1>"
            f"<div class='error-box'><b>Fehler:</b> {html.escape(error)}</div>"
            "<p>Bitte starte den Dienst manuell:</p>"
            "<pre>sudo systemctl restart zendure-controller.service</pre>"
            "<p><a href='/settings'>Zurück zu den Settings</a></p>"
        )
    elif not enabled:
        body = (
            "<h1>Dienstneustart nicht aktiviert</h1>"
            "<div class='warning-box'>Der Neustart aus der Weboberfläche ist deaktiviert oder nicht konfiguriert. "
            "Aktiviere WEB_SERVICE_RESTART_ENABLED und richte das root-geschützte Hilfsscript ein.</div>"
            "<p>Manueller Befehl:</p><pre>sudo systemctl restart zendure-controller.service</pre>"
            "<p><a href='/settings'>Zurück zu den Settings</a></p>"
        )
    else:
        body = (
            "<h1>Dienstneustart wird ausgeführt</h1>"
            "<div class='info-box'>Der Neustart wurde ausgelöst. Die Verbindung zur Weboberfläche kann für einige Sekunden unterbrochen werden.</div>"
            "<p>Die Hauptseite wird nach kurzer Wartezeit automatisch geöffnet.</p>"
            f"<script>setTimeout(function(){{ window.location.href='{html.escape(redirect_url, quote=True)}'; }}, 10000);</script>"
            f"<p><a href='{html.escape(redirect_url, quote=True)}'>Hauptseite öffnen</a></p>"
        )
    page += f"<div class='section'>{body}</div>"
    page += build_footer()
    return page



def section_intro_text(group: str) -> str:
    texts = {
        "Netzwerk": "Verbindungsparameter für Shelly-kompatible HTTP-Quelle, SMA-Direktquelle, MQTT, Zendure-Local-API und Diagnosezugriffe. Änderungen an Broker, Topics, Ports oder lokalen API-Zielen können einen Dienstneustart erfordern.",
        "Weboberfläche": "Darstellung und Bedienfunktionen der ZEC-Webseiten. Diese Einstellungen verändern die Oberfläche, nicht die eigentliche Regelstrategie.",
        "Regelung": "Grundparameter der AUTO-Regelung: Totzone, Glättung, Schrittweite, Lade-/Entladegrenzen und SOC-Grenzen. Diese Werte bestimmen die Dynamik des Controllers.",
        "Manueller Modus": "Manuelle Modi übersteuern die automatische Netzleistungsregelung bewusst. Feste Lade-/Entladevorgänge sollten nur zeitweise und mit passenden SOC-Zielen genutzt werden.",
        "Zweitbatterie": "Dieser Bereich konfiguriert das Zusammenspiel zwischen Primärspeicher und Zendure: Messwerte des Primärspeichers, Cross-Charge-Schutz und Restüberschuss-Ernte.",
        "Nachtmodus": "Der Nachtmodus entlädt Zendure in einem festen Zeitfenster mit fester Leistung. Die Reserve-SOC-Grenze schützt vor zu tiefer Entladung; die Prognose zeigt, ob die Entladung voraussichtlich bis zum Zeitfenster-Ende reicht.",
        "Sicherheit / Fallback": "Sicherheitsgrenzen und Fehlerreaktionen. Diese Einstellungen bestimmen, wann der Controller bei fehlenden oder nicht aktuellen Daten vorsichtig wird.",
        "Messdaten / Historie": "Legt fest, ob und wohin V4-Messdaten geschrieben werden. Logging darf die Live-Regelung nicht gefährden; bei Problemen läuft die Regelung weiter.",
        "Analyse / Replay": "Grenzen für lokale Pi-sichere Analysen. Größere Datenmengen sollten bewusst bestätigt oder offline ausgewertet werden.",
        "Logging": "Runtime-Textlogs und Debug-Ausgaben. Diese Logs dienen Fehlersuche und Betrieb, ersetzen aber nicht das strukturierte V4-Measurement.",
    }
    return texts.get(group, "")

def section_intro_box(group: str) -> str:
    text = section_intro_text(group)
    if not text:
        return ""
    return f"<div class='card section-intro-card'><h3>{html.escape(group)} – Überblick</h3><div class='small'>{html.escape(text)}</div></div>"

def subgroup_help_text(subgroup: str) -> str:
    texts = {
        "Zweitbatterie-Messwerte": "<div class='small'>Hier wird festgelegt, woher die Leistung der Zweitbatterie bzw. des Primärspeichers kommt und wie deren Vorzeichen zu interpretieren ist. Für ZEC gilt: positiv = Zweitbatterie lädt, negativ = Zweitbatterie entlädt.</div>",
        "Cross-Charge-Schutz": "<div class='small'>Der Schutz verhindert Gegenfluss zwischen Primärspeicher und Zendure. Er bleibt das Sicherheitsnetz für alle Funktionen, die Zweitbatterie- und Zendure-Leistung koordinieren.</div>",
        "Restüberschuss-Ernte": "<div class='small'>Diese Funktion ist nur im AUTO-Modus wirksam. Sie startet erst, wenn der Primärspeicher für eine gewisse Zeit nahe seiner Ladegrenze lädt und gleichzeitig Netzexport anliegt. Kurze Wolkenlücken lösen die Funktion nicht sofort aus.</div>",
    }
    return texts.get(subgroup, "")


def build_settings_page(
    cfg: Dict[str, Any],
    validation_issues: Optional[List[ValidationIssue]] = None,
    validation_state: str = "",
    saved: bool = False,
    restart_required: bool = False,
    restart_keys: str = "",
    csrf_token: str = "",
    system_payload: Optional[Dict[str, Any]] = None,
    server_time: str = "",
) -> str:
    """Render the RC20 settings application inside the shared ZEC shell."""
    token = html.escape(csrf_token, quote=True)
    topbar = render_global_topbar(
        active="settings",
        analysis_available=replay_service_available(cfg),
        analysis_port=int(cfg.get("REPLAY_WEB_PORT", 8090) or 8090),
        system=system_payload,
        server_time=server_time,
    )
    return f"""<!doctype html>
<html lang="de" data-theme="{'dark' if bool(cfg.get('UI_DARK_MODE', False)) else 'light'}"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="zec-csrf" content="{token}">
<meta name="robots" content="noindex,nofollow">
<title>Einstellungen · Zendure Energy Controller</title>
<link rel="icon" href="/favicon.svg">
<link rel="stylesheet" href="/static/status_v2.css?v={html.escape(APP_VERSION_LABEL)}">
<link rel="stylesheet" href="/static/settings_v2.css?v={html.escape(APP_VERSION_LABEL)}">
</head><body class="zec-settings-v2">
{topbar}
<div class="settings-contextbar">
  <button id="mobileMenu" class="mobile-menu" type="button" aria-label="Kategorien öffnen" aria-expanded="false" aria-controls="settingsSidebar">☰</button>
  <div class="settings-title-block"><div class="settings-title">ZEC Settings</div><div class="settings-subtitle">Konfiguration, Regelung und Diagnose</div></div>
  <div class="header-statuses">
    <span id="headerVersion" class="header-pill">{html.escape(APP_VERSION_LABEL)}</span>
    <span id="headerSource" class="header-pill">Config: …</span>
    <span id="headerReady" class="header-pill"><span class="health-dot"></span> Ready: …</span>
  </div>
  <div class="header-spacer"></div>
  <button id="openConfigStates" class="toolbar-button" type="button">▣ Konfigurationsstände</button>
  <button id="openSearch" class="toolbar-button" type="button">⌕ Suche</button>
  <div class="mode-toggle" role="group" aria-label="Ansicht"><button type="button" data-mode="standard">Standard</button><button type="button" data-mode="expert">Experte</button></div>
  <div class="config-health"><span id="healthDot" class="health-dot"></span><span id="healthText">Konfiguration wird geprüft</span></div>
</div>
<div class="settings-app">
  <aside id="settingsSidebar" class="settings-sidebar" aria-label="Einstellungskategorien" aria-hidden="true">
    <nav id="settingsNav" class="sidebar-nav"></nav>
    <div id="sidebarVersion" class="sidebar-version">Controller: {html.escape(APP_VERSION_LABEL)}</div>
  </aside>
  <main class="settings-main">
    <details id="mobileCategories" class="mobile-categories"><summary>Kategorie auswählen</summary><div id="mobileCategoryList"></div></details>
    <div id="settingsContent" class="loading">Settings-Modell wird geladen …</div>
  </main>
</div>
<div id="categoryDrawerBackdrop" class="category-drawer-backdrop" hidden></div>
<div class="save-bar"><div id="dirtyCount" class="dirty-count"><span class="dot"></span><span id="dirtyText">Keine ungespeicherten Änderungen</span></div><div class="save-spacer"></div><button id="restartAction" class="discard-btn" type="button" hidden>Dienst neu starten</button><button id="discardChanges" class="discard-btn" type="button" disabled>Verwerfen</button><button id="reviewChanges" class="review-btn" type="button" disabled>Änderungen prüfen</button></div>
<aside id="searchDrawer" class="search-drawer" aria-hidden="true" aria-label="Einstellungen durchsuchen"><div class="search-drawer-head"><h2>Settings durchsuchen</h2><button id="closeSearch" class="modal-close" type="button" aria-label="Suche schließen">×</button></div><div class="search-wrap"><span class="search-icon">⌕</span><input id="settingsSearch" type="search" placeholder="Bezeichnung, Hilfe, Synonym oder Config-Key" autocomplete="off"><button id="searchClear" class="search-clear" type="button" aria-label="Suche leeren">×</button></div><div id="searchResults" class="search-results"><div class="empty-state">Suchbegriff eingeben.</div></div></aside>
<div id="drawerBackdrop" class="drawer-backdrop"></div>
<div id="previewModal" class="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="previewTitle"><div class="modal"><div class="modal-head"><h2 id="previewTitle">Änderungen prüfen</h2><button id="previewClose" class="modal-close" type="button">×</button></div><div id="previewBody" class="modal-body"></div><div class="modal-actions"><button id="previewBack" class="back-btn" type="button">Zurück</button><button id="commitChanges" class="commit-btn" type="button">Speichern</button></div></div></div>
<div id="helpModal" class="modal-backdrop help-backdrop" role="dialog" aria-modal="true" aria-labelledby="helpTitle"><div class="modal help-modal"><div class="modal-head"><h2 id="helpTitle">Einstellungshilfe</h2><button id="helpClose" class="modal-close" type="button" aria-label="Hilfe schließen">×</button></div><div id="helpBody" class="modal-body help-body"></div><div class="modal-actions help-actions"><button id="helpDone" class="back-btn" type="button">Schließen</button></div></div></div>
<div id="configStatesModal" class="modal-backdrop config-states-backdrop" role="dialog" aria-modal="true" aria-labelledby="configStatesTitle"><div class="modal config-states-modal"><div class="modal-head"><h2 id="configStatesTitle">Konfigurationsstände · Import · Export</h2><button id="configStatesClose" class="modal-close" type="button" aria-label="Konfigurationsstände schließen">×</button></div><div id="configStatesBody" class="modal-body config-states-body"></div><div class="modal-actions"><button id="configStatesDone" class="back-btn" type="button">Schließen</button></div></div></div>
<div id="settingsToast" class="toast" role="status"></div>
<script>window.ZEC_SETTINGS_BOOTSTRAP={{system:{json.dumps(system_payload or {}, ensure_ascii=False)},server_time:{json.dumps(server_time, ensure_ascii=False)}}};</script>
<script src="/static/settings_v2.js?v={html.escape(APP_VERSION_LABEL)}" defer></script>
</body></html>"""


def build_night_time_card(name: str, label: str, hour: Any, minute: Any, description: str, has_error: bool = False, has_warning: bool = False) -> str:
    state_class = " error-card" if has_error else (" warning-card" if has_warning else "")
    safe_name = html.escape(name, quote=True)
    safe_value = html.escape(format_hhmm(hour, minute), quote=True)
    return f"""
    <div class="card{state_class}">
        <div class="label">{html.escape(label)}</div>
        <input type="text" name="{safe_name}" value="{safe_value}" pattern="^\\d{{1,2}}:\\d{{1,2}}$" inputmode="numeric" data-night-time="1" placeholder="hh:mm">
        <details class="help"><summary>Parameterinfo</summary><div class="small">{html.escape(description)}</div></details>
    </div>
    """


def build_setting_card(key: str, meta: Dict[str, Any], value: Any, has_error: bool = False, has_warning: bool = False) -> str:
    label = html.escape(str(meta.get("label", key)))
    description = html.escape(str(meta.get("description", "")))
    unit = str(meta.get("unit", ""))
    unit_label = unit_to_label(unit)
    if unit_label:
        label = f"{label} {html.escape(unit_label)}"
    input_html = build_input(key, meta, value)
    attrs = manual_card_attr(key) + cross_profile_card_attr(meta)
    state_class = " error-card" if has_error else (" warning-card" if has_warning else "")
    return f"""
    <div class="card{state_class}"{attrs}>
        <div class="label">{label}</div>
        {input_html}
        <details class="help"><summary>Parameterinfo</summary><div class="small">{description}</div></details>
    </div>
    """


def build_input(key: str, meta: Dict[str, Any], value: Any) -> str:
    input_type = meta.get("type")
    safe_key = html.escape(key)
    safe_value = html.escape("" if value is None else str(value), quote=True)

    if input_type == "bool":
        checked = "checked" if bool(value) else ""
        return f'<input type="checkbox" name="{safe_key}" {checked}>'

    if input_type == "select":
        options = meta.get("options", {})
        option_html = ""
        for option_value, option_label in options.items():
            selected = "selected" if str(value) == str(option_value) else ""
            option_html += (
                f'<option value="{html.escape(str(option_value), quote=True)}" {selected}>'
                f'{html.escape(str(option_label))}</option>'
            )
        return f'<select name="{safe_key}">{option_html}</select>'

    if input_type == "int":
        min_attr = f' min="{meta["min"]}"' if "min" in meta else ""
        max_attr = f' max="{meta["max"]}"' if "max" in meta else ""
        return f'<input type="number" step="1" name="{safe_key}" value="{safe_value}"{min_attr}{max_attr}>'

    if input_type == "optional_int":
        min_attr = f' min="{meta["min"]}"' if "min" in meta else ""
        max_attr = f' max="{meta["max"]}"' if "max" in meta else ""
        return f'<input type="number" step="1" name="{safe_key}" value="{safe_value}"{min_attr}{max_attr} placeholder="leer = deaktiviert">'

    if input_type == "float":
        step = meta.get("step", 0.01)
        min_attr = f' min="{meta["min"]}"' if "min" in meta else ""
        max_attr = f' max="{meta["max"]}"' if "max" in meta else ""
        return f'<input type="number" step="{step}" name="{safe_key}" value="{safe_value}"{min_attr}{max_attr}>'

    if input_type == "password":
        return f'<input type="password" name="{safe_key}" value="{safe_value}">'

    return f'<input type="text" name="{safe_key}" value="{safe_value}">'


def build_mqtt_diagnostics_page(cfg: Dict[str, Any], rows: List[Dict[str, Any]], cleared: bool = False) -> str:
    page = build_base_header("MQTT Diagnose", cfg=cfg)
    enabled = bool(cfg.get("MQTT_TOPIC_DIAGNOSTIC_ENABLED", False))
    cleared_html = "<div class='info-box'>Die MQTT-Diagnosetabelle wurde geleert. Neue empfangene Diagnosewerte erscheinen automatisch wieder in der Tabelle.</div>" if cleared else ""
    filter_text = html.escape(str(cfg.get('MQTT_TOPIC_DIAGNOSTIC_FILTER', 'Zendure/#')))
    view_mode = str(cfg.get('MQTT_TOPIC_DIAGNOSTIC_VIEW_MODE', 'filtered')).lower()
    view_text = 'alle empfangenen Controller-Topics' if view_mode == 'all' else 'nur passende Diagnosefilter-Topics'
    page += f"""
    <div class="section">
        {section_title('MQTT Topic-Diagnose', 1, True)}
        {cleared_html}
        <div class="small">
            Status: <b>{'aktiv' if enabled else 'deaktiviert'}</b><br>
            Filter: <code>{filter_text}</code><br>
            Anzeige: <b>{html.escape(view_text)}</b><br>
            Hinweis: MQTT-Topic-Matching ist groß-/kleinschreibungssensitiv. <code>EVCC/#</code> passt nicht auf <code>evcc/site/...</code>.<br>
            Diese Seite zeigt die zuletzt mitgeschnittenen MQTT-Nachrichten. Für längere Mitschnitte bitte nur zeitweise aktivieren.<br>
            Die Tabelle wird automatisch aktualisiert; alternativ kann sie manuell über <b>Aktualisieren</b> neu geladen werden.
            <br><a href="/mqtt-diagnostics.csv">MQTT-Diagnose als CSV herunterladen</a>
        </div>
        <form method="post" action="/mqtt-diagnostics/clear" onsubmit="return confirm('MQTT-Diagnosetabelle wirklich leeren? Die Live-Diagnose läuft danach weiter und neue Werte erscheinen automatisch wieder.');">
            <button class="save save-small" type="submit">Diagnosetabelle leeren</button>
            <button class="save save-small" type="button" onclick="refreshMqttDiagnostics();">Aktualisieren</button>
        </form>
        <div class="small" id="mqtt-diagnostics-live-status">Live-Aktualisierung: aktiv, Intervall 3 Sekunden. Zeilen im Puffer: <span id="mqtt-diagnostics-count">{len(rows)}</span></div>
    </div>
    <div class="section"><table id="mqtt-diagnostics-table">
        <thead><tr><th>Datum</th><th>Zeit</th><th>Topic</th><th>Filter</th><th>Payload</th></tr></thead>
        <tbody id="mqtt-diagnostics-body">
    """
    page += render_mqtt_diagnostics_rows(rows)
    page += """</tbody></table></div>
    <script>
    function mqttDiagEscape(value) {
        return String(value === null || value === undefined ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }
    function mqttDiagRow(row) {
        const filterCell = row.diagnostic_filter_matched ? 'passt' : mqttDiagEscape(row.diagnostic_view_mode || 'filtered');
        return '<tr>'
            + '<td>' + mqttDiagEscape(row.date || '') + '</td>'
            + '<td>' + mqttDiagEscape(row.timestamp || '') + '</td>'
            + '<td style="text-align:left">' + mqttDiagEscape(row.topic || '') + '</td>'
            + '<td>' + filterCell + '</td>'
            + '<td style="text-align:left"><code>' + mqttDiagEscape(row.payload || '') + '</code></td>'
            + '</tr>';
    }
    async function refreshMqttDiagnostics() {
        const status = document.getElementById('mqtt-diagnostics-live-status');
        try {
            const response = await fetch('/mqtt-diagnostics/data', {cache: 'no-store'});
            if (!response.ok) {
                throw new Error('HTTP ' + response.status);
            }
            const data = await response.json();
            const rows = Array.isArray(data.rows) ? data.rows : [];
            const visible = rows.slice(-200).reverse();
            const body = document.getElementById('mqtt-diagnostics-body');
            if (body) {
                body.innerHTML = visible.length
                    ? visible.map(mqttDiagRow).join('')
                    : '<tr><td colspan="5">Noch keine MQTT-Diagnosedaten vorhanden.</td></tr>';
            }
            const count = document.getElementById('mqtt-diagnostics-count');
            if (count) {
                count.textContent = String(data.count || rows.length || 0);
            }
            if (status) {
                const now = new Date().toLocaleTimeString();
                status.innerHTML = 'Live-Aktualisierung: aktiv, letzte Aktualisierung ' + mqttDiagEscape(now)
                    + '. Zeilen im Puffer: <span id="mqtt-diagnostics-count">' + mqttDiagEscape(data.count || rows.length || 0) + '</span>';
            }
        } catch (err) {
            if (status) {
                status.textContent = 'Live-Aktualisierung fehlgeschlagen: ' + err;
            }
        }
    }
    window.addEventListener('load', function() {
        refreshMqttDiagnostics();
        window.setInterval(refreshMqttDiagnostics, 3000);
    });
    </script>
    """
    page += build_footer()
    return page


def render_mqtt_diagnostics_rows(rows: List[Dict[str, Any]]) -> str:
    html_rows = ""
    for row in reversed(rows[-200:]):
        html_rows += (
            "<tr>"
            f"<td>{html.escape(str(row.get('date', '')))}</td>"
            f"<td>{html.escape(str(row.get('timestamp', '')))}</td>"
            f"<td style='text-align:left'>{html.escape(str(row.get('topic', '')))}</td>"
            f"<td>{'passt' if row.get('diagnostic_filter_matched') else html.escape(str(row.get('diagnostic_view_mode', 'filtered')))}</td>"
            f"<td style='text-align:left'><code>{html.escape(str(row.get('payload', '')))}</code></td>"
            "</tr>"
        )
    if not rows:
        html_rows += "<tr><td colspan='5'>Noch keine MQTT-Diagnosedaten vorhanden.</td></tr>"
    return html_rows

def diagnostics_to_csv(rows: Iterable[Dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["date", "timestamp", "topic", "diagnostic_filter", "diagnostic_view_mode", "diagnostic_filter_matched", "payload"])
    writer.writerow({"date": "Datum [lokal]", "timestamp": "Uhrzeit [lokal]", "topic": "MQTT Topic", "diagnostic_filter": "Diagnosefilter", "diagnostic_view_mode": "Anzeigemodus", "diagnostic_filter_matched": "Filter passt", "payload": "Payload"})
    for row in rows:
        writer.writerow({
            "date": row.get("date", ""),
            "timestamp": row.get("timestamp", ""),
            "topic": row.get("topic", ""),
            "diagnostic_filter": row.get("diagnostic_filter", ""),
            "diagnostic_view_mode": row.get("diagnostic_view_mode", ""),
            "diagnostic_filter_matched": row.get("diagnostic_filter_matched", ""),
            "payload": row.get("payload", ""),
        })
    return buffer.getvalue()
