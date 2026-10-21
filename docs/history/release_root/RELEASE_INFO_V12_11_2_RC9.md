# Release-Information V12.11.2-RC9

## Änderungen

- Replay-Status über `/health` statt über die vollständige Startseite.
- Negative Replay-Ergebnisse werden nur kurz gecacht.
- Lokale API: `nicht ausgeführt` statt irreführender `0,0 ms` bei übersprungenem Poll.
- Timing-Reihenfolge entsprechend dem freigegebenen Zielbild korrigiert.
- Mini-Graph: `neuester:` statt `aktuell`.
- Logging: `Belegter Speicher` und belegte Bytes von Gesamt.
- Kommandoabgleich-Leertexte verkürzt.
- Ereignisfooter unterscheidet Störungen, Warnungen, Hinweise und technische Einschränkungen.
- Vier Differentialtests für den bestehenden Modusübergang nach manueller Entladung.

## Tests

```text
python3 -m py_compile *.py tools/*.py
node --check static/status_v2.js
bash -n tools/update_zendure_controller.sh
python3 -m unittest discover -s tests -q
```

Ergebnis:

```text
351 Tests
OK
```

## Migration

Keine Konfigurations- oder Datenbankmigration.

## Nicht-Ziele

- keine Änderung der Regelstrategie,
- keine historische Ereignisbereinigung,
- keine Änderung von MQTT-Themen oder Kommandostruktur,
- keine Änderung am Messdatenschema.
