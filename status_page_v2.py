# SPDX-License-Identifier: AGPL-3.0-or-later
"""Standalone V2 status-page renderer.

The page deliberately does not reuse the historical status-card markup.  It
consumes only the compact status view model and dedicated cached graph APIs.
"""

from __future__ import annotations

import html
import json
from typing import Any, Dict, Iterable

from version import APP_VERSION_LABEL


def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _icon(name: str) -> str:
    paths = {
        "home": '<path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10.5V20h13v-9.5"/>',
        "graph": '<path d="M4 18V6"/><path d="M4 18h16"/><path d="m6 15 4-5 3 3 5-7"/>',
        "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3A1.7 1.7 0 0 0 10 3V2.8h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z"/>',
        "analysis": '<path d="M4 12h3l2-5 4 10 2-5h5"/>',
        "manual": '<path d="M4 5.5A3.5 3.5 0 0 1 7.5 2H12v18H7.5A3.5 3.5 0 0 0 4 23.5Z"/><path d="M20 5.5A3.5 3.5 0 0 0 16.5 2H12v18h4.5a3.5 3.5 0 0 1 3.5 3.5Z"/>',
        "meter": '<path d="M4 17a8 8 0 1 1 16 0"/><path d="m12 17 4-5"/><path d="M8 17h8"/>',
        "mode": '<path d="M4.5 9A8 8 0 0 1 18 5.5"/><path d="M18 2v4h-4"/><path d="M19.5 15A8 8 0 0 1 6 18.5"/><path d="M6 22v-4h4"/>',
        "battery": '<rect x="3" y="6" width="17" height="12" rx="2"/><path d="M20 10h2v4h-2"/><path d="M7 10h6"/><path d="M10 7v6"/>',
        "primary": '<rect x="3" y="5" width="18" height="13" rx="2"/><path d="M8 21h8"/><path d="M12 18v3"/><path d="M7 9h10"/>',
        "radio": '<path d="M5 9a10 10 0 0 0 0 6"/><path d="M8 11a6 6 0 0 0 0 2"/><path d="M19 9a10 10 0 0 1 0 6"/><path d="M16 11a6 6 0 0 1 0 2"/><circle cx="12" cy="12" r="2"/>',
        "database": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
        "diagnostics": '<path d="M4 18h16"/><path d="M6 15V9"/><path d="M10 15V5"/><path d="M14 15v-3"/><path d="M18 15V7"/>',
        "resources": '<rect x="5" y="5" width="14" height="14" rx="2"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
        "events": '<path d="M7 4h10v16H7z"/><path d="M9 8h6M9 12h6M9 16h4"/>',
        "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6"/><path d="M12 7h.01"/>',
        "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    }
    body = paths.get(name, paths["info"])
    return f'<svg class="zec-icon" viewBox="0 0 24 24" aria-hidden="true">{body}</svg>'


def _info_button(title: str, text: str) -> str:
    return (
        f'<button type="button" class="zec-info-button" data-info-title="{_e(title)}" '
        f'data-info-text="{_e(text)}" aria-label="Information zu {_e(title)}">{_icon("info")}</button>'
    )


def _ring(key: str, label: str, soc: Any, subtitle: str = "SOC aktuell") -> str:
    try:
        n = float(soc)
        value = max(0.0, min(100.0, n))
        shown = f"{round(n):.0f} %"
        valid = True
    except Exception:
        value = 0.0
        shown = "—"
        valid = False
    return f'''
      <div class="zec-soc-block" data-ring-block="{_e(key)}">
        <div class="zec-soc-ring {'is-unknown' if not valid else ''}" data-ring="{_e(key)}" style="--soc:{value:.2f}">
          <div class="zec-soc-ring-inner">
            <strong data-zec="{_e(key)}.soc_text">{_e(shown)}</strong>
            <span>{_e(label)}</span>
          </div>
        </div>
        <div class="zec-soc-caption" data-zec="{_e(key)}.caption">{_e(subtitle)}</div>
      </div>
    '''


def _unit_rows(units: Iterable[Dict[str, Any]]) -> str:
    rows = []
    for idx, unit in enumerate(units, start=1):
        key = f"zendure.units.{idx-1}"
        rows.append(
            f'''<div class="zec-unit-row" data-unit-index="{idx-1}">
              <span class="zec-unit-name">{_e(unit.get('name') or f'Unit {idx}')}</span>
              <span data-zec="{key}.detail">{_e(unit.get('detail') or '—')}</span>
            </div>'''
        )
    return "".join(rows)


def _nav(analysis_available: bool, analysis_port: int) -> str:
    links = [
        f'<a class="is-active" href="/">{_icon("home")}<span>Status</span></a>',
        f'<a href="/graph">{_icon("graph")}<span>Graph</span></a>',
        f'<a href="/settings">{_icon("settings")}<span>Settings</span></a>',
    ]
    if analysis_available:
        links.append(
            f'<a class="analysis-service-link" href="#" data-replay-port="{int(analysis_port)}">'
            f'{_icon("analysis")}<span>Analyse-Service</span><i class="zec-nav-live-dot"></i></a>'
        )
    links.append(f'<a href="/manual.pdf">{_icon("manual")}<span>Handbuch</span></a>')
    return "".join(links)


def render_status_page_v2(
    cfg: Dict[str, Any],
    payload: Dict[str, Any],
    *,
    analysis_available: bool,
    analysis_port: int,
) -> str:
    payload = dict(payload or {})
    payload.setdefault("logging", {})
    payload.setdefault("resources", {})
    payload.setdefault("diag", {})
    payload.setdefault("events", {"items": [], "open_count": 0})
    dark = bool(cfg.get("UI_DARK_MODE", False))
    theme = "dark" if dark else "light"
    units = list(payload.get("zendure", {}).get("units") or [])[:2]
    if not units:
        units = [{"name": "Zendure", "soc": payload.get("zendure", {}).get("soc"), "detail": "—"}]

    if len(units) == 1:
        unit = units[0]
        zendure_body = f'''
          <div class="zec-storage-layout zec-storage-layout-single">
            {_ring('zendure', 'Zendure', unit.get('soc'), unit.get('caption') or 'SOC aktuell')}
            <div class="zec-storage-details">
              <div class="zec-detail-row"><span>Istleistung</span><strong data-zec="zendure.actual">{_e(payload['zendure'].get('actual'))}</strong></div>
              <div class="zec-detail-row"><span>Zustand</span><strong data-zec="zendure.state">{_e(unit.get('state_text') or '—')}</strong></div>
              <div class="zec-detail-row"><span>Rest bis Max-SOC</span><strong data-zec="zendure.remaining_text">{_e(payload['zendure'].get('remaining_text'))}</strong></div>
              <div class="zec-detail-row"><span>Max-SOC</span><strong data-zec="zendure.max_soc_text">{_e(payload['zendure'].get('max_soc_text'))}</strong></div>
            </div>
          </div>
        '''
    else:
        zendure_body = f'''
          <div class="zec-dual-rings">
            {_ring('zendure_unit_1', units[0].get('name') or 'Unit 1', units[0].get('soc'), units[0].get('state_text') or '—')}
            {_ring('zendure_unit_2', units[1].get('name') or 'Unit 2', units[1].get('soc'), units[1].get('state_text') or '—')}
          </div>
          <div class="zec-system-summary">
            <span>System-SOC</span><strong data-zec="zendure.system_soc_text">{_e(payload['zendure'].get('system_soc_text'))}</strong>
            <span>Ist gesamt</span><strong data-zec="zendure.actual">{_e(payload['zendure'].get('actual'))}</strong>
          </div>
          <div class="zec-unit-list">{_unit_rows(units)}</div>
        '''

    warnings = list(payload.get("system", {}).get("warnings") or [])
    warnings_html = "".join(f"<li>{_e(w)}</li>" for w in warnings) or "<li>Keine aktiven Warnungen oder Fehler.</li>"
    bootstrap = json.dumps(payload, ensure_ascii=False).replace("</", "<" + "\\/")

    return f'''<!doctype html>
<html lang="de" data-theme="{theme}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Zendure Energy Controller – Status</title>
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="/static/status_v2.css?v={_e(APP_VERSION_LABEL)}">
</head>
<body class="zec-status-v2">
  <header class="zec-topbar">
    <div class="zec-brand"><span class="zec-wordmark">ZENDURE</span><span class="zec-product">Energy Controller</span><span class="zec-brand-divider" aria-hidden="true"></span></div>
    <nav class="zec-main-nav" aria-label="Hauptnavigation">{_nav(analysis_available, analysis_port)}</nav>
    <div class="zec-topbar-right">
      <div class="zec-system-menu-wrap">
        <button id="systemStatusButton" class="zec-system-pill { _e(payload['system'].get('kind','ok')) }" type="button" aria-expanded="false">
          <span class="zec-status-dot"></span><span data-zec="system.label">{_e(payload['system'].get('label'))}</span>
        </button>
        <div id="systemStatusMenu" class="zec-system-menu" hidden>
          <div class="zec-system-menu-title">Systemstatus</div>
          <ul id="systemWarningList">{warnings_html}</ul>
          <div class="zec-system-menu-stand">Stand: <span data-zec="server_time">{_e(payload.get('server_time'))}</span></div>
        </div>
      </div>
      <span class="zec-version-pill">{_e(APP_VERSION_LABEL)}</span>
      <span class="zec-clock">{_icon('clock')}<b id="localClock">{_e(payload.get('server_time'))}</b></span>
      <details id="expertMenuDetails" class="zec-expert-menu-wrap">
        <summary id="expertMenuButton" class="zec-expert-button" aria-label="Expertenmenü öffnen">Experte <span aria-hidden="true">▾</span></summary>
        <div id="expertMenu" class="zec-expert-menu">
          <a href="/mqtt-diagnostics">MQTT Diagnose</a>
          <a href="/measurements">Messdaten-CSV</a>
          <a href="/status_old">Alte Statusseite</a>
          <a href="/graph_old">Alter Graph</a>
        </div>
      </details>
    </div>
  </header>

  <div id="criticalBanner" class="zec-critical-banner" {'hidden' if payload['system'].get('kind') != 'bad' else ''}>
    <strong>Schutzmodus aktiv.</strong> <span data-zec="system.critical_text">{_e(payload['system'].get('critical_text') or 'Regelung ist eingeschränkt.')}</span>
  </div>

  <main class="zec-page-shell">
    <section class="zec-main-grid" aria-label="Aktueller Systemstatus">
      <article class="zec-card zec-grid-card" data-card="grid">
        <header class="zec-card-header"><div class="zec-card-title">{_icon('meter')}<h2>Netzleistung</h2></div>{_info_button('Netzleistung','Diese Karte zeigt den aktuellen ungefilterten Netzleistungswert am Netzanschlusspunkt. Negative Werte bedeuten Einspeisung/Export, positive Werte Netzbezug. Der Mini-Graph zeigt die letzten Messpunkte und reagiert direkt auf die Maus.')}</header>
        <div class="zec-card-center">
          <div class="zec-grid-value" data-zec="grid.value">{_e(payload['grid'].get('value'))}</div>
          <div class="zec-grid-state" data-zec="grid.status">{_e(payload['grid'].get('status'))}</div>
        </div>
        <div class="zec-mini-chart-wrap"><canvas id="gridMiniChart" aria-label="Netzleistungsverlauf der letzten Messpunkte"></canvas><div id="gridMiniTooltip" class="zec-chart-tooltip" hidden></div></div>
        <footer class="zec-card-footer"><span class="zec-status-dot { _e(payload['grid'].get('tone','ok')) }"></span><span>Quelle: <b data-zec="grid.source">{_e(payload['grid'].get('source'))}</b> · <span data-zec="grid.freshness_text">{_e(payload['grid'].get('freshness_text'))}</span></span></footer>
      </article>

      <article class="zec-card zec-mode-card" data-card="mode">
        <header class="zec-card-header"><div class="zec-card-title">{_icon('mode')}<h2>Betriebsmodus</h2></div>{_info_button('Betriebsmodus','Diese Karte zeigt die aktuelle Entscheidung des zentralen ZEC-Reglers. Der Zielwert beschreibt Laden, Entladen oder Neutralbetrieb. Nacht- und Fixed-Modi zeigen zusätzlich Prognose, Ziel-SOC und Folgemodus.')}</header>
        <div class="zec-mode-main">
          <div class="zec-mode-name" data-zec="mode.mode">{_e(payload['mode'].get('mode'))}</div>
          <div class="zec-mode-public" data-zec="mode.text">{_e(payload['mode'].get('text'))}</div>
        </div>
        <div class="zec-mode-details">
          <div class="zec-mode-row"><span>Ziel</span><strong data-zec="mode.target">{_e(payload['mode'].get('target'))}</strong></div>
          <div class="zec-mode-row"><span>Grund</span><strong data-zec="mode.reason">{_e(payload['mode'].get('reason'))}</strong></div>
          <div class="zec-mode-projection" data-zec="mode.projection">{_e(payload['mode'].get('projection'))}</div>
          <div class="zec-mode-row zec-last-change"><span>Letzte Änderung</span><strong data-zec="mode.last_change">{_e(payload['mode'].get('last_change'))}</strong></div>
        </div>
        <footer class="zec-card-footer"><span class="zec-status-dot { _e(payload['mode'].get('tone','ok')) }"></span><span data-zec="mode.status_text">{_e(payload['mode'].get('status_text'))}</span></footer>
      </article>

      <article class="zec-card zec-zendure-card" data-card="zendure">
        <header class="zec-card-header"><div class="zec-card-title">{_icon('battery')}<h2>{'Zendure-System' if len(units)>1 else 'Zendure / Batterie'}</h2></div>{_info_button('Zendure / Batterie','Diese Karte zeigt SOC und tatsächliche Leistung des Zendure-Speichers. Bei zwei Headunits werden beide Units separat dargestellt; beide folgen weiterhin dem gemeinsamen systemischen Operating Mode.')}</header>
        {zendure_body}
        <div class="zec-inline-warning" data-zec="zendure.command_warning" {'hidden' if not payload['zendure'].get('command_warning') else ''}>{_e(payload['zendure'].get('command_warning'))}</div>
        <footer class="zec-card-footer"><span class="zec-status-dot { _e(payload['zendure'].get('tone','ok')) }"></span><span>Telemetrie: <b data-zec="zendure.source">{_e(payload['zendure'].get('source'))}</b></span></footer>
      </article>

      <article class="zec-card zec-primary-card" data-card="primary">
        <header class="zec-card-header"><div class="zec-card-title">{_icon('primary')}<h2>Primärspeicher</h2></div>{_info_button('Primärspeicher','Diese Karte zeigt den SMA-/Primärspeicher. ZEC steuert ihn nicht direkt, berücksichtigt SOC und Lade-/Entladeleistung jedoch für Harvest, Cross-Charge-Schutz und die defensive Speicherpriorität.')}</header>
        <div class="zec-storage-layout zec-storage-layout-single">
          {_ring('primary', 'SMA', payload['primary'].get('soc'), 'SOC aktuell')}
          <div class="zec-storage-details">
            <div class="zec-detail-row"><span>Istleistung</span><strong data-zec="primary.actual">{_e(payload['primary'].get('actual'))}</strong></div>
            <div class="zec-detail-row"><span>Status</span><strong data-zec="primary.status">{_e(payload['primary'].get('status'))}</strong></div>
            <div class="zec-detail-row zec-harmony-row"><span>Harmonisierung</span><strong data-zec="primary.line">{_e(payload['primary'].get('line'))}</strong></div>
          </div>
        </div>
        <footer class="zec-card-footer"><span class="zec-status-dot { _e(payload['primary'].get('tone','ok')) }"></span><span><b data-zec="primary.source">{_e(payload['primary'].get('source'))}</b> · <span data-zec="primary.freshness_text">{_e(payload['primary'].get('freshness_text'))}</span></span></footer>
      </article>

      <article class="zec-card zec-source-card" data-card="source">
        <header class="zec-card-header"><div class="zec-card-title">{_icon('radio')}<h2>Netzleistungsquelle</h2></div>{_info_button('Netzleistungsquelle','Diese Karte zeigt die aktive Netzleistungsquelle, deren Aktualität und ob mehrere erkannte SMA-Geräte korrekt auf das konfigurierte Zielgerät gefiltert werden. Alte verworfene Einzelmesswerte ändern den aktuellen Quellenstatus nicht.')}</header>
        <div class="zec-source-name" data-zec="source.name">{_e(payload['source'].get('name'))}</div>
        <div class="zec-source-device" data-zec="source.device_line">{_e(payload['source'].get('device_line'))}</div>
        <dl class="zec-key-values">
          <div><dt>Letztes Paket</dt><dd data-zec="source.age_text">{_e(payload['source'].get('age_text'))}</dd></div>
          <div><dt>Pakete</dt><dd data-zec="source.packets_text">{_e(payload['source'].get('packets_text'))}</dd></div>
        </dl>
        <div class="zec-rejected-event" data-zec="source.rejected_text" {'hidden' if not payload['source'].get('rejected_text') else ''}>{_e(payload['source'].get('rejected_text'))}</div>
        <div class="zec-rejected-count" data-zec="source.rejected_count_text" {'hidden' if not payload['source'].get('rejected_count_text') else ''}>{_e(payload['source'].get('rejected_count_text'))}</div>
        <footer class="zec-card-footer"><span class="zec-status-dot { _e(payload['source'].get('tone','ok')) }"></span><span data-zec="source.auto_text">{_e(payload['source'].get('auto_text'))}</span></footer>
      </article>
    </section>

    <section class="zec-wide-card zec-soc-day-card">
      <header class="zec-wide-header">
        <div><div class="zec-card-title">{_icon('graph')}<h2>Speicher-SOC Tagesgraph</h2></div></div>
        <div class="zec-day-nav"><button id="dayPrev" type="button">‹ Zurück</button><button id="dayToday" type="button">Heute</button><button id="dayNext" type="button">Vor ›</button><label class="zec-day-picker-label" aria-label="Datum direkt auswählen"><strong id="socDayLabel"></strong><input id="socDayPicker" type="date" aria-label="Datum des Speicher-SOC-Tagesgraphen auswählen"></label></div>
      </header>
      <div class="zec-day-chart-wrap"><canvas id="storageSocChart" aria-label="Speicher-SOC im Tagesverlauf"></canvas><div id="storageSocTooltip" class="zec-chart-tooltip" hidden></div></div>
      <div id="storageSocLegend" class="zec-chart-legend"></div>
      <div id="storageSocStatus" class="zec-chart-status">SOC-Daten werden geladen…</div>
    </section>

    <section class="zec-lower-grid">
      <article class="zec-lower-card" data-lower="logging">
        <header class="zec-card-header"><div class="zec-card-title">{_icon('database')}<h2>Messdaten / Logging</h2></div>{_info_button('Messdaten / Logging','Zeigt CSV-Protokoll, SQLite-Graphspeicher, Speicherziel, Queue, Fallback und verfügbaren Speicher. Dateisystemdaten werden ausschließlich gecacht im Web-Backend erfasst; der Regelzyklus bleibt unberührt.')}</header>
        <div class="zec-health-rows">
          <div><span>CSV-Protokoll</span><strong data-zec="logging.status">{_e(payload['logging'].get('status'))}</strong></div>
          <div><span>SQLite-Graphspeicher</span><strong data-zec="logging.db">{_e(payload['logging'].get('db'))}</strong></div>
          <div><span>Speicherziel</span><strong data-zec="logging.target">{_e(payload['logging'].get('target'))}</strong></div>
          <div><span>DB-Datei</span><strong data-zec="logging.db_name">{_e(payload['logging'].get('db_name'))}</strong></div>
          <div><span>DB-Größe</span><strong data-zec="logging.db_size_text">—</strong></div>
          <div><span>Queue</span><strong data-zec="logging.queue_text">—</strong></div>
          <div><span>Letzter DB-Schreibvorgang</span><strong data-zec="logging.last_write">{_e(payload['logging'].get('last_write'))}</strong></div>
          <div><span>Fallback</span><strong data-zec="logging.fallback_text">—</strong></div>
          <div><span>Freier Speicher</span><strong data-zec="logging.free_text">—</strong></div>
        </div>
        <div class="zec-meter"><div class="zec-meter-fill" data-meter="logging.disk"></div></div>
        <footer class="zec-card-footer"><span class="zec-status-dot {_e(payload['logging'].get('tone','ok'))}"></span><span data-zec="logging.footer">Messdatenspeicherung wird bewertet</span></footer>
      </article>

      <article class="zec-lower-card" data-lower="resources">
        <header class="zec-card-header"><div class="zec-card-title">{_icon('resources')}<h2>Systemressourcen</h2></div>{_info_button('Systemressourcen','CPU zeigt die Gesamtauslastung aller Kerne. RAM wird Linux-korrekt über MemAvailable bewertet. Systemlast (1/5/15 Min.) ist auf dem Vierkern-Pi bei etwa 4,0 vollständig ausgelastet. Historische Throttling-Bits sind Hinweise, aktuelle Bits sind Störungen.')}</header>
        <div class="zec-resource-block"><div class="zec-resource-label"><span>CPU-Auslastung</span><strong data-zec="resources.cpu_text">—</strong></div><div class="zec-meter"><div class="zec-meter-fill" data-meter="resources.cpu"></div></div></div>
        <div class="zec-resource-block"><div class="zec-resource-label"><span>RAM-Auslastung</span><strong data-zec="resources.ram_text">—</strong></div><div class="zec-meter"><div class="zec-meter-fill" data-meter="resources.ram"></div></div></div>
        <div class="zec-resource-block"><div class="zec-resource-label"><span>CPU-Temperatur</span><strong data-zec="resources.temp_text">—</strong></div><div class="zec-meter"><div class="zec-meter-fill" data-meter="resources.temp"></div></div></div>
        <div class="zec-health-rows compact">
          <div><span>Systemlast (1/5/15 Min.)</span><strong data-zec="resources.load_text">—</strong></div>
          <div><span>Swap-Nutzung</span><strong data-zec="resources.swap_text">—</strong></div>
          <div><span>Systemlaufzeit</span><strong data-zec="resources.uptime_text">—</strong></div>
          <div><span>Throttling / Unterspannung</span><strong data-zec="resources.throttle_text">—</strong></div>
        </div>
        <footer class="zec-card-footer"><span class="zec-status-dot {_e(payload['resources'].get('tone','unknown'))}"></span><span data-zec="resources.status">{_e(payload['resources'].get('status'))}</span></footer>
      </article>

      <article class="zec-lower-card" data-lower="diagnostics">
        <header class="zec-card-header"><div class="zec-card-title">{_icon('diagnostics')}<h2>Controller &amp; Schnittstellen</h2></div>{_info_button('Controller & Schnittstellen','Zeigt den zuletzt abgeschlossenen aktiven Gesamtdurchlauf und dessen wesentliche Abschnitte. Mittelwerte und P95 können später ergänzend in die Detaildiagnose aufgenommen werden. Der Zendure-Kommandoabgleich sendet AC-Modus sowie Lade-/Entladelimits nach Kommunikationsunsicherheit erneut.')}</header>
        <div class="zec-health-chain"><span data-chain="rule">● Regelung</span><span data-chain="mqtt">● MQTT</span><span data-chain="api">● API</span><span data-chain="effect">● Wirkung</span></div>
        <div class="zec-health-rows">
          <div><span>Regelzyklus</span><strong data-zec="diag.rule">{_e(payload['diag'].get('rule'))}</strong></div>
          <div><span>MQTT-Broker</span><strong data-zec="diag.broker">{_e(payload['diag'].get('broker'))}</strong></div>
          <div><span>Zendure-Telemetrie</span><strong data-zec="diag.mqtt">{_e(payload['diag'].get('mqtt'))}</strong></div>
          <div><span>Lokale API</span><strong data-zec="diag.api">{_e(payload['diag'].get('api'))}</strong></div>
          <div><span>Kommandowirkung</span><strong data-zec="diag.effect">{_e(payload['diag'].get('effect'))}</strong></div>
        </div>
        <div class="zec-timing-title">Durchlaufzeiten – letzter Durchlauf</div>
        <div class="zec-health-rows compact">
          <div><span>Aktiver Gesamtdurchlauf</span><strong data-zec="diag.loop_text">{_e(payload['diag'].get('loop_text'))}</strong></div>
          <div><span>Reine Regelentscheidung</span><strong data-zec="diag.control_text">—</strong></div>
          <div><span>MQTT-/Wirkungspfad</span><strong data-zec="diag.command_text">—</strong></div>
          <div><span>Logging im Hauptthread</span><strong data-zec="diag.measurement_logging_text">{_e(payload['diag'].get('measurement_logging_text'))}</strong></div>
          <div><span>SQLite-Schreiben, asynchron</span><strong data-zec="diag.sqlite_text">—</strong></div>
          <div><span>Langsamster Abschnitt</span><strong data-zec="diag.slowest_text">—</strong></div>
        </div>
        <div class="zec-meter"><div class="zec-meter-fill" data-meter="diag.cycle"></div></div>
        <div class="zec-health-rows compact">
          <div><span>Analyse / Replay</span><strong data-zec="diag.analysis">{_e(payload['diag'].get('analysis'))}</strong></div>
          <div><span>Controller-Laufzeit</span><strong data-zec="diag.uptime_text">—</strong></div>
          <div class="zec-full-row"><span>Letzter Zendure-Kommandoabgleich</span><strong data-zec="diag.resync_text">—</strong></div>
        </div>
        <footer class="zec-card-footer"><span class="zec-status-dot ok"></span><span data-zec="diag.footer">Controller und Schnittstellen werden bewertet</span></footer>
      </article>

      <article class="zec-lower-card zec-events-card" data-lower="events">
        <header class="zec-card-header"><div class="zec-card-title">{_icon('events')}<h2>Betriebsereignisse</h2></div>{_info_button('Betriebsereignisse','Persistentes Betriebsjournal relevanter Zustandswechsel. Es zeigt keine Rohlogs und keinen Regelzyklus-Spam. Offene Ereignisse stehen zuerst, danach Heute und Gestern. Das Journal beeinflusst keine Regelentscheidung und keinen Kommandoabgleich.')}</header>
        <div class="zec-events-scroll" id="operationalEvents"><div class="zec-empty">Ereignisse werden geladen…</div></div>
        <footer class="zec-card-footer"><span class="zec-status-dot unknown"></span><span data-zec="events.footer">Ereignisstatus wird bewertet</span></footer>
      </article>
    </section>
  </main>

  <div id="zecInfoPopover" class="zec-info-popover" hidden><strong id="zecInfoTitle"></strong><div id="zecInfoText"></div></div>
  <script>window.ZEC_BOOTSTRAP={bootstrap};</script>
  <script src="/static/status_v2.js?v={_e(APP_VERSION_LABEL)}"></script>
</body>
</html>'''
