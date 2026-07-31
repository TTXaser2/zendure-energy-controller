# Build Validation – V12.11.2-RC18

## Basis

```text
V12.11.2-RC17
SHA256 0a5def2f8df824e52ea648ee087e7667435555a98d8821db3d8a7e4872161602
```

## Prüfungen

```text
python3 -m py_compile *.py tools/*.py      PASS
node --check static/status_v2.js           PASS
bash -n tools/update_zendure_controller.sh PASS
python3 -m json.tool config.example.json   PASS
python3 -m unittest discover -s tests -q   483 Tests, PASS
```

Bekannte, bereits vor RC18 vorhandene Python-3.13-`ResourceWarning`-Hinweise älterer SQLite-Tests bleiben ohne Testfehler.

## RC18-Intended-Delta-Tests

17 neue Tests prüfen insbesondere:

- immutable Latest-Snapshot und genau einen Workerthread;
- Request-Timeoutdeckel und monotones Backoff;
- Erfolg, Fehler und Erhalt des letzten erfolgreichen Datensnapshots;
- Configgeneration/IP-Wechsel und Verwerfen verspäteter Ergebnisse;
- deaktivierten Worker und kontrollierten Shutdown;
- blockierenden HTTP-Request ohne Blockierung des Controller-Snapshotreads;
- MQTT-Priorität und timestamp-korrekten API-Fallback;
- RC17→RC18-Headerrotation;
- numerische Power-Cap-/Smoothing-/Step-Flags;
- gestagte Runtime-Events ohne zusätzliche Datei-I/O-Phase vor dem vorhandenen Measurement-Write.

## Measurement-Vertrag

```text
RC18 Standard: 246 Felder · 7842bfef39d47f93
RC18 Extended: 249 Felder · 8f61d07e66428a6e
RC17 Standard: 238 Felder · 192ccc890c2e1d80
RC17 Extended: 241 Felder · f0ce0f22d7110a80
```

## Excel

```text
tools/zendure_regelung_lernwerkzeug_v4_2_7_final.xlsx
SHA256 15f699008c82fe71367604fcb97e1900c023fe8929b40d3fc7210ee2117e79fe
```

Bitidentisch zum RC17-Paket und zur maßgeblichen Projektdatei.

## Sicherheitsabgrenzung

- keine Änderung der RC17-Harvest-Formeln;
- keine Änderung an AUTO, NIGHT oder festen Modi;
- keine Änderung an Command-Lifecycle, Resync, Late-Effect-Guard, Flash-Schutz oder Offgrid;
- keine neuen Config-Keys oder geänderten Defaults;
- keine Storage-Retention/Kompression;
- keine Credentials, produktive `config.json`, Logs, SQLite-Dateien oder Cacheartefakte im Releasepaket.
