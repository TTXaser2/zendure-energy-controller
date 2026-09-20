# ZEC – Master-Backlog & Roadmap

**Stand:** 20.09.2026  
**Status:** kanonische, persistente Entwicklungsledger- und Roadmap-Autorität  
**Produktbasis:** V16.1.0 / `v16.1.0-20260919`

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

Diese Reihenfolge ist der aus der Reconciliation abgeleitete Arbeitsbestand; jede Umsetzung benötigt weiterhin eine konkrete Scopeanalyse und Nutzerfreigabe.

1. **ZEC-BL-CTRL-S3-001 – Saison-/Tagesprofile Completion & Effectiveness.** Die Settings sind in V16 exponiert/validiert, aber nicht vollständig runtime-verdrahtet. Zuerst Sourceaudit und Intended-vs-Actual-Vertrag, danach ggf. geschlossener Funktionsblock.
2. **ZEC-BL-STORAGE-001 – Measurement-/SQLite-Storage-Lifecycle.** S4/S5/S6/S7/S9 neu gegen V16 inventarisieren und in sicheren Stufen umsetzen; kein destruktives Enforcement vor nachgewiesener Restore-/Protection-/Coverage-Sicherheit.
3. **ZEC-BL-ANALYSIS-HANDOFF-001 – Graph → Analyse-Service.** Markierte reale Zeitfenster reproduzierbar an den bestehenden Analysedienst übergeben.
4. **ZEC-BL-SIM-001 – kontrafaktische Regler-Simulation.** Reale historische Situationen mit alternativen Reglerparametern durchspielen und Reality-vs-Simulation vergleichbar machen.
5. **ZEC-BL-CTRL-001 / ZEC-BL-CTRL-CAP-001 – adaptive Strategie und weiche Kapazitätsgewichtung.** Erst nach bzw. mit belastbarer Simulation/Evidenz.
6. **ZEC-BL-BATCARE-001 – Battery Care / Winter- und Reserve-SOC-Erhaltung.** Thema erhalten, Brainstorming vorhanden, aber neue fachliche Spezifikation erforderlich.
7. **ZEC-BL-SCENARIO-001 – allgemeiner Szenarioeditor** für synthetische Situationen, getrennt von historischer Counterfactual-Simulation.
8. **ZEC-BL-MULTI-001 – echter Multi-Zendure-Command-/Regelpfad.** Darstellung mehrerer Entities existiert; echte Befehlsverteilung bleibt separat.
9. **ZEC-BL-REL-001 – repo-zentrierter/reproduzierbarer Releaseprozess / CI.** Perspektivisch automatisieren, ohne aktuelle Sicherheitsgates abzuschwächen.

Querschnittlich bleiben `DEP-002`, Diagnose-/Command-Langzeitevidenz, Lernwerkzeugabgleich und Storage-Langzeitperformance mitzunehmen.

### 3.1 Historische S1–S9-Stufen – vollständige Reconciliation

| Stufe | historische Bedeutung | aktueller Ledgerstatus | Auflösung |
|---|---|---|---|
| S1 | Settings-Basis, UI und Legacy-Audit | CLOSED | in RC20/V12.11.x–V12.12.x produktiv umgesetzt; dauerhaft in der Closed-Historie erhalten |
| S2 | Primärspeicherintegration | CLOSED / SUPERSEDED BY V15 ARCHITECTURE | source-neutrale Primärspeicherintegration und direkte read-only Modbus-Anbindung in V15.0.0 schließen die alte S2-Kopplungslücke |
| S3 | Saison- und Tagesprofile | OPEN | `ZEC-BL-CTRL-S3-001` |
| S4 | SQLite-Pfad und `report_only` | OPEN / partial | `ZEC-BL-STORAGE-S4-001` |
| S5 | SQLite-Enforce | OPEN | `ZEC-BL-STORAGE-S5-001`; Bedeutung aus `conversations.json` wiederhergestellt |
| S6 | V4-Schutz, Katalog und Sicherheitsdialog | OPEN / partial | `ZEC-BL-STORAGE-S6-001` |
| S7 | V4 `compress_only` und Restore | OPEN | `ZEC-BL-STORAGE-S7-001` |
| S8 | Analyse- und Simulationspakete | PARTIAL / SPLIT | vorhandener Analysedienst ist produktiv; fehlende Graph-Übergabe `ZEC-BL-ANALYSIS-HANDOFF-001`, echte Simulation `ZEC-BL-SIM-001`, Szenarioeditor `ZEC-BL-SCENARIO-001` |
| S9 | V4-Retention Enforce | OPEN / nachgelagert | `ZEC-BL-STORAGE-S9-001` |

Damit ist keine historische S1–S9-Stufe mehr nur implizit oder unaufgelöst.

## 4. Offenes und zurückgestelltes Master-Ledger

### ZEC-BL-CTRL-S3-001 – Saison-/Tagesprofile Completion & Effectiveness

- **Status:** OPEN
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

