# SPEZIFIKATION ZEC-MEASUREMENT-V4 STORAGE-HÄRTUNG UND RC18-FELDBUDGET V1.0

**Projekt:** Zendure Energy Controller (ZEC)  
**Status:** finaler Planungsstand, keine Build- oder Deploymentfreigabe  
**Basis:** ZEC V12.11.2-RC17, produktive Storage-Analyse vom 31.07.2026, RC18-Spezifikation zur asynchronen lokalen Zendure-API  
**Geltungsbereich:** ZEC-MEASUREMENT-V4 Standard/Extended, Manifest, Sidecars, Analyse-/Exportwerkzeuge  

---

## 1. Zweck

Diese Spezifikation löst zwei voneinander getrennte Aufgaben:

1. **Storage-Härtung von ZEC-MEASUREMENT-V4**
   - Gesamtbelegung wirksam begrenzen;
   - geschlossene CSV-Dateien verlustfrei komprimieren;
   - Dateianzahl und Analyseaufwand beherrschbar halten;
   - Manifest, Sidecars, Export, Replay und Offlineanalyse konsistent halten;
   - aktive Regelung, Commandpfad und Datenerfassung nicht blockieren.

2. **Verbindliches Feldbudget für RC18**
   - die geplanten 16 Local-API-Felder nach zyklischer Notwendigkeit klassifizieren;
   - unnötige Wiederholung von Worker-/Fehlerzuständen vermeiden;
   - die RC18-Analysierbarkeit ohne pauschale Erweiterung um 16 zyklische Spalten erhalten.

Die Storage-Härtung ist **kein Bestandteil des RC18-Async-Local-API-Implementierungsdeltas**. Sie ist ein eigener späterer Releaseblock. Das RC18-Feldbudget ist dagegen ein Addendum, das Abschnitt 11 der bisherigen RC18-Spezifikation vor einem Build ersetzt.

---

## 2. Verbindliche Ausgangslage

### 2.1 Produktivbestand am 31.07.2026

```text
CSV-Dateien gesamt:                 244
CSV-Messzeilen:                 739.082
CSV-Gesamtbelegung:             611,64 MiB
Primärverzeichnis:              610,95 MiB
Fallback-Verzeichnis:             0,69 MiB
Freier Speicher:                199,77 GiB von 218,75 GiB
Lesefehler:                           0
```

Es besteht kein akuter Speicherengpass. Das Wachstum ist jedoch ohne wirksame Gesamtretention langfristig unbeschränkt.

### 2.2 Aktuelles RC17-Standardprofil

```text
Feldanzahl:                        238
produktive RC17-Dateien:            11
produktive RC17-Zeilen:         20.297
mittlere Datenzeile:            1.516,4 Byte
konfigurierter Schätzwert:         650 Byte
Abweichungsfaktor:                2,33
Wachstum bei 3-s-Intervall:       41,65 MiB/Tag
Jahresprojektion:                 14,85 GiB/Jahr
```

### 2.3 Reale Komprimierbarkeit

Für RC17 Standard wurde mit einer realen 16-MiB-Probe bei gzip Level 6 gemessen:

```text
Einsparung:                       95,79 %
komprimierter Anteil:              4,21 %
```

Die hohe Quote entsteht durch zahlreiche konstante, langsam wechselnde und wiederholte Zustands-, Reason-, Source-, Flag- und Counterwerte.

### 2.4 Aktuelle produktive Konfiguration

```text
MEASUREMENT_LOG_MODE:                     standard
MEASUREMENT_SCHEMA_VERSION:               4
MEASUREMENT_LOG_MAX_BYTES:                3.000.000
MEASUREMENT_LOG_BACKUP_COUNT:             20
MEASUREMENT_LOG_ESTIMATED_ROW_BYTES:      650
MEASUREMENT_LOG_MIN_FREE_DISK_MB:         500
MEASUREMENT_LOG_FALLBACK_MAX_BYTES:       10.000.000
MEASUREMENT_LOG_FALLBACK_BACKUP_COUNT:    2
INTERVAL_SECONDS:                         3
```

Die aktuelle 3-MB-Grenze erzeugt bei RC17 ungefähr alle 1,65 Stunden eine neue Datei, also typischerweise 14 bis 15 Dateien pro Tag.

---

## 3. Nachgewiesene Ist-Probleme

### 3.1 V4-Backupanzahl begrenzt den timestamp-basierten Bestand nicht

Die Legacy-Rotation in `csv_logger.py` besitzt `_1`, `_2`, ... und löscht nach `BACKUP_COUNT`. Der V4-Writer in `measurement_v4.py` erzeugt dagegen bei jedem Service-Start und bei jeder Größenrotation neue timestamp-basierte Dateien.

Im V4-Rotationspfad wird `MEASUREMENT_LOG_BACKUP_COUNT` nicht zur Bereinigung der timestamp-basierten Dateien verwendet. Der produktive Bestand von 244 Dateien bei konfigurierten 20 Rotationsdateien bestätigt die fehlende wirksame V4-Gesamtbegrenzung.

