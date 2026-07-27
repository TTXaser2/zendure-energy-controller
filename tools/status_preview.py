#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Passive live preview for the common ZEC status-page renderer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from status_page_v2 import render_status_page_v2  # noqa: E402
from status_preview_scenarios import (  # noqa: E402
    DEFAULT_SCENARIO,
    build_preview_grid_payload,
    build_preview_soc_payload,
    build_preview_status_payload,
    normalize_scenario,
)
from version import APP_VERSION, APP_VERSION_LABEL  # noqa: E402


def create_preview_app(*, dark_mode: bool = False) -> FastAPI:
    app = FastAPI(title="Zendure Status UI Preview", version=APP_VERSION)
    static_dir = PROJECT_ROOT / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def homepage(scenario: str = Query(DEFAULT_SCENARIO)) -> str:
        key = normalize_scenario(scenario)
        payload = build_preview_status_payload(key)
        return render_status_page_v2(
            {"UI_DARK_MODE": bool(dark_mode)},
            payload,
            analysis_available=False,
            analysis_port=8090,
        )

    @app.get("/status-view-data")
    def status_view_data(scenario: str = Query(DEFAULT_SCENARIO)):
        return build_preview_status_payload(normalize_scenario(scenario))

    @app.get("/grid-mini-data")
    def grid_mini_data(scenario: str = Query(DEFAULT_SCENARIO)):
        return build_preview_grid_payload(normalize_scenario(scenario))

    @app.get("/storage-soc-day-data")
    def storage_soc_day_data(
        date: Optional[str] = Query(None),
        scenario: str = Query(DEFAULT_SCENARIO),
    ):
        return build_preview_soc_payload(normalize_scenario(scenario), date=date)

    @app.get("/favicon.svg")
    def favicon_svg():
        svg = """<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 64 64\"><rect width=\"64\" height=\"64\" rx=\"14\" fill=\"#2563eb\"/><path d=\"M17 20h30L27 44h20\" fill=\"none\" stroke=\"white\" stroke-width=\"7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></svg>"""
        return Response(svg, media_type="image/svg+xml")

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "service": "zendure-status-preview",
            "version": APP_VERSION_LABEL,
            "read_only": True,
            "mqtt": False,
            "controller": False,
            "writes": False,
        }

    @app.get("/ready")
    def ready():
        return {"ready": True, "service": "zendure-status-preview", "version": APP_VERSION_LABEL}

    return app


app = create_preview_app()


def main() -> int:
    parser = argparse.ArgumentParser(description="Passive ZEC status-page preview with synthetic live data")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8091)
    parser.add_argument("--dark", action="store_true", help="Render preview in dark mode")
    args = parser.parse_args()
    preview_app = create_preview_app(dark_mode=args.dark)
    uvicorn.run(preview_app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
