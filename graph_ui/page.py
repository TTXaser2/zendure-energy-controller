# SPDX-License-Identifier: AGPL-3.0-or-later
"""Clean-sheet Graph UI for ZEC V14.1.

The presentation layer is intentionally isolated from legacy graph markup.
All values are loaded through the Graph Core V3 API contracts.
"""
from __future__ import annotations

import html


def render_graph_page(shell_html: str, *, version_label: str) -> str:
    """Render the greenfield graph page inside the shared ZEC shell."""
    css_link = f'<link rel="stylesheet" href="/static/graph_v14_1.css?v={html.escape(version_label)}">'
    page = shell_html.replace("</head>", css_link + "</head>", 1)
    page += r'''
    <main class="gf-page" data-greenfield-contract="v14.1.3">
      <section class="gf-analysis-toolbar" aria-label="Analysezeitraum und Werkzeuge">
        <div class="gf-toolbar-title">
          <span class="gf-eyebrow">Graph Core V3</span>
          <strong>Analyse-Workspace</strong>
          <button type="button" class="gf-info" data-gf-info="workspace" aria-label="Info zum Analyse-Workspace">i</button><button type="button" class="gf-layout-reset" id="gfResetLayout" title="Lane-Reihenfolge und Einklappzustand zurücksetzen">Layout zurücksetzen</button>
        </div>
        <div class="gf-toolbar-controls">
          <div class="gf-preset-row" role="group" aria-label="Zeitraum">
            <button type="button" class="gf-chip" data-gf-preset="2h">2 h</button>
            <button type="button" class="gf-chip" data-gf-preset="6h">6 h</button>
            <button type="button" class="gf-chip is-active" data-gf-preset="24h">24 h</button>
            <button type="button" class="gf-chip" data-gf-preset="48h">48 h</button>
            <button type="button" class="gf-chip" id="gfCustomToggle">Benutzerdefiniert</button>
          </div>
          <button type="button" class="gf-chip" id="gfSelectMode" aria-pressed="false">Bereich markieren</button>
          <button type="button" class="gf-button compact" id="gfRefresh">Aktualisieren</button>
        </div>
        <div class="gf-toolbar-status">
          <span id="gfRuntimeBadge" class="gf-badge neutral">History wird geprüft…</span>
          <span id="gfLoadBadge" class="gf-badge neutral">noch keine Daten</span>
          <span id="gfBusyBadge" class="gf-busy-badge" hidden><span class="gf-spinner" aria-hidden="true"></span><span id="gfBusyText">Ansicht wird geladen…</span></span>
        </div>
        <div class="gf-custom-range" id="gfCustomRange" hidden>
          <label>Von <input id="gfFrom" type="datetime-local"></label>
          <label>Bis <input id="gfTo" type="datetime-local"></label>
          <button type="button" class="gf-button compact" id="gfApplyRange">Anwenden</button>
        </div>
        <div class="gf-selection-bar" id="gfSelectionBar" hidden>
          <span><strong>Markierter Bereich:</strong> <span id="gfSelectionSummary">—</span></span>
          <button type="button" class="gf-button compact" id="gfZoomSelection">Auf Auswahl zoomen</button>
          <button type="button" class="gf-button compact secondary" id="gfCompareSelection">Auswahl vergleichen</button>
          <button type="button" class="gf-button compact ghost" id="gfClearSelection">Löschen</button>
          <button type="button" class="gf-info" data-gf-info="selection" aria-label="Info zur Bereichsmarkierung">i</button>
        </div>
      </section>

      <section id="gfGlobalNotice" class="gf-notice" hidden></section>

      <section class="gf-three-column" aria-label="Graph-Arbeitsbereich">
        <aside class="gf-left-rail" aria-label="Untersuchung auswählen">
          <div class="gf-panel-head">
            <div>
              <span class="gf-kicker">Untersuchung</span>
              <h2>Was möchtest du verstehen?</h2>
            </div>
          </div>
          <nav class="gf-investigation-list" id="gfInvestigationList">
            <button type="button" class="gf-investigation is-active" data-gf-investigation="grid">
              <strong>Netzregelung verstehen</strong>
              <span>Netz, Speicherwirkung und Reglerziel gemeinsam betrachten.</span>
            </button>
            <button type="button" class="gf-investigation" data-gf-investigation="storage">
              <strong>Speicher verstehen</strong>
              <span>Leistung, SOC und historische Grenzen synchron lesen.</span>
            </button>
            <button type="button" class="gf-investigation" data-gf-investigation="control">
              <strong>Regelentscheidung verfolgen</strong>
              <span>Zielwertpipeline und Zustände bis zum finalen Sollwert.</span>
            </button>
            <button type="button" class="gf-investigation" data-gf-investigation="free">
              <strong>Freies Lagebild</strong>
              <span>Beliebige verfügbare Reihen kombinieren.</span>
            </button>
          </nav>

          <div id="gfFreeSeries" class="gf-free-series" hidden>
            <div class="gf-section-label">Serien</div>
            <input id="gfSeriesSearch" class="gf-search" type="search" placeholder="Reihe suchen…" autocomplete="off">
            <div id="gfSeriesList" class="gf-series-list"></div>
          </div>

          <div class="gf-left-meta">
            <div class="gf-section-label">Aktive Ansicht</div>
            <div id="gfViewSummary" class="gf-summary">Netzregelung verstehen · 24 h</div>
            <div id="gfCoverageSummary" class="gf-quality-stack"></div>
          </div>
        </aside>

        <section class="gf-temporal-workspace" aria-label="Synchronisierte Zeitspuren">
          <article class="gf-lane gf-lane-power" data-gf-lane="power">
            <header class="gf-lane-head">
              <div class="gf-heading-with-info"><div><span class="gf-kicker" id="gfPowerKicker">Leistung</span><h2 id="gfPowerTitle">Leistungsfluss &amp; Regelziel</h2></div><button type="button" class="gf-info" data-gf-info="cursor" aria-label="Info zum synchronen Cursor">i</button></div>
              <div class="gf-lane-head-right"><div id="gfPowerLegend" class="gf-inline-legend" aria-label="Legende"></div><div class="gf-lane-tools" aria-label="Lane anordnen"><button type="button" data-gf-lane-move="up" aria-label="Lane nach oben">↑</button><button type="button" data-gf-lane-move="down" aria-label="Lane nach unten">↓</button><button type="button" data-gf-lane-toggle aria-expanded="true" aria-label="Lane einklappen">▾</button></div></div>
            </header>
            <div class="gf-lane-body">
              <div class="gf-chart-wrap gf-chart-large" data-gf-main-chart="power">
                <canvas id="gfPowerChart"></canvas>
                <div id="gfPowerCursorCard" class="gf-cursor-card" hidden></div>
                <div id="gfPowerEmpty" class="gf-empty" hidden>Im gewählten Zeitraum sind für diese Ansicht keine Leistungswerte verfügbar.</div>
              </div>
            </div>
            <div class="gf-lane-busy" hidden><span class="gf-spinner"></span><span>Daten werden geladen…</span></div>
          </article>

          <article class="gf-lane gf-lane-soc" data-gf-lane="soc">
            <header class="gf-lane-head">
              <div><span class="gf-kicker" id="gfSocKicker">Speicher</span><h2 id="gfSocTitle">SOC &amp; historische Grenzen</h2></div>
              <div class="gf-lane-head-right"><div id="gfSocLegend" class="gf-inline-legend" aria-label="Legende"></div><div class="gf-lane-tools" aria-label="Lane anordnen"><button type="button" data-gf-lane-move="up" aria-label="Lane nach oben">↑</button><button type="button" data-gf-lane-move="down" aria-label="Lane nach unten">↓</button><button type="button" data-gf-lane-toggle aria-expanded="true" aria-label="Lane einklappen">▾</button></div></div>
            </header>
            <div class="gf-lane-body">
              <div class="gf-chart-wrap gf-chart-medium" data-gf-main-chart="soc">
                <canvas id="gfSocChart"></canvas>
                <div id="gfSocCursorCard" class="gf-cursor-card" hidden></div>
                <div id="gfSocEmpty" class="gf-empty" hidden>Keine SOC-Daten im sichtbaren Zeitraum.</div>
              </div>
            </div>
            <div class="gf-lane-busy" hidden><span class="gf-spinner"></span><span>Daten werden geladen…</span></div>
          </article>

          <article class="gf-lane gf-lane-state" data-gf-lane="state">
            <header class="gf-lane-head">
              <div class="gf-heading-with-info"><div><span class="gf-kicker" id="gfStateKicker">Controller</span><h2 id="gfStateTitle">Zustände &amp; Ereignisse</h2></div><button type="button" class="gf-info" data-gf-info="states" aria-label="Info zu Zuständen und Ereignissen">i</button></div>
              <div class="gf-lane-head-right"><span class="gf-help">Modus, Intent, Grund und Commands auf derselben Zeitachse</span><div class="gf-lane-tools" aria-label="Lane anordnen"><button type="button" data-gf-lane-move="up" aria-label="Lane nach oben">↑</button><button type="button" data-gf-lane-move="down" aria-label="Lane nach unten">↓</button><button type="button" data-gf-lane-toggle aria-expanded="true" aria-label="Lane einklappen">▾</button></div></div>
            </header>
            <div class="gf-lane-body">
              <div class="gf-state-wrap">
                <div id="gfStateHoverPanel" class="gf-state-hover-panel" hidden>
                  <div id="gfStateMagnifier" class="gf-state-magnifier"></div>
                  <div id="gfStateCursorCard" class="gf-cursor-card gf-state-card" hidden></div>
                </div>
                <div id="gfStateTimeline" class="gf-state-timeline" aria-label="Zustands-Timeline"></div>
              </div>
            </div>
            <div class="gf-lane-busy" hidden><span class="gf-spinner"></span><span>Zustände werden geladen…</span></div>
          </article>

          <section id="gfComparisonArea" class="gf-comparison-area" data-gf-lane="comparison" aria-label="Vergleichswerkzeuge">
            <header class="gf-comparison-head">
              <div class="gf-heading-with-info"><div><span class="gf-kicker">Vergleich</span><h2>Verläufe vergleichen</h2></div><button type="button" class="gf-info" data-gf-info="comparison" aria-label="Info zu Vergleichsfunktionen">i</button></div>
              <div class="gf-lane-head-right"><div class="gf-comparison-switches">
                <div class="gf-segmented" role="group" aria-label="Vergleichstyp">
                  <button type="button" id="gfComparePeriodsMode" class="is-active">Zeiträume</button>
                  <button type="button" id="gfCompareEpisodesMode">Episoden t=0</button>
                </div>
                <div class="gf-segmented" role="group" aria-label="Vergleichsdarstellung">
                  <button type="button" id="gfCompareSide" class="is-active">Nebeneinander</button>
                  <button type="button" id="gfCompareOverlay">Überlagert</button>
                </div>
              </div><div class="gf-lane-tools" aria-label="Lane anordnen"><button type="button" data-gf-lane-move="up" aria-label="Lane nach oben">↑</button><button type="button" data-gf-lane-move="down" aria-label="Lane nach unten">↓</button><button type="button" data-gf-lane-toggle aria-expanded="true" aria-label="Lane einklappen">▾</button></div></div>
            </header>
            <div class="gf-lane-body">

            <div id="gfPeriodCompareControls" class="gf-compare-controls">
              <div class="gf-period-block">
                <strong>Zeitraum A</strong>
                <label>Von <input id="gfPeriodAFrom" type="datetime-local"></label>
                <label>Bis <input id="gfPeriodATo" type="datetime-local"></label>
              </div>
              <div class="gf-period-block">
                <strong>Zeitraum B</strong>
                <label>Von <input id="gfPeriodBFrom" type="datetime-local"></label>
                <label>Bis <input id="gfPeriodBTo" type="datetime-local"></label>
              </div>
              <div class="gf-compare-actions">
                <button type="button" class="gf-button compact secondary" id="gfPeriodCurrentToA">Aktueller Zeitraum → A</button>
                <button type="button" class="gf-button compact secondary" id="gfPeriodPreviousDay">A − 24 h → B</button>
                <button type="button" class="gf-button compact" id="gfLoadPeriodComparison">Zeiträume vergleichen</button>
              </div>
            </div>

            <div id="gfEpisodeCompareControls" class="gf-compare-controls gf-episode-controls" hidden>
              <div class="gf-episode-guide"><strong>Ereignisreaktionen vergleichen</strong><span>Wähle zwei vergleichbare Trigger. Beide Verläufe werden relativ zum jeweiligen Ereignis bei <b>t=0</b> ausgerichtet.</span></div>
              <div class="gf-episode-filter"><label class="gf-field">Trigger filtern<input id="gfTriggerSearch" type="search" placeholder="z. B. DISCHARGE, Nachtmodus, Publish"></label><label class="gf-field">Typ<select id="gfTriggerKindFilter"><option value="ALL">Alle Trigger</option></select></label></div>
              <label class="gf-field">Episode A<select id="gfTriggerA"></select></label>
              <label class="gf-field">Episode B<select id="gfTriggerB"></select></label>
              <div class="gf-two-fields">
                <label class="gf-field">vor t=0 (min)<input id="gfBeforeMin" type="number" min="0" value="15"></label>
                <label class="gf-field">nach t=0 (min)<input id="gfAfterMin" type="number" min="1" value="45"></label>
              </div>
              <div class="gf-compare-actions">
                <span id="gfTriggerBadge" class="gf-badge neutral">Trigger laden…</span>
                <button type="button" id="gfSimilarTriggerB" class="gf-button compact secondary">Ähnlichen Trigger für B wählen</button>
                <button type="button" id="gfLoadEpisodeComparison" class="gf-button compact">Episoden vergleichen</button>
              </div>
            </div>

            <div id="gfComparisonEmpty" class="gf-comparison-empty">Wähle zwei Zeiträume oder zwei Ereignisse. Die Ergebnisse erscheinen hier direkt unter den synchronen Hauptspuren.</div>
            <div id="gfCompareHoverCard" class="gf-compare-hover-card" hidden></div>
            <div id="gfCompareSideView" class="gf-compare-side" hidden>
              <section class="gf-compare-period-panel">
                <div class="gf-compare-caption" id="gfCompareCaptionA">A</div>
                <div class="gf-chart-wrap gf-chart-small"><canvas id="gfComparePowerA"></canvas></div>
                <div class="gf-chart-wrap gf-chart-mini"><canvas id="gfCompareSocA"></canvas></div>
              </section>
              <section class="gf-compare-period-panel">
                <div class="gf-compare-caption" id="gfCompareCaptionB">B</div>
                <div class="gf-chart-wrap gf-chart-small"><canvas id="gfComparePowerB"></canvas></div>
                <div class="gf-chart-wrap gf-chart-mini"><canvas id="gfCompareSocB"></canvas></div>
              </section>
            </div>
            <div id="gfCompareOverlayView" class="gf-compare-overlay" hidden>
              <div class="gf-chart-wrap gf-chart-small"><canvas id="gfComparePowerOverlay"></canvas></div>
              <div class="gf-chart-wrap gf-chart-mini"><canvas id="gfCompareSocOverlay"></canvas></div>
            </div>
            </div>
            <div class="gf-lane-busy" hidden><span class="gf-spinner"></span><span>Vergleich wird geladen…</span></div>
          </section>
        </section>

        <aside class="gf-context-panel" id="gfContextPanel" aria-label="Kontext und Inspector">
          <div class="gf-context-mobile-head">
            <strong>Kontext</strong>
            <button type="button" id="gfCloseContext" aria-label="Kontext schließen">×</button>
          </div>
          <div class="gf-context-tabs" role="tablist">
            <button type="button" class="is-active" data-gf-context-tab="inspector">Inspector</button>
            <button type="button" data-gf-context-tab="command">Command</button>
            <button type="button" data-gf-context-tab="quality">Daten</button>
          </div>

          <section class="gf-context-body is-active" data-gf-context-body="inspector">
            <div class="gf-context-title"><span class="gf-kicker">Cursor</span><h2>Regler-Inspector</h2><span id="gfInspectorTime" class="gf-badge neutral">kein Punkt gewählt</span></div>
            <div id="gfInspectorEmpty" class="gf-context-empty">Klicke in einen Graphen oder eine Zustandsspur. Alle Lanes bleiben dabei zeitlich synchron.</div>
            <div id="gfInspectorContent" hidden>
              <div class="gf-inspector-section"><h3>Messwerte</h3><div id="gfInspectorMeasurements" class="gf-kv-list"></div></div>
              <div class="gf-inspector-section"><h3>Zielwertpipeline</h3><div id="gfInspectorPipeline" class="gf-kv-list"></div></div>
              <div class="gf-inspector-section"><h3>Zustände</h3><div id="gfInspectorStates" class="gf-kv-list"></div></div>
              <div class="gf-inspector-section"><h3>Historische Config</h3><div id="gfInspectorConfig" class="gf-kv-list"></div></div>
              <div class="gf-inspector-section"><h3>Entities / Topologie</h3><div id="gfInspectorEntities" class="gf-kv-list"></div></div>
              <div id="gfInspectorCommandLink"></div>
            </div>
          </section>

          <section class="gf-context-body" data-gf-context-body="command">
            <div class="gf-context-title"><span class="gf-kicker">Ursache / Wirkung</span><h2>Command-Follow</h2><button type="button" class="gf-info" data-gf-info="command" aria-label="Info zu Command-Follow">i</button><span id="gfCommandBadge" class="gf-badge neutral">kein Command</span></div>
            <div id="gfCommandEmpty" class="gf-context-empty">Wähle im Inspector einen korrelierten Publish-Event oder einen Publish in der Ereignisspur.</div>
            <div id="gfCommandContent" hidden>
              <div id="gfCommandSummary" class="gf-kv-list"></div>
              <div id="gfCommandLegend" class="gf-inline-legend gf-command-legend" aria-label="Command-Legende"></div>
              <div class="gf-chart-wrap gf-chart-context"><canvas id="gfCommandChart"></canvas><div id="gfCommandCursorCard" class="gf-cursor-card" hidden></div></div>
              <div id="gfCommandEvidence" class="gf-callout"></div>
            </div>
          </section>

          <section class="gf-context-body" data-gf-context-body="quality">
            <div class="gf-context-title"><span class="gf-kicker">Coverage / Evidence</span><h2>Datenqualität</h2><button type="button" class="gf-info" data-gf-info="evidence" aria-label="Info zur Datenqualität">i</button></div>
            <div id="gfQualitySummary" class="gf-quality-summary"></div><div id="gfQualityContent" class="gf-quality-list"></div>
            <p class="gf-help">Measurement V4 ist keine Laufzeitvoraussetzung. Fehlende Instrumentierung, echte Datenlücken und Retention werden getrennt ausgewiesen.</p>
          </section>
        </aside>
      </section>

      <button type="button" id="gfMobileContextButton" class="gf-mobile-context-button" aria-label="Inspector öffnen">Inspector</button>
      <div id="gfInfoPopover" class="gf-info-popover" role="tooltip" hidden></div>
    </main>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="/static/graph_v14_1.js?v=''' + html.escape(version_label) + r'''" defer></script>
    '''
    return page
