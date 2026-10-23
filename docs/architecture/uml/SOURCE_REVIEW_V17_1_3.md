# ZEC UML-Regleratlas – fachliche Source- und visuelle Einzelprüfung V17.1.3

**Reviewstand:** 22.10.2026, technischer Buildreview der V17.1.3-Kandidatenquellen (keine Pi-Feldfreigabe).
**Scope:** alle 19 historischen V0.4-Blätter und 3 neue, DOT als verlässliche editierbare Quelle; PlantUML historisch/unverifiziert.

## Reproduzierbare Sourceanker

- `S3_TIME_CONSUMED`: **PASS** (Quelltext-Invariante auf realem Releasekandidaten, keine Simulation physischer Wirkung)
- `S3_TIME_OPERATIONAL`: **PASS** (Quelltext-Invariante auf realem Releasekandidaten, keine Simulation physischer Wirkung)
- `SEASON_OPT_IN`: **PASS** (Quelltext-Invariante auf realem Releasekandidaten, keine Simulation physischer Wirkung)
- `FAST_A400_R100`: **PASS** (Quelltext-Invariante auf realem Releasekandidaten, keine Simulation physischer Wirkung)
- `FAST_NEAR_LIMIT`: **PASS** (Quelltext-Invariante auf realem Releasekandidaten, keine Simulation physischer Wirkung)
- `SAFE_CROSS_CHARGE`: **PASS** (Quelltext-Invariante auf realem Releasekandidaten, keine Simulation physischer Wirkung)
- `STATUS_1S`: **PASS** (Quelltext-Invariante auf realem Releasekandidaten, keine Simulation physischer Wirkung)
- `MINI_3S`: **PASS** (Quelltext-Invariante auf realem Releasekandidaten, keine Simulation physischer Wirkung)
- `GRID_STALE_DEBOUNCE`: **PASS** (Quelltext-Invariante auf realem Releasekandidaten, keine Simulation physischer Wirkung)
- `GRID_STALE_CLASSIFICATION`: **PASS** (Quelltext-Invariante auf realem Releasekandidaten, keine Simulation physischer Wirkung)
- `CONTROLLER_LOCK`: **PASS** (Quelltext-Invariante auf realem Releasekandidaten, keine Simulation physischer Wirkung)
- `NIGHT_MIN_SOC`: **PASS** (Quelltext-Invariante auf realem Releasekandidaten, keine Simulation physischer Wirkung)
- `PROVENANCE_MARKER`: **PASS** (Quelltext-Invariante auf realem Releasekandidaten, keine Simulation physischer Wirkung)

## Sicht- und Fachprüfung aller Blätter

22 PNG-Darstellungen in sechs Reviewbögen auf Struktur, Lesbarkeit, Beschneidung und offensichtliche Kontradiktionen geprüft; Detailbeschriftungen zusätzlich in Original-DOT gelesen, SVG bleibt ohne externen Renderer verlustfrei zoombar. Sehr breite Diagramme sind als Overview nicht kleinformatig druckbar; die Hauptnutzung ist die skalierbare SVG-Einzelansicht. Das ist ein Layout-Limit, kein fehlender Inhalt.

