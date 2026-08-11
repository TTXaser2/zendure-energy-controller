# SPEZIFIKATION ZEC V12.13.0 – Measurement V4-only Runtime & Legacy-V3-Cleanup

**Stand:** 11.08.2026  
**Basis:** `zendure_controller_v12_12_2.zip`  
**Basis-Version:** `12.12.2` / `v12.12.2-20260810`  
**Basis-SHA256:** `d2b80098a4fb9ae3d3070f3c009aaaa42a8146a54abda2cd7d6bb0bde4dd8c71`  
**Status:** Inventur und Zielspezifikation; noch keine V12.13.0-Codeänderung

## 1. Ziel

Der produktive ZEC-Runtimepfad wird eindeutig auf **ZEC-MEASUREMENT-V4** festgelegt. Historische V3-Kompatibilität bleibt ausschließlich als **offline/read-only Analysekompatibilität** erhalten. V3 darf weder produktiver Writer, Runtime-Fallback, UI-Auswahl noch impliziter Default sein.

## 2. Inventurbefund V12.12.2

### 2.1 Produktiver Writer ist bereits V4, aber V3 ist weiterhin schaltbar

`csv_logger.py::CsvRotatingLogger.log()` verzweigt aktuell über `measurement_schema_version(config)`:

- Schema `4` → `MeasurementV4Logger`
- sonst → vollständiger Legacy-V3-Writer

`measurement_schema_version()` fällt bei fehlendem Key sogar implizit auf `3` zurück. Damit ist V3 weiterhin echter Runtime-/Schreibpfad.

### 2.2 Interner Controller-Snapshot trägt weiterhin V3-Schemaidentität

`state.py::record_graph_point()` erzeugt den internen RAM-/Graph-/Measurement-Quellsnapshot mit:

- `schema = CSV_SCHEMA`
- `CSV_SCHEMA = "ZEC-MEASUREMENT-V3"`
- `schema_version = "3.0"`

Der V4-Writer konvertiert diesen internen Snapshot anschließend in das V4-Feldschema. Die V3-Kennzeichnung ist für die Konvertierung nicht erforderlich und vermischt interne Controllerdaten mit einem historischen Persistenzschema.

### 2.3 `version.py` exportiert weiterhin V3 als scheinbar globale Schemaidentität

`CSV_SCHEMA = "ZEC-MEASUREMENT-V3"` wird aus `version.py` exportiert. Das ist semantisch falsch, weil die produktive Messgrundlage V4 ist.

### 2.4 Settings-/Config-Schicht bietet V3 weiter als Schemaoption an

`MEASUREMENT_SCHEMA_VERSION` ist noch als Migration-only Setting mit Optionen `4` und `3 / Legacy V3` registriert. `config_manager.py` beschreibt explizites Zurückstellen auf V3 weiterhin als zulässigen Pfad.

### 2.5 `/graph-data.csv` exportiert weiterhin V3

Der Web-Endpunkt serialisiert den RAM-Graphen über `csv_logger.rows_to_csv()`. Damit entsteht weiterhin ein V3-formatierter Export, obwohl dies kein produktiver Measurement-V4-Datensatz samt Manifest/Snapshots ist.

### 2.6 Replay/Analyse besitzt wertvolle historische V3-Lesefähigkeit

`tools/replay_core.py`, `tools/replay_web.py`, `tools/replay_csv.py` und `tools/import_measurements_to_db.py` können historische V3-Dateien lesen. Diese Fähigkeit ist offline/read-only und soll erhalten bleiben. Sie darf aber V3 nicht länger als aktuelles oder primäres Schema ausweisen.

## 3. Verbindliches Zielbild

### 3.1 Runtime

- `CsvRotatingLogger` besitzt **keinen V3-Schreibzweig** mehr.
- `MEASUREMENT_LOG_MODE=standard|extended` schreibt immer V4.
- `MEASUREMENT_LOG_MODE=off` schreibt keine Measurement-CSV, der unabhängige SQLite-Graphstore bleibt wie bisher möglich.
- Fehlender `MEASUREMENT_SCHEMA_VERSION`-Key führt **niemals** zu V3.
- Ein historischer Wert `3` wird bei Upgrade kontrolliert auf `4` migriert; kein stilles V3-Runtimeverhalten.
- Kein V3-Headercheck, keine V3-Rotation und kein V3-Writer im produktiven Controllerpfad.

### 3.2 Config-/Rollback-Kompatibilität

`MEASUREMENT_SCHEMA_VERSION` bleibt in V12.13.0 zunächst als **inertes, verstecktes Kompatibilitäts-/Migrationsmerkmal mit festem Wert `4`** erhalten. Gründe:

1. bestehende V12.12.x-Konfigurationen mit Wert `4` müssen keinen unnötigen Config-Revision-Sprung erfahren;
2. ein Code-Rollback auf V12.12.2 bleibt mit derselben Config sicher V4 und fällt nicht aufgrund eines fehlenden Keys auf dessen historischen V3-Default zurück;
3. Wert `3` wird einmalig und ausdrücklich als Release-Migration `3 → 4` behandelt.

