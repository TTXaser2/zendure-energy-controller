#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Optional separate web UI for Zendure Energy Controller CSV analysis.

import argparse
import csv
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlencode

import uvicorn
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response

# Running this file directly from /opt/zendure-controller/tools should still
# allow imports from the project root and from tools/.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from replay_core import (  # noqa: E402
    CSV_SCHEMA,
    AnalysisLimits,
    analyze_files,
    summary_csv,
)
from replay_report import (  # noqa: E402
    actuator_table,
    charts_html,
    command_efficiency_table,
    cross_charge_table,
    data_quality_table,
    deadband_table,
    energy_table,
    events_table,
    fair_regulator_table,
    high_soc_table,
    mode_quality_table,
    oscillation_table,
    overview_table,
    overall_verdict_html,
    recommendations_table,
    summary_cards,
    text_report,
    tracking_table,
)

try:
    from version import APP_VERSION as REPLAY_VERSION  # noqa: E402
except Exception:  # pragma: no cover
    REPLAY_VERSION = "12.8.9"

SAFE_DEFAULTS = AnalysisLimits(max_files=2, max_total_bytes=6 * 1024 * 1024, max_rows=20_000)
EXTENDED_DEFAULTS = AnalysisLimits(max_files=3, max_total_bytes=10 * 1024 * 1024, max_rows=35_000)
CACHE_TTL_SECONDS = 15 * 60

_job_lock = threading.RLock()
_current_job: Optional[Dict[str, Any]] = None
_result_cache: Dict[str, Dict[str, Any]] = {}


def load_config() -> Dict[str, Any]:
    path = PROJECT_ROOT / "config.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _int_cfg(cfg: Dict[str, Any], key: str, default: int) -> int:
    try:
        return int(float(cfg.get(key, default)))
    except Exception:
        return int(default)


def log_dir_from_config(cfg: Dict[str, Any]) -> Path:
    raw = str(cfg.get("MEASUREMENT_LOG_DIR", cfg.get("CSV_LOG_DIR", "logs")) or "logs")
    path = Path(raw)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def list_csv_files(base: Path) -> List[Path]:
    if not base.exists():
        return []
    files = [p for p in base.glob("*.csv") if p.is_file()]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def resolve_csv_file(base: Path, name: str) -> Path:
    candidate = (base / name).resolve()
    if base not in candidate.parents and candidate != base:
        raise ValueError("Ungültiger Dateipfad.")
    if not candidate.exists() or not candidate.is_file():
        raise FileNotFoundError(candidate)
    return candidate


def resolve_csv_files(base: Path, names: Sequence[str]) -> List[Path]:
    resolved: List[Path] = []
    seen = set()
    for name in names:
        if not name:
            continue
        path = resolve_csv_file(base, name)
        key = str(path)
        if key not in seen:
            seen.add(key)
            resolved.append(path)
    if not resolved:
        raise ValueError("Keine CSV-Datei ausgewählt.")
    return resolved


def selected_files_from_query(files: Optional[List[str]], file: str, available: List[Path]) -> List[str]:
    selected = [f for f in (files or []) if f]
    if file and file not in selected:
        selected.append(file)
    # V12.8.5: keine automatische Analyse mehr. Für Bedienbarkeit wird nur eine
    # Vorauswahl angezeigt; analysiert wird erst per explizitem Button/POST.
    if not selected and available:
        selected = [available[0].name]
    return selected


def url_for_request_port(request: Request, port: int) -> str:
    scheme = request.url.scheme or "http"
    host = request.url.hostname or "127.0.0.1"
    if host in {"0.0.0.0", "::"}:
        host = "127.0.0.1"
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        return f"{scheme}://{host}"
    return f"{scheme}://{host}:{int(port)}"


def safe_limits(cfg: Optional[Dict[str, Any]] = None) -> AnalysisLimits:
    cfg = cfg or {}
    return AnalysisLimits(
        max_files=_int_cfg(cfg, "ANALYSIS_MAX_FILES", SAFE_DEFAULTS.max_files),
        max_total_bytes=_int_cfg(cfg, "ANALYSIS_MAX_TOTAL_BYTES", SAFE_DEFAULTS.max_total_bytes),
        max_rows=_int_cfg(cfg, "ANALYSIS_MAX_ROWS", SAFE_DEFAULTS.max_rows),
    )


def extended_limits(cfg: Optional[Dict[str, Any]] = None) -> AnalysisLimits:
    cfg = cfg or {}
    return AnalysisLimits(
        max_files=_int_cfg(cfg, "ANALYSIS_EXTENDED_MAX_FILES", EXTENDED_DEFAULTS.max_files),
        max_total_bytes=_int_cfg(cfg, "ANALYSIS_EXTENDED_MAX_TOTAL_BYTES", EXTENDED_DEFAULTS.max_total_bytes),
        max_rows=_int_cfg(cfg, "ANALYSIS_EXTENDED_MAX_ROWS", EXTENDED_DEFAULTS.max_rows),
    )


def _bytes_text(value: int) -> str:
    if value >= 1024 * 1024:
        return f"{value / 1024 / 1024:.1f} MiB".replace(".", ",")
    return f"{value / 1024:.1f} KiB".replace(".", ",")


def _csv_timestamp_label(row: Dict[str, Any]) -> str:
    return str(row.get("datetime_local") or (str(row.get("date", "")) + " " + str(row.get("timestamp", ""))).strip() or row.get("timestamp") or "-")


def _scan_csv_profile(paths: Sequence[Path], max_scan_rows: int = 100_000) -> Dict[str, Any]:
    rows = 0
    global_first_ts = "-"
    global_last_ts = "-"
    file_ranges: List[Tuple[str, str, str]] = []
    schema_errors: List[str] = []
    for path in paths:
        file_first_ts = "-"
        file_last_ts = "-"
        try:
            with open(path, "r", encoding="utf-8", newline="") as f:
                sample = f.read(4096)
                f.seek(0)
                first_line = sample.splitlines()[0] if sample.splitlines() else ""
                if ";" not in first_line:
                    schema_errors.append(f"{path.name}: kein Semikolon-CSV")
                    continue
                reader = csv.DictReader(f, delimiter=";")
                if not reader.fieldnames or "schema" not in reader.fieldnames:
                    schema_errors.append(f"{path.name}: Spalte 'schema' fehlt")
                    continue
                for row in reader:
                    if not any((v or "").strip() for v in row.values()):
                        continue
                    if rows < max_scan_rows:
                        schema = (row.get("schema") or "").strip()
                        if schema != CSV_SCHEMA:
                            schema_errors.append(f"{path.name}: Schema {schema or 'leer'} ist nicht {CSV_SCHEMA}")
                            break
                        label = _csv_timestamp_label(row)
                        if label and label != "-":
                            if file_first_ts == "-" or label < file_first_ts:
                                file_first_ts = label
                            if file_last_ts == "-" or label > file_last_ts:
                                file_last_ts = label
                            if global_first_ts == "-" or label < global_first_ts:
                                global_first_ts = label
                            if global_last_ts == "-" or label > global_last_ts:
                                global_last_ts = label
                    rows += 1
        except Exception as exc:
            schema_errors.append(f"{path.name}: {exc}")
        if file_first_ts != "-" or file_last_ts != "-":
            file_ranges.append((path.name, file_first_ts, file_last_ts))
    inverted = global_first_ts != "-" and global_last_ts != "-" and global_first_ts > global_last_ts
    return {
        "estimated_rows": rows,
        "period_start": global_first_ts,
        "period_end": global_last_ts,
        "file_ranges": file_ranges,
        "period_inverted": inverted,
        "schema_errors": schema_errors[:5],
    }



