# ZEC V18.0.1 – manueller UML-Quellen- und Bildreview

**Reviewzeitpunkt:** 02.11.2026. **Quellidentität:** V18.0.1 / `v18.0.1-20261102`.
**Umfang:** 22/22 versionierte DOT-/SVG-/PNG-Diagramme. Dies ist ein fachlicher As-built-Diagrammreview, keine Produkt-/Hardware-/Installerfreigabe.

## Methode und Grenzen

1. Die aktuellen DOT-/SVG-/PNG-Dateien wurden mit Graphviz gerendert und als vollständiger Satz von 22 Bildern visuell kontrolliert (Diagrammfluss, Knoten/Edges, keine offensichtlich fehlenden/überlagerten Bildinhalte).
2. Der Reviewer hat die sourcegebundenen Controller-, Care-, Command-, Measurement-, UI-/Diagnose-Pfade aus dem tatsächlich versionierten Kandidaten geprüft und die 22 Trace-Symbole gegen die aktuellen Dateien und Python-AST abgeglichen.
3. Sicherheitskritische Sonderfälle wurden gesondert geprüft: 01/02/10 Nacht-SOC-Stale mit neuem SAFE_STATE→HOLD-Guard; 03/05 PV- versus Fast-Capture-Ziel; 06 Cross-Charge; 08/09/18 Journal-/Command-Evidence; 16 echte Zyklusmarker; 21 Statuspoll nicht gleich Messrate.
4. Alte V17.1.3 und CP26-Claims sind historisch unter `CHANGE_IMPACT.md` erhalten; die gerenderten aktuellen Blätter tragen V18.0.1 und differenzieren Reserve-Wirkung (zwei natürliche Episoden), PV-Teilbeobachtung und weiterhin nicht evaluierte Netzpflege/Notladung.
5. Weder dieser Review noch die synthetischen Tests belegen eine Freigabe für Netzlade-/Notlade-Wirkung, einen echten Pi-Installations-PASS oder `PRODUCTIVE_PASS`.

## Individueller Diagramm-Review

