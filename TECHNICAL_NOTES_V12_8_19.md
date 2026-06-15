# Technical Notes V12.8.19

V12.8.19 ist ein bereinigtes UI-/Analyse-Nacharbeitsrelease auf Basis von V12.8.17. V12.8.18 wurde nicht als fachliche Basis weitergeführt, weil die Statusseiten-Netzleistung und die MQTT-Wirkungsbalken nicht zufriedenstellend umgesetzt waren.

## Statusseite: Netzleistung als echter Messwert

Die Karte `Netzleistung` zeigt den aktuellen Shelly-/UniMeter-Rohmesswert als Hauptwert, sofern die Messung frisch ist. Der geglättete AUTO-Regelwert bleibt eine Diagnosegröße und wird in Modi ohne aktive AUTO-Regelung als `n.a. / nicht aktiv` markiert.

Wichtig: Feste Nachtentladung, STOP/HOLD und feste Lade-/Entlademodi werden dadurch nicht von Grid-Daten abhängig. Grid wird in diesen Modi nur best-effort für Statusseite, CSV und Diagnose aktualisiert. Fehlerhafte oder fehlende Grid-Daten dürfen die feste Nachtentladung nicht wieder blockieren.

## Nachtmodus-Infotext

Der Hilfetext zum Nachtmodus beschreibt nun die Semantik aus V12.8.17: `NIGHT_DISCHARGE_STOP_SOC_PERCENT` pausiert nur die feste Nacht-Basisentladung. Die AUTO-Regelung bleibt für Lastspitzen aktiv und darf bis zum globalen `MIN_SOC_PERCENT` entladen.

## Analyse-Webseite

Die Auswahl-/Risikobox berechnet den Zeitraum bei Mehrdatei-Auswahl nun als globales Minimum aller Startzeitpunkte und globales Maximum aller Endzeitpunkte. Dadurch entstehen keine invertierten Zeiträume mehr, wenn rotierende CSV-Dateien in nicht-chronologischer Reihenfolge ausgewählt werden.

Die Datenqualitätswarnung zeigt konkreter, welche Daten fehlen, wie viele Zeilen bzw. welcher Prozentanteil betroffen sind und wie SAFE_STATE-Zeit einzuordnen ist.

Der Diagramm-Bereich enthält spezifischere Info-Texte für Betriebszustände und MQTT-Wirkungskategorien. Die mobile Balkendarstellung wurde verbessert.

## MQTT-Wirkungsbalken

Die Balken der MQTT-Wirkung werden strikt anhand der absoluten Anzahl Kommandos im Block skaliert. Bei `0 Kommandos` wird kein gefüllter Wertbalken dargestellt; der Hintergrund-/Track wird bei 0 nicht prominent als Balken gezeigt.

Getesteter Referenzfall:

```text
verbessert       37 Kommandos
neutral          75 Kommandos
verschlechtert   23 Kommandos
nicht bewertbar   0 Kommandos
```

Erwartung: `neutral` längster Balken, dann `verbessert`, dann `verschlechtert`, `nicht bewertbar` ohne gefüllten Balken.

## Tests

Auf dem final entpackten ZIP wurden ausgeführt:

```bash
python3 -m py_compile *.py tools/*.py
python3 -m unittest discover -s tests -v
```

Ergebnis: 100 Tests OK.
