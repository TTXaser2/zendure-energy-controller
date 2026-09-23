# ZEC – Master-Backlog & Roadmap

**Stand:** 22.09.2026  
**Status:** kanonische, persistente Entwicklungsledger- und Roadmap-Autorität  
**Produktbasis:** V16.2.5 / `v16.2.5-20260922` (**TECHNICAL BUILD PASS + REAL UPDATE PASS + AUTOMATED FIELD PASS + MANUAL ACCEPTED WITH KNOWN UI FOLLOW-UPS**; `TRANSITIONAL:LIMIT_READBACK_CONVERGENCE` zulässig; Kartenlayout/Mobile Settings/Instance Owner/Graph-Linienbreak/Warnungsfunktion real bestätigt; zwei nicht blockierende Frontend-Restpunkte werden in den nächsten ohnehin anstehenden Release integriert)

## 1. Zweck und Persistenzvertrag

Diese Datei ist nicht nur eine Liste aktueller offener Aufgaben. Sie ist das **verlustfreie Master-Ledger der ZEC-Produktentwicklung**. Jeder recoverbare relevante Entwicklungs-, Evidenz-, Spezifikations- oder Prozesspunkt erhält eine stabile ID, Provenienz und einen expliziten Status.

Ein Eintrag darf nicht durch Quellenbereinigung verschwinden. Er darf nur fortgeschrieben und in einen anderen Status überführt werden. Die **Roadmap** ist eine priorisierte Sicht auf dieses Ledger; das Ledger selbst bleibt historisch vollständig.

Historische Chats, Übergaben und Releaseunterlagen sind Provenienz-/Archivbelege. Aktuelle reale Sources und aktuelle reale Evidenz haben bei Widerspruch Vorrang.

## 2. Statusmodell

- `OPEN`: fachlich offen und grundsätzlich umsetzbar; vor Umsetzung Scope/Freigabe erforderlich.
- `DEFERRED`: bewusst zurückgestellt, nicht erledigt.
- `SPEC_NEEDED`: Thema ist beschlossen/erhalten, aber ein freigegebener implementierbarer Scope fehlt.
- `EVIDENCE_PENDING`: Implementierung existiert im Wesentlichen, aber ein geplanter realer Nachweis fehlt.
- `IN_PROGRESS`: aktiv freigegebener Entwicklungsblock.
- `CLOSED`: implementiert/abgeschlossen; Abschluss- und Releasebeleg bleibt dauerhaft erhalten.
- `SUPERSEDED`: durch spätere Architektur ersetzt; historische Provenienz bleibt erhalten.
- `REJECTED`: bewusst verworfen; Grund bleibt erhalten.

Zusätzlich kann `implementation_state` beispielsweise `none`, `partial` oder `implemented` sein. **Diskutiert**, **freigegeben**, **implementiert** und **real feldvalidiert** sind getrennte Aussagen.

## 3. Aktuelle Roadmap – priorisierte Sicht

**Roadmapstand 22.09.2026 nach abgeschlossener V16.2.5-Feldentscheidung:** Das Update V16.2.4 → V16.2.5 ist real erfolgreich. Der konsolidierte automatische Feldlauf ist PASS; `controller_ready` war wegen `LIMIT_READBACK_CONVERGENCE` transient, `controller_readiness_acceptance=PASS TRANSITIONAL:LIMIT_READBACK_CONVERGENCE`. Instance Owner, Speicherstatuskarten-Geometrie, Mobile Settings, sichtbare Graph-Linienunterbrechung sowie die funktionale ein-/ausklappbare High-SOC-/Command-Warnung sind real beobachtet.

Die reale Sichtprüfung hat zwei klar isolierte Frontend-Restpunkte ergeben: (1) `ZEC-BL-GRAPH-GAP-001`: Cursor/Tooltip/Inspector müssen innerhalb bestätigter Evidence-Gaps einen ehrlichen Gap-/Empty-State statt Nearest-Sample-Werten bzw. Epoch-Nullzeit zeigen; (2) `ZEC-BL-UI-STATUS-003`: der persistente Warnhinweis soll im kompakten Zustand höhenneutral als Warning-Chip im Kartenkopf erscheinen, während Details Desktop als verankertes Popover und mobil als Bottom-Sheet/Modal außerhalb des normalen Kartenflows geöffnet werden. Der Nutzer hat am 22.09.2026 ausdrücklich entschieden, für diese zwei kleinen, bereits klar abgegrenzten UI-Härtungen **keinen separaten Hotfix-Zyklus** zu erzwingen. Sie werden im nächsten ohnehin anstehenden Release als eigenständige, regressionsgeprüfte Frontend-Subscopes mitgeführt und sind **keine Sequencing-Blocker**.

Das Sequencing-Gate ist am 22.09.2026 durch ausdrückliche Nutzerentscheidung geschlossen: **`ZEC-BL-CTRL-FASTCAP-001` wird als nächster Controllerblock umgesetzt; Fast Capture wird technisch und fachlich von `ZEC-BL-CTRL-ADAPTIVE-001` entkoppelt.** Die eingefrorene A400/R100-Spezifikation wurde gegen die reale V16.2.5-Codebasis revalidiert (`PASS_WITH_V16_2_5_INTEGRATION_DELTAS`). `controller_logic.py`, `ZendureController.py`, `command_lifecycle.py`, `config_validator.py` und `primary_storage_source.py` sind zwischen V16.0.2 und V16.2.5 byteidentisch; die notwendigen Deltas betreffen vor allem State-/Settings-/Measurement-/UI- und Feldevidenzverträge. Die revalidierte Spezifikation `ZEC_FAST_CAPTURE_A400_R100_PRODUKTIONSSPEZIFIKATION_V16_2_5_REVALIDATED.md` ist Blockautorität. Der V17.0.0-Makro-Implementierungsscope wurde anschließend ausdrücklich freigegeben. Checkpoint A (Controllerkern/State/Differential-/Safetytests) ist fokussiert PASS mit 110 Tests + 11 Subtests; Checkpoint B (Settings/Validation, Measurement V4, Fast-Feldanalyse und V17-Feldabnahme) ist fokussiert PASS mit 114 Tests + 640 Subtests. Ein TECHNICAL BUILD PASS liegt noch nicht vor.

Adaptive bleibt vollständig erhalten, ist aber kein Vorläufer für Fast Capture. Nach Bereitstellung des Fast-Capture-Releases beginnt ein eigener Adaptive-Spezifikationsblock; reale Fast-Episoden dürfen dabei als Evidenzinput dienen. Adaptive-Controller-Sourcearbeit benötigt weiterhin Lernzustand/Persistenz/Reset, Confidence/Fallback, S3-Mapping, Capacity-Weighting-Vertrag und eigene explizite Freigabe.

Aktuelle priorisierte Sicht:

1. **`ZEC-BL-CTRL-FASTCAP-001` – Fast Capture A400/R100:** **IN_PROGRESS**; V17.0.0-Makro-Scope ausdrücklich freigegeben. Checkpoint A und Checkpoint B sind fokussiert PASS; Checkpoint C mit den zwei bereits freigegebenen isolierten UI-Follow-ups ist fokussiert PASS mit 12 Tests; vollständige Releasegates stehen noch aus. Der Release muss die Fast-spezifische read-only Feldanalyse gleich mitliefern.
2. **Verbindliche UI-Follow-ups im selben nächsten ohnehin anstehenden Release:** `ZEC-BL-GRAPH-GAP-001` Gap-aware Cursor/Tooltip/Inspector sowie `ZEC-BL-UI-STATUS-003` höhenneutraler Warning-Chip + Desktop-Popover/Mobile-Bottom-Sheet. Beide als isolierte Frontend-Deltas mit eigener Regression; keine Kopplung an Fast-Reglerlogik.
3. **`ZEC-BL-CTRL-ADAPTIVE-001` – Adaptive-Spezifikationsblock nach Fast-Capture-Release:** S3 + adaptive Strategie + weiche Kapazitätsgewichtung vollständig spezifizieren; produktive Sourcearbeit erst separat freigeben.
4. **ZEC-BL-BATCARE-001 – Battery Care / Winter- und Reserve-SOC-Erhaltung** folgt gemäß bestehender Roadmap nach dem adaptiven Block; vor Implementierung ist aus dem erhaltenen Brainstorming eine explizit freigegebene Spezifikation zu erstellen.
5. **ZEC-BL-STORAGE-001 – Measurement-/SQLite-Storage-Lifecycle.** S4/S5/S6/S7/S9 gegen die aktuelle Codebasis inventarisieren und in sicheren Stufen umsetzen.
6. **ZEC-BL-ANALYSIS-HANDOFF-001 – Graph → Analyse-Service.**
7. **ZEC-BL-SIM-001 – kontrafaktische Regler-Simulation.**
8. **ZEC-BL-SCENARIO-001 – allgemeiner Szenarioeditor.**
9. **ZEC-BL-MULTI-001 – echter Multi-Zendure-Command-/Regelpfad.** Darstellung mehrerer Entities ist keine aktive Dual-Headunit-Regelung.
10. **ZEC-BL-REL-001 – repo-zentrierter/reproduzierbarer Releaseprozess / CI.**

Querschnittlich bleiben `ZEC-BL-PRIMARY-METADATA-001`, `ZEC-BL-UI-STATUS-EXPERT-001`, Diagnose-/Command-Langzeitevidenz, Lernwerkzeugabgleich und Storage-Langzeitperformance erhalten.

### 3.1 Historische S1–S9-Stufen – vollständige Reconciliation

| Stufe | historische Bedeutung | aktueller Ledgerstatus | Auflösung |
|---|---|---|---|
| S1 | Settings-Basis, UI und Legacy-Audit | CLOSED | in RC20/V12.11.x–V12.12.x produktiv umgesetzt; dauerhaft in der Closed-Historie erhalten |
| S2 | Primärspeicherintegration | CLOSED / SUPERSEDED BY V15 ARCHITECTURE | source-neutrale Primärspeicherintegration und direkte read-only Modbus-Anbindung in V15.0.0 schließen die alte S2-Kopplungslücke |
| S3 | Saison- und Tagesprofile | OPEN / in adaptiven Umbrella eingeplant | `ZEC-BL-CTRL-S3-001` als Child von `ZEC-BL-CTRL-ADAPTIVE-001`; kein separater vorgelagerter S3-Release |
| S4 | SQLite-Pfad und `report_only` | OPEN / partial | `ZEC-BL-STORAGE-S4-001` |
| S5 | SQLite-Enforce | OPEN | `ZEC-BL-STORAGE-S5-001`; Bedeutung aus `conversations.json` wiederhergestellt |
| S6 | V4-Schutz, Katalog und Sicherheitsdialog | OPEN / partial | `ZEC-BL-STORAGE-S6-001` |
| S7 | V4 `compress_only` und Restore | OPEN | `ZEC-BL-STORAGE-S7-001` |
| S8 | Analyse- und Simulationspakete | PARTIAL / SPLIT | vorhandener Analysedienst ist produktiv; fehlende Graph-Übergabe `ZEC-BL-ANALYSIS-HANDOFF-001`, echte Simulation `ZEC-BL-SIM-001`, Szenarioeditor `ZEC-BL-SCENARIO-001` |
| S9 | V4-Retention Enforce | OPEN / nachgelagert | `ZEC-BL-STORAGE-S9-001` |

Damit ist keine historische S1–S9-Stufe mehr nur implizit oder unaufgelöst.

