# Technical Notes V12.10.0-RC3

V12.10.0-RC3 ist eine Stabilitäts-Nacharbeit zu RC2. V4-Logging bleibt aktiv, V3 bleibt als Legacy-/Rollback-Pfad verfügbar. Die AUTO-Regelstrategie, Nachtmodus-Logik, Cross-Charge-Strategie, MQTT-Subscriptions und MQTT-Kommandostruktur bleiben unverändert.

## Schwerpunkt

RC3 schützt die Reglerreaktionszeit und verbessert die V4-Dateikonsistenz nach den Live-Befunden aus RC2.

## Änderungen

- `MEASUREMENT_LOG_MODE=off` ist für V4 nun ein harter Logging-Bypass: keine Pfadauflösung, keine Disk-Statistik, kein Manifest, kein Snapshot und keine Retention-Berechnung im Zyklus.
- V4-Manifest-Updates werden gepuffert/debounced statt pro Messzyklus geschrieben. Defaults: alle 25 Zeilen oder spätestens nach 30 Sekunden; beim Schließen wird final aktualisiert.
- Bei bereits vorhandener `zendure_measurements_v4.csv` startet eine neue Controller-Session in einer neuen session-spezifischen Datei, z. B. `zendure_measurements_v4_YYYYMMDDTHHMMSSZ.csv`. Dadurch werden RC-/Service-Start-Segmente nicht mehr in dieselbe physische Datei gemischt.
- Bestehende Config-Snapshots werden nachmigriert: fehlt `CROSS_CHARGE_SIGNIFICANT_W`, wird der Wert aus `SMA_DISCHARGE_BLOCK_W` ergänzt.
- Die lokale Zendure-API bekommt einen wirksamen Regelzyklus-Timeoutdeckel (`ZENDURE_LOCAL_API_CONTROL_TIMEOUT_CAP_SECONDS`, Default 1.5 s), damit optionale Read-only-Telemetrie die Live-Regelung nicht mehrere Sekunden blockieren kann.
- RC3 ergänzt Cycle-Timing-Diagnose: Gesamtzeit ohne Sleep, langsamster gemessener Teil und JSON-Details im Status/Snapshot. Langsame Zyklen ab `SLOW_CYCLE_WARN_MS` werden im Runtime-Log markiert.

## Tests

`python -m unittest discover -q` → 151 Tests OK.
