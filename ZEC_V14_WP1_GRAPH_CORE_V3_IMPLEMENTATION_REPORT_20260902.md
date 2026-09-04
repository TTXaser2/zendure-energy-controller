# ZEC V14 – WP1 Graph-Core V3 Rebuild & Backfill Foundation

**Stand:** 02.09.2026  
**Status:** Engineering-Handoff; **kein produktiv installierbarer V14-Release**  
**Verifizierte Ausgangsbasis:** ZEC V13.0.3 / `v13.0.3-20260814`  
**Basis-ZIP SHA256:** `15082a6651130848d4c4d1b339a549dde9ae77b984d3c4333f9d738b803b0698`  
**Basis-Source-Manifest:** 407/407 PASS

## 1. Freigegebener Scope

WP1 implementiert die technische Grundlage für einen komplett neu aufgebauten V14-Graph-Core aus Measurement V4. Die produktive V13-Live-Regelung, Command-Semantik und der aktuelle V2-Live-Writer werden in WP1 bewusst nicht umgeschaltet.

Ziele:

- neues Graph-Core-Schema V3 als frische SQLite-Datenbasis;
- Measurement V4 als primäre Rebuildquelle;
- scaled signed SQLite INTEGER als bevorzugte Speicherrepräsentation, benchmarkvalidiert gegen REAL;
- metrikspezifische Long-Term-Aggregation;
- sparse Intervals/Command Events/Run Namespace/Topology/Coverage/Retention-Grundstrukturen;
- strikt begrenzte Behandlung historischer `TRAILING_NUL_PADDING`-Artefakte;
- deterministischer Offline-Rebuild mit Validierungsreport;
- keine stillen historischen Rekonstruktionen bei nicht belegbarer Semantik.

## 2. Neue Implementierung

### `graph_core_v3.py`

Enthält:

- Schema-Version `3`;
- kanonischen Series-/Storage-Vertrag;
- 64-Bit-scaled-INTEGER-Codec mit Range-/Finite-Prüfung;
- Wide-System-Raw-Schema;
- metrikspezifische 1-Minuten-Aggregation;
- Entity-Raw-/1-Minuten-Tabellen für spätere instance-aware Topologien;
- `graph_runs` zur historischen Namespacierung laufzeitlokaler IDs;
- `graph_intervals` für Mode/Intent/Reason/Limiter/Quality/Source/Effect;
- `graph_command_events` für Desired/Publish/Readback/Effect/Resync/Neutralization;
- `graph_topology_timeline`;
- `graph_retention_ledger`;
- `graph_source_files` und `graph_series_coverage`;
- Wiederverwendung von `graph_config_timeline` ohne den ungenutzten V13-Hash-Index;
- strikte V4-Quelleingangsvalidierung.

### `tools/rebuild_graph_core_v3.py`

Offline-Rebuildtool:

- verändert die alte V2-DB nie;
- erzeugt die Ziel-DB von Null;
- streamt V4-Dateien;
- sortiert Quellen deterministisch über ersten Measurement-Timestamp;
- verwirft keine alten Daten zugunsten erfundener neuer Semantik;
- überspringt überlappende/out-of-order Raw-Timestamps deterministisch und reportet sie;
- bildet Long-Term-Buckets vollständig neu;
- bildet sparse State-/Command-/Topology-Historie;
- kann die verifizierte V2-`graph_config_timeline` optional als zusätzliche Config-Evidenz übernehmen;
- führt `PRAGMA integrity_check` und strukturelle Validierungen aus;
- schreibt einen maschinenlesbaren JSON-Report.

### `tools/benchmark_graph_core_v3.py`

Reproduzierbarer REAL-vs-scaled-INTEGER-Benchmark mit identischer fachlicher Datenmenge und 15 Graph-Core-Serien.

## 3. Storage-Entscheidung

### Wertebereich

