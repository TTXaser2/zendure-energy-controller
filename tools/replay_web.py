#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Optional separate web UI for Zendure Energy Controller CSV analysis.

import argparse
import html
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlencode

import uvicorn
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

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
    analyze_file,
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
    recommendations_table,
    summary_cards,
    text_report,
    tracking_table,
)

try:
    from version import APP_VERSION as REPLAY_VERSION  # noqa: E402
except Exception:  # pragma: no cover
    REPLAY_VERSION = "12.8.4"


def load_config() -> Dict[str, Any]:
    path = PROJECT_ROOT / "config.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def log_dir_from_config(cfg: Dict[str, Any]) -> Path:
    raw = str(cfg.get("CSV_LOG_DIR", "logs") or "logs")
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


def query_for_files(selected: Sequence[str]) -> str:
    return urlencode([("files", item) for item in selected])


def safe_limits() -> AnalysisLimits:
    return AnalysisLimits(max_files=20, max_total_bytes=50 * 1024 * 1024, max_rows=500_000)


def analyze_selected(base: Path, selected: Sequence[str], cfg: Dict[str, Any]) -> Dict[str, Any]:
    paths = resolve_csv_files(base, selected)
    return analyze_files(
        [str(p) for p in paths],
        min_soc_percent=int(cfg.get("MIN_SOC_PERCENT", 15)),
        max_soc_percent=int(cfg.get("MAX_SOC_PERCENT", 99)),
        limits=safe_limits(),
        target_band_w=float(cfg.get("DEADBAND_W", 100) or 100),
        significant_grid_w=200.0,
        cross_discharge_threshold_w=float(cfg.get("SMA_DISCHARGE_BLOCK_W", 80) or 80),
        zendure_charge_threshold_w=float(cfg.get("MIN_EFFECTIVE_SURPLUS_FOR_CHARGE_W", 150) or 100),
        max_charge_power_w=float(cfg.get("MAX_CHARGE_POWER_W", 2100) or 2100),
        max_discharge_power_w=float(cfg.get("MAX_DISCHARGE_POWER_W", 2100) or 2100),
    )