### 3.2 Beschreibung und tatsächliche V4-Semantik widersprechen sich

Die Settings-Beschreibung bezeichnet `MEASUREMENT_LOG_BACKUP_COUNT` als Anzahl rollierend behaltener Dateien. Für V4 ist diese Aussage derzeit falsch.

### 3.3 Schätzgröße ist veraltet

`MEASUREMENT_LOG_ESTIMATED_ROW_BYTES=650` unterschätzt RC17 Standard um Faktor 2,33. Die Konfigurationsbeschreibung, der Wert sei für V4 Standard praxisnah, ist damit überholt.

### 3.4 Manifest besitzt keinen vollständigen Storage-Lifecycle

Der V4-Writer erzeugt Manifesteinträge, lässt `closed_time_utc` aber im normalen Rotationspfad leer. Das Manifest unterscheidet bislang nicht belastbar zwischen:

- aktiver CSV;
- geschlossener CSV;
- verifizierter gzip-Datei;
- zur Löschung freigegebener Datei;
- bereits entfernter Datei.

### 3.5 Analysewerkzeuge kennen nur `.csv`

Mindestens Analysepaket, Import und mehrere Replay-/Offlinewerkzeuge suchen derzeit ausschließlich nach `zendure_measurements_v4*.csv`. Eine Kompression ohne vorherige Toolkompatibilität würde Daten faktisch aus Standardworkflows ausblenden.

### 3.6 Dateianzahl ist unabhängig von der Bytebelegung ein Problem

Bei unveränderten 3 MB entstehen ungefähr:

```text
pro Tag:                          14–15 Dateien
pro 30 Tage:                    ca. 435 Dateien
pro 90 Tage:                  ca. 1.300 Dateien
pro Jahr:                     ca. 5.300 Dateien
```

Selbst komprimiert bleiben Verzeichnis-, Manifest-, Paket- und Analysescans bei dieser Dateianzahl unnötig teuer.

---

## 4. Nicht-Ziele

Die Storage-Härtung darf nicht:

- Regelalgorithmen, Modi, Harvest, Cross-Charge oder Command-Lifecycle ändern;
- den Regelthread durch Kompression, Hashing, Verifikation, Scan oder Löschung blockieren;
- aktive oder möglicherweise noch beschriebene Dateien komprimieren oder löschen;
- Diagnosefelder ohne separaten fachlichen Nachweis entfernen;
- CSV durch ein proprietäres Binärformat ersetzen;
- bestehende historische CSV-Dateien bei Installation ungefragt löschen;
- einen unbounded Queue- oder Historienpuffer im RAM erzeugen;
- auf dem Pi komplette CSV-Dateien in den Speicher laden;
- bei Fehlern die Erfassung pausieren, solange noch ausreichend Speicher vorhanden ist;
- das bestehende Mindestfreispeicher-Sicherheitsnetz ersetzen.

---

## 5. Release- und Migrationsstrategie

### 5.1 Trennung der Releases

**RC18:** ausschließlich asynchrone lokale Zendure-API plus das in Abschnitt 14 definierte reduzierte Measurement-Feldbudget.

**Storage-Härtungsrelease:** eigener späterer Releaseblock nach RC18-Abnahme oder als separat benannter Logging-RC. Keine Kopplung an Harvest- oder Local-API-Funktionalität.

### 5.2 Keine automatische destruktive Migration

Bei bestehenden Installationen startet der neue Storage-Lifecycle grundsätzlich im Modus:

```text
report_only
```

Dieser Modus:

- inventarisiert;
- berechnet Einspar- und Retentionsprognosen;
- meldet Inkonsistenzen;
- verändert keine Messdatei.

Kompression und Löschung werden erst nach ausdrücklicher Konfigurationsänderung aktiv.

### 5.3 Wartungsmodi

Neuer Config-Key:

```text
MEASUREMENT_LOG_MAINTENANCE_MODE
```

Zulässige Werte:

```text
off
report_only
compress_only
enforce
```

Semantik:

- `off`: kein Scan außer minimaler Statusermittlung;
- `report_only`: vollständiger Scan und Vorschau, keine Dateiveränderung;
- `compress_only`: geschlossene Dateien sicher komprimieren, nichts aufgrund von Alter/Volumen löschen;
- `enforce`: komprimieren und Retentionsgrenzen durch Löschen der ältesten freigegebenen Archive durchsetzen.

Default für Migration und Neuinstallation:

```text
report_only
```

Damit erfolgt niemals eine überraschende Löschung allein durch ein Update.

---

## 6. Neue Storage-Konfiguration

### 6.1 Verbindliche neue Keys

