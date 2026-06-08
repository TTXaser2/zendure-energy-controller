# Technical Notes V12.8.10

## Schwerpunkt

Kleiner Hotfix für die Analyse-/Replay-Weboberfläche. Der Live-Regelalgorithmus wurde nicht geändert.

## Änderungen

- Diagramm-Info-Aufklapper werden im Balkendiagramm nicht mehr innerhalb der Label-Spalte gerendert, sondern als eigenes Grid-Element über die gesamte Breite des Diagramm-Elements. Dadurch bleiben Label/Balken/Wert stabil und die Erklärungstexte sind besser lesbar.
- Bei Änderung der CSV-Auswahl wird der Startbutton sofort gesperrt.
- Während die Auswahlprüfung läuft, zeigt der Button `Aktualisiere Dateiauswahl…`.
- Eine Analyse kann erst gestartet werden, wenn das Auswahlprofil geladen, gültig und nicht abgelehnt ist.
- Schnelle Auswahlwechsel werden durch eine Sequenznummer abgesichert; veraltete `/selection-profile`-Antworten werden ignoriert.

## Tests

- `python3 -m py_compile *.py tools/*.py`
- `python3 -m unittest discover -s tests -v`
