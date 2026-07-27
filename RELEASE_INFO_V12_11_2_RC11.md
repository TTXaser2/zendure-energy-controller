# Release-Information – V12.11.2-RC11

## Zusammenfassung

V12.11.2-RC11 ist ein sicherheits- und recoveryorientierter Zwischenrelease. Er behebt die in der Produktivstörung vom 25.07.2026 bestätigten Blindstellen der 0-W-Neutralisierung und Command-Effect-Überwachung.

## Geändert

- vollständiger Desired-Command-Batch mit Sequenz, Intent, AC-Modus und beiden Limits,
- aktive 0-W-Neutralisierungsüberwachung,
- Full-State-Resync auch bei Ziel 0 W,
- intentbasierter Effect-Timer statt exakter Wattwertbindung,
- getrennte Klassifikation von Richtungsreaktion, Teilwirkung und Sollwerttracking,
- unterhalb der Diagnosegrenze keine falsche `COMMAND_EFFECTIVE`-Bewertung,
- unabhängige, confidencebasierte Leistungsrichtungsbeobachtung,
- offene Mismatches bleiben bei Telemetrieunsicherheit offen,
- Status und Betriebsjournal trennen „Resync ausgeführt“ von „Wirkung bestätigt“,
- additiver Measurement-V4-Vertrag mit sicherer Headerrotation.

## Neuer Konfigurationswert

```text
COMMAND_NEUTRALIZATION_TIMEOUT_SECONDS = 30
```

Wertebereich: 5–300 Sekunden.

## Sicherheitsabgrenzung

Nicht verändert wurden:

- normale AUTO-Regelstrategie,
- Harvest-Allokation einschließlich `SMA_FULL_OR_IDLE`,
- symmetrische Cross-Charge-Berechnung,
- Nacht-Festwert und feste Modi außerhalb der beabsichtigten Wirkungsüberwachung,
- lokale Zendure-API-Architektur,
- MQTT-Topics und Zendure-Payloadstruktur.

## Bekannte offene P1-Punkte

- `SMA_FULL_OR_IDLE`: Delta-/Absolutwertfehler,
- lokale Zendure-API: synchroner Blockierer des Regelzyklus.

Diese Punkte werden bewusst nicht in RC11 vermischt.

## Validierung des Buildstands

```text
python3 -m py_compile *.py tools/*.py     OK
node --check static/status_v2.js          OK
bash -n tools/update_zendure_controller.sh OK
python3 -m unittest discover -s tests -q  384 Tests, OK
```

Bekannter unveränderter Wartungspunkt: Einige ältere SQLite-Tests erzeugen unter Python 3.13 `ResourceWarning: unclosed database`. Die Tests sind grün; RC11 führt keinen neuen synchronen Datenbankzugriff in den Regelpfad ein.

Die finale Excel-Lernsimulation bleibt bitidentisch:

```text
tools/zendure_regelung_lernwerkzeug_v4_2_7_final.xlsx
SHA256: 15f699008c82fe71367604fcb97e1900c023fe8929b40d3fc7210ee2117e79fe
```
