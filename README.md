# Zendure Energy Controller V12.11.2-RC8

## Aktueller Release

V12.11.2-RC8 schließt den nach der RC7-Produktivsichtung bestätigten UI-/Diagnose-Backlog ab.

Wesentliche Änderungen:

- quantisierungsbewusste SOC-Anzeigekurve statt kaum wirksamer Plateau-Bézier-Glättung,
- sichere Auflösung einer veralteten MQTT-Unsicherheitswarnung bei bestätigtem neutralem Soll-/Istzustand,
- verständlicher Zykluskontext mit Start-zu-Start-Abstand und aktivem Arbeitsanteil,
- gestapelter Timing-Verteilungsbalken mit identischer Farblegende im Linienbaum,
- Slow-Cycle-Bewertung ausschließlich gegen `SLOW_CYCLE_WARN_MS`,
- robuster Installations-Ready-Check mit Retry, JSON-Prüfung und eindeutiger Fehlerausgabe,
- FastAPI-Lifespan statt veralteter `on_event`-Handler,
- geschlossener Dateihandle im Operations-Dashboard-Test.

Ausführliche Informationen:

```text
TECHNICAL_NOTES_V12_11_2_RC8.md
RELEASE_INFO_V12_11_2_RC8.md
```

## Architektur und Regelungsschutz

RC8 verändert keine fachliche Energie-Regelstrategie von AUTO, NIGHT_DISCHARGE, FIXED, Harvest, Cross-Charge oder Safe-State.

Die Korrektur in `controller_logic.py` betrifft ausschließlich ein diagnostisches Warn-Latch. Es wird nur dann aufgelöst, wenn der aktuelle Sollwert neutral ist und frische Zendure-Live-Telemetrie eine neutrale Gerätewirkung bestätigt. Die Korrektur sendet kein MQTT-Kommando und verändert keine Resync-Berechtigung.

SOC-Rekonstruktion, Timing-Verteilungsbalken und Slow-Cycle-Darstellung sind reine UI-/Diagnosefunktionen. Rohmesswerte, Tooltipwerte, Schwellen, Datenbank und Messschema bleiben unverändert.

## Installation

Siehe `README_INSTALLATION.md`.