| ID | Diagramm | Source-Trace | Fachentscheidung / Prüfung | Ergebnis |
|---|---|---|---|---|
| 01 | `01_CONTROLLER_STATE_MACHINE` | `controller_logic.py::run_once` | SAFE_STATE, STOP, manual, Night und AUTO bleiben getrennte Zustände; Battery Care bleibt Policy, nicht zweiter Modus. Recovery verlangt SOC/Grid fresh und neutralen Readback/Ist. | `SOURCE_REVIEW_PASS` |
| 02 | `02_CONTROL_CYCLE_ACTIVITY` | `controller_logic.py::run_once` | run_once priorisiert Safety/Telemetrie vor AUTO. Care-Nacht-R bei importnahem Netz führt zur 0-W-Grenze; stale->HOLD nur nach physischer Neutralität. | `SOURCE_REVIEW_PASS` |
| 03 | `03_CHARGE_TARGET_PIPELINE` | `battery_care_pv_allocation.py::allocate_care_pv` | Care-PV-Target ist absolut und unterliegt dem bestehenden Publisher/Import-Guard. Kein B+Overlay-Doppelzählen. | `SOURCE_REVIEW_PASS` |
| 04 | `04_HARVEST_STATE_MACHINE` | `controller_logic.py::update_rest_surplus_harvest_state` | Harvest Entry/Stay/Exit bleibt orthogonal zur zusätzlichen Care-Priorität. | `SOURCE_REVIEW_PASS` |
| 05 | `05_FAST_CAPTURE_STATE_MACHINE` | `controller_logic.py::handle_charge` | Fast-Capture-Stufen bezeichnen Overlay/Shadow/Off mit eigenständigen Guards; Care-PV wird nicht zusätzlich als Fast-Overlay addiert. | `SOURCE_REVIEW_PASS` |
| 06 | `06_CROSS_CHARGE_ACTIVITY` | `controller_logic.py::_apply_symmetric_cross_charge_limit` | Primärspeicher-Cross-Charge-Veto schützt normal; eingeschränkte Notlade-Ausnahme bleibt economic-only und unter Hardware-Safety. | `SOURCE_REVIEW_PASS` |
| 07 | `07_COMMAND_LIFECYCLE_SEQUENCE` | `command_lifecycle.py` | Command Lifecycle bleibt einziger Owner; Desired/Readback und Gerätewirkung bleiben unterschiedliche Gates. | `SOURCE_REVIEW_PASS` |
| 08 | `08_COMMAND_EFFECT_RECOVERY_STATE` | `operational_events.py::_observe_battery_care_incident` | Notlade-Command-Mismatch ist persistenter Incident, mit Fehler-/Retrypfad; Entladeschutz-Recovery verlangt 0-W-Beobachtung. | `SOURCE_REVIEW_PASS` |
| 09 | `09_COMPONENT_MAP` | `operational_events.py::_observe_care_reserve_reached` | ControllerState, Measurement, Status und EventJournal sind getrennt; neues Schutzreserve-Episodenjournal trennt 0-W-Anforderung von Bestätigung. | `SOURCE_REVIEW_PASS` |
| 10 | `10_DISCHARGE_NIGHT_MANUAL_PATHS` | `controller_logic.py::_battery_care_reserve_soc` | Nachtreserve, global MIN_SOC und Battery-Care-R sind getrennte Schwellen, Care R verhindert erneute Entladung und erlaubt neutralen Recovery ohne Bypass. | `SOURCE_REVIEW_PASS` |
| 11 | `11_AUTO_GRID_EXPORT_DETAIL` | `controller_logic.py::handle_charge` | AUTO_GRID_EXPORT verwendet weiterhin Baseline-, Clamp-, Ramp-/Cross-Charge-Guards; keine neue V18.0.1-Rechenformel. | `SOURCE_REVIEW_PASS` |
| 12 | `12_AUTO_GRID_IMPORT_DETAIL` | `controller_logic.py::handle_discharge` | AUTO_GRID_IMPORT bleibt SOC/Deadband-, Rampen- und Cross-Charge-gebunden; zusätzliche Care-R wirkt vorrangig. | `SOURCE_REVIEW_PASS` |
| 13 | `13_FULL_OR_IDLE_DEEP_DIVE` | `controller_logic.py::_harvest_time_profile` | Harvest FULL/IDLE und Fast FULL_IDLE bleiben unterschiedliche Strategiekonzepte; S3-Profilfenster sind konfigurierbar. | `SOURCE_REVIEW_PASS` |
| 14 | `14_NEAR_LIMIT_POWER_BALANCE` | `controller_logic.py::handle_charge` | Near-Limit-Exportkompensation, Baseline und Fast-Overlay bleiben unter Export-/Cross-Charge-Grenzen. | `SOURCE_REVIEW_PASS` |
| 15 | `15_PRIORITY_OVERRIDE_LAYERS` | `battery_care_policy.py::decide_care` | STOP und Safety stehen vor Care, danach Messungen, SOC, S3/Harvest und Publisher; kein neuer Safety-Override. | `SOURCE_REVIEW_PASS` |
| 16 | `16_TIMING_HYSTERESIS` | `battery_care_stage_events.py::observed_care_stage` | Stufenereignisse nur nach unterschiedlichen abgeschlossenen Controllerzyklen; reine UI-Polls sind keine neuen Stufeneintritte. | `SOURCE_REVIEW_PASS` |
| 17 | `17_RULE_CYCLE_MICROSCOPE` | `controller_logic.py::handle_charge` | Zahlenbeispiel NEAR_LIMIT ist didaktische Erklärung und kein universal festes Leistungsversprechen. | `SOURCE_REVIEW_PASS` |
| 18 | `18_REASON_LIMITER_PROVENANCE` | `battery_care_graph_history.py::care_day_incidents` | Care angefordert/gewähltes Command/Readback/physische Wirkung sowie Persistenz getrennt; Reason und Limiter dokumentieren Pfade. | `SOURCE_REVIEW_PASS` |
| 19 | `19_HIGH_SOC_STRATEGIC_SHARE_TIME_PROFILE` | `controller_logic.py::_harvest_time_profile` | Zeitprofile/High-SOC-Anteile sind aus Settings statt hardcoded; Export-Capture hat Vorrang. | `SOURCE_REVIEW_PASS` |
| 20 | `20_S3_POLICY_OPT_IN` | `controller_logic.py::_s3_season_policy` | S3 requested/effective/applicability bleibt opt-in und eigenständige Strategiediagnose, nicht Care-Regelmodus. | `SOURCE_REVIEW_PASS` |
| 21 | `21_LIVE_STATUS_VS_CONTROL` | `static/status_v2.js` | UI-Live-Poll 1000ms, Minigraph 3000ms, Controllerzyklen typischerweise 3s; Messzeitstempel bleiben unabhängig. | `SOURCE_REVIEW_PASS` |
| 22 | `22_GRID_STALE_EVENT` | `operational_events.py` | Grid-Stale-Open/Resolve ist diagnostisches Ereignis und überschreibt keinen Betriebsmodus/Command-Owner. | `SOURCE_REVIEW_PASS` |

## Integrität / Releasegrenzen

- Alle 22 aktuellen Manifest-SHA256 für DOT, SVG und PNG wurden bytegenau geprüft. Die aktuellen SHA256 stehen im Manifest sowie im V18.0.1-Anhang von `RELEASE_TRACEABILITY.md`.
- Die Diagramm-Reviewfreigabe ist **keine** Abkürzung für `ZEC_BUILD_EVIDENCE_V1`, vollständige Versionstests, `V18_0_1_SOURCE_MANIFEST.sha256`, Releaseinstaller-/Rollback-Gates oder Pi-Feldabnahme.
- Alle 85 historisch versionsspezifisch ausgenommenen Tests sind weiterhin im Sourcebaum vorhanden; dies ist ein gesondertes QA-/Applikabilitäts-Thema, keine UML-Freigabe.
