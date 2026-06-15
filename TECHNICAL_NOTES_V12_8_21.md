# Technical Notes V12.8.21

V12.8.21 ist ein kleiner UI-/Dokumentations-Nacharbeitsrelease auf Basis von V12.8.20. Die AUTO-Regelstrategie, Statusseite, MQTT-Subscriptions, MQTT-Kommandostruktur, CSV-Schema und das Datenmodell bleiben unverändert.

## Anlass

Nach dem erfolgreichen Diagramm-/Balkenlayout-Fix in V12.8.20 enthielten einzelne Analyse-Hilfetexte noch historische Formulierungen wie `Seit V12.8.17 ...`. Für UI-Hilfetexte ist das nicht sinnvoll: Die Oberfläche soll den aktuellen Funktionsstand erklären; Versionshistorie gehört in README, Changelog oder Technical Notes.

## Änderungen

- Analyse-Hilfetext zu `NIGHT_DISCHARGE` gegenwartsbezogen formuliert.
- High-SOC-Hinweise in der Analyse von Versionshistorie bereinigt.
- Installations-/Betriebshinweise im aktuellen Bedienabschnitt gegenwartsbezogen formuliert.
- Neuer Test `tests/test_v12_8_21_help_texts.py` prüft, dass Analyse-Hilfetexte keine historischen Versionsformulierungen enthalten.

## Nicht geändert

- Keine Änderung am Live-Regelalgorithmus.
- Keine Änderung an Statusseite oder Diagramm-Balkenlayout gegenüber V12.8.20.
- Keine Änderung an MQTT-Subscriptions oder MQTT-Kommandostruktur.
- Kein Wechsel des CSV-Schemas; `ZEC-MEASUREMENT-V2` bleibt unverändert.
- Finale Excel-Lernsimulation bleibt unverändert in `tools/`.