def _limits_to_dict(limits: AnalysisLimits) -> Dict[str, int]:
    return {
        "max_files": int(limits.max_files),
        "max_total_bytes": int(limits.max_total_bytes),
        "max_rows": int(limits.max_rows),
    }

def _meminfo_available_mb() -> Optional[int]:
    try:
        values: Dict[str, int] = {}
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if ":" not in line:
                continue
            key, rest = line.split(":", 1)
            parts = rest.strip().split()
            if parts:
                values[key] = int(parts[0]) // 1024
        return values.get("MemAvailable")
    except Exception:
        return None


def _worker_memory_limit_mb(cfg: Dict[str, Any], extended: bool = False) -> int:
    key = "ANALYSIS_EXTENDED_WORKER_MEMORY_LIMIT_MB" if extended else "ANALYSIS_WORKER_MEMORY_LIMIT_MB"
    default = 380 if extended else 300
    return max(128, _int_cfg(cfg, key, default))


def _worker_timeout_seconds(cfg: Dict[str, Any], extended: bool = False) -> int:
    key = "ANALYSIS_EXTENDED_WORKER_TIMEOUT_SECONDS" if extended else "ANALYSIS_WORKER_TIMEOUT_SECONDS"
    default = 300 if extended else 180
    return max(30, _int_cfg(cfg, key, default))


def selection_profile(paths: Sequence[Path], cfg: Dict[str, Any]) -> Dict[str, Any]:
    total_size = sum(p.stat().st_size for p in paths)
    scan = _scan_csv_profile(paths)
    rows = int(scan.get("estimated_rows") or 0)
    safe = safe_limits(cfg)
    ext = extended_limits(cfg)
    mem_available_mb = _meminfo_available_mb()
    safe_memory_mb = _worker_memory_limit_mb(cfg, extended=False)
    ext_memory_mb = _worker_memory_limit_mb(cfg, extended=True)
    schema_errors = scan.get("schema_errors") or []
    unsafe_memory = mem_available_mb is not None and mem_available_mb < max(180, int(safe_memory_mb * 0.75))
    if schema_errors:
        risk = "rejected"
        text = "Nicht analysierbar: Die Auswahl enthält keine durchgängig gültigen ZEC-MEASUREMENT-V3-Dateien."
        needs_confirm = False
        rejected = True
    elif unsafe_memory:
        risk = "rejected"
        text = "Nicht empfohlen: Auf dem Raspberry Pi ist aktuell zu wenig freier RAM für eine sichere lokale Analyse verfügbar."
        needs_confirm = False
        rejected = True
    elif len(paths) <= safe.max_files and total_size <= safe.max_total_bytes and rows <= safe.max_rows:
        risk = "pi-safe"
        text = "Pi-Safe: kleine V3-Auswahl; Analyse läuft zusätzlich in einem isolierten Worker mit Timeout und Speicherlimit."
        needs_confirm = False
        rejected = False
    elif len(paths) <= ext.max_files and total_size <= ext.max_total_bytes and rows <= ext.max_rows:
        risk = "extended"
        text = "Größere V3-Analyse: nur bewusst starten. Sie läuft isoliert, kann aber länger dauern und wird bei Zeit-/Speicherlimit abgebrochen."
        needs_confirm = True
        rejected = False
    else:
        risk = "rejected"
        text = "Nicht empfohlen: lokale Analyse auf dem Raspberry Pi wird fail-closed abgelehnt. Bitte kleinere V3-Auswahl verwenden oder offline auf PC analysieren."
        needs_confirm = False
        rejected = True
    return {
        "file_count": len(paths),
        "total_size_bytes": total_size,
        "total_size_text": _bytes_text(total_size),
        "estimated_rows": rows,
        "period_start": scan.get("period_start", "-"),
        "period_end": scan.get("period_end", "-"),
        "file_ranges": scan.get("file_ranges") or [],
        "period_inverted": bool(scan.get("period_inverted")),
        "risk": risk,
        "risk_text": text,
        "needs_confirmation": needs_confirm,
        "rejected": rejected,
        "schema_errors": schema_errors,
        "safe_limits": _limits_to_dict(safe),
        "extended_limits": _limits_to_dict(ext),
        "mem_available_mb": mem_available_mb,
        "worker_memory_limit_mb": ext_memory_mb if risk == "extended" else safe_memory_mb,
        "worker_timeout_seconds": _worker_timeout_seconds(cfg, extended=(risk == "extended")),
    }


def _analysis_key(paths: Sequence[Path], extended: bool) -> str:
    parts = []
    for path in paths:
        st = path.stat()
        parts.append(f"{path.name}:{st.st_size}:{int(st.st_mtime)}")
    return json.dumps({"files": parts, "extended": bool(extended), "version": REPLAY_VERSION}, sort_keys=True)


def _cache_put(key: str, result: Dict[str, Any]) -> None:
    _result_cache[key] = {"time": time.time(), "result": result}
    # Bounded cache: the analysis is local and single-user; two entries are enough.
    for old_key, item in list(_result_cache.items()):
        if time.time() - float(item.get("time", 0)) > CACHE_TTL_SECONDS or len(_result_cache) > 2:
            _result_cache.pop(old_key, None)


def _cache_get(key: str) -> Optional[Dict[str, Any]]:
    item = _result_cache.get(key)
    if not item:
        return None
    if time.time() - float(item.get("time", 0)) > CACHE_TTL_SECONDS:
        _result_cache.pop(key, None)
        return None
    return item.get("result")


def _make_snapshot(paths: Sequence[Path]) -> Tuple[Path, List[Path]]:
    tmpdir = Path(tempfile.mkdtemp(prefix="zec-analysis-"))
    copied: List[Path] = []
    for index, src in enumerate(paths, start=1):
        safe_name = f"{index:02d}_{src.name}"
        dest = tmpdir / safe_name
        shutil.copy2(src, dest)
        copied.append(dest)
    return tmpdir, copied