## 4. Offenes und zurückgestelltes Master-Ledger

### ZEC-BL-CTRL-ADAPTIVE-001 – gemeinsamer adaptiver Reglerblock (S3 + adaptive Strategie + Kapazitätsgewichtung)

- **Status:** SPEC_NEEDED / OPEN; Controller-Implementierung noch nicht begonnen. Nach Nutzerentscheidung vom 22.09.2026 ist Adaptive von Fast Capture entkoppelt und folgt als eigener Spezifikationsblock nach Bereitstellung des Fast-Capture-Releases.
- **Rolle:** Roadmap-/Umbrella-Eintrag für `ZEC-BL-CTRL-S3-001`, `ZEC-BL-CTRL-001` und `ZEC-BL-CTRL-CAP-001`. Die Child-IDs bleiben eigenständig erhalten und dürfen durch die Zusammenführung nicht verschwinden.
- **Entscheidung 20.09.2026:** S3 nicht separat vorab implementieren. Saisonale Faktoren und dynamische Tagesprofile sollen mit der adaptiven Lade-/SOC-/Ertragsstrategie sowie der weichen Kapazitätsgewichtung in einem konsistenten Regelmodell zusammengeführt werden, sofern die finale Lernmodell-Übergabe dies bestätigt.
- **Pflicht vor Sourceänderung:** Es existiert nach aktueller Quellenprüfung keine weitere verlorene/finale Adaptive-Spezifikation. Der nächste Adaptive-Arbeitsschritt ist daher bewusst **Spezifikation**, nicht Suche nach einem vorausgesetzten Artefakt. Neu zu erstellen sind mindestens: Mapping-Matrix vorhandene S3-Settings → aktive Nutzervorgabe / Modellinput / deterministischer Fallback / deprecated; Abdeckung von `CTRL-001` und `CTRL-CAP-001`; konkretes Optimierungsziel und Aktionsraum; Lernzustand/Persistenz/Versionierung/Reset; Inputvertrag; Confidence/Fallback; Hardwarewechsel-/Invalidierungsvertrag; Offline-/Replay-/Shadow-/Differential-Evidenz; Safety-/Hardwaregrenzen und reproduzierbare Entscheidungsprovenienz.
- **Simulation/Evidenz:** Der spätere produktive allgemeine Counterfactual-Simulator `ZEC-BL-SIM-001` bleibt ein eigener Roadmappunkt und ist nicht zwingende Vorbedingung für diesen Block. Vor produktiver Reglerwirkung sind dennoch belastbare simulationsnahe bzw. replay-/pretrainer-/shadowbasierte Nachweise auf realen Daten erforderlich.
- **Normative Grenzen:** Die bestehende Grundinvariante „aktuell vermeidbare Einspeisung vor strategischer Ladeverteilung“ bleibt erhalten. Adaptive/gelernte Logik darf harte Safety-, SOC-, Command-, Recovery-, Cross-Charge- und Hardwareschonungsregeln nicht überstimmen.
- **Versionsklasse:** erst mit finalem Runtime-Scope festlegen; ein echter neuer produktiver Lern-/Adaptionslayer ist nach `01_ZEC_PROJECT_RULES.md` als neues Entwicklungsthema zu bewerten, eine rein statische Parameternutzung gegebenenfalls anders.
- **Exit:** Child-IDs einzeln mit Implementierungs-/Evidenzstatus reconciliert; keine exponierte S3-Einstellung bleibt unbeabsichtigt wirkungslos; Lern-/Fallback-/Recovery-Verhalten und Hardware-/Konvergenzeigenschaften sind nachgewiesen.

### ZEC-BL-CTRL-S3-001 – Saison-/Tagesprofile Completion & Effectiveness

- **Status:** OPEN
- **Roadmapbindung ab 20.09.2026:** Child-Scope von `ZEC-BL-CTRL-ADAPTIVE-001`; kein separater vorgelagerter S3-Release vorgesehen.
- **Historische Herkunft:** S3 `Saison- und Tagesprofile`; Settings-/RC19-Planung und spätere Completion-Audits.
- **Aktueller V16-Befund:** Registry und Validation enthalten Kalenderfenster, Tagesprofilzeiten und gestaffelte High-SOC-Entry-Confirm-Zeiten. Für repräsentative S3-Keys existiert außerhalb Registry/Validation/Tests kein Runtime-Consumer.
- **Risiko:** UI/Config kann eine Wirksamkeit suggerieren, die der reale Regler nicht vollständig besitzt.
- **Vor Umsetzung:** reale V16-Zielwert-/State-Machine-Analyse; historische harte Zeiten/Confirm-Werte gegen Zielsettings abgleichen; Zustand/Rechnung/Wirkung/Recovery; Konvergenz und Hardwareschonung.
- **Exit:** explizit nachweisen, welche S3-Settings runtimewirksam sind; Tests für Kalender über Jahreswechsel, Tagesgrenzen, Hold-/Confirm-Übergänge und No-Regression.

### ZEC-BL-STORAGE-001 – Measurement-/SQLite-Storage-Lifecycle

- **Status:** OPEN
- **Rolle:** Parent für die historischen S4/S5/S6/S7/S9-Stufen sowie Langzeitperformance und retention-aware Backfill.
- **Grundinvariante:** keine automatische Löschung/Kompression allein aufgrund vorhandener Settings. Jede destruktive Stufe benötigt Vorschau, Protection/Coverage, Restore und klare Provenienz.

#### ZEC-BL-STORAGE-S4-001 – S4 SQLite-Pfad & report_only
- **Status:** OPEN; `implementation_state=partial`.
- SQLite ist produktive Messdatenbasis; Pfad-/Writer-/Graphfunktionen existieren. Maintenance-Settings sind vorhanden, aber der historische S4-Lifecycle ist nicht als vollständig geschlossener Maintenancevertrag nachgewiesen.
- Vor S5 ist S4 gegen reale V16-Datenbankpfade, Status-Snapshot, Inventory/Long-run und Schutz gegen Controller-Blockierung abzuschließen.

#### ZEC-BL-STORAGE-S5-001 – S5 SQLite-Enforce
- **Status:** OPEN; `implementation_state=none/placeholder settings`.
- **Recoverybeleg:** OpenAI-Export definiert S5 eindeutig als `SQLite-Enforce`.
- V16 besitzt `MEASUREMENT_DB_MAINTENANCE_MODE` und Retention-Settings/Validation, aber keinen produktiven Retention-Enforcer.
- Muss Retention/Backfill, Online-Betrieb, DB-Locking, Crashsicherheit, Vacuum-/Compaction-Strategie und Restore berücksichtigen.

#### ZEC-BL-STORAGE-S6-001 – S6 V4-Schutz, Katalog & Sicherheitsdialog
- **Status:** OPEN; `implementation_state=partial`.
- Teile der Katalog-/Coverage-/Validation-Infrastruktur existieren. Vor einer Lösch-/Kompressionsstufe muss ein vollständiger, manipulations- und crashsicherer Bestandsschutz nachgewiesen werden.
- Protection muss u. a. aktive Datei, Incident-/Forensic-/Simulation-Coverage und explizite Schutzzeiträume respektieren.

#### ZEC-BL-STORAGE-S7-001 – S7 V4 `compress_only` & Restore
- **Status:** OPEN.
- Historischer Vertrag: geschlossene `.csv` streamingbasiert komprimieren, temporäres `.csv.gz.tmp`, Flush/fsync, vollständige Dekompressions-/SHA256-/gzip-CRC/EOF-Verifikation, atomisches Rename, Manifestumschaltung, Original erst ganz am Ende löschen.
- Toolchain muss `.csv` und `.csv.gz` transparent lesen: Analyse/Replay, Backfill, Import, Diagnosepakete und relevante Branchanalyse.
- Runtime-/Betriebsereignisse benötigen einen konsistenten Rotation-/gzip-Lifecycle; deren relevante Evidenz darf nicht früher verschwinden als zugehörige Measurements.

#### ZEC-BL-S8-001 – S8 Analyse- und Simulationspakete
- **Status:** OPEN; `implementation_state=partial`, historischer Sammelpunkt.
- Der reale Datenanalysedienst/Replay-Service ist produktiv vorhanden. Der historische S8-Rest wird bewusst auf drei konkrete Nachfolger aufgeteilt:
  - `ZEC-BL-ANALYSIS-HANDOFF-001` – Graph-Selection/Evidence-Handoff an Analyse;
  - `ZEC-BL-SIM-001` – kontrafaktische Regler-Simulation realer historischer Situationen;
  - `ZEC-BL-SCENARIO-001` – allgemeiner/synthetischer Szenarioeditor.
- S8 gilt erst als vollständig geschlossen, wenn diese Aufteilung fachlich abgeschlossen oder ausdrücklich anders entschieden wurde.

#### ZEC-BL-STORAGE-S9-001 – S9 V4-Retention Enforce
- **Status:** OPEN, absichtlich nachgelagert.
- Erst nach S6/S7, real verifiziertem Restore, Coverage-/Protection-Gates und expliziter Freigabe destruktiv aktivieren.
- Retention nach Alter/Gesamtgröße muss aktive/geschützte Dateien ausnehmen und fail-closed arbeiten.

#### ZEC-BL-STORAGE-BACKFILL-001 – retention-aware Backfill/Rebuild
- **Status:** OPEN; `implementation_state=partial`.
- **Normative Invariante:** Daten, die absichtlich durch Retention entfernt wurden, dürfen durch späteres Backfill nicht stillschweigend wieder permanent hergestellt werden.
- Graph Core V3 besitzt hierfür bereits Retention-Ledger/`PURGED_BY_RETENTION` und Reapply beim Rebuild. Der Vertrag muss über V4/SQLite/Graph/Restore hinweg konsistent werden.

#### ZEC-BL-STORAGE-GRAPH-001 – automatische Graph-Retention entscheiden
- **Status:** SPEC_NEEDED / DEFERRED.
- V14 implementierte Retention-Ledger-Semantik, aber ausdrücklich keine automatische Retentiondauer, keinen Scheduler und keine automatische VACUUM-Policy.
- Vor jeder Automatisierung müssen Highres-/1-Minuten-Langzeitbedarf, Speicherbudget, Coverage und Rebuildverhalten fachlich festgelegt werden.

#### ZEC-BL-STORAGE-PERF-001 – SQLite-/Storage-Langzeitverhalten
- **Status:** OPEN / observation.
- Langzeitperformance, Größenwachstum, Retention/Backfill und seltene Langläuferepisoden evidenzbasiert beobachten. Kurze Feldsnapshots sind kein Langzeitnachweis.

### ZEC-BL-ANALYSIS-HANDOFF-001 – Graph-Auswahl an bestehenden Analyse-Service

- **Status:** OPEN.
- **Produktkette:** Status → Graph-Exploration → Analyse-Handoff → bestehender Analysedienst.
- Historische Graphplanung spezifiziert die Aktion `In Analyse untersuchen`.
- Handoff soll ein reproduzierbares Untersuchungsobjekt übertragen, mindestens Zeitraum/Selection, Zeitzone, REAL-Dataset, Guided/Free-Kontext, relevante Series/Entities, historische Version/Config/Topologie, Coverage/Evidence und optional Fokuszeitpunkt.
- Der Graph entscheidet keine Kausalität; der Analysedienst bewertet nach Analyse-Regelwerk.
- Aktuell fehlt die Aktion; `replay_web.py` ist im Startpfad primär dateibasiert.

