# ZEC – Master-Backlog & Roadmap

**Stand:** 21.09.2026  
**Status:** kanonische, persistente Entwicklungsledger- und Roadmap-Autorität  
**Produktbasis:** V16.2.3 / `v16.2.3-20260921` (TECHNICAL BUILD PASS; reale V16.2.3-Update-Feldabnahme noch offen; Build-Evidence-/Preflight-Hotfix nach realem mutationsfreiem V16.2.2-Preflight-Fail; letzte reale Feldbasis V16.2.0)

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

**Roadmapentscheidung vom 20.09.2026:** Die bisher getrennten Punkte `ZEC-BL-CTRL-S3-001`, `ZEC-BL-CTRL-001` und `ZEC-BL-CTRL-CAP-001` werden für die nächste Controllerentwicklung unter `ZEC-BL-CTRL-ADAPTIVE-001` als gemeinsamer Entwicklungsblock geführt. Die drei Child-IDs bleiben vollständig erhalten und müssen beim Abschluss einzeln reconciliiert werden. Hintergrund ist die laufende Lernmodell-/Pretrainer-Konzeption im Projektchat **„Installierte PV Anlage“**, in der saisonale Faktoren, dynamische Tagesprofile, SOC-/Ertragsstrategie und Kapazitätsgewichtung gemeinsam modelliert werden. Ein separater vorgelagerter S3-Release soll dadurch vermieden werden.

Die priorisierte Reihenfolge lautet ab dieser Entscheidung:

1. **ZEC-BL-CTRL-ADAPTIVE-001 – gemeinsamer adaptiver Reglerblock (`S3 + CTRL-001 + CTRL-CAP-001`).** Die finale Implementierung beginnt erst nach einer belastbaren Übergabe der laufenden Lernmodell-/Pretrainer-Konzeption. S3 wird dabei nicht gestrichen, sondern als verpflichtender Compatibility-/Migrationsteil aufgenommen. Der produktive allgemeine Simulator `SIM-001` ist kein zwingender Vorläufer; der Entwicklungsblock selbst benötigt jedoch belastbare Offline-/Replay-/Pretrainer-/Shadow-/Differential-Evidenz.
2. **ZEC-BL-BATCARE-001 – Battery Care / Winter- und Reserve-SOC-Erhaltung.** Wegen der zeitnahen Winterrelevanz unmittelbar nach dem adaptiven Block. Vor Implementierung ist aus dem erhaltenen Brainstorming eine explizit freigegebene Spezifikation zu erstellen.
3. **ZEC-BL-STORAGE-001 – Measurement-/SQLite-Storage-Lifecycle.** S4/S5/S6/S7/S9 gegen die aktuelle Codebasis inventarisieren und in sicheren Stufen umsetzen; kein destruktives Enforcement vor nachgewiesener Restore-/Protection-/Coverage-Sicherheit.
4. **ZEC-BL-ANALYSIS-HANDOFF-001 – Graph → Analyse-Service.** Markierte reale Zeitfenster reproduzierbar an den bestehenden Analysedienst übergeben.
5. **ZEC-BL-SIM-001 – kontrafaktische Regler-Simulation.** Reale historische Situationen mit alternativen Reglerparametern durchspielen und Reality-vs-Simulation vergleichbar machen.
6. **ZEC-BL-SCENARIO-001 – allgemeiner Szenarioeditor** für synthetische Situationen, getrennt von historischer Counterfactual-Simulation.
7. **ZEC-BL-MULTI-001 – echter Multi-Zendure-Command-/Regelpfad.** Darstellung mehrerer Entities existiert; echte Befehlsverteilung bleibt separat.
8. **ZEC-BL-REL-001 – repo-zentrierter/reproduzierbarer Releaseprozess / CI.** Perspektivisch automatisieren, ohne aktuelle Sicherheitsgates abzuschwächen.

Querschnittlich bleiben `ZEC-BL-DEP-002`, `ZEC-BL-PRIMARY-METADATA-001`, Diagnose-/Command-Langzeitevidenz, Lernwerkzeugabgleich und Storage-Langzeitperformance mitzunehmen. `ZEC-BL-DEP-002` erhält weiterhin keinen eigenen Release und wird beim nächsten geeigneten Implementierungsrelease gebündelt.