```text
MEASUREMENT_LOG_MAINTENANCE_MODE             = report_only
MEASUREMENT_LOG_COMPRESSION_MIN_AGE_MINUTES  = 15
MEASUREMENT_LOG_RETENTION_MAX_AGE_DAYS       = 90
MEASUREMENT_LOG_RETENTION_MAX_TOTAL_BYTES    = 2000000000
MEASUREMENT_LOG_RETENTION_PROTECT_HOURS      = 48
```

Validierung:

```text
COMPRESSION_MIN_AGE_MINUTES:   5 .. 1440
RETENTION_MAX_AGE_DAYS:        1 .. 3650
RETENTION_MAX_TOTAL_BYTES:     100 MB .. 500 GB
RETENTION_PROTECT_HOURS:       1 .. 720
```

### 6.2 Interne, nicht als normale Settings exponierte Konstanten

```text
maintenance interval:             3600 s
startup delay:                     300 s
max files per maintenance run:       8
compression chunk size:             1 MiB
compression level:                  gzip level 1
orphan temp maximum age:            24 h
closed-file stability guard:        120 s
```

Diese Werte sind Implementierungsparameter und sollen die Settings-Seite nicht unnötig erweitern.

### 6.3 Bestehende Keys

`MEASUREMENT_LOG_MAX_BYTES` bleibt die maximale Größe **einer aktiven unkomprimierten Datei**.

`MEASUREMENT_LOG_BACKUP_COUNT` wird für V4 als veraltet gekennzeichnet und nicht mehr als wahrheitswidrige Retentionsgrenze dargestellt. Es bleibt nur für Legacy-Schemata beziehungsweise Rückwärtskompatibilität erhalten.

Für V4 zeigt die UI stattdessen:

- aktive Dateigröße;
- aktuelle Gesamtbelegung;
- komprimierte Gesamtbelegung;
- effektives Alter der ältesten verfügbaren Messung;
- wirksame Age-/Byte-Retention;
- geschützte jüngste Historie.

### 6.4 Fallback

Für das Fallback-Verzeichnis bleibt die bestehende harte Kombination wirksam:

```text
MEASUREMENT_LOG_FALLBACK_MAX_BYTES
MEASUREMENT_LOG_FALLBACK_BACKUP_COUNT
```

Der neue V4-Lifecycle muss diese Anzahl tatsächlich durchsetzen. Es werden höchstens die konfigurierte Anzahl Fallback-Messdateien beziehungsweise deren verifizierte gzip-Nachfolger behalten.

Fallback-Dateien werden ebenfalls komprimiert, aber nie zulasten der aktiven Regelung. Bei Kompressionsfehlern bleibt die unkomprimierte Datei erhalten.

---

## 7. Worker-Architektur

### 7.1 Eigener Storage-Maintenance-Worker

Die Storage-Härtung verwendet genau einen daemonisierten Hintergrundworker:

```text
MeasurementStorageMaintenanceWorker
```

Der Worker:

- wird nicht im Regelzyklus ausgeführt;
- besitzt keine unbeschränkte Aufgabenqueue;
- scannt den aktuellen Bestand bei Bedarf neu;
- verarbeitet sequenziell höchstens acht Dateien pro Lauf;
- schläft interruptibel;
- veröffentlicht nur einen kleinen unveränderlichen Statussnapshot;
- schreibt niemals direkt in Regler- oder Command-State.

### 7.2 Auslöser

Ein Lauf wird ausgelöst:

- fünf Minuten nach Prozessstart;
- nach einer erfolgreichen Größenrotation;
- nach einem Wechsel des Loggingziels;
- danach höchstens einmal pro Stunde;
- manuell über eine explizite Diagnose-/Settings-Aktion.

Mehrere Signale werden koalesziert; es entsteht keine Queue pro Rotation.

### 7.3 Ressourcenpriorität

Der Worker arbeitet best effort und niedrig priorisiert. Kompression und Hashing dürfen weder den Zyklus noch MQTT, SMA-Listener, SQLite-Writer oder Webserver messbar beeinträchtigen.

Verbindliche Produktivkriterien:

```text
keine Erhöhung cycle_total_without_sleep_ms p95 > 2 ms
kein Zyklus > 1 s durch Storage-Maintenance
kein zusätzlicher Command-Publish
kein zusätzlicher Resync
kein acMode-Wechsel
kein physischer Richtungswechsel
kein 0-W-Zwischenzustand
```

---

## 8. Dateilebenszyklus

### 8.1 Zustände

Jede Measurement-Datei befindet sich genau in einem Zustand:

```text
ACTIVE_CSV
CLOSED_CSV
COMPRESSING
COMPRESSED_VERIFIED
RETENTION_ELIGIBLE
DELETED
ERROR_RETAINED
```

`DELETED` wird nicht dauerhaft als Manifesttombstone behalten; der Vorgang wird stattdessen in `zec_runtime_events.jsonl` protokolliert.

### 8.2 Aktive Datei

Eine Datei ist aktiv, wenn sie:

