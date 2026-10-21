# Technical Notes – V12.11.0-RC11

## Zweck

V12.11.0-RC11 ist ein Mock-up-Fidelity-Release auf Basis von V12.11.0-RC10.

Der Release setzt die moderne Statusseite deutlich näher am hellen Status-Mock-up um, wenn `UI_DARK_MODE=false` ist. Die Graph-Seite bleibt am dunklen Graph-Mock-up orientiert.

## Enthalten

- Light-Theme für die moderne Statusseite bei `UI_DARK_MODE=false`.
- Statusseite stärker nach Mock-up komponiert:
  - fünf große Top-Karten,
  - Netzleistung mit Sparkline,
  - Betriebsmoduskarte,
  - Zendure-Batteriekarte mit SOC-Ring,
  - Netzleistungsquellen-Karte,
  - Messdaten-/Logging-Karte,
  - SOC-Tagesgraph im hellen Mock-up-Stil,
  - Footer-Systemkarten.
- Graph-Seite bleibt dark und nutzt weiter das moderne RC10-Graphlayout.
- Legacy-Fallbacks bleiben erreichbar: `/status_old`, `/graph_old`.

## Nicht enthalten

Keine Änderung an AUTO, Nachtmodus, Cross-Charge, Restüberschuss-Ernte, MQTT-Kommandos, MQTT-Topics, Measurement-V4-Schema oder Excel-Lernsimulation.

Die geplante `PRIMARY_CHARGE_WINDOW_HARVEST`-Strategie bleibt ein separater Regelungsblock.