`ZEC-BL-UI-STATUS-EXPERT-001` ist als wiederhergestellter offener UI-Completion-Punkt dauerhaft im Ledger enthalten, erhält aber **noch keine Position in der priorisierten Reihenfolge**, solange der Nutzer seine Einordnung gegenüber den oben priorisierten Entwicklungsblöcken nicht ausdrücklich festgelegt hat.

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

- **Status:** OPEN; Controller-Implementierung noch nicht begonnen, Design-/Lernmodellarbeit läuft als Vorarbeit im Projektchat **„Installierte PV Anlage“**.
- **Rolle:** Roadmap-/Umbrella-Eintrag für `ZEC-BL-CTRL-S3-001`, `ZEC-BL-CTRL-001` und `ZEC-BL-CTRL-CAP-001`. Die Child-IDs bleiben eigenständig erhalten und dürfen durch die Zusammenführung nicht verschwinden.
- **Entscheidung 20.09.2026:** S3 nicht separat vorab implementieren. Saisonale Faktoren und dynamische Tagesprofile sollen mit der adaptiven Lade-/SOC-/Ertragsstrategie sowie der weichen Kapazitätsgewichtung in einem konsistenten Regelmodell zusammengeführt werden, sofern die finale Lernmodell-Übergabe dies bestätigt.
- **Pflicht vor Sourceänderung:** Die Übergabe aus der Lernmodell-/Pretrainer-Arbeit muss mindestens eine Mapping-Matrix liefern: vorhandene S3-Settings → weiter aktive Nutzervorgabe / Modellinput / deterministischer Fallback / deprecated; Abdeckung von `CTRL-001`; Abdeckung von `CTRL-CAP-001`; Lernzustand/Persistenz/Reset; Confidence/Fallback; Offline-/Replay-/Shadow-/Differential-Evidenz; Safety-/Hardwaregrenzen.
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

- **Status:** OPEN; `implementation_state=none`, Produktionsspezifikation vollständig.
- **Provenienz:** Pretrainer V0.5 -> V0.6.1 und Freeze-Spezifikation vom 19.09.2026.
- **Scope:** Fast-Overlay ausschließlich für `FULL_IDLE` und `NEAR_LIMIT`; `RESERVE_UNKNOWN` bleibt im normalen Baseline-Regelpfad. Produktionskandidat A400/R100.
- **Evidenz:** V0.6.1 Vollhistorie mit 2.141.031/2.141.031 Rows und exakter Replay-Parität; Replay ist keine Closed-Loop-Feldevidenz.
- **Vor Implementierung:** Spezifikation gegen die dann aktuelle Sourcebasis revalidieren; Block A/V16.1.0 darf nicht durch parallele ungesicherte Working-Trees überschrieben werden.
- **Exit:** Build-/Differential-PASS -> reale Shadow-Abnahme -> begrenzte Active-Feldabnahme; Safety, Command-Effect und Hardware-Schonung separat belegen.

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

- **Status:** OPEN, **kein eigener Entwicklungsrelease**.
- Beim nächsten geeigneten Implementierungsrelease mit erledigen: persistenter maschinenlesbarer Installationsreport neben Installerlog/Evidence; `/tmp` höchstens Zusatzkopie; Feldtool bevorzugt persistenten Report; reale Backup-Datei mit Pfad/Größe/SHA256 verifizieren.
- Reglerkernänderung nicht vorgesehen.

### ZEC-BL-DEP-003 – V16.2.1 Manifest-/Deploymentvertrag und einmalige Fehlerbehandlung