- `MeasurementV4Logger._open_path` entspricht; oder
- zur aktuellen Session-Path-Map gehört und noch nicht explizit geschlossen wurde.

Eine aktive Datei wird niemals:

- komprimiert;
- umbenannt;
- gehasht über den bisher geschriebenen Umfang hinaus;
- gelöscht.

### 8.3 Geschlossen-Markierung

Bei Größenrotation, Zielwechsel, Schemawechsel und kontrolliertem Shutdown muss der Writer vor Übergabe an den Maintenance-Worker:

1. flushen;
2. Datei schließen;
3. Manifest `closed_time_utc` setzen;
4. `row_count`, erstes/letztes Measurement, Dateigröße und Header-Hash finalisieren;
5. Runtime-Event `measurement_file_closed` schreiben.

Nach einem ungeplanten Prozessende erkennt der nächste Start ältere Sessiondateien über:

- sie sind nicht die aktuelle Sessiondatei;
- Größe und mtime sind mindestens 120 Sekunden stabil;
- Header ist lesbar;
- letzte CSV-Zeile ist vollständig parsebar.

Erst danach werden sie als `CLOSED_CSV` reconciliert.

---

## 9. Sichere gzip-Kompression

### 9.1 Zulässige Quelle

Komprimiert werden ausschließlich Dateien, die:

- `CLOSED_CSV` sind;
- älter als `MEASUREMENT_LOG_COMPRESSION_MIN_AGE_MINUTES` sind;
- nicht durch einen Analyse-/Exportlock geschützt sind;
- einen gültigen bekannten V4- oder historischen Header besitzen;
- keine bereits vorhandene ungeklärte `.gz`-Variante haben.

### 9.2 Transaktion

Für `file.csv`:

1. Shared/Exclusive-Lock prüfen und exklusiven Maintenance-Lock erwerben.
2. Quellgröße, Header, erste/letzte vollständige Zeile und SHA256 der Quelle streamingbasiert ermitteln.
3. `file.csv.gz.tmp` mit gzip Level 1 streamingbasiert schreiben.
4. Tempdatei flushen und `fsync` ausführen.
5. Tempdatei vollständig streamingbasiert dekomprimieren und SHA256 gegen Quelle prüfen.
6. gzip-CRC/EOF muss gültig sein.
7. `os.replace(file.csv.gz.tmp, file.csv.gz)` atomar ausführen.
8. Verzeichnis-Metadaten best effort synchronisieren.
9. Manifest atomar auf komprimierten Pfad, Größen und Hashes aktualisieren.
10. Erst danach `file.csv` entfernen.
11. Runtime-Event `measurement_file_compressed` schreiben.

Bei jedem Fehler bleibt die unkomprimierte Quelldatei erhalten.

### 9.3 Crash-Recovery

Beim nächsten Scan werden folgende Fälle repariert:

- `.gz.tmp` ohne gültiges Ende: Tempdatei nach 24 Stunden entfernen;
- gültige `.gz.tmp` plus Quelle: Verifikation fortsetzen;
- gültige `.gz` plus Quelle, Manifest noch CSV: Manifest reparieren, dann Quelle entfernen;
- Manifest zeigt `.gz`, Quelle zusätzlich vorhanden: gzip verifizieren, Quelle entfernen;
- Manifest zeigt CSV, Quelle fehlt, gültige `.gz` vorhanden: Manifest auf gzip reparieren;
- weder Quelle noch gzip vorhanden: Manifestinkonsistenz melden, nicht stillschweigend bereinigen.

### 9.4 Gzip-Namensvertrag

```text
zendure_measurements_v4_<timestamp>.csv
→ zendure_measurements_v4_<timestamp>.csv.gz
```

`measurement_file_id` und `logical_stream_id` bleiben unverändert.

---

## 10. Retentionsalgorithmus

### 10.1 Grundsatz

Gelöscht werden nur `COMPRESSED_VERIFIED`-Dateien. Eine unkomprimierte Datei wird wegen Retention niemals direkt gelöscht.

### 10.2 Sortierung

Die Reihenfolge basiert auf:

```text
last_measurement_epoch_ms
```

Fallback bei fehlender Manifestinformation:

```text
Dateiinhalt letzter Messzeitpunkt
```

mtime und Dateiname sind nur letzte Notlösung und führen ohne eindeutige Evidenz nicht zur automatischen Löschung.

### 10.3 Schutzmenge

Unbedingt geschützt sind:

- aktive Datei;
- alle Dateien der aktuellen Session;
- alle Dateien innerhalb `MEASUREMENT_LOG_RETENTION_PROTECT_HOURS`;
- Dateien mit ungeklärter Manifest-/Hashinkonsistenz;
- Dateien unter Shared-Lock eines Export-/Analyseprozesses;
- mindestens die zwei jüngsten geschlossenen Dateien je aktivem Ziel.

### 10.4 Enforce-Reihenfolge

Im Modus `enforce`:

