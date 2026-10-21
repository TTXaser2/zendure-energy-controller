# Technical Notes V12.11.0-RC14

## Ziel

RC14 ist ein UI-Polish- und Diagnosekomfort-Release auf Basis von RC13. Der Schwerpunkt liegt auf der modernen Statusseite und auf schnellerer Support-Arbeit am Raspberry Pi.

## UI-Polish

- Konsistentes lokales SVG-Iconset in `web_ui.py` über `_ui_icon(...)`.
- Keine externen Font-/Icon-Dateien und kein externer Icon-CDN-Zugriff.
- Topbar, Hauptkarten und Footerkarten nutzen einheitliche Inline-SVGs statt gemischter Unicode-/Emoji-Symbole.
- Die Netzleistungs-Mini-Historie ist nun eine skalierte Mini-Chart-Komponente:
  - Achsen und dezente Gitterlinien,
  - Min-/Max-Skalenhinweis,
  - aktueller Wert,
  - Nullreferenz bei Vorzeichenwechsel.
- Bei fehlender echter Historie bleibt der Text-Fallback erhalten; es wird weiterhin keine Fake-Kurve erzeugt.
- Nachtmoduskontext in der Betriebsmodus-Karte ist neutral dargestellt. Normale Kontextinformation nutzt keine gelbe Warnbox mehr.

## Support-/Crash-Diagnose

- Neues Tool `tools/collect_zec_crash_package.sh`.
- Ziel: schnelleres Sammeln von Kernel-, Storage-, Service- und Vorboot-Informationen bei Pi-Hängern/Reboots.
- Ausgabe nach `/home/pi/Downloads/zec_crash_<timestamp>.zip` und zusätzlich `zec_crash_latest.zip`.
- `tools/create_desktop_shortcuts.sh` erstellt nun drei Desktop-Aktionen:
  - ZEC Trace sammeln,
  - ZEC Diagnosepaket erstellen,
  - ZEC Crashpaket erstellen.

## Bewusst nicht geändert

- Keine Änderung an AUTO.
- Keine Änderung an Nachtmodus-Regelwirkung.
- Keine Änderung an Cross-Charge.
- Keine Änderung an Restüberschuss-Ernte.
- Keine Änderung an Zendure-MQTT-Topics oder Kommandos.
- Keine Änderung am Measurement-V4-Schema.
- Keine Änderung an der Excel-Lernsimulation.
