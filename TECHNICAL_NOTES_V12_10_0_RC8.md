# Technical Notes V12.10.0-RC8

RC8 ist ein isolierter Stabilitäts-Fix nach der RC7-Liveanalyse. Ziel ist, die Messdatenbasis und Diagnosewege wieder verlässlich zu machen und einen Restart-/HOLD-Zustand zu neutralisieren, ohne neue große Reglerstrategie einzuführen.

## Enthalten

- V4-Logger schreibt neue Service-Starts immer in eine eigene kurze Session-Datei `zendure_measurements_v4_<UTC>.csv`.
- Manifest-Eintrag und physische CSV-Datei müssen dadurch wieder eindeutig zusammenpassen.
- Bestehende `zendure_measurements_v4.csv` wird nicht als aktive neue Session-Datei wiederverwendet und nicht überschrieben.
- Diagnosepaket-Tool stoppt Services standardmäßig nicht mehr; `--stop-services` ist nur noch eine explizite Option.
- Diagnosepaket-Tool kann fallback-only Pakete erzeugen, wenn Primary leer ist und Fallback-Daten vorhanden sind.
- 0-Byte-CSV-Dateien werden nicht als gültige Messdatenbasis gezählt.
- Manifest-referenzierte, aber physisch fehlende Dateien werden im Pakettool als Warnung ausgegeben und in `PACKAGE_INFO.txt` dokumentiert.
- Nach Service-Neustart sendet AUTO/HOLD/DEADBAND einmalig ein erzwungenes neutrales 0/0-Kommando, damit ein vor dem Restart wirksames Zendure-Limit nicht unsichtbar weiterläuft.
- Statuskarte „Zendure Systemleistung“ trennt Zielwert, Istleistung, letztes MQTT-Kommando und unterdrücktes Kommando klarer.

## Nicht enthalten

- Keine Restüberschuss-Ernte bei SMA-Ladelimit.
- Keine neue MQTT-Topic- oder Kommandostruktur.
- Keine breite Healthcheck-Architektur im Live-Regelzyklus.
- Keine neue Cross-Charge-Strategie jenseits der Restart-/HOLD-Neutralisierung.

## Tests

- `python3 -m unittest discover -q` → 174 Tests OK.
- `python3 -m py_compile *.py tools/*.py` → OK.
- `bash -n tools/create_zec_analysis_package.sh` → OK.
