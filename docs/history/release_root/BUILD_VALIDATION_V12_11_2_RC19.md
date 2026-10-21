# Build Validation – Zendure Energy Controller V12.11.2-RC19

**Stand:** 31.07.2026  
**Basis:** finales V12.11.2-RC18-ZIP  
**Release-Scope:** Status-/Diagnose-Stabilisierung

## 1. Syntax- und Vertragsprüfungen

```text
python3 -m py_compile *.py tools/*.py       PASS
node --check static/status_v2.js            PASS
bash -n tools/update_zendure_controller.sh  PASS
python3 -m json.tool config.example.json    PASS
git diff --check                            PASS
```

## 2. Unit- und Regressionstests

```text
python3 -m unittest discover -s tests -q
498 Tests
Ergebnis: OK
```

Davon 15 neue RC19-Tests für:

- exakte CHARGE-/DISCHARGE-Reason-Semantik;
- STOP_HOLD ohne Deadband-Fehlklassifikation;
- korrekte Restkapazität in Early-Return-Modi;
- Requested-vs-Applied und Device-Cap in festen Modi;
- Fixed-Mode-ETA anhand wirksamer Leistung;
- Local-API-Workerdarstellung und Info-Popover;
- Backoff-/Fallback-Diagnose;
- Installer-Ready-Check mit `ready=true`.

Bekannt bleiben Python-3.13-`ResourceWarning`-Hinweise älterer SQLite-Tests. Es trat kein Testfehler auf.

## 3. Measurement-V4-Vertrag

```text
RC19 Standard: 246 Felder
Header-Hash:    7842bfef39d47f93

RC19 Extended: 249 Felder
Header-Hash:    8f61d07e66428a6e
```

Damit ist RC19 gegenüber RC18 schemaidentisch. Es gibt keine Headerrotation und keine zusätzliche Logging-Spalte.

## 4. Excel-Invariante

```text
tools/zendure_regelung_lernwerkzeug_v4_2_7_final.xlsx
SHA256: 15f699008c82fe71367604fcb97e1900c023fe8929b40d3fc7210ee2117e79fe
```

Bitidentisch zur RC18-Basis.

## 5. Sicherheitsabgrenzung

Nicht geändert wurden:

```text
mqtt_bridge.py
command_lifecycle.py
cross_charge.py
zendure_local_api.py
zendure_power_observation.py
config_manager.py
config.example.json
measurement_v4.py
measurement_v4_contract.py
```

`controller_logic.py` ändert nur Housekeeping-/Diagnosezustände und erhält im Fixed-Mode-Pfad die bereits von der unveränderten Command-Cap-Pipeline angewandte Leistung als Requested-vs-Applied-Stufen. Der tatsächlich publizierte Befehl bleibt zum RC18-Verhalten identisch.

## 6. Paketprüfung

Die endgültige ZIP-Prüfung erfolgt nach Erstellung nochmals auf dem frisch entpackten Paket. Das externe Release-Manifest enthält Größe, SHA256, Eintragszahl und Artefaktprüfung.
