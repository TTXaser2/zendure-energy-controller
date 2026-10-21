# Technical Notes V12.11.0-RC10

## Ziel

RC10 ist ein Modern-UI-Pixel-Pass auf Basis von RC9. Ziel ist maximale Annäherung an die abgestimmten Mock-ups für Status- und Graph-Seite.

## Enthalten

- Neue moderne Header-/Nav-Struktur mit ZENDURE-Branding.
- Moderne Statusseite im dunklen Dashboard-Stil, unabhängig vom bisherigen UI_DARK_MODE-Schalter.
- Kuratierte Hauptkarten: Netzleistung, Betriebsmodus, Zendure, Netzleistungsquelle, Messdaten.
- Neue Energiefluss-Sektion mit zentralem Modus-Orb.
- SOC-Tageskurve bleibt 00:00-24:00 mit Tooltip-Kontext.
- Graph-Seite mit Mock-up-näherer Toolbar, großem Chart-Panel, KPI-Strip, Analyse-Karten und Signal-Tabelle.
- Legacy-Fallback bleibt über Expertenmenü erreichbar: /status_old und /graph_old.

## Nicht enthalten

- Keine Änderung an AUTO.
- Keine Änderung am Nachtmodus.
- Keine Änderung an Cross-Charge.
- Keine Änderung an Restüberschuss-Ernte.
- Keine Änderung an MQTT-Kommandos oder Topics.
- Keine Änderung am Measurement-V4-Schema.

## Tests

- py_compile
- unittest discover
- bash -n tools/create_zec_analysis_package.sh
