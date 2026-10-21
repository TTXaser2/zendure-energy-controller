# V12.11.2-RC2

Gezielter UI-Nacharbeitsrelease auf Basis V12.11.2-RC1.

## Änderungen
- redundanten Status-Seitenkopf entfernt; Systemstatus in Navbar integriert
- obere Statusseite vertikal verdichtet
- Info-Hinweise als begrenzte, viewport-sichere Popover statt unkontrollierter Browser-Tooltips
- Minigraph mit interaktiven Trefferpunkten und Wert-/Status-Hinweis
- Zendure-/Primärspeicher-Ringe nutzen Kartenhintergrund und werden im Snapshot-Refresh aktualisiert
- Primärspeicher-Livefelder um bestehende SMA-/Second-Battery-Feldnamen ergänzt
- Tagesgraph verwendet echte `{x, y}`-Punkte für Zendure und Primärspeicher
- doppelten Text „Messquelle aktuell“ entfernt

## Regelpfad
Keine Änderung an Regelalgorithmus, Command-Lifecycle, MQTT-Steuerung, Harvest, Cross-Charge oder NIGHT_DISCHARGE. Sämtliche Änderungen liegen in Web-Rendering, Snapshot-Abbildung und Graphdarstellung. Dadurch entstehen keine neuen Latches, Race-Conditions oder Prioritätsumkehrungen im Reglerzustandsautomaten.