1. Kandidaten älter als `RETENTION_MAX_AGE_DAYS` löschen, älteste zuerst.
2. Gesamtbelegung neu berechnen.
3. Falls oberhalb `RETENTION_MAX_TOTAL_BYTES`, weitere älteste nicht geschützte Archive löschen.
4. Nach jedem Delete Manifest atomar aktualisieren und Runtime-Event schreiben.
5. Sobald keine sicheren Kandidaten mehr existieren, stoppen und Warnung ausgeben.

### 10.5 Keine aggressive Notlöschung

Sinkt freier Speicher unter `MEASUREMENT_LOG_MIN_FREE_DISK_MB`, gilt weiterhin:

- Logging pausiert gemäß bestehendem Schutz;
- Maintenance darf nur innerhalb der konfigurierten Retention löschen;
- geschützte oder inkonsistente Dateien werden nicht zur Freispeichergewinnung geopfert;
- kein automatisches „lösche alles Alte“ außerhalb des Vertrages.

---

## 11. Manifestvertrag V4.1 Storage-Lifecycle

Das Measurement-Schema bleibt V4; der Sidecar-Manifestvertrag erhält eine additive Revision.

### 11.1 Zusätzliche Felder je Datei

```text
storage_state
closed_time_utc
uncompressed_size_bytes
compressed_size_bytes
compression
source_sha256
archive_sha256
archive_verified_time_utc
maintenance_last_error
maintenance_last_error_time_utc
```

`compression` ist `none` oder `gzip`.

### 11.2 Pfadsemantik

Nach erfolgreicher Kompression zeigen `file_name` und `relative_path` auf `.csv.gz`. Der ursprüngliche CSV-Name bleibt optional als:

```text
original_file_name
```

erhalten.

### 11.3 Manifestbereinigung

Nach erfolgreicher Retentionslöschung wird der Dateieintrag aus `files[]` entfernt. Das Runtime-Event enthält:

```text
event_type=measurement_file_deleted
measurement_file_id
logical_stream_id
last_measurement_epoch_ms
compressed_size_bytes
retention_reason=MAX_AGE|MAX_TOTAL_BYTES|FALLBACK_COUNT
```

### 11.4 Manifestgröße

Das Manifest enthält nur physisch vorhandene Messdateien. Dadurch wächst es nicht dauerhaft mit gelöschten Archiven.

---

## 12. Sidecars

### 12.1 Config-Snapshots

`zec_config_snapshots.json` darf nur Snapshots löschen, die:

- von keiner im Manifest vorhandenen Datei referenziert werden;
- älter als die älteste erhaltene Messdatei sind;
- nicht dem aktuellen `config_control_hash` entsprechen.

Die Bereinigung erfolgt erst nach erfolgreicher Measurement-Retention.

### 12.2 Runtime-Events

`zec_runtime_events.jsonl` erhält eine eigene größenbasierte Rotation und gzip-Archivierung. Die Aufbewahrung darf nicht kürzer sein als die Measurement-Retention.

Ein Runtime-Event darf nicht gelöscht werden, solange eine erhaltene Measurement-Datei denselben Zeitraum abdeckt und das Event für deren Interpretation erforderlich sein kann.

### 12.3 Graphstore

SQLite-Graphstore und CSV-Retention bleiben getrennte Datenprodukte. Die CSV-Retention darf keine SQLite-Löschung auslösen. SQLite besitzt eine eigene Aggregations-/Retentionstrategie.

---

## 13. Tool- und Exportkompatibilität

Vor Aktivierung von `compress_only` oder `enforce` müssen alle relevanten Werkzeuge `.csv` und `.csv.gz` streamingbasiert unterstützen.

### 13.1 Verbindlich anzupassen

```text
tools/create_zec_analysis_package.sh
tools/replay_csv.py
tools/replay_core.py
tools/replay_report.py
tools/import_measurements_to_db.py
tools/backfill_measurement_reasons.py
RC17-/RC18-Branch-Auswerter
Storage-Analyzer
Analysepaket-Validierung
Status-/Download-Endpunkte für Messdaten
```

### 13.2 Reader-Vertrag

Python:

```text
.csv     → open(..., encoding="utf-8", newline="")
.csv.gz  → gzip.open(..., mode="rt", encoding="utf-8", newline="")
```

Alle Reader müssen:

- zeilenweise streamen;
- tatsächlichen Header klassifizieren;
- gemischte Schema- und Kompressionsstände unterstützen;
- gzip-CRC-/EOF-Fehler melden;
- bei einer beschädigten Datei andere Dateien weiter analysieren können.

### 13.3 Analysepaket

Das Paket übernimmt `.csv.gz` vorzugsweise unverändert. Es dekomprimiert nicht automatisch und verdoppelt dadurch nicht temporär den Speicherbedarf.

`--latest-only` ermittelt die jüngste logische Messdatei anhand Manifest/Measurement-Zeit, nicht nur anhand Dateiendung oder mtime.

