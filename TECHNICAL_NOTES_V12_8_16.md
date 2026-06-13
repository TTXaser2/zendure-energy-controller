# Technical Notes V12.8.16

V12.8.16 ist eine gezielte Nacharbeit zur Nachtmodus-Reserve-SOC-Logik aus V12.8.15. Die AUTO-Regelstrategie bleibt unverändert.

## Ziel

`NIGHT_DISCHARGE_STOP_SOC_PERCENT` soll keine einmalige Sperre für das gesamte Nachtfenster sein, sondern eine laufende Untergrenze für die Nachtentladung. Damit entspricht die Logik der Bedienintention: nachts nicht unter den Reserve-SOC entladen, aber bei später wieder höher gemeldetem SOC im selben Nachtfenster wieder laufen dürfen.

## Änderungen

- Nachtfenster-Latch aus der Reserve-SOC-Logik entfernt.
- Keine Hysterese eingeführt.
- Stop-Bedingung: `SOC <= NIGHT_DISCHARGE_STOP_SOC_PERCENT`.
- Lauf-/Wiederanlauf-Bedingung: `SOC > NIGHT_DISCHARGE_STOP_SOC_PERCENT`, sofern Nachtfenster, SOC-Freshness und MQTT-Kommandopfad gültig sind.
- Statusgrund `NIGHT_RESERVE_SOC` bleibt erhalten.
- Latch-spezifische Diagnosefelder aus Status-/Graph-/CSV-Datensatz entfernt.
- Settings-UI mit `hh:mm`-Zeitfeldern und automatischer Normalisierung bleibt unverändert aus V12.8.15 erhalten.

## Tests

Erweiterte/angepasste Tests in `tests/test_v12_8_15_night_mode.py` prüfen:

- Nachtmodus ohne Reserve-SOC verhält sich wie bisher.
- Stop bei `SOC == NIGHT_DISCHARGE_STOP_SOC_PERCENT`.
- Wiederanlauf im selben Nachtfenster bei `SOC > NIGHT_DISCHARGE_STOP_SOC_PERCENT`.
- Stop-Grund wird beim Verlassen des Nachtfensters zurückgesetzt.
- globaler `MIN_SOC_PERCENT` bleibt harte Grenze.
- CSV-/Graph-Felder enthalten Reserve-SOC und Stop-Grund, aber keine Latch-Felder mehr.

## Nicht geändert

- Keine Änderung der AUTO-Regelstrategie.
- Keine Änderung an MQTT-Topic-Struktur oder Subscriptions.
- Keine Änderung an der finalen Excel-Lernsimulation.
- Kein Wechsel des CSV-Schemas; V12.8.16 bleibt bei `ZEC-MEASUREMENT-V2`.
