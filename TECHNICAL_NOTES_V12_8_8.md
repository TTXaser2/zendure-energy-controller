# Technical Notes V12.8.8

V12.8.8 ist ein kleiner Hotfix auf Basis von V12.8.7.

## Anlass

In V12.8.7 wurde die Analyse-Weboberfläche zwar serverseitig korrekt erweitert, die JavaScript-Initialisierung scheiterte jedoch im Browser durch einen Syntaxfehler in einem Confirm-Text mit nicht korrekt escaped Newline-Zeichen. Dadurch wurde der Analyse-Button nicht per JavaScript angebunden; es wirkte so, als passiere beim Klick nichts.

## Änderung

- Newline-Zeichen im JavaScript-Confirm-Text werden korrekt als `\\n` ausgegeben.
- Der Analyse-Button, Status-Polling und die dynamische Auswahlprüfung initialisieren wieder korrekt.
- Keine Änderung am Live-Regelalgorithmus.

## Tests

- `python3 -m py_compile *.py tools/*.py`
- `python3 -m unittest discover -s tests -v`
- zusätzlicher Regressionstest gegen unescaped Newline im JavaScript-Confirm-Text