### 13.4 Locking

Neuer Lock:

```text
.zec_measurement_storage.lock
```

- Maintenance verwendet exklusiven Lock.
- Analysepaket, Import und manuelle Exporte verwenden Shared-Lock während Dateiinventur und Kopie/Lesen.
- Kann ein Lock nicht innerhalb kurzer Zeit erworben werden, wartet Maintenance bis zum nächsten Lauf; die Regelung ist davon unberührt.

---

## 14. RC18-Feldbudget-Addendum

Dieser Abschnitt ersetzt die bisherige Festlegung „16 additive Standardfelder“ aus Abschnitt 11 der RC18-Async-Local-API-Spezifikation.

### 14.1 Grundsatz

Nur Werte, die für die Rekonstruktion **jedes einzelnen Regelzyklus** notwendig sind, gehören in jede Standardzeile. Workerzustände, Fehlertexte, Backoff und Configgeneration werden als Status- und Runtime-Eventdaten geführt.

### 14.2 Acht additive Standardfelder

Verbindlich in Standard und damit auch in Extended:

```text
zendure_local_api_snapshot_sequence
zendure_local_api_success_sequence
zendure_local_api_new_success_applied
zendure_local_api_last_success_age_s
zendure_local_api_snapshot_valid
zendure_local_api_snapshot_stale
zendure_local_api_request_duration_ms
zendure_local_api_snapshot_apply_ms
```

Neue Feldzahlen:

```text
RC17 Standard:   238
RC18 Standard:   246

RC17 Extended:   241
RC18 Extended:   249
```

Die finalen Header-Hashes entstehen erst aus dem gebauten Vertrag.

### 14.3 Zyklische Semantik

- `snapshot_sequence`: letzter vom Hauptthread beobachteter Worker-Attempt-/Snapshotstand;
- `success_sequence`: Identität des letzten erfolgreichen Datensnapshots;
- `new_success_applied`: nur im tatsächlichen Apply-Zyklus `1`, sonst `0`;
- `last_success_age_s`: monotones Alter des aktuell verfügbaren Erfolgs;
- `snapshot_valid`: Erfolg vorhanden und Configgeneration passend;
- `snapshot_stale`: vom Controller tatsächlich verwendetes Stale-Ergebnis;
- `request_duration_ms`: nur in dem Zyklus befüllt, in dem ein neuer abgeschlossener Attemptstatus übernommen wird, sonst leer;
- `snapshot_apply_ms`: nur bei tatsächlicher synchroner Verarbeitung befüllt, sonst leer.

`request_duration_ms` bleibt ausdrücklich außerhalb von `cycle_total_without_sleep_ms`.

### 14.4 Aus Standard entfernte acht Felder

Nicht zyklisch in Measurement V4:

```text
zendure_local_api_worker_state
zendure_local_api_worker_config_generation
zendure_local_api_latest_attempt_ok
zendure_local_api_last_attempt_age_s
zendure_local_api_consecutive_errors
zendure_local_api_backoff_remaining_s
zendure_local_api_latest_error_code
zendure_local_api_parse_warning_count
```

Diese Werte bleiben vollständig verfügbar über:

- `/status`;
- `/ready`, soweit relevant;
- Local-API-Statuskarte;
- `zec_runtime_events.jsonl`;
- Produktivanalysepaket.

### 14.5 Verbindliche Runtime-Events RC18

```text
local_api_worker_started
local_api_worker_stopped
local_api_config_generation_changed
local_api_attempt_completed
local_api_snapshot_applied
local_api_snapshot_discarded_generation_mismatch
local_api_backoff_entered
local_api_backoff_left
local_api_parse_warning
local_api_worker_error
```

`local_api_attempt_completed` enthält mindestens:

```text
snapshot_sequence
success_sequence
worker_config_generation
attempt_ok
request_duration_ms
consecutive_errors
backoff_remaining_s
error_code
parse_warning_count
```

Damit bleibt die vollständige Workerhistorie erhalten, ohne sie alle drei Sekunden zu duplizieren.

### 14.6 Bytebudget RC18

Unter einem repräsentativen RC17-Produktivzustand darf die durchschnittliche Standardzeile allein durch RC18 höchstens wachsen um:

```text
64 Bytes pro Zeile
oder 4,5 % gegenüber derselben RC17-Fixture
```

Zielwert:

```text
typisch +25 bis +45 Bytes pro Zeile
```

Lange Freitext-Reason-Felder sind für RC18 im zyklischen Standardprofil verboten.

### 14.7 Änderung der RC18-Spezifikation

Alle bisherigen Stellen mit:

```text
254 Standardfelder
257 Extendedfelder
16 neue Measurement-Felder
```

werden ersetzt durch:

```text
246 Standardfelder
249 Extendedfelder
8 neue Measurement-Felder
8 Status-/Runtime-Eventfelder
```

