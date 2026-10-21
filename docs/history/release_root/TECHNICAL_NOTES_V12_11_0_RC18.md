# Technical Notes V12.11.0-RC18

V12.11.0-RC18 ist ein kleiner Datenmigrations-/Verifikationsrelease auf Basis von RC17.

## Ziel

RC17 führte den parallelen SQLite-Graph-/Measurement-Store ein. RC18 ergänzt dazu ein manuell startbares Migrationstool, damit vorhandene Measurement-CSV-Logs einmalig in die SQLite-Datenbank importiert werden können. Dadurch stehen für die Status- und Graph-Webseiten sofort Echtdaten zur Verfügung, ohne auf neu einlaufende Messpunkte warten zu müssen.

## Neues Tool

```text
tools/import_measurements_to_db.py
```

Eigenschaften:

- streaming-basierte CSV-Verarbeitung, keine Vollbeladung großer Logs in den RAM;
- automatische Ziel-DB-Ermittlung über `MEASUREMENT_DB_*`;
- automatische Log-Verzeichnis-Ermittlung über die Measurement-Konfiguration;
- optionale direkte Datei-/Glob-/Verzeichnisangabe;
- Batch-Schreiben in SQLite;
- nutzt die RC17-Extraktionslogik aus `measurement_db.extract_measurement_point`;
- befüllt `measurement_raw` und `measurement_1min`;
- Fortschrittsausgaben für Pi-Betrieb;
- `--dry-run` für Probeprüfung;
- `--reset` für bewussten Neuaufbau der SQLite-Datei.

Beispiel:

```bash
cd /opt/zendure-controller
python3 tools/import_measurements_to_db.py --log-dir /mnt/zec-usb/ZEC/logs
```

Mit explizitem Ziel:

```bash
python3 tools/import_measurements_to_db.py --db-path /mnt/zec-usb/ZEC/logs/zec_measurements.sqlite3 /mnt/zec-usb/ZEC/logs/zendure_measurements*.csv
```

## Nicht-Ziele

- Keine automatische Migration beim Controller-Start.
- Kein Import alter V2-Legacydaten als Pflichtfunktion.
- Keine Änderung an CSV-/V4-Messdaten.
- Keine Änderung an AUTO, Nachtmodus, Cross-Charge, Restüberschuss-Ernte oder MQTT-Kommandos.

## Tests

Zusätzlich zu den bestehenden RC17-Tests ergänzt RC18 Tests für:

- Versionlabel RC18;
- Import einer semikolongetrennten V4-Measurement-CSV in SQLite;
- erzeugte `measurement_raw`- und `measurement_1min`-Zeilen;
- Abfrage über `query_graph_points`;
- CLI-`--dry-run` ohne DB-Schreibzugriff.