### ZEC-BL-SIM-001 – kontrafaktische Regler-Simulation auf realen Daten

- **Status:** SPEC_NEEDED / OPEN.
- **Frage:** „Was wäre in genau dieser real stattgefundenen Situation passiert, wenn andere Regelparameter bzw. eine andere freigegebene Reglerlogik gegolten hätten?“
- Muss reale Eingangsdaten, damalige Config/Topologie, Timer/Hysterese/Latches und bekannte/nicht beobachtbare Gerätezustände transparent behandeln.
- Deterministische Ergebnisse und approximierte Annahmen müssen getrennt markiert werden.
- Zielintegration: Reality vs Simulation A/B im Graphen vergleichbar; keine Simulation darf als reale Evidenz ausgegeben werden.
- Historischer Alias: S8 `Analyse- und Simulationspakete`; Analyseanteil existiert heute, echte Counterfactual-Simulation nicht.

### ZEC-BL-SCENARIO-001 – allgemeiner Szenarioeditor

- **Status:** DEFERRED / SPEC_NEEDED.
- Synthetische frei definierte Eingangssituationen sind von `SIM-001` zu trennen.
- Erst sinnvoll, wenn Simulationskern und Parametrisierung belastbar definiert sind.


### ZEC-BL-CTRL-FASTCAP-001 – Fast Capture A400/R100

- **Status:** IN_PROGRESS / TECHNICAL_BUILD_PASS / FIELD_PENDING; `implementation_state=implemented`; `sequencing=ACTIVE`; `spec_state=REVALIDATED_V16_2_5`; V17.0.1 ist der korrigierte Releasekandidat nach fail-closed Packaging-Reject von V17.0.0. Checkpoint A (Controllerkern/State/Differential-/Safetytests) fokussiert PASS: 110 Tests + 11 Subtests. Checkpoint B (Settings/Validation, Measurement V4, Fast-Feldanalyse, V17-Feldabnahme) fokussiert PASS: 114 Tests + 640 Subtests. Kein TECHNICAL BUILD PASS; Checkpoint C/UI-Follow-ups sind fokussiert PASS (12 Tests), vollständige Releasegates stehen noch aus.
- **Provenienz:** Pretrainer V0.5 -> V0.6.1, Freeze-Spezifikation vom 19.09.2026 und V16.2.5-Revalidierung vom 22.09.2026. Aktive Blockautorität: `ZEC_FAST_CAPTURE_A400_R100_PRODUKTIONSSPEZIFIKATION_V16_2_5_REVALIDATED.md`.
- **Scope:** Fast-Overlay ausschließlich für `FULL_IDLE` und `NEAR_LIMIT`; `RESERVE_UNKNOWN` bleibt im normalen Baseline-Regelpfad. Produktionskandidat A400/R100. Strategische Baseline `B` und kurzfristiger Fast-Overlay `O` sind strikt getrennte Schichten.
- **Evidenz:** V0.6.1 Vollhistorie mit 2.141.031/2.141.031 Rows und exakter Replay-Parität; Replay ist keine Closed-Loop-Feldevidenz. Die V16.2.5-Revalidierung bestätigt den Reglerkern byteidentisch zur ursprünglichen Spezifikationsbasis und definiert die notwendigen Settings-/Measurement-/UI-/Evidence-Deltas.
- **Analysewerkzeug-Audit:** `tools/v16_field_acceptance.py`, `tools/create_zec_analysis_package.sh` sowie `tools/replay_core.py`/`replay_report.py` sind als Basis wertvoll, aber allein nicht ausreichend für Zustand/Rechnung/physikalische Wirkung/Recovery des neuen Fast-Pfads. Der initiale Fast-Capture-Release muss deshalb ein releasegekoppeltes read-only Fast-Analysewerkzeug samt Tests und maschinenlesbarem Report mitliefern; fehlende natürliche Fast-Episoden sind `NOT_EVALUABLE`, niemals synthetischer PASS.
- **Feldevidenzvertrag:** Build/Differential-PASS -> reale Shadow-Abnahme -> begrenzte Active-Feldabnahme. Shadow muss Klassifikation, Mathematik und Mutationsfreiheit belegen. Active muss zusätzlich reale Exportreduktion bzw. transparent nicht bewertbare Episoden, Import-Guard/Recovery, Command-Readback/Effect, Cross-Charge und Hardwareschonung episodespezifisch auswerten.
- **Sequenzgrenze:** Nach Bereitstellung des Fast-Capture-Releases darf die Adaptive-Spezifikation beginnen, während Fast-Feldevidenz weiter gesammelt wird. Adaptive-Sourcearbeit bleibt separat freigabepflichtig und darf Fast Capture nicht stillschweigend verändern.
- **Exit:** vollständiger Build-/Differentialnachweis, ausgelieferte Fast-Verifikationslogik, reale Shadow-Evidenz und anschließend begrenzte Active-Evidenz nach `ZEC_ANALYSE_REGELWERK_V1.1.md`; Safety, Command-Effect und Hardware-Schonung separat belegen.

### ZEC-BL-PRIMARY-SMA-FLOOR-001 – Sunny-Island Entladeuntergrenze als Capability

- **Status:** CLOSED; `implementation_state=implemented`, `field_state=REAL_FIELD_PASS` in V16.1.0.
- **Reale Vorimplementierungs-Evidenz:** SMA Register `31009` (`Lower discharge limit for self-consumption range in %`, U32/FIX0/RO) lieferte am realen Sunny Island 19 %; FC03/FC04 identisch.
- **V16.1.0 Block A:** SMA-template-spezifische, read-only Capability `current_discharge_floor_soc`; getrennte Freshness/Validity/Invalidierung; diagnostischer normalisierter `primary_usable_soc_percent`; API/Status/Readiness/Connection-Test/Measurement-V4-Evidenz.
- **Safety-Grenze:** keine Reglerwirkung; `controller_logic.py` bleibt byteidentisch zu V16.0.2. Andere Primärspeicherprofile erhalten diese Capability nicht automatisch.
- **Settings-Vertrag:** kein editierbarer Floor, kein Override, kein On/Off-Schalter, keine ZEC-Saisonkurve; generische UI-/Help-Bezeichnungen werden auf „Primärspeicher“ neutralisiert; explizite Anzeigenamen bleiben erhalten.
- **Reale Feldabnahme 20.09.2026:** Update V16.0.2 → V16.1.0 erfolgreich; Capability auf realem `modbus_template`/Sunny Island `supported=true`, `fresh=true`, `valid=true`, Floor `19.0 %`; `primary_usable_soc_percent` real vorhanden/plausibel; Feldtool-Gate `primary_storage_sma_discharge_floor_capability=PASS`.
- **Abgrenzung der Feldabnahme:** globales `/ready` blieb während der Abnahme wegen eines bestehenden `INPUT_LIMIT`-/`ACTIVE_ACCEPTANCE_LIMITED`-Zustands `false`; dies ist kein Block-A-Pfad und wird separat unter `ZEC-BL-DIAG-FIELD-001` dokumentiert.

### ZEC-BL-CTRL-USABLE-SOC-001 – Block B: strategische usable-SOC-Integration

- **Status:** DEFERRED / SPEC_NEEDED; `implementation_state=none`.
- **Provenienz:** Folgeblock der SMA-Capability-Entscheidung vom 19.09.2026.
- **Ziel:** den aus realem Roh-SOC und aktueller geräteseitiger Entladeuntergrenze abgeleiteten nutzbaren Primär-SOC gezielt in Winter-/Schwachertragsstrategie verwenden.
- **Abgrenzung:** kein globaler Ersatz des Roh-SOC. FULL/IDLE, High-SOC-/Taper-Erkennung, Lade-Headroom bis 100 %, Fast Capture sowie physische Safety-/Limitentscheidungen bleiben am realen Roh-SOC bzw. Leistungszustand.
- **Voraussetzung:** mit Adaptive-/Replay-Ergebnissen zusammenführen; Zustand, Rechnung, physikalische Wirkung, Konvergenz, Recovery und Hardwareschonung vor Reglerfreigabe separat belegen.

### ZEC-BL-CTRL-CAP-001 – echte weiche Kapazitätsgewichtung

- **Status:** SPEC_NEEDED.
- **Roadmapbindung ab 20.09.2026:** Child-Scope von `ZEC-BL-CTRL-ADAPTIVE-001`; die laufende Lernmodell-/Pretrainer-Arbeit ist primärer Spezifikationsinput.
- `HARVEST_CAPACITY_WEIGHTING_MODE` ist historisch bewusst diagnostisch geblieben; keine echte Reglerwirkung vortäuschen.
- Eine neue weiche Gewichtung ist eine Reglerstrategie. Vor produktiver Wirkung ist sie mit historischen Produktivdaten über belastbare Offline-/Replay-/Pretrainer-/Shadow- bzw. simulationsnahe Evidenz zu prüfen; der spätere allgemeine Produktiv-Simulator `ZEC-BL-SIM-001` ist dafür keine zwingende Vorbedingung. Danach Differential-/Konvergenz-/Hardwareschonungsbewertung und explizite Freigabe.

### ZEC-BL-CTRL-001 – ertrags-/SOC-bewusste Ladeverteilung weiterentwickeln

- **Status:** OPEN.
- **Roadmapbindung ab 20.09.2026:** Child-Scope von `ZEC-BL-CTRL-ADAPTIVE-001`; nicht mehr als separater späterer Block hinter `SIM-001` geplant.
- Die Grundinvariante „aktuell vermeidbare Einspeisung vor strategischer Ladeverteilung“ ist bereits produktiv implementiert und darf nicht neu erfunden werden.
- Erweiterungsraum: adaptive/lernende Ladeannahme-/Taper-Kennlinie, batteriespezifische Anpassung, erweiterte SOC-/Ertragsstrategie.
- Vor produktiver Reglerwirkung: Lernzustand/Persistenz/Reset, Confidence/Fallback, belastbare Offline-/Replay-/Pretrainer-/Shadow-/Differential-Evidenz, Konvergenz/Oszillation, Zustand/Rechnung/Wirkung/Recovery und Hardwarebelastung.

### ZEC-BL-BATCARE-001 – Battery Care / Winter- und Reserve-SOC-Erhaltung

- **Status:** SPEC_NEEDED.
- **Roadmappriorität ab 20.09.2026:** unmittelbar nach `ZEC-BL-CTRL-ADAPTIVE-001`, ausdrücklich wegen der zeitnahen Winterrelevanz.
- **Wichtig:** Es existiert keine freigegebene Battery-Care-Spezifikation. Der Chat vom 11.08.2026 wird als **Brainstorming-Provenienz** erhalten, nicht als normative Entscheidung.
- Recoverter Brainstorming-Input, ausdrücklich neu zu prüfen:
  - opt-in / default-off als Idee;
  - kalendergebundene Wirksamkeit über Jahreswechsel;
  - Trigger-SOC → Ziel-SOC als echte Episode/Hysterese statt Nachregeln am Ziel;
  - mögliche Policy-/Episode-Architektur statt komplett neuem gleichrangigem Hauptmodus;
  - Safety, MIN/MAX, Command-Guards/Recovery und Cross-Charge bleiben übergeordnet;
  - bei aktiver Episode und temporärer Ladesperre eher HOLD als unbeabsichtigtes Weiterentladen;
  - offene Grundsatzfrage, ob kontrollierte Netzladung für Reserveerhaltung zulässig sein soll; niemals SMA→Zendure-Cross-Charge;
  - eigener Battery-Care-Leistungscap als mögliche Hardwareschonungsoption;
  - Restart benötigt bei echter Hysterese möglicherweise restartfeste Episode-Provenienz, die selbst niemals ein Kommando autorisiert;
  - Leap-Day-/Kalendersemantik, SOC-Freshness, Exit-Neutralisierung, Events/Measurement/Settings und No-Regression sind zu spezifizieren.