SQLite `INTEGER` ist signed 64 Bit. Bei `W × 10` liegt die theoretische Leistungsdomäne bei rund ±922 PW. 30 kW werden als `300000`, 1 GW als `10000000000` gespeichert. Storage-Range und fachliche Plausibilitätsgrenze bleiben getrennte Verträge.

### Benchmark, 100.000 Samples

Siehe `validation/V14_WP1_REAL_VS_INTEGER_BENCHMARK.json`.

| Kennzahl | REAL | scaled INTEGER |
|---|---:|---:|
| DB-Größe | 14.409.728 B | 7.225.344 B |
| Bytes/Raw-Zeile | 144,097 | 72,253 |
| 24-h-Range Query Median | 20,784 ms | 18,532 ms |
| 48-h-Range Query Median | 41,846 ms | 38,875 ms |
| Write 100k | 1,193 s | 1,266 s |

**DB-Reduktion:** 49,86 %.  
**Entscheidung:** scaled INTEGER `×10` ist für WP1 gewählt. Die Write-Differenz liegt weit unter einem Niveau, das den deutlichen Footprint- und Queryvorteil aufwiegt; der produktive Live-Writer bleibt in WP1 ohnehin unverändert.

## 4. Aggregationsvertrag

Physische Leistung:

- `min`
- `max`
- `sum`
- `last`
- `valid_count`

SOC und Target-Pipeline:

- `min`
- `max`
- `last`
- `valid_count`

Damit wird der V2-Befund beseitigt, bei dem optionale Mittelwerte mit dem globalen Bucket-`sample_count` gewichtet wurden. Künftige größere Zoom-Buckets können für Power korrekt als `Σsum / Σcount` gebildet werden, statt Durchschnitte von Durchschnitten zu berechnen.

## 5. Rebuild-Coverage-Gate aus Produktivdaten

Vom Nutzer am 01.09.2026 read-only ermittelt:

- SQLite Raw gesamt: 1.643.995 Zeilen (Haupt + Fallback);
- SQLite belegte Minuten: 84.103;
- Measurement V4: 745 Dateien / 1.645.321 Zeilen;
- V4 belegte Minuten: 84.209;
- Overlap: **84.103/84.103 SQLite-Minuten**;
- `DB_ONLY_MINUTES=0`;
- `V4_ONLY_MINUTES=106`;
- V4 startet am 23.06.2026 und damit vor der SQLite-Historie;
- V4 ist daher primäre Rebuildquelle;
- V2 bleibt Rollback-/Vergleichsevidenz, nicht reguläre Measurement-Backfillquelle.

### Historische NUL-Anomalie

Eine Datei:

`zendure_measurements_v4_20260709T211719Z.csv`

- Dateigröße exakt 8192 B;
- letzte Measurement-Zeile vollständig und mit CRLF abgeschlossen;
- danach genau 307 NUL-Bytes bis EOF;
- keine Nutzdaten hinter dem NUL-Suffix.

Klassifikation: `TRAILING_NUL_PADDING`, kein verlorener Measurement-Record.

WP1 toleriert ausschließlich einen reinen EOF-NUL-Suffix nach vollständigem Record. Embedded NUL, Daten nach NUL oder strukturell beschädigte Records führen zu Fehler/Review statt stiller Reparatur.

## 6. Synthetischer End-to-End-Rebuild

50.000 V4-Zeilen, 3-s-Abstand, 15 Systemserien, State-/Command-/Topology-Daten und 307 EOF-NUL-Bytes:

- Rebuild-Zeit: 2,174 s interne Toolzeit / 2,73 s Gesamtprozess;
- Peak RSS: 102.348 KiB;
- V3-DB: 4.874.240 B;
- Raw: 50.000;
- 1-Minute: 2.501;
- Command Events: 3.812;
- Sparse Intervals: 3.259;
- Runs: 1;
- `PRAGMA integrity_check=ok`;
- `duplicate_raw_timestamps=0`;
- `trailing_nul_bytes=307` korrekt protokolliert.

