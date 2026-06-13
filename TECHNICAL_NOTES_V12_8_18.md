# Technical Notes V12.8.18

## Ziel

V12.8.18 bündelt UI- und Analyse-Nacharbeiten aus dem Betrieb von V12.8.17. Der Live-Regelalgorithmus, die MQTT-Kommandostruktur und das CSV-Schema bleiben unverändert.

## Änderungen

### Statusseite

- Die Karte `Netzleistung` zeigt als Hauptwert den aktuellen/frischen Roh-/Messwert der Netzleistung.
- Der geglättete AUTO-Regelwert bleibt als Diagnose sichtbar, wird aber im festen Nachtmodus nicht mehr als prominenter aktueller Statuswert dargestellt.
- Wenn die Netzmessung nicht gültig/aktuell ist, wird kein alter Zahlenwert als normale Netzleistung angezeigt.
- Der Nachtmodus-Infotext erklärt die V12.8.17-Semantik: `NIGHT_DISCHARGE_STOP_SOC_PERCENT` pausiert nur die feste Nacht-Basisentladung; AUTO bleibt für Lastspitzen aktiv.

### Analyse-Webseite

- `selection_profile()` berechnet bei Mehrdatei-Auswahl den angezeigten Zeitraum aus globalem `min(start_ts)` und `max(end_ts)` aller Dateien.
- Der Diagrammbereich enthält spezifischere Info-Texte für Betriebszustände und MQTT-Wirkungskategorien.
- Mobile Balkendarstellung wurde stabilisiert: Labels, Balken, Werte und Info-Links werden unter schmalen Viewports gestapelt.
- MQTT-Wirkungsbalken verwenden eine einheitliche absolute Balkenbasis innerhalb des Blocks; die Textwerte nennen zusätzlich Prozent und Basis.
- Datenqualitätswarnungen sind konkreter und nennen betroffene Felder, Anzahl, Prozentanteil und SAFE_STATE-Zeit.

## Nicht geändert

- Keine Änderung der AUTO-Regelstrategie.
- Keine Änderung an MQTT-Subscriptions oder MQTT-Kommandostruktur.
- CSV-Schema bleibt `ZEC-MEASUREMENT-V2`.
- Finale Excel-Lernsimulation bleibt unverändert in `tools/` enthalten.

## Tests

Ausgeführt auf dem final entpackten Paket:

```bash
python3 -m py_compile *.py tools/*.py
python3 -m unittest discover -s tests -v
```

Ergebnis: 98 Tests OK.
