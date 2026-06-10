# Technical Notes V12.8.12

## 1. Ziel

V12.8.12 ist ein begrenzter UI-/Diagnose-Hotfix und eine Nachhärtung des in V12.8.11 eingeführten Flow-/Freshness-/Diagnose-Unterbaus. Die fachliche Regelstrategie bleibt unverändert.

## 2. MQTT-Diagnosepuffer leeren

Die MQTT-Topic-Diagnoseseite enthält nun einen Button `Diagnosetabelle leeren`. Der Button ruft serverseitig `POST /mqtt-diagnostics/clear` auf. Dadurch wird nur der gepufferte Diagnosetabelleninhalt gelöscht.

Wichtig:

- MQTT-Subscriptions werden nicht geändert.
- Die laufende Diagnose bleibt aktiv.
- Nach dem Leeren erscheinen neu empfangene, zum Diagnosemodus passende Nachrichten wieder in der Tabelle.
- Der Clear-Vorgang dient nur dazu, alte und neue Diagnosewerte sauber unterscheiden zu können.

## 3. Settings-Restart-Redirect

Die Neustartseite nach `Dienst jetzt neu starten` leitet nun auf die Hauptseite des Controllers weiter, also auf `/` am konfigurierten `WEB_PORT`. Bisher wurde `/status` verwendet, obwohl die eigentliche Controller-Hauptseite unter `/` liegt.

Der Redirect bleibt absolut, damit auch eine Änderung von `WEB_PORT` korrekt berücksichtigt wird. Beispiel:

```text
http://192.168.0.40:8085/
```

statt bisher:

```text
http://192.168.0.40:8085/status
```

## 4. Tests

Neue Tests in `tests/test_v12_8_12_ui_fixes.py` prüfen:

- MQTT-Diagnoseseite enthält Clear-Button und Sicherheitsabfrage.
- `clear_mqtt_diagnostics()` leert vorhandene Diagnosereihen und neue Werte können danach wieder gespeichert werden.
- Restart-Redirect nutzt die Hauptseite `/` statt `/status`.

Zusätzlich wurde der bestehende Restart-UI-Test auf die neue Zielseite angepasst.

## 5. Abgrenzung

Nicht Bestandteil von V12.8.12:

- keine Änderung der eigentlichen Regelstrategie,
- kein vollständiger Standard-/Expertenmodus,
- kein Analyse-Streaming-/Aggregationsumbau,
- keine Datenbank-/Betriebsprotokoll-Funktion,
- keine Änderung der Excel-Lernsimulation.
