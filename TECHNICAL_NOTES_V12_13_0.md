# Technical Notes – Zendure Energy Controller V12.13.0

## 1. Productive Runtime ist V4-only

`CsvRotatingLogger` besitzt keinen produktiven V3-Schreibzweig mehr. `log()` und Runtime-Events delegieren ausschließlich an `MeasurementV4Logger`. `measurement_schema_version()` liefert für die produktive Runtime fest `4`; ein fehlender Config-Key oder historischer Legacywert kann den Writer nicht auf V3 umschalten.

Die früheren V3-Writer-Primitiven und V3-Rotationspfade des Facade-Loggers wurden entfernt.

## 2. V4-Schemaautorität

`measurement_v4_contract.py` exportiert nun explizit:

```text
MEASUREMENT_SCHEMA_NAME = ZEC-MEASUREMENT-V4
MEASUREMENT_SCHEMA_VERSION = 4
```

Die Feldverträge bleiben unverändert:

```text
STANDARD_HEADER = 246 Felder
EXTENDED_HEADER = 249 Felder
```

Header-SHA256 gegenüber V12.12.2:

```text
Standard: 7842bfef39d47f93dc39689aa04da7658564af565e5051c24f90b32021d184a7
Extended: 8f61d07e66428a6e8757333d35d5dd73dd3a0975ac9a16714b93dc9b86460e93
```

## 3. Config-/Registry-Kompatibilität

`MEASUREMENT_SCHEMA_VERSION` bleibt als versteckter Kompatibilitätsmarker erhalten, besitzt aber nur noch den zulässigen Wert `4` und keine Runtime-Auswahlwirkung mehr.

Die bestehende idempotente Migration behandelt einen historischen V3-Marker ausdrücklich:

```text
3 -> 4
MIG-V12.13-MEASUREMENT-SCHEMA-3-TO-4
```

Ein bereits vorhandener Wert `4` bleibt No-op. Das bewahrt zugleich einen sicheren Rollback auf ältere V12.12.x-Stände, die den Marker weiterhin lesen.

## 4. Schema-neutraler interner Snapshot

`ControllerState` kennzeichnet den internen Zyklus-/Graph-Snapshot nicht mehr als `ZEC-MEASUREMENT-V3` bzw. `schema_version=3.0`. Dieser Datensatz ist ein interner Controller-Snapshot; erst der V4-Writer bildet daraus den persistierten Measurement-V4-Datensatz.

`controller_logic.py` wurde hierfür ausschließlich dokumentarisch angepasst; der semantische AST ist gegenüber V12.12.2 identisch.

## 5. Graph-Exportvertrag

`/graph-data.csv` ist ausdrücklich kein Measurement-V4-Paket. Der Export verwendet:

```text
ZEC-GRAPH-EXPORT-V1
schema_version=1.0
```

Damit wird weder eine historische V3-Identität noch eine unvollständige V4-Paketsemantik vorgetäuscht.

## 6. Historische V3-Kompatibilität

`tools/replay_core.py`, `tools/replay_csv.py`, `tools/replay_web.py` und `tools/import_measurements_to_db.py` dürfen historische V3-Dateien weiterhin offline/read-only verarbeiten.

Dafür wird die eindeutige Konstante `LEGACY_V3_SCHEMA` verwendet. Eine mehrdeutige generische `CSV_SCHEMA`-Konstante existiert auch in diesen Werkzeugen nicht mehr.

## 7. No-Regression

Nicht fachlich geändert werden:

- Single-Instance-/Command-Owner-Safety;
- AUTO/HOLD;
- Harvest-Zielwertbildung und Harvest-Timing aus V12.12.2;
- Cross-Charge;
- NIGHT;
- Command Lifecycle/Resync;
- Measurement-Manifest Rotation/Rowcount/Clean-Close;
- SQLite-/Storage-Vertrag.

`command_lifecycle.py`, `mqtt_bridge.py`, `cross_charge.py`, `zendure_power_observation.py` und das Excel-Lernwerkzeug bleiben byteidentisch. `measurement_v4.py` ändert nur Kommentare; `controller_logic.py` nur einen Docstring. Der V4-Header ist exakt identisch.