- Beispielwerte aus dem Brainstorming (z. B. 12/20 %) sind **keine allgemeinen Softwaredefaults**.

### ZEC-BL-MULTI-001 – echter Multi-Zendure-Command-/Regelpfad

- **Status:** DEFERRED / SPEC_NEEDED.
- Graph/Entitymodell kann mehrere Zendures darstellen. Der produktive Commandpfad ist weiterhin auf eine aktive Controller-/`DEVICE_ID`-Instanz ausgelegt.
- Echte Zielallokation, Priorität, Safety, Readback, Wirkung, Ausfall einer Unit und gemeinsame Netzkonvergenz müssen separat spezifiziert werden.

### ZEC-BL-REL-001 – repo-zentrierter/reproduzierbarer Releaseprozess

- **Status:** DEFERRED.
- Historisches Ziel: repo-zentrierter Build, reproduzierbares ZIP, weniger manuelles Kopieren, perspektivisch GitHub/GitHub Actions.
- V16.2.0 enthält weiterhin keine `.github`-Automation. Umsetzung darf bestehende Fresh-extract-, Manifest-, Hash-, Test-, Datenblatt- und Feldgates nicht abschwächen.

### ZEC-BL-LEARN-001 – Lernwerkzeug V4.2.7 auf V16-Registry/Defaults abgleichen

- **Status:** OPEN.
- Strukturintegrität des XLSX ist belegt; Dashboard enthält noch historischen „Startwert V12.8.10“.
- Werte/Bezeichnungen gegen reale V16-Registry und `config.example.json` prüfen; keine anlagenspezifischen Werte als allgemeine Defaults übernehmen.

### ZEC-BL-DIAG-001 – aktuelle Fehler vs. historisches `last_error`

- **Status:** OPEN / observation-hardening.
- Diagnosesemantik weiter schärfen, damit historische Fehler nicht als aktueller aktiver Incident erscheinen.

### ZEC-BL-CMD-OBS-001 – Command-/Readback-Feldevidenz

- **Status:** OPEN / evidence.
- Command Effect, Readback, Resync und physikalische Wirkung weiter mit realen Episoden belegen. Zeitliche Reihenfolge allein ist kein Kausalitätsnachweis.

### ZEC-EV-OFFGRID-001 – kontrollierter realer Offgrid-Feldtest

- **Status:** EVIDENCE_PENDING / DEFERRED.
- Die Power-Semantik trennt `gridOffPower` von Hausnetz-/Packfluss und ZEC verändert die Offgrid-Konfiguration nicht.
- Historisch ausdrücklich offen: ungefährlichen Verbraucher am Offgrid-Ausgang real testen und belegen, dass Offgrid-Last nicht als Hausnetzentladung, Cross-Charge oder fehlgeschlagene Neutralisierung interpretiert wird.

### ZEC-BL-PRIMARY-METADATA-001 – technische Primärspeicher-Metadaten automatisch aus Gerät/Template

- **Status:** SPEC_NEEDED.
- **Provenienz:** Status-GUI-/V16.2.0-Scope vom 20.09.2026.
- **Ziel:** technische Eigenschaften wie nutzbare/nominale Kapazität, maximale Ladeleistung und maximale Entladeleistung sollen – soweit das konkrete Gerät sie belastbar bereitstellt – perspektivisch über Geräteprofile/Templates automatisch erfasst werden, statt dauerhaft manuell gepflegt werden zu müssen.
- **Vor Umsetzung zu entscheiden:** Source-vs.-manueller Fallback/Override-Vertrag, Freshness/Validity, Gerätewechsel/Invalidierung, Einheiten und Verhalten bei nur teilweise verfügbaren Capabilities.
- **Abgrenzung:** V16.2.0 implementiert ausschließlich optionale manuelle Status-/Diagnose-Fallbackwerte; daraus entsteht keine Reglerwirkung.

### ZEC-BL-DEP-002 – persistente Installationsreports

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; Release `V16.2.4 / v16.2.4-20260921`.
- **Umsetzung V16.2.4:** Der Installer schreibt den maschinenlesbaren Installationsreport atomar und timestamped persistent unter `/home/pi/Downloads`; `/tmp/zec_v16_2_4_install_report.json` bleibt ausschließlich Kompatibilitätskopie.
- **Feldtool-Vertrag:** Ein explizites `--install-report` gewinnt immer. Ohne expliziten Pfad wird der neueste persistente releasespezifische Report bevorzugt; nur wenn keiner vorhanden ist, darf die definierte `/tmp`-Kompatibilitätskopie verwendet werden.
- **Integrität:** Reportformat, Release-/Buildidentität und Installationsmodus werden fail-closed validiert. Beim Update wird die im Report referenzierte reale Rollback-Datei weiterhin über Pfad, Größe und SHA256 verifiziert.
- **Abgrenzung:** keine Änderung an Rollback-, Supportcapture-, Installationszustands-, Regler-, Command-, Safety- oder Recoverysemantik.
- **Technischer Exit V16.2.4:** vollständige Regression `1123 Tests + 698 Subtests PASS` über 150 Testdateien; identischer Lauf mit `ResourceWarning=error`; Bash `13/13`, Browser-JS `3/3`, Compileall, Deployment-Harness `11/11`, Root-Artefakt-Transaktion, Datenblatt-, Build-Evidence-, Manifest-/Hygiene- und Fresh-extract-Gates PASS.
- **Realer Exit 22.09.2026:** Update V16.2.3 → V16.2.4 erfolgreich; persistenter Report `/home/pi/Downloads/zec_v16_2_4_install_report_20260921_232843.json` real gefunden und vom Feldtool ohne explizites `--install-report` bevorzugt; Report-SHA256 `778b0716fba2c79ff6f77f26e11b818fb08cee96b9e0630f7cbf8624280b5260`; reale Rollback-Datei SHA256 `8e541acdc71fffb4e97bb9ec0428eab575eba526eeacf4d1f32c28b0fbf77150`; `rollback_backup_integrity=RELEASE_BACKUP_EXACT`; Gesamtfeldlauf PASS. Damit CLOSED / REAL_FIELD_PASS.

### ZEC-BL-DEP-003 – V16.2.1 Manifest-/Deploymentvertrag und einmalige Fehlerbehandlung

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; technischer Fix ab V16.2.2, realer Exit mit `V16.2.3 / v16.2.3-20260921`.
- **Realer Fund 21.09.2026:** V16.2.1 bestand Package-/Fresh-Extract-Gates, enthielt aber fünf `.pytest_cache`-Dateien im Source-Manifest. Der Installer schließt `.pytest_cache/` beim Update/Fresh-Install bewusst aus und prüfte anschließend das unveränderte vollständige Manifest im Ziel; dadurch brach der reale Updatepfad V16.2.0 → V16.2.1 nach Backup und Copy mit fehlenden Manifestdateien ab.
- **Rollback-Evidenz:** automatischer Update-Rollback stellte V16.2.0 wieder her; `/health` meldete V16.2.0 alive=true, `/ready` true und keine failed_checks. V16.2.1 erhält daher keinen Real-Field-PASS.
- **Zweiter bestätigter Befund:** `set -E` vererbt den `ERR`-Trap in Subshells. Ein Fehler im Manifest-Subshell konnte Supportcapture/Rollback dort und anschließend nochmals im Hauptprozess auslösen; dies erklärt die zwei Diagnosepakete des realen Fehlversuchs.
- **V16.2.2-Scope:** volatile Cache-/Bytecode-/Runtime-DB-Artefakte fail-closed aus Release-Tree und aktuellem Manifest ausschließen; gemeinsamer Manifestverifier für Paket und Ziel; Paket-Preflight prüft Release-Hygiene vor jeder Mutation; reales rsync-Update und Fresh-Install werden gegen denselben Manifestvertrag regressionsgetestet; nur der Haupt-Shellprozess darf Supportcapture/Rollback finalisieren.
- **Abgrenzung:** keine UI-, Regler-, Command-, Safety- oder Recoverysemantikänderung; `controller_logic.py` muss byteidentisch bleiben. `ZEC-BL-DEP-002` wird in diesem Hotfix nicht stillschweigend mit umgesetzt.
- **Pre-Freeze-Evidenz:** vollständige Regression `1106 Tests + 698 Subtests PASS`, identischer Lauf mit `ResourceWarning=error`, Bash `13/13`, Browser-JS `3/3`, Compileall, Deployment-Harness `11/11`, Root-Rollback, Datenblatt und reale rsync/Manifest-Regression für Update/Fresh PASS. Das neue Hygiene-Gate erkannte ein während QA entstandenes Runtime-SQLite-Artefakt fail-closed; dieses wurde vor Manifest/Paketbau entfernt.
- **Technical Exit:** paketierter Fresh-Extract ohne volatile Artefakte, Manifest/Hygiene, vollständige Regression `1106 + 698`, identischer ResourceWarning-Lauf, statische Gates, Deployment-Harness und Root-Rollback PASS.
- **Realer Exit 21.09.2026:** V16.2.3-Preflight und Update V16.2.0 → V16.2.3 erfolgreich; konsolidierte Feldabnahme insgesamt PASS. Exaktes Rollback-Backup SHA256 `d860ad8d3af8cdd31d6e568357509f6320258c2ef5d79e699e1a33e11ed8d518`. Damit ist der Manifest-/rsync-/Single-Finalization-Vertrag real bestätigt.

### ZEC-BL-UI-STATUS-002 – V16.2.0 Status-/SOC-Day-/Mobile-Settings-Härtung

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; Release `V16.2.0 / v16.2.0-20260920`.
- **Provenienz:** reale V16.1.0-Nutzung / Nutzerbefunde vom 20.09.2026.
- **Scope:** Primärspeicher-SOC-Ring-Layout; Tageswechsel-sicherer SOC-Day-Cache; „Jetzt“-Markierung nur am aktuellen Tag; mobile Settings-Suche mit erreichbarer Commit-Leiste; richtungsabhängige Restenergie und Leistungsbalken für beide Speicher; optionale Primärspeicher-Fallbackwerte für Kapazität und maximale Entladeleistung.
- **Safety:** reine UI-/Diagnose-/Settings-Metadaten-Erweiterung; `controller_logic.py` bleibt byteidentisch; neue Primärspeicherwerte besitzen keine Reglerwirkung.
- **Technischer Exit:** vollständige Regression `1098 Tests + 698 Subtests PASS`, identischer Lauf mit `ResourceWarning=error`, Browser-/Compile-/Deployment-/Datenblatt-/Fresh-extract-Gates PASS.
- **Realer Exit 20.09.2026:** Update V16.1.0 → V16.2.0 erfolgreich; Installer `ready=true`; konsolidierte read-only Feldabnahme insgesamt PASS mit allen 26 ausgewiesenen Checks PASS, einschließlich Releaseidentität, Controller-Readiness, Graph-/SOC-Day-/Settings-Verträgen, Installationsreport, Rollback-Backup und Performance-Budgets.

