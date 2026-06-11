# Technical Notes V12.8.14

## Zweck

V12.8.14 ist ein minimaler Hotfix auf Basis von V12.8.13. Anlass waren zwei produktive Beobachtungen nach V12.8.13:

1. Der neue Routentest aus V12.8.13 verwendete `fastapi.testclient.TestClient` und erzeugte dadurch auf dem Raspberry Pi eine zusätzliche Test-only-Abhängigkeit auf `httpx`.
2. Nach `Diagnosetabelle leeren` füllte sich der MQTT-Diagnosepuffer serverseitig wieder, die im Browser sichtbare Tabelle aktualisierte sich aber erst nach manuellem Seiten-Refresh.

Die fachliche Regelstrategie bleibt unverändert.

## Änderungen

- Neuer Endpunkt `/mqtt-diagnostics/data` liefert die aktuellen MQTT-Diagnosezeilen als JSON.
- Die MQTT-Diagnoseseite aktualisiert die sichtbare Tabelle per JavaScript-Polling alle 3 Sekunden.
- Der Button `Aktualisieren` lädt die Diagnosezeilen zusätzlich manuell nach.
- Nach `Diagnosetabelle leeren` erscheinen neue Diagnosewerte automatisch wieder in der sichtbaren Tabelle, sobald sie serverseitig eintreffen.
- Der V12.8.13-Routentest wurde auf direkte Route-/Endpoint-Prüfung umgestellt und benötigt kein `fastapi.testclient.TestClient` mehr. Damit entsteht keine zusätzliche `httpx`-Abhängigkeit auf dem Zielsystem.
- Headless-Verhalten des neuen JSON-Endpunkts ist abgesichert: Im Headless-Modus werden keine Diagnosezeilen ausgeliefert.

## Tests

Neue bzw. angepasste Tests:

- `tests/test_v12_8_13_mqtt_diagnostics_route.py` prüft die MQTT-Diagnoseroute ohne TestClient-/httpx-Abhängigkeit.
- `tests/test_v12_8_14_mqtt_diagnostics_polling.py` prüft Polling-Markup, JSON-Datenendpunkt, Clear plus neue Nachricht und Headless-Verhalten.

Ausgeführt auf final entpacktem ZIP:

```bash
python3 -m py_compile *.py tools/*.py
python3 -m unittest discover -s tests -v
```

Ergebnis: 82 Tests OK.

## Nicht geändert

- Keine Änderung am Live-Regelalgorithmus.
- Keine Änderung an Freshness-/Validity-Entscheidungslogik.
- Keine Änderung an MQTT-Subscriptions oder MQTT-Kommandos.
- Keine Änderung an der finalen Excel-Lernsimulation.