Nicht mehr zulässig:

- UI-Auswahl `Legacy V3`;
- Runtime-Verzweigung aufgrund dieses Keys;
- `MEASUREMENT_LOG_SCHEMA` als aktive Schemawahl.

### 3.3 Interner Snapshot

Der `ControllerState`-Graph-/Zyklusdatensatz wird als **schema-neutraler interner Snapshot** behandelt. Die Felder `schema=ZEC-MEASUREMENT-V3` und `schema_version=3.0` werden aus diesem internen Datensatz entfernt. Der V4-Builder erhält weiterhin dieselben fachlichen Eingangswerte.

### 3.4 Produktive Schema-Konstanten

- `version.CSV_SCHEMA` wird entfernt.
- Der kanonische V4-Vertrag erhält eindeutig benannte Konstanten in `measurement_v4_contract.py`, z. B. `MEASUREMENT_SCHEMA_NAME = "ZEC-MEASUREMENT-V4"` und `MEASUREMENT_SCHEMA_VERSION = 4` bzw. äquivalent ohne Namenskollision zur Config.
- Offline-V3-Code verwendet eine ausdrücklich historische Konstante wie `LEGACY_V3_SCHEMA`.

### 3.5 Graph-CSV-Export

`/graph-data.csv` darf nicht länger einen V3-Measurementdatensatz vortäuschen. Er wird als eigener, schema-neutraler UI-/Graph-Export definiert, z. B. `ZEC-GRAPH-EXPORT-V1`, mit nur für den Graph relevanten Spalten.

Wichtig:

- kein falsches V4-Label auf einer Datei ohne V4-Manifest/Config-Snapshots;
- Endpunkt und Dateiname können zur Abwärtskompatibilität bestehen bleiben;
- dieser Export ist kein Measurement-V4-Analysepaket.

### 3.6 Historische V3-Analyse

V3 bleibt zulässig nur in:

- Offline-Replay alter Dateien;
- Offline-Analyse alter Dateien;
- optionalem historischen Import in den SQLite-Graphstore;
- Regressionstests für genau diese Lesekompatibilität.

UI-/Health-/Reporttexte der Replay-Werkzeuge müssen V4 als aktuelle Grundlage und V3 ausdrücklich als **historisch/read-only** kennzeichnen.

## 4. Klassifikation der Fundstellen

| Komponente | V12.12.2-Befund | V12.13.0-Aktion |
|---|---|---|
| `csv_logger.py` | vollständiger V3-Writer + V3-Default | V3-Writer entfernen; Wrapper nur V4 + DB + gemeinsame Storage-Helfer |
| `state.py` | interner Snapshot als V3 markiert | Schemaidentität aus internem Snapshot entfernen |
| `version.py` | globale `CSV_SCHEMA=V3` | entfernen |
| `config_manager.py` | V3 als zulässige Option/Rollback | V4 fest; Upgrade 3→4; kein Runtime-Schalter |
| `settings_registry.py` | `Legacy V3` auswählbar im Migrationvertrag | nur fester V4-Kompatibilitätswert; Dependency aus `MEASUREMENT_LOG_MODE` entfernen |
| Registry-Snapshot | enthält V3-Option/Dependency | regenerieren |
| `web_ui.py` | `/graph-data.csv` über V3-Serializer | eigener Graph-Export; V3-Import entfernen |
| `controller_logic.py` | Kommentare referenzieren V3-Zeilenschema | auf aktuellen V4-/Runtimevertrag korrigieren |
| `measurement_v4.py` | Kommentare beschreiben parallelen V3-Writer | historische Formulierungen bereinigen; fachliche Fallbacks nicht ändern |
| `tools/replay_core.py` | `CSV_SCHEMA` meint V3; V3+V4 Reader | V3-Reader behalten, Konstante als `LEGACY_V3_SCHEMA`; V4 als primär markieren |
| `tools/replay_web.py` | Health/Validation nennt V3 als Schema | Supported-Schema-Semantik; V3 historisch/read-only |
| `tools/replay_csv.py` | V3/V4 allgemein | Hilfetext: V4 aktuell, V3 historisch |
| `tools/import_measurements_to_db.py` | akzeptiert V3/V4 | read-only Import beibehalten, explizit als Legacy-Import dokumentieren |
| aktuelle Doku/Handbuch | V4 produktiv, V3 noch „Legacy-Pfad“ | präzisieren: V3 nur Offline-Lesen, kein Runtimepfad |
| historische Release-/Technical-Notes | historische V3-Aussagen | **nicht umschreiben** |

## 5. Testmigration

### 5.1 Zu entfernende/ersetzende Runtime-V3-Tests

- V3-Writer-Header/Rotation/Prepare-Row-Tests werden entfernt oder auf V4 umgestellt.
- `measurement_schema_version({}) == 3` wird ersetzt durch Nachweis des festen V4-Vertrags.
- SQLite-Tests verwenden keinen künstlichen V3-Runtimewert mehr.
- Tests, die `version.CSV_SCHEMA == V3` erwarten, werden ersetzt.
- Feldvertragsprüfungen gegen `csv_logger.CSV_FIELDS` wandern auf `measurement_v4_contract.STANDARD_HEADER/EXTENDED_HEADER` oder auf den schema-neutralen internen Snapshot, je nach ursprünglichem Testzweck.