- **Status:** EVIDENCE_PENDING; `implementation_state=implemented`; Technical Build PASS in `V16.2.2 / v16.2.2-20260921`; reale Update-Feldabnahme V16.2.0 → V16.2.3 noch offen.
- **Realer Fund 21.09.2026:** V16.2.1 bestand Package-/Fresh-Extract-Gates, enthielt aber fünf `.pytest_cache`-Dateien im Source-Manifest. Der Installer schließt `.pytest_cache/` beim Update/Fresh-Install bewusst aus und prüfte anschließend das unveränderte vollständige Manifest im Ziel; dadurch brach der reale Updatepfad V16.2.0 → V16.2.1 nach Backup und Copy mit fehlenden Manifestdateien ab.
- **Rollback-Evidenz:** automatischer Update-Rollback stellte V16.2.0 wieder her; `/health` meldete V16.2.0 alive=true, `/ready` true und keine failed_checks. V16.2.1 erhält daher keinen Real-Field-PASS.
- **Zweiter bestätigter Befund:** `set -E` vererbt den `ERR`-Trap in Subshells. Ein Fehler im Manifest-Subshell konnte Supportcapture/Rollback dort und anschließend nochmals im Hauptprozess auslösen; dies erklärt die zwei Diagnosepakete des realen Fehlversuchs.
- **V16.2.2-Scope:** volatile Cache-/Bytecode-/Runtime-DB-Artefakte fail-closed aus Release-Tree und aktuellem Manifest ausschließen; gemeinsamer Manifestverifier für Paket und Ziel; Paket-Preflight prüft Release-Hygiene vor jeder Mutation; reales rsync-Update und Fresh-Install werden gegen denselben Manifestvertrag regressionsgetestet; nur der Haupt-Shellprozess darf Supportcapture/Rollback finalisieren.
- **Abgrenzung:** keine UI-, Regler-, Command-, Safety- oder Recoverysemantikänderung; `controller_logic.py` muss byteidentisch bleiben. `ZEC-BL-DEP-002` wird in diesem Hotfix nicht stillschweigend mit umgesetzt.
- **Pre-Freeze-Evidenz:** vollständige Regression `1106 Tests + 698 Subtests PASS`, identischer Lauf mit `ResourceWarning=error`, Bash `13/13`, Browser-JS `3/3`, Compileall, Deployment-Harness `11/11`, Root-Rollback, Datenblatt und reale rsync/Manifest-Regression für Update/Fresh PASS. Das neue Hygiene-Gate erkannte ein während QA entstandenes Runtime-SQLite-Artefakt fail-closed; dieses wurde vor Manifest/Paketbau entfernt.
- **Technical Exit:** paketierter Fresh-Extract ohne volatile Artefakte, Manifest/Hygiene, vollständige Regression `1106 + 698`, identischer ResourceWarning-Lauf, statische Gates, Deployment-Harness und Root-Rollback PASS.
- **Realer Exit:** erfolgreiche Update-Feldabnahme V16.2.0 → V16.2.3; erst danach CLOSED / REAL_FIELD_PASS.

### ZEC-BL-UI-STATUS-002 – V16.2.0 Status-/SOC-Day-/Mobile-Settings-Härtung

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; Release `V16.2.0 / v16.2.0-20260920`.
- **Provenienz:** reale V16.1.0-Nutzung / Nutzerbefunde vom 20.09.2026.
- **Scope:** Primärspeicher-SOC-Ring-Layout; Tageswechsel-sicherer SOC-Day-Cache; „Jetzt“-Markierung nur am aktuellen Tag; mobile Settings-Suche mit erreichbarer Commit-Leiste; richtungsabhängige Restenergie und Leistungsbalken für beide Speicher; optionale Primärspeicher-Fallbackwerte für Kapazität und maximale Entladeleistung.
- **Safety:** reine UI-/Diagnose-/Settings-Metadaten-Erweiterung; `controller_logic.py` bleibt byteidentisch; neue Primärspeicherwerte besitzen keine Reglerwirkung.
- **Technischer Exit:** vollständige Regression `1098 Tests + 698 Subtests PASS`, identischer Lauf mit `ResourceWarning=error`, Browser-/Compile-/Deployment-/Datenblatt-/Fresh-extract-Gates PASS.
- **Realer Exit 20.09.2026:** Update V16.1.0 → V16.2.0 erfolgreich; Installer `ready=true`; konsolidierte read-only Feldabnahme insgesamt PASS mit allen 26 ausgewiesenen Checks PASS, einschließlich Releaseidentität, Controller-Readiness, Graph-/SOC-Day-/Settings-Verträgen, Installationsreport, Rollback-Backup und Performance-Budgets.

### ZEC-BL-DEP-004 – kanonischer maschinenlesbarer Build-Evidence-/Preflight-Vertrag