- **Status:** EVIDENCE_PENDING; `implementation_state=implemented` in V16.1.0.
- **Reale Vorimplementierungs-Evidenz:** SMA Register `31009` (`Lower discharge limit for self-consumption range in %`, U32/FIX0/RO) lieferte am realen Sunny Island 19 %; FC03/FC04 identisch.
- **V16.1.0 Block A:** SMA-template-spezifische, read-only Capability `current_discharge_floor_soc`; getrennte Freshness/Validity/Invalidierung; diagnostischer normalisierter `primary_usable_soc_percent`; API/Status/Readiness/Connection-Test/Measurement-V4-Evidenz.
- **Safety-Grenze:** keine Reglerwirkung; `controller_logic.py` bleibt byteidentisch zu V16.0.2. Andere Primärspeicherprofile erhalten diese Capability nicht automatisch.
- **Settings-Vertrag:** kein editierbarer Floor, kein Override, kein On/Off-Schalter, keine ZEC-Saisonkurve; generische UI-/Help-Bezeichnungen werden auf „Primärspeicher“ neutralisiert; explizite Anzeigenamen bleiben erhalten.
- **Offene Evidenz:** reale V16.1.0-Feldabnahme der Capability nach Installation; Capability-Ausfall darf die gesunde Primärspeicher-Readiness nicht allein blockieren.

### ZEC-BL-CTRL-USABLE-SOC-001 – Block B: strategische usable-SOC-Integration

- **Status:** DEFERRED / SPEC_NEEDED; `implementation_state=none`.
- **Provenienz:** Folgeblock der SMA-Capability-Entscheidung vom 19.09.2026.
- **Ziel:** den aus realem Roh-SOC und aktueller geräteseitiger Entladeuntergrenze abgeleiteten nutzbaren Primär-SOC gezielt in Winter-/Schwachertragsstrategie verwenden.
- **Abgrenzung:** kein globaler Ersatz des Roh-SOC. FULL/IDLE, High-SOC-/Taper-Erkennung, Lade-Headroom bis 100 %, Fast Capture sowie physische Safety-/Limitentscheidungen bleiben am realen Roh-SOC bzw. Leistungszustand.
- **Voraussetzung:** mit Adaptive-/Replay-Ergebnissen zusammenführen; Zustand, Rechnung, physikalische Wirkung, Konvergenz, Recovery und Hardwareschonung vor Reglerfreigabe separat belegen.

### ZEC-BL-CTRL-CAP-001 – echte weiche Kapazitätsgewichtung

- **Status:** SPEC_NEEDED.
- `HARVEST_CAPACITY_WEIGHTING_MODE` ist historisch bewusst diagnostisch geblieben; keine echte Reglerwirkung vortäuschen.
- Eine neue weiche Gewichtung ist eine Reglerstrategie und soll zuerst im Simulationsdienst mit historischen Produktivdaten geprüft werden; danach Differential-/Konvergenz-/Hardwareschonungsbewertung und explizite Freigabe.

### ZEC-BL-CTRL-001 – ertrags-/SOC-bewusste Ladeverteilung weiterentwickeln

- **Status:** OPEN.
- Die Grundinvariante „aktuell vermeidbare Einspeisung vor strategischer Ladeverteilung“ ist bereits produktiv implementiert und darf nicht neu erfunden werden.
- Erweiterungsraum: adaptive/lernende Ladeannahme-/Taper-Kennlinie, batteriespezifische Anpassung, erweiterte SOC-/Ertragsstrategie.
- Vor Implementierung: Lernzustand/Persistenz/Reset, Confidence/Fallback, Simulation, Konvergenz/Oszillation, Zustand/Rechnung/Wirkung/Recovery und Hardwarebelastung.

### ZEC-BL-BATCARE-001 – Battery Care / Winter- und Reserve-SOC-Erhaltung

- **Status:** SPEC_NEEDED.
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
- V16.0.2 enthält keine `.github`-Automation. Umsetzung darf bestehende Fresh-extract-, Manifest-, Hash-, Test-, Datenblatt- und Feldgates nicht abschwächen.

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

### ZEC-BL-DEP-002 – persistente Installationsreports

- **Status:** OPEN, **kein eigener Entwicklungsrelease**.
- Beim nächsten geeigneten Implementierungsrelease mit erledigen: persistenter maschinenlesbarer Installationsreport neben Installerlog/Evidence; `/tmp` höchstens Zusatzkopie; Feldtool bevorzugt persistenten Report; reale Backup-Datei mit Pfad/Größe/SHA256 verifizieren.
- Reglerkernänderung nicht vorgesehen.

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
| `ZEC-HIST-V16_1_0` | V16.1.0 | EVIDENCE_PENDING | SMA Sunny Island 31009 Capability, separate Freshness/Diagnose/usable SOC, source-neutrale Primärspeicher-Namenshygiene; keine Reglerwirkung; reale V16.1.0-Feldabnahme noch offen |

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
