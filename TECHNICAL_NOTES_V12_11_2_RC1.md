# Technical Notes – V12.11.2-RC1

## Ziel

V12.11.2-RC1 kombiniert zwei eng abgegrenzte Themen:

1. Neue Statusseite mit zentralem Snapshot-Refresh, Hauptkarten und Speicher-SOC-Tagesgraph.
2. Bereinigung der COMMAND_RESYNC-/COMMAND_NOT_EFFECTIVE-Diagnose ohne Änderung der Regelstrategie.

## Latch-/Race-/Prioritätsprüfung

### COMMAND_RESYNC

Die Resync-Deduplizierung basiert nicht allein auf „dieser Sollwert wurde bereits gesendet“. Ein identischer Sollwert bleibt erneut sendbar, wenn eine belastbare Unsicherheit besteht, insbesondere bei längerem STALE, Reconnect, hartem MQTT-Verlust, unsicher gesendetem aktiven Sollwert oder bestätigtem Soll-/Ist-Mismatch.

Der Zustandsautomat nutzt nur In-Memory-Zustände, Zeitstempel und bereits vorhandene Telemetrie-Snapshots. Es gibt keine zusätzlichen MQTT-Reads, Zendure-API-Aufrufe, Netzwerkzugriffe, Datenbankzugriffe, Dateizugriffe, Sleeps oder Retry-Schleifen im Regelpfad. Dadurch entsteht keine neue blockierende Prioritätsumkehr gegenüber dem Regelzyklus.

### COMMAND_NOT_EFFECTIVE

Der Zustand wird nur gesetzt, wenn:

- ein relevanter Nicht-Null-Sollwert aktiv ist,
- die Diagnosegrenze überschritten wird,
- die Telemetrie frisch/plausibel ist,
- die Abweichung über die Mindestzeit bestehen bleibt,
- keine legitimen SOC-/Schutz-/Cross-Charge-Limiter die Abweichung erklären.

Übergänge:

- `no_command`: Zielwert 0 W.
- `COMMAND_PENDING`: neuer relevanter Sollwert, Reaktionszeit läuft.
- `COMMAND_TELEMETRY_UNCERTAIN`: Wirksamkeit nicht bewertbar; kein Gerätefehler.
- `COMMAND_MISMATCH_CONFIRMED`: persistenter plausibler Mismatch.
- `COMMAND_EFFECTIVE` / `COMMAND_LIMITED_BY_SOC_OR_POWER`: Wirkung plausibel oder legitim begrenzt; `COMMAND_NOT_EFFECTIVE` wird deterministisch gelöscht.

Ein vorheriger `COMMAND_NOT_EFFECTIVE`-Limiter wird bei Recovery explizit entfernt, damit der Diagnosezustand nicht „kleben“ bleibt.

## UI-Architektur

Die neue Statusseite ruft Livewerte über `/status-view-data` ab. Die Kartenlogik ist snapshot-basiert und transportneutral vorbereitet. Der Speicher-SOC-Tagesgraph nutzt `/storage-soc-day-data?date=YYYY-MM-DD`, 00:00–24:00 Tagesachsen und Cache. Schwere Analyse-/Availability-Endpunkte werden nicht im Live-Refresh verwendet.

## Tests

Neu: `tests/test_v12_11_2_rc1_ui_command_lifecycle.py`

Abgedeckt:

- kurzer PARTIAL_STALE-Recovery erzeugt keinen unnötigen Resync,
- langer STALE-Recovery sendet identischen aktiven Sollwert erneut,
- `COMMAND_NOT_EFFECTIVE` recovered deterministisch bei passender Istleistung,
- unsichere Telemetrie wird nicht als bestätigter Gerätefehler gewertet,
- neue Statusseite enthält Hauptkarten, Snapshot-Endpunkt und Tagesgraphnavigation.
