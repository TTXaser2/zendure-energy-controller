# Technical Notes V12.8.20

V12.8.20 ist ein gezieltes Analyse-/Diagramm-UI-Nacharbeitsrelease auf Basis von V12.8.19. Die AUTO-Regelstrategie, MQTT-Subscriptions, MQTT-Kommandostruktur und das CSV-Schema bleiben unverändert.

## Analyse-Diagramme: robustes Balkenlayout

Die Diagrammzeilen wurden layoutseitig umgebaut. Bisher standen Label, Balken und langer Werttext in einer gemeinsamen Grid-Zeile. Dadurch konnte besonders im rechten Diagrammblock `MQTT-Wirkung` der Textbereich die verfügbare Balkenbreite zusammendrücken; optisch wirkten Balken trotz rechnerisch korrekter Werte weiter zu klein oder inkonsistent.

Neue Struktur je Diagrammzeile:

```text
Begriff              [Balken über definierter Breite]
                     Wert / Prozent / Basis
info                 Erklärung bei Aufklappen
```

Der Werttext steht damit unterhalb des Balkens und beeinflusst dessen verfügbare Breite nicht mehr. Labels dürfen umbrechen, die Balken behalten eine definierte Breite, und die mobile Darstellung verwendet eine einspaltige Struktur.

## Info-Texte vollständig für bekannte Zustände

Der fehlende Info-Text für `HOLD` wurde ergänzt. Zusätzlich wurden die Hilfetexte für bekannte Controller-/Replay-Betriebszustände erweitert, darunter u. a. `MIN_SOC`, `MAX_SOC`, `STOP_HOLD`, `BLOCKED_BY_SMA`, `MANUAL_FIXED_CHARGE`, `MANUAL_FIXED_DISCHARGE`, `CHARGE_RAMP_DOWN`, `DISCHARGE_RAMP_DOWN`, `STARTUP` und `OTHER`.

V12.8.20 ergänzt außerdem einen Test, der bekannte Diagramm-Zustände und MQTT-Wirkungskategorien gegen die vorhandenen Hilfetexte prüft. Dadurch sollen Beschreibungslücken künftig in der Entwicklung auffallen, statt in der UI still kaschiert zu werden.

## Tests

Auf dem final entpackten ZIP wurden ausgeführt:

```bash
python3 -m py_compile *.py tools/*.py
python3 -m unittest discover -s tests -v
```

Ergebnis: 103 Tests OK.
