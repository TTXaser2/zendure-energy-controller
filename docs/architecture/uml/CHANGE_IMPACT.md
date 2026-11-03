# UML Change-Impact – Abgleich V17.1.3 – Source- und Visualreview abgeschlossen

**Reviewstatus:** technische Zuordnung / visuelle und fachliche Source-Endabnahme PASS; releasebezogene QA folgt. Altdiagramme gegen V17.0.2, neuer Sourcebezug V17.1.3.

| ID | Status | Prüfthema und Entscheidung | Fachreview |
|---|---|---|---|
| 01 | UPDATED | S3 ist kein eigener current_mode; Grid-Stale ist Ereignis. | `SOURCE_REVIEW_PASS` |
| 02 | UPDATED | NIGHT/MIN_SOC entkoppelt fixe Entladung von zulässiger Grid-Verarbeitung. | `SOURCE_REVIEW_PASS` |
| 03 | UPDATED | S3-Saisonwirkung gilt nur bei opt-in und ist nachrangig zum Export-Capture-Floor. | `SOURCE_REVIEW_PASS` |
| 04 | UPDATED | Profil/Bestätigungsdauer sind konfigurierbare S3-Werte. | `SOURCE_REVIEW_PASS` |
| 05 | REVIEWED_UNCHANGED | V17.1.3 Sourceconsumer weiterhin unter Schutzinvarianten; keine zusätzliche UML-Änderung abgeleitet. | `SOURCE_REVIEW_PASS` |
| 06 | REVIEWED_UNCHANGED | V17.1.3 Sourceconsumer weiterhin unter Schutzinvarianten; keine zusätzliche UML-Änderung abgeleitet. | `SOURCE_REVIEW_PASS` |
| 07 | REVIEWED_UNCHANGED | V17.1.3 Sourceconsumer weiterhin unter Schutzinvarianten; keine zusätzliche UML-Änderung abgeleitet. | `SOURCE_REVIEW_PASS` |
| 08 | REVIEWED_UNCHANGED | V17.1.3 Sourceconsumer weiterhin unter Schutzinvarianten; keine zusätzliche UML-Änderung abgeleitet. | `SOURCE_REVIEW_PASS` |
| 09 | UPDATED | Getrennte 1-s-Live- und 3-s-Minigraph-Polls; Stale-Diagnose. | `SOURCE_REVIEW_PASS` |
| 10 | UPDATED | MIN_SOC blockiert Entladung, nicht die gesamte Netzverarbeitung. | `SOURCE_REVIEW_PASS` |
| 11 | REVIEWED_UNCHANGED | V17.1.3 Sourceconsumer weiterhin unter Schutzinvarianten; keine zusätzliche UML-Änderung abgeleitet. | `SOURCE_REVIEW_PASS` |
| 12 | REVIEWED_UNCHANGED | V17.1.3 Sourceconsumer weiterhin unter Schutzinvarianten; keine zusätzliche UML-Änderung abgeleitet. | `SOURCE_REVIEW_PASS` |
| 13 | UPDATED | Zeitprofil-Confirm ist konfigurierbar. | `SOURCE_REVIEW_PASS` |
| 14 | UPDATED | Saisonpolicy kann strategischen Share unterdrücken. | `SOURCE_REVIEW_PASS` |
| 15 | UPDATED | S3 nur Strategieebene, kein Safety-/Command-Override. | `SOURCE_REVIEW_PASS` |
| 16 | UPDATED | Runtimekonfigurierbare Zeitgrenzen anstelle der fixen Altuhrzeiten. | `SOURCE_REVIEW_PASS` |
| 17 | UPDATED | V17.1.3 Sourceconsumer weiterhin unter Schutzinvarianten; keine zusätzliche UML-Änderung abgeleitet. | `SOURCE_REVIEW_PASS` |
| 18 | UPDATED | S3 requested/effective und applicability als eigene Diagnosedimension. | `SOURCE_REVIEW_PASS` |
| 19 | UPDATED | S3 opt-in und konfigurierbare Tagesprofile ersetzen hardcoded-only-Altmodell. | `SOURCE_REVIEW_PASS` |
| 20 | NEW | Opt-in/Saisonpolicy gegenüber V0.4 erforderlich. | `SOURCE_REVIEW_PASS` |
| 21 | NEW | Sourcepoll vs. Regler- und Minigraph-Takt unterscheidbar. | `SOURCE_REVIEW_PASS` |
| 22 | NEW | Stale-Ereignis-Debounce und Controllerunabhängigkeit. | `SOURCE_REVIEW_PASS` |


## CP19 – Entwicklung / 26.10.2026 (keine Releasefreigabe)

