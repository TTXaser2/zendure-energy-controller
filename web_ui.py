# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

import csv
import html
import io
import json
import os
import shlex
import subprocess
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

import requests
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse, JSONResponse

from config_manager import CONFIG_SCHEMA, ConfigManager, validate_config
from config_validator import ValidationIssue, restart_relevant_changes, split_issues, validate_config_semantics
from cross_charge import cross_charge_enabled
from csv_logger import rows_to_csv, estimate_retention_hours, measurement_log_mode, detected_log_mounts, resolve_log_path
from measurement_db import query_graph_points, resolve_measurement_db_path, db_status_for_config
from version import APP_VERSION, APP_VERSION_LABEL, CSV_SCHEMA
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


def service_restart_enabled(cfg: Dict[str, Any]) -> bool:
    return bool(cfg.get("WEB_SERVICE_RESTART_ENABLED", False)) and bool(str(cfg.get("SERVICE_RESTART_COMMAND", "")).strip())


def trigger_service_restart(cfg: Dict[str, Any]) -> None:
    command = str(cfg.get("SERVICE_RESTART_COMMAND", "")).strip()
    if not command:
        raise RuntimeError("SERVICE_RESTART_COMMAND ist leer.")
    args = shlex.split(command)
    if not args:
        raise RuntimeError("SERVICE_RESTART_COMMAND ist ungültig.")
    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def delayed_service_restart(cfg: Dict[str, Any], delay_seconds: float = 1.0) -> None:
    # Copy the relevant command now; after the service restarts, the original
    # config object may no longer exist in this process.
    local_cfg = dict(cfg)
    timer = threading.Timer(delay_seconds, trigger_service_restart, args=[local_cfg])
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
    """Return a detailed machine-readable readiness status for monitoring."""
    now_status = "ok"
    checks: Dict[str, Any] = {}

    mqtt_ok = bool(snap.get("mqtt_connected"))
    checks["mqtt"] = {"ok": mqtt_ok, "connected": mqtt_ok}

    shelly_age = snap.get("last_shelly_update_age_seconds")
    shelly_timeout = int(cfg.get("SHELLY_STALE_TIMEOUT_SECONDS", 15))
    shelly_ok = shelly_age is not None and int(shelly_age) <= shelly_timeout
    checks["shelly"] = {"ok": shelly_ok, "age_seconds": shelly_age, "timeout_seconds": shelly_timeout}

    soc_age = snap.get("last_soc_update_age_seconds")
    soc_timeout = int(cfg.get("SOC_STALE_TIMEOUT_SECONDS", 90))
    soc_ok = snap.get("battery_soc") is not None and soc_age is not None and int(soc_age) <= soc_timeout
    checks["zendure_soc"] = {
        "ok": soc_ok,
        "soc_percent": snap.get("battery_soc"),
        "source": snap.get("zendure_telemetry_source"),
        "fallback_active": snap.get("zendure_local_api_fallback_active"),
        "age_seconds": soc_age,
        "timeout_seconds": soc_timeout,
    }

    if cross_charge_enabled(cfg):
        evcc_age = snap.get("last_sma_battery_update_age_seconds")
        evcc_timeout = int(cfg.get("SECOND_BATTERY_STALE_TIMEOUT_SECONDS", cfg.get("EVCC_STALE_TIMEOUT_SECONDS", 30)))
        evcc_ok = evcc_age is not None and int(evcc_age) <= evcc_timeout
        checks["cross_charge_second_battery"] = {"ok": evcc_ok, "age_seconds": evcc_age, "timeout_seconds": evcc_timeout}

    safe_state = snap.get("current_mode") == "SAFE_STATE"
    checks["controller"] = {
        "ok": not safe_state and int(snap.get("consecutive_errors") or 0) == 0,
        "mode": snap.get("current_mode"),
        "consecutive_errors": snap.get("consecutive_errors"),
        "last_error": snap.get("last_error"),
        "last_error_time": snap.get("last_error_time"),
    }

    failed = [name for name, item in checks.items() if isinstance(item, dict) and not item.get("ok", False)]
    if failed:
        now_status = "degraded"
    if safe_state:
        now_status = "safe_state"

    return {
        "status": now_status,
        "ready": not failed and not safe_state,
        "version": APP_VERSION,
        "uptime_seconds": snap.get("uptime_seconds"),
        "checks": checks,
        "failed_checks": failed,
    }