Siehe `validation/V14_WP1_SYNTHETIC_REBUILD_REPORT.json`.

## 7. Technische-Schulden-Befunde

### In V3-WP1 bereits berücksichtigt

1. Redundante V2-Indizes auf `INTEGER PRIMARY KEY` werden in V3 nicht erzeugt.
2. Der unbelegte `idx_graph_config_timeline_hash` wird in V3 entfernt.
3. V2-Average-Semantik mit globalem Samplecount wird nicht übernommen.
4. Laufzeitlokale Command-IDs erhalten über `graph_runs` eine historische Namespace-Grundlage.
5. Wiederholte Mode/Reason/Limiter-/Quality-/Source-Texte werden als sparse Intervalle modelliert statt Raw-Wiederholung.
6. Historical V4 trailing-NUL wird eng klassifiziert statt globaler stiller NUL-Bereinigung.

### Bewusst spätere WPs

1. `MEASUREMENT_DB_MAX_QUEUE_ROWS` ist derzeit Registry-Altlast ohne Runtimewirkung; Entscheidung/Entfernung bzw. echte Verdrahtung gehört zum Live-Writer-Cutover.
2. SQLite-Retention-Settings besitzen noch keinen produktiven Enforce-Worker; Umsetzung gehört zum Retention-/Ledger-WP.
3. Bestehender `/graph-view-data`-SQLite-Pfad ist faktisch 1-Minute-only; Query Planner gehört zum Query-Service-WP.
4. Historische Multi-Zendure-Instance-Daten fehlen im V2-Store; V3-Schema ist vorbereitet, reale Instrumentierung folgt separat.
5. `command_publish_epoch_s` besitzt noch keine monotone Publish-Zeit; Ergänzung gehört zur Command-/Run-Instrumentierung.

Keiner dieser Punkte wurde in WP1 stillschweigend verändert, weil dies ohne Live-Writer-/Instrumentation-Cutover unnötig Scope und Regressionrisiko vergrößert hätte.

## 8. Tests / Gates

### Baseline vor Änderung

- 808 Tests PASS
- 681 Subtests PASS

### WP1 nach Änderung

- **819 Tests PASS**
- **681 Subtests PASS**
- neue WP1-Tests: 11 PASS
- vollständiger Lauf mit `PYTHONWARNINGS=error::ResourceWarning`: PASS
- `compileall` für neue Module/Tools/Tests: PASS
- REAL-vs-INTEGER-Benchmark: PASS, INTEGER gewählt
- synthetischer End-to-End-Rebuild: PASS

## 9. Live-Regelung / No-Regression

WP1 ändert **keine bestehende Produktiv-Quelldatei**. Es werden nur neue Module, Tools, Tests und Validierungsartefakte hinzugefügt.

Daher unverändert:

- Regelalgorithmus;
- MQTT-/Commandpfad;
- Command-Wirkungslogik;
- V4-Livewriter;
- bestehender V2-SQLite-Livewriter;
- Statusseite;
- Graphseite;
- Installer;
- Operational-Events-DB.

Das ist absichtlich: WP1 baut und verifiziert die neue Persistenzgrundlage, ohne vorzeitig einen produktiven Cutover durchzuführen.

## 10. Nächster Implementierungsblock

Empfohlen: **WP2 – Graph-Core V3 Live Writer & Cutover Foundation**.

Ziele:

- V3-Writer in den produktiven Measurementpfad integrieren;
- bestehende V2-Queue-/Writer-Schulden beseitigen;
- Run-ID beim echten Controllerstart erzeugen;
- monotone Command-Publish-Zeit instrumentieren;
- V3-DB-Status/Diagnostics anbinden;
- noch keine neue Graph-UI;
- weiterhin keine Änderung der fachlichen Regelentscheidungen oder Commandwerte.

Für WP2 ist eine neue Makrofreigabe erforderlich.