- **08 UPDATED:** bestätigter Stufe-3-Notlade-Command-Effect-Mismatch → einmaliger synchroner Incident-Commit → OPEN/Recovery; kurze SQLite-Fehler-/Retry-Semantik ist nun sichtbar.
- **09 UPDATED:** OperationalEventJournal ist derselbe SQLite-Store; die seltene einmalige Write-through-Ausnahme zum sonst asynchronen Journal ist sichtbar. Kein neuer Publisher oder zweiter Controller-Owner.
- **01–07, 10–22 REVIEWED_UNCHANGED:** CP19 ändert keine zusätzlichen Regler-Branches, Geräte-/BMS-Commandlimits, Pollintervalle oder übrige fachliche Diagrammpfade. Dies ist ein Entwicklungsabgleich, **keine** erneute visuelle Vollabnahme oder technische Releasefreigabe.

## CP26 – Battery Care / 27.10.2026 (nur Development-Sourceabgleich)

Ausgang CP25: 22/22 Renderartefakte vorhanden, aber `CONTROLLER_SOURCE_MISMATCH` gegen veränderten Controllerkern; alte `SOURCE_REVIEW_PASS`-Einträge belegen nur V17.1.3-Basisreview. Nachstehende Entscheidungen sind **keine manuelle technische Releasefreigabe**.

| Blatt | CP26-Impact | Code-/Fachbezug | Gate |
|---|---|---|---|
| 01 | UPDATED | Policy: Care R schützt AUTO/NIGHT vor Entladung; STOP bleibt absolut. Stufe 1 PV, Stufe 2 Netzpflege, Stufe 3 Notladung bis Episode-R. Kein neuer current_mode. | `DEVELOPMENT_SOURCE_REVIEW_PENDING` |
| 02 | UPDATED | Care-Anforderung nur nach Safety-/Messfreigaben durch bestehenden Command-Owner. Abgeschlossener Zyklus markiert Stage-Provenienz; keine Beobachtungsabkürzung. | `DEVELOPMENT_SOURCE_REVIEW_PENDING` |
| 03 | UPDATED | Care-PV ist ABSOLUTES Ziel inklusive bereits physischer Zendure-Ladung, nicht B+Fast-Overlay. Care-Import-Backoff; Netzpflege/Notladung mit separatem Powercap. | `DEVELOPMENT_SOURCE_REVIEW_PENDING` |
| 04 | REVIEWED_UNCHANGED | keine unmittelbare Care-Diagrammpflicht im entsprechenden Altpfad; Source-Trace im Manifest weiterhin vorhanden | `DEVELOPMENT_SOURCE_REVIEW_PENDING` |
| 05 | UPDATED | Battery-Care-PV-Absolutziel und Fast-Capture-Overlay dürfen denselben Export NICHT doppelt allokieren. Normaler Baselinepfad nach Care-Exit erhalten. | `DEVELOPMENT_SOURCE_REVIEW_PENDING` |
| 06 | UPDATED | Einzige begrenzte Ausnahme: bestaetigte Care-NOTLADUNG umgeht wirtschaftliches Cross-Charge-Veto, nie Hardware-, BMS-, STOP-, SmartMode- oder Command-Safety. | `DEVELOPMENT_SOURCE_REVIEW_PENDING` |
| 07 | REVIEWED_UNCHANGED | keine unmittelbare Care-Diagrammpflicht im entsprechenden Altpfad; Source-Trace im Manifest weiterhin vorhanden | `DEVELOPMENT_SOURCE_REVIEW_PENDING` |
| 08 | UPDATED | Care-Notlade-Command-Mismatch: synchroner SQLite-Commit pro eindeutiger Failure-ID und ursprünglicher Reserve R; parallele offene Vorfälle unabhängig recoverbar. | `DEVELOPMENT_SOURCE_REVIEW_PENDING` |
| 09 | UPDATED | Care Module: pure Policy, PV-Arbiter, Grid-Beobachtung, persistente Episoden. OperationalEventJournal: mehrere Notladevorfälle und bestätigte Stage-Transition nach 2 abgeschlossenen Zyklen; SOC-Graph read-only. | `DEVELOPMENT_SOURCE_REVIEW_PENDING` |
| 10 | UPDATED | Care NIGHT-Untergrenze = max(MIN_SOC,R,ggf. höhere Nachtreserve). STOP hat Vorrang. Export-Laden bleibt bei Reservestop erlaubt. | `DEVELOPMENT_SOURCE_REVIEW_PENDING` |
| 11 | REVIEWED_UNCHANGED | keine unmittelbare Care-Diagrammpflicht im entsprechenden Altpfad; Source-Trace im Manifest weiterhin vorhanden | `DEVELOPMENT_SOURCE_REVIEW_PENDING` |
| 12 | REVIEWED_UNCHANGED | keine unmittelbare Care-Diagrammpflicht im entsprechenden Altpfad; Source-Trace im Manifest weiterhin vorhanden | `DEVELOPMENT_SOURCE_REVIEW_PENDING` |
| 13 | REVIEWED_UNCHANGED | keine unmittelbare Care-Diagrammpflicht im entsprechenden Altpfad; Source-Trace im Manifest weiterhin vorhanden | `DEVELOPMENT_SOURCE_REVIEW_PENDING` |
| 14 | REVIEWED_UNCHANGED | keine unmittelbare Care-Diagrammpflicht im entsprechenden Altpfad; Source-Trace im Manifest weiterhin vorhanden | `DEVELOPMENT_SOURCE_REVIEW_PENDING` |
| 15 | UPDATED | Priorität: STOP/Safety vor Care. PV-Umlenkung vor moderater Netzpflege; Notladung mit eng begrenzter wirtschaftlicher Cross-Charge-Ausnahme. Einheitlicher Publisher. | `DEVELOPMENT_SOURCE_REVIEW_PENDING` |
| 16 | UPDATED | Persistierte Care-Stufenmarker erst nach ZWEI unterschiedlichen abgeschlossenen Controllerzyklen. Ein einzelnes Statuspoll/SOC-Rauschen erzeugt kein Ereignis. | `DEVELOPMENT_SOURCE_REVIEW_PENDING` |
| 17 | REVIEWED_UNCHANGED | keine unmittelbare Care-Diagrammpflicht im entsprechenden Altpfad; Source-Trace im Manifest weiterhin vorhanden | `DEVELOPMENT_SOURCE_REVIEW_PENDING` |
| 18 | UPDATED | Evidenztrennung: Care-Policy/Shadow != gewähltes Commandziel != readback != physische AC-Wirkung. Stage-Marker belegen Zyklen, Notladefehler separate bestätigte Mismatches. | `DEVELOPMENT_SOURCE_REVIEW_PENDING` |
| 19 | REVIEWED_UNCHANGED | keine unmittelbare Care-Diagrammpflicht im entsprechenden Altpfad; Source-Trace im Manifest weiterhin vorhanden | `DEVELOPMENT_SOURCE_REVIEW_PENDING` |
| 20 | REVIEWED_UNCHANGED | keine unmittelbare Care-Diagrammpflicht im entsprechenden Altpfad; Source-Trace im Manifest weiterhin vorhanden | `DEVELOPMENT_SOURCE_REVIEW_PENDING` |
| 21 | UPDATED | Care-Status und historische Graph-Marker verwenden belegte abgeschlossene Reglerzyklen und persistierte Events; 1-s-Browserpoll ist KEIN 1-s-Physiksample. | `DEVELOPMENT_SOURCE_REVIEW_PENDING` |
| 22 | REVIEWED_UNCHANGED | keine unmittelbare Care-Diagrammpflicht im entsprechenden Altpfad; Source-Trace im Manifest weiterhin vorhanden | `DEVELOPMENT_SOURCE_REVIEW_PENDING` |