---

## 15. Zeilengrößen- und Retentionsdiagnose

### 15.1 Dynamische Zeilengröße

Der Logger führt pro Profil eine EWMA der tatsächlich serialisierten Zeilengröße:

```text
alpha = 0,01
```

Statuswerte:

```text
measurement_actual_row_bytes_ewma
measurement_projected_bytes_per_day
measurement_projected_files_per_day
measurement_archive_total_bytes
measurement_archive_oldest_time
measurement_archive_compression_ratio
```

Diese Werte gehören ausschließlich in Status/UI, nicht als weitere zyklische Measurement-Spalten.

### 15.2 Fallback vor erster Zeile

Schemaprofilabhängige Startwerte:

```text
Standard:   1.600 Bytes
Extended:   5.000 Bytes, bis reale Produktivdaten vorliegen
```

`MEASUREMENT_LOG_ESTIMATED_ROW_BYTES` wird für V4 nicht mehr als primäre Wahrheit verwendet. Der Key bleibt nur rückwärtskompatibel.

### 15.3 UI-Warnung zur Dateigröße

Die Settings-Seite zeigt eine nicht blockierende Warnung, wenn die konfigurierte Dateigröße voraussichtlich zu mehr als acht Dateien pro Tag führt.

Für den aktuellen Produktivwert von 3 MB wäre die Warnung aktiv. Eine Erhöhung auf 10–25 MB wird empfohlen, aber niemals automatisch durchgeführt.

---

## 16. Tests

### 16.1 Unit- und Integrationstests Storage

1. aktive Datei wird nie komprimiert;
2. geschlossene stabile Datei wird komprimiert;
3. Kompressionsfehler erhält Quelle;
4. SHA256-Abweichung erhält Quelle und markiert Fehler;
5. gültige gzip-Datei ist vollständig dekomprimierbar;
6. Manifest-ID bleibt bei Kompression gleich;
7. Pfad wechselt atomar auf `.csv.gz`;
8. Quelle wird erst nach Manifestupdate entfernt;
9. Crash nach Tempwrite wird reconciliert;
10. Crash nach finalem gzip vor Manifestupdate wird reconciliert;
11. Crash nach Manifestupdate vor Source-Unlink wird reconciliert;
12. `.gz.tmp` wird nicht als Messdatei analysiert;
13. Retention löscht nur verifizierte Archive;
14. Retention schützt aktuelle Session;
15. Retention schützt konfigurierte jüngste Stunden;
16. Max-Age löscht älteste zuerst;
17. Max-Total-Bytes löscht älteste zuerst;
18. inkonsistente Datei wird nicht gelöscht;
19. Shared-Lock verhindert Maintenance-Delete;
20. Exclusive-Lock blockiert nicht den Regelthread;
21. Fallback-Anzahl wird real begrenzt;
22. Config-Snapshot bleibt solange referenziert;
23. unreferenzierter alter Config-Snapshot wird bereinigt;
24. Manifest enthält nur vorhandene Dateien;
25. Runtime-Delete-Event enthält vollständige Identität;
26. report_only verändert keinen Bytewert und keine mtime;
27. compress_only löscht keine Archive aufgrund von Retention;
28. enforce respektiert Age-, Byte- und Protect-Grenzen;
29. Maintenance verarbeitet höchstens acht Dateien je Lauf;
30. Neustart erzeugt keine unbounded Taskqueue.

### 16.2 Toolkompatibilität

31. Analysepaket mit nur CSV;
32. Analysepaket mit nur CSV.GZ;
33. Analysepaket mit gemischtem Bestand;
34. `--latest-only` wählt korrekte logische Datei;
35. Replay liest gzip streamingbasiert;
36. Import liest gzip streamingbasiert;
37. Branch-Auswerter liest gzip streamingbasiert;
38. beschädigtes gzip wird gemeldet, übrige Dateien werden verarbeitet;
39. historische Header in gzip bleiben klassifizierbar;
40. Paket enthält Manifest und Sidecars konsistent.

### 16.3 RC18-Feldbudget

41. Standardheader exakt 246 Felder;
42. Extendedheader exakt 249 Felder;
43. acht neue Felder in beiden Profilen vorhanden;
44. acht Worker-/Fehlerfelder nicht im zyklischen Header;
45. alle acht ausgelagerten Werte im Status vorhanden;
46. alle ausgelagerten Änderungen als Runtime-Events rekonstruierbar;
47. `request_duration_ms` nur bei neuem Attemptstatus befüllt;
48. `snapshot_apply_ms` nur bei Apply befüllt;
49. HTTP-Dauer fließt nicht in Zyklussumme ein;
50. durchschnittliches RC18-Zeilenplus <=64 Byte beziehungsweise <=4,5 %;
51. kein neues langes Freitextfeld im Standardprofil;
52. Configgeneration-Mismatch über Event und Sequenzen nachweisbar;
53. stale/valid-Fall pro Regelzyklus rekonstruierbar;
54. kein wiederholtes Apply desselben `success_sequence`.

