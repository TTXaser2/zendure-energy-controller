# Technical Notes V12.8.17

V12.8.17 ist ein gezielter Hotfix zur Nachtmodus-Reserve-SOC-Logik aus V12.8.16.

## Anlass

Beim Live-Test wurde beobachtet, dass der Controller nach Erreichen von `NIGHT_DISCHARGE_STOP_SOC_PERCENT` innerhalb des Nachtfensters im technischen Pfad `STOP_HOLD` blieb. Dadurch wurde die Netzleistung nicht mehr gelesen und Zendure konnte trotz realem Netzbezug nicht mehr im AUTO-Modus für Lastspitzen einspringen.

## Änderung

`NIGHT_DISCHARGE_STOP_SOC_PERCENT` pausiert ab V12.8.17 nur noch die feste Nacht-Basisentladung:

- Wenn `SOC <= NIGHT_DISCHARGE_STOP_SOC_PERCENT`, wird die feste Nachtentladung einmalig auf 0 W gesetzt.
- Danach läuft der normale AUTO-Zweig weiter.
- Die Grid-/Shelly-/UniMeter-Leistung wird wieder gelesen.
- Bei realem Netzbezug darf Zendure im AUTO-Modus bis zum globalen `MIN_SOC_PERCENT` entladen.
- Der Diagnosegrund `NIGHT_RESERVE_SOC` bleibt erhalten, bedeutet nun aber: feste Nachtentladung pausiert, AUTO-Regelung bleibt aktiv.

Die normale feste Nachtentladung bleibt weiterhin unabhängig von frischen Grid-Daten, solange der Reserve-SOC nicht erreicht ist.

## Nicht geändert

- Keine Änderung am CSV-Schema; weiterhin `ZEC-MEASUREMENT-V2`.
- Keine Änderung an MQTT-Subscriptions oder MQTT-Kommandostruktur.
- Keine Änderung an der AUTO-Zielwertbildung, Deadband-Logik, Cross-Charge-Strategie oder Leistungsgrenzen.
- Finale Excel-Lernsimulation bleibt unverändert unter `tools/` enthalten.

## Tests

Ergänzte/angepasste Tests prüfen insbesondere:

- Reserve-SOC pausiert feste Nachtentladung und führt in den AUTO/Grid-Zweig.
- Bei Netzbezug während pausierter Nachtentladung wird AUTO-Entladung möglich.
- Eine bereits laufende AUTO-Entladung wird im Reserve-SOC-Zustand nicht in jedem Zyklus wieder auf 0 W zurückgesetzt.
- Bei SOC oberhalb Reserve-SOC darf die feste Nachtentladung im selben Nachtfenster wieder laufen.
- Globaler `MIN_SOC_PERCENT` bleibt harte Untergrenze.
