# Technical Notes V12.8.15

V12.8.15 ist eine gezielte Nachtmodus-Erweiterung auf Basis von V12.8.14. Die AUTO-Regelstrategie bleibt unverändert.

## Ziel

Der Nachtmodus kann nun optional nicht nur bis zur Endzeit oder bis zum globalen Mindest-SOC entladen, sondern bis zu einem eigenen Reserve-/Stop-SOC. Damit kann morgens Reserve im Zendure-Akku für Lastspitzen verbleiben.

## Änderungen

- Neue optionale Config-Option `NIGHT_DISCHARGE_STOP_SOC_PERCENT`.
- `None`, leer oder nicht gesetzt bedeutet: bisheriges Verhalten.
- Wenn gesetzt, wird der wirksame Nachtmodus-Stop-SOC als mindestens globaler `MIN_SOC_PERCENT` behandelt.
- Wenn der Reserve-SOC erreicht wird, setzt der Controller die Nachtentladung auf 0 W und aktiviert einen Nachtfenster-Latch.
- Der Latch verhindert einen erneuten Start im selben Nachtfenster, auch wenn der gemeldete SOC danach geringfügig steigt.
- Der Latch wird zurückgesetzt, sobald das Nachtfenster verlassen wurde.
- Status, Graph und CSV enthalten Diagnosefelder für Nachtmodus-Stop-SOC, Latch und Stop-Grund.
- Die Settings-Webseite zeigt Nachtmodus-Start und -Ende als `hh:mm`-Felder. Intern bleiben die bisherigen Hour-/Minute-Config-Felder erhalten.
- Uhrzeitfelder werden im Browser beim Verlassen normalisiert, z. B. `5:30` -> `05:30`.
- Server-seitige Validierung lehnt ungültige Uhrzeiten und einen Nachtmodus-Reserve-SOC unterhalb des globalen Mindest-SOC ab.

## Tests

Neue Tests in `tests/test_v12_8_15_night_mode.py` prüfen:

- Nachtmodus ohne Reserve-SOC verhält sich wie bisher.
- Stop bei `NIGHT_DISCHARGE_STOP_SOC_PERCENT`.
- Latch verhindert Wiederanlauf im selben Nachtfenster.
- Latch-Reset nach Verlassen des Nachtfensters.
- globaler `MIN_SOC_PERCENT` bleibt harte Grenze.
- Validierung für Reserve-SOC unter Mindest-SOC.
- CSV-/Graph-Felder für den Nachtmodus-Vertrag.
- Settings-UI mit zwei `hh:mm`-Feldern statt vier internen Feldern.
- Uhrzeitnormalisierung und serverseitige Zeitfeld-Mappinglogik.

## Nicht geändert

- Keine Änderung der AUTO-Regelstrategie.
- Keine Änderung an MQTT-Topic-Struktur oder Subscriptions.
- Keine Änderung an der finalen Excel-Lernsimulation.
- Kein Wechsel des CSV-Schemas; V12.8.15 bleibt bei `ZEC-MEASUREMENT-V2`.