### 16.4 Performance und Hardware

55. gzip Level 1 erreicht auf realer Standardprobe mindestens 90 % Einsparung;
56. gzip Level 1 wird gegen Level 6 bezüglich CPU-Zeit und Quote dokumentiert;
57. Maintenance-Lauf erhöht Zyklus-p95 höchstens um 2 ms;
58. kein Zyklus >1 s wegen Maintenance;
59. kein RAM-Wachstum mit Dateianzahl;
60. keine vollständige Datei im RAM;
61. keine zusätzlichen Command-Publishes;
62. keine zusätzlichen Resyncs;
63. keine zusätzlichen acMode-Wechsel;
64. keine zusätzlichen physischen Richtungswechsel;
65. keine zusätzlichen 0-W-Zwischenzustände;
66. kein periodisches fsync pro Messzeile;
67. maximal ein fsync pro erfolgreich erzeugtem Archiv plus Manifesttransaktion;
68. Fallback-/SD-Schreiblast bleibt begrenzt.

---

## 17. Produktivabnahme

### 17.1 Report-only

Mindestens 24 Stunden:

- keine Dateiänderung;
- vorgeschlagene Kompressionskandidaten plausibel;
- aktive Datei korrekt ausgeschlossen;
- prognostizierte Einsparung plausibel;
- keine Regelzyklusverschlechterung.

### 17.2 Compress-only

Mindestens 48 Stunden:

- alle geschlossenen geeigneten Dateien verifiziert komprimiert;
- keine verlorene Measurement-ID;
- Analysepaket, Replay und Branchanalyse funktionieren mit gzip;
- gemessene Einsparung Standard mindestens 90 %;
- keine beschädigten Archive;
- keine Regel-/Command-/Hardware-Nebenwirkung.

### 17.3 Enforce

Erst nach ausdrücklicher Nutzerfreigabe:

- Retentionsvorschau dokumentieren;
- zu löschende älteste Zeitgrenze anzeigen;
- ersten Enforce-Lauf mit Download-/Backupnachweis begleiten;
- Manifest und Sidecars danach konsistent;
- älteste verfügbare Measurement-Zeit stimmt mit UI/Status;
- keine Datei innerhalb Protect-Hours gelöscht.

---

## 18. Empfohlenes Zielprofil für die vorhandene Installation

Keine sofortige Configänderung; Zielwerte erst nach Implementierung und report-only-Abnahme setzen.

Empfohlene spätere Konfiguration:

```text
MEASUREMENT_LOG_MAINTENANCE_MODE             = enforce
MEASUREMENT_LOG_COMPRESSION_MIN_AGE_MINUTES  = 15
MEASUREMENT_LOG_RETENTION_MAX_AGE_DAYS       = 90
MEASUREMENT_LOG_RETENTION_MAX_TOTAL_BYTES    = 2000000000
MEASUREMENT_LOG_RETENTION_PROTECT_HOURS      = 48
MEASUREMENT_LOG_MAX_BYTES                    = 25000000
```

Die Änderung von aktuell 3 MB auf 25 MB erfolgt ausschließlich nach separater Freigabe. Erwartete Wirkung bei RC17-Größe:

```text
3 MB:     ca. 14–15 Dateien/Tag
25 MB:    ca. 1,7 Dateien/Tag
```

Bei gemessener RC17-Kompression würden 90 Tage Standard grob deutlich unter 250 MiB liegen; die 2-GB-Grenze bietet Reserve für Extended-Phasen, Sidecars, schlechtere Kompressionsquoten und Schemawachstum.

---

## 19. Freigabegrenzen

Mit dieser Spezifikation ist freigegeben:

- fachliche Planung;
- Codeinventur;
- Testentwurf;
- spätere Implementierungsabschätzung;
- Anpassung der RC18-Spezifikation auf das reduzierte Feldbudget.

Nicht freigegeben:

- Änderung produktiver Configwerte;
- Kompression vorhandener Dateien;
- Löschung vorhandener Dateien;
- Änderung von `MEASUREMENT_LOG_MAX_BYTES`;
- Build eines Storage-Härtungsreleases;
- Build von RC18.

---

## 20. Entscheidungsstand

```text
Akuter Speicherengpass:                    nein
fehlende V4-Gesamtretention:               nachgewiesen
veraltete Zeilengrößenschätzung:           nachgewiesen
Kompressionspotenzial:                     95,79 % bei RC17/Level 6
Storage-Härtungsarchitektur:               spezifiziert
Destruktive Migration:                     ausgeschlossen
RC18 zyklische neue Felder:                8 statt 16
RC18 Standardfeldzahl geplant:             246 statt 254
RC18 Extendedfeldzahl geplant:             249 statt 257
Buildfreigabe:                             nicht erteilt
Produktivänderung:                         keine
```
