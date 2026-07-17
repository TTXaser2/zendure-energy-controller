# Zendure Energy Controller V12.11.2-RC1

## Wichtige Änderungen in V12.11.2-RC1

V12.11.2-RC1 ist ein Statusseiten-/Diagnose-Release auf Basis von V12.11.1-RC3. Die bestehende Regelstrategie bleibt unverändert; der Fokus liegt auf einer neuen, snapshot-basierten Statusseite und auf einer robusteren COMMAND_RESYNC-/COMMAND_NOT_EFFECTIVE-Diagnose.

### Neue Statusseite

- Neues Top-Level-Layout mit fünf Hauptkarten: Netzleistung, Betriebsmodus, Zendure/Batterie, Primärspeicher/SMA-Batterie und Netzleistungsquelle.
- Zentrale Snapshot-Aktualisierung über `/status-view-data`, ohne vollständigen Seitenreload.
- Netzleistung, Betriebsmodus, Zendure, Primärspeicher und Datenquelle werden regelmäßig aktualisiert.
- Zendure-Karte zeigt Telemetrie-/Command-Warnungen, falls Sollwerte nicht wirksam werden.
- Primärspeicher-Karte zeigt im Standardmodus Harvest-/Cross-Charge-relevante Hinweise.
- Netzleistungsquelle zeigt nutzerverständlich Pakete/min, Mehrgeräte-Filterung und verworfene Messwerte.
- Dark-Mode-fähige CSS-Token-Grundlage; der SOC-Ring-Innenbereich verwendet den Kartenhintergrund.

### Speicher-SOC Tagesgraph

- Neuer Tagesgraph 00:00–24:00 mit Navigation für vorherigen Tag, heutigen Tag und nächsten Tag.
- Heute zeigt Messdaten bis jetzt und lässt den zukünftigen Tagesbereich leer.
- Bei einer Zendure-Headunit werden Zendure-SOC und Primärspeicher-SOC angezeigt.
- Graphdaten kommen aus SQLite/Cache; keine CSV-Liveparsing-Last auf der Statusseite.

### COMMAND_RESYNC und COMMAND_NOT_EFFECTIVE

- Kurze STALE-/PARTIAL_STALE-Phasen lösen nicht mehr automatisch häufige Resyncs aus.
- Resync bleibt bei belastbarer Unsicherheit möglich: längerer STALE-Zustand, Reconnect, harter MQTT-Verlust, unsicher gesendeter aktiver Sollwert oder bestätigter Command-Mismatch.
- Deduplizierung unterdrückt nur redundante Wiederholungen innerhalb des Cooldowns; sie blockiert keinen notwendigen Resync bei bestätigter Unsicherheit.
- COMMAND_NOT_EFFECTIVE wird nur bei persistenter, relevanter Soll-/Ist-Abweichung und frischer plausibler Telemetrie gesetzt.
- Recovery wird deterministisch erkannt; der Zustand wird zurückgesetzt, sobald Soll und Ist wieder plausibel übereinstimmen.
- Telemetrieunsicherheit wird als eigener Zustand bewertet und nicht als bestätigter Gerätefehler dargestellt.

## Installation

Siehe `README_INSTALLATION.md`.
