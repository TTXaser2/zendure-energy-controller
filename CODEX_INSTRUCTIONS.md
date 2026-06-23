# Codex-Anweisungen für Zendure Energy Controller

- Keine Änderung an produktiver config.json.
- Keine Logs, CSV-Messdaten, ZIPs oder produktiven Zugangsdaten committen.
- Keine Änderung am Live-Regelalgorithmus ohne ausdrückliche Freigabe.
- Keine Änderung an MQTT-Topic-Struktur oder Kommandosemantik, außer explizit beauftragt.
- Finale Excel-Datei in tools/ nicht ändern.
- Änderungen klein halten.
- Tests ergänzen, wenn Bugfix oder Verhalten geändert wird.
- Vor Abschluss ausführen:
  - python3 -m py_compile *.py tools/*.py
  - python3 -m unittest discover -s tests -v
- Am Ende Diff, geänderte Dateien, Tests und Risiken zusammenfassen.