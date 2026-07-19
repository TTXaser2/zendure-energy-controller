# Zendure Energy Controller V12.11.2-RC3

## Statusseite V2 – echter Neuaufbau

V12.11.2-RC3 setzt die über mehrere Tage abgestimmte Statusseiten-Spezifikation als eigenständige Oberfläche um. Die historische Statusseite bleibt ausschließlich als Experten-/Legacy-Fallback erreichbar; ihr Markup und ihre Kartenstruktur werden von der neuen Statusseite nicht wiederverwendet.

### Hauptoberfläche

- Kompakte, am freigegebenen Mockup orientierte Topbar mit dienstabhängiger Navigation und globaler Systemstatus-Pill.
- Fünf Hauptkarten: Netzleistung, Betriebsmodus, Zendure/Batterie, Primärspeicher/SMA-Batterie und Netzleistungsquelle.
- Netzleistungs-Minigraph als eigener Canvas-Chart mit unmittelbarem Hover wie beim SOC-Graphen; Info-Popover und Chart-Tooltip sind technisch getrennt.
- Betriebsmodus mit Klartext, Zielwert, Grund, letzter Änderung sowie Nacht-/Fixed-Prognosen.
- Zendure-Karte mit einem breiten Ring-/Detail-Layout für eine Headunit und zwei separaten Ringen plus Unit-Aufschlüsselung für zwei Headunits.
- Primärspeicher-Karte mit SOC, Istleistung und im Standardmodus sichtbarer Harvest-/Cross-Charge-Harmonisierung.
- Netzleistungsquelle mit Paketen/min, Mehrgeräte-Filterstatus sowie verworfenen Messwerten mit Zeitpunkt und Grund.

### Speicher-SOC Tagesgraph

- Voller Kalendertag 00:00–24:00.
- Navigation vorheriger Tag / Heute / nächster Tag.
- Zendure- und Primärspeicher-SOC, bei zwei Headunits separate Unit-Serien.
- Direkter Canvas-Hover mit SOC, Leistungen, Modus und Grund.
- SQLite-/Cache-Daten; vergangene Tage stark cachebar, aktueller Tag im 60-s-Rhythmus.

### Refresh und Lastschutz

- Zentrale Snapshot-Single-Source-of-Truth über `/status-view-data`.
- Keine vollständigen Seitenreloads und keine unabhängigen Poller je Karte.
- Polling ohne überlappende Requests, mit AbortController und Drosselung in Hintergrundtabs.
- Mini-Graph und Tagesgraph nutzen eigene leichte, gecachte Endpunkte.
- Fehlerhafte UI-Abfragen erhalten bestehende Werte und setzen sie niemals auf 0.

### COMMAND_RESYNC / COMMAND_NOT_EFFECTIVE

Die in V12.11.2-RC1 eingeführte latch-sichere Resync-Deduplizierung und der bestätigungsbasierte COMMAND_NOT_EFFECTIVE-Zustandsautomat bleiben enthalten. Kurze Freshness-Störungen lösen keinen unnötigen Resync aus; bei Reconnect, langem STALE, Command-Mismatch oder verlorenem Command-Zustand bleibt ein identischer Sollwert erneut sendbar.

## Installation

Siehe `README_INSTALLATION.md`.
