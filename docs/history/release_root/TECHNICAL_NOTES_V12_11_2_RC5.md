# Zendure Energy Controller V12.11.2-RC5

## Zweck

RC5 setzt die gemeinsam spezifizierte dritte Ebene der Statusseite als Operations-Dashboard um und behebt zugleich den RC4-Datumswähler.

## Änderungen

- Vier feste Karten: **Messdaten / Logging**, **Systemressourcen**, **Controller & Schnittstellen**, **Betriebsereignisse**.
- Linux-/Raspberry-Pi-Ressourcen aus gecachten `/proc`-/`/sys`-Quellen; `vcgencmd` mit Timeout und Cache.
- Hochauflösende direkte Messung des zuletzt abgeschlossenen aktiven Controllerdurchlaufs über `perf_counter_ns()`.
- Timing-Aufschlüsselung für Hauptteil, Logging, Wirkungsprüfung und langsamsten Abschnitt.
- Eindeutige Bezeichnung **Zendure-Kommandoabgleich** einschließlich AC-Modus und Lade-/Entladelimits.
- Persistentes, begrenztes Betriebsjournal in `zec_operational_events.sqlite3`; Beobachtung und SQLite-Schreiben ausschließlich in separatem Web-/Diagnosethread.
- Ereignisansicht: offene Ereignisse zuerst, danach heute und gestern, innerhalb einer begrenzten scrollbaren Karte.
- Der gesamte sichtbare Datumsbereich öffnet über `showPicker()` den nativen Kalender; Focus/Click-Fallback bleibt vorhanden.

## Regler- und Sicherheitsabgrenzung

- Keine Änderung an AUTO, NIGHT, FIXED, Harvest, Cross-Charge oder Safe-State-Entscheidungen.
- Keine zusätzlichen Netzwerk-, Datei- oder SQLite-Zugriffe im Regelpfad.
- Das Ereignisjournal beobachtet Zustände nur und darf weder MQTT-Sendungen deduplizieren noch einen Kommandoabgleich verhindern.
- Keine neuen Steuer-Latches, keine Prioritätsumkehr und keine zweite Kommandoquelle.
- Die einzige Änderung in `controller_logic.py` betrifft die monotone Timing-Instrumentierung; die fachlichen Regelpfade bleiben unverändert.

## Tests

- Python-Kompilierung aller Haupt- und Toolmodule.
- JavaScript-Syntaxprüfung.
- 305 Unit-Tests.
- Bitidentische finale Excel-Lernsimulation im Ordner `tools/`.
