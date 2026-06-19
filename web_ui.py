# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

import csv
import html
import io
import os
import shlex
import subprocess
import threading
from typing import Any, Dict, Iterable, List, Optional

import requests
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse

from config_manager import CONFIG_SCHEMA, ConfigManager, validate_config
from config_validator import ValidationIssue, restart_relevant_changes, split_issues, validate_config_semantics
from cross_charge import cross_charge_enabled
from csv_logger import rows_to_csv, estimate_retention_hours, measurement_log_mode, detected_log_mounts, resolve_log_path
from version import APP_VERSION, CSV_SCHEMA
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
    "Cross-Charge-Schutz",
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

    @app.get("/status")
    def status():
        snap = state.snapshot()
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
            headers={"Content-Disposition": "attachment; filename=graph-data.csv"},
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
        return html_or_headless(build_settings_page, cfg, saved=saved, restart_required=restart_required, restart_keys=restart_keys)

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

    @app.get("/logs/current.csv")
    def current_csv_log():
        cfg = config_manager.get()
        if cfg.get("HEADLESS_MODE", False):
            return HTMLResponse(build_headless_page(cfg))
        path, _, _ = resolve_log_path(cfg, allow_fallback=True)
        if not os.path.exists(path):
            return PlainTextResponse("Messdaten-Datei existiert noch nicht oder Messdaten-Logging ist deaktiviert.", status_code=404)
        return FileResponse(path, media_type="text/csv", filename=os.path.basename(path))

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


