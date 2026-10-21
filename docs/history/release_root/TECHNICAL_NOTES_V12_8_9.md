# Technische Notizen V12.8.9

## Schwerpunkt

V12.8.9 überarbeitet die Analyse-/Replay-Weboberfläche mit Fokus auf Verständlichkeit, Dark-Mode-Lesbarkeit und robuste Bedienrückmeldungen. Der Live-Regelalgorithmus wurde nicht verändert.

## Korrekturen

- Extended-/Warn-Analysen serialisieren `AnalysisLimits` nicht mehr direkt als Objekt, sondern als JSON-fähige Dicts. Dadurch ist der Fehler `Object of type AnalysisLimits is not JSON serializable` behoben.
- Die Release-Hinweisbox wurde aus der Analyse-Webseite entfernt. Die Version bleibt im Seitentitel sichtbar; Release-Details stehen in README/Technical Notes.
- Auswahl-/Risikobox mit Überschrift und erklärendem Text ergänzt.
- Abbruch einer laufenden Analyse zeigt jetzt einen bestätigten Endzustand: Analyse wurde abgebrochen, keine Analyse läuft, neue Analyse kann gestartet werden.
- `nach oben`-Link am Ende der Analyseergebnisse führt wieder zum Seitenanfang.
- `zendure-replay.service`: `StartLimitIntervalSec` und `StartLimitBurst` stehen nun im `[Unit]`-Abschnitt. Der Kommentar zum optionalen Betrieb wurde präzisiert.

## Darstellungsverbesserungen

- Kurzfazit-/Bewertungsboxen sind im Dark Mode kontrastreicher.
- Ampelfarben wurden systematischer definiert und im Dark Mode eindeutiger dargestellt:
  - Grün: OK/unkritisch
  - Gelb/Amber: prüfen/eingeschränkt/mittlerer Handlungsdruck
  - Rot: kritisch/hoher Handlungsdruck
  - Grau: nicht bewertbar/zu wenig Daten/nicht anwendbar
- Info-Aufklapper wurden layout-stabiler umgesetzt, damit Tabellenlabels beim Öffnen nicht verrutschen.
- Diagrammblock überarbeitet:
  - allgemeine Abschnittserklärung
  - Info-Text je Diagramm
  - Info-Text je wichtiger Einzelbegriff
  - Einheiten/Basis direkt an Balkenwerten
  - Betriebszustände mit menschenlesbarer Dauer und Prozentanteil
  - MQTT-Wirkung mit Count/Prozent/Basis und Kausalitätshinweis
- In der Soll-/Ist-Folge wurde das Label `95%-Perzentil |Netz|` zu `95%-Perzentil Soll/Ist-Abweichung` korrigiert.

## Tests

- py_compile für Haupt- und Tool-Dateien
- unittest discover
- zusätzliche Tests für Replay-UI-Serialisierung, HTML-Kontrast-/Semantikmarker und systemd-Placement