### ZEC-BL-DEP-004 – kanonischer maschinenlesbarer Build-Evidence-/Preflight-Vertrag

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; Release `V16.2.3 / v16.2.3-20260921`.
- **Fund 21.09.2026:** realer V16.2.2-`--preflight-only`-Lauf auf V16.2.0 brach vor jeder Produktivmutation ab, weil der Installer nicht vorhandene Freitextmarker in den vorhandenen grünen QA-Dateien verlangte. Diagnosebundle belegte `installed_identity=V16.2.0` und `rollback_result=not_required_preflight`.
- **Root Cause:** Build-Erzeugung und Installer hatten keinen gemeinsamen maschinenlesbaren Evidence-Vertrag; human-readable QA-Texte wurden als implizite Parser-API missbraucht.
- **V16.2.3-Scope:** `ZEC_BUILD_EVIDENCE_V1`; gemeinsamer `deployment_contract.py verify-build-evidence`; Installerdelegation ohne Freitextparsing; fail-closed Release-/Count-/ResourceWarning-Prüfung; finales Paketgate muss den Evidence-Teil des echten Installer-Preflights aus dem Fresh Extract ausführen.
- **Abgrenzung:** keine UI-, Regler-, Command-, Safety- oder Recoveryänderung; `controller_logic.py` bleibt byteidentisch. `ZEC-BL-DEP-002` bleibt separat offen.
- **Realer Exit 21.09.2026:** mutationsfreier V16.2.3-Preflight PASS; anschließendes Update V16.2.0 → V16.2.3 erfolgreich; Installationsreport SHA256 `7f727963537ca81c78184bdd28933ce24f5654f78a3c86126e5f0e66a98097ff`; Feldartefakt SHA256 `cd82a345765186104b9b6fbb485e69d0f43740f83d8bf81f70d104c95db5eab7`; Feldlauf insgesamt PASS. Damit ist der maschinenlesbare Build-Evidence-/Preflight-Vertrag real bestätigt.

### ZEC-BL-UI-SETTINGS-001 – Settings-Webmodell unterdrückt aktuelle produktive Releasefelder

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; Release `V16.2.4 / v16.2.4-20260921`.
- **Realer Fund 21.09.2026:** Nach erfolgreichem V16.2.3-Update fehlten `SECOND_BATTERY_CAPACITY_WH` und `SECOND_BATTERY_MAX_DISCHARGE_POWER_W` auf der realen Settings-Webseite. Bei der Sourceverifikation wurde zusätzlich bestätigt, dass auch der produktive Aktivierungsschalter `SECOND_BATTERY_INTEGRATION_ENABLED` vom selben historischen S1/RC19-Filter betroffen war.
- **Root Cause:** Provenienzmetadaten `release_stage`/`origin` wurden fälschlich als Produkt-Surface-Autorität verwendet.
- **Umsetzung V16.2.4:** `SettingsRegistry` trennt explizit `SurfaceState` (`operational`/`target_only`) und Hardware-/Konfigurations-`Applicability`. `settings_model.py` und First-Install-Persistenz verwenden dieselbe zentrale operative Surface-Autorität. Nichtlegacy-Settings müssen explizit klassifiziert sein; unbekannte aktive/visible Kandidaten schlagen fail-closed fehl.
- **Hardwarevariabilität:** `SECOND_BATTERY_INTEGRATION_ENABLED` bleibt als operativer Einstieg unabhängig vom aktuellen Primärspeicherzustand erreichbar. Untergeordnete Primärspeicherfelder sind produktiv freigegeben, werden aber abhängig vom aktuellen Browser-Draft der Integration sichtbar. Die Topologie kann 1 oder 2 Zendure-Entities ausweisen; daraus entstehen ausdrücklich keine zweite Zendure-Commandkonfiguration und keine Freigabe von `ZEC-BL-MULTI-001`.
- **Negativvertrag:** spätere S3/S4/S6/S7-Zielsettings bleiben `target_only` und dürfen auch bei passender Hardware nicht produktiv exponiert werden.
- **Feldtool-Lücke geschlossen:** Die V16.2.4-Feldabnahme prüft live `/settings/model`, die drei erwarteten Primärspeicher-Controls, deren Surface-/Applicability-Vertrag sowie Negativproben für target-only Settings.
- **Safety:** keine Regler-, Command-, Safety- oder Recoveryänderung; `controller_logic.py` bleibt byteidentisch.
- **Realer Exit 22.09.2026:** konsolidierter V16.2.4-Feldlauf PASS; `primary_storage_settings_surface=PASS`; `SECOND_BATTERY_INTEGRATION_ENABLED`, `SECOND_BATTERY_CAPACITY_WH` und `SECOND_BATTERY_MAX_DISCHARGE_POWER_W` jeweils real `available=True`, `editable=True`, `applicable=True`, `surface_state=operational`. Manuelle UI-Prüfung bestätigte Kapazitätsvalidation und die daraus resultierende kWh-/Maximalleistungsanzeige auf der Sunny-Island-Karte. Damit CLOSED / REAL_FIELD_PASS.

### ZEC-BL-UI-SETTINGS-MOBILE-001 – Mobile Settings ohne horizontalen Content-Overflow

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; `technical_state=TECHNICAL_BUILD_PASS`; Release `V16.2.5 / v16.2.5-20260922`.
- **Implementierungsstand 22.09.2026:** responsiver Viewport-/Intrinsic-Width-Vertrag umgesetzt; Input/Einheit stapeln auf kleinen Viewports, lange Keys/Fehler/Meta-Pills brechen, Pinch-Zoom bleibt zulässig aber nicht erforderlich. Fokussierte UI-/Diagnose-Regression und vollständige Build-/Fresh-extract-Gates PASS.
- **Reale Feldabnahme 22.09.2026:** auf realem iPhone im Expertenmodus geprüft. Input, Einheit, langer technischer Key, Validierungsfehler, Meta-Pills, Standard/Experte-Umschalter und die feste Änderungsleiste bleiben innerhalb des nutzbaren Settings-Viewports erreichbar; der gezeigte absichtlich ungültige Draftwert wird vollständig und ohne horizontal abgeschnittenen Content dargestellt. Kein Commit des Testwerts.
- **Realer Fund 22.09.2026:** Auf dem iPhone laufen Settings-Controls, Einheit, Validierungsbox und teilweise der Standard/Experte-Umschalter rechts über den Viewport hinaus. Die Seite ist absichtlich nicht horizontal scrollbar; dadurch wird Inhalt abgeschnitten und ist nicht erreichbar.
- **Root-Cause-Richtung:** der mobile Scrollcontainer ist auf vertikale Interaktion begrenzt (`overflow-x:hidden` / vertikaler Touch-Pfad), während einzelne Settings-Layoutzeilen eine Mindest-/Intrinsic-Breite oberhalb des Viewports behalten.
- **Zielvertrag V16.2.5:** Settings-Content muss bei 320/375/390/430 CSS-Pixel vollständig innerhalb des Viewports bleiben; horizontales Scrollen oder Pinch-Zoom sind kein Ersatz für responsives Layout. Lange Keys, Fehlermeldungen, Einheiten, Meta-Pills und Standard/Experte-Umschalter müssen umbrechen bzw. in eine mobile Layoutvariante wechseln. `scrollWidth <= clientWidth` ist als Regression-Gate abzudecken.
- **Abgrenzung:** keine Settings-Semantik-, Validation-, Persistenz- oder Regleränderung.

### ZEC-BL-UI-STATUS-003 – Speicherstatuskarten-Konsolidierung und reale Layout-Completion

- **Status:** OPEN / REAL_FIELD_PASS_WITH_UI_FOLLOWUP; `implementation_state=implemented_v16_2_5_plus_followup`; `technical_state=TECHNICAL_BUILD_PASS`; Releasebasis `V16.2.5 / v16.2.5-20260922`.
- **Standardkartenvertrag:** große signierte Istleistung ohne zusätzliche Richtungsbeschriftung; einteiliger Leistungsbalken Laden grün links→rechts / Entladen orange rechts→links; W/kW relativ zur belastbaren Maximalleistung ohne Prozentlabel; `Ladegrenze`/`Entladegrenze`; `Noch ladbar`/`Noch entladbar` als SOC-Prozentpunkte plus kWh nur bei belastbarer Kapazität.
- **Kapazitätspriorität:** reale/source-seitige usable/effective Kapazität → belastbare Geräte-/Templatekapazität → manueller Fallback → keine kWh. Keine scheinpräzisen Ersatzwerte.
- **V16.2.5 real bestätigt:** Desktop und reales iPhone zeigen keine Footer-/Content-Überdeckung; `Noch ladbar` steht lesbar in der rechten Detailspalte, Leistungsbeschriftung/-balken bleiben lesbar. Eine reale aktive `HIGH_SOC_CHARGE_LIMITED`-/Ladeannahme-Warnung wurde am 22.09.2026 sowohl eingeklappt als auch ausgeklappt beobachtet: Warnung bleibt sichtbar, Details sind lesbar und auf-/zuklappbar, regulärer Inhalt wird nicht überdeckt.
- **Neues reales UX-Finding 22.09.2026:** Bereits die eingeklappte V16.2.5-Warnungsbox vergrößert die Speicherkarte und dadurch die gesamte obere Kartenreihe deutlich. Das widerspricht dem erreichten Ziel hoher vertikaler Informationsdichte, obwohl die funktionale Warnungs-Evidenz selbst PASS ist.
- **Freigegebener Follow-up-Vertrag:** aktiver Warnzustand höhenneutral als Warning-Chip im vorhandenen Kartenkopf, vorzugsweise mit fachlicher Kurzbezeichnung (`Begrenzt`, `Ladeannahme` o. ä.); bei mehreren aktiven Warnungen aggregierter Hinweis/Anzahl. Details werden außerhalb des normalen Kartenflows geöffnet: Desktop als an der Karte verankertes nicht-layoutverschiebendes Popover, mobil als touch-taugliches Bottom-Sheet bzw. kompaktes Modal. Schließen der Details darf die aktive Warnung nicht verbergen. Hover allein reicht nicht; Touch/Tastatur müssen funktionieren. Keine schwebende Box darf regulären Karteninhalt verdecken.
- **Sequencing-/Releaseentscheidung:** Für diesen Follow-up wird kein eigener Hotfix-Zyklus erzwungen. Er ist verbindlicher isolierter Frontend-Subscope des nächsten ohnehin anstehenden Releases und blockiert die Fast-Capture-vs.-Adaptive-Entscheidung nicht.
- **Expert-Slice:** der V16.2.4-Primärspeicher-Slice `Strategie & Diagnose` bleibt erhalten; der vollständige kartenübergreifende Expertenmodus bleibt unter `ZEC-BL-UI-STATUS-EXPERT-001` offen.
- **Safety:** reine UI-/Diagnosedarstellung; keine Regler-, Command-, Safety- oder Recoveryänderung; bis zu einem Controllerrelease-spezifisch anders freigegebenen Scope bleibt die bestehende Reglersemantik unberührt.
- **Follow-up-Exit:** eingeklappte aktive Warnung erzeugt keine zusätzliche Karten-/Gridhöhe; geöffnete Details verschieben das Seitenlayout nicht; Warnexistenz bleibt permanent sichtbar; Desktop/Mobile/Keyboard/Touch und Mehrfachwarnungsfall regressionsgetestet.