def build_base_header(title: str, refresh: bool = False, cfg: Optional[Dict[str, Any]] = None) -> str:
    refresh_tag = ""
    dark = bool((cfg or {}).get("UI_DARK_MODE", False))
    theme_css = """
            body { background:#0f172a; color:#e5e7eb; }
            .section { background:#111827; box-shadow:0 2px 10px rgba(0,0,0,0.55); }
            .card { background:#1f2937; border-color:#374151; }
            .label, .small, .technical { color:#cbd5e1; }
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
            .nav {{ margin-bottom:22px; line-height:2.4; display:flex; flex-wrap:wrap; gap:10px 34px; align-items:center; }} .nav a {{ display:inline-block; padding:3px 0; }} .version-pill {{ font-size:12px; font-weight:bold; color:white; background:#777; padding:2px 8px; border-radius:10px; }} .section-title-row {{ display:flex; align-items:center; justify-content:space-between; gap:16px; }} .section-title-row h1, .section-title-row h2 {{ margin-top:0; }}
            .subnav {{ margin-top:14px; line-height:2.2; display:flex; flex-wrap:wrap; gap:8px 24px; align-items:center; }} .subnav a {{ display:inline-block; }}
            canvas {{ width:100%; max-height:520px; }}
            .mini-chart-frame {{ height:230px; min-height:230px; max-height:230px; overflow:hidden; }}
            #miniChart {{ height:210px !important; max-height:210px !important; }}
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
            document.addEventListener('DOMContentLoaded', function() {{
                setupPersistentDetails();
                toggleManualFields();
                toggleCrossChargeFields();
                setupNightTimeInputs();
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
    <div class="nav"><a href="/">Status</a><a href="/graph">Großer Graph</a><a href="/settings">Settings</a><a href="/mqtt-diagnostics">MQTT Diagnose</a><a href="/zendure-properties">Zendure Properties</a><a href="/graph-data.csv">Download Graph CSV</a><a href="/logs/current.csv">Download Messdaten CSV</a><a href="/manual.pdf">Download Handbuch</a><a href="/docs">API Docs</a></div>
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


def build_status_page(cfg: Dict[str, Any], s: Dict[str, Any]) -> str:
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
            f"Quelle: Shelly/UniMeter · Alter: {age_text(grid_age)}<br>"
            f"{auto_rule_line}<br>"
            f'positiv = <span class="red">Netzbezug</span>, negativ = <span class="green">Einspeisung</span>'
        )
    else:
        grid_details = (
            f"{grid_status_line}<br>"
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
    night_details = (
        f"Zeitfenster: {int(cfg.get('NIGHT_START_HOUR', 0)):02d}:{int(cfg.get('NIGHT_START_MINUTE', 0)):02d}–{int(cfg.get('NIGHT_END_HOUR', 0)):02d}:{int(cfg.get('NIGHT_END_MINUTE', 0)):02d}<br>"
        f"Leistung: {int(cfg.get('NIGHT_DISCHARGE_POWER_W', 0))} W<br>"
        f"Reserve-SOC: {night_stop_soc if night_stop_soc is not None else '-'} %<br>"
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
            settings_group='Cross-Charge-Schutz'
        )
        sma_card_html = status_card(
            second_name_html,
            f'{sma_display_power:.1f} W',
            f'Darstellung: positiv = Ladung, negativ = Entladung<br>'
            f'Entladung berechnet: {s["sma_battery_discharge_power"]:.1f} W<br>'
            f'SOC: {s["sma_battery_soc"] if s["sma_battery_soc"] is not None else "-"} %<br>'
            f'MQTT Update: {s["last_sma_battery_update_time"]}',
            'gray',
            f'Dieser Wert kommt per MQTT aus der generischen MQTT-Zusatzbatterie-Integration. Für die Anzeige wird die in den Settings konfigurierte Vorzeichenlogik berücksichtigt: positiv bedeutet Ladung von {second_name_html}, negativ bedeutet Entladung. Der positive Entladewert wird intern für den Cross-Charge-Schutz genutzt, um Batterie-zu-Batterie-Ladung zu vermeiden.',
            settings_group='Cross-Charge-Schutz'
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
    measurement_log_details = (
        f"Status: {measurement_status}<br>"
        f"Aktives Ziel: {active_target} · konfiguriert: {configured_target}<br>"
        f"Datei: {measurement_path}<br>"
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
            Die Überschriften der Karten in diesem Bereich sind anklickbar und öffnen den jeweils passenden Konfigurationsbereich in den Settings.
        </div>
        <div class="section-tools"><a href="#" onclick="expandSectionInfo('status-overview'); return false;">Alle Infos auf- und zuklappen</a></div>
        <div class="grid" id="status-overview">
            {status_card(
                'Netzleistung',
                grid_main_value,
                grid_details,
                grid_class,
                'Der Hauptwert ist der aktuelle Shelly-/UniMeter-Messwert am Netzanschlusspunkt. AUTO-spezifische Diagnosewerte wie der geglättete Regelwert werden nur als Diagnose gezeigt und in festen Modi als nicht aktiv markiert. Feste Nachtentladung oder Stop/Hold hängen dadurch nicht von Grid-Daten ab, die Statusseite zeigt sie aber best-effort aktuell an.',
                settings_group='Regelung'
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
                f'Soll {signed_power(zendure_setpoint_signed)}',
                f'Headunit erreicht: {actual_system_html}<br>'
                f'Angefordertes Lade-Limit: {s["last_input_power"]} W / Entlade-Limit: {s["last_output_power"]} W<br>'
                f'Darstellung: positiv = Ladung, negativ = Entladung',
                zendure_setpoint_class,
                'Diese Karte unterscheidet zwischen der vom Controller angeforderten Sollleistung und der tatsächlich an der Zendure-Headunit erreichten Systemleistung. Positive Werte bedeuten Laden, negative Werte Entladen. Bei aktiver Entladeanforderung werden mehrdeutige positive Pack-Rohwerte als interner Pack-zu-Headunit-Fluss und damit systemisch als Entladung interpretiert. Abweichungen sind normal: inputLimit/outputLimit sind nur Vorgaben; die reale Leistung hängt von Zendure-Firmware, Ladezustand, Temperatur, internen Grenzen, AC/DC-Pfad und Reaktionszeit ab.',
                settings_group='Regelung'
            )}
            {status_card(
                'Aktueller Modus',
                badge(mode_label(current_mode), mode_color),
                f'Aktiv seit: {s["last_mode_change_time"]} ({format_hms(s["last_mode_duration_seconds"])})<br>{html.escape(str(s["control_reason"]))}',
                'gray',
                'Zeigt den aktuellen Betriebszustand des Controllers. Die farbige Anzeige nutzt den verständlichen Modusnamen. Der technische Modus-Code bleibt darunter sichtbar, damit Graph-, CSV- und Eventdaten eindeutig zugeordnet werden können.',
                current_mode,
                settings_group='Regelung'
            )}
            {status_card(
                'Betriebsart',
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
        </div>
    </div>
    {build_mini_graph_section()}
    <div class="section">{heading_link('Diagnose', 'Sicherheit / Fallback', 2)}<div class="section-tools"><a href="#" onclick="expandSectionInfo('status-diagnostics'); return false;">Alle Infos auf- und zuklappen</a></div><div class="grid" id="status-diagnostics">
        {status_card('Aktive Betriebslogik', html.escape(path_human), html.escape(str(s['last_control_action'])), 'gray', 'Die aktive Betriebslogik beschreibt den aktuell verwendeten Entscheidungsweg des Controllers in verständlicher Form. Der technische Code bleibt darunter sichtbar, damit man Events, Graphdaten und Logausgaben eindeutig zuordnen kann.', path_code)}
        {status_card('Regelzyklus', f'{s["last_loop_duration_ms"]} ms', f'Zyklen: {s["loop_counter"]}<br>Uptime: {format_dhms(s["uptime_seconds"])}', 'gray', 'Ein Regelzyklus ist ein kompletter Durchlauf der Steuerung: Messwerte lesen, Schutzlogik prüfen, Zielwert berechnen, MQTT-Befehl senden und Graph-/CSV-Daten speichern. Die Dauer zeigt, wie lange dieser Durchlauf gebraucht hat; das Intervall wird in den Settings festgelegt.')}
        {status_card('Fehler', str(s['consecutive_errors']), f'Letzter Fehler: {html.escape(str(s["last_error"]))}<br>Zeitpunkt: {html.escape(str(s.get("last_error_time", "-")))}<br>Safe-State: {s["safe_state_counter"]}x', 'red', 'Der Fehlerzähler zählt direkt aufeinanderfolgende Fehler. Safe-State bedeutet: Lade- und Entladeleistung werden auf 0 W gesetzt, um bei unsicheren Daten oder Kommunikationsproblemen keine unkontrollierte Energieverschiebung auszulösen.')}
        {status_card('Messdaten-Logging', measurement_mode, measurement_log_details, 'gray', 'Messdaten-Logging ist optional und nachgelagert. Standard speichert vollständige Reglerdiagnose inklusive MQTT-Stale-Aggregat und Szenario ohne Zendure. Erweitert ergänzt große Detaildaten für Simulation, What-if und tiefe MQTT-/Freshness-Analyse. USB-/SD-Fallback-Details sind Betriebsdiagnose und werden im Runtime-Log dokumentiert; die Regelung läuft weiter, auch wenn Logging pausiert oder fehlschlägt.', settings_group='Messdaten / Historie')}
        {status_card('Analyse-Weboberfläche', f'Port {replay_port}', analysis_link_html, 'gray', 'Die Analyse läuft bewusst getrennt vom Live-Regler. Der Dienst wird mitgeliefert, aber nicht automatisch aktiviert.')}
        {status_card('High-SOC-Ladeannahme', html.escape(str(s.get('charge_acceptance_state', 'ok'))), html.escape(str(s.get('charge_acceptance_reason', '-'))), 'gray', 'Leichtgewichtige Diagnose: Zeigt, ob Zendure eine angeforderte Ladeleistung bei hohem SOC plausibel annimmt. Diese Diagnose greift nicht aktiv in die Regelung ein.')}
    </div></div>
    {build_event_section(s['event_history'])}
    """
    page += build_footer()
    return page

