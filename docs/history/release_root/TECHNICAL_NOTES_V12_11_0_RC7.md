# Technical Notes V12.11.0-RC7

V12.11.0-RC7 ist ein UI-/Diagnose-/Export-Release auf Basis von V12.11.0-RC6.

## Ziel

Der Release modernisiert Status- und Graph-Seite, ergänzt eine leichte SOC-Tageskurve und ersetzt den direkten Messdaten-CSV-Link durch eine Exportseite mit Zeitraumsauswahl. Die Live-Regelung bleibt unverändert.

## Enthalten

- Dark-Mode als neuer Default für die Weboberfläche.
- Kompakte einzeilige Nav-Bar:
  - Status
  - Graph
  - Settings
  - Analyse-Service, sofern erreichbar
  - MQTT Diagnose
  - Messdaten-CSV
  - Handbuch
- Entfernt aus der Nav-Bar:
  - direkter Download Graph CSV
  - langer Text Download Handbuch
- Statusseite:
  - alte Kurzverlauf-Sektion entfernt
  - neue Zendure-SOC-Tageskurve für den aktuellen lokalen Tag
  - SOC-Tageskurve nutzt RAM-Livewert und best-effort Bootstrap aus Measurement-V4-CSV-Dateien
  - Nachtmodus-Prognose bleibt sichtbar
  - Netzleistungsquelle ist dynamisch formuliert und nicht mehr starr SMA-zentriert
- Graph-Seite:
  - neue Dark-Mode-Verlaufsdiagnose
  - Hauptgraph mit Kernlinien
  - Tooltip mit Regelkontext
  - KPI-Leiste
  - Ereignis-/Markerübersicht
  - aktive Signale/Quellen
  - Graph-Verlauf CSV bleibt auf der Graph-Seite verfügbar
- Messdaten-CSV:
  - neue Exportseite `/measurements`
  - verfügbare Messdaten-Zeitspanne wird ermittelt
  - CSV-Export mit Start-/Endzeit-Auswahl
  - klare Hinweise, wenn Logging deaktiviert ist oder keine Daten vorhanden sind
- Neue JSON-Endpunkte:
  - `/graph-view-data`
  - `/soc-day-data`
  - `/measurements/availability`
  - `/measurements/export.csv`
- Default-/Example-Config anonymisiert:
  - keine produktive Zendure Device-ID
  - keine produktive SMA-Seriennummer
  - keine produktive SMA-SUSy-ID als Beispiel
- Zusätzliche RC7-Tests für Nav-Bar, Messdaten-Verfügbarkeit, Graphdaten-Fallback, SOC-Tageskurve und anonymisierte Example-Config.

## Bewusst nicht geändert

- Keine Änderung an AUTO-Regelstrategie.
- Keine Änderung an Nachtmodus-Regelwirkung.
- Keine Änderung an Cross-Charge-Regelwirkung.
- Keine Änderung an Restüberschuss-Ernte.
- Keine Änderung an Zendure-MQTT-Kommandostruktur.
- Keine Änderung an Zendure-MQTT-Topicstruktur.
- Keine neue Datenbank und keine neue permanente Datenhaltung für die SOC-Tageskurve.
- Keine neue PV-/Hausverbrauch-Datenquelle; Linien werden nur angezeigt, wenn valide Daten vorhanden sind.
- Keine Änderung an finaler Excel-Lernsimulation.

## Hinweise

Die neue SOC-Tageskurve ist diagnostisch. Wenn der Bootstrap aus Measurement-CSV fehlschlägt oder keine Dateien vorhanden sind, läuft der Controller normal weiter und die Kurve startet ab dem aktuellen Livewert.

Der Messdaten-Export basiert auf vorhandenen CSV-Logs. Wenn Logging deaktiviert ist, aber historische Daten vorhanden sind, können diese weiterhin exportiert werden. Wenn weder Logging noch historische Daten vorhanden sind, weist die Exportseite auf die Aktivierung des Messdaten-Loggings in den Settings hin.