def build_app() -> FastAPI:
    app = FastAPI(title="Zendure Replay Analyse", version=REPLAY_VERSION)

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
        options = "".join(
            f'<option value="{html.escape(p.name, quote=True)}" {"selected" if p.name in selected else ""}>{html.escape(p.name)} ({p.stat().st_size / 1024:.1f} KiB)</option>'
            for p in available
        )
        result_html = ""
        download_query = query_for_files(selected)
        if selected:
            try:
                result = analyze_selected(base, selected, cfg)
                result_html = f"""
                <div class="toc" id="top">
                    <b>Navigation:</b>
                    <a href="#kurzfazit">Kurzfazit</a><a href="#empfehlungen">Empfehlungen</a><a href="#diagramme">Diagramme</a>
                    <a href="#datenqualitaet">Datenqualität</a><a href="#regler">Reglerqualität</a><a href="#stellreserve">Stellreserve</a>
                    <a href="#tracking">Soll/Ist</a><a href="#deadband">Deadband</a><a href="#mqtt">MQTT</a>
                    <a href="#cross">Cross-Charge</a><a href="#matrix">Matrix</a><a href="#ereignisse">Ereignisse</a>
                </div>
                <h2 id="kurzfazit">Kurzfazit</h2>
                <div class="cards">{summary_cards(result)}</div>
                <h2 id="empfehlungen">Handlungsempfehlungen</h2><table>{recommendations_table(result)}</table>
                <p class="notice">Die Analyse liefert Hinweise auf wahrscheinliche Ursachen. Parameteränderungen sollten immer mit ausreichender Datenqualität und mehreren passenden Logzeiträumen gegengeprüft werden.</p>
                <h2 id="diagramme">Diagramme</h2>{charts_html(result)}
                <h2 id="ueberblick">Überblick</h2><table>{overview_table(result)}</table>
                <h2 id="datenqualitaet">Datenqualität</h2><table>{data_quality_table(result)}</table>
                <h2 id="energie">Energiefluss der ausgewählten Dateien</h2><table>{energy_table(result)}</table>
                <h2 id="regler">Faire Reglerqualität</h2><table>{fair_regulator_table(result)}</table>
                <h2 id="stellreserve">Stellreserve / Sättigung</h2><table>{actuator_table(result)}</table>
                <h2 id="tracking">Zendure Soll-/Ist-Folge</h2><table>{tracking_table(result)}</table>
                <h2 id="deadband">Deadband-Erfolg</h2><table>{deadband_table(result)}</table>
                <h2 id="mqtt">MQTT-Kommandowirkung</h2><table>{command_efficiency_table(result)}</table>
                <h2 id="oszillation">Oszillation / Richtungswechsel</h2><table>{oscillation_table(result)}</table>
                <h2 id="cross">Cross-Charge-Analyse</h2><table>{cross_charge_table(result)}</table>
                <h2 id="highsoc">Nachtentladung und High-SOC</h2><table>{high_soc_table(result)}</table>
                <h2 id="matrix">Betriebszustandsmatrix</h2><table>{mode_quality_table(result)}</table>
                <h2 id="ereignisse">Ereignisprotokoll</h2><table>{events_table(result)}</table>
                <p class="downloads">
                    <a href="/report.txt?{html.escape(download_query, quote=True)}">Text-Report</a>
                    <a href="/report.json?{html.escape(download_query, quote=True)}">JSON-Report</a>
                    <a href="/summary.csv?{html.escape(download_query, quote=True)}">CSV-Summary</a>
                    <a href="#top">nach oben</a>
                </p>
                """
            except Exception as exc:
                result_html = f"<div class='error'>Analysefehler: {html.escape(str(exc))}</div>"
        else:
            result_html = "<div class='error'>Keine CSV-Dateien im Logverzeichnis gefunden.</div>"

        selected_count = len(selected)
        return f"""
        <html><head><title>Zendure Replay Analyse</title><meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
        body{{font-family:Arial,sans-serif;margin:20px;background:#f5f7fb;color:#111827}}
        a{{color:#1565c0}} .section{{background:white;padding:18px;border-radius:12px;margin-bottom:18px;box-shadow:0 2px 8px #ddd}}
        table{{border-collapse:collapse;width:100%;margin-bottom:16px}} th,td{{border:1px solid #ddd;padding:8px;text-align:left;vertical-align:top}} th{{background:#f1f5f9;width:34%}}
        .error{{background:#fee2e2;border:1px solid #f87171;padding:12px;border-radius:8px}}
        .notice{{background:#eef6ff;border:1px solid #bfdbfe;padding:10px;border-radius:8px}}
        .small{{font-size:0.92em;color:#4b5563}} select{{min-width:320px;max-width:100%}} button{{padding:7px 12px}}
        .topnav{{display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin-bottom:10px}} .downloads a{{display:inline-block;margin-right:14px}}
        .badge{{display:inline-block;padding:3px 8px;border-radius:999px;font-weight:bold}} .ok{{background:#dcfce7}} .warn{{background:#fef3c7}} .bad{{background:#fee2e2}} .neutral{{background:#e5e7eb}}
        .term-info{{display:inline-block;margin-left:6px}}.term-info summary{{display:inline;color:#1565c0;cursor:pointer;font-weight:normal}}.term-info div{{margin-top:6px;color:#374151;font-weight:normal;line-height:1.35}}
        .toc{{position:sticky;top:0;background:#fff;border:1px solid #dbe4ef;padding:10px;border-radius:10px;margin-bottom:14px;z-index:5}}
        .toc a{{display:inline-block;margin:3px 8px 3px 0}} .cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:10px 0 16px}}
        .card{{border:1px solid #dbe4ef;border-radius:10px;padding:12px;background:#f8fafc;display:flex;justify-content:space-between;gap:8px;align-items:center}}
        .chartgrid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px}} .barrow{{display:grid;grid-template-columns:120px 1fr 70px;gap:8px;align-items:center;margin:6px 0}}
        .barbox{{height:14px;background:#e5e7eb;border-radius:999px;overflow:hidden}} .bar{{height:14px;background:#93c5fd;border-radius:999px}}
        h2{{scroll-margin-top:70px;border-bottom:1px solid #e5e7eb;padding-bottom:4px}}
        </style></head><body>
        <div class="topnav"><a href="{html.escape(controller_url, quote=True)}">← Zurück zum Zendure Controller</a><span class="small">Analyse-Dienst: {html.escape(replay_url)}</span></div>
        <div class="section"><h1>Zendure Replay Analyse V{REPLAY_VERSION}</h1>
        <p>Separater Analyse-Dienst für CSV-Dateien im Schema <code>{CSV_SCHEMA}</code>. Der Live-Controller wird hiervon nicht importiert oder beeinflusst.</p>
        <form method="get">
            <label>CSV-Dateien:</label><br>
            <select name="files" multiple size="8">{options}</select><br><br>
            <button type="submit">Analyse starten</button>
        </form>
        <p class="small">Mehrfachauswahl ist möglich. Schutzgrenzen: maximal 20 Dateien, 50 MB Gesamtgröße und 500.000 Messpunkte je Analyselauf. Ausgewählt: {selected_count} Datei(en).</p>
        <p class="small">Logverzeichnis: <code>{html.escape(str(base))}</code></p></div>
        <div class="section">{result_html}</div>
</body></html>
        """

    @app.get("/report.txt")
    def report_txt(files: Optional[List[str]] = Query(default=None), file: str = Query(default="")):
        cfg = load_config()
        base = log_dir_from_config(cfg)
        selected = selected_files_from_query(files, file, [])
        try:
            result = analyze_selected(base, selected, cfg)
            return PlainTextResponse(text_report(result), media_type="text/plain; charset=utf-8")
        except Exception as exc:
            return PlainTextResponse(f"Analysefehler: {exc}\n", status_code=400)

    @app.get("/report.json")
    def report_json(files: Optional[List[str]] = Query(default=None), file: str = Query(default="")):
        cfg = load_config()
        base = log_dir_from_config(cfg)
        selected = selected_files_from_query(files, file, [])
        try:
            result = analyze_selected(base, selected, cfg)
            # Do not leak absolute paths by default in the JSON download.
            result.pop("paths", None)
            return Response(json.dumps(result, indent=2, ensure_ascii=False), media_type="application/json; charset=utf-8")
        except Exception as exc:
            return Response(json.dumps({"error": str(exc)}, ensure_ascii=False), status_code=400, media_type="application/json; charset=utf-8")

    @app.get("/summary.csv")
    def report_summary_csv(files: Optional[List[str]] = Query(default=None), file: str = Query(default="")):
        cfg = load_config()
        base = log_dir_from_config(cfg)
        selected = selected_files_from_query(files, file, [])
        try:
            result = analyze_selected(base, selected, cfg)
            return PlainTextResponse(summary_csv(result), media_type="text/csv; charset=utf-8")
        except Exception as exc:
            return PlainTextResponse(f"metric;value\nerror;{str(exc).replace(';', ',')}\n", status_code=400, media_type="text/csv; charset=utf-8")

    @app.get("/health")
    def health():
        return {"status": "ok", "schema": CSV_SCHEMA, "version": REPLAY_VERSION}

    return app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8090)
    args = parser.parse_args()
    uvicorn.run(build_app(), host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