### ZEC-BL-DIAG-OWNER-001 – Produktive Instance-Owner-Evidenz im Statussnapshot

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; `technical_state=TECHNICAL_BUILD_PASS`; Release `V16.2.5 / v16.2.5-20260922`.
- **Implementierungsstand 22.09.2026:** die fünf Instance-Owner-Felder sind im allgemeinen `ControllerState.snapshot()` ergänzt; Lock-/Owner-Semantik unverändert. Fokussierte Regression sowie vollständige Build-/Fresh-extract-Gates PASS.
- **Realer Exit 22.09.2026:** produktiver Snapshot bestätigt `INSTANCE_OWNER_ACTIVE=True`, `INSTANCE_OWNER_PID=39159`, `INSTANCE_OWNER_BUILD_ID=v16.2.5-20260922`. Damit ist der V16.2.4-Falschzustand `Owner nicht bestätigt` im realen V16.2.5-Pfad behoben, ohne Änderung der Instance-Lock-/Single-Owner-Semantik.
- **Realer Fund 22.09.2026:** Die produktive V16.2.4-Instanz läuft gesund und `ready=true`, aber `Controller & Schnittstellen` zeigt `Owner nicht bestätigt`, `Prozess —`, `Build —`. Der Feldsnapshot bestätigt `instance_owner_active=False`, `instance_owner_pid=None`, leere Build-ID.
- **Sourceverifikation:** `ZendureController.py` setzt Owner-Status/PID/Build-ID beim erfolgreichen Instance-Lock; `readiness_snapshot()` exportiert sie. Der allgemeine `ControllerState.snapshot()`-Pfad für `/status-view-data` übernimmt diese Felder jedoch nicht vollständig, wodurch ein falscher Diagnosezustand entsteht.
- **Zielvertrag V16.2.5:** Instance-Owner-Evidenz muss in allen relevanten Status-/Readiness-Snapshots konsistent sein; die UI darf eine real bestätigte produktive Instanz nicht als unbestätigt darstellen. Keine Lock-/Single-Owner-Semantikänderung, nur Snapshot-/Diagnosekonsistenz.
- **Exit:** Regression über `/health`, `/ready`, `/status` und `/status-view-data` bzw. deren reale Datenpfade; produktive Ownerdaten konsistent, fehlende Ownerdaten weiterhin ehrlich als unbestätigt dargestellt.

### ZEC-BL-GRAPH-GAP-001 – echte Datenlücken unterbrechen numerische Graphlinien

- **Status:** OPEN / REAL_FIELD_PASS_WITH_UI_FOLLOWUP; `implementation_state=partial`; `technical_state=TECHNICAL_BUILD_PASS`; Releasebasis `V16.2.5 / v16.2.5-20260922`.
- **V16.2.5 real bestätigt:** bestätigte Nicht-AVAILABLE-Evidence erzeugt renderseitige `null`-Breaks; über bekannter Controller-Downtime ist die numerische Linie tatsächlich sichtbar unterbrochen. Es entstehen keine synthetischen Messwerte. Damit ist der primäre Graph-Gap-Fix real PASS.
- **Verbleibender Interaktionsfehler:** Beim Hover/Klick innerhalb einer bestätigten Lücke zeigt das synchronisierte Cursor-/Tooltip-Overlay weiterhin Werte des nächsten realen Messpunkts außerhalb der Lücke; der Inspector liefert zwar keine Messwerte, rendert bei `actual_ms=null` aber `01.01.1970, 01:00:00` statt eines ehrlichen Gap-/Empty-States.
- **Sourceverifikation:** `syncPlugin` und `updateCursorCards()` verwenden `nearestDatasetPoint()`/`nearestIndex()` ohne Evidence-Gap-Gate; die `y:null`-Breaks verhindern die Linie, nicht das Nearest-Sample-Overlay. `renderInspector()` wandelt `null` über `Number(null)` in `0` und erzeugt damit den Epoch-Zeitwert.
- **Follow-up-Zielvertrag:** Innerhalb bestätigter `GAP`/`NOT_INSTRUMENTED`/`PURGED_BY_RETENTION`-Intervalle dürfen Cursor, Tooltip, Marker und Inspector keinen realen Nachbarpunkt an den Cursorzeitpunkt projizieren. Stattdessen Gap-/Empty-State ohne synthetische Werte; außerhalb bestätigter Lücken bleibt die bisherige Nearest-Interaktion unverändert. Normale Sampling-Jittertoleranz darf nicht unnötig in Gap-Semantik umklassifiziert werden.
- **Sequencing-/Releaseentscheidung:** Der Restfehler ist ein isolierter UI-/Interaktionsdefekt und kein Daten-, Regler-, Command-, Safety- oder Recoveryfehler. Wegen der real bereits korrekten Linienunterbrechung wird kein eigener V16.2.6-Hotfix-Zyklus erzwungen. Der Fix ist verbindlicher, eigenständig regressionsgeprüfter Frontend-Subscope des nächsten ohnehin anstehenden Releases und blockiert die Fast-Capture-vs.-Adaptive-Entscheidung nicht.
- **Exit:** Query-/Frontend-Regression mit Vorher-/Nachherpunkten und echtem Gap; Linie, Hover/Cursor, Tooltip, Inspector und Coverage/Evidence semantisch konsistent; im nicht verfügbaren Intervall keine Nearest-Sample-Werte oder Marker am Cursor; kein Epoch-Nullzeit-Fallback; außerhalb des Gaps unveränderte Interaktion.

### ZEC-BL-UI-STATUS-EXPERT-001 – vollständiger Statusseiten-Experten-/Diagnosemodus

- **Status:** OPEN; `implementation_state=partial`; Roadmapposition nach V16.2.4 weiterhin nicht automatisch festgelegt.
- **V16.2.4-Stand:** `UI_MODE=standard|expert` steuert nun auf der Primärspeicherkarte einen echten sichtbaren Superset-Slice. Im Expertenmodus werden `Strategie & Diagnose` mit Harmonisierung, Harvest/Strategie, diagnostischem usable SOC und Quellenstatus kompakt gerendert; die Standardkarte bleibt unverändert schlank.
- **Vertrag:** Expert bleibt Superset von Standard. Kritische Warnungen und Standardinformationen verschwinden nicht; der Modus ändert niemals Regler-/Command-/Safety-Semantik und erzeugt keine neue externe I/O.
- **Weiter offen:** der kartenübergreifende Completion-Scope mit vertieftem Status-Snapshot, Freshness/Validity, Reason-/Limiter-/Sollwertpipeline, Command-Effect/Readback/Resync, Timing/Runtime, Events und kontextbezogenen Diagnosezugängen. Nur vorhandene belastbare Daten dürfen exponiert werden.
- **Interaktion/Privacy:** technische Details benötigen erkennbare responsive Zugänge; Hover allein reicht nicht. Secrets und rohe vertrauliche Konfiguration bleiben ausgeschlossen.
- **Exit des Gesamtpunkts:** `UI_MODE` wirkt nachweisbar kartenübergreifend; Expert ist vollständiges Superset; responsive/Accessibility-/Regressionstests decken beide Modi und Moduswechsel ab.

### ZEC-BL-DIAG-FIELD-001 – Feldabnahme-Tool an Release- und Readinessvertrag synchronisieren

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; Release `V16.2.0 / v16.2.0-20260920`; **kein eigener Hotfix-Release**.
- **Fund V16.1.0 Realfeldabnahme 20.09.2026:** `tools/v16_field_acceptance.py` prüfte bei `SUPPORTED_UPDATE` noch hart auf V16.0.1 / `v16.0.1-20260915`, obwohl der V16.1.0-Installer korrekt ausschließlich V16.0.2 / `v16.0.2-20260917` als Updatequelle akzeptierte. Dadurch entstand ein falsches `install_report=FAIL` trotz realem Report `status=ok` für V16.0.2 → V16.1.0 und exakt verifiziertem Rollback-Backup.
- **Zweiter historischer Vertragsunterschied:** das Feldtool verlangte im Normalpfad strikt `ready=true`, während der Installer bereits eine gemeinsame releasespezifische READY/TRANSITIONAL/REJECT-Klassifikation besaß.
- **Umsetzung V16.2.0:** erwartete Updatequelle wird aus dem Installer-/Releasevertrag abgeleitet; Feldtool und Installer verwenden dieselbe sichere Readiness-Akzeptanzklassifikation, ohne Runtime-`/ready` abzuschwächen.
- **Realer Exit 20.09.2026:** reales Update V16.1.0 → V16.2.0 mit `FULL_READY`; Feldtool meldete `controller_ready: FULL_READY`, `controller_readiness_acceptance: READY:FULL_READY`, `install_report: PASS` und `rollback_backup_integrity: RELEASE_BACKUP_EXACT`; Gesamtfeldabnahme PASS.

### ZEC-EV-DEP-001 – reale Clean-Fresh-/FIRST_INSTALL_SETUP-/Uninstaller-Abnahme

- **Status:** DEFERRED durch Nutzerentscheidung vom 19.09.2026.
- Risiko bewusst akzeptiert; weiterhin erforderlich, aber bis auf weiteres kein Entwicklungsblocker.
- Offener Realpfad: read-only Uninstaller-Preflight, User-Data-Backup/Fresh-Reset, CLEAN_FRESH_INSTALL, Fresh Install, FIRST_INSTALL_SETUP, erster Settings-Commit, Restart NORMAL, Feldabnahme, abschließender Reset/Restore.

## 5. Dauerhaft geschlossene / supersedierte Entwicklungshistorie

Die folgenden Einträge bleiben bewusst im Master-Ledger. Die Liste ist auf die aus Release-Tree und Chat-Export belastbar recoverbaren größeren Schritte ausgerichtet.

