# Technical Notes V12.11.0-RC1

V12.11.0-RC1 ist ein Diagnose-/Analyse-/UI-/Validierungsrelease auf Basis von V12.10.0-RC10. Die Live-Regelstrategie bleibt unverändert.

## Enthalten

- Semantischer Settings-Validator mit handlungsorientierten ERROR/WARNING/INFO-Meldungen.
- Trennung zwischen benutzerseitig korrigierbaren Settings-Problemen und temporären externen Datenquellenproblemen.
- Statusseite: kompakter Konfigurationsstatus und Zendure-Local-API-Timingkarte.
- Analyse-/Replay-Seite: automatische Harvest-Wirkungsanalyse.
- Gegenfaktische Schätzung des vermiedenen Sofort-Exports durch Harvest mit klarer Annahme.
- Sommer-/Vollspeicher-Einordnung: vorgezogene Speicherung vs. wahrscheinlich dauerhaft zusätzliche Speicherung.
- Cross-Charge-/Harvest-Transition-Auswertung während Harvest.
- Local-API-Timing-Auswertung aus `cycle_timing_json`.
- Settings-UI: Bereichs-Einleitungen, Abstand vor Unterabschnitten, korrigierte Zweitbatterie-Einleitung, Nachtmodus-Master-Schalter zuerst.
- Legacy-Parameter `SMA_DISCHARGE_BLOCK_W` bleibt für Migration/Kompatibilität vorhanden, wird aber nicht mehr in der normalen Settings-UI angezeigt.

## Nicht enthalten

- Keine Änderung an AUTO-Regelstrategie.
- Keine Änderung an Harvest Entry/Stay/Exit.
- Keine Änderung an Cross-Charge-Regelwirkung.
- Keine Änderung an Nachtmodus-Regelwirkung.
- Keine Änderung an MQTT-Topic- oder MQTT-Kommandostruktur.
- Kein Umbau der Zendure-Local-API-Architektur.

## Tests

- `python3 -m py_compile *.py tools/*.py`
- `python3 -m unittest discover -q`
- `bash -n tools/create_zec_analysis_package.sh`
