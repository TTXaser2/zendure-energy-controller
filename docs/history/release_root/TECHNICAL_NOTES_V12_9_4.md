# Technical Notes V12.9.4

## Zweck

V12.9.4 ist ein kleiner Stabilitätsrelease zu V12.9.3. Der Fokus liegt auf Messdaten-Speicherziel, USB-/SD-Fallback-Diagnose, kompakter Statusseitenanzeige und isolierten Tests. Die Live-Regelstrategie, der Nachtmodus, die MQTT-Kommandostruktur und das `ZEC-MEASUREMENT-V3`-Grundschema bleiben unverändert.

## Architekturentscheidung

USB-/SD-Fallback-Details sind Betriebsdiagnose des Loggers, nicht fachliche Regler-Messdaten. Deshalb werden keine neuen USB-Detailspalten in das Measurement-CSV aufgenommen. Die bestehende V3-Datensammlung bleibt konsistent; `measurement_log_status` bleibt kurzfristig bestehen, wird aber nicht weiter ausgebaut.

Die detaillierte Ursache eines Fallback-Ereignisses wird in `zendure_runtime.log` geschrieben, wenn Datei-Logging aktiviert ist. Die Statusseite zeigt kompakt Zähler, letzten Zeitpunkt und letzten Grund.

## Änderungen

- Messdaten-Statusbox auf der Statusseite kompakter und operativ ausgerichtet.
- Prominente Schema-Zeile aus der Messdaten-Statusbox entfernt. Das Schema bleibt unverändert `ZEC-MEASUREMENT-V3`.
- `resolve_log_target()` ergänzt eine interne Zielauflösung mit Runtime-Diagnose:
  - primärer Pfad, Mountpoint, exists, is_mount, writable, free_mb, failure_reason, exception, aktives Ziel.
- Bei SD-Fallback-Ereignissen erzeugt der Controller eine Runtime-Log-Zeile mit konkreten Primary-/Fallback-Details.
- Fallback-Zähler zählt Ereignisse seit Controller-Start, nicht Messzyklen.
- Statusseite zeigt aktives Ziel, Pfad, Fallback-Zähler, letzten Fallback-Zeitpunkt und letzten Fallback-Grund.
- Der V12.9.3-Test für externen Mountpoint/Fallback ist gegen reale Mountpoints isoliert.
- Default-Dateiname für das Runtime-Log ist für neue Konfigurationen konsistent `zendure_runtime.log`.

## Tests

Neue Tests in `tests/test_v12_9_4_logging_diagnostics.py` prüfen:

- USB-/Fallback-Detaildiagnose wird nicht als neue Measurement-CSV-Spalten aufgenommen.
- Fallback-Diagnosedaten stehen für Runtime-Log und Statusseite bereit.
- Fallback-Ereignisse werden nur einmal gezählt, solange das Fehlerbild gleich bleibt.
- Runtime-Log-Formatter enthält Primary-Fehlerdetails.
- Statusseitenquelltext enthält keine prominente Schema-Zeile in der Messdatenkarte mehr.

Zusätzlich wurde `tests/test_v12_9_2_logging_storage.py` so isoliert, dass reale USB-/Mountpoints auf dem Zielsystem den Fallback-Test nicht beeinflussen.

## Nicht geändert

- Keine Änderung an AUTO-Regelstrategie.
- Keine Änderung an Nachtmodus-Logik.
- Keine Änderung an MQTT-Subscriptions oder MQTT-Kommandostruktur.
- Keine neuen V3-Measurement-CSV-Spalten.
- Keine Temperatur-Logging-Erweiterung.
- Keine Schema-Kürzung von `ZEC-MEASUREMENT-V3`.
- Keine Simulator-Integration.
- Keine gzip-Kompression.
- Finale Excel-Lernsimulation bleibt unverändert in `tools/` enthalten.