def build_mini_graph_section() -> str:
    return """
    <div class="section">
        <h2><a class="section-heading-link" href="/settings#settings-section-7" title="Passenden Konfigurationsbereich öffnen">Kurzverlauf</a></h2>
        <div class="small">Kompakte Übersicht: Netzleistung, signierte Zendure-Soll-/Istleistung und SOC. <a href="/graph">Ausführliche Graph-Seite öffnen</a></div>
        <div class="mini-chart-frame" style="height:230px;min-height:230px;position:relative;margin-top:8px;">
            <canvas id="miniChart" height="210" style="width:100%;height:210px;display:block;"></canvas>
        </div>
        <div id="miniChartFallback" class="small"></div>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
        const MINI_GRAPH_VISIBILITY_KEY = 'zendure-controller-mini-graph-visibility-v12_8';
        let miniChart = null;

        function loadMiniGraphVisibility() {
            try {
                return JSON.parse(localStorage.getItem(MINI_GRAPH_VISIBILITY_KEY) || '{}');
            } catch (e) {
                return {};
            }
        }

        function saveMiniGraphVisibilityFromChart() {
            if (!miniChart) return;
            const visibility = {};
            miniChart.data.datasets.forEach(function(dataset, index) {
                visibility[dataset.label] = miniChart.isDatasetVisible(index);
            });
            try {
                localStorage.setItem(MINI_GRAPH_VISIBILITY_KEY, JSON.stringify(visibility));
            } catch (e) {}
        }

        function applyMiniStoredVisibility(datasets) {
            const visibility = loadMiniGraphVisibility();
            datasets.forEach(function(dataset) {
                if (Object.prototype.hasOwnProperty.call(visibility, dataset.label)) {
                    dataset.hidden = !visibility[dataset.label];
                }
            });
            return datasets;
        }

        async function loadMiniGraph() {
            const res = await fetch('/graph-data');
            const data = await res.json();
            const labels = data.map(x => x.timestamp);
            const canvas = document.getElementById('miniChart');
            if (window.Chart) {
                const defaultLegendClickHandler = Chart.defaults.plugins.legend.onClick;
                const datasets = applyMiniStoredVisibility([
                    { label:'Netzleistung (Watt)', data:data.map(x=>x.grid_power), borderWidth:2, pointRadius:0 },
                    { label:'Zendure Sollleistung (Watt)', data:data.map(x=>(x.zendure_target_power_w ?? x.zendure_target_signed_power ?? x.charge_power ?? 0)), borderWidth:1, pointRadius:0 },
                    { label:'Zendure Istleistung (Watt)', data:data.map(x=>(x.zendure_actual_power_w ?? x.zendure_system_signed_power ?? 0)), borderWidth:1, pointRadius:0 },
                    { label:'Zendure SOC (Prozent)', data:data.map(x=>x.soc), borderWidth:1, pointRadius:0, yAxisID:'y1' }
                ]);

                miniChart = new Chart(canvas.getContext('2d'), {
                    type: 'line',
                    data: { labels: labels, datasets: datasets },
                    options: {
                        animation:false,
                        responsive:true,
                        maintainAspectRatio:false,
                        resizeDelay:200,
                        plugins:{
                            legend:{
                                display:true,
                                onClick:function(e, legendItem, legend) {
                                    defaultLegendClickHandler(e, legendItem, legend);
                                    saveMiniGraphVisibilityFromChart();
                                }
                            }
                        },
                        scales:{
                            y:{ beginAtZero:false, title:{ display:true, text:'Leistung in Watt' } },
                            y1:{ position:'right', beginAtZero:true, max:100, title:{ display:true, text:'Zendure SOC in Prozent' } }
                        }
                    }
                });
                return;
            }
            drawMiniFallback(canvas, data);
            document.getElementById('miniChartFallback').innerText = 'Chart.js nicht geladen. Einfache Canvas-Fallback-Darstellung aktiv.';
        }
        function drawMiniFallback(canvas, data) {
            const ctx = canvas.getContext('2d');
            const w = canvas.width = canvas.clientWidth || 900;
            const h = canvas.height = 180;
            ctx.clearRect(0,0,w,h);
            ctx.font = '12px Arial';
            ctx.fillText('Netzleistung/Zendure Soll/Zendure Ist in Watt; SOC in Prozent', 10, 15);
            const vals = [];
            data.forEach(r => { vals.push(r.grid_power_w ?? r.grid_power ?? 0, r.zendure_target_power_w ?? 0, r.zendure_actual_power_w ?? 0); });
            const min = Math.min(-100, ...vals), max = Math.max(100, ...vals);
            function y(v){ return h - 20 - ((v-min)/(max-min))*(h-40); }
            function line(key){ ctx.beginPath(); data.forEach((r,i)=>{ const x=10+i*Math.max(1,(w-20)/Math.max(1,data.length-1)); const yy=y(r[key]||0); if(i===0)ctx.moveTo(x,yy); else ctx.lineTo(x,yy); }); ctx.stroke(); }
            ctx.strokeRect(10,20,w-20,h-40); line('grid_power_w'); line('zendure_target_power_w'); line('zendure_actual_power_w');
        }
        loadMiniGraph().catch(e => { document.getElementById('miniChartFallback').innerText = 'Mini-Graph konnte nicht geladen werden: '+e; });
        </script>
    </div>
    """


