# Technical Notes V12.9.3

## Zweck

V12.9.3 ist ein kleiner Nacharbeitsrelease zu V12.9.2. Der Fokus liegt auf der Messdaten-Speicherziel-/USB-Logik und der Konsistenz des SD-Fallback-Status. Die Live-Regelstrategie und die MQTT-Kommandostruktur bleiben unverändert.

## Änderungen

- Speicherziel `external_mount` verwendet jetzt die abgestimmte Variante A:
  - finaler Pfad = USB-/Mountpoint + `MEASUREMENT_LOG_DIR` + `MEASUREMENT_LOG_FILE`.
  - Beispiel: `/media/pi/4CD6-6466` + `ZEC/logs` + `zendure_measurements.csv` ergibt `/media/pi/4CD6-6466/ZEC/logs/zendure_measurements.csv`.
- Bei leerem `MEASUREMENT_LOG_MOUNTPOINT` wird ein erkannter schreibbarer externer Mountpoint automatisch akzeptiert.
- Die Settings-Validierung warnt nicht mehr fälschlich, wenn ein automatisch erkannter externer Mountpoint schreibbar ist.
- Die Messdaten-Infobox zeigt Speicherziel, USB-/Mountpoint, Unterordner und aktive Datei transparenter getrennt an.
- Die Beschreibung von `MEASUREMENT_LOG_MIN_FREE_DISK_MB` stellt klar, dass der Wert für das aktuell aktive Messdatenziel gilt: interne SD, externer Mountpoint oder SD-Fallback.
- Die Fallback-Statuslogik im CSV-Logger wurde atomarisiert:
  - Zielauflösung, tatsächliches Schreibziel, CSV-Zeile und zurückgemeldeter Status verwenden dieselbe Entscheidung pro Zyklus.
  - Bei erfolgreichem USB-Schreiben wird keine `active_fallback_sd`-Markierung in die USB-Zeile geschrieben.
  - Wenn auf SD-Fallback geschrieben wird, trägt diese Zeile selbst `active_fallback_sd`.

## Tests

Neue Tests in `tests/test_v12_9_3_usb_logging.py` prüfen:

- Auto-USB-Mountpoint + konfigurierter Unterordner nach Variante A.
- Settings-Validierung akzeptiert leeres Mountpoint-Feld bei automatisch erkanntem schreibbarem externem Ziel.
- Fallback-Zeilen enthalten konsistent `active_fallback_sd`.
- USB-Zeilen überschreiben alte/stale Fallback-Statuswerte aus dem Controller-State und erzeugen keine Fallback-Datei.

## Nicht geändert

- Keine Änderung an AUTO-Regelstrategie.
- Keine Änderung an MQTT-Kommandostruktur.
- Keine Änderung am V3-Grundschema.
- Keine gzip-Kompression.
- Keine V2-Migration oder V2-spezifische Logbereinigung.
