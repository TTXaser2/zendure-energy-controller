# Technical Notes V12.10.0-RC5

V12.10.0-RC5 ist ein Release-Candidate zur Stabilisierung der V4-Loggültigkeit und zur begrenzten Nachtmodus-Exit-Neutralisierung. Die AUTO-Regelstrategie, symmetrische Cross-Charge-Strategie, MQTT-Subscriptions und MQTT-Kommandostruktur bleiben unverändert.

## V4-Rotation und Manifest

- Physische V4-CSV-Dateien werden manifestgeführt behandelt.
- Bei Größenrotation wird eine neue datierte V4-Datei begonnen, statt versteckte `_1`/`_2`-Dateien ohne eigenen Manifest-Eintrag zu erzeugen.
- Jede neu geschriebene physische V4-CSV-Datei erhält einen eigenen Eintrag in `zec_measurement_manifest.json`.
- `logging_file_rotated` wird als Runtime-Event geschrieben.

## Analysepaket-Tool

- Neues Tool: `tools/create_zec_analysis_package.sh`.
- Default-Output: `/home/pi/Downloads`.
- Measurement-Pfad wird automatisch erkannt: zuerst `/media/pi/4CD6-6466/ZEC/logs`, dann `/media/pi/2.0 GB Volume/ZEC/logs`.
- Standardmäßig werden alle `zendure_measurements_v4*.csv`-Dateien eingepackt; `--latest-only` ist optional.
- Temporäre Arbeitsverzeichnisse werden nach erfolgreicher ZIP-Erstellung gelöscht.
- `config.json` wird nicht eingepackt.

## Statusseite / Timing

- Timing-Hauptkennzahl heißt `Aktive Zykluszeit`.
- Hauptwert und Detailwerte kommen aus derselben Timing-Struktur.
- `cycle_total_without_sleep_ms` wird nicht mehr als „Langsamster Teil“ angezeigt.
- Technische Timing-Feldnamen werden in der UI durch verständliche Bezeichnungen ersetzt.

## V4-Mapping

- `control_effective_export_w` nutzt zusätzliche Fallbacks aus der Szenario-Rekonstruktion, wenn keine expliziten Regler-Eingangsfelder vorhanden sind.

## Nachtmodus-Exit-Neutralisierung

Beim Verlassen der festen Nachtentladung wird ein noch aktiver Entlade-Sollwert einmalig auf 0 W neutralisiert. Dadurch kann ein alter Nacht-Entladewert nicht über HOLD/Deadband weiterlaufen. Die Neutralisierung darf `MIN_COMMAND_CHANGE_W` übersteuern. Danach kann AUTO normal weiterarbeiten.

## Nicht enthalten

- Keine symmetrische Cross-Charge-Strategieänderung.
- Keine Restüberschuss-Ernte am SMA-Ladelimit.
- Keine What-if-/Simulator-Nachrechnung.

## Tests

`python -m unittest discover -q` → 157 Tests OK.