def _read_worker_rss_mb(pid: int) -> Optional[int]:
    try:
        for line in Path(f"/proc/{pid}/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                parts = line.split()
                if len(parts) >= 2:
                    return int(parts[1]) // 1024
    except Exception:
        return None
    return None


def _terminate_worker(proc: subprocess.Popen, grace_seconds: float = 3.0) -> None:
    if proc.poll() is not None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=grace_seconds)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
        try:
            proc.wait(timeout=grace_seconds)
        except Exception:
            pass


def _run_worker(snapshot_paths: Sequence[Path], cfg: Dict[str, Any], extended: bool, job: Dict[str, Any], cancel_event: threading.Event) -> Dict[str, Any]:
    limits = extended_limits(cfg) if extended else safe_limits(cfg)
    memory_mb = _worker_memory_limit_mb(cfg, extended=extended)
    timeout_s = _worker_timeout_seconds(cfg, extended=extended)
    worker_script = TOOLS_DIR / "replay_worker.py"
    with tempfile.TemporaryDirectory(prefix="zec-worker-") as tmp:
        tmp_path = Path(tmp)
        request_path = tmp_path / "request.json"
        output_path = tmp_path / "result.json"
        request_path.write_text(json.dumps({
            "paths": [str(p) for p in snapshot_paths],
            "cfg": cfg,
            "limits": _limits_to_dict(limits),
            "memory_mb": memory_mb,
        }, ensure_ascii=False), encoding="utf-8")
        proc = subprocess.Popen(
            [sys.executable, str(worker_script), "--request", str(request_path), "--output", str(output_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        job["worker_pid"] = proc.pid
        start = time.time()
        last_phase = "Analyse-Worker läuft"
        while True:
            if cancel_event.is_set():
                _terminate_worker(proc)
                raise RuntimeError("Analyse abgebrochen.")
            rc = proc.poll()
            if rc is not None:
                break
            elapsed = time.time() - start
            if elapsed > timeout_s:
                _terminate_worker(proc)
                raise RuntimeError(f"Analyse wegen Zeitlimit abgebrochen ({timeout_s} s). Bitte kleinere Auswahl verwenden oder offline analysieren.")
            rss = _read_worker_rss_mb(proc.pid)
            if rss is not None and rss > memory_mb:
                _terminate_worker(proc)
                raise RuntimeError(f"Analyse wegen Speicherlimit abgebrochen ({rss} MB > {memory_mb} MB). Bitte kleinere Auswahl verwenden oder offline analysieren.")
            phase = f"Analyse-Worker läuft ({int(elapsed)} s" + (f", RSS {rss} MB" if rss is not None else "") + ")"
            if phase != last_phase:
                job.update({"phase": phase, "percent": min(80, 40 + int(elapsed / max(1, timeout_s) * 40))})
                last_phase = phase
            time.sleep(0.5)
        stdout, stderr = proc.communicate(timeout=5)
        if proc.returncode != 0:
            detail = (stderr or stdout or f"Exit-Code {proc.returncode}").strip()
            raise RuntimeError("Analyse-Worker fehlgeschlagen: " + detail[-1000:])
        if not output_path.exists():
            raise RuntimeError("Analyse-Worker hat kein Ergebnis geliefert.")
        return json.loads(output_path.read_text(encoding="utf-8"))


def analyze_snapshot(paths: Sequence[Path], cfg: Dict[str, Any], extended: bool, cancel_event: threading.Event, job: Dict[str, Any]) -> Dict[str, Any]:
    tmpdir: Optional[Path] = None
    try:
        job.update({"phase": "Snapshot wird erstellt", "percent": 20})
        tmpdir, snapshot_paths = _make_snapshot(paths)
        if cancel_event.is_set():
            raise RuntimeError("Analyse abgebrochen.")
        job.update({"phase": "Isolierter Analyse-Worker wird gestartet", "percent": 35})
        result = _run_worker(snapshot_paths, cfg, extended, job, cancel_event)
        result["filenames"] = [p.name for p in paths]
        result["paths"] = [str(p) for p in paths]
        result["total_size_bytes"] = sum(p.stat().st_size for p in paths)
        job.update({"phase": "Report wird erzeugt", "percent": 85})
        return result
    finally:
        if tmpdir and tmpdir.exists():
            shutil.rmtree(tmpdir, ignore_errors=True)
        job.pop("worker_pid", None)


def render_result_html(result: Dict[str, Any], job_id: str) -> str:
    download_job = html.escape(job_id, quote=True)
    return f"""
    <div class="toc" id="analysis-nav">
        <b>Navigation:</b>
        <a href="#kurzfazit">Kurzfazit</a><a href="#empfehlungen">Empfehlungen</a><a href="#diagramme">Diagramme</a>
        <a href="#datenqualitaet">Datenqualität</a><a href="#regler">Reglerqualität</a><a href="#stellreserve">Stellreserve</a>
        <a href="#tracking">Soll/Ist</a><a href="#deadband">Deadband</a><a href="#mqtt">MQTT</a>
        <a href="#cross">Cross-Charge</a><a href="#matrix">Matrix</a><a href="#ereignisse">Ereignisse</a>
    </div>
    <h2 id="kurzfazit">Kurzfazit</h2>
    <p class="section-intro">Dieser Block verdichtet den analysierten Zeitraum zu einem Gesamturteil. Er zeigt, ob akuter Handlungsdruck besteht oder ob Abweichungen überwiegend durch Randbedingungen wie SOC-, Leistungs- oder Datenlimits erklärbar sind.</p>
    {overall_verdict_html(result)}
    <div class="cards">{summary_cards(result)}</div>
    <h2 id="empfehlungen">Handlungsempfehlungen</h2>
    <p class="section-intro">Hier stehen konkrete, priorisierte Hinweise. Sie sind Diagnosehinweise und sollten nur mit ausreichender Datenqualität und passenden Logzeiträumen in Parameteränderungen übersetzt werden.</p>
    <table>{recommendations_table(result)}</table>
    <p class="notice">Die Analyse liefert Hinweise auf wahrscheinliche Ursachen. Parameteränderungen sollten immer mit ausreichender Datenqualität und mehreren passenden Logzeiträumen gegengeprüft werden.</p>
    <h2 id="diagramme">Diagramme</h2>
    <p class="section-intro">Die Diagramme verdichten den analysierten Zeitraum. Sie zeigen je nach Diagramm Prozentanteile, Anzahl von Ereignissen oder aufsummierte Zeitdauer. Die Einheit steht direkt am jeweiligen Wert; Info-Texte erläutern Begriff, Basis und Interpretation.</p>
    {charts_html(result)}
    <h2 id="ueberblick">Überblick</h2><p class="section-intro">Basisdaten der Analyse: Dateien, Zeitraum, Messpunktanzahl und zeitliche Qualität der Daten.</p><table>{overview_table(result)}</table>
    <h2 id="datenqualitaet">Datenqualität</h2><p class="section-intro">Bewertet, ob die Datenbasis für belastbare Schlüsse ausreicht. Fehlende Netz-, SOC- oder Istwerte können die Aussagekraft einzelner Blöcke deutlich reduzieren.</p><table>{data_quality_table(result)}</table>
    <h2 id="energie">Energiefluss der ausgewählten Dateien</h2><p class="section-intro">Integrierte Energieflüsse im ausgewählten Zeitraum. Vorzeichen: Netz + Bezug/- Einspeisung, Speicher + Laden/- Entladen.</p><table>{energy_table(result)}</table>
    <h2 id="regler">Faire Reglerqualität</h2><p class="section-intro">Bewertet nur den Anteil, den der Regler tatsächlich beeinflussen konnte. Volle Batterie, Leistungsgrenzen und Safe-State werden getrennt betrachtet.</p><table>{fair_regulator_table(result)}</table>
    <h2 id="stellreserve">Stellreserve / Sättigung</h2><p class="section-intro">Zeigt, wie oft Zendure am Lade- oder Entladelimit war. Hohe Sättigung bedeutet: Mehr Regleraggressivität hilft wenig; eher Kapazität/Leistungsgrenzen prüfen.</p><table>{actuator_table(result)}</table>
    <h2 id="tracking">Zendure Soll-/Ist-Folge</h2><p class="section-intro">Vergleicht angeforderte Zendure-Sollleistung mit tatsächlich erreichter Istleistung. Große Abweichungen können durch Zendure-Firmware, SOC, Temperatur, Telemetriealter oder Limits entstehen.</p><table>{tracking_table(result)}</table>
    <h2 id="deadband">Deadband-Erfolg</h2><p class="section-intro">Bewertet, ob die Totzone sinnvoll Ruhe erzeugt oder ob der Regler trotz vorhandener Reserve zu oft außerhalb des Zielbands bleibt.</p><table>{deadband_table(result)}</table>
    <h2 id="mqtt">MQTT-Kommandowirkung</h2><p class="section-intro">Bewertet grob, ob gesendete MQTT-Kommandos anschließend eine erkennbare Verringerung der Netzabweichung bewirken. Nicht bewertbar bedeutet meist: Safe-State, fehlende Folgedaten oder überlagerte Last-/PV-Sprünge.</p><table>{command_efficiency_table(result)}</table>
    <h2 id="oszillation">Oszillation / Richtungswechsel</h2><p class="section-intro">Sucht nach unruhiger Regelung: häufige Vorzeichenwechsel, schnelle Gegenbefehle, große Sollwertsprünge und Moduswechsel.</p><table>{oscillation_table(result)}</table>
    <h2 id="cross">Cross-Charge-Analyse</h2><p class="section-intro">Bewertet, ob die Zusatzbatterie entlädt, während Zendure gleichzeitig lädt. Kritische Überschneidungen deuten auf unerwünschtes Umladen zwischen Speichern hin.</p><table>{cross_charge_table(result)}</table>
    <h2 id="highsoc">Nachtentladung und High-SOC</h2><p class="section-intro">Zeigt Zeitanteile bei SOC-Grenzen und eine leichte High-SOC-Ladeannahme-Diagnose. Schwerpunkt dieser Version bleibt die Regler- und Cross-Charge-Bewertung.</p><table>{high_soc_table(result)}</table>
    <h2 id="matrix">Betriebszustandsmatrix</h2><p class="section-intro">Verdichtet die Analyse nach abgeleiteten Betriebszuständen. So sieht man, ob Abweichungen eher in AUTO, Nachtentladung, Safe-State oder Limit-Situationen auftreten.</p><table>{mode_quality_table(result)}</table>
    <h2 id="ereignisse">Ereignisprotokoll</h2><p class="section-intro">Chronologische Auswahl erkannter Auffälligkeiten und Zustandswechsel. Die Liste ist begrenzt, damit große Analysen die Oberfläche nicht überladen.</p><table>{events_table(result)}</table>
    <p class="downloads">
        <a href="/report.txt?job_id={download_job}">Text-Report</a>
        <a href="/report.json?job_id={download_job}">JSON-Report</a>
        <a href="/summary.csv?job_id={download_job}">CSV-Summary</a>
        <a href="#top">nach oben</a>
    </p>
    """


def _current_job_snapshot() -> Optional[Dict[str, Any]]:
    with _job_lock:
        if not _current_job:
            return None
        job = dict(_current_job)
        job.pop("cancel_event", None)
        return job


def _get_result_from_job(job_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    with _job_lock:
        if _current_job and _current_job.get("id") == job_id:
            return _current_job.get("result"), _current_job.get("cache_key")
        for item in _result_cache.values():
            result = item.get("result")
            if result and result.get("_job_id") == job_id:
                return result, result.get("_cache_key")
    return None, None


def build_app() -> FastAPI:
    app = FastAPI(title="Zendure Replay Analyse", version=REPLAY_VERSION)

    @app.get("/selection-profile")
    def selection_profile_endpoint(files: Optional[List[str]] = Query(default=None), file: str = Query(default="")):
        cfg = load_config()
        base = log_dir_from_config(cfg)
        selected = [f for f in (files or []) if f]
        if file and file not in selected:
            selected.append(file)
        try:
            paths = resolve_csv_files(base, selected)
            return {"profile": selection_profile(paths, cfg)}
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request, files: Optional[List[str]] = Query(default=None), file: str = Query(default="")):
        cfg = load_config()
        base = log_dir_from_config(cfg)
        available = list_csv_files(base)
        selected = selected_files_from_query(files, file, available)
        controller_port = int(cfg.get("WEB_PORT", 8080) or 8080)
        replay_port = int(cfg.get("REPLAY_WEB_PORT", 8090) or 8090)
        controller_url = url_for_request_port(request, controller_port)
        replay_url = url_for_request_port(request, replay_port)
        dark = bool(cfg.get("UI_DARK_MODE", False))
        ui_mode = str(cfg.get("UI_MODE", "standard") or "standard")
        options = "".join(
            f'<option value="{html.escape(p.name, quote=True)}" data-size="{p.stat().st_size}" {"selected" if p.name in selected else ""}>{html.escape(p.name)} ({_bytes_text(p.stat().st_size)})</option>'
            for p in available
        )
        profile_html = ""
        try:
            paths = resolve_csv_files(base, selected) if selected else []
            if paths:
                profile = selection_profile(paths, cfg)
                badge_cls = {"pi-safe": "ok", "extended": "warn", "rejected": "bad"}.get(profile["risk"], "neutral")
                errors = "".join(f"<li>{html.escape(e)}</li>" for e in profile.get("schema_errors") or [])
                profile_html = f"""
                <div class="analysis-profile {badge_cls}">
                    <div class="profile-title">Informationen zu den ausgewählten Dateien</div>
                    <div class="profile-explain">Diese Box zeigt Dateianzahl, Gesamtgröße, abgedeckten Zeitraum, geschätzte Messpunkte und das Auslastungsrisiko des Raspberry Pi für diese Analyseauswahl.</div>
                    <b>Auswahl:</b> {profile['file_count']} Datei(en), {profile['total_size_text']}, ca. {profile['estimated_rows']} Messpunkte<br>
                    <b>Zeitraum:</b> {html.escape(str(profile['period_start']))} bis {html.escape(str(profile['period_end']))}<br>
                    <b>Risiko:</b> {html.escape(profile['risk_text'])}
                    {('<ul>' + errors + '</ul>') if errors else ''}
                </div>
                """
        except Exception as exc:
            profile_html = f"<div class='error'>Auswahl konnte nicht geprüft werden: {html.escape(str(exc))}</div>"

        initial_job = _current_job_snapshot()
        initial_running = bool(initial_job and initial_job.get("status") == "running")
        initial_status = html.escape(str(initial_job.get("phase"))) if initial_running and initial_job else "Bereit. Analyse startet erst nach Klick auf „Analyse starten“."
        dark_css = """
        body{background:#0f172a;color:#e5e7eb}.section{background:#111827;box-shadow:0 2px 10px rgba(0,0,0,.55)}
        table th{background:#263244;color:#e5e7eb} th,td{border-color:#475569}.toc{background:#111827;border-color:#334155}
        .card{background:#1f2937;border-color:#374151}.notice{background:#10233d;border-color:#2563eb;color:#dbeafe}.analysis-profile{background:#1f2937;color:#e5e7eb}
        .analysis-profile.ok{background:#064e3b;border-color:#22c55e;color:#dcfce7}.analysis-profile.warn{background:#713f12;border-color:#facc15;color:#fef9c3}.analysis-profile.bad{background:#7f1d1d;border-color:#ef4444;color:#fee2e2}
        select{background:#0b1220;color:#e5e7eb;border:1px solid #64748b}button{background:#243244;color:#e5e7eb;border:1px solid #64748b}
        button:hover:not(:disabled){background:#334155}.statusline{background:#10233d;border-color:#2563eb;color:#dbeafe}.statusline.error{background:#7f1d1d;border-color:#ef4444;color:#fee2e2}.statusline.done{background:#064e3b;border-color:#22c55e;color:#dcfce7}
        .progressbox{background:#334155}.progressbar{background:#60a5fa}a{color:#7dd3fc}.section-intro{color:#cbd5e1}
        .term-info div{color:#cbd5e1}.ok{background:#065f46;color:#dcfce7}.warn{background:#facc15;color:#1f2937}.bad{background:#991b1b;color:#fee2e2}.neutral{background:#475569;color:#e5e7eb}
        .badge.ok{background:#22c55e;color:#052e16}.badge.warn{background:#facc15;color:#1f2937}.badge.bad{background:#ef4444;color:#450a0a}.badge.neutral{background:#64748b;color:#f8fafc}
        .verdict{background:#1f2937;border-color:#475569;color:#e5e7eb}.verdict h3,.verdict p{color:#e5e7eb}
        .profile-title{color:#e5e7eb}.profile-explain{color:#cbd5e1}.chart-info div{color:#cbd5e1}.chart-info summary{color:#7dd3fc}
        """ if dark else """
        """
        return f"""
        <html><head><title>Zendure Replay Analyse</title><meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
        body{{font-family:Arial,sans-serif;margin:20px;background:#f5f7fb;color:#111827}}
        a{{color:#1565c0}} .section{{background:white;padding:18px;border-radius:12px;margin-bottom:18px;box-shadow:0 2px 8px #ddd}}
        table{{border-collapse:collapse;width:100%;margin-bottom:16px}} th,td{{border:1px solid #ddd;padding:8px;text-align:left;vertical-align:top}} th{{background:#f1f5f9;width:34%}}
        .error{{background:#fee2e2;border:1px solid #f87171;padding:12px;border-radius:8px}}
        .notice{{background:#eef6ff;border:1px solid #bfdbfe;padding:10px;border-radius:8px}}
        .small{{font-size:0.92em;color:#64748b}} select{{min-width:320px;max-width:100%}} button{{padding:7px 12px;border-radius:6px;cursor:pointer}}
        button:disabled{{opacity:.55;cursor:not-allowed}} .topnav{{display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin-bottom:10px}} .downloads a{{display:inline-block;margin-right:14px}}
        .badge{{display:inline-block;padding:3px 8px;border-radius:999px;font-weight:bold}} .ok{{background:#dcfce7;color:#14532d}} .warn{{background:#fde68a;color:#78350f}} .bad{{background:#fee2e2;color:#7f1d1d}} .neutral{{background:#e5e7eb;color:#374151}}
        .badge.ok{{background:#22c55e;color:#052e16}}.badge.warn{{background:#facc15;color:#1f2937}}.badge.bad{{background:#ef4444;color:#450a0a}}.badge.neutral{{background:#94a3b8;color:#0f172a}}
        .term-info{{display:block;margin:3px 0 0 0}}.term-info summary{{display:inline-block;color:#1565c0;cursor:pointer;font-weight:normal}}.term-info div{{margin-top:6px;color:#374151;font-weight:normal;line-height:1.35}} .label-main{{font-weight:bold}}
        .toc{{position:sticky;top:0;background:#fff;border:1px solid #dbe4ef;padding:10px;border-radius:10px;margin-bottom:14px;z-index:5}}
        .toc a{{display:inline-block;margin:3px 8px 3px 0}} .cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:10px 0 16px}}
        .card{{border:1px solid #dbe4ef;border-radius:10px;padding:12px;background:#f8fafc;display:flex;justify-content:space-between;gap:8px;align-items:center}}
        .chartgrid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:18px}} .chart-card{{min-width:0}} .barrow{{display:grid;grid-template-columns:minmax(120px,38%) minmax(180px,1fr);gap:6px 10px;align-items:center;margin:12px 0 16px 0}}
        .barlabel{{min-width:0;overflow-wrap:anywhere}} .barvalue{{grid-column:2;font-size:.98em;line-height:1.25}} .barrow .term-info{{grid-column:1 / -1;margin:0 0 2px 0;max-width:none}} .barrow .term-info div{{max-width:none;width:100%;box-sizing:border-box;margin-top:6px;line-height:1.35}}
        .barbox{{height:14px;width:100%;min-width:0;background:rgba(148,163,184,.28);border-radius:999px;overflow:hidden;margin-top:2px}} .barbox.empty{{background:rgba(148,163,184,.10);border:1px solid rgba(148,163,184,.35);box-sizing:border-box}} .bar{{height:14px;background:#93c5fd;border-radius:999px}} .bar.zero{{background:transparent}} .chart-info{{margin:0 0 8px 0}} .chart-info summary{{color:#1565c0;cursor:pointer}} .chart-info div{{margin-top:6px;color:#475569;line-height:1.35}}
        @media (max-width: 620px){{.chartgrid{{grid-template-columns:1fr}}.barrow{{grid-template-columns:1fr;gap:4px;margin:14px 0 18px 0}}.barlabel{{font-weight:bold;overflow-wrap:anywhere}}.barvalue{{grid-column:1}}.barbox{{width:100%;min-width:0}}.barrow .term-info{{grid-column:1;margin:0 0 8px 0}}}}
        h2{{scroll-margin-top:70px;border-bottom:1px solid #e5e7eb;padding-bottom:4px}} .section-intro{{margin-top:-4px;color:#475569;line-height:1.45}}
        .analysis-profile{{padding:10px;border-radius:8px;margin:12px 0;border:1px solid #cbd5e1}} .analysis-profile.ok{{border-color:#22c55e}} .analysis-profile.warn{{border-color:#f59e0b}} .analysis-profile.bad{{border-color:#ef4444}}
        .profile-title{{font-weight:bold;font-size:1.05em;margin-bottom:4px}}.profile-explain{{font-size:.92em;color:#475569;margin-bottom:8px;line-height:1.35}}
        .statusline{{padding:10px;border-radius:8px;margin:12px 0;background:#eef6ff;border:1px solid #bfdbfe;color:#1e3a8a;min-height:38px}} .statusline.error{{background:#fee2e2;border-color:#f87171;color:#7f1d1d}} .statusline.done{{background:#dcfce7;border-color:#22c55e;color:#064e3b}} .progressbox{{height:14px;background:#e5e7eb;border-radius:999px;overflow:hidden;margin-top:8px}} .progressbar{{height:14px;background:#93c5fd;width:0%;transition:width .25s ease}}
        .verdict{{display:block;border:1px solid #dbe4ef;border-radius:10px;padding:14px;background:#f8fafc;margin:8px 0 14px}} .verdict h3{{margin:0 0 6px}}
        {dark_css}
        </style></head><body id="top" class="mode-{html.escape(ui_mode, quote=True)}">
        <div class="topnav"><a href="{html.escape(controller_url, quote=True)}">← Zurück zum Zendure Controller</a><span class="small">Analyse-Dienst: {html.escape(replay_url)}</span></div>
        <div class="section"><h1>Zendure Replay Analyse V{REPLAY_VERSION}</h1>
        <p>Separater Analyse-Dienst für CSV-Dateien im Schema <code>{CSV_SCHEMA}</code>. Der Live-Controller wird hiervon nicht importiert oder beeinflusst.</p>
        <form id="analysisForm">
            <label>CSV-Dateien:</label><br>
            <select id="filesSelect" name="files" multiple size="8">{options}</select><br><br>
            <div id="profileBox">{profile_html}</div>
            <button id="startBtn" type="button" {'disabled' if initial_running else ''}>Analyse starten</button>
            <button id="cancelBtn" type="button" style="display:{'inline-block' if initial_running else 'none'}">Analyse abbrechen</button>
        </form>
        <div id="analysisStatus" class="statusline"><span id="statusText">{initial_status}</span><div class="progressbox"><div id="progressBar" class="progressbar" style="width:{int(initial_job.get('percent',0)) if initial_job else 0}%"></div></div></div>
        <noscript><div class="error">Für Start-/Fortschrittsanzeige der Analyse ist JavaScript erforderlich.</div></noscript>
        </div>
        <div class="section" id="result"><h2>Analyseergebnis</h2><p class="section-intro">Noch kein Ergebnis in dieser Sitzung. Wähle Dateien aus und starte die Analyse explizit.</p></div>
        <script>
        let currentJobId = {json.dumps(initial_job.get('id') if initial_job else None)};
        let pollTimer = null;
        let analysisBusy = !!currentJobId;
        let profileUpdating = false;
        let profileReady = false;
        let profileRejected = true;
        let profileRequestSeq = 0;
        const START_LABEL = 'Analyse starten';
        function byId(id){{return document.getElementById(id);}}
        function refreshStartButton(){{
          const start=byId('startBtn');
          if(!start) return;
          if(analysisBusy){{start.disabled=true; start.textContent=START_LABEL; return;}}
          if(profileUpdating){{start.disabled=true; start.textContent='Aktualisiere Dateiauswahl…'; return;}}
          if(!profileReady){{start.disabled=true; start.textContent='Dateiauswahl prüfen'; return;}}
          if(profileRejected){{start.disabled=true; start.textContent='Analyse nicht möglich'; return;}}
          start.disabled=false; start.textContent=START_LABEL;
        }}
        function setBusy(busy){{
          analysisBusy = !!busy;
          const cancel=byId('cancelBtn');
          if(cancel) cancel.style.display=busy?'inline-block':'none';
          refreshStartButton();
        }}
        function setStatus(text, percent, kind='info'){{
          const box=byId('analysisStatus'); const bar=byId('progressBar'); const textNode=byId('statusText');
          if(textNode) textNode.textContent=text||'';
          if(box){{box.classList.remove('error','done'); if(kind==='error') box.classList.add('error'); if(kind==='done') box.classList.add('done');}}
          if(bar) bar.style.width=Math.max(0, Math.min(100, Number(percent)||0))+'%';
        }}
        function selectedFiles(){{
          const sel=byId('filesSelect'); if(!sel) return [];
          return Array.from(sel.selectedOptions).map(o=>o.value).filter(Boolean);
        }}
        function escapeHtml(value){{return String(value).replace(/[&<>'"]/g, ch => ({{'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}}[ch]));}}
        function renderProfile(profile){{
          const box=byId('profileBox'); if(!box) return;
          if(!profile){{
            profileReady=false; profileRejected=true;
            box.innerHTML='<div class="analysis-profile bad"><div class="profile-title">Informationen zu den ausgewählten Dateien</div><div class="profile-explain">Bitte mindestens eine CSV-Datei auswählen.</div><b>Auswahl:</b> Keine gültige Auswahl.</div>';
            refreshStartButton(); return;
          }}
          const cls = profile.risk==='pi-safe' ? 'ok' : (profile.risk==='extended' ? 'warn' : 'bad');
          const errors = (profile.schema_errors||[]).map(e=>'<li>'+escapeHtml(e)+'</li>').join('');
          box.innerHTML = '<div class="analysis-profile '+cls+'">'
            + '<div class="profile-title">Informationen zu den ausgewählten Dateien</div>'
            + '<div class="profile-explain">Diese Box zeigt Dateianzahl, Gesamtgröße, abgedeckten Zeitraum, geschätzte Messpunkte und das Auslastungsrisiko des Raspberry Pi für diese Analyseauswahl.</div>'
            + '<b>Auswahl:</b> '+profile.file_count+' Datei(en), '+profile.total_size_text+', ca. '+profile.estimated_rows+' Messpunkte<br>'
            + '<b>Zeitraum:</b> '+escapeHtml(profile.period_start||'-')+' bis '+escapeHtml(profile.period_end||'-')+'<br>'
            + '<b>Risiko:</b> '+escapeHtml(profile.risk_text||'-')
            + (errors ? '<ul>'+errors+'</ul>' : '') + '</div>';
          profileReady=true; profileRejected=!!profile.rejected || profile.file_count < 1; refreshStartButton();
        }}
        async function updateProfile(){{
          const seq=++profileRequestSeq;
          const files=selectedFiles();
          profileUpdating=true; profileReady=false; profileRejected=true; refreshStartButton();
          if(files.length<1){{profileUpdating=false; renderProfile(null); return;}}
          const box=byId('profileBox');
          if(box) box.innerHTML='<div class="analysis-profile"><div class="profile-title">Informationen zu den ausgewählten Dateien</div><div class="profile-explain">Dateiauswahl wird aktualisiert. Der Analyse-Start wird erst freigegeben, wenn diese Prüfung abgeschlossen ist.</div><b>Status:</b> Auswahl wird geprüft…</div>';
          const params=new URLSearchParams(); files.forEach(f=>params.append('files', f));
          try{{
            const res=await fetch('/selection-profile?'+params.toString(), {{cache:'no-store'}});
            const js=await res.json();
            if(seq !== profileRequestSeq) return;
            if(!res.ok){{throw new Error(js.error||'Auswahl konnte nicht geprüft werden.');}}
            profileUpdating=false;
            renderProfile(js.profile);
          }}catch(e){{
            if(seq !== profileRequestSeq) return;
            profileUpdating=false; profileReady=false; profileRejected=true;
            byId('profileBox').innerHTML='<div class="error">Auswahl konnte nicht geprüft werden: '+escapeHtml(e.message||e)+'</div>';
            refreshStartButton();
          }}
        }}
        async function startAnalysis(confirmExtended=false){{
          if(profileUpdating || !profileReady || profileRejected){{
            setStatus('Bitte warten: Die Informationen zu den ausgewählten Dateien werden noch aktualisiert oder die Auswahl ist nicht gültig.', 0, 'info');
            refreshStartButton();
            return;
          }}
          const form=byId('analysisForm'); const data=new FormData(form);
          if(confirmExtended) data.append('extended_confirm','1');
          setBusy(true); setStatus('Analyse wird angefordert...', 5, 'info');
          byId('result').innerHTML='<h2>Analyseergebnis</h2><p class="section-intro">Analyse wurde gestartet. Ergebnis erscheint nach Abschluss automatisch.</p>';
          try{{
            const res=await fetch('/start-analysis',{{method:'POST',body:data}});
            const js=await res.json().catch(()=>({{error:'Ungültige Serverantwort'}}));
            if(js.profile) renderProfile(js.profile);
            if(js.requires_confirmation){{
              setBusy(false); setStatus(js.message||'Große Analyse erfordert Bestätigung.',0,'info');
              if(confirm((js.message||'Große Analyse starten?')+'\\n\\nWeiter?')) startAnalysis(true);
              return;
            }}
            if(!res.ok){{
              setBusy(false); setStatus(js.error||'Analyse konnte nicht gestartet werden.',0,'error');
              byId('result').innerHTML='<h2>Analyseergebnis</h2><div class="error">'+escapeHtml(js.error||'Analyse konnte nicht gestartet werden.')+'</div>';
              return;
            }}
            currentJobId=js.job_id; setStatus(js.phase||'Analyse gestartet', js.percent||10, 'info');
            if(js.status==='done'){{setBusy(false); setStatus(js.phase||'Analyse abgeschlossen',100,'done'); loadResult(); return;}}
            pollStatus();
          }}catch(e){{
            setBusy(false); setStatus('Fehler beim Start: '+(e.message||e),0,'error');
            byId('result').innerHTML='<h2>Analyseergebnis</h2><div class="error">Fehler beim Start: '+escapeHtml(e.message||e)+'</div>';
          }}
        }}
        async function pollStatus(){{
          if(!currentJobId) return;
          try{{
            const res=await fetch('/analysis-status?job_id='+encodeURIComponent(currentJobId), {{cache:'no-store'}}); const js=await res.json();
            const status=js.status||'none';
            if(status==='done'){{
              setBusy(false); clearTimeout(pollTimer); setStatus(js.phase||'Analyse abgeschlossen',100,'done'); loadResult(); return;
            }}
            if(status==='cancelled'||status==='canceled'){{
              setBusy(false); clearTimeout(pollTimer); setStatus(js.phase||'Analyse wurde abgebrochen. Bereit für neue Analyse.',100,'done');
              byId('result').innerHTML='<h2>Analyseergebnis</h2><p class="section-intro">Analyse wurde abgebrochen. Es läuft keine Analyse mehr; du kannst jetzt eine neue Analyse starten.</p>'; return;
            }}
            if(status==='error'){{
              setBusy(false); clearTimeout(pollTimer); setStatus(js.error||js.phase||'Analysefehler',100,'error');
              byId('result').innerHTML='<h2>Analyseergebnis</h2><div class="error">'+escapeHtml(js.error||js.phase||'Analysefehler')+'</div>'; return;
            }}
            setStatus((js.phase||status||'-'), js.percent||0, 'info');
            setBusy(true); pollTimer=setTimeout(pollStatus, 1500);
          }}catch(e){{setStatus('Warte auf Analyse-Status...',20,'info'); pollTimer=setTimeout(pollStatus,2500);}}
        }}
        async function loadResult(){{
          try{{
            const res=await fetch('/analysis-result?job_id='+encodeURIComponent(currentJobId), {{cache:'no-store'}});
            const text=await res.text();
            byId('result').innerHTML=text;
            if(!res.ok) setStatus('Analyse abgeschlossen, aber Ergebnis konnte nicht geladen werden.',100,'error');
          }}catch(e){{setStatus('Analyse abgeschlossen, Ergebnisabruf fehlgeschlagen: '+(e.message||e),100,'error');}}
        }}
        async function cancelAnalysis(){{
          if(!currentJobId) return;
          try{{
            const res=await fetch('/cancel-analysis?job_id='+encodeURIComponent(currentJobId),{{method:'POST'}});
            const js=await res.json().catch(()=>({{phase:'Abbruch angefordert'}}));
            setStatus(js.phase||'Abbruch angefordert...',50,'info');
            pollStatus();
          }}catch(e){{setStatus('Abbruch konnte nicht angefordert werden: '+(e.message||e),0,'error');}}
        }}
        document.addEventListener('DOMContentLoaded', function(){{
          const sel=byId('filesSelect'); if(sel) sel.addEventListener('change', updateProfile);
          const start=byId('startBtn'); if(start) start.addEventListener('click', function(){{startAnalysis(false);}});
          const cancel=byId('cancelBtn'); if(cancel) cancel.addEventListener('click', cancelAnalysis);
          refreshStartButton();
          updateProfile();
          if(currentJobId) pollStatus();
        }});
        </script>
        </body></html>
        """

    @app.post("/start-analysis")
    async def start_analysis(request: Request):
        global _current_job
        cfg = load_config()
        base = log_dir_from_config(cfg)
        form = await request.form()
        selected = [str(x) for x in form.getlist("files") if str(x)]
        extended_confirm = str(form.get("extended_confirm", "")) == "1"
        try:
            paths = resolve_csv_files(base, selected)
            profile = selection_profile(paths, cfg)
            if profile["rejected"]:
                return JSONResponse({"error": profile["risk_text"], "profile": profile}, status_code=400)
            if profile["needs_confirmation"] and not extended_confirm:
                return JSONResponse({"requires_confirmation": True, "message": profile["risk_text"], "profile": profile}, status_code=409)
            extended = bool(profile["needs_confirmation"])
            key = _analysis_key(paths, extended)
            cached = _cache_get(key)
            if cached:
                job_id = str(cached.get("_job_id") or uuid.uuid4())
                cached["_job_id"] = job_id
                return {"job_id": job_id, "status": "done", "phase": "Gecachtes Ergebnis verfügbar", "percent": 100}
            with _job_lock:
                if _current_job and _current_job.get("status") == "running":
                    return JSONResponse({"error": "Es läuft bereits eine Analyse. Bitte warten oder abbrechen.", "job_id": _current_job.get("id")}, status_code=409)
                job_id = uuid.uuid4().hex
                cancel_event = threading.Event()
                _current_job = {
                    "id": job_id, "status": "running", "phase": "Analyse wird vorbereitet", "percent": 10,
                    "error": "", "result": None, "html": "", "started": time.time(), "finished": None,
                    "selected": [p.name for p in paths], "cache_key": key, "cancel_event": cancel_event,
                }
                job = _current_job

            def worker() -> None:
                try:
                    result = analyze_snapshot(paths, cfg, extended, cancel_event, job)
                    if cancel_event.is_set():
                        raise RuntimeError("Analyse abgebrochen.")
                    result["_job_id"] = job_id
                    result["_cache_key"] = key
                    html_result = render_result_html(result, job_id)
                    _cache_put(key, result)
                    with _job_lock:
                        job.update({"status": "done", "phase": "Analyse abgeschlossen", "percent": 100, "result": result, "html": html_result, "finished": time.time()})
                except Exception as exc:
                    with _job_lock:
                        if cancel_event.is_set():
                            job.update({"status": "cancelled", "phase": "Analyse wurde abgebrochen. Bereit für neue Analyse.", "percent": 100, "error": "", "finished": time.time()})
                        else:
                            job.update({"status": "error", "phase": "Analysefehler", "percent": 100, "error": str(exc), "finished": time.time()})

            threading.Thread(target=worker, name="zec-analysis", daemon=True).start()
            return {"job_id": job_id, "status": "running", "phase": "Analyse gestartet", "percent": 10, "profile": profile}
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.get("/analysis-status")
    def analysis_status(job_id: str = Query(default="")):
        job = _current_job_snapshot()
        if not job or (job_id and job.get("id") != job_id):
            return {"status": "none", "phase": "Keine laufende Analyse", "percent": 0}
        return {k: v for k, v in job.items() if k not in {"result", "html", "cache_key"}}

    @app.get("/analysis-result", response_class=HTMLResponse)
    def analysis_result(job_id: str = Query(default="")):
        job = _current_job_snapshot()
        if job and job.get("id") == job_id and job.get("status") == "done":
            with _job_lock:
                return HTMLResponse(str((_current_job or {}).get("html") or "<div class='error'>Kein Ergebnis.</div>"))
        result, _ = _get_result_from_job(job_id)
        if result:
            return HTMLResponse(render_result_html(result, job_id))
        return HTMLResponse("<div class='error'>Kein gecachtes Ergebnis für diese Analyse-ID gefunden.</div>", status_code=404)

    @app.post("/cancel-analysis")
    def cancel_analysis(job_id: str = Query(default="")):
        with _job_lock:
            if not _current_job or _current_job.get("id") != job_id or _current_job.get("status") != "running":
                return {"status": "none", "phase": "Keine passende laufende Analyse"}
            cancel_event = _current_job.get("cancel_event")
            if cancel_event:
                cancel_event.set()
            _current_job["phase"] = "Abbruch angefordert"
            return {"status": "cancelling", "phase": "Abbruch angefordert. Bitte warten, bis die Analyse beendet wurde."}

    @app.get("/report.txt")
    def report_txt(job_id: str = Query(default="")):
        result, _ = _get_result_from_job(job_id)
        if not result:
            return PlainTextResponse("Kein gecachtes Analyseergebnis vorhanden. Bitte Analyse zuerst über die Weboberfläche starten.\n", status_code=409)
        return PlainTextResponse(text_report(result), media_type="text/plain; charset=utf-8")

    @app.get("/report.json")
    def report_json(job_id: str = Query(default="")):
        result, _ = _get_result_from_job(job_id)
        if not result:
            return Response(json.dumps({"error": "Kein gecachtes Analyseergebnis vorhanden. Bitte Analyse zuerst starten."}, ensure_ascii=False), status_code=409, media_type="application/json; charset=utf-8")
        return Response(json.dumps(result, indent=2, ensure_ascii=False), media_type="application/json; charset=utf-8")

    @app.get("/summary.csv")
    def report_summary_csv(job_id: str = Query(default="")):
        result, _ = _get_result_from_job(job_id)
        if not result:
            return PlainTextResponse("metric;value\nerror;Kein gecachtes Analyseergebnis vorhanden. Bitte Analyse zuerst starten.\n", status_code=409, media_type="text/csv; charset=utf-8")
        return PlainTextResponse(summary_csv(result), media_type="text/csv; charset=utf-8")

    @app.get("/health")
    def health():
        job = _current_job_snapshot()
        return {"status": "ok", "schema": CSV_SCHEMA, "version": REPLAY_VERSION, "analysis_job": {"status": job.get("status"), "phase": job.get("phase")} if job else None}

    return app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8090)
    args = parser.parse_args()
    uvicorn.run(build_app(), host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
