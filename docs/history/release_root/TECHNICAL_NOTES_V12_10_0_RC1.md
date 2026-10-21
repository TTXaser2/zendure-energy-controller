# Technical Notes V12.10.0-RC1

## Ziel

V12.10.0-RC1 aktiviert erstmals `ZEC-MEASUREMENT-V4` als realen Loggingpfad, ohne die Reglerlogik, MQTT-Subscriptions oder MQTT-Kommandostruktur zu ändern. V3 bleibt als Legacy-/Rollback-Pfad erhalten.

## Neue Module

- `measurement_v4_contract.py`: finaler V4-Header, Extended-Header, Enums, Bitmasks und Header-Hash.
- `measurement_v4.py`: V4-Writer, V3->V4-Row-Builder, Manifest-, Config-Snapshot- und Runtime-JSONL-Schreiber.

## Aktivierung

Neue/normalisierte Konfigurationen erhalten `MEASUREMENT_SCHEMA_VERSION=4`. Bei `MEASUREMENT_LOG_MODE=standard` oder `extended` schreibt der Controller V4-Dateien. Wird der bisherige Standarddateiname `zendure_measurements.csv` verwendet, schreibt V4 bewusst nach `zendure_measurements_v4.csv`, damit bestehende V3-Dateien nicht gemischt werden.

Rollback auf Legacy-V3 ist über `MEASUREMENT_SCHEMA_VERSION=3` möglich.

## V4-Dateien

- `zendure_measurements_v4.csv`
- `zec_measurement_manifest.json`
- `zec_config_snapshots.json`
- `zec_runtime_events.jsonl`

## Sicherheitsgrenzen

- Keine Änderung an AUTO-Regelstrategie, Nachtmodus, Cross-Charge-Strategie oder MQTT-Kommandos.
- Schreibfehler bei Manifest oder Config-Snapshot pausieren nur das Measurement-Logging; Regler und MQTT-Kommandopfad laufen weiter.
- V3 bleibt im Code erhalten.

## Tests

`python -m unittest discover -q` → 141 Tests OK.