| ID | Fachlich abgeglichen gegen | Entscheidung |
|---|---|---|
| 01 | controller_logic.py::run_once, state.py::ControllerState | PASS: Betriebsmodi von S3-Strategie und Diagnoseereignis getrennt |
| 02 | controller_logic.py::run_once, controller_logic.py::handle_night_mode | PASS: Night-MIN_SOC bei frischem Export kein Early-Return vor AUTO |
| 03 | controller_logic.py::_harvest_time_profile, controller_logic.py::_s3_season_policy, controller_logic.py::handle_charge | PASS: Baseline B, Harvest und Fast O getrennt; Strategie dem Capture-Floor nachgeordnet |
| 04 | controller_logic.py::_harvest_time_profile, controller_logic.py::update_rest_surplus_harvest_state | PASS: Harvest-Eligibility, Confirm, Hold und neue Zeitprofile |
| 05 | controller_logic.py::handle_charge, state.py::ControllerState | PASS: Fast Capture eigenständige Overlay-Schicht, FULL_IDLE/NEAR_LIMIT, W/s |
| 06 | controller_logic.py::handle_charge, controller_logic.py::_apply_symmetric_cross_charge_limit | PASS: Signed Cross-Charge in beiden Richtungen, kein Richtungsüberschwingen |
| 07 | command_lifecycle.py, controller_logic.py::_publish_signed_target | PASS: Command-Demand, Readback und Wirkung getrennt; Neutralisierung aktiv |
| 08 | command_lifecycle.py, controller_logic.py::run_once | PASS: Command-Effect-Transitionen; Recovery nicht mit Publish gleichsetzen |
| 09 | controller_logic.py, web_ui.py::build_grid_mini_payload, operational_events.py | PASS: Quell-/Regel-/Command-/Diagnosearchitektur; usable Primär-SOC nur Diagnose |
| 10 | controller_logic.py::run_once, controller_logic.py::handle_discharge | PASS: Manual/Night/AUTO und globales MIN_SOC ohne Exportladeblock |
| 11 | controller_logic.py::handle_charge | PASS: Exportzweig, Baseline-Glättung, Ramp und O erst danach |
| 12 | controller_logic.py::handle_discharge | PASS: Importzweig, Rückrichtungssperre, MIN_SOC und Cross-Charge |
| 13 | controller_logic.py::_harvest_time_profile, controller_logic.py::handle_charge | PASS: Harvest SMA_FULL_OR_IDLE und Fast FULL_IDLE mit unterschiedlichen Kriterien |
| 14 | controller_logic.py::handle_charge, controller_logic.py::_s3_season_policy | PASS: Harvest NEAR_LIMIT und Fast NEAR_LIMIT mit unterschiedlicher Reserve |
| 15 | controller_logic.py::run_once, controller_logic.py::handle_charge | PASS: Prioritäten/Overrides lokal statt global linear, S3 nachrangig |
| 16 | controller_logic.py::_harvest_time_profile, controller_logic.py::_s3_season_policy | PASS: Frische Beobachtungen, Harvest-Profile konfigurierbar und Fast-Zeitsemantik |
| 17 | controller_logic.py::handle_charge | PASS: didaktische B-/O-Werte ausdrücklich nicht als reale Feldwirkung ausgeben |
| 18 | state.py::ControllerState, controller_logic.py::_s3_season_policy | PASS: Status/Rechnung/Wirkung/Recovery und STRATEGIC_SHARE nur Rechenprovenienz |
| 19 | controller_logic.py::_harvest_time_profile, controller_logic.py::_s3_season_policy | PASS: konfigurierbare Tagesprofilfenster & Confirm statt hart codierter TARGET_ONLY-Altbehauptung |
| 20 | controller_logic.py::_s3_season_policy, controller_logic.py::_s3_calendar_parallel | PASS: S3 requested/effective, Calendar-Jahreswechsel und opt-in |
| 21 | static/status_v2.js, web_ui.py::build_grid_mini_payload, operational_events.py | PASS: 1-s Browser-Livepoll, 3-s Mini-Chart-Poll, unveränderter Reglerzyklus |
| 22 | operational_events.py, state.py | PASS: Grid-Stale-Diagnose mit 6-/4-s Entprellung, kein Regelmodus |

## Behobene Review-Findings

1. Blatt 19: Alte Behauptung fester Tagesprofilzeiten und `TARGET_ONLY` war anhand `_harvest_time_profile(cfg)` und `settings_registry.py` widerlegt. Korrigiert: die vier operativen HH:MM-Grenzen werden gelesen, Default 09:30/11:30/14:30/18:00, ungültige Reihenfolge fällt auf Defaults zurück; Confirm pro Profil ebenfalls konfigurierbar. DOT/SVG/PNG neu gerendert und gehast.
2. Blatt 17: Alttext „Active weiterhin nicht freigegeben“ widersprach dokumentierter früherer Active-NEAR_LIMIT-Feldevidenz. Korrigiert: Active-NEAR_LIMIT im Vorgänger beobachtet, belastbare FULL_IDLE-Episode noch offen. Kein neuer Real-Pi-Nachweis behauptet.
3. Die korrekte Trennung `STRATEGIC_SHARE` (Rechen-/Auswahlmarker) vs `current_mode` ist in Blättern 18/19 beibehalten.
4. Historische `.puml`-Sekundärquellen bleiben ausdrücklich `SECONDARY_UNVERIFIED`; ihre bloße Existenz ist kein Renderer-PASS.

## Grenzen und Abnahme

- Fachliche Sourcekonsistenz und technische/visuelle Dokumentenlesbarkeit: **PASS** für vorliegende V17.1.3-Sources und 22 Diagramme.
- Physische S3-/Fast-Capture-FULL_IDLE-/Grid-Stale-Naturepisoden bleiben getrennte `EVIDENCE_PENDING` und werden durch dieses Review nicht freigegeben.
- Die V17.1.3-Releasegates für gesamte Regression, frische Paketbytes, Deployment und Datenblatt müssen separat PASS sein.