def build_health_payload(snap: Dict[str, Any]) -> Dict[str, Any]:
    """Return a minimal liveness status. This endpoint answers: is the process alive?"""
    return {
        "status": "ok",
        "alive": True,
        "version": APP_VERSION,
        "uptime_seconds": snap.get("uptime_seconds"),
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


def measurement_availability(cfg: Dict[str, Any], max_rows_per_file: int = 250000) -> Dict[str, Any]:
    files = _measurement_csv_files(cfg)
    first_dt: Optional[datetime] = None
    last_dt: Optional[datetime] = None
    row_count = 0
    readable_files = 0
    for path in files:
        seen = 0
        file_has_rows = False
        for row in _read_csv_rows(path):
            seen += 1
            if seen > max_rows_per_file:
                break
            dt = _parse_measurement_dt(row)
            if dt is None:
                continue
            file_has_rows = True
            row_count += 1
            if first_dt is None or dt < first_dt:
                first_dt = dt
            if last_dt is None or dt > last_dt:
                last_dt = dt
        if file_has_rows:
            readable_files += 1
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
        "files": [os.path.basename(p) for p in files[-10:]],
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
    port = int(cfg.get("REPLAY_WEB_PORT", 8090) or 8090)
    now = time.time()
    if _replay_health_cache.get("port") == port and now - float(_replay_health_cache.get("checked_epoch") or 0) < 30:
        return bool(_replay_health_cache.get("available"))
    available = False
    try:
        r = requests.get(f"http://127.0.0.1:{port}/", timeout=0.75)
        available = r.status_code < 500
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
    app = FastAPI(title="Zendure Energy Controller", version=APP_VERSION)

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
        snap.pop("graph_history", None)
        snap.pop("event_history", None)
        snap.pop("mqtt_topic_diagnostics", None)
        return snap

    @app.get("/graph-data")
    def graph_data():
        return state.snapshot()["graph_history"]

    @app.get("/graph-data.csv")
    def graph_data_csv():
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
    def soc_day_data():
        return build_soc_day_payload(config_manager.get(), state.snapshot())

    @app.get("/grid-mini-sparkline", response_class=HTMLResponse)
    def grid_mini_sparkline():
        snap = state.snapshot()
        svg = _mini_svg_sparkline(_grid_mini_values_from_snapshot(snap), stroke="#2ca24d")
        return HTMLResponse(svg)

    @app.get("/measurements", response_class=HTMLResponse)
    def measurements_page():
        return html_or_headless(build_measurements_page, config_manager.get())

    @app.get("/measurements/availability")
    def measurements_availability():
        data = measurement_availability(config_manager.get())
        try:
            data["measurement_db"] = db_status_for_config(config_manager.get())
        except Exception as exc:
            data["measurement_db"] = {"measurement_db_status": "error", "measurement_db_error": str(exc)}
        return data

    @app.get("/measurement-db-status")
    def measurement_db_status():
        return db_status_for_config(config_manager.get())

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
            availability = measurement_availability(cfg)
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
        return config_manager.get()

    @app.get("/health")
    def health():
        cfg = config_manager.get()
        return build_health_payload(state.snapshot())

    @app.get("/ready")
    def ready():
        cfg = config_manager.get()
        payload = build_ready_payload(cfg, state.snapshot())
        return payload

    @app.get("/settings", response_class=HTMLResponse)
    def settings_page(request: Request):
        cfg = config_manager.get()
        saved = request.query_params.get("saved") == "1"
        restart_required = request.query_params.get("restart_required") == "1"
        restart_keys = request.query_params.get("restart_keys", "")
        issues = validate_config_semantics(cfg, current=cfg, perform_live_checks=False, base_dir=os.getcwd())
        return html_or_headless(build_settings_page, cfg, validation_issues=issues, saved=saved, restart_required=restart_required, restart_keys=restart_keys)

    @app.post("/settings/validate")
    async def validate_settings_preview(request: Request):
        if config_manager.get().get("HEADLESS_MODE", False):
            return JSONResponse({"status": "disabled", "issues": []}, status_code=403)
        form = await request.form()
        current_cfg = config_manager.get()
        raw_cfg = dict(current_cfg)
        for key, meta in CONFIG_SCHEMA.items():
            if meta.get("type") == "bool":
                raw_cfg[key] = key in form
            elif key in form:
                raw_cfg[key] = form.get(key)
        issues = apply_night_time_form_fields(raw_cfg, form)
        issues += validate_config_semantics(raw_cfg, current=current_cfg, perform_live_checks=False, base_dir=os.getcwd())
        buckets = split_issues(issues)
        return JSONResponse({
            "errors": len(buckets.get("ERROR", [])),
            "warnings": len(buckets.get("WARNING", [])),
            "infos": len(buckets.get("INFO", [])),
            "issues": [issue.as_dict() for issue in issues],
        })

    @app.post("/save-config")
    async def save_config_web(request: Request):
        if config_manager.get().get("HEADLESS_MODE", False):
            return HTMLResponse(build_headless_page(config_manager.get()), status_code=403)
        form = await request.form()
        current_cfg = config_manager.get()
        raw_cfg = dict(current_cfg)
        for key, meta in CONFIG_SCHEMA.items():
            if meta.get("type") == "bool":
                raw_cfg[key] = key in form
            elif key in form:
                raw_cfg[key] = form.get(key)
        validation_issues = apply_night_time_form_fields(raw_cfg, form)

        validation_issues += validate_settings_before_save(raw_cfg, current_cfg)
        issue_buckets = split_issues(validation_issues)
        confirmed_warnings = form.get("_confirm_warnings") == "1"
        cfg, _ = validate_config(raw_cfg)

        if issue_buckets.get("ERROR"):
            return HTMLResponse(build_settings_page(cfg, validation_issues, validation_state="error"), status_code=400)

        if issue_buckets.get("WARNING") and not confirmed_warnings:
            return HTMLResponse(build_settings_page(cfg, validation_issues, validation_state="warning"), status_code=409)

        changed_restart_keys = restart_relevant_changes(cfg, current_cfg)
        config_manager.save(cfg)
        if on_config_saved:
            on_config_saved()
        if changed_restart_keys:
            return RedirectResponse(
                url="/settings?saved=1&restart_required=1&restart_keys=" + html.escape(",".join(changed_restart_keys), quote=True),
                status_code=303,
            )
        return RedirectResponse(url="/settings?saved=1", status_code=303)

    @app.get("/graph", response_class=HTMLResponse)
    def graph_page():
        return html_or_headless(build_graph_page, config_manager.get())

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

    @app.post("/restart-service", response_class=HTMLResponse)
    async def restart_service(request: Request):
        cfg = config_manager.get()
        if cfg.get("HEADLESS_MODE", False):
            return HTMLResponse(build_headless_page(cfg), status_code=403)
        if not service_restart_enabled(cfg):
            return HTMLResponse(build_restart_service_page(cfg, enabled=False, redirect_url=status_url_after_restart(request, cfg)), status_code=403)
        try:
            delayed_service_restart(cfg, delay_seconds=1.2)
            return HTMLResponse(build_restart_service_page(cfg, enabled=True, redirect_url=status_url_after_restart(request, cfg)))
        except Exception as exc:
            return HTMLResponse(build_restart_service_page(cfg, enabled=True, error=str(exc), redirect_url=status_url_after_restart(request, cfg)), status_code=500)

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
            input[type="number"], input[type="text"], input[type="password"], select { background:#0b1220; color:#e5e7eb; border:1px solid #64748b; }
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
            .modern-section {{ background:#0b1220; border:1px solid rgba(148,163,184,.14); border-radius:24px; padding:22px; margin-bottom:22px; box-shadow:0 12px 36px rgba(0,0,0,.32); }}
            .modern-section-header {{ display:flex; align-items:flex-start; justify-content:space-between; gap:16px; margin-bottom:16px; flex-wrap:wrap; }}
            .modern-section h2 {{ margin:0; font-size:22px; letter-spacing:-.02em; }}
            .modern-flow {{ display:grid; grid-template-columns:1fr auto 1fr; gap:18px; align-items:center; }}
            .flow-list {{ display:flex; flex-direction:column; gap:12px; }}
            .flow-row {{ display:flex; align-items:center; justify-content:space-between; gap:12px; border:1px solid rgba(148,163,184,.12); background:rgba(2,6,23,.34); border-radius:14px; padding:11px 12px; }}
            .flow-label {{ color:#cbd5e1; font-size:13px; }} .flow-value {{ font-weight:900; }}
            .flow-center {{ width:112px; height:112px; border-radius:999px; display:flex; flex-direction:column; align-items:center; justify-content:center; background:radial-gradient(circle at 50% 50%, rgba(45,212,191,.22), rgba(15,23,42,.96) 62%); border:1px solid rgba(45,212,191,.35); text-align:center; }}
            .flow-center b {{ font-size:24px; }}
            .soc-ring {{ width:150px; height:150px; border-radius:999px; display:flex; align-items:center; justify-content:center; margin:2px auto 14px; background:conic-gradient(#22c55e var(--soc,0%), rgba(148,163,184,.16) 0); position:relative; }}
            .soc-ring:after {{ content:""; position:absolute; inset:13px; border-radius:999px; background:#0b1220; border:1px solid rgba(148,163,184,.12); }}
            .soc-ring span {{ position:relative; z-index:1; font-size:34px; font-weight:900; }}
            .modern-table {{ width:100%; border-collapse:collapse; font-size:13px; }} .modern-table th,.modern-table td {{ border:0; border-bottom:1px solid rgba(148,163,184,.14); text-align:left; padding:9px 6px; }} .modern-table th {{ background:transparent; color:#94a3b8; font-weight:700; }}
            .modern-warning {{ border:1px solid rgba(245,158,11,.42); background:rgba(245,158,11,.09); color:#fde68a; border-radius:16px; padding:13px 14px; margin-top:14px; }}
            .legacy-note {{ margin-top:14px; color:#94a3b8; font-size:13px; }} .legacy-note a {{ color:#7dd3fc; }}
            .expert-menu {{ position:relative; display:inline-flex; }} .expert-menu-button {{ border:0; border-radius:10px; padding:8px 10px; background:rgba(21,101,192,.08); color:#7dd3fc; cursor:pointer; font:inherit; }} .expert-menu-panel {{ display:none; position:absolute; right:0; top:calc(100% + 8px); min-width:180px; background:#0b1220; border:1px solid #334155; border-radius:14px; padding:8px; z-index:50; box-shadow:0 12px 30px rgba(0,0,0,.4); }} .expert-menu.open .expert-menu-panel {{ display:block; }} .expert-menu-panel a {{ display:block; background:transparent; padding:9px 10px; }}
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
            .zec-control select option {{ background:#0b1220; color:#f8fafc; }}
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
        "zendure_local_api_ms": "Zendure API",
        "cycle_display_metrics_ms": "Statuswerte",
        "grid_display_read_ms": "Grid-Anzeige",
        "grid_control_read_ms": "Grid-Regelwert",
        "cross_charge_metrics_ms": "Zusatzbatterie",
        "charge_acceptance_diag_ms": "Ladeannahme-Diagnose",
        "graph_snapshot_ms": "Status-Snapshot",
        "measurement_logging_ms": "Messdaten-Logging",
        "run_once_ms": "Regelentscheidung",
        "finish_cycle_ms": "Zyklusabschluss",
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
    local_api_ms = timing_obj.get("zendure_local_api_ms")
    local_api_details = (
        f"Modus: {html.escape(local_api_mode)}<br>"
        f"Letzter Zyklus: {html.escape(str(local_api_ms if local_api_ms is not None else '-'))} ms<br>"
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
    {build_soc_day_section(cfg)}
    <div class="section">{heading_link('Diagnose', 'Sicherheit / Fallback', 2)}<div class="section-tools"><a href="#" onclick="expandSectionInfo('status-diagnostics'); return false;">Alle Infos auf- und zuklappen</a></div><div class="grid" id="status-diagnostics">
        {status_card('Aktive Betriebslogik', html.escape(path_human), html.escape(str(s['last_control_action'])), 'gray', 'Die aktive Betriebslogik beschreibt den aktuell verwendeten Entscheidungsweg des Controllers in verständlicher Form. Der technische Code bleibt darunter sichtbar, damit man Events, Graphdaten und Logausgaben eindeutig zuordnen kann.', path_code)}
        {status_card('Aktive Zykluszeit', f'{active_cycle_ms} ms', timing_details, 'gray', 'Die aktive Zykluszeit ist die Zeit, in der der Controller für einen Regelzyklus tatsächlich arbeitet: Datenquellen prüfen, Regelentscheidung berechnen, MQTT-Kommandopfad ausführen, Status aktualisieren und Messdaten schreiben. Nicht enthalten ist die geplante Wartezeit bis zum nächsten Regelintervall. Der langsamste Teil zeigt, welcher echte Abschnitt innerhalb des letzten Zyklus am meisten Zeit benötigt hat.')}
        {status_card('Zendure Local API Timing', html.escape(local_api_mode), local_api_details, 'gray', 'Zeigt, ob die lokale Zendure-API deaktiviert, nur als Diagnose, als Fallback oder als aktive Telemetriequelle genutzt wird. Lange lokale API-Antworten können einzelne Regelzyklen verlängern; dies ist Diagnose, keine Regelstrategieänderung.', settings_group='Netzwerk')}
        {status_card('Fehler', str(s['consecutive_errors']), f'Letzter Fehler: {html.escape(str(s["last_error"]))}<br>Zeitpunkt: {html.escape(str(s.get("last_error_time", "-")))}<br>Safe-State: {s["safe_state_counter"]}x', 'red', 'Der Fehlerzähler zählt direkt aufeinanderfolgende Fehler. Safe-State bedeutet: Lade- und Entladeleistung werden auf 0 W gesetzt, um bei unsicheren Daten oder Kommunikationsproblemen keine unkontrollierte Energieverschiebung auszulösen.')}
        {status_card('Messdaten-Logging', measurement_mode, measurement_log_details, 'gray', 'Messdaten-Logging ist optional und nachgelagert. Standard speichert vollständige Reglerdiagnose inklusive MQTT-Stale-Aggregat und Szenario ohne Zendure. Erweitert ergänzt große Detaildaten für Simulation, What-if und tiefe MQTT-/Freshness-Analyse. USB-/SD-Fallback-Details sind Betriebsdiagnose und werden im Runtime-Log dokumentiert; die Regelung läuft weiter, auch wenn Logging pausiert oder fehlschlägt.', settings_group='Messdaten / Historie')}
        {status_card('Analyse-Weboberfläche', f'Port {replay_port}', analysis_link_html, 'gray', 'Die Analyse läuft bewusst getrennt vom Live-Regler. Der Dienst wird mitgeliefert, aber nicht automatisch aktiviert.')}
        {status_card('High-SOC-Ladeannahme', html.escape(str(s.get('charge_acceptance_state', 'ok'))), html.escape(str(s.get('charge_acceptance_reason', '-'))), 'gray', 'Leichtgewichtige Diagnose: Zeigt, ob Zendure eine angeforderte Ladeleistung bei hohem SOC plausibel annimmt. Diese Diagnose greift nicht aktiv in die Regelung ein.')}
    </div></div>
    {build_event_section(s['event_history'])}
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


def _modern_body_start(cfg: Dict[str, Any], active: str, force_dark: bool = False) -> str:
    cfg2 = dict(cfg or {})
    cfg2["__hide_nav"] = True
    dark = bool(force_dark or cfg2.get("UI_DARK_MODE", False))
    # Modern pages use explicit theme classes. This decouples the new dashboard
    # from the legacy page theme and allows a true mock-up-fidelity light shell.
    theme_class = "modern-dark" if dark else "modern-light"
    return (
        build_base_header("Zendure Energy Controller", cfg=cfg2)
        + f'<script>document.body.classList.add("zec-modern-body","{theme_class}");</script>'
        + _modern_topbar(active, cfg or {})
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
      <div class="zec-top-actions"><span class="zec-system-pill">System aktiv</span><span class="modern-pill">V{APP_VERSION}</span><span class="zec-clock" id="zecClock">--:--:--</span></div>
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
    return (
        f'<svg class="sparkline" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Mini-Verlauf: Minimum {html.escape(fmt(lo))}, Maximum {html.escape(fmt(hi))}, aktuell {html.escape(fmt(nums[-1]))}">'
        f'<line class="mini-grid" x1="{left}" y1="{top}" x2="{width-right}" y2="{top}"/>'
        f'<line class="mini-grid" x1="{left}" y1="{top + plot_h/2:.1f}" x2="{width-right}" y2="{top + plot_h/2:.1f}"/>'
        f'<line class="mini-axis" x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}"/>'
        f'<line class="mini-axis" x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}"/>'
        f'{zero_line}'
        f'<polyline class="mini-line" points="{points_attr}" stroke="{html.escape(stroke)}"/>'
        f'<circle class="mini-dot" cx="{last_x}" cy="{last_y}" r="3" stroke="{html.escape(stroke)}"/>'
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


def build_status_page(cfg: Dict[str, Any], s: Dict[str, Any]) -> str:
    """Modern status page.

    RC12 intentionally treats the mock-up as the visual contract. The legacy
    detail matrix stays available via /status_old, but the default page is a
    curated dashboard instead of a transformed legacy card wall.
    """
    m = _modern_status_summary(cfg, s)
    current_mode = str(m["mode"])
    grid = float(m["grid"] or 0.0)
    actual = float(m["actual"] or 0.0)
    target = float(m["target"] or 0.0)
    sma_power = float(s.get('sma_battery_display_power', s.get('sma_battery_power', 0.0)) or 0.0)
    soc_num = m["soc"] if m["soc"] is not None else None
    soc_val = f"{soc_num} %" if soc_num is not None else "- %"
    soc_ring = max(0, min(100, int(float(soc_num or 0))))
    grid_kw = grid / 1000.0
    actual_kw = actual / 1000.0
    target_kw = target / 1000.0
    sma_kw = sma_power / 1000.0
    grid_cls = "zec-accent-blue" if abs(grid) < 0.1 else ("zec-accent-red" if grid > 0 else "zec-accent-green")
    actual_cls = "zec-accent-blue" if abs(actual) < 0.1 else ("zec-accent-green" if actual > 0 else "zec-accent-blue")
    graph_hist = list(s.get("graph_history", []) or [])
    grid_sparkline = _mini_svg_sparkline([r.get("grid_power") if isinstance(r, dict) else None for r in graph_hist], stroke="#2ca24d")
    mode_kind = "bad" if current_mode == "SAFE_STATE" else ("warn" if current_mode in {"HOLD", "STOP_HOLD", "BLOCKED_BY_SMA"} else "ok")
    log_kind = "ok" if m["logging_status"] == "active" else "warn"
    mqtt_kind = "ok" if m["mqtt_ok"] else "warn"
    source_title = "Netzleistungsquelle"
    source_device = "SMA Home Manager 2.0" if str(cfg.get("GRID_METER_SOURCE", "")) == "sma_energy_meter_udp" else "Shelly-kompatibel"
    source_detail = _short_source_name(s.get("raw_grid_source") or s.get("grid_power_source") or source_device)
    source_age = age_text(s.get("grid_power_age_seconds"))
    packet_rate = s.get("sma_energy_meter_packet_rate_per_min") or s.get("sma_packet_rate_per_min")
    packet_rate_line = f"{float(packet_rate)/60.0:.1f} Hz" if packet_rate is not None else "-"
    socket_mode = str(s.get("sma_energy_meter_socket_mode") or s.get("sma_socket_mode") or cfg.get("SMA_ENERGY_METER_SOCKET_MODE", "-"))
    measurement_target = str(s.get("measurement_log_active_target_type") or cfg.get("MEASUREMENT_LOG_STORAGE_TARGET", "-"))
    measurement_log_details = f"Status: {m['logging_status']} · Ziel: {measurement_target}"
    active_cycle_ms = int(s.get("last_cycle_total_ms") or s.get("last_loop_duration_ms") or 0)
    slowest_key = str(s.get("last_cycle_slowest_step") or "")
    slowest_ms = int(s.get("last_cycle_slowest_step_ms") or 0)
    timing_step_labels = {"measurement_logging_ms": "Messdaten-Logging", "finish_cycle_ms": "Zyklusabschluss", "run_once_ms": "Regelentscheidung"}
    slowest_label = timing_step_labels.get(slowest_key, slowest_key or "-")
    grid_measurement_line = f"aktueller Messwert: {grid:.1f} W" if m["grid_valid"] else "aktueller Messwert: nicht gültig"
    grid_relevance_line = "für AUTO-Regelung genutzt" if m["grid_used"] else "nicht regelrelevant"
    auto_rule_line = f"Geglätteter AUTO-Regelwert: {float(s.get('grid_power', 0.0) or 0.0):.1f} W" if m["grid_used"] else "Geglätteter AUTO-Regelwert: n.a."
    mqtt_recovery_hint = "" if m["mqtt_ok"] else "Zendure Live-Status prüfen. Falls nach Raspberry-/Mosquitto-Neustart keine Live-Werte kommen, MQTT in der Zendure-App erneut speichern/aktivieren."
    compatibility_status_text = (
        f"Aktive Zykluszeit {active_cycle_ms} ms · {slowest_label} {slowest_ms} ms · "
        f"{grid_measurement_line} · {grid_relevance_line} · {auto_rule_line} · {measurement_log_details} · {mqtt_recovery_hint}"
    )
    measurement_interval = int(cfg.get("MEASUREMENT_LOG_INTERVAL_SECONDS", cfg.get("INTERVAL_SECONDS", 3)) or 0)
    measurement_file = str(s.get("measurement_current_file_name") or s.get("measurement_current_file") or "-")
    measurement_path = str(s.get("measurement_log_active_directory") or s.get("measurement_primary_path") or cfg.get("MEASUREMENT_LOG_DIR", "-"))
    measurement_db_path = str(s.get("measurement_db_path") or resolve_measurement_db_path(cfg))
    measurement_db_file = os.path.basename(measurement_db_path) if measurement_db_path else "-"
    db_active = m.get("db_status") in {"active", "queued", "available", "hit"}
    rows_today = s.get("measurement_rows_today") or s.get("measurement_current_file_rows") or "-"
    rows_total = s.get("measurement_total_rows") or "-"
    night_projection = night_mode_projection_text(cfg, s, current_mode)
    night_enabled = bool(cfg.get("NIGHT_DISCHARGE_ENABLED")) or current_mode == "NIGHT_DISCHARGE"
    night_line = ""
    if night_enabled:
        night_state = "aktiv" if current_mode == "NIGHT_DISCHARGE" else "aktuell nicht aktiv"
        night_extra = f" · {html.escape(night_projection)}" if current_mode == "NIGHT_DISCHARGE" and night_projection else ""
        night_line = (
            f"<div class='zec-mode-context'><b>Nachtmodus:</b> {night_state} · "
            f"Fenster {int(cfg.get('NIGHT_START_HOUR',0)):02d}:{int(cfg.get('NIGHT_START_MINUTE',0)):02d}–{int(cfg.get('NIGHT_END_HOUR',0)):02d}:{int(cfg.get('NIGHT_END_MINUTE',0)):02d} · "
            f"Leistung {int(cfg.get('NIGHT_DISCHARGE_POWER_W',0))} W{night_extra}</div>"
        )
    grid_warning_html = ""
    if not m["grid_valid"]:
        grid_warning_html = "<div class='zec-card-warning'><b>Hinweis:</b> Netzleistungswert prüfen.</div>"
    zendure_warning_html = ""
    if not m["mqtt_ok"]:
        zendure_warning_html = "<div class='zec-card-warning'><b>Hinweis:</b> Zendure-MQTT nicht vollständig frisch. SOC/Leistung bitte prüfen.</div>"
    logging_warning_html = ""
    if m["logging_mode"] == "off" or m["logging_status"] == "off":
        logging_warning_html = "<div class='zec-card-warning'><b>Hinweis:</b> Messdatenstatus: disabled.</div>"
    elif m["logging_status"] != "active":
        logging_warning_html = "<div class='zec-card-warning'><b>Hinweis:</b> Messdatenstatus: " + html.escape(str(m["logging_status"])) + ".</div>"
    global_warnings = []
    if m["errors"]:
        global_warnings.append(f"{m['errors']} Controllerfehler in Folge")
    warning_html = "" if not global_warnings else "<div class='zec-alert-strip'><b>Systemhinweis:</b> " + " · ".join(html.escape(w) for w in global_warnings) + "</div>"
    active_limiter = limiter_text(list(s.get("active_limiters", []))) or str(s.get("target_final_reason") or s.get("control_reason") or "-")
    mode_goal = str(s.get("control_reason") or s.get("target_final_reason") or "Eigenverbrauch optimieren")
    latest_change = str(s.get("last_mode_change_time") or s.get("last_target_change_time") or "-")
    mode_display = html.escape(m["mode_label"])
    charge_text = "Laden" if actual > 0 else ("Entladen" if actual < 0 else "Bereit")
    capacity_kwh = cfg.get("ZENDURE_BATTERY_CAPACITY_KWH") or cfg.get("ZENDURE_TOTAL_CAPACITY_KWH") or cfg.get("BATTERY_CAPACITY_KWH") or "-"
    try:
        capacity_line = f"{float(capacity_kwh):.1f} kWh"
    except Exception:
        capacity_line = str(capacity_kwh)
    uptime = str(s.get("system_uptime_human") or s.get("process_uptime_human") or "-")
    cpu = s.get("cpu_percent", s.get("system_cpu_percent", "-"))
    mem_percent = s.get("memory_percent", s.get("system_memory_percent", "-"))
    mem_used = s.get("memory_used_mb", "-")
    mem_total = s.get("memory_total_mb", "-")
    ntp_time = str(s.get("ntp_time") or s.get("system_time") or "-")
    ntp_offset = str(s.get("ntp_offset_s") or s.get("ntp_offset") or "-")
    mqtt_broker = str(cfg.get("MQTT_BROKER", cfg.get("MQTT_HOST", "-")))
    mqtt_port = str(cfg.get("MQTT_PORT", ""))
    mqtt_broker_line = f"{mqtt_broker}:{mqtt_port}" if mqtt_port else mqtt_broker
    build_time = str(s.get("controller_build_time") or "-")
    page = _modern_body_start(cfg, "status")
    page += f"""
    <main class="modern-page zec-shell">
      <section class="zec-card-row" aria-label="Status-Hauptkarten">
        <div class="zec-card mockup-top-card">
          <div class="zec-card-label">{_ui_icon("bolt")}<span>Netzleistung</span></div>
          <div class="zec-card-value big2 {grid_cls}">{grid_kw:+.2f} kW</div>
          <div class="zec-card-sub">{'Bezug aus Netz' if grid > 0 else 'Einspeisung / Überschuss' if grid < 0 else 'Netzleistung ausgeglichen'}</div>
          <div id="gridMiniSparkline">{grid_sparkline}</div>
          <div class="zec-card-sub"><span class="status-dot {'ok' if m['grid_valid'] else 'warn'}"></span> Quelle: {html.escape(source_detail)}</div>
        </div>
        <div class="zec-card mockup-top-card">
          <div class="zec-card-label">{_ui_icon("mode")}<span>Betriebsmodus</span></div>
          <div class="zec-card-value {('zec-accent-green' if current_mode.startswith('AUTO') else '')}">{mode_display}</div>
          <div class="zec-card-sub" style="font-size:18px;margin-top:10px">{html.escape(current_mode)}</div>
          <div class="zec-card-sub" style="margin-top:22px">⌁ Ziel: {html.escape(mode_goal)}<br>◴ Letzte Änderung: {html.escape(latest_change)}</div>
          {night_line}
        </div>
        <div class="zec-card mockup-top-card zec-battery-card">
          <div class="zec-card-label">{_ui_icon("battery")}<span>Zendure (Batterie)</span></div>
          <div class="zec-battery-layout">
            <div class="soc-ring" style="--soc:{soc_ring}%"><span><b class="soc-value">{soc_num if soc_num is not None else '-'} %</b><small class="soc-label">SOC</small></span></div>
            <div class="zec-battery-metrics">
              <div><div class="zec-battery-metric-label">Lade-/Entladeleistung</div><div class="zec-battery-metric-value {actual_cls}">{actual_kw:+.2f} kW</div></div>
              <div><div class="zec-battery-metric-label">Zustand</div><b>{html.escape(charge_text)}</b></div>
              <div><div class="zec-battery-metric-label">Kapazität</div><b>{html.escape(capacity_line)}</b></div>
            </div>
          </div>
          <div class="zec-card-sub"><span class="status-dot {'ok' if m['mqtt_ok'] else 'warn'}"></span> Quelle: MQTT <span style="float:right">Status: {'gültig' if m['mqtt_ok'] else 'prüfen'}</span></div>
          {zendure_warning_html}
        </div>
        <div class="zec-card mockup-top-card">
          <div class="zec-card-label">{_ui_icon("meter")}<span>{html.escape(source_title)}</span></div>
          <table class="mockup-card-table">
            <tr><td>Gerät</td><td>{html.escape(source_device)}</td></tr>
            <tr><td>Quelle</td><td>{html.escape(source_detail)}</td></tr>
            <tr><td>Verbindung</td><td>{'Aktiv' if m['grid_valid'] else 'Prüfen'} <span class="status-dot {'ok' if m['grid_valid'] else 'warn'}"></span></td></tr>
            <tr><td>Paket-Rate</td><td>{html.escape(packet_rate_line)}</td></tr>
            <tr><td>Socket-Modus</td><td>{html.escape(socket_mode)}</td></tr>
          </table>
          <div class="zec-card-sub"><span class="status-dot {'ok' if m['grid_valid'] else 'warn'}"></span> Letztes Paket: Alter {source_age}</div>
          {grid_warning_html}
        </div>
        <div class="zec-card mockup-top-card">
          <div class="zec-card-label">{_ui_icon("database")}<span>Messdaten / Logging</span></div>
          <table class="mockup-card-table">
            <tr><td>Logging</td><td>{'Aktiv' if m['logging_status']=='active' else 'Aus'} <span class="status-dot {'ok' if m['logging_status']=='active' else 'warn'}"></span></td></tr>
            <tr><td>Messdaten-CSV</td><td>{'Aktiv' if m['logging_mode']!='off' else 'Aus'} <span class="status-dot {'ok' if m['logging_mode']!='off' else 'warn'}"></span></td></tr>
            <tr><td>SQLite-Graphspeicher</td><td>{'Aktiv' if db_active else html.escape(str(m.get('db_status') or '-'))} <span class="status-dot {'ok' if db_active else 'warn'}"></span></td></tr>
            <tr><td>Intervall</td><td>{measurement_interval} s</td></tr>
            <tr><td>Gespeicherte Daten</td><td>Heute: {html.escape(str(rows_today))}<br>Gesamt: {html.escape(str(rows_total))}</td></tr>
            <tr><td>Datei</td><td>{html.escape(measurement_file)}</td></tr>
            <tr><td>DB-Datei</td><td>{html.escape(measurement_db_file)}</td></tr>
            <tr><td>Pfad</td><td>{html.escape(measurement_path)}</td></tr>
          </table>
          {logging_warning_html}
        </div>
      </section>
      {warning_html}
      {build_modern_soc_day_section(cfg)}
      <section class="mockup-footer-grid" aria-label="Systemstatus">
        <div class="mockup-footer-card"><h3>{_ui_icon("clock")}<span>Systemlaufzeit</span></h3><div class="num">{html.escape(uptime)}</div><div class="sub">Controllerprozess / System</div></div>
        <div class="mockup-footer-card"><h3>{_ui_icon("cpu")}<span>CPU Auslastung</span></h3><div class="num">{html.escape(str(cpu))} %</div><div class="sub">Momentanwert; Verlauf nicht verfügbar</div></div>
        <div class="mockup-footer-card"><h3>{_ui_icon("memory")}<span>Speicherauslastung</span></h3><div class="num">{html.escape(str(mem_percent))} %</div><div class="sub">{html.escape(str(mem_used))} MB / {html.escape(str(mem_total))} MB</div></div>
        <div class="mockup-footer-card"><h3>{_ui_icon("radio")}<span>MQTT</span></h3><div class="num {'zec-accent-green' if m['mqtt_ok'] else 'zec-accent-yellow'}">{'Verbunden' if m['mqtt_ok'] else 'Prüfen'}</div><div class="sub">Broker: {html.escape(mqtt_broker_line)}<br>Client-ID: {html.escape(str(cfg.get('MQTT_CLIENT_ID','-')))}</div></div>
        <div class="mockup-footer-card"><h3>{_ui_icon("clock")}<span>NTP Zeit</span></h3><div class="num" style="font-size:18px">{html.escape(ntp_time)}</div><div class="sub">Offset: {html.escape(ntp_offset)}<br><span class="status-dot ok"></span> Quelle: System</div></div>
        <div class="mockup-footer-card"><h3>{_ui_icon("server")}<span>Controller</span></h3><div class="num">{APP_VERSION_LABEL}</div><div class="sub">Build: {html.escape(build_time)}<br>Reason: {html.escape(active_limiter)}</div></div>
      </section>
      <div id="modern-diagnostics" style="display:none">Legacy-Fallback: /status_old · /graph_old · {html.escape(compatibility_status_text)}</div>
    </main>
    <script>
    (function(){{
      async function refreshGridMiniSparkline(){{
        if (document.visibilityState === 'hidden') return;
        const box = document.getElementById('gridMiniSparkline');
        if (!box) return;
        try {{
          const res = await fetch('/grid-mini-sparkline', {{cache:'no-store'}});
          if (!res.ok) return;
          const svg = await res.text();
          if (svg && svg.indexOf('<svg') >= 0) box.innerHTML = svg;
        }} catch(e) {{}}
      }}
      setInterval(refreshGridMiniSparkline, 10000);
      document.addEventListener('visibilitychange', function(){{ if(document.visibilityState !== 'hidden') refreshGridMiniSparkline(); }});
    }})();
    </script>
    """
    page += build_footer()
    return page


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




def build_graph_page(cfg: Dict[str, Any]) -> str:
    page = _modern_body_start(cfg, "graph", force_dark=True)
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


def build_settings_page(cfg: Dict[str, Any], validation_issues: Optional[List[ValidationIssue]] = None, validation_state: str = "", saved: bool = False, restart_required: bool = False, restart_keys: str = "") -> str:
    error_keys = validation_issue_keys(validation_issues, "ERROR")
    warning_keys = validation_issue_keys(validation_issues, "WARNING")
    page = build_base_header("Zendure Settings", cfg=cfg)
    nav_links = "".join(
        f"<a href='#settings-section-{index}'>{html.escape(group)}</a>"
        for index, group in enumerate(GROUP_ORDER)
    )
    page += "<form method='post' action='/save-config'>"
    page += (
        f"<div class='section' id='settings-top'>{section_title('Zendure Energy Controller Settings', 1, True)}"
        + build_validation_messages(validation_issues, validation_state)
        + build_save_result_message(cfg, saved, restart_required, restart_keys)
        + "<div class='small'>Änderungen werden validiert und atomar in config.json gespeichert. "
        "Wichtig: Änderungen werden erst übernommen und gespeichert, wenn auf einen "
        "<b>Speichern</b>-Button geklickt wird. Nach dem Speichern werden Änderungen sofort aktiv. "
        "Ausnahmen sind z. B. MQTT-/Topic-, Web-Port- oder Startparameter-Änderungen; "
        "dort ist ein Neustart weiterhin empfehlenswert.</div>"
        f"<div class='subnav'>{nav_links}</div>"
        "</div>"
    )

    for index, group in enumerate(GROUP_ORDER):
        section_id = f"settings-section-{index}"
        page += (
            f"<div class='section' id='{section_id}'>"
            f"<h2>{html.escape(group)}</h2>"
            f"<div class='section-tools'><a href='#' onclick=\"expandSectionInfo('{section_id}'); return false;\">Alle Infos auf- und zuklappen</a> &nbsp;|&nbsp; <a href='#page-top'>nach oben</a></div>"
            + build_section_validation_messages(group, validation_issues)
        )
        page += "<div class='grid'>" + section_intro_box(group) + "</div>"
        if group == "Messdaten / Historie":
            mode = measurement_log_mode(cfg)
            retention_h = estimate_retention_hours(cfg)
            mounts = detected_log_mounts()
            if mounts:
                mount_lines = "<br>Erkannte externe Ziele: " + "; ".join(
                    f"<code>{html.escape(str(m.get('mountpoint')))}</code> ({html.escape(str(m.get('free_mb', '-')))} MB frei, {'schreibbar' if m.get('writable') else 'nicht schreibbar'})"
                    for m in mounts[:5]
                )
            else:
                mount_lines = "<br>Erkannte externe Ziele: keine beschreibbaren USB-/Mountpoints gefunden."
            resolved_path, fallback_active, target_reason = resolve_log_path(cfg, allow_fallback=True)
            storage_target = str(cfg.get("MEASUREMENT_LOG_STORAGE_TARGET", "internal_sd"))
            configured_subdir = str(cfg.get("MEASUREMENT_LOG_DIR", "logs") or "logs").lstrip("/")
            mountpoint_info = ""
            if target_reason.startswith("external_mount:") or target_reason.startswith("external_auto:"):
                mountpoint_info = target_reason.split(":", 1)[1]
            elif storage_target == "external_mount":
                configured = str(cfg.get("MEASUREMENT_LOG_MOUNTPOINT", "") or "").strip()
                mountpoint_info = configured or "automatische Erkennung"
            page += (
                "<div class='info-box' style='margin:12px 0;'>"
                "<b>Messdaten-Modi:</b><br>"
                "<b>Aus</b>: keine zyklischen Messdaten, maximale SD-Schonung; spätere Analyse aus neuen Daten ist nicht möglich.<br>"
                "<b>Standard</b>: vollständige Reglerdiagnose inklusive Roh-/Norm-Kernwerten, Freshness/Validity, MQTT-Stale-Aggregat, Sollwertkaskade, Kommando und Szenario ohne Zendure.<br>"
                "<b>Erweitert</b>: Standard plus Detaildaten für Simulation, What-if sowie tiefe MQTT-/Freshness-/Packdatenanalyse; erzeugt größere Dateien und sollte gezielt verwendet werden.<br>"
                f"Aktueller Modus: <b>{html.escape(mode)}</b>. Grob geschätzte Aufbewahrung bei aktuellen Grenzwerten: <b>{html.escape(str(retention_h))} Stunden</b>. "
                "Diese Schätzung ist bewusst praxisnah, nicht bytegenau. Die Regelung läuft weiter, auch wenn Logging pausiert oder fehlschlägt.<br>"
                f"Speicherziel: <b>{html.escape(storage_target)}</b><br>"
                + (f"USB-/Mountpoint: <code>{html.escape(mountpoint_info)}</code><br>" if storage_target == "external_mount" else "")
                + (f"Unterordner auf dem Ziel: <code>{html.escape(configured_subdir)}</code><br>" if storage_target == "external_mount" else "")
                + f"Aktive Datei: <code>{html.escape(resolved_path)}</code>"
                + (" <b>(SD-Fallback aktiv)</b>" if fallback_active else "")
                + f"<br>Zielstatus: {html.escape(target_reason)}"
                + mount_lines
                + "</div>"
            )
        page += "<div class='grid'>"
        if group == "Nachtmodus":
            if "NIGHT_DISCHARGE_ENABLED" in CONFIG_SCHEMA:
                meta = CONFIG_SCHEMA["NIGHT_DISCHARGE_ENABLED"]
                page += build_setting_card("NIGHT_DISCHARGE_ENABLED", meta, cfg.get("NIGHT_DISCHARGE_ENABLED"), "NIGHT_DISCHARGE_ENABLED" in error_keys, "NIGHT_DISCHARGE_ENABLED" in warning_keys)
            page += build_night_time_card(
                "NIGHT_START_TIME",
                "Startzeit",
                cfg.get("NIGHT_START_HOUR"),
                cfg.get("NIGHT_START_MINUTE"),
                "Startzeit des Nachtmodus im Format hh:mm. Eingaben wie 5:30 werden beim Verlassen des Feldes sichtbar zu 05:30 normalisiert.",
                "NIGHT_START_HOUR" in error_keys or "NIGHT_START_MINUTE" in error_keys,
                "NIGHT_START_HOUR" in warning_keys or "NIGHT_START_MINUTE" in warning_keys,
            )
            page += build_night_time_card(
                "NIGHT_END_TIME",
                "Endzeit",
                cfg.get("NIGHT_END_HOUR"),
                cfg.get("NIGHT_END_MINUTE"),
                "Endzeit des Nachtmodus im Format hh:mm. Nachtfenster über Mitternacht werden weiterhin unterstützt.",
                "NIGHT_END_HOUR" in error_keys or "NIGHT_END_MINUTE" in error_keys,
                "NIGHT_END_HOUR" in warning_keys or "NIGHT_END_MINUTE" in warning_keys,
            )
        current_subgroup = None
        for key, meta in CONFIG_SCHEMA.items():
            if meta.get("group") != group:
                continue
            if meta.get("hidden"):
                continue
            if group == "Nachtmodus" and key in {"NIGHT_DISCHARGE_ENABLED", "NIGHT_START_HOUR", "NIGHT_START_MINUTE", "NIGHT_END_HOUR", "NIGHT_END_MINUTE"}:
                continue
            subgroup = str(meta.get("subgroup", "") or "")
            if subgroup and subgroup != current_subgroup:
                if current_subgroup is not None:
                    page += "</div><div class='grid'>"
                page += f"<div class='card subgroup-card'><h3>{html.escape(subgroup)}</h3>{subgroup_help_text(subgroup)}</div>"
                current_subgroup = subgroup
            page += build_setting_card(key, meta, cfg.get(key), key in error_keys, key in warning_keys)
        page += "</div>"
        if group == "Manueller Modus":
            page += "<div class='small' style='margin-top:12px;'>Die Detailfelder werden abhängig vom gewählten manuellen Modus eingeblendet. Ohne JavaScript bleiben sie sichtbar, damit die Seite weiterhin vollständig bedienbar ist.</div>"
        page += "<button class='save' type='submit'>Speichern</button>"
        page += "</div>"

    page += "</form>"
    page += build_footer()
    return page

def unit_to_label(unit: str) -> str:
    return {"W": "in Watt", "s": "in Sekunden", "%": "in Prozent", "Bytes": "in Bytes"}.get(unit, unit)


def manual_card_attr(key: str) -> str:
    if key == "MANUAL_MODE":
        return ' data-manual-card="base"'
    if key in MANUAL_DISCHARGE_KEYS:
        return ' data-manual-card="discharge"'
    if key in MANUAL_CHARGE_KEYS:
        return ' data-manual-card="charge"'
    return ""


def cross_profile_card_attr(meta: Dict[str, Any]) -> str:
    profile = str(meta.get("cross_profile", "") or "")
    if profile in {"evcc", "custom"}:
        return ' data-cross-profile="{}"'.format(html.escape(profile, quote=True))
    return ""


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