def event_display_text(event: Dict[str, Any]) -> str:
    text = str(event.get("text", ""))
    if text.startswith("Moduswechsel: ") and " -> " in text:
        rest = text.replace("Moduswechsel: ", "", 1)
        old, new = rest.split(" -> ", 1)
        return f"Moduswechsel: {mode_label(old)} -> {mode_label(new)} ({old} -> {new})"
    return text


def build_event_section(events: List[Dict[str, Any]]) -> str:
    rows = ""
    for event in reversed(events[-20:]):
        count = int(event.get("count", 1))
        count_text = f" <span class='small'>({count}x)</span>" if count > 1 else ""
        rows += (
            "<div class='small' style='padding:6px 0;border-bottom:1px solid #eee;'>"
            f"<b>{html.escape(str(event.get('time', '-')))}</b> - "
            f"{html.escape(event_display_text(event))}"
            f"{count_text}"
            "</div>"
        )
    if not rows:
        rows = "<div class='small'>Noch keine Events.</div>"
    return "<div class='section'><h2><a class='section-heading-link' href='/settings#settings-section-7' title='Passenden Konfigurationsbereich öffnen'>Historische Events</a></h2>" + rows + "</div>"


def build_graph_page(cfg: Dict[str, Any]) -> str:
    evcc_enabled = bool(cross_charge_enabled(cfg))
    second_name = second_battery_name(cfg)
    second_name_js = second_name.replace("\\", "\\\\").replace("'", "\\'")
    second_name_html = html.escape(second_name)
    evcc_legend = f"""
            <li><b>{second_name_html} Leistung (Watt)</b>: Für die Darstellung normierte Leistung der Zusatzbatterie. Positive Werte bedeuten Laden, negative Werte bedeuten Entladen. Die Vorzeichenlogik aus den Settings wird dabei berücksichtigt.</li>
            <li><b>{second_name_html} SOC (Prozent)</b>: Ladezustand der Zusatzbatterie in Prozent, sofern die MQTT-Datenquelle diesen Wert liefert.</li>
            <li><b>Effektiver Überschuss (Watt)</b>: Überschuss, den der Controller nach Abzug von Zusatzbatterie-Entladung und Sicherheitsreserve noch als sicher nutzbar für Zendure-Ladung betrachtet.</li>
    """ if evcc_enabled else """
            <li><b>Cross-Charge-Schutz</b>: In den Settings deaktiviert. Zusatzbatteriewerte, Zusatzbatterie-SOC und effektiver Überschuss werden auf dieser Seite ausgeblendet.</li>
    """
    page = build_base_header("Zendure Controller Graph", cfg=cfg)
    page += f"""
    <div class="section">
        {section_title('Zendure Controller Live Analyse', 1, True)}
        <div class="small">Linien können per Klick auf die Legende ein- und ausgeblendet werden. <a href="/graph-data.csv">Aktuelle Graph-Daten als CSV herunterladen</a></div>
        <canvas id="powerChart" height="420"></canvas>
        <div id="chartStatus" class="small"></div>
    </div>
    <div class="section">
        <h2>Legende zum großen Graphen</h2>
        <ul class="small legend-list">
            <li><b>Netzleistung (Watt)</b>: Geglättete Netzleistung am Hausanschlusspunkt in Watt. Positive Werte bedeuten Netzbezug, negative Werte Einspeisung.</li>
            <li><b>Netzleistung Rohwert (Watt)</b>: Ungefilterter Shelly-/Uni-Meter-Messwert in Watt. Hilfreich, um Lastsprünge und Filterwirkung zu beurteilen.</li>
            <li><b>Zendure Sollleistung (Watt)</b>: Vom Controller angeforderte signierte Leistung. Positive Werte bedeuten Laden, negative Werte Entladen.</li>
            <li><b>Zendure Istleistung (Watt)</b>: Aus den Headunit-Sensoren abgeleitete reale signierte Systemleistung. Positive Werte bedeuten Laden, negative Werte Entladen. Bei aktiver Entladeanforderung wird eine positive interne Pack-&gt;Headunit-Leistung als Entladung interpretiert, damit Nachtentladung nicht fälschlich als Ladung erscheint.</li>
            <li><b>Pack/DC Rohleistung (Watt)</b>: Zendure-Rohsensor <code>packInputPower</code> bzw. Pack-<code>power</code>. Dieser Wert beschreibt interne DC-/Pack-Flüsse und ist nicht immer identisch mit der externen Systemleistung. Im Nachtmodus kann ein positiver Rohwert bedeuten: Pack liefert Leistung an die Headunit.</li>
            <li><b>AC Haus Ausgang (Watt)</b>: Zendure-MQTT-Sensor <code>outputHomePower</code>. Leistung, die Zendure AC-seitig ins Haus liefert. Bei Entladung können Pack/DC und AC Haus fast gleich groß sein; das ist normal.</li>
            {evcc_legend}
            <li><b>Zielwert nach Rampe (Watt)</b>: Interner Zielwert nach Glättung und Rampenbegrenzung.</li>
            <li><b>Zendure SOC (Prozent)</b>: Ladezustand der Zendure-Batterie in Prozent auf der rechten Achse.</li>
        </ul>
    </div>
    <div class="section"><h2>Messwert-Tabelle</h2><table id="dataTable"></table></div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
    const CROSS_CHARGE_ENABLED = {str(evcc_enabled).lower()};
    const secondName = '{second_name_js}';
    const GRAPH_VISIBILITY_KEY = 'zendure-controller-big-graph-visibility-v12_8';
    let chart = null;

    function loadGraphVisibility() {{
        try {{
            return JSON.parse(localStorage.getItem(GRAPH_VISIBILITY_KEY) || '{{}}');
        }} catch (e) {{
            return {{}};
        }}
    }}

    function saveGraphVisibilityFromChart() {{
        if (!chart) return;
        const visibility = {{}};
        chart.data.datasets.forEach(function(dataset, index) {{
            visibility[dataset.label] = chart.isDatasetVisible(index);
        }});
        try {{
            localStorage.setItem(GRAPH_VISIBILITY_KEY, JSON.stringify(visibility));
        }} catch (e) {{}}
    }}

    function currentGraphVisibility() {{
        const visibility = loadGraphVisibility();
        if (chart) {{
            chart.data.datasets.forEach(function(dataset, index) {{
                visibility[dataset.label] = chart.isDatasetVisible(index);
            }});
        }}
        return visibility;
    }}

    function applyStoredVisibility(datasets) {{
        const visibility = currentGraphVisibility();
        datasets.forEach(function(dataset) {{
            if (Object.prototype.hasOwnProperty.call(visibility, dataset.label)) {{
                dataset.hidden = !visibility[dataset.label];
            }}
        }});
        return datasets;
    }}

    function buildTable(data) {{
        let html = '<tr><th>Datum</th><th>Zeit</th><th>Netzleistung (Watt)</th><th>Rohwert (Watt)</th><th>Zendure Soll (Watt)</th><th>Zendure Ist (Watt)</th><th>Pack/DC Roh (Watt)</th><th>AC Haus Roh (Watt)</th><th>Ladeannahme</th>';
        if (CROSS_CHARGE_ENABLED) {{
            html += '<th>' + secondName + ' (Watt)</th><th>' + secondName + ' SOC (Prozent)</th><th>Effektiver Überschuss (Watt)</th>';
        }}
        html += '<th>Zendure SOC (Prozent)</th><th>Modus</th><th>Begrenzung</th></tr>';
        data.slice().reverse().forEach(r => {{
            html += `<tr><td>${{r.date ?? ''}}</td><td>${{r.timestamp}}</td><td>${{r.grid_power_w ?? r.grid_power}}</td><td>${{r.raw_grid_power_w ?? r.raw_grid_power}}</td><td>${{r.zendure_target_power_w ?? ''}}</td><td>${{r.zendure_actual_power_w ?? r.zendure_system_signed_power ?? ''}}</td><td>${{r.zendure_raw_pack_input_power_w ?? r.zendure_pack_power ?? r.actual_zendure_charge_power}}</td><td>${{r.zendure_raw_output_home_power_w ?? r.zendure_ac_home_power ?? r.actual_zendure_discharge_power}}</td><td>${{r.charge_acceptance_state ?? ''}}</td>`;
            if (CROSS_CHARGE_ENABLED) {{
                html += `<td>${{r.sma_battery_display_power ?? r.sma_battery_power}}</td><td>${{r.sma_soc ?? ''}}</td><td>${{r.effective_export_power}}</td>`;
            }}
            html += `<td>${{r.soc}}</td><td>${{r.mode_label ?? r.mode}}</td><td>${{r.limit_label ?? r.limit_reason}}</td></tr>`;
        }});
        document.getElementById('dataTable').innerHTML = html;
    }}
    async function updateGraph() {{
        const res = await fetch('/graph-data');
        const data = await res.json();
        buildTable(data);
        if (!window.Chart) {{ document.getElementById('chartStatus').innerText = 'Chart.js wurde nicht geladen. Die Tabelle und der CSV-Export funktionieren weiterhin.'; return; }}
        const labels = data.map(x => x.timestamp);
        let datasets = [
            {{label:'Netzleistung (Watt)', data:data.map(x=>(x.grid_power_w ?? x.grid_power)), borderWidth:2, pointRadius:0}},
            {{label:'Netzleistung Rohwert (Watt)', data:data.map(x=>(x.raw_grid_power_w ?? x.raw_grid_power)), borderWidth:1, pointRadius:0, hidden:true}},
            {{label:'Zendure Sollleistung (Watt)', data:data.map(x=>(x.zendure_target_power_w ?? x.zendure_target_signed_power ?? 0)), borderWidth:2, pointRadius:0}},
            {{label:'Zendure Istleistung (Watt)', data:data.map(x=>(x.zendure_actual_power_w ?? x.zendure_system_signed_power ?? 0)), borderWidth:2, pointRadius:0}},
            {{label:'Pack/DC Rohleistung (Watt)', data:data.map(x=>(x.zendure_raw_pack_input_power_w ?? x.zendure_pack_power ?? x.actual_zendure_charge_power)), borderWidth:1, pointRadius:0, hidden:true}},
            {{label:'AC Haus Ausgang Roh (Watt)', data:data.map(x=>(x.zendure_raw_output_home_power_w ?? x.zendure_ac_home_power ?? x.actual_zendure_discharge_power)), borderWidth:1, pointRadius:0, hidden:true}}
        ];
        if (CROSS_CHARGE_ENABLED) {{
            datasets.push({{label:secondName + ' Leistung (Watt)', data:data.map(x=>(x.second_battery_power_w ?? x.sma_battery_display_power ?? x.sma_battery_power)), borderWidth:1, pointRadius:0, hidden:true}});
            datasets.push({{label:secondName + ' SOC (Prozent)', data:data.map(x=>x.sma_soc), borderWidth:1, pointRadius:0, yAxisID:'y1', hidden:true}});
            datasets.push({{label:'Effektiver Überschuss (Watt)', data:data.map(x=>(x.effective_export_power_w ?? x.effective_export_power)), borderWidth:1, pointRadius:0, hidden:true}});
        }}
        datasets.push({{label:'Zielwert nach Rampe (Watt)', data:data.map(x=>(x.target_after_ramp_w ?? x.target_after_ramp)), borderWidth:1, pointRadius:0, hidden:true}});
        datasets.push({{label:'Zendure SOC (Prozent)', data:data.map(x=>(x.zendure_soc_percent ?? x.soc)), borderWidth:1, pointRadius:0, yAxisID:'y1', hidden:true}});
        datasets = applyStoredVisibility(datasets);
        if (!chart) {{
            const defaultLegendClickHandler = Chart.defaults.plugins.legend.onClick;
            chart = new Chart(document.getElementById('powerChart').getContext('2d'), {{
                type:'line', data:{{labels:labels, datasets:datasets}},
                options:{{
                    animation:false,
                    responsive:true,
                    interaction:{{mode:'index',intersect:false}},
                    plugins:{{
                        legend:{{
                            display:true,
                            onClick:function(e, legendItem, legend) {{
                                defaultLegendClickHandler(e, legendItem, legend);
                                saveGraphVisibilityFromChart();
                            }}
                        }}
                    }},
                    scales:{{
                        y:{{beginAtZero:false, title:{{display:true, text:'Leistung in Watt'}}}},
                        y1:{{position:'right', beginAtZero:true, max:100, title:{{display:true, text:'SOC in Prozent'}}}}
                    }}
                }}
            }});
        }} else {{
            chart.data.labels = labels;
            chart.data.datasets = datasets;
            chart.update();
        }}
    }}
    setInterval(updateGraph, 2000); updateGraph();
    </script>
    """
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
        parts.append(
            "<div class='error-box'>"
            "<b>Konfiguration wurde nicht gespeichert.</b> "
            "Bitte korrigiere die folgenden Fehler. Die bisherigen Einstellungen bleiben unverändert."
            f"<ul>{error_rows}</ul>"
            "</div>"
            + "".join(additional_parts) +
            "<div id='validationModal' class='validation-modal' role='dialog' aria-modal='true'>"
            "<div class='validation-modal-content'>"
            "<h2>Konfiguration wurde nicht gespeichert</h2>"
            "<p>Mindestens eine Einstellung ist unvollständig, widersprüchlich oder nicht erreichbar. "
            "Die betroffenen Felder sind rot markiert. Warnungen werden erst nach Behebung der Fehler gesondert behandelt.</p>"
            f"<ul>{error_rows}</ul>"
            "<button type='button' onclick='closeValidationModal()'>Dialog schließen und Fehler prüfen</button>"
            "</div></div>"
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
            "<div id='validationModal' class='validation-modal' role='dialog' aria-modal='true'>"
            "<div class='validation-modal-content warning'>"
            "<h2>Konfiguration enthält Warnungen</h2>"
            "<p>Das Speichern ist möglich, aber die folgenden Punkte sollten bewusst bestätigt werden. "
            "Betroffene Felder sind gelb markiert.</p>"
            f"<ul>{rows}</ul>"
            f"{confirm_button} "
            "<button type='button' onclick='closeValidationModal()'>Zurück zur Prüfung</button>"
            "</div></div>"
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
    page = build_base_header("Zendure Service Neustart", cfg=cfg)
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
        for key, meta in CONFIG_SCHEMA.items():
            if meta.get("group") != group:
                continue
            if group == "Nachtmodus" and key in {"NIGHT_START_HOUR", "NIGHT_START_MINUTE", "NIGHT_END_HOUR", "NIGHT_END_MINUTE"}:
                continue
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
