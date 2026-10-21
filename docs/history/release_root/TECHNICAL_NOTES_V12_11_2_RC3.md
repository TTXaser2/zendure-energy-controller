# V12.11.2-RC3 – Statusseite V2

## Ziel

Echter Neuaufbau der Statusseite nach der vollständig abgestimmten UI-Spezifikation und dem freigegebenen Mockup. Die historische Statusseite ist nur noch Legacy-/Experten-Fallback und keine Markup- oder Layoutbasis mehr.

## Implementierung

- `status_page_v2.py`: eigenständiges semantisches Markup, fünf Hauptkarten, Tagesgraph und funktionaler unterer Bereich.
- `static/status_v2.css`: Design-Tokens, Light-/Dark-Mode-Fähigkeit, responsive Mockup-Proportionen, Ringinnenfläche gleich Kartenhintergrund.
- `static/status_v2.js`: zentraler Refresh-Manager, Canvas-Minigraph und Canvas-SOC-Tagesgraph, getrennte Info-Popover und Chart-Tooltips, Tagesnavigation.
- `/status-view-data`: gecachter kompakter View-Snapshot.
- `/grid-mini-data`: leichter Minigraph-Endpunkt.
- `/storage-soc-day-data?date=YYYY-MM-DD`: Tagesdaten 00:00–24:00 aus SQLite/Cache.

## Fachliche Anzeigen

- Betriebsmodus mit Nacht-/Fixed-Prognose, Zielwert, Grund und letzter Änderung.
- Eine Headunit: Ring links, Details rechts. Zwei Headunits: zwei Ringe, System-SOC und Unit-Aufschlüsselung.
- Primärspeicher-Harmonisierung mit Harvest- und Cross-Charge-Aussage im Standardmodus.
- Netzleistungsquelle mit Paketen/min, korrekt gefilterten SMA-Geräten sowie verworfenen Messwerten.
- Zendure-MQTT-NO_LIVE/RETAINED_ONLY zeigt den operativen Hinweis, MQTT in der Zendure-App erneut zu speichern/aktivieren.

## Latch-, Race- und Prioritätssicherheit

Die UI liest nur atomare Snapshots und gecachte Daten. Sie schreibt keine Reglerzustände und führt keine synchronen Zendure-, MQTT-, Netzwerk-, Datei- oder Datenbankzugriffe im Regelpfad aus. Die einzigen zusätzlichen Controller-State-Felder sind begrenzte Diagnose-Skalare für verworfene Netzwerte; sie werden im bereits vorhandenen Plausibilitäts-Exception-Pfad unter dem bestehenden `RLock` aktualisiert. Es gibt keine neue Zustandskante der Regelmaschine und damit keinen neuen Latch.

Die bereits enthaltene COMMAND_RESYNC-Deduplizierung unterdrückt nur identische, redundante Wiederholungen ohne belastbare Unsicherheit. Reconnect, langer STALE-Zustand, Geräte-/Sessionverlust, bestätigter Mismatch und nicht beobachtete Gerätewirkung öffnen ausdrücklich erneut eine Sendekante. Dadurch kann kein „bereits gesendet“-Latch entstehen.

## Tests

- Legacy-No-Regression-Suite aktualisiert auf die eigenständige Status-V2-Architektur.
- Neue Tests für Topbar, fünf Karten, 1-/2-Headunit-Layout, Harvest-Harmonisierung, Pakete/min, getrennte Tooltip-Systeme, 24h-Tagesnavigation, Dark-Mode-Tokens und MQTT-Recovery-Hinweis.
- Python-Kompilation, JavaScript-Syntaxprüfung, komplette Unit-Test-Suite und Browser-/Hover-Validierung.
