# ZEC V16.0.2 – Final Validation 2026-09-17

## Releaseidentität

- Version: `16.0.2`
- Label: `V16.0.2`
- Build-ID: `v16.0.2-20260917`
- Installerpaket: `zendure_controller_v16_0_2.zip`
- unterstützte Updatequelle: `16.0.1 / v16.0.1-20260915`

## Scope

V16.0.2 ist ein enger Installer-Hygiene-/Härtungsrelease. Verwaiste Python-Caches entfernter Altmodule werden vor `rsync --delete` ausschließlich unter einem fail-closed geprüften Cachevertrag bereinigt. Der Live-Regelalgorithmus wurde nicht geändert.

## Geschützter Reglerkern

`controller_logic.py` ist gegenüber V16.0.1 byteidentisch:

`d243945adbb04dfa19fa915f8f32cafb375b7258888b2ecd6fb7a064cdea99ff`

## Technische Gates

- Cache-Hygiene-Regression: **4/4 PASS**
- pytest: **1078 Tests + 692 Subtests PASS**
- pytest mit `ResourceWarning=error`: **1078 Tests + 692 Subtests PASS**
- Deployment-/Fresh-Install-Harness: **11/11 PASS**
- Bash-Syntax: **14/14 PASS**
- Browser-JavaScript: **3/3 PASS**
- Python-Compileall: **PASS**
- Root-Artefakt-Rollback-Fixture: **PASS**
- technisches Datenblatt: **PASS**, 9 Seiten visuell geprüft
- Runtime-Artefaktfreiheit des Releasebestands: **PASS**

## Fresh-Extract-Testnachweis

Der finale Releasebestand wurde frisch extrahiert. Wegen der Laufzeitgrenze der Ausführungsumgebung wurde pytest deterministisch in zwei Prozesse geteilt. Für Shard B wurde `tests/test_v12_10_rc9_rest_surplus.py` zusätzlich als Bootstrap geladen, weil ein historischer Testbestand seinen MQTT-Teststub pro Prozess voraussetzt.

Normal:

- Shard A: 559 Tests + 688 Subtests PASS
- Shard B: 523 Tests + 4 Subtests PASS
- 4 Bootstrap-Tests doppelt
- Netto: **1078 Tests + 692 Subtests PASS**

`ResourceWarning=error`:

- Shard A: 559 Tests + 688 Subtests PASS
- Shard B: 523 Tests + 4 Subtests PASS
- 4 Bootstrap-Tests doppelt
- Netto: **1078 Tests + 692 Subtests PASS**

## Freigabestatus

**TECHNICAL BUILD PASS**

Nicht behauptet wird `PRODUCTIVE-PASS`. Offen bleiben die reale Update-Feldabnahme V16.0.1 → V16.0.2 und der separat zurückgestellte reale Clean-Fresh-/FIRST_INSTALL_SETUP-/Uninstaller-Evidenzblock.
