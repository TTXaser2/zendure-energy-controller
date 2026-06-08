# Technical Notes V12.8.7

V12.8.7 ist ein fokussierter Hotfix für die Analyse-/Replay-Weboberfläche.

## Änderungen

- Neuer Endpoint `/selection-profile` zur dynamischen Prüfung der aktuell ausgewählten CSV-Dateien.
- Die grüne Auswahl-/Risikobox wird bei Änderungen der Mehrfachauswahl clientseitig aktualisiert.
- Der Analyse-Startbutton wird zusätzlich per `addEventListener` gebunden, damit die Bedienung robuster ist.
- Status-, Fehler- und Abschlussmeldungen werden in der UI deutlicher dargestellt.
- Dark-Mode-CSS für `.statusline`, `.statusline.error` und `.statusline.done` ergänzt.
- Keine Änderung an Live-Regelalgorithmus, MQTT-Kommandopfad oder Controller-Housekeeping.

## Testfokus

- Syntaxcheck aller Python-Dateien.
- Bestehende Unit-Tests.
- Manuelle Endpoint-Plausibilisierung über `/selection-profile`, `/start-analysis` und `/analysis-status`.
