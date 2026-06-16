# Technical Notes V12.9.2

V12.9.2 ist ein Stabilitäts- und Messdaten-Nacharbeitsrelease auf Basis von V12.9.1. Die Live-Regelstrategie, MQTT-Subscriptions und MQTT-Kommandostruktur bleiben unverändert.

## Schwerpunkte

- Analyse-/Replay-Datenqualität erkennt Zendure-SOC nun primär über die V3-Felder `norm_zendure_soc_percent` und `raw_zendure_soc_percent` statt über alte Aliasfelder.
- Analyse-Preflight auf dem Raspberry Pi wurde nachjustiert: kleine V3-Dateien werden trotz knapper Desktop-RAM-Reserve zugelassen, solange `MemAvailable` nicht extrem niedrig ist. Der Worker-Schutz mit Timeout und Speicherlimit bleibt aktiv.
- Bool-Felder im V3-CSV werden künftig als `1`/`0` geschrieben; Analyse/Replay akzeptiert weiterhin ältere `true`/`false`-Werte.
- Messdaten-Logger schreibt gepuffert und führt kein hartes `fsync` pro Messzeile aus. Flush erfolgt periodisch nach Zeilenanzahl oder Zeit. Bei Stromausfall können letzte Messdaten fehlen; die Regelung bleibt davon unabhängig.
- Settings für Messdaten-Speicherziel erweitert: interne SD, externer Mountpoint/USB-Ziel oder benutzerdefinierter Pfad.
- Bei externem Speicherziel wird ein begrenzter und sichtbar markierter SD-Fallback unterstützt, wenn das primäre Ziel nicht verfügbar ist und Fallback erlaubt ist.
- Status-/Settings-Seite zeigen den aufgelösten Logzielpfad, erkannte externe Mountpoints und Fallback-Hinweise.

## Bewusst nicht enthalten

- Keine gzip-Kompression rotierter Logs, da das Ziel SD-Schreiblastreduktion ist und nachträgliche Kompression zusätzliche I/O erzeugen würde.
- Keine kryptischen Enum-/Reason-Kürzel.
- Keine Metadaten-Auslagerung.
- Keine nur-bei-Abweichung-Reason-Felder.
- Kein reduziertes Logging-Intervall.
- Keine Änderung der AUTO-Regelstrategie.

## Tests

Erwartete Prüfungen:

```bash
python3 -m py_compile *.py tools/*.py
python3 -m unittest discover -s tests -v
```