| Ledger-ID | Release/Phase | Status | recoverbarer Abschlussinhalt |
|---|---|---|---|
| `ZEC-HIST-BASE-001` | frühe V12-Entwicklung | SUPERSEDED | lokale MQTT-/Zendure-Steuerung, frühe Shelly-/Graph-/Statusgrundlagen; in spätere Architektur überführt |
| `ZEC-HIST-MEAS-V3` | V12.9.x | SUPERSEDED | Measurement V3 als Diagnose-/Historienbasis; später durch V4 ersetzt |
| `ZEC-HIST-MEAS-V4` | V12.10/V12.13 | CLOSED | Measurement V4 als produktiver Diagnosevertrag; seit V12.13.0 V4-only Runtime, V3 nur offline/read-only |
| `ZEC-HIST-RC6` | V12.11.2-RC6 | CLOSED | UI-/Diagnose-Hotfix, Operational-Event-Semantik und Legacy-Statusreferenz |
| `ZEC-HIST-RC7` | V12.11.2-RC7 | CLOSED | MQTT-Freshness-0s-Fehler, Command-Lifecycle-/Timing-/Journaldiagnose |
| `ZEC-HIST-RC8` | V12.11.2-RC8 | CLOSED | SOC-Darstellung, stale Warnungsauflösung und UI/Diagnose/Installationsstabilisierung |
| `ZEC-HIST-RC9` | V12.11.2-RC9 | CLOSED | Replay-/Timing-/Status-/Logging-Diagnosepolish |
| `ZEC-HIST-RC10` | V12.11.2-RC10 | CLOSED | topologiefähige Statusseite und passiver Live-Preview-Dienst |
| `ZEC-HIST-RC11` | V12.11.2-RC11 | CLOSED | 0-W-Neutralisierung, Full-State-Resync, intentbasierter Effect-Timer, unabhängige Wirkungsklassifikation |
| `ZEC-HIST-RC12` | V12.11.2-RC12 | CLOSED | SmartMode-/Flash-Schutz, Command-State-Rücklesung, getrennte Netz-/Pack-/Offgrid-Powersemantik |
| `ZEC-HIST-RC13` | V12.11.2-RC13 | CLOSED | Neutralisierungs-Deduplizierung, Command-State-Gate, Trackingtoleranz, Publish-Evidenz |
| `ZEC-HIST-RC14` | V12.11.2-RC14 | CLOSED | High-SOC-Ladeannahme/Taper-Reklassifikation ohne Zielwertformeländerung |
| `ZEC-HIST-RC15` | V12.11.2-RC15 | CLOSED | Publish-Historie vs. Geräte-Readback getrennt, Late-Effect-/Recovery-Guard-Härtung |
| `ZEC-HIST-RC16` | V12.11.2-RC16 | CLOSED | `SMA_FULL_OR_IDLE` Delta→Absolutzielkorrektur |
| `ZEC-HIST-RC17` | V12.11.2-RC17 | CLOSED | Harvest 0-W-Netzziel/Export-Capture-Untergrenze, High-SOC-/Near-Limit-Allokation |
| `ZEC-HIST-RC18` | V12.11.2-RC18 | CLOSED | asynchroner lokaler Zendure-API-Worker; keine externe I/O im Regelzyklus |
| `ZEC-HIST-RC19` | V12.11.2-RC19 | CLOSED | Status-/Diagnose-Stabilisierung, Requested-vs-Applied, API-Worker-Sichtbarkeit |
| `ZEC-HIST-RC20` | V12.11.2-RC20/Fix6 | CLOSED | SettingsRegistry/UI, Config-Runtime, Preview/Commit, Restart, Last-Good/Recovery-Unterbau |
| `ZEC-HIST-V12_11_3` | V12.11.3 | CLOSED | Installer-Readiness-Akzeptanz sicherer transienter Commandzustände |
| `ZEC-HIST-V12_11_4` | V12.11.4 | CLOSED | mobile Settings/Modal/Event-Reconciliation/Warnzähler |
| `ZEC-HIST-V12_11_5` | V12.11.5 | CLOSED | Desktop-Settings-Shell, Nacht-HH:MM-Compoundfelder, Preview-422-UX, Adminaktionen |
| `ZEC-HIST-V12_11_6` | V12.11.6 | CLOSED | Settings-/Status-UX, lokale Validation, Default/Reset-Semantik, sichere Sentinelwerte |
| `ZEC-HIST-V12_11_7` | V12.11.7 | CLOSED | explizite Default-Provenienz/Reset-Policy und fail-closed FIRST_INSTALL_SETUP-Vertrag |
| `ZEC-HIST-V12_12_0` | V12.12.0 | CLOSED | strukturierte Settings-Hilfe & Guided Configuration |
| `ZEC-HIST-V12_12_1` | V12.12.1 | CLOSED | Help-/Terminologie-/Such-/Mobile-Quality-Fix |
| `ZEC-HIST-V12_12_2` | V12.12.2 | CLOSED | Single-Owner, monotone/fresh Harvest-Entry, Limiter-/Manifest-/SOC-UI-Härtung |
| `ZEC-HIST-V12_13_0` | V12.13.0 | CLOSED | Measurement V4-only / Legacy-V3-Runtime-Cleanup |
| `ZEC-HIST-V13_0_0` | V13.0.0 | CLOSED | benannte Konfigurationsstände, Import/Export, Portabilität, historische Config-/SOC-Timeline |
| `ZEC-HIST-V13_0_1` | V13.0.1 | CLOSED | Readiness-/Releaseidentitätsfix der V13-Linie |
| `ZEC-HIST-V13_0_2` | V13.0.2 | CLOSED | Config-State-/CSRF-/SQLite-Writer-/Backfill-Härtung |
| `ZEC-HIST-V13_0_3` | V13.0.3 | CLOSED | Config-Preview-UX-Hotfix und Feldabschluss vor Graph-Hauptblock |
| `ZEC-HIST-V14_0_0` | V14.0.0 | CLOSED | Graph Core V3, relationale Persistenz, Query/Catalog, Coverage/Evidence/Retention-Ledger, Inspector/Command-Follow/Episodenvergleich, Rebuild/Cutover |
| `ZEC-HIST-V14_1_0` | V14.1.0 | CLOSED | Greenfield Graph-UI/Analyse-Workspace |
| `ZEC-HIST-V14_1_1` | V14.1.1 | CLOSED | Installer-/Runtime-Root-Fix für Graphassets |
| `ZEC-HIST-V14_1_2` | V14.1.2 | CLOSED | explizite Selection, Zeitraum-/Episodenvergleich, synchronisierte Interaktion/Evidence-Segmente |
| `ZEC-HIST-V14_1_3` | V14.1.3 | CLOSED | Graph-State-History-Repair und Status-SOC-Responsiveness |
| `ZEC-HIST-V14_1_4` | V14.1.4 | CLOSED | Graph-/Status-Performance und UX-Polish |
| `ZEC-HIST-V15_0_0` | V15.0.0 | CLOSED | source-neutrale Primärspeicherarchitektur, EVCC/custom/Modbus-Template, read-only Modbus/TCP |
| `ZEC-HIST-V15_0_1` | V15.0.1 | CLOSED | Graph-/Analyse- und Primary-Settings-UX-Härtung |
| `ZEC-HIST-V15_0_2` | V15.0.2 | CLOSED | Graph-Interaktionsbugfixes / Detailausschnitt / Command-Follow-Layout |
| `ZEC-HIST-V15_0_3` | V15.0.3 | CLOSED | technisches Datenblatt dauerhaft in Releasevertrag integriert |
| `ZEC-HIST-V16_0_0` | V16.0.0 | CLOSED IMPLEMENTATION | brokerneutraler Installer/Fresh-Install/Uninstaller/Support-Grundvertrag; Real-Fresh-Evidenz siehe `EV-DEP-001` |
| `ZEC-HIST-V16_0_1` | V16.0.1 | CLOSED | Installer-Paketidentitäts-Hotfix |
| `ZEC-BL-DEP-001` | V16.0.2 | CLOSED | fail-closed Cleanup verwaister Python-Caches entfernter Quellbäume; realer Updatepfad bestätigt |
| `ZEC-HIST-V16_1_0` | V16.1.0 | CLOSED | SMA Sunny Island 31009 Capability, separate Freshness/Diagnose/usable SOC, source-neutrale Primärspeicher-Namenshygiene; keine Reglerwirkung; reales Update/Block-A am 20.09.2026 feldabgenommen. Rohes Feldtool `23 PASS / 2 FAIL`; beide FAILs als Toolvertrag-Abweichungen unter `ZEC-BL-DIAG-FIELD-001` belegt. |

## 6. No-Drop-/Reconciliation-Vertrag für dieses Ledger

Vor dem Entfernen/Archivieren einer Übergabe, Spezifikation, Work-Chat-Delta-Datei oder historischen Projektquelle müssen alle Planungsmarker und IDs gegen dieses Ledger reconciliiert werden. Mindestens zu prüfen:

```text
Backlog / Roadmap / offen / Restpunkt / später / perspektivisch
Nicht Bestandteil / deferred / TODO / Folgeblock / S1..S9
```

Jeder Fund benötigt genau eine Auflösung:

1. bestehender Master-Eintrag,
2. neuer Master-Eintrag, oder
3. explizit belegtes `CLOSED`, `SUPERSEDED` oder `REJECTED`.

Ein ungeklärter Fund bedeutet **BACKLOG_NO_DROP_GATE = FAIL** und blockiert die Quellenbereinigung.

## 7. Release-Evidenz und Changelog

Ab dem ersten Release nach dieser Kanonisierung wird eine Snapshot-Fassung dieses Master-Ledgers im Release-Tree mitgeliefert:

```text
docs/ZEC_Master_Backlog.md
```

Sie ist Entwicklungs-/Roadmap-Evidenz. Ein Release-Changelog kann aus den seit dem Vorgänger neu `CLOSED` gesetzten bzw. releasezugeordneten Einträgen abgeleitet werden. Das Changelog ersetzt das Ledger nicht; offene, zurückgestellte, supersedierte und verworfene Punkte bleiben im Master erhalten.

## 8. Recovery-Provenienz 19.09.2026

Der aktuelle Ledgerstand wurde aus folgenden Ebenen reconciliiert:

1. aktuelle kanonische Projektquellen;
2. verifiziertes V16.0.2-Release-ZIP und darin erhaltene Spezifikationen/Release-/Übergabeunterlagen;
3. `conversations.json` mit 34 systematisch geprüften ZEC-/Zendure-relevanten Chats;
4. aktueller V16.0.2-Implementierungsgegencheck.

Details: `ZEC_34_CHAT_RECONCILIATION_20260919.md`.

## 9. Roadmapentscheidung 20.09.2026 – Provenienz

Nutzerentscheidung im ZEC-Projekt am 20.09.2026 nach Recovery/Neuaufstellung des Master-Ledgers:

```text
(S3 + adaptive Strategie + Kapazitätsgewichtung)
→ Battery Care
→ Storage
→ Graph→Analyse-Handoff
→ Counterfactual Simulation
→ Szenarioeditor
→ Multi-Zendure-Commandbetrieb
→ Release/CI-Hardening
```

Begründung für die Zusammenführung des ersten Blocks: Im parallelen Projektchat **„Installierte PV Anlage“** wird das grundlegende Lernmodell für adaptive Lade-/SOC-/Ertragsstrategie und Kapazitätsgewichtung entwickelt; saisonale Faktoren und dynamische Tagesprofile sind Teil dieser Konzeption. Die finale Abdeckung ist erst mit der dortigen Abschlussübergabe verbindlich festzustellen. Bis dahin werden keine historischen Child-Scopes als erledigt markiert.

## 10. Projektquellen-Reconciliation 21.09.2026

Der V16.2.3-Technical-Freeze-Stand enthält maschinell inventarisiert **81 eindeutige stabile `ZEC-BL`/`ZEC-EV`/`ZEC-HIST`-IDs**. Die Post-Freeze-Reconciliation nach realer V16.2.3-Installation und manueller UI-Prüfung erhält sämtliche 81 IDs und ergänzt genau eine neue ID:

1. `ZEC-BL-UI-SETTINGS-001` – real bestätigter Settings-Webmodell-/Availability-Defekt für aktuelle produktive V16.2.0-Felder.

Fortgeschrieben, aber nicht entfernt oder umbenannt wurden insbesondere:

- `ZEC-BL-DEP-003` → `CLOSED / REAL_FIELD_PASS` durch erfolgreichen V16.2.3-Updatepfad;
- `ZEC-BL-DEP-004` → `CLOSED / REAL_FIELD_PASS` durch erfolgreichen V16.2.3-Preflight/Update;
- `ZEC-BL-UI-STATUS-003` → `OPEN`, `implementation_state=partial`, weil die manuelle UI-Prüfung nach automatischem PASS einen realen Surface-Defekt fand;
- `ZEC-BL-UI-STATUS-EXPERT-001` bleibt `OPEN / partial` und erhält den realen Primärspeicher-Superset-Befund;
- `ZEC-BL-CTRL-FASTCAP-001`, `ZEC-BL-CTRL-ADAPTIVE-001` und alle Child-/Folgepunkte bleiben vollständig erhalten; ihre nächste Reihenfolge wird nach dem unmittelbaren UI-/Settings-Bugfix explizit entschieden.

