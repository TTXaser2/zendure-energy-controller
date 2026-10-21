# ZEC V16.0.2 – Build Validation

## Identität

- Version: `16.0.2`
- Label: `V16.0.2`
- Build-ID: `v16.0.2-20260917`

## Scope

Enger Installer-Hygiene-/Härtungsfix für verwaiste `__pycache__`-Verzeichnisse entfernter Altmodule. Keine fachliche Änderung des Live-Regelalgorithmus.

## Source-Gates

- neuer Cache-Hygiene-Regressionsblock: **4/4 PASS**
- vollständige pytest-Suite: **1078 Tests + 692 Subtests PASS**
- vollständige pytest-Suite mit `ResourceWarning=error`: **1078 Tests + 692 Subtests PASS**
- Python-Compileall: **PASS**
- Browser-JavaScript-Syntax: **3/3 PASS**
- Bash-Syntax: **14/14 PASS**
- Deployment-/Fresh-Install-Harness: **11/11 PASS**
- Root-Artefakt-Rollback-Fixture: **PASS**
- technisches Datenblatt: **9 Seiten DOCX/PDF, Releaseidentitätsgate und visuelle Prüfung PASS**
- Measurement-V4-Header: **246/249, unverändert**
- Testdateien: **144**
- `controller_logic.py` zu V16.0.1: **byteidentisch**
  (`d243945adbb04dfa19fa915f8f32cafb375b7258888b2ecd6fb7a064cdea99ff`)

## Finales Fresh-Extract-Gate

Das finale bereinigte Installerpaket wurde erneut in ein leeres Verzeichnis extrahiert und vollständig getestet.

Normaler pytest-Lauf, deterministisch in zwei Shards:

- Shard A: **559 Tests + 688 Subtests PASS**
- Shard B: **523 Tests + 4 Subtests PASS**
- vier Bootstrap-Tests aus `tests/test_v12_10_rc9_rest_surplus.py` wurden in Shard B absichtlich zusätzlich geladen, damit der historische MQTT-Teststub in einem separaten pytest-Prozess identisch zum Gesamtlauf verfügbar ist;
- Nettoergebnis: **1078 Tests + 692 Subtests PASS**.

Mit `ResourceWarning=error` wurde dieselbe Shardfolge wiederholt:

- Shard A: **559 Tests + 688 Subtests PASS**
- Shard B: **523 Tests + 4 Subtests PASS**
- Nettoergebnis: **1078 Tests + 692 Subtests PASS**.

Zusätzlich PASS: Releaseidentität, Source-Manifest, Datenblattgate, Runtime-Artefaktfreiheit, geschützter Reglerkern, Cache-Hygiene-Regression, Deployment-Harness, Bash- und Browser-JavaScript-Gates.

## Status

**TECHNICAL BUILD PASS**

Ein vollständiger `PRODUCTIVE-PASS` ist weiterhin nicht zulässig. Für V16.0.2 steht mindestens die reale Update-Feldabnahme V16.0.1 → V16.0.2 aus. Die bereits separat zurückgestellte reale Clean-Fresh-/FIRST_INSTALL_SETUP-/Uninstaller-Abnahmekette bleibt ebenfalls offen.
