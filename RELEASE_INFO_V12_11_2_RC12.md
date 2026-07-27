# Release-Information – V12.11.2-RC12

## Zusammenfassung

V12.11.2-RC12 schließt den nach der RC11-Produktivprüfung erkannten Zendure-Command-Contract- und Power-Semantik-Block. Schwerpunkt ist die Reduzierung vermeidbarer Flash-Schreibvorgänge, die sichere Rücklesung des vollständigen Gerätezustands und die korrekte Trennung von Netz-, Batterie- und Offgrid-Leistung.

## Verifizierter Gerätekontrakt

Auf dem produktiven Gerät `HEC4NENCN492025` wurden per retained MQTT-Discovery bestätigt:

```text
smartMode/set  → ON / OFF
acMode/set     → Input mode / Output mode
inputLimit/set → 0–2400 W, Schritt 1 W
outputLimit/set→ 0–2400 W, Schritt 1 W
```

Die lokale API bestätigte nach der kontrollierten Schutzmaßnahme `smartMode=1`, ohne Änderung von AC-Modus, Limits, Gerätegrenzen oder Offgrid-Modus.

## Geändert

- `smartMode=1` ist harte Voraussetzung für aktive dynamische Regelkommandos.
- Der ZEC-Runtime-Setter kann `smartMode` nicht deaktivieren.
- Vollständige Command-State-Rücklesung von `smartMode`, `acMode`, `inputLimit` und `outputLimit`.
- Minimale gleichgerichtete Limitupdates nach bestätigtem statischem Zustand.
- Gedrosselter Full-State-Abgleich bei Start, Reconnect, Richtungswechsel, unsicherem Zustand und Recovery.
- Keine Runtime-Schreibpfade für `inverseMaxPower`, `chargeMaxLimit`, `gridOffMode`, `socSet` oder `minSoc`.
- Read-only-Gerätegrenzen klemmen Lade- und Entladeziele zusätzlich.
- Korrekte Sensorsemantik:
  - `outputPackPower` = Batterieladung,
  - `packInputPower` = Batterieentladung,
  - `gridInputPower` = Netz-/AC-Eingang,
  - `outputHomePower` = Ausgang zum Haus,
  - `gridOffPower` = separater Offgrid-Verbrauch.
- Offgrid-Last bleibt von netzseitiger Command-Effect-Bewertung getrennt.
- High-SOC-Ladeannahmebegrenzung wird als `COMMAND_CHARGE_ACCEPTANCE_LIMITED` klassifiziert, ohne falschen Resync.
- Mismatch-Auflösung durch Sicherheitsneutralisierung wird nicht als Recovery bezeichnet.
- `FULL_STATE_NEUTRALIZATION_SENT` und `FULL_STATE_RESYNC_SENT` sind getrennt.
- Measurement-V4-Headerrotation von RC10 oder RC11 auf RC12.

## Sicherheitsinvarianten

- ZEC sendet im produktiven Runtime-Pfad niemals `smartMode=OFF`.
- Aktive dynamische Limits werden nicht gesendet, solange Flash-Schutz oder Command-State nicht frisch bestätigt sind.
- Eine Sicherheitsneutralisierung bleibt handlungsfähig und setzt beide Limits auf 0 W.
- Offgrid-Konfiguration wird nicht verändert.
- Offgrid-Batterieentladung gilt nicht als Hausnetzausgang.
- `writeRsp` wird nicht als Geräte-Acknowledgement verwendet.

## Neue Defaults

```text
ZENDURE_COMMAND_STATE_FRESH_SECONDS = 30
ZENDURE_SMART_MODE_RETRY_SECONDS = 30
ZENDURE_COMMAND_STATE_RETRY_SECONDS = 30
```

## Bewusst nicht geändert

- `SMA_FULL_OR_IDLE`-Zielwertformel,
- synchrone lokale Zendure-API,
- normale AUTO-/Nacht-/Fixed-/Cross-Charge-/Harvest-Formeln außerhalb der Device-Cap-Klemmung,
- Offgrid-Modus und sonstige persistente Zendure-Konfiguration,
- Settings-Redesign.

## Buildvalidierung

```text
python3 -m py_compile *.py tools/*.py      OK
node --check static/status_v2.js           OK
bash -n tools/update_zendure_controller.sh OK
python3 -m unittest discover -s tests -q   399 Tests, OK
```

Einige ältere SQLite-Tests erzeugen unter Python 3.13 weiterhin `ResourceWarning` für nicht geschlossene Testverbindungen. Es trat kein Testfehler auf.

Die finale Excel-Lernsimulation bleibt unverändert und wird bitidentisch ausgeliefert.