### 5.2 Zu erhaltende Legacy-Tests

- Historische V3-Datei kann durch Replay/Analyse gelesen werden.
- V2 bleibt abgelehnt.
- V3 und V4 dürfen in einem Analyselauf nicht unzulässig vermischt werden, sofern der aktuelle Replayvertrag dies weiterhin vorsieht.
- Offline-SQLite-Import alter V3-Dateien bleibt möglich.

### 5.3 Neue Pflicht-Regressionen

1. fehlender Schema-Key → V4 Writer;
2. Schema-Key `4` → V4 Writer;
3. historischer Schema-Key `3` → Migration auf 4, danach ausschließlich V4;
4. kein produktiver Codepfad erzeugt `ZEC-MEASUREMENT-V3`;
5. kein produktiver Codepfad erzeugt `schema_version=3.0`;
6. `MEASUREMENT_LOG_MODE=off` → keine CSV, SQLite unabhängig weiter möglich;
7. Standard/Extended V4 unverändert 246/249 Felder;
8. Manifest, Config-Snapshots, Runtime-JSONL und Rotation unverändert funktionsfähig;
9. `/graph-data.csv` enthält kein V3-Measurementlabel und ist klarer Graph-Export;
10. Replay liest historische V3-Datei weiterhin read-only;
11. Replay liest V4 weiterhin inklusive Manifest-/Snapshotprüfung;
12. Rollback-Kompatibilität: normalisierte Config enthält weiterhin den festen Marker `MEASUREMENT_SCHEMA_VERSION=4`.

## 6. No-Regression

Unverändert bleiben müssen:

- AUTO_GRID_EXPORT / AUTO_GRID_IMPORT / HOLD;
- Harvest-Zielwertbildung und V12.12.2 monotonic/fresh-distinct Hysterese;
- Cross-Charge;
- NIGHT_DISCHARGE / Reserve / Neutralisierung;
- Command Lifecycle / Resync / Single-Owner-Safety;
- Measurement-V4 Standardheader (246 Felder);
- Measurement-V4 Extendedheader (249 Felder);
- V12.12.2 Manifest Rotation/Rowcount/Close-Semantik;
- SQLite-Graphstore und dessen nichtblockierende Queue;
- Storage-Fallback-/Mountpoint-Verhalten;
- V4 Config-Snapshot- und Runtime-Event-Vertrag;
- historische V3-Dateien auf Datenträgern werden weder gelöscht noch verändert.

## 7. Ausdrücklich nicht im Scope

- V4-Feldschema-Redesign;
- neue Measurement-V5;
- Änderung der Regleralgorithmen;
- neue SQLite-Architektur;
- Löschung/Migration alter V3-Dateien;
- automatisches Umschreiben historischer V3-Dateien auf V4;
- Entfernung der V3-Offline-Lesefähigkeit;
- Replay-/Simulations-Neuentwicklung über die notwendige Semantikbereinigung hinaus;
- neue Supply-Chain-/Installed-Tree-Provenance.

## 8. Erwartete betroffene Dateien

Voraussichtlich:

- `csv_logger.py`
- `state.py`
- `version.py`
- `config_manager.py`
- `settings_registry.py`
- `generated/SETTINGS_REGISTRY_SNAPSHOT.json`
- `web_ui.py`
- `controller_logic.py` (nur Terminologie/Kommentar, keine Regelrechnung)
- `measurement_v4.py` (Legacy-Kommentare/ggf. Konstantenimport; V4-Writerfunktion unverändert)
- `measurement_v4_contract.py` (kanonische Schemaidentität)
- `tools/replay_core.py`
- `tools/replay_web.py`
- `tools/replay_csv.py`
- `tools/import_measurements_to_db.py` (nur explizite Legacy-Semantik, falls nötig)
- betroffene Tests
- aktuelle Handbuch-/Release-Dokumentation
- Installer-/Migrationstest für Schema 3→4

## 9. Exit-Gate V12.13.0

Zusätzlich zum normalen ZEC-Releasegate:

- statischer Nachweis: kein produktiver V3-Writerpfad;
- statischer Nachweis: `ZEC-MEASUREMENT-V3` nur noch unter `tools/`/Legacy-Tests/historischen Dokumenten;
- V4-Header 246/249 byte-/inhaltlich unverändert;
- V4 Writer-, Manifest-, Snapshot-, Runtime-Event- und Storage-Regression vollständig grün;
- Offline-V3-Reader-Test grün;
- Config-Migration 3→4 idempotent und rollbackkompatibel;
- Graph-CSV-Smoke;
- vollständige unittest/pytest/ResourceWarning/Syntax-/Manifestgates;
- finales ZIP erneut frisch extrahieren und Gates wiederholen.

## 10. Versionsziel

**V12.13.0** – normale technische Weiterentwicklung innerhalb des bestehenden Measurement-/Storage-Themas.

