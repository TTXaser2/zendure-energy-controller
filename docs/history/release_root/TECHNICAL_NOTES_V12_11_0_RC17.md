# Technical Notes V12.11.0-RC17

## Schwerpunkt

V12.11.0-RC17 ergänzt einen SQLite-basierten Graph-/Measurement-Store als parallele, leichte Datenbasis für Status- und Graph-Webseiten.

Der Release ist eine technische Grundlage für schnelle GUI-Historienabfragen. Die bisherige CSV-/V4-Messdatenablage bleibt unverändert erhalten.

## Motivation

Auf dem Raspberry Pi waren die historischen HTTP-Endpunkte trotz RC16 noch zu langsam:

- `/soc-day-data` ca. 17–18 s
- `/graph-view-data?range=24h&resolution=1min` ca. 17–18 s

`/status` selbst war mit ca. 20 ms schnell. Damit lag der Flaschenhals eindeutig in der historischen CSV-/Measurement-Verarbeitung, nicht in der Regelung.

## Neu

- Neues Modul `measurement_db.py`.
- SQLite-Datei `zec_measurements.sqlite3` als optionaler Graphspeicher.
- Standardmäßig aktiviert über `MEASUREMENT_DB_ENABLED=true`.
- DB-Datei liegt automatisch neben dem aktiven Messdatenziel oder optional bei `MEASUREMENT_DB_PATH`.
- Der DB-Schreiber läuft über eine Queue und einen Hintergrund-Writer.
- Bei voller Queue oder DB-Fehlern wird die Regelung nicht blockiert.
- Der DB-Store wird auch befüllt, wenn `MEASUREMENT_LOG_MODE=off` ist.
- 1-Minuten-Aggregation in `measurement_1min` für schnelle Graph-/SOC-Abfragen.
- `/graph-view-data` bevorzugt SQLite-Daten, falls vorhanden.
- `/soc-day-data` bevorzugt SQLite-Daten, falls vorhanden.
- `/measurement-db-status` ergänzt eine einfache DB-Statusdiagnose.
- `/measurements/availability` enthält zusätzlich `measurement_db`.
- Statusseite zeigt in der Karte „Messdaten / Logging“ den SQLite-Graphspeicher.
- `collect_zec_trace.sh` misst zusätzlich `/grid-mini-sparkline` und `/measurement-db-status`.

## SQLite-Schema

### `measurement_raw`

Roh-/Momentwerte je Messpunkt:

- Zeitbasis `ts_ms`
- Netzleistung
- Zendure Soll/Ist
- SOC
- Modus
- Datenstatus
- ausgewählte Zustandsflags

### `measurement_1min`

Vorgefertigte 1-Minuten-Buckets:

- `bucket_start_ms`
- `sample_count`
- `grid_avg_w`, `grid_min_w`, `grid_max_w`
- letzte Zendure-Soll-/Istleistung
- letzter SOC
- letzter Modus
- aggregierte Flags

Die Web-GUI liest primär diese Tabelle, damit 24h-Graphen nicht jedes Mal CSV-Dateien scannen müssen.

## Wichtige Sicherheitsentscheidung

Die DB ist bewusst nachgelagert:

- kein DB-Schreibfehler stoppt den Controller,
- keine DB-Queue blockiert den Reglerzyklus,
- CSV/V4 bleibt als Diagnose- und Fallback-Format erhalten,
- UI-Endpunkte fallen auf vorhandene Measurement-/RAM-Daten zurück, wenn die DB fehlt.

## Konfiguration

Neue Optionen:

- `MEASUREMENT_DB_ENABLED`
- `MEASUREMENT_DB_FILE`
- `MEASUREMENT_DB_PATH`
- `MEASUREMENT_DB_MAX_QUEUE_ROWS`

## Nicht geändert

- Keine Änderung an AUTO.
- Keine Änderung am Nachtmodus-Regelverhalten.
- Keine Änderung an Cross-Charge.
- Keine Änderung an Restüberschuss-Ernte.
- Keine Änderung an Zendure-MQTT-Kommandos oder Topics.
- Keine Änderung am Measurement-V4-CSV-Format.
- Keine Änderung an der finalen Excel-Lernsimulation.

## Hinweise

SQLite auf SD/vfat funktioniert grundsätzlich, ist aber nicht die finale Wunschplattform. Für langfristig robuste Datenhaltung ist die geplante SSD mit ext4 klar vorzuziehen.