## V18.0.1 Korrekturscope – Quelländerungen, fachliche Nachprüfung OFFEN

01 und 02: `controller_logic.py` Nacht-SOC-Stale-Battery-Care-Reserve SAFE_STATE→HOLD neu nur nach neutralem Ist/Readback. 07/08/09 (je nach Atlasbelegung) Command-/Safety-Readback auf geänderten Pfad prüfen; `operational_events.py` Schutzreserve-Journal als eigener Diagnosepfad, keine Hardwareänderung. Status/Settings/Diagnose mit dem Realstand V18.0.1 abgleichen. Die übrigen 22 Blätter bleiben bis zur tatsächlichen individuellen fachlichen Prüfung Entwicklungsstände, nicht `SOURCE_REVIEW_PASS`.

## V18.0.1 – CP12 versioned diagram refresh (release expert review STILL PENDING)

Exact release candidate `v18.0.1-20261102`: updated diagram IDs 01, 02, 03, 04, 05, 06, 08, 09, 10, 13, 14, 15, 16, 18, 19, 20, 21, 22. Version labels, stale CP26 pre-field caveats and 2 confirmed reserve episodes now distinguish `RESERVE_NEUTRALIZATION_FIELD_PASS` from PV partial and N/E unknown.

- 01: explicit SAFE_STATE→HOLD recovery gate after independent 0-W readback/effect in Care R night window, no fresh discharge authorization.
- 02: nighttime Care-R/import branch and guarded SAFE_STATE→HOLD/0-W early return.
- 09: episode-scoped reserve journal with request vs physical confirmation, no second command owner.
- 10: Night/Care-R vs global MIN_SOC and conditional stale recovery.
- All other modified DOTs: source-version/field-evidence provenance updated; no behavior claim beyond their branch.

22/22 current source tracers and render hashes checked by technical gate. **Full semantic manual review, final README/datasheet/docs consistency and installer release gate are not passed by this refresh.**

## V18.0.1 – fachlicher Quellen-/Bildreview 22/22

22 individuelle Diagrammentscheidungen mit aktuellen Source- und Asset-Hashes sind in `SOURCE_REVIEW_V18_0_1_20261102.md` dokumentiert. Dies erlaubt ausschließlich den UML-As-built-Reviewstatus, nicht das Produktrelease oder den Pi-Feld-PASS.