Damit enthält dieses Ledger nach Kanonisierung **82 eindeutige stabile IDs**. Keine Vorgänger-ID wurde entfernt. Die im Handover inventarisierten Planungsmarker sind entweder einem bestehenden Eintrag oder `ZEC-BL-UI-SETTINGS-001` zugeordnet.

**BACKLOG_NO_DROP_GATE = PASS**

### V16.2.4 Build-Reconciliation 21.09.2026

Der freigegebene V16.2.4-Block erzeugt **keine neue Ledger-ID**. Alle 82 zuvor kanonisierten stabilen IDs bleiben erhalten. Fortgeschrieben werden ausschließlich bestehende Punkte: `ZEC-BL-UI-SETTINGS-001`, `ZEC-BL-UI-STATUS-003`, `ZEC-BL-UI-STATUS-EXPERT-001` und `ZEC-BL-DEP-002`. Fast Capture, Adaptive samt Child-IDs, usable-SOC Block B, Primary Metadata und Battery Care bleiben unverändert recoverbar.

**BACKLOG_NO_DROP_GATE = PASS (82/82 IDs erhalten)**

### V16.2.4 Real-Field-/V16.2.5-Hotfix-Reconciliation 22.09.2026

Die reale V16.2.4-Abnahme erhält alle bisherigen **82** stabilen IDs und ergänzt für die manuell bestätigten neuen Defektklassen genau drei IDs:

1. `ZEC-BL-UI-SETTINGS-MOBILE-001`;
2. `ZEC-BL-DIAG-OWNER-001`;
3. `ZEC-BL-GRAPH-GAP-001`.

`ZEC-BL-UI-SETTINGS-001` und `ZEC-BL-DEP-002` werden durch reale V16.2.4-Evidenz auf `CLOSED / REAL_FIELD_PASS` fortgeschrieben. `ZEC-BL-UI-STATUS-003` bleibt erhalten und wird wegen der realen Karten-/Warnungsbefunde in den freigegebenen V16.2.5-Hotfix überführt. `ZEC-BL-UI-STATUS-EXPERT-001` bleibt `OPEN / partial`. Fast Capture, Adaptive samt Child-IDs, usable-SOC Block B, Primary Metadata, Battery Care und alle übrigen Vorgängerpunkte bleiben unverändert recoverbar.

Damit enthält das Ledger **85 eindeutige stabile IDs**. Keine Vorgänger-ID wurde entfernt oder umbenannt.

**BACKLOG_NO_DROP_GATE = PASS (82/82 Vorgänger-IDs erhalten; 3 neue IDs; Gesamt 85)**

### V16.2.5 Real-Field-Reconciliation 22.09.2026

Die reale Installation V16.2.4 → V16.2.5 und der konsolidierte automatische Feldlauf sind PASS. Die übergebene Evidence weist `controller_ready=WARN LIMIT_READBACK_CONVERGENCE`, aber `controller_readiness_acceptance=PASS TRANSITIONAL:LIMIT_READBACK_CONVERGENCE` aus; das entspricht dem bestehenden Readinessvertrag. Evidence-Archiv-SHA256: `b8b188f487f05eac5fcba8d94614ecb17731c88389708e84425113cf43cad239`.

Die anschließende manuelle Sichtprüfung und Nutzerentscheidung führen ohne neue Ledger-ID zu folgenden Fortschreibungen:

- `ZEC-BL-UI-SETTINGS-MOBILE-001` → `CLOSED / REAL_FIELD_PASS`;
- `ZEC-BL-DIAG-OWNER-001` → `CLOSED / REAL_FIELD_PASS`;
- `ZEC-BL-UI-STATUS-003` → funktionale V16.2.5-Warnungsdarstellung real PASS; neuer UX-Follow-up für höhenneutralen Header-Warning-Chip mit Desktop-Popover/Mobile-Bottom-Sheet bleibt `OPEN`;
- `ZEC-BL-GRAPH-GAP-001` → sichtbare Linienunterbrechung real PASS; Gap-aware Cursor-/Tooltip-/Inspector-Semantik bleibt `OPEN`.

Der Nutzer entscheidet am 22.09.2026 ausdrücklich, für die beiden isolierten UI-Restpunkte keinen eigenen Hotfix-Zyklus zu erzwingen. Beide werden verbindlich im nächsten ohnehin anstehenden Release separat regressionsgeprüft mitgeführt und blockieren die Fast-Capture-vs.-Adaptive-Sequencing-Entscheidung nicht. Damit ist das Sequencing-Gate freigegeben, ohne eine Reihenfolge vorwegzunehmen.

Alle bisherigen **85** stabilen IDs bleiben erhalten; keine ID wird entfernt, umbenannt oder durch die neue Feldbeobachtung ersetzt.

**BACKLOG_NO_DROP_GATE = PASS (85/85 IDs erhalten; 0 neue IDs)**

### Fast-Capture-Sequencing-/Revalidation-Reconciliation 22.09.2026

Die neutrale Gegenüberstellung Fast Capture versus Adaptive ist abgeschlossen. Der Nutzer bestätigt die technische Entkopplung und legt **Fast Capture A400/R100 als nächsten Controllerblock** fest. Die eingefrorene Produktionsspezifikation wurde gegen V16.2.5 revalidiert und um die releaseintegrierte Feldverifikationspflicht ergänzt. Adaptive bleibt mit sämtlichen Child-IDs erhalten und wird nach Bereitstellung des Fast-Capture-Releases als eigener Spezifikationsblock fortgeführt.

Es entsteht keine neue Ledger-ID: Die Verifikationslogik ist Bestandteil des Exit-/Evidenzvertrags von `ZEC-BL-CTRL-FASTCAP-001`, und die Adaptive-Spezifikationslücke bleibt unter `ZEC-BL-CTRL-ADAPTIVE-001` samt Child-IDs erhalten. Alle bisherigen **85** stabilen IDs bleiben unverändert.

**BACKLOG_NO_DROP_GATE = PASS (85/85 IDs erhalten; 0 neue IDs)**



### V17.0.0 Fast-Capture Checkpoint A/B Reconciliation 22.09.2026

Der freigegebene V17.0.0-Fast-Capture-Block bleibt unter der bestehenden ID `ZEC-BL-CTRL-FASTCAP-001`; es entsteht keine neue Ledger-ID. Checkpoint A implementiert Controllerkern/State und bestand die fokussierte Differential-/Safetyregression mit **110 Tests + 11 Subtests PASS**. Checkpoint B ergänzt Settings-/Validationvertrag, Measurement-V4-Evidenz, `tools/fast_capture_field_analysis.py`, `tools/v17_field_acceptance.py` und die Analysis-Package-Integration; die fokussierte Checkpoint-B-Regression bestand mit **114 Tests + 640 Subtests PASS**.

Die V16.2.5-Produktivbasis bleibt bis Release-/Feldfreigabe unverändert. Die zwei bekannten Frontend-Follow-ups bleiben unter `ZEC-BL-GRAPH-GAP-001` und `ZEC-BL-UI-STATUS-003` erhalten und bilden den nächsten isolierten Entwicklungscheckpoint. Vollständige Regression, ResourceWarning-, Syntax-, Manifest-, Fresh-extract- und Releasegates sind noch ausstehend; daher **kein TECHNICAL BUILD PASS**.

Checkpoint C setzt die zwei separat freigegebenen Frontend-Follow-ups um: Gap-aware Cursor/Marker/Inspector/Command-Follow/Comparison-Hover sowie den höhenneutralen Zendure-Warning-Chip mit Desktop-Popover/Mobile-Bottom-Sheet. Die fokussierte Checkpoint-C-Regression besteht mit **12 Tests PASS**.

**BACKLOG_NO_DROP_GATE = PASS (85/85 IDs erhalten; 0 neue IDs)**


### V17.0.0 Technical-Build-Pass Reconciliation 22.09.2026

Der freigegebene Fast-Capture-Releaseblock erreicht **TECHNICAL BUILD PASS**. Vollständige Regression: **156 Testdateien / 1162 Tests + 706 Subtests PASS**; identischer `-W error::ResourceWarning`-Lauf ebenfalls **1162 + 706 PASS**. Bash-Syntax 13/13, Browser-JS 3/3, Python-Compileall, Deployment-Harness 11/11, Datenblatt-Gate, Build-Evidence, Release-Hygiene, Source-Manifest und Fresh-extract-Manifestverifikation sind PASS.

Finales Paket: `zendure_controller_v17_0_0.zip`, SHA256 `5f8a72edd00c32f0c6ce71871b51cfe479dc1cf465636402bc364e9608c45712`. `controller_logic.py` SHA256 `113cb9cc60475cb59294bf07ab750e63580b59112f178948b7e386fd0539b031`.

`ZEC-BL-CTRL-FASTCAP-001` bleibt bis realer Shadow-/Active-Wirkungsevidenz **IN_PROGRESS / TECHNICAL_BUILD_PASS / FIELD_PENDING**. Die beiden UI-Follow-ups sind technisch im Release enthalten, reale Sichtprüfung nach Installation bleibt Feldgate. V16.2.5 bleibt bis erfolgreicher V17.0.0-Installation die reale Runtimebasis. Adaptive bleibt unverändert als nachgelagerter Spezifikationsblock erhalten.

**BACKLOG_NO_DROP_GATE = PASS (85/85 IDs erhalten; 0 neue IDs)**


### V17.0.0 Packaging-Reject / V17.0.1 Technical-Build-Pass Reconciliation 22.09.2026

`ZEC-BL-CTRL-FASTCAP-001` bleibt dieselbe stabile Ledger-ID; es entsteht keine neue Produkt-ID. Der erste reale V17.0.0-Installerlauf auf der V16.2.5-Runtime wurde im Paket-Preflight **vor jeder Produktivmutation** abgewiesen, weil das ausgelieferte ZIP den vom Installervertrag geforderten Root `zendure_controller_v17_0_0/` nicht enthielt. V17.0.0 ist damit zurückgezogen. Der Befund erweitert den bestehenden Deployment-/Release-Evidenzvertrag, ohne Fast-Capture-Semantik zu ändern.

V17.0.1 korrigiert Releaseidentität, Packaging und Paketgate. `tools/release_package.py` erzwingt beim Build und Verify den kanonischen ZIP-Root; Regression enthält Positiv- und rootless-Negativtest. Technical Exit: **157 Testdateien, 1164 Tests + 706 Subtests PASS**, identischer ResourceWarning-Lauf, Datenblatt/Build-Evidence/Hygiene/Manifest/Browser-JS/Bash/Compile/Deployment-Harness PASS sowie finales Fresh-Extract mit erwarteter Rootstruktur und 921/921 Manifestdateien PASS. `ZEC-BL-CTRL-FASTCAP-001` bleibt bis realer Shadow-/Active-Wirkungsevidenz **IN_PROGRESS / TECHNICAL_BUILD_PASS / FIELD_PENDING**. V16.2.5 bleibt bis erfolgreicher V17.0.1-Installation reale Runtimebasis.

**BACKLOG_NO_DROP_GATE: PASS – 85/85 stabile IDs erhalten; keine neue ID erforderlich.**
