# Technical Notes V12.11.0-RC13

RC13 ist ein Support-/Debugging-Workflow-Release auf Basis von RC12.

## Ziel

Die wiederkehrenden manuellen Debugging-Schritte werden in wiederverwendbare Tools verschoben. Der Nutzer soll bei Traceback-, Service- oder Diagnosefällen möglichst nur noch ein Script starten und die erzeugte Datei bereitstellen müssen.

## Enthalten

- Neues Tool `tools/collect_zec_trace.sh`:
  - sammelt Service-Status, Controller-/Replay-Journal, Runtime-Log, Version, Pi-/Systemdaten, Mount-/Disk-Status und HTTP-Ready-/Statusauszüge in eine Textdatei.
  - Standardausgabe nach `/home/pi/Downloads/zec_trace_<timestamp>.txt`.
  - Zusätzlich wird `zec_trace_latest.txt` aktualisiert.
  - Standardmäßig werden sensitive JSON-Felder wie Token, User, Password und Serial redigiert.
- Neues Tool `tools/run_zec_analysis_package_interactive.sh`:
  - startet das bestehende Diagnosepaket-Script in einer terminalfreundlichen Variante und hält das Fenster offen.
- Neues Tool `tools/create_desktop_shortcuts.sh`:
  - erstellt Desktop-Verknüpfungen für „ZEC Trace sammeln“ und „ZEC Diagnosepaket erstellen“.
- Update-Script bleibt kompatibel und setzt Shell-Tools im Ziel weiterhin ausführbar.
- README ergänzt um Kurzbeschreibung und Aufrufe.

## Nicht enthalten

- Keine Änderung an AUTO, Nachtmodus-Regelwirkung, Cross-Charge oder Restüberschuss-Ernte.
- Keine Änderung an Zendure-MQTT-Kommandos oder Topicstruktur.
- Keine Änderung am Measurement-V4-Schema.
- Keine GitHub-Actions-/Release-Publishing-Umstellung; diese folgt als separater Strukturwechsel nach RC13.
