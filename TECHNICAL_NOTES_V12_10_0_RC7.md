# Technical Notes V12.10.0-RC7

## Schwerpunkt

RC7 ist ein Schutz- und Diagnose-RC nach der RC6-Liveauswertung. Der Live-Regelpfad bleibt bewusst schlank. Die größten Änderungen liegen in den nicht-regelrelevanten Analyse-/Exportpfaden und in der Korrektur irreführender V4-Diagnosefelder.

## Änderungen

- Analysepaket-Tool: `replay_report.txt` wird standardmäßig nicht mehr auf dem Raspberry Pi erzeugt. Das Paket enthält weiterhin CSV, Manifest, Config-Snapshots, Runtime-Events und Runtime-/Fallback-Logs und ist damit vollständig offline auswertbar.
- Analysepaket-Tool: optionaler Replay-Report nur noch per `--with-replay-report`; dann mit `timeout`, niedriger CPU-Priorität (`nice`) und niedriger I/O-Priorität (`ionice`, falls verfügbar).
- Analyse-Service: Worker wird mit niedriger Priorität gestartet (`nice`, `ionice` falls verfügbar). Die Preflight-Anzeige berücksichtigt zusätzlich geschätzten Worker-Speicher, RAM-Reserve und Systemlast.
- V4 Cross-Charge-Diagnose: `control_cross_charge_detected` / `control_cross_charge_limited` werden nicht mehr durch normale gleichgerichtete Ladefälle oder Low-Surplus-Rampdown künstlich gesetzt.
- V4 Mapping: `safe_state_reason` bleibt leer, wenn `safe_state_active=0` bzw. der V4-`operating_mode` nicht `SAFE_STATE` ist.
- V4 Mapping: `control_grid_power_w` und `control_effective_export_w` nutzen Fallbacks auch dann, wenn das primäre Legacy-Feld leer ist.
- V4 Rotation: neue Rotationsdateien erhalten kurze, nicht kaskadierende Namen wie `zendure_measurements_v4_YYYYMMDDTHHMMSSZ.csv`.
- Shutdown: SIGTERM/SIGINT fordert einen sauberen Controller-Stop an; der V4-Logger kann dadurch Manifest und Datei besser abschließen.
- Settings: Schätzwert je V4-Standard-Messpunkt auf 650 Bytes angepasst.
- Settings: `LOG_CONTROL` klarer als zusätzliches Debug-/Textlogging eingeordnet.
- V4-Ist-Datenanalyse: Bereich, Tabellen und Kategorien erhalten erklärende Info-Texte.

## Nicht geändert

- Keine MQTT-Topic- oder Kommandostrukturänderung.
- Keine Restüberschuss-Ernte am SMA-Ladelimit.
- Keine breite neue Healthcheck-Architektur im Live-Regelzyklus.
- Keine Cross-Charge-Korrektur in NIGHT_DISCHARGE, festen manuellen Modi, STOP_HOLD oder SAFE_STATE.