- **Status:** EVIDENCE_PENDING; `implementation_state=implemented`; V16.2.3 Technical Build PASS; reales Update weiterhin offen.
- **Fund 21.09.2026:** realer V16.2.2-`--preflight-only`-Lauf auf V16.2.0 brach vor jeder Produktivmutation ab, weil der Installer nicht vorhandene Freitextmarker in den vorhandenen grünen QA-Dateien verlangte. Diagnosebundle belegte `installed_identity=V16.2.0` und `rollback_result=not_required_preflight`.
- **Root Cause:** Build-Erzeugung und Installer hatten keinen gemeinsamen maschinenlesbaren Evidence-Vertrag; human-readable QA-Texte wurden als implizite Parser-API missbraucht.
- **V16.2.3-Scope:** `ZEC_BUILD_EVIDENCE_V1`; gemeinsamer `deployment_contract.py verify-build-evidence`; Installerdelegation ohne Freitextparsing; fail-closed Release-/Count-/ResourceWarning-Prüfung; finales Paketgate muss den Evidence-Teil des echten Installer-Preflights aus dem Fresh Extract ausführen.
- **Abgrenzung:** keine UI-, Regler-, Command-, Safety- oder Recoveryänderung; `controller_logic.py` bleibt byteidentisch. `ZEC-BL-DEP-002` bleibt separat offen.
- **Realer Exit:** erfolgreicher mutationsfreier V16.2.3-Preflight und anschließende kompakte reale Update-Feldabnahme V16.2.0 → V16.2.3.

### ZEC-BL-UI-STATUS-003 – V16.2.1 Speicherstatuskarten-Konsolidierung

- **Status:** EVIDENCE_PENDING; `implementation_state=implemented`; ursprünglich in `V16.2.1 / v16.2.1-20260921` technisch gebaut, wegen realem Installer-Fail nicht feldabgenommen; unverändert über V16.2.2 in V16.2.3 übernommen und dort erneut feldabzunehmen.
- **Provenienz:** reale V16.2.0-Nutzung / Nutzerbefunde vom 21.09.2026 nach erfolgreichem V16.2.0-Feld-PASS.
- **Befund:** Die V16.2.0-Primärspeicherkarte war trotz funktionaler Zusatzanzeigen visuell überladen; der SOC-Ring-/Detailbereich und Harmonisierung/Harvest konkurrierten um die feste Kartenhöhe. Zusätzlich war die normalisierte usable-SOC-Prozentzahl in der Standardansicht mathematisch korrekt, aber neben dem Roh-SOC nicht intuitiv genug.
- **Freigegebener Scope:** gemeinsamer Standardkartenvertrag für Zendure und Primärspeicher; große signierte Istleistung ohne zusätzliche ausgeschriebene Richtung; einteiliger Leistungsbalken mit Laden grün links→rechts und Entladen orange rechts→links; konkrete Leistung/Maximalleistung statt Prozentlabel; gemeinsame Bezeichnungen `Zustand`, `Ladegrenze`/`Entladegrenze`; `Noch ladbar`/`Noch entladbar` als SOC-Prozentpunkte und, bei belastbarer Kapazität, zusätzlich kWh.
- **Kapazitätsvertrag:** reale/source-seitige usable/effective Kapazität hat Vorrang, sofern belastbar vorhanden; danach andere belastbare Geräte-/Templatewerte, danach manueller Fallback. Fehlt eine belastbare Kapazität, bleibt die Prozentpunkt-Angabe erhalten und nur die kWh-Angabe entfällt. `ZEC-BL-PRIMARY-METADATA-001` bleibt für die spätere automatische Geräte-/Template-Ermittlung offen.
- **Diagnoseabgrenzung:** `primary_usable_soc_percent` bleibt intern/API-/Measurement-seitig diagnostisch erhalten, wird aber aus der Standardkarte entfernt. Harmonisierung/Harvest/Quellen- und usable-SOC-Details bleiben im Expertenkontext zugänglich. Dies schließt den vollständigen Statusseiten-Expertenmodus `ZEC-BL-UI-STATUS-EXPERT-001` nicht.
- **Safety:** reine UI-/Diagnose-/Settingsdarstellung; keine Regler-, Command-, Safety- oder Recoveryänderung; `controller_logic.py` muss byteidentisch bleiben.
- **Pre-Freeze-Nachweis:** fokussierte Regression `71 Tests + 10 Subtests PASS`; vollständige Regression `1100 Tests + 698 Subtests PASS`; identischer Lauf mit `ResourceWarning=error`; Bash `13/13`, Browser-JS `3/3`, Compileall, Deployment-Harness `11/11`, Root-Rollback und Datenblatt-Gate PASS.
- **Technischer Exit:** Source-Manifest und vollständiger paketierter Fresh-extract einschließlich Regression, ResourceWarning-, Syntax/Compile-, Deployment-, Root-Rollback- und Datenblatt-Gates PASS.
- **Offen:** kompakte reale Update-Feldabnahme des unverändert übernommenen UI-Scopes mit V16.2.0 → V16.2.3.

