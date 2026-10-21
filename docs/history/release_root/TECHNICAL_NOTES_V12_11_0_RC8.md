# Technical Notes V12.11.0-RC8

V12.11.0-RC8 ist ein Stabilitäts- und UI-Korrekturrelease auf Basis von V12.11.0-RC7.

## Ziel

RC8 korrigiert die unmittelbar nach RC7 beobachteten Punkte, ohne die Live-Regelstrategie zu verändern:

- Keine Änderung an AUTO-Strategie.
- Keine Änderung an Nachtmodus-Regelwirkung.
- Keine Änderung an Cross-Charge-Regelwirkung.
- Keine Änderung an Restüberschuss-Ernte / Harvest-Regellogik.
- Keine Änderung an Zendure-MQTT-Kommandos oder Topic-Struktur.

## Änderungen

### Statusseite / SOC-Tageskurve

- Die x-Achse der SOC-Tageskurve ist jetzt fest auf den lokalen Tag 00:00 bis 24:00 skaliert.
- Vorhandene SOC-Punkte werden an ihrer echten Tagesposition angezeigt.
- Fehlende Zeiträume bleiben als leerer Bereich bzw. Lücke sichtbar.
- Der Measurement-V4-Bootstrap der SOC-Tageskurve wird gecacht, damit Browser-Auto-Refresh nicht wiederholt große CSV-Dateien scannt.
- Neuer optionaler Parameter `SOC_DAY_GRAPH_BOOTSTRAP_CACHE_SECONDS`, Default 300 Sekunden.

### Analyse-Service-Link

- Der Analyse-Service-Link wird nicht mehr wegen eines zu kurzen Health-Check-Timeouts aus der Nav-Bar entfernt.
- Der Link nutzt clientseitig den aktuellen Browser-Hostnamen und den konfigurierten Analyse-Port.
- Wenn der lokale Health-Check nicht bestätigt werden kann, bleibt der Link sichtbar, aber mit Warnpunkt statt OK-Punkt.

### Statusseite sichtbarer Refurbish-Schritt

- Die Statusseite erhält oberhalb der Detailkarten eine kompakte Dashboard-Kartenreihe für Netzleistung, Betriebsmodus, Zendure, Netzleistungsquelle und Messdaten.
- Die bisherigen Detailkarten bleiben erhalten, damit keine Diagnoseinformation verloren geht.

### Netzleistungs-Plausibilitätsfilter

- Neuer Parameter `GRID_POWER_PLAUSIBILITY_MAX_ABS_W`, Default 30000 W.
- Netzleistungswerte oberhalb dieser absoluten Grenze werden verworfen.
- Verworfen wird vor Glättung und AUTO-Regelung, damit extreme SMA-/Shelly-Ausreißer nicht in den Regler-Eingang gelangen.
- Der letzte gültige Wert bleibt erhalten; bei weiter ausbleibenden gültigen Werten greift die vorhandene Stale-/Safe-State-Logik.

### Harvest-/Restüberschuss-Strategie

- Keine Logikänderung in RC8.
- Für einen folgenden Regelungsblock ist vorgemerkt: PRIMARY_CHARGE_WINDOW_HARVEST mit festen Monatsgruppen und konfigurierbaren Zeitfenstern:
  - Nov-Jan: konfigurierbare Zeit, Vorschlag 10:00-14:30
  - Feb/Mär/Okt: konfigurierbare Zeit, Vorschlag 09:30-15:30
  - Apr-Sep: konfigurierbare Zeit, Vorschlag 08:30-17:00
- Diese Strategie wird bewusst nicht in denselben Hotfix aufgenommen, weil sie eine echte Regellogikänderung wäre.

## Tests

Ergänzt wurden RC8-Tests für:

- SOC-Tagesachse 00:00-24:00.
- SOC-Bootstrap-Cache ohne erneuten CSV-Scan bei jedem Abruf.
- Analyse-Service-Link mit Browser-Host-Ziel statt `127.0.0.1`.
- Sichtbare Analyse-Service-Navigation auch bei nicht bestätigtem Health-Check.
- Netzleistungs-Plausibilitätsfilter.
- Keine Harvest-/Restüberschuss-Regellogikänderung.
