# Release Info – Zendure Energy Controller V12.13.0

**Version:** `12.13.0`  
**Label:** `V12.13.0`  
**Build-ID:** `v12.13.0-20260811`

## Zweck

V12.13.0 ist der freigegebene Measurement-V4-only-/Legacy-V3-Cleanup auf Basis V12.12.2. Der produktive Runtime-Schreibpfad ist ausschließlich Measurement V4; historische V3-Dateien bleiben ausschließlich über Offline-/Read-only-Werkzeuge lesbar.

## Muss-Scope

1. produktiven V3-Writer und Runtime-Fallback entfernen;
2. fehlende oder historische Schemaauswahl darf keinen V3-Writer aktivieren;
3. historische Config `MEASUREMENT_SCHEMA_VERSION=3` kontrolliert auf `4` migrieren;
4. Schemaauswahl in Registry/Config auf festen versteckten V4-Kompatibilitätsmarker reduzieren;
5. internen Controller-/Graph-Snapshot von V3-Schemaidentität entkoppeln;
6. globale mehrdeutige `version.CSV_SCHEMA` entfernen;
7. `/graph-data.csv` als eigenständigen `ZEC-GRAPH-EXPORT-V1` kennzeichnen;
8. historische V3-Lesefähigkeit in Replay/Analyse/Import ausdrücklich offline/read-only erhalten;
9. produktiven Measurement-V4-Contract unverändert lassen.

## Measurement-Vertrag

Produktiv gilt ausschließlich:

```text
ZEC-MEASUREMENT-V4
Standard: 246 Felder
Extended: 249 Felder
```

Der Graph-CSV-Download ist kein Measurement-Paket und trägt deshalb die eigenständige Kennung `ZEC-GRAPH-EXPORT-V1`.

## Abgrenzung

Nicht Bestandteil sind Regler-/Harvest-/Cross-Charge-/NIGHT-/Command-Änderungen, ein neues Measurement-Schema, SQLite-/Storage-Redesign oder die Löschung historischer V3-Datendateien.