### ZEC-BL-UI-STATUS-EXPERT-001 – vollständiger Statusseiten-Experten-/Diagnosemodus

- **Status:** OPEN; `implementation_state=partial`; Roadmapposition noch nicht festgelegt.
- **Provenienz:** historische UI-Arbeit seit V12.8.x/V12.11.x (`kein vollständiger Standard-/Expertenmodus`, `Experten-/Diagnoseansicht` als Restpunkt), Projektchat **„Redesign Statusseite“** sowie der weiterhin aktive `UI_MODE`-Vertrag. Die historische Diskussion ist Provenienz; der hier festgehaltene Scope wird gegen V16.2.0 neu verankert.
- **V16.2.0 Ist-Befund:** `UI_MODE=standard|expert` ist in `SettingsRegistry`/Config/Help vorhanden. `status_page_v2.py` rendert ein Experten-/Diagnose-Navigationsmenü mit Links u. a. zu MQTT-Diagnose, Messdaten und Legacy-Status, wertet `UI_MODE` aber nicht als Darstellungsmodus der V2-Statuskarten aus. Das vorhandene Menü ist daher nicht gleichbedeutend mit dem vollständigen Statusseiten-Expertenmodus.
- **Zielvertrag:** Expertenmodus bleibt Superset des Standardmodus. Kernstatus, Warnungen und handlungsrelevante Informationen bleiben unverändert sichtbar; zusätzliche technische Details werden vertiefend zugänglich, ohne die Standardkarten dauerhaft zu überladen.
- **Historisch recoverter Inhaltsrahmen:** vollständiger/vertiefter Status-Snapshot; Rohstatus und Quelle relevanter Daten; Freshness/Validity/Datenalter; Reason-/Limiter- und Sollwertpipeline; Command-Effect/Readback/Resync; Timing-/Runtime-Diagnose; letzte relevante Runtime-Events; kontextbezogene Links zu Graph, Analyse und Settings. Nur vorhandene belastbare Daten dürfen dargestellt werden.
- **Interaktion:** vertiefende Diagnose über klar erkennbare Detailzugänge bzw. aufklappbare/kontextsensitive Detailflächen; Hover allein darf keine notwendige Diagnoseinformation tragen. Die konkrete responsive Modal-/Sidepanel-/Inline-Ausprägung wird vor Implementierung gegen die aktuelle Statusseite festgelegt.
- **Safety/Privacy:** reine UI-/Diagnosefunktion; keine Regler-/Commandwirkung, keine neue externe I/O im Regelzyklus, keine Secret-Exposition.
- **Vor Umsetzung:** V16.2.0-Karten-/ViewModel-Inventar erstellen; je Karte Standardkern vs. Expertendetails mappen; `UI_MODE`-Wirksamkeit und Reload-/Persistenzvertrag festlegen; Desktop/Mobile/Keyboard-/Accessibility-Verhalten definieren; bestehendes Experten-Navigationsmenü sauber vom Darstellungsmodus abgrenzen.
- **Exit:** `UI_MODE=standard|expert` wirkt nachweisbar auf der Statusseite; Expert ist vollständiges Superset; kritische Warnungen/Standardinformationen bleiben identisch; technische Details nutzen reale Snapshot-/Diagnosedaten; responsive/Accessibility-/Regressionstests decken beide Modi und Moduswechsel ab.

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

Ausgangspunkt ist der V16.2.0-Releasefreeze mit 76 eindeutigen Ledger-IDs und die danach in der kanonischen Projektquelle fortgeschriebene reale Feldabnahme. Die Quellenbereinigung/replacement vom 21.09.2026 erhält sämtliche 76 IDs unverändert und ergänzt genau zwei Planungs-IDs:

1. `ZEC-BL-CTRL-ADAPTIVE-001` – persistente Abbildung der Nutzerentscheidung zur gemeinsamen Entwicklung von S3, adaptiver Strategie und Kapazitätsgewichtung; die drei Child-IDs bleiben erhalten.
2. `ZEC-BL-UI-STATUS-EXPERT-001` – Recovery des historisch vorgesehenen, in V16.2.0 nur teilweise vorbereiteten Statusseiten-Expertenmodus.

Damit enthält dieses Ledger **78 eindeutige IDs**. Kein V16.2.0-Release-/Feldpunkt und keine frühere Ledger-ID wurde entfernt. Der Expertenmodus erhält bewusst noch keine priorisierte Roadmapposition.

**BACKLOG_NO_DROP_GATE = PASS**

