# Technical Notes V12.11.0-RC9

V12.11.0-RC9 ist ein UI-Refactor-Release auf Basis von V12.11.0-RC8.

## Ziel

RC9 trennt die bisherige Legacy-Weboberfläche von einer neuen modernen Standardoberfläche. Dadurch muss die neue UI nicht weiter additiv auf der alten Kartenmatrix aufbauen. Die alte Oberfläche bleibt als Diagnose- und Fallbackpfad erhalten.

## Neue / geänderte Routen

- `/` – neue moderne Statusseite.
- `/graph` – neue moderne Graph-/Verlaufsdiagnose.
- `/status_old` – Legacy-Statusseite mit der bisherigen Detailkartenstruktur.
- `/graph_old` – Legacy-Graphseite.

Die JSON-Route `/status` bleibt als Status-API unverändert erhalten.

## UI-Struktur

### Moderne Statusseite

- Kuratierte Hauptansicht mit fünf Hauptkarten:
  - Netzleistung
  - Betriebsmodus
  - Zendure
  - Netzleistungsquelle
  - Messdaten
- Kompakte Energieflussübersicht.
- Nachtmodus-Prognose bleibt sichtbar.
- SOC-Tageskurve bleibt mit fester 00:00–24:00-Achse erhalten.
- Diagnose-/Fallbackbereich verweist auf Legacy-Seiten.

### Moderne Graph-Seite

- Neu komponierter Graph-Container im Dark-Mode-Stil.
- Toolbar für Zeitraum, Auflösung und Auto-Refresh.
- Hauptgraph über `/graph-view-data`.
- KPI-Leiste aus demselben Graph-Datensatz.
- Ereignis-/Markerbereich.
- Aktive Signale-/Quellen-Tabelle.
- Link zum Legacy-Graph `/graph_old`.

## Expertenmenü

Die Navigation enthält ein kleines Expertenmenü mit Links auf:

- Alte Statusseite
- Alter Graph
- Moderne Diagnose

## Pi-/Browser-Last

- Die neue Statusseite verwendet keinen automatischen kompletten Seitenreload.
- Die neue Graph-Seite pausiert Auto-Refresh, wenn der Tab im Hintergrund ist (`document.visibilityState`).
- Teure CSV-/Measurement-Scans bleiben auf gecachte Endpunkte oder explizite Benutzeraktionen beschränkt.

## Nicht geändert

- Keine Änderung an AUTO.
- Keine Änderung am Nachtmodus.
- Keine Änderung an Cross-Charge.
- Keine Änderung an Restüberschuss-Ernte.
- Keine Änderung an Zendure-MQTT-Kommandos oder Topics.
- Keine Änderung am Measurement-V4-Schema.
- Keine Änderung an der finalen Excel-Lernsimulation.

## Tests

Ergänzt wurden RC9-Tests für:

- moderne Statusseite mit Legacy-Fallbacklinks,
- moderne Graph-Seite mit Legacy-Fallbacklink,
- Expertenmenü,
- registrierte Legacy-Routen.
